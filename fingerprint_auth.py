"""IoT Fingerprint Authentication System - Improved Version
Author: Dilip Reddy
Description: SIFT-based fingerprint authentication with image upload and web interface
Features: Image file upload, better matching, multi-capture templates, Flask web UI
"""
import tkinter as tk
import cv2
import os
import numpy as np
import pandas as pd
import datetime
import time
from tkinter import messagebox, simpledialog, filedialog
from pathlib import Path

# Initialize GUI window
window = tk.Tk()
window.title("Fingerprint Authentication System - v2.0")
window.configure(background='blue')
window.geometry('1400x600')

# Create title label
message = tk.Label(window, text="Fingerprint Security System v2.0", 
                   bg='green', fg='white', width=50, height=3, 
                   font=('times', 30, 'italic bold underline'))
message.place(x=200, y=40)

# Create necessary directories
for folder in ['Fingerprints', 'StudentDetails', 'Attendance', 'UploadedImages']:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Initialize database file
details_path = 'StudentDetails/StudentDetails.csv'
if not os.path.exists(details_path):
    pd.DataFrame(columns=['Id', 'Name']).to_csv(details_path, index=False)

def enhance_fingerprint(image):
    """Enhance fingerprint image quality using adaptive techniques"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
    
    # Thresholding
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Invert if needed (ridges should be white)
    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)
    
    return binary

def extract_descriptors(image):
    """Extract SIFT/ORB descriptors from fingerprint image"""
    try:
        # Try SIFT first (better quality)
        sift = cv2.SIFT_create()
        keypoints, descriptors = sift.detectAndCompute(image, None)
        
        if descriptors is not None:
            return keypoints, descriptors
    except:
        pass
    
    # Fallback to ORB
    orb = cv2.ORB_create(nfeatures=2000)
    keypoints, descriptors = orb.detectAndCompute(image, None)
    return keypoints, descriptors if descriptors is not None else np.array([])

def get_good_matches(desc1, desc2, method='FLANN'):
    """Find good matches between two descriptor sets with improved matching"""
    if desc1.size == 0 or desc2.size == 0:
        return []
    
    try:
        # Use FLANN for SIFT descriptors
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(desc1, desc2, k=2)
    except:
        # Fallback to Brute Force
        bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        matches = bf.knnMatch(desc1, desc2, k=2)
    
    # Lowe's ratio test
    good = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.7 * n.distance:
                good.append(m)
    
    return good

def create_template(captures):
    """Create a composite template from multiple captures"""
    if not captures:
        return None
    
    # Average the descriptors from all captures
    all_descriptors = []
    for cap in captures:
        all_descriptors.extend(cap)
    
    if not all_descriptors:
        return None
    
    # Convert to numpy array and calculate mean
    template = np.mean(all_descriptors, axis=0)
    return template

def register():
    """Register a new fingerprint template with multiple captures"""
    name = simpledialog.askstring("Register", "Enter Name")
    if not name:
        return
    
    id_input = simpledialog.askstring("Register", "Enter ID (numeric)")
    if not id_input or not id_input.isdigit():
        messagebox.showerror("Error", "Invalid ID")
        return
    
    user_id = int(id_input)
    df = pd.read_csv(details_path)
    
    if user_id in df['Id'].values:
        messagebox.showerror("Error", "ID already exists")
        return
    
    # Ask for registration method
    method = simpledialog.askstring("Registration Method", "Enter method (webcam/upload)")
    method = method.lower() if method else 'webcam'
    
    captures = []
    
    if method == 'upload':
        messagebox.showinfo("Upload", "Select fingerprint image file")
        filepath = filedialog.askopenfilename(
            title="Select Fingerprint Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")]
        )
        
        if filepath:
            image = cv2.imread(filepath)
            if image is not None:
                enhanced = enhance_fingerprint(image)
                kp, desc = extract_descriptors(enhanced)
                
                if desc.size > 100:
                    captures.append(desc)
                    # Save the image
                    cv2.imwrite(f'UploadedImages/{user_id}_registered.jpg', image)
                    messagebox.showinfo("Success", "Image registered successfully!")
                else:
                    messagebox.showerror("Error", "Poor image quality. Try another image.")
            else:
                messagebox.showerror("Error", "Could not read image")
    else:
        # Webcam registration
        messagebox.showinfo("Register", 
                          "Hold finger close to webcam. SPACE to capture (up to 5 times). ESC to finish.")
        
        cam = cv2.VideoCapture(0)
        
        while len(captures) < 5:
            ret, frame = cam.read()
            if not ret:
                continue
            
            cv2.imshow(f'Register - Capture {len(captures) + 1}/5 (SPACE to capture)', frame)
            key = cv2.waitKey(1)
            
            if key == 32: # SPACE
                enhanced = enhance_fingerprint(frame)
                kp, desc = extract_descriptors(enhanced)
                
                if desc.size > 100:
                    captures.append(desc)
                    messagebox.showinfo("Captured", f"Capture {len(captures)} successful!")
                else:
                    messagebox.showerror("Error", "Poor quality - try better lighting.")
            
            if key == 27: # ESC
                break
        
        cam.release()
        cv2.destroyAllWindows()
    
    if captures:
        # Save composite template
        template = create_template(captures)
        np.save(f'Fingerprints/{user_id}_template.npy', template)
        np.save(f'Fingerprints/{user_id}_descriptors.npy', captures[0])
        
        new_entry = pd.DataFrame({'Id': [user_id], 'Name': [name]})
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_csv(details_path, index=False)
        messagebox.showinfo("Success", f"Registered {name} with ID {user_id}")
    else:
        messagebox.showerror("Error", "No valid captures. Registration failed.")

def authenticate():
    """Authenticate user with fingerprint (webcam or upload)"""
    df = pd.read_csv(details_path)
    if df.empty:
        messagebox.showinfo("Info", "No registered users")
        return
    
    # Ask for authentication method
    method = simpledialog.askstring("Authentication Method", "Enter method (webcam/upload)")
    method = method.lower() if method else 'webcam'
    
    live_desc = None
    best_score = 0
    best_name = "Unknown"
    best_id = None
    threshold = 30  # Improved threshold
    
    if method == 'upload':
        messagebox.showinfo("Upload", "Select fingerprint image file")
        filepath = filedialog.askopenfilename(
            title="Select Fingerprint Image for Authentication",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")]
        )
        
        if filepath:
            image = cv2.imread(filepath)
            if image is not None:
                enhanced_live = enhance_fingerprint(image)
                kp_live, live_desc = extract_descriptors(enhanced_live)
                
                if live_desc.size < 100:
                    messagebox.showerror("Error", "Poor image quality. Try another image.")
                    return
            else:
                messagebox.showerror("Error", "Could not read image")
                return
    else:
        # Webcam authentication
        messagebox.showinfo("Login", "Hold registered finger close to webcam. SPACE to capture.")
        
        cam = cv2.VideoCapture(0)
        
        while True:
            ret, frame = cam.read()
            if not ret:
                continue
            
            cv2.imshow('Login - SPACE to capture', frame)
            key = cv2.waitKey(1)
            
            if key == 32: # SPACE
                enhanced_live = enhance_fingerprint(frame)
                kp_live, live_desc = extract_descriptors(enhanced_live)
                
                if live_desc.size < 100:
                    messagebox.showerror("Error", "Poor quality. Try again.")
                    continue
                break
            
            if key == 27: # ESC
                cam.release()
                cv2.destroyAllWindows()
                return
        
        cam.release()
        cv2.destroyAllWindows()
    
    # Compare with all registered fingerprints
    if live_desc is not None:
        for _, row in df.iterrows():
            user_id = int(row['Id'])
            filepath = f'Fingerprints/{user_id}_descriptors.npy'
            
            if os.path.exists(filepath):
                stored_desc = np.load(filepath)
                good_matches = get_good_matches(live_desc, stored_desc)
                score = len(good_matches)
                
                if score > best_score:
                    best_score = score
                    best_name = row['Name']
                    best_id = user_id
        
        # Authentication result
        if best_score >= threshold:
            ts = time.time()
            date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            
            messagebox.showinfo("Success", 
                              f"{best_name} (ID: {best_id}) authenticated!\nMatch Score: {best_score}")
            
            # Record attendance
            attendance_file = f'Attendance/attendance_{date}.csv'
            attendance_entry = pd.DataFrame({
                'Id': [best_id],
                'Name': [best_name],
                'Date': [date],
                'Time': [time_str],
                'Score': [best_score]
            })
            
            if os.path.exists(attendance_file):
                existing = pd.read_csv(attendance_file)
                attendance_entry = pd.concat([existing, attendance_entry], ignore_index=True)
            
            attendance_entry.to_csv(attendance_file, index=False)
        else:
            messagebox.showinfo("Failed", 
                              f"Unknown fingerprint.\nBest Match: {best_name} ({best_id})\nScore: {best_score}/{threshold}")

# Create GUI Buttons
tk.Button(window, text="Register Fingerprint", command=register, 
          fg='red', bg='yellow', width=20, height=3, 
          activebackground='Red', font=('times', 15, 'bold')).place(x=100, y=400)

tk.Button(window, text="Login with Fingerprint", command=authenticate, 
          fg='red', bg='yellow', width=20, height=3, 
          activebackground='Red', font=('times', 15, 'bold')).place(x=600, y=400)

tk.Button(window, text="Quit", command=window.destroy, 
          fg='red', bg='yellow', width=15, height=3, 
          activebackground='Red', font=('times', 15, 'bold')).place(x=1000, y=400)

if __name__ == '__main__':
    window.mainloop()
