import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from PIL import Image, ImageTk
import time
import os
import sys

class QRCodeScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AS94 PokeCode Scanner")
        self.root.geometry("640x550")  # Adjusted height to accommodate status and controls
        self.root.resizable(False, False)

        # Set up the custom icon
        if getattr(sys, 'frozen', False):  # Running in a PyInstaller bundle
            application_path = sys._MEIPASS
        else:
            application_path = os.path.dirname(__file__)

        icon_path = os.path.join(application_path, 'favicon.ico')
        self.root.iconbitmap(icon_path)

        # Set up GUI components
        self.button_frame = ttk.LabelFrame(root)
        self.button_frame.pack(padx=10, pady=10, fill="both", expand="yes")

        self.status_label = tk.Label(self.button_frame, text="Status: Not started!", font=("Helvetica", 12))
        self.status_label.pack(pady=5)

        self.current_code_label = tk.Label(self.button_frame, text="Current Code: N/A", font=("Helvetica", 12))
        self.current_code_label.pack(pady=5)

        self.live_indicator = tk.Label(self.button_frame, text="Camera Not Active", font=("Helvetica", 12), fg="red")
        self.live_indicator.pack(pady=5)

        # Create a frame to hold buttons and center them
        self.button_container = tk.Frame(self.button_frame)
        self.button_container.pack(pady=5)

        self.start_button = tk.Button(self.button_container, text="Start Camera", command=self.toggle_camera)
        self.start_button.pack(side="left", padx=5)

        self.open_button = tk.Button(self.button_container, text="Open Scanned Codes!", command=self.open_scanned_codes)
        self.open_button.pack(side="left", padx=5)

        self.clean_button = tk.Button(self.button_container, text="Delete All!", command=self.clean_file)
        self.clean_button.pack(side="left", padx=5)

        # Initialize camera and QR code detector
        self.vid = None
        self.is_camera_on = False
        self.is_scanning = False
        self.scan_thread = None

        self.canvas = tk.Canvas(self.root, width=640, height=480)
        self.canvas.pack()

        self.qr_detector = cv2.QRCodeDetector()  # QR code detector

        # Variables to manage cooldown and last scanned code
        self.last_scanned_code = ""
        self.last_scanned_time = 0
        self.cooldown_period = 3  # 3 seconds cooldown

    def toggle_camera(self):
        if self.is_camera_on:
            self.stop_scanning()
            self.stop_camera()
        else:
            self.start_camera()
            self.start_scanning()

    def start_camera(self):
        self.vid = cv2.VideoCapture(0, cv2.CAP_MSMF)
        if not self.vid.isOpened():
            messagebox.showerror("Error", "Could not open video source.")
            return

        self.is_camera_on = True
        self.live_indicator.config(text="Camera Active", fg="green")
        self.status_label.config(text="Status: Scanning QR Codes")
        self.start_button.config(text="Stop Camera")

    def stop_camera(self):
        if self.is_camera_on and self.vid.isOpened():
            self.vid.release()
            self.vid = None
            self.canvas.delete("all")

        self.is_camera_on = False
        self.live_indicator.config(text="Camera Not Active", fg="red")
        self.status_label.config(text="Status: Not started")
        self.start_button.config(text="Start Camera")

    def start_scanning(self):
        if not self.is_scanning:
            self.is_scanning = True
            if self.scan_thread is None or not self.scan_thread.is_alive():
                self.scan_thread = threading.Thread(target=self.scan)
                self.scan_thread.start()

    def stop_scanning(self):
        self.is_scanning = False
        self.status_label.config(text="Status: Scanning Stopped")

    def scan(self):
        while self.is_scanning:
            if self.vid is not None and self.vid.isOpened():
                ret, frame = self.vid.read()
                if ret:
                    # Show the live frame even if no QR code is detected
                    self.root.after(0, self.show_frame, frame)

                    try:
                        # QR code detection
                        qr_code, pts, _ = self.qr_detector.detectAndDecode(frame)
                        current_time = time.time()

                        # Only process the QR code if it differs from the last scanned one and cooldown period has passed
                        if qr_code and qr_code != self.last_scanned_code and (current_time - self.last_scanned_time) > self.cooldown_period:
                            self.last_scanned_code = qr_code
                            self.last_scanned_time = current_time

                            # Update the label with the last scanned QR code
                            self.root.after(0, self.current_code_label.config, {'text': f"Last Code Scanned: {qr_code}"})

                            # Flash the frame green to indicate QR detected (3 blinks)
                            self.blink_green(frame)

                            # Save scanned code to file
                            with open('qr_codes.txt', 'a') as file:
                                file.write(qr_code + '\n\n')

                    except Exception as e:
                        print(f"Error decoding frame: {e}")

                    cv2.waitKey(1)  # Give OpenCV some time to process
                else:
                    print("Failed to capture frame.")
            else:
                print("Camera is not opened.")
                self.stop_scanning()

    def blink_green(self, frame):
        """Flashes the frame green three times."""
        for _ in range(2):
            # Show the green flash frame
            flashed_frame = self.flash_frame(frame)
            self.root.after(0, self.show_frame, flashed_frame)

            # Wait for 200 milliseconds
            time.sleep(0.15)

            # Show the normal frame again
            self.root.after(0, self.show_frame, frame)

            # Wait for 200 milliseconds
            time.sleep(0.15)

    def flash_frame(self, frame):
        """Adds a green flash effect to the frame."""
        green_frame = np.copy(frame)
        green_frame[:, :, 0] = 76
        green_frame[:, :, 1] = 177
        green_frame[:, :, 2] = 44
        return green_frame

    def show_frame(self, frame):
        """Displays the current frame on the canvas."""
        if frame is None:
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image=image)

        self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        self.canvas.image = photo  # Keep a reference to avoid garbage collection

    def open_scanned_codes(self):
        """Opens the file where scanned QR codes are saved."""
        file_path = 'qr_codes.txt'
        os.system(f"start {os.path.abspath(file_path)}")

    def clean_file(self):
        """Deletes all scanned QR codes."""
        self.current_code_label.config(text="Current Code: N/A")
        self.status_label.config(text="Start Scanning Codes!")
        with open('qr_codes.txt', 'w') as file:
            file.write("")

    def __del__(self):
        """Ensures proper cleanup when the application is closed."""
        self.stop_scanning()
        if self.vid is not None:
            self.stop_camera()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    root = tk.Tk()
    app = QRCodeScannerApp(root)
    root.mainloop()
