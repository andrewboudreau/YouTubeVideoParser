# YouTube Video Downloader with Cookies Authentication

This script allows you to download YouTube videos using cookies for authentication, which can be useful for accessing higher quality videos or videos that require login.

## How to Get YouTube Cookies

1. Install a browser extension like "Cookie-Editor" for Chrome or Firefox
2. Log in to YouTube in your browser
3. Click on the Cookie-Editor extension icon
4. Click "Export" and select "Export as Netscape HTTP Cookie File"
5. Save the file to your computer (e.g., `youtube_cookies.txt`)

## Using Cookies for Authentication

```bash
python download_youtube_video.py https://www.youtube.com/watch?v=VIDEO_ID --cookies youtube_cookies.txt
```

## Examples

List available formats:
```bash
python download_youtube_video.py https://www.youtube.com/watch?v=VIDEO_ID --list --cookies youtube_cookies.txt
```

Download specific format:
```bash
python download_youtube_video.py https://www.youtube.com/watch?v=VIDEO_ID --format 22 --cookies youtube_cookies.txt
```

## Security Notes

- Keep your cookies file secure as it contains your authentication information
- Cookies will eventually expire, so you may need to export a new file periodically
- This method is more secure than storing passwords in scripts or environment variables
- Your cookies are passed directly to yt-dlp and are not stored by this script
