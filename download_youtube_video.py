import os
import sys
import subprocess
import datetime
import re
import platform
import argparse
from getpass import getpass

def list_formats(video_url, username=None, password=None):
    """List all available formats for the video"""
    try:
        print(f"Fetching available formats for: {video_url}")
        print("This may take a moment...")
        
        command = [
            "yt-dlp", 
            "-F",  # Capital F to list all formats
        ]
        
        # Add authentication if provided
        if username and password:
            command.extend(["--username", username, "--password", password])
        elif username:
            command.extend(["--username", username])
            
        command.append(video_url)
        
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

def download_with_ytdlp(video_url, format_code=None, username=None, password=None):
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
        
        # Add authentication if provided
        if username and password:
            command.extend(["--username", username, "--password", password])
        elif username:
            command.extend(["--username", username])
            # Password will be prompted by yt-dlp if needed
        
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
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Download YouTube videos with authentication support')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--list', action='store_true', help='List available formats')
    parser.add_argument('--format', '-f', help='Format code to download')
    parser.add_argument('--username', '-u', help='YouTube username or email')
    parser.add_argument('--password', '-p', help='YouTube password (omit for secure prompt)')
    parser.add_argument('--use-env', action='store_true', help='Use YT_USERNAME and YT_PASSWORD environment variables')
    
    args = parser.parse_args()
    
    # Check if the URL is valid
    if not re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$', args.url):
        print("Error: Invalid YouTube URL")
        sys.exit(1)
    
    # Get credentials from environment variables if requested
    username = None
    password = None
    
    if args.use_env:
        username = os.environ.get('YT_USERNAME')
        password = os.environ.get('YT_PASSWORD')
        if not username:
            print("Warning: YT_USERNAME environment variable not set")
    elif args.username:
        username = args.username
        if args.password:
            password = args.password
        else:
            # Securely prompt for password if not provided
            password = getpass("Enter YouTube password: ")
    
    # Check if we should list formats
    if args.list:
        list_formats(args.url, username, password)
        print("\nTo download a specific format, run:")
        print(f"python download_youtube_video.py {args.url} --format <format_code>")
        return
    
    # Download the video
    download_with_ytdlp(args.url, args.format, username, password)

if __name__ == "__main__":
    main()
