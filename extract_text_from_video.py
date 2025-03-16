import cv2
import pytesseract
import os
import argparse
import numpy as np
from datetime import timedelta

def extract_text_from_video(video_path, output_file, duration_seconds=10, frame_step=12, start_offset=0):
    """
    Extract text from video frames, processing one frame every 'frame_step' frames
    for the specified duration in seconds.
    
    Args:
        video_path: Path to the video file
        output_file: Path to save the extracted text
        duration_seconds: Process only X seconds of video
        frame_step: Process one frame every X frames
        start_offset: Start processing from this time offset in seconds
    """
    # Check if video file exists
    if not os.path.isfile(video_path):
        print(f"Error: Video file {video_path} not found")
        return

    # Check if pytesseract is properly installed
    
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        print("Error: Tesseract OCR not found. Please install it and ensure it's in your PATH.")
        print("Installation guide: https://github.com/tesseract-ocr/tesseract")
        return

    # Open the video file
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        print(f"Error: Could not open video {video_path}")
        return

    # Get video properties
    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate start frame and frames to process based on offset and duration
    start_frame = int(fps * start_offset)
    frames_to_process = min(int(fps * duration_seconds), total_frames - start_frame)
    
    print(f"Video FPS: {fps}")
    print(f"Starting at offset: {start_offset} seconds (frame {start_frame})")
    print(f"Processing {frames_to_process} frames ({duration_seconds} seconds of video)")
    print(f"Taking 1 frame every {frame_step} frames")
    
    # Set video position to start frame
    video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    # Create directory for frames if needed
    frames_dir = "extracted_frames"
    os.makedirs(frames_dir, exist_ok=True)
    
    # Open output file for writing
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Video Text Extraction Results for {os.path.basename(video_path)}\n")
        f.write(f"Processing {duration_seconds} seconds starting at {start_offset} seconds, one frame every {frame_step} frames\n")
        f.write("=" * 80 + "\n\n")
        
        frame_count = 0
        processed_count = 0
        
        while frame_count < frames_to_process:
            ret, frame = video.read()
            
            if not ret:
                break
                
            # Process every Nth frame
            if frame_count % frame_step == 0:
                timestamp = timedelta(seconds=frame_count/fps)
                frame_filename = os.path.join(frames_dir, f"frame_{frame_count:06d}.jpg")
                
                # Save the frame as image
                cv2.imwrite(frame_filename, frame)
                
                # Extract text using pytesseract
                try:
                    # Get text with positioning data
                    data = pytesseract.image_to_data(frame, output_type=pytesseract.Output.DICT)
                    
                    # Write frame header to file
                    f.write(f"Frame {frame_count} (Time: {timestamp})\n")
                    f.write(f"Image saved as: {frame_filename}\n")
                    
                    # Filter out empty text
                    text_found = False
                    
                    for i in range(len(data['text'])):
                        # Skip empty text
                        if not data['text'][i].strip():
                            continue
                            
                        text_found = True
                        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                        conf = data['conf'][i]
                        text = data['text'][i]
                        
                        # Write text and position data to file
                        f.write(f"  Text: '{text}' (Confidence: {conf}%)\n")
                        f.write(f"  Position: x={x}, y={y}, width={w}, height={h}\n")
                        
                    if not text_found:
                        f.write("  No text detected in this frame.\n")
                        
                    f.write("\n" + "-" * 40 + "\n\n")
                    
                except Exception as e:
                    f.write(f"  Error processing frame: {str(e)}\n\n")
                
                processed_count += 1
                print(f"Processed frame {frame_count}/{frames_to_process} ({processed_count} total frames processed)")
                
            frame_count += 1
                
    video.release()
    print(f"Processing complete. Results saved to {output_file}")
    print(f"Extracted frames saved to {frames_dir}/ directory")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text from video frames")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("--output", default="video_text_extraction.txt", help="Output text file path")
    parser.add_argument("--duration", type=int, default=10, help="Process N seconds of video (default: 10)")
    parser.add_argument("--step", type=int, default=12, help="Process one frame every N frames (default: 12)")
    parser.add_argument("--offset", type=int, default=0, help="Start at N seconds into the video (default: 0)")
    
    args = parser.parse_args()
    extract_text_from_video(args.video_path, args.output, args.duration, args.step, args.offset)
