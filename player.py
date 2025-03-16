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
import csv
from enum import Enum, auto
import queue

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
        
        # Define selection area types
        class SelectionType(Enum):
            CREDITS = auto()
            WIN = auto()
            BET = auto()
            
        self.SelectionType = SelectionType
        
        # Selection rectangle variables
        self.current_selection_type = None
        self.selection_areas = {
            SelectionType.CREDITS: {"active": False, "rect": None, "handle": None, 
                                   "start_x": 0, "start_y": 0, "current_x": 0, "current_y": 0,
                                   "color": "red", "label": "Credits"},
            SelectionType.WIN: {"active": False, "rect": None, "handle": None, 
                               "start_x": 0, "start_y": 0, "current_x": 0, "current_y": 0,
                               "color": "green", "label": "Win"},
            SelectionType.BET: {"active": False, "rect": None, "handle": None, 
                               "start_x": 0, "start_y": 0, "current_x": 0, "current_y": 0,
                               "color": "blue", "label": "Bet"}
        }
        
        self.resize_active = False
        self.handle_size = 10
        self.current_frame_image = None
        self.scale_factor_x = 1.0
        self.scale_factor_y = 1.0
        
        # CSV file for saving extracted data
        self.csv_file = "extracted_data.csv"
        self.csv_header_written = False
        
        # Auto-processing settings
        self.auto_process = False
        self.process_interval = 15  # Process every 15 frames
        self.last_processed_frame = -self.process_interval  # Start immediately
        self.processing_queue = queue.Queue()
        self.current_values = {
            "Credits": "N/A",
            "Win": "N/A",
            "Bet": "N/A"
        }
        
        # Thread synchronization
        self.video_lock = threading.RLock()  # Reentrant lock for video access
        self.frame_buffer = None  # Store the latest frame for processing
        
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
        
        # Current values display
        values_frame = tk.Frame(self.video_frame, bg="#333333", height=40)
        values_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Labels for current values
        self.credits_label = tk.Label(values_frame, text="Credits: N/A", 
                                     bg="#333333", fg="white", font=("Arial", 10, "bold"))
        self.credits_label.pack(side=tk.LEFT, padx=10)
                
        self.bet_label = tk.Label(values_frame, text="Bet: N/A", 
                                 bg="#333333", fg="white", font=("Arial", 10, "bold"))
        self.bet_label.pack(side=tk.LEFT, padx=10)

        self.win_label = tk.Label(values_frame, text="Win: N/A", 
                                 bg="#333333", fg="white", font=("Arial", 10, "bold"))
        self.win_label.pack(side=tk.LEFT, padx=10)
        
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
        
        # Selection type radio buttons
        selection_frame = tk.Frame(control_frame, bg="#f0f0f0")
        selection_frame.pack(side=tk.LEFT, padx=5)
        
        self.selection_var = tk.StringVar(value="CREDITS")
        tk.Label(selection_frame, text="Selection:", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Radiobutton(selection_frame, text="Credits", variable=self.selection_var, 
                      value="CREDITS", bg="#f0f0f0", command=self.update_selection_type).pack(side=tk.LEFT)
        tk.Radiobutton(selection_frame, text="Win", variable=self.selection_var, 
                      value="WIN", bg="#f0f0f0", command=self.update_selection_type).pack(side=tk.LEFT)
        tk.Radiobutton(selection_frame, text="Bet", variable=self.selection_var, 
                      value="BET", bg="#f0f0f0", command=self.update_selection_type).pack(side=tk.LEFT)
        
        # Extract from all selections button
        self.extract_all_btn = ttk.Button(control_frame, text="Extract All & Save to CSV", 
                                         command=self.extract_all_selections, state=tk.DISABLED)
        self.extract_all_btn.pack(side=tk.LEFT, padx=5)
        
        # Auto-process toggle button
        self.auto_process_btn = ttk.Button(control_frame, text="Start Auto Processing", 
                                          command=self.toggle_auto_process, state=tk.DISABLED)
        self.auto_process_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear all selections button
        self.clear_all_btn = ttk.Button(control_frame, text="Clear All Selections", 
                                       command=self.clear_all_selections, state=tk.DISABLED)
        self.clear_all_btn.pack(side=tk.LEFT, padx=5)
        
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
            self.extract_all_btn.config(state=tk.NORMAL)
            self.clear_all_btn.config(state=tk.NORMAL)
            self.auto_process_btn.config(state=tk.NORMAL)
            self.update_selection_type()
            
            # Start background processing thread
            self.processing_thread = threading.Thread(target=self.process_queue)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            # Update status
            video_name = os.path.basename(file_path)
            self.status_bar.config(text=f"Loaded: {video_name} | {self.fps:.2f} FPS | Duration: {timedelta(seconds=self.duration)}")
    
    def display_frame(self, frame):
        # Convert frame from BGR to RGB for display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Get fixed canvas dimensions - use the initial dimensions
        canvas_width = 1280
        canvas_height = 720
        
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
        
        # Redraw all active selection rectangles
        for sel_type, sel_data in self.selection_areas.items():
            if sel_data["active"]:
                self.draw_selection_rectangle(sel_type)
        
        # Check if we should auto-process this frame
        if self.auto_process and self.playing:
            current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current_pos >= self.last_processed_frame + self.process_interval:
                self.last_processed_frame = current_pos
                # Store the current frame for processing
                self.frame_buffer = frame.copy()
                # Add to processing queue instead of processing immediately
                self.processing_queue.put(current_pos)
    
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
            # Get the next frame with lock to prevent concurrent access
            with self.video_lock:
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
            self.root.after(0, lambda f=frame.copy(): self.display_frame(f))
            
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
        
        # Use lock when accessing the video file
        with self.video_lock:
            # Seek to the frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            # Update current frame
            self.current_frame = target_frame
            
            # Display the frame
            ret, frame = self.cap.read()
            if ret:
                frame_copy = frame.copy()  # Make a copy to avoid threading issues
                # Step back to keep position correct
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        
        # Display the frame (outside the lock)
        if ret:
            self.display_frame(frame_copy)
        
        # Update time label
        self.update_time_label()
    
    def extract_current_frame(self):
        if not self.cap:
            return
        
        # Get the current frame with lock
        with self.video_lock:
            current_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos - 1)  # Adjust for already moved position
            ret, frame = self.cap.read()
            
            if not ret:
                self.status_bar.config(text="Error: Could not read current frame")
                return
                
            # Make a copy of the frame to avoid threading issues
            frame = frame.copy()
        
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
    
    def update_selection_type(self):
        """Update the current selection type based on radio button selection"""
        selection_str = self.selection_var.get()
        if selection_str == "CREDITS":
            self.current_selection_type = self.SelectionType.CREDITS
        elif selection_str == "WIN":
            self.current_selection_type = self.SelectionType.WIN
        elif selection_str == "BET":
            self.current_selection_type = self.SelectionType.BET
    
    def on_mouse_down(self, event):
        if not self.cap or not self.current_selection_type:
            return
            
        sel_data = self.selection_areas[self.current_selection_type]
        
        # Check if clicking on resize handle of current selection type
        if sel_data["active"] and sel_data["handle"]:
            handle_coords = self.canvas.coords(sel_data["handle"])
            if (abs(event.x - handle_coords[0]) <= self.handle_size and 
                abs(event.y - handle_coords[1]) <= self.handle_size):
                self.resize_active = True
                return
        
        # Check if clicking inside any existing selection rectangle to move it
        for sel_type, data in self.selection_areas.items():
            if data["active"] and data["rect"]:
                coords = self.canvas.coords(data["rect"])
                if (coords[0] <= event.x <= coords[2] and 
                    coords[1] <= event.y <= coords[3]):
                    # Switch to this selection type
                    self.current_selection_type = sel_type
                    self.selection_var.set(sel_type.name)
                    
                    # Calculate offset for moving
                    sel_data = self.selection_areas[sel_type]
                    sel_data["start_x"] = sel_data["start_x"] - (event.x - coords[0])
                    sel_data["start_y"] = sel_data["start_y"] - (event.y - coords[1])
                    sel_data["current_x"] = sel_data["current_x"] - (event.x - coords[0])
                    sel_data["current_y"] = sel_data["current_y"] - (event.y - coords[1])
                    
                    self.resize_active = False
                    return
                
        # Start a new selection for current type
        sel_data = self.selection_areas[self.current_selection_type]
        sel_data["active"] = True
        sel_data["start_x"] = event.x
        sel_data["start_y"] = event.y
        sel_data["current_x"] = event.x
        sel_data["current_y"] = event.y
        self.draw_selection_rectangle(self.current_selection_type)
    
    def on_mouse_drag(self, event):
        if not self.cap or not self.current_selection_type:
            return
            
        sel_data = self.selection_areas[self.current_selection_type]
        if not sel_data["active"]:
            return
            
        if self.resize_active:
            # Resizing the selection
            sel_data["current_x"] = max(0, min(event.x, self.canvas.winfo_width()))
            sel_data["current_y"] = max(0, min(event.y, self.canvas.winfo_height()))
        else:
            # Creating/moving the selection
            sel_data["current_x"] = event.x
            sel_data["current_y"] = event.y
            
        self.draw_selection_rectangle(self.current_selection_type)
    
    def on_mouse_up(self, event):
        self.resize_active = False
        if not self.current_selection_type:
            return
            
        sel_data = self.selection_areas[self.current_selection_type]
        # Ensure the rectangle has some minimum size
        if abs(sel_data["current_x"] - sel_data["start_x"]) < 10 or abs(sel_data["current_y"] - sel_data["start_y"]) < 10:
            if not self.resize_active:  # Only clear if not resizing
                self.clear_selection(self.current_selection_type)
    
    def draw_selection_rectangle(self, selection_type):
        sel_data = self.selection_areas[selection_type]
        
        # Delete existing rectangle
        if sel_data["rect"]:
            self.canvas.delete(sel_data["rect"])
        if sel_data["handle"]:
            self.canvas.delete(sel_data["handle"])
            
        # Draw new rectangle
        x1 = min(sel_data["start_x"], sel_data["current_x"])
        y1 = min(sel_data["start_y"], sel_data["current_y"])
        x2 = max(sel_data["start_x"], sel_data["current_x"])
        y2 = max(sel_data["start_y"], sel_data["current_y"])
        
        sel_data["rect"] = self.canvas.create_rectangle(
            x1, y1, x2, y2, 
            outline=sel_data["color"], 
            width=2,
            dash=(5, 5)
        )
        
        # Add label to the top-left corner
        self.canvas.create_text(
            x1 + 5, y1 + 5,
            text=sel_data["label"],
            fill=sel_data["color"],
            anchor=tk.NW,
            font=("Arial", 8, "bold")
        )
        
        # Add resize handle at bottom-right corner
        sel_data["handle"] = self.canvas.create_rectangle(
            x2 - self.handle_size, y2 - self.handle_size,
            x2 + self.handle_size, y2 + self.handle_size,
            fill=sel_data["color"], outline="white"
        )
    
    def clear_selection(self, selection_type):
        sel_data = self.selection_areas[selection_type]
        sel_data["active"] = False
        if sel_data["rect"]:
            self.canvas.delete(sel_data["rect"])
            sel_data["rect"] = None
        if sel_data["handle"]:
            self.canvas.delete(sel_data["handle"])
            sel_data["handle"] = None
    
    def clear_all_selections(self):
        for sel_type in self.selection_areas:
            self.clear_selection(sel_type)
    
    def extract_from_selection(self, selection_type):
        """Extract text from a specific selection area"""
        if not self.cap or not self.current_frame_image is not None:
            return None, None
            
        sel_data = self.selection_areas[selection_type]
        if not sel_data["active"]:
            return None, None
            
        # Get selection coordinates
        x1 = min(sel_data["start_x"], sel_data["current_x"])
        y1 = min(sel_data["start_y"], sel_data["current_y"])
        x2 = max(sel_data["start_x"], sel_data["current_x"])
        y2 = max(sel_data["start_y"], sel_data["current_y"])
        
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
            return None, None
            
        # Save the cropped frame
        current_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        frame_filename = os.path.join(
            self.extracted_frames_dir, 
            f"frame_{int(current_pos):06d}_{sel_data['label'].lower()}.jpg"
        )
        cv2.imwrite(frame_filename, cropped_frame)
        
        # Process the cropped frame with OCR
        try:
            # Extract text data
            text = pytesseract.image_to_string(cropped_frame).strip()
            
            # Draw rectangle on the frame to show the selection
            display_frame = self.current_frame_image.copy()
            cv2.rectangle(
                display_frame, 
                (orig_x1, orig_y1), 
                (orig_x2, orig_y2), 
                (0, 0, 255) if selection_type == self.SelectionType.CREDITS else
                (0, 255, 0) if selection_type == self.SelectionType.WIN else
                (255, 0, 0),  # BET
                2
            )
            
            return text, frame_filename
            
        except Exception as e:
            print(f"Error extracting text from {sel_data['label']}: {str(e)}")
            return None, None
    
    def extract_all_selections(self):
        """Extract text from all selection areas and save to CSV"""
        if not self.cap or self.current_frame_image is None:
            self.status_bar.config(text="No video loaded or no frame available")
            return
            
        # Check if any selections are active
        active_selections = [sel_type for sel_type, sel_data in self.selection_areas.items() if sel_data["active"]]
        if not active_selections:
            self.status_bar.config(text="Please create at least one selection rectangle first")
            return
            
        # Get the current frame position and timestamp
        current_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        timestamp = timedelta(seconds=current_pos/self.fps)
        
        # Clear previous text
        self.text_display.delete(1.0, tk.END)
        self.text_display.insert(tk.END, f"Frame {int(current_pos)} (Time: {timestamp})\n\n")
        
        # Extract text from each active selection
        results = {}
        display_frame = self.current_frame_image.copy()
        
        for sel_type in self.selection_areas:
            text, filename = self.extract_from_selection(sel_type)
            if text is not None:
                results[sel_type] = text
                self.text_display.insert(tk.END, f"{self.selection_areas[sel_type]['label']}: {text}\n\n")
        
        # Save results to CSV
        self.save_to_csv(current_pos, timestamp, results)
        
        # Display the annotated frame
        self.display_frame(display_frame)
        
        # Update status
        self.status_bar.config(text=f"Text extracted from all selections and saved to CSV")
        
        # Reset position to maintain continuity
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
    
    def save_to_csv(self, frame_number, timestamp, results):
        """Save the extracted text to a CSV file"""
        # Prepare the data row
        row = {
            'Frame': int(frame_number),
            'Timestamp': str(timestamp),
            'Credits': results.get(self.SelectionType.CREDITS, ''),
            'Win': results.get(self.SelectionType.WIN, ''),
            'Bet': results.get(self.SelectionType.BET, '')
        }
        
        # Update current values display
        self.update_current_values(results)
        
        # Check if file exists to determine if we need to write the header
        file_exists = os.path.isfile(self.csv_file)
        
        # Write to CSV
        with open(self.csv_file, 'a', newline='') as csvfile:
            fieldnames = ['Frame', 'Timestamp', 'Credits', 'Win', 'Bet']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            writer.writerow(row)
    
    def update_current_values(self, results):
        """Update the current values display"""
        if self.SelectionType.CREDITS in results:
            self.current_values["Credits"] = results[self.SelectionType.CREDITS]
            self.credits_label.config(text=f"Credits: {self.current_values['Credits']}")
            
        if self.SelectionType.WIN in results:
            self.current_values["Win"] = results[self.SelectionType.WIN]
            self.win_label.config(text=f"Win: {self.current_values['Win']}")
            
        if self.SelectionType.BET in results:
            self.current_values["Bet"] = results[self.SelectionType.BET]
            self.bet_label.config(text=f"Bet: {self.current_values['Bet']}")
    
    def toggle_auto_process(self):
        """Toggle automatic processing of frames"""
        if not self.cap:
            return
            
        # Check if any selections are active
        active_selections = [sel_type for sel_type, sel_data in self.selection_areas.items() if sel_data["active"]]
        if not active_selections:
            self.status_bar.config(text="Please create at least one selection rectangle first")
            return
            
        self.auto_process = not self.auto_process
        
        if self.auto_process:
            self.auto_process_btn.config(text="Stop Auto Processing")
            self.status_bar.config(text=f"Auto processing enabled - processing every {self.process_interval} frames")
        else:
            self.auto_process_btn.config(text="Start Auto Processing")
            self.status_bar.config(text="Auto processing disabled")
    
    def process_queue(self):
        """Background thread to process frames from the queue"""
        while True:
            try:
                # Get frame number from queue with a timeout
                frame_number = self.processing_queue.get(timeout=0.5)
                
                # Process the frame
                self.process_frame_in_background(frame_number)
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except queue.Empty:
                # No frames to process, just continue waiting
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in processing thread: {str(e)}")
                time.sleep(1)  # Avoid tight loop in case of persistent errors
    
    def process_frame_in_background(self, frame_number):
        """Process a frame in the background thread"""
        if not self.cap or self.frame_buffer is None:
            return
            
        # Use the buffered frame instead of accessing the video file
        frame = self.frame_buffer.copy()
            
        # Get timestamp
        timestamp = timedelta(seconds=frame_number/self.fps)
        
        # Extract text from each active selection
        results = {}
        
        for sel_type, sel_data in self.selection_areas.items():
            if not sel_data["active"]:
                continue
                
            # Get selection coordinates
            x1 = min(sel_data["start_x"], sel_data["current_x"])
            y1 = min(sel_data["start_y"], sel_data["current_y"])
            x2 = max(sel_data["start_x"], sel_data["current_x"])
            y2 = max(sel_data["start_y"], sel_data["current_y"])
            
            # Convert to original image coordinates
            orig_x1 = int(x1 * self.scale_factor_x)
            orig_y1 = int(y1 * self.scale_factor_y)
            orig_x2 = int(x2 * self.scale_factor_x)
            orig_y2 = int(y2 * self.scale_factor_y)
            
            # Ensure coordinates are within image bounds
            frame_h, frame_w = frame.shape[:2]
            orig_x1 = max(0, min(orig_x1, frame_w))
            orig_y1 = max(0, min(orig_y1, frame_h))
            orig_x2 = max(0, min(orig_x2, frame_w))
            orig_y2 = max(0, min(orig_y2, frame_h))
            
            # Crop the image
            cropped_frame = frame[orig_y1:orig_y2, orig_x1:orig_x2]
            
            if cropped_frame.size == 0:
                continue
                
            try:
                # Extract text data
                text = pytesseract.image_to_string(cropped_frame).strip()
                if text:
                    results[sel_type] = text
            except Exception as e:
                print(f"Error extracting text from {sel_data['label']}: {str(e)}")
        
        # Save results to CSV if we found any text
        if results:
            # Use the main thread to update UI and save to CSV
            self.root.after(0, lambda: self.save_to_csv(frame_number, timestamp, results))

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTextPlayer(root)
    root.mainloop()
