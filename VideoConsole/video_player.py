import cv2
import os
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext
from PIL import Image, ImageTk
import numpy as np
from datetime import timedelta
import threading
import time
import queue

from ocr_utils import OCRProcessor
from data_handler import DataHandler
from graph_view import GraphView
from selection_manager import SelectionManager, SelectionType

class VideoTextPlayer:
    def __init__(self, root):
        # Main window setup
        self.root = root
        self.root.title("Video Text Player")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")
        
        # Initialize components
        self.ocr = OCRProcessor()
        self.data_handler = DataHandler()
        
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
        
        # Current frame image for processing
        self.current_frame_image = None
        
        # Current values display
        self.current_values = {
            "Credits": "N/A",
            "Win": "N/A",
            "Bet": "N/A"
        }
        
        # Auto-processing settings
        self.auto_process = False
        self.process_interval = 15  # Process every 15 frames
        self.last_processed_frame = -self.process_interval  # Start immediately
        self.processing_queue = queue.Queue()
        
        # Thread synchronization
        self.video_lock = threading.RLock()  # Reentrant lock for video access
        self.frame_buffer = None  # Store the latest frame for processing
        
        # Create UI components
        self.create_widgets()
        
        # Playback thread
        self.playback_thread = None
        self.stop_playback = False
        
        # Start background processing thread
        self.processing_thread = threading.Thread(target=self.process_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
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
        self.video_canvas = tk.Canvas(self.video_frame, bg="black", width=800, height=450)
        self.video_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Initialize selection manager
        self.selection_manager = SelectionManager(self.video_canvas)
        
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
        self.video_canvas.bind("<ButtonPress-1>", self.selection_manager.on_mouse_down)
        self.video_canvas.bind("<B1-Motion>", self.selection_manager.on_mouse_drag)
        self.video_canvas.bind("<ButtonRelease-1>", self.selection_manager.on_mouse_up)
        
        # Bind keyboard events for nudging selection rectangles
        self.root.bind("<Left>", lambda e: self.nudge_selection("left"))
        self.root.bind("<Right>", lambda e: self.nudge_selection("right"))
        self.root.bind("<Up>", lambda e: self.nudge_selection("up"))
        self.root.bind("<Down>", lambda e: self.nudge_selection("down"))
        
        # Right panel containing text display and graph
        right_panel = tk.Frame(top_frame, bg="#f0f0f0", width=400)
        right_panel.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.BOTH, expand=True)
        
        # Text display area
        text_frame = tk.Frame(right_panel, bg="#f0f0f0")
        text_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Text results
        tk.Label(text_frame, text="Extracted Text:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.text_display = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=40, height=10, font=("Consolas", 10))
        self.text_display.pack(fill=tk.BOTH, expand=True)
        
        # Initialize graph view
        self.graph_view = GraphView(right_panel)
        
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
        
        # Extract current frame button
        self.extract_btn = ttk.Button(control_frame, text="Extract Current Frame", command=self.extract_current_frame, state=tk.DISABLED)
        self.extract_btn.pack(side=tk.LEFT, padx=5)
                
        # Selection type radio buttons
        selection_frame = tk.Frame(control_frame, bg="#f0f0f0")
        selection_frame.pack(side=tk.LEFT, padx=5)
        
        self.selection_var = tk.StringVar(value="CREDITS")
        tk.Label(selection_frame, text="Selection:", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Radiobutton(selection_frame, text="Credits", variable=self.selection_var, 
                      value="CREDITS", bg="#f0f0f0", command=self.update_selection_type).pack(side=tk.LEFT)
        tk.Radiobutton(selection_frame, text="Bet", variable=self.selection_var, 
                      value="BET", bg="#f0f0f0", command=self.update_selection_type).pack(side=tk.LEFT)
        tk.Radiobutton(selection_frame, text="Win", variable=self.selection_var, 
                      value="WIN", bg="#f0f0f0", command=self.update_selection_type).pack(side=tk.LEFT)
        
        # Extract from all selections button
        self.extract_all_btn = ttk.Button(control_frame, text="Extract All & Save to CSV", 
                                         command=self.extract_all_selections, state=tk.DISABLED)
        self.extract_all_btn.pack(side=tk.LEFT, padx=5)
        
        # Auto-process toggle button
        self.auto_process_btn = ttk.Button(control_frame, text="Start Auto Processing", 
                                          command=self.toggle_auto_process, state=tk.DISABLED)
        self.auto_process_btn.pack(side=tk.LEFT, padx=5)
        
        # Update graph button
        self.update_graph_btn = ttk.Button(control_frame, text="Update Graph", 
                                          command=self.update_graph, state=tk.DISABLED)
        self.update_graph_btn.pack(side=tk.LEFT, padx=5)
        
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
            self.update_graph_btn.config(state=tk.NORMAL)
            self.update_selection_type()
            
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
        scale_factor_x = frame_w / new_w
        scale_factor_y = frame_h / new_h
        self.selection_manager.set_scale_factors(scale_factor_x, scale_factor_y)
        
        resized_frame = cv2.resize(rgb_frame, (new_w, new_h))
        
        # Store the current frame for OCR processing
        self.current_frame_image = frame.copy()
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(image=Image.fromarray(resized_frame))
        
        # Clear canvas and display the image
        self.video_canvas.delete("all")
        self.video_canvas.create_image(canvas_width // 2, canvas_height // 2, image=self.photo)
        
        # Redraw all active selection rectangles
        self.selection_manager.redraw_all_selections()
        
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
    
    def update_selection_type(self):
        """Update the current selection type based on radio button selection"""
        selection_str = self.selection_var.get()
        self.selection_manager.set_current_type(selection_str)
    
    def nudge_selection(self, direction):
        """Nudge the current selection in the specified direction"""
        status_msg = self.selection_manager.nudge_selection(direction)
        if status_msg:
            self.status_bar.config(text=status_msg)
    
    def clear_all_selections(self):
        """Clear all selection rectangles"""
        self.selection_manager.clear_all_selections()
        
        # Reset displayed values
        self.current_values = {"Credits": "N/A", "Win": "N/A", "Bet": "N/A"}
        self.credits_label.config(text=f"Credits: {self.current_values['Credits']}")
        self.bet_label.config(text=f"Bet: {self.current_values['Bet']}")
        self.win_label.config(text=f"Win: {self.current_values['Win']}")
        
        # Clear text display
        self.text_display.delete(1.0, tk.END)
    
    def extract_current_frame(self):
        """Extract text from the current frame"""
        if not self.cap:
            return
            
        if not self.ocr.model_loaded:
            self.status_bar.config(text="Please wait for the TrOCR model to finish loading...")
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
        
        # Process the frame with TrOCR
        try:
            extracted_text = self.ocr.extract_text(frame)
            
            # Clear previous text
            self.text_display.delete(1.0, tk.END)
            
            # Get timestamp
            timestamp = timedelta(seconds=current_pos/self.fps)
            
            # Create header for results
            self.text_display.insert(tk.END, f"Frame {int(current_pos)} (Time: {timestamp})\n\n")
            
            if extracted_text and extracted_text.strip():
                # Add text to display
                self.text_display.insert(tk.END, f"Extracted Text:\n{extracted_text}\n\n")
                
                # Since TrOCR doesn't provide bounding boxes, we'll just add a label to the frame
                cv2.putText(frame, "Text detected", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
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
    
    def extract_all_selections(self):
        """Extract text from all selection areas and save to CSV"""
        if not self.cap or self.current_frame_image is None:
            self.status_bar.config(text="No video loaded or no frame available")
            return
            
        # Check if any selections are active
        active_selections = self.selection_manager.get_active_selections()
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
        
        for sel_type in SelectionType:
            coords = self.selection_manager.get_selection_coordinates(sel_type)
            if coords is None:
                continue
                
            orig_x1, orig_y1, orig_x2, orig_y2 = coords
            
            # Ensure coordinates are within image bounds
            frame_h, frame_w = self.current_frame_image.shape[:2]
            orig_x1 = max(0, min(orig_x1, frame_w))
            orig_y1 = max(0, min(orig_y1, frame_h))
            orig_x2 = max(0, min(orig_x2, frame_w))
            orig_y2 = max(0, min(orig_y2, frame_h))
            
            # Crop the image
            cropped_frame = self.current_frame_image[orig_y1:orig_y2, orig_x1:orig_x2]
            
            if cropped_frame.size == 0:
                continue
                
            # Save the cropped frame
            frame_filename = os.path.join(
                self.extracted_frames_dir, 
                f"frame_{int(current_pos):06d}_{self.selection_manager.selection_areas[sel_type]['label'].lower()}.jpg"
            )
            cv2.imwrite(frame_filename, cropped_frame)
            
            # Process with OCR
            try:
                raw_text = self.ocr.extract_text(cropped_frame)
                if raw_text:
                    # Clean the text to extract only numeric values
                    cleaned_text = self.ocr.clean_numeric_text(raw_text)
                    
                    if cleaned_text:
                        results[sel_type] = cleaned_text
                        self.text_display.insert(tk.END, f"{self.selection_manager.selection_areas[sel_type]['label']}: {raw_text} → {cleaned_text}\n\n")
                    else:
                        self.text_display.insert(tk.END, f"{self.selection_manager.selection_areas[sel_type]['label']}: {raw_text} (not a valid number)\n\n")
            except Exception as e:
                print(f"Error extracting text: {str(e)}")
        
        # Update current values display
        self.update_current_values(results)
        
        # Save results to CSV
        if self.data_handler.save_to_csv(current_pos, timestamp, results, SelectionType):
            self.status_bar.config(text=f"Text extracted from all selections and saved to CSV")
        else:
            self.status_bar.config(text=f"Text extracted but not saved to CSV (validation failed)")
        
        # Reset position to maintain continuity
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
    
    def update_current_values(self, results):
        """Update the current values display"""
        if SelectionType.CREDITS in results:
            self.current_values["Credits"] = results[SelectionType.CREDITS]
            self.credits_label.config(text=f"Credits: {self.current_values['Credits']}")
            
        if SelectionType.WIN in results:
            self.current_values["Win"] = results[SelectionType.WIN]
            self.win_label.config(text=f"Win: {self.current_values['Win']}")
            
        if SelectionType.BET in results:
            self.current_values["Bet"] = results[SelectionType.BET]
            self.bet_label.config(text=f"Bet: {self.current_values['Bet']}")
            
        # Auto-update the graph if we have new data
        if self.auto_process and any(key in results for key in [SelectionType.CREDITS, SelectionType.BET, SelectionType.WIN]):
            self.root.after(1000, self.update_graph)  # Update graph after a delay to avoid too frequent updates
    
    def toggle_auto_process(self):
        """Toggle automatic processing of frames"""
        if not self.cap:
            return
            
        # Check if any selections are active
        active_selections = self.selection_manager.get_active_selections()
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
    
    def update_graph(self):
        """Update the graph with data from the CSV file"""
        data_df = self.data_handler.get_data_for_graph()
        status_msg = self.graph_view.update_graph(data_df)
        self.status_bar.config(text=status_msg)
    
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
        """Process a frame in the background thread using TrOCR"""
        if not self.cap or self.frame_buffer is None:
            return
            
        if not self.ocr.model_loaded:
            print("TrOCR model not loaded yet, skipping frame processing")
            return
            
        # Use the buffered frame instead of accessing the video file
        frame = self.frame_buffer.copy()
            
        # Get timestamp
        timestamp = timedelta(seconds=frame_number/self.fps)
        
        # Extract text from each active selection
        results = {}
        
        for sel_type in SelectionType:
            coords = self.selection_manager.get_selection_coordinates(sel_type)
            if coords is None:
                continue
                
            orig_x1, orig_y1, orig_x2, orig_y2 = coords
            
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
                # Extract text
                raw_text = self.ocr.extract_text(cropped_frame)
                
                # Clean the text to extract only numeric values
                if raw_text:
                    cleaned_text = self.ocr.clean_numeric_text(raw_text)
                    if cleaned_text:
                        results[sel_type] = cleaned_text
            except Exception as e:
                print(f"Error extracting text from {sel_type.name}: {str(e)}")
        
        # Save results to CSV if we found any text
        if results:
            # Update UI and save to CSV in the main thread
            self.root.after(0, lambda: self.save_background_results(frame_number, timestamp, results))
    
    def save_background_results(self, frame_number, timestamp, results):
        """Save results from background processing"""
        # Update current values display
        self.update_current_values(results)
        
        # Save to CSV
        self.data_handler.save_to_csv(frame_number, timestamp, results, SelectionType)
