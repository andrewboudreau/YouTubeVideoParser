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
        
        # Selection rectangle variables
        self.selection_active = False
        self.selection_rect = None
        self.start_x = 0
        self.start_y = 0
        self.current_x = 0
        self.current_y = 0
        self.resize_handle = None
        self.resize_active = False
        self.handle_size = 10
        self.current_frame_image = None
        self.scale_factor_x = 1.0
        self.scale_factor_y = 1.0
        
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
        
        # Bind mouse events for selection rectangle
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
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
        
        # Extract from selection button
        self.extract_selection_btn = ttk.Button(control_frame, text="Extract from Selection", command=self.extract_from_selection, state=tk.DISABLED)
        self.extract_selection_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear selection button
        self.clear_selection_btn = ttk.Button(control_frame, text="Clear Selection", command=self.clear_selection, state=tk.DISABLED)
        self.clear_selection_btn.pack(side=tk.LEFT, padx=5)
        
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
            self.extract_selection_btn.config(state=tk.NORMAL)
            self.clear_selection_btn.config(state=tk.NORMAL)
            
            # Update status
            video_name = os.path.basename(file_path)
            self.status_bar.config(text=f"Loaded: {video_name} | {self.fps:.2f} FPS | Duration: {timedelta(seconds=self.duration)}")
    
    def display_frame(self, frame):
        # Convert frame from BGR to RGB for display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Get fixed canvas dimensions - use the initial dimensions
        canvas_width = 800
        canvas_height = 450
        
        # Resize frame to fit canvas while maintaining aspect ratio
        frame_h, frame_w = frame.shape[:2]
        ratio = min(canvas_width / frame_w, canvas_height / frame_h)
        new_w = int(frame_w * ratio)
        new_h = int(frame_h * ratio)
        
        # Store scale factors for coordinate conversion
        self.scale_factor_x = frame_w / new_w
        self.scale_factor_y = frame_h / new_h
        
        resized_frame = cv2.resize(rgb_frame, (new_w, new_h))
        
        # Store the current frame for OCR processing
        self.current_frame_image = frame.copy()
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(image=Image.fromarray(resized_frame))
        
        # Clear canvas and display the image
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=self.photo)
        
        # Redraw selection rectangle if it exists
        if self.selection_active:
            self.draw_selection_rectangle()
    
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
    
    def on_mouse_down(self, event):
        if not self.cap:
            return
            
        # Check if clicking on resize handle
        if self.selection_active and self.resize_handle:
            handle_coords = self.canvas.coords(self.resize_handle)
            if (abs(event.x - handle_coords[0]) <= self.handle_size and 
                abs(event.y - handle_coords[1]) <= self.handle_size):
                self.resize_active = True
                return
                
        # Start a new selection
        self.clear_selection()
        self.selection_active = True
        self.start_x = event.x
        self.start_y = event.y
        self.current_x = event.x
        self.current_y = event.y
        self.draw_selection_rectangle()
    
    def on_mouse_drag(self, event):
        if not self.selection_active:
            return
            
        if self.resize_active:
            # Resizing the selection
            self.current_x = max(0, min(event.x, self.canvas.winfo_width()))
            self.current_y = max(0, min(event.y, self.canvas.winfo_height()))
        else:
            # Creating/moving the selection
            self.current_x = event.x
            self.current_y = event.y
            
        self.draw_selection_rectangle()
    
    def on_mouse_up(self, event):
        self.resize_active = False
        # Ensure the rectangle has some minimum size
        if abs(self.current_x - self.start_x) < 10 or abs(self.current_y - self.start_y) < 10:
            if not self.resize_active:  # Only clear if not resizing
                self.clear_selection()
    
    def draw_selection_rectangle(self):
        # Delete existing rectangle
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        if self.resize_handle:
            self.canvas.delete(self.resize_handle)
            
        # Draw new rectangle
        x1 = min(self.start_x, self.current_x)
        y1 = min(self.start_y, self.current_y)
        x2 = max(self.start_x, self.current_x)
        y2 = max(self.start_y, self.current_y)
        
        self.selection_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2, 
            outline="red", 
            width=2,
            dash=(5, 5)
        )
        
        # Add resize handle at bottom-right corner
        self.resize_handle = self.canvas.create_rectangle(
            x2 - self.handle_size, y2 - self.handle_size,
            x2 + self.handle_size, y2 + self.handle_size,
            fill="red", outline="white"
        )
    
    def clear_selection(self):
        self.selection_active = False
        self.resize_active = False
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None
        if self.resize_handle:
            self.canvas.delete(self.resize_handle)
            self.resize_handle = None
    
    def extract_from_selection(self):
        if not self.cap or not self.selection_active or not self.current_frame_image is not None:
            if not self.selection_active:
                self.status_bar.config(text="Please create a selection rectangle first")
            return
            
        # Get the current frame position
        current_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        
        # Get selection coordinates
        x1 = min(self.start_x, self.current_x)
        y1 = min(self.start_y, self.current_y)
        x2 = max(self.start_x, self.current_x)
        y2 = max(self.start_y, self.current_y)
        
        # Convert to original image coordinates
        orig_x1 = int(x1 * self.scale_factor_x)
        orig_y1 = int(y1 * self.scale_factor_y)
        orig_x2 = int(x2 * self.scale_factor_x)
        orig_y2 = int(y2 * self.scale_factor_y)
        
        # Ensure coordinates are within image bounds
        frame_h, frame_w = self.current_frame_image.shape[:2]
        orig_x1 = max(0, min(orig_x1, frame_w))
        orig_y1 = max(0, min(orig_y1, frame_h))
        orig_x2 = max(0, min(orig_x2, frame_w))
        orig_y2 = max(0, min(orig_y2, frame_h))
        
        # Crop the image
        cropped_frame = self.current_frame_image[orig_y1:orig_y2, orig_x1:orig_x2]
        
        if cropped_frame.size == 0:
            self.status_bar.config(text="Selection area is too small or invalid")
            return
            
        # Save the cropped frame
        frame_filename = os.path.join(self.extracted_frames_dir, f"frame_{int(current_pos):06d}_cropped.jpg")
        cv2.imwrite(frame_filename, cropped_frame)
        
        # Process the cropped frame with OCR
        try:
            # Extract text data with positions
            data = pytesseract.image_to_data(cropped_frame, output_type=pytesseract.Output.DICT)
            
            # Clear previous text
            self.text_display.delete(1.0, tk.END)
            
            # Get timestamp
            timestamp = timedelta(seconds=current_pos/self.fps)
            
            # Create header for results
            self.text_display.insert(tk.END, f"Selected Region from Frame {int(current_pos)} (Time: {timestamp})\n")
            self.text_display.insert(tk.END, f"Region: ({orig_x1}, {orig_y1}) to ({orig_x2}, {orig_y2})\n\n")
            
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
                
                # Draw rectangle on the cropped frame copy to show text location
                cv2.rectangle(cropped_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            if not text_found:
                self.text_display.insert(tk.END, "No text detected in the selected region.\n")
            
            # Save the annotated cropped frame
            annotated_filename = os.path.join(self.extracted_frames_dir, f"frame_{int(current_pos):06d}_cropped_annotated.jpg")
            cv2.imwrite(annotated_filename, cropped_frame)
            
            # Display the annotated frame with selection rectangle
            display_frame = self.current_frame_image.copy()
            cv2.rectangle(display_frame, (orig_x1, orig_y1), (orig_x2, orig_y2), (0, 0, 255), 2)
            self.display_frame(display_frame)
            
            # Update status
            self.status_bar.config(text=f"Text extracted from selected region. Cropped frame saved as {frame_filename}")
            
        except Exception as e:
            self.status_bar.config(text=f"Error extracting text from selection: {str(e)}")
            self.text_display.delete(1.0, tk.END)
            self.text_display.insert(tk.END, f"Error extracting text: {str(e)}")
        
        # Reset position to maintain continuity
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTextPlayer(root)
    root.mainloop()
