import os
import sys
import subprocess
import datetime
import re
import platform

def list_formats(video_url):
    """List all available formats for the video"""
    try:
        print(f"Fetching available formats for: {video_url}")
        print("This may take a moment...")
        
        command = [
            "yt-dlp", 
            "-F",  # Capital F to list all formats
            video_url
        ]
        
        result = subprocess.run(command, 
                               shell=(platform.system() == "Windows"),
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)
        
        if result.returncode == 0:
            print("\nAvailable formats:")
            print(result.stdout)
            return True
        else:
            print(f"Error fetching formats: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False

def download_with_ytdlp(video_url, format_code=None):
    try:
        # Check if yt-dlp is installed
        try:
            subprocess.run(["yt-dlp", "--version"], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, 
                          check=True,
                          shell=(platform.system() == "Windows"))
        except (subprocess.SubprocessError, FileNotFoundError):
            print("yt-dlp is not installed. Installing it now...")
            
            # Install yt-dlp using pip
            install_cmd = ["pip", "install", "yt-dlp"]
            subprocess.run(install_cmd, check=True, shell=(platform.system() == "Windows"))
            print("yt-dlp installed successfully!")
        
        # Get current datetime
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Format the output filename template
        # %(channel)s = YouTube channel name
        # We add the current date/time manually since we want the current time, not upload time
        filename_template = f"%(channel)s_{current_time}.%(ext)s"
        
        # Clean up the filename to remove invalid characters
        filename_template = re.sub(r'[\\/*?:"<>|]', "_", filename_template)
        
        # Prepare the yt-dlp command
        command = [
            "yt-dlp", 
            "-o", filename_template,  # Output filename format
            "--no-playlist",          # Don't download playlists
            "--no-mtime",             # Don't use the media file's modification time
        ]
        
        # Add format code if specified
        if format_code:
            command.extend(["-f", format_code])
        else:
            command.extend(["-f", "best"])  # Best quality by default
            
        command.append(video_url)
        
        print(f"Downloading video from: {video_url}")
        print(f"Using filename template: {filename_template}")
        if format_code:
            print(f"Format selected: {format_code}")
        else:
            print("Format selected: best available quality")
            
        print("Starting download...")
        
        # Execute the command
        result = subprocess.run(command, 
                               shell=(platform.system() == "Windows"),
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)
        
        if result.returncode == 0:
            print("Download completed successfully!")
            
            # Try to extract the actual filename from the output
            output = result.stdout
            match = re.search(r'Destination:\s+(.*\.[\w\d]+)', output)
            if match:
                filename = match.group(1)
                print(f"Video saved as: {filename}")
            else:
                print("Video saved with the format: [ChannelName]_[DateTime].[ext]")
        else:
            print(f"Error downloading the video:")
            print(result.stderr)
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def main():
    # Check if URL is provided
    if len(sys.argv) < 2:
        print("Usage:")
        print("  List formats: python yt_dlp_downloader.py <YouTube URL> --list")
        print("  Download specific format: python yt_dlp_downloader.py <YouTube URL> --format <format_code>")
        print("  Download best quality: python yt_dlp_downloader.py <YouTube URL>")
        sys.exit(1)
    
    # Get URL from command line argument
    video_url = sys.argv[1]
    
    # Check if the URL is valid
    if not re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$', video_url):
        print("Error: Invalid YouTube URL")
        sys.exit(1)
    
    # Check if we should list formats
    if len(sys.argv) >= 3 and sys.argv[2] == "--list":
        list_formats(video_url)
        print("\nTo download a specific format, run:")
        print(f"python yt_dlp_downloader.py {video_url} --format <format_code>")
        return
        
    # Check if a format was specified
    format_code = None
    if len(sys.argv) >= 4 and sys.argv[2] == "--format":
        format_code = sys.argv[3]
        
    # Download the video
    download_with_ytdlp(video_url, format_code)

if __name__ == "__main__":
    main()