import cv2
import pytesseract
import os
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext
from PIL import Image, ImageTk
import numpy as np
from datetime import timedelta
import threading
import time

class VideoTextPlayer:
    def __init__(self, root):
        # Initialize Tesseract path - update this for your system if needed
        self.tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        
        # Main window setup
        self.root = root
        self.root.title("Video Text Player")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")
        
        # Video variables
        self.video_path = None
        self.cap = None
        self.fps = 0
        self.total_frames = 0
        self.current_frame = 0
        self.duration = 0
        self.playing = False
        self.extracted_frames_dir = "extracted_frames"
        os.makedirs(self.extracted_frames_dir, exist_ok=True)
        
        # Create UI components
        self.create_widgets()
        
        # Playback thread
        self.playback_thread = None
        self.stop_playback = False
        
    def create_widgets(self):
        # Main frame layout
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top frame for video and controls
        top_frame = tk.Frame(main_frame, bg="#f0f0f0")
        top_frame.pack(fill=tk.BOTH, expand=True)
        
        # Video display area
        self.video_frame = tk.Frame(top_frame, bg="black", width=800, height=450)
        self.video_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.BOTH, expand=True)
        
        # Canvas for video display
        self.canvas = tk.Canvas(self.video_frame, bg="black", width=800, height=450)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Text display area (right panel)
        text_frame = tk.Frame(top_frame, bg="#f0f0f0", width=400)
        text_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.BOTH)
        
        # Text results
        tk.Label(text_frame, text="Extracted Text:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.text_display = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=40, height=20, font=("Consolas", 10))
        self.text_display.pack(fill=tk.BOTH, expand=True)
        
        # Bottom frame for controls
        bottom_frame = tk.Frame(main_frame, bg="#f0f0f0", height=150)
        bottom_frame.pack(fill=tk.X, pady=10)
        
        # Control buttons frame
        control_frame = tk.Frame(bottom_frame, bg="#f0f0f0")
        control_frame.pack(fill=tk.X, pady=5)
        
        # Load video button
        self.load_btn = ttk.Button(control_frame, text="Load Video", command=self.load_video)
        self.load_btn.pack(side=tk.LEFT, padx=5)
        
        # Play/Pause button
        self.play_pause_btn = ttk.Button(control_frame, text="Play", command=self.toggle_play_pause, state=tk.DISABLED)
        self.play_pause_btn.pack(side=tk.LEFT, padx=5)
        
        # Extract text button
        self.extract_btn = ttk.Button(control_frame, text="Extract Text from Frame", command=self.extract_current_frame, state=tk.DISABLED)
        self.extract_btn.pack(side=tk.LEFT, padx=5)
        
        # Time display
        self.time_label = tk.Label(control_frame, text="00:00:00 / 00:00:00", bg="#f0f0f0", font=("Arial", 10))
        self.time_label.pack(side=tk.RIGHT, padx=10)
        
        # Progress bar frame
        progress_frame = tk.Frame(bottom_frame, bg="#f0f0f0")
        progress_frame.pack(fill=tk.X, pady=5)
        
        # Video progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(progress_frame, variable=self.progress_var, from_=0, to=100, 
                                     orient=tk.HORIZONTAL, command=self.seek)
        self.progress_bar.pack(fill=tk.X, padx=10)
        self.progress_bar.config(state=tk.DISABLED)
        
        # Status bar
        self.status_bar = tk.Label(main_frame, text="Ready. Load a video to begin.", 
                                  bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def load_video(self):
        # Open file dialog to select video
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov"), ("All files", "*.*")]
        )
        
        if file_path:
            # Release previous video if any
            if self.cap is not None:
                self.stop_playback = True
                if self.playback_thread and self.playback_thread.is_alive():
                    self.playback_thread.join()
                self.cap.release()
            
            self.video_path = file_path
            self.cap = cv2.VideoCapture(file_path)
            
            if not self.cap.isOpened():
                self.status_bar.config(text=f"Error: Could not open video {file_path}")
                return
            
            # Get video properties
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.duration = self.total_frames / self.fps
            self.current_frame = 0
            
            # Display the first frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame)
            
            # Update time label and controls
            self.update_time_label()
            self.progress_bar.config(state=tk.NORMAL)
            self.play_pause_btn.config(state=tk.NORMAL)
            self.extract_btn.config(state=tk.NORMAL)
            
            # Update status
            video_name = os.path.basename(file_path)
            self.status_bar.config(text=f"Loaded: {video_name} | {self.fps:.2f} FPS | Duration: {timedelta(seconds=self.duration)}")
    
    def display_frame(self, frame):
        # Convert frame from BGR to RGB for display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Resize frame to fit canvas while maintaining aspect ratio
        frame_h, frame_w = frame.shape[:2]
        ratio = min(canvas_width / frame_w, canvas_height / frame_h)
        new_w = int(frame_w * ratio)
        new_h = int(frame_h * ratio)
        
        resized_frame = cv2.resize(rgb_frame, (new_w, new_h))
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(image=Image.fromarray(resized_frame))
        
        # Update canvas
        self.canvas.config(width=new_w, height=new_h)
        self.canvas.create_image(new_w // 2, new_h // 2, image=self.photo)
    
    def toggle_play_pause(self):
        if not self.cap:
            return
        
        if self.playing:
            # Pause the video
            self.playing = False
            self.play_pause_btn.config(text="Play")
            self.stop_playback = True
        else:
            # Play the video
            self.playing = True
            self.play_pause_btn.config(text="Pause")
            self.stop_playback = False
            
            # Start playback in a separate thread
            self.playback_thread = threading.Thread(target=self.play_video)
            self.playback_thread.daemon = True
            self.playback_thread.start()
    
    def play_video(self):
        # Main playback loop
        while self.playing and not self.stop_playback:
            # Get the next frame
            ret, frame = self.cap.read()
            
            if not ret:
                # End of video
                self.playing = False
                self.play_pause_btn.config(text="Play")
                # Reset to beginning
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.current_frame = 0
                # Update UI
                self.root.after(0, self.update_time_label)
                break
            
            # Update current frame
            self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            
            # Display the frame
            self.root.after(0, lambda f=frame: self.display_frame(f))
            
            # Update progress and time
            self.root.after(0, self.update_time_label)
            
            # Control playback speed
            time.sleep(1 / self.fps)
    
    def update_time_label(self):
        if not self.cap:
            return
        
        # Calculate current time and total duration
        current_time = self.current_frame / self.fps
        total_time = self.total_frames / self.fps
        
        # Format as HH:MM:SS
        current_str = str(timedelta(seconds=int(current_time)))
        total_str = str(timedelta(seconds=int(total_time)))
        
        # Update label
        self.time_label.config(text=f"{current_str} / {total_str}")
        
        # Update progress bar without triggering the seek function
        progress_val = (self.current_frame / self.total_frames) * 100
        self.progress_var.set(progress_val)
    
    def seek(self, value):
        if not self.cap or self.progress_bar.cget('state') == tk.DISABLED:
            return
        
        # Calculate the frame to seek to
        value = float(value)
        target_frame = int((value / 100) * self.total_frames)
        
        # Seek to the frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        
        # Update current frame
        self.current_frame = target_frame
        
        # Display the frame
        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)
            # Step back to keep position correct
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        
        # Update time label
        self.update_time_label()
    
    def extract_current_frame(self):
        if not self.cap:
            return
        
        # Get the current frame
        current_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos - 1)  # Adjust for already moved position
        ret, frame = self.cap.read()
        
        if not ret:
            self.status_bar.config(text="Error: Could not read current frame")
            return
        
        # Save the frame
        frame_filename = os.path.join(self.extracted_frames_dir, f"frame_{int(current_pos):06d}.jpg")
        cv2.imwrite(frame_filename, frame)
        
        # Process the frame with OCR
        try:
            # Extract text data with positions
            data = pytesseract.image_to_data(frame, output_type=pytesseract.Output.DICT)
            
            # Clear previous text
            self.text_display.delete(1.0, tk.END)
            
            # Get timestamp
            timestamp = timedelta(seconds=current_pos/self.fps)
            
            # Create header for results
            self.text_display.insert(tk.END, f"Frame {int(current_pos)} (Time: {timestamp})\n\n")
            
            # Track if any text was found
            text_found = False
            
            # Process all text found
            for i in range(len(data['text'])):
                # Skip empty text
                if not data['text'][i].strip():
                    continue
                
                text_found = True
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                conf = data['conf'][i]
                text = data['text'][i]
                
                # Add text with position to display
                self.text_display.insert(tk.END, f"Text: '{text}' (Confidence: {conf}%)\n")
                self.text_display.insert(tk.END, f"Position: x={x}, y={y}, width={w}, height={h}\n\n")
                
                # Draw rectangle on the frame copy to show text location
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            if not text_found:
                self.text_display.insert(tk.END, "No text detected in this frame.\n")
            
            # Display the annotated frame
            self.display_frame(frame)
            
            # Save the annotated frame
            annotated_filename = os.path.join(self.extracted_frames_dir, f"frame_{int(current_pos):06d}_annotated.jpg")
            cv2.imwrite(annotated_filename, frame)
            
            # Update status
            self.status_bar.config(text=f"Text extracted from frame {int(current_pos)}. Frame saved as {frame_filename}")
            
        except Exception as e:
            self.status_bar.config(text=f"Error extracting text: {str(e)}")
            self.text_display.delete(1.0, tk.END)
            self.text_display.insert(tk.END, f"Error extracting text: {str(e)}")
        
        # Reset position to maintain continuity
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTextPlayer(root)
    root.mainloop()