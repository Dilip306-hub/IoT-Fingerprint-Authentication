"""IoT Fingerprint Authentication System
Author: Dilip Reddy
Description: SIFT-based fingerprint authentication for resource-constrained IoT devices
"""

import tkinter as tk
import cv2
import os
import numpy as np
import pandas as pd
import datetime
import time
from tkinter import messagebox, simpledialog

# Initialize GUI window
window = tk.Tk()
window.title("Fingerprint Authentication System")
window.configure(background='blue')
window.geometry('1400x600')

# Create title label
message = tk.Label(window, text="Fingerprint Security System", 
                   bg='green', fg='white', width=50, height=3, 
                   font=('times', 30, 'italic bold underline'))
message.place(x=200, y=40)

# Create necessary directories
for folder in ['Fingerprints', 'StudentDetails', 'Attendance']:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Initialize database file
details_path = 'StudentDetails/StudentDetails.csv'
if not os.path.exists(details_path):
    pd.DataFrame(columns=['Id', 'Name']).to_csv(details_path, index=False)

def enhance_fingerprint(image):
    """Enhance fingerprint image quality using Gaussian blur and thresholding"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Invert if needed (ridges should be white)
    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)
    return binary

def extract_descriptors(image):
    """Extract SIFT or ORB descriptors from fingerprint image"""
    orb = cv2.ORB_create(nfeatures=1000)
    keypoints, descriptors = orb.detectAndCompute(image, None)
    return keypoints, descriptors if descriptors is not None else np.array([])

def get_good_matches(desc1, desc2):
    """Find good matches between two descriptor sets using FLANN"""
    if desc1.size == 0 or desc2.size == 0:
        return []
    
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(desc1, desc2, k=2)
    
    good = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.75 * n.distance:  # Lowe's ratio test
                good.append(m)
    return good

def register():
    """Register a new fingerprint template"""
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
    
    messagebox.showinfo("Register", 
        "Hold finger close to webcam. Good light, plain background. SPACE to capture (up to 5 times). ESC to finish.")
    
    captures = []
    cam = cv2.VideoCapture(0)
    
    while len(captures) < 5:
        ret, frame = cam.read()
        if not ret:
            continue
        
        cv2.imshow('Register - SPACE to capture', frame)
        key = cv2.waitKey(1)
        
        if key == 32:  # SPACE
            enhanced = enhance_fingerprint(frame)
            kp, desc = extract_descriptors(enhanced)
            
            if desc.size > 100:
                captures.append(desc)
                messagebox.showinfo("Captured", f"Capture {len(captures)} successful!")
            else:
                messagebox.showerror("Error", "Poor quality - try better lighting.")
        
        if key == 27:  # ESC
            break
    
    if captures:
        np.save(f'Fingerprints/{user_id}.npy', captures[0])
        new_entry = pd.DataFrame({'Id': [user_id], 'Name': [name]})
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_csv(details_path, index=False)
        messagebox.showinfo("Success", f"Registered {name} with ID {user_id}")
    
    cam.release()
    cv2.destroyAllWindows()

def authenticate():
    """Authenticate user with fingerprint"""
    df = pd.read_csv(details_path)
    if df.empty:
        messagebox.showinfo("Info", "No registered users")
        return
    
    messagebox.showinfo("Login", "Hold registered finger close to webcam. SPACE to capture.")
    
    cam = cv2.VideoCapture(0)
    best_score = 0
    best_name = "Unknown"
    best_id = None
    
    while True:
        ret, frame = cam.read()
        if not ret:
            continue
        
        cv2.imshow('Login - SPACE to capture', frame)
        key = cv2.waitKey(1)
        
        if key == 32:  # SPACE
            enhanced_live = enhance_fingerprint(frame)
            kp_live, live_desc = extract_descriptors(enhanced_live)
            
            if live_desc.size < 100:
                messagebox.showerror("Error", "Poor quality. Try again.")
                continue
            
            # Compare with all registered fingerprints
            for _, row in df.iterrows():
                user_id = int(row['Id'])
                filepath = f'Fingerprints/{user_id}.npy'
                
                if os.path.exists(filepath):
                    stored_desc = np.load(filepath)
                    good_matches = get_good_matches(live_desc, stored_desc)
                    score = len(good_matches)
                    
                    if score > best_score:
                        best_score = score
                        best_name = row['Name']
                        best_id = user_id
            
            # Authentication threshold
            if best_score >= 20:  # Adjustable threshold
                ts = time.time()
                date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                
                messagebox.showinfo("Success", 
                    f"{best_name} (ID: {best_id}) authenticated! Score: {best_score}")
                
                # Record attendance
                attendance_file = f'Attendance/attendance_{date}.csv'
                attendance_entry = pd.DataFrame({
                    'Id': [best_id],
                    'Name': [best_name],
                    'Date': [date],
                    'Time': [time_str]
                })
                
                if os.path.exists(attendance_file):
                    existing = pd.read_csv(attendance_file)
                    attendance_entry = pd.concat([existing, attendance_entry], ignore_index=True)
                
                attendance_entry.to_csv(attendance_file, index=False)
            else:
                messagebox.showinfo("Failed", 
                    f"Unknown fingerprint. Best score: {best_score}")
            break
        
        if key == 27:  # ESC
            break
    
    cam.release()
    cv2.destroyAllWindows()

# Create GUI Buttons
tk.Button(window, text="Register Fingerprint", command=register, 
          fg='red', bg='yellow', width=20, height=3, 
          activebackground='Red', font=('times', 15, 'bold')).place(x=200, y=400)

tk.Button(window, text="Login with Fingerprint", command=authenticate, 
          fg='red', bg='yellow', width=20, height=3, 
          activebackground='Red', font=('times', 15, 'bold')).place(x=600, y=400)

tk.Button(window, text="Quit", command=window.destroy, 
          fg='red', bg='yellow', width=15, height=3, 
          activebackground='Red', font=('times', 15, 'bold')).place(x=1000, y=400)

if __name__ == '__main__':
    window.mainloop()
