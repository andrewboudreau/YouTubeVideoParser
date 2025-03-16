# YouTube Video Downloader with Authentication

This script allows you to download YouTube videos with authentication support, which can be useful for accessing higher quality videos or videos that require login.

## Authentication Methods

There are three ways to provide your YouTube credentials:

### 1. Command Line Arguments

```bash
python download_youtube_video.py https://www.youtube.com/watch?v=VIDEO_ID --username your_email@example.com --password your_password
```

Note: Providing passwords on the command line is not secure as they may be visible in your command history.

### 2. Username with Secure Password Prompt

```bash
python download_youtube_video.py https://www.youtube.com/watch?v=VIDEO_ID --username your_email@example.com
```

This will prompt you to enter your password securely (characters won't be displayed as you type).

### 3. Environment Variables (Most Secure)

Set environment variables before running the script:

```bash
# On Linux/macOS
export YT_USERNAME="your_email@example.com"
export YT_PASSWORD="your_password"

# On Windows
set YT_USERNAME=your_email@example.com
set YT_PASSWORD=your_password
```

Then run the script with the `--use-env` flag:

```bash
python download_youtube_video.py https://www.youtube.com/watch?v=VIDEO_ID --use-env
```

## Examples

List available formats:
```bash
python download_youtube_video.py https://www.youtube.com/watch?v=VIDEO_ID --list --use-env
```

Download specific format:
```bash
python download_youtube_video.py https://www.youtube.com/watch?v=VIDEO_ID --format 22 --use-env
```

## Security Notes

- Environment variables are generally more secure than command line arguments
- For maximum security, use the username flag without password to get a secure prompt
- Your credentials are passed directly to yt-dlp and are not stored by this script
