# Overview
This repository is a workflow for downloading and parsing content from youtube videos.

![VideoConsole](./demo.png)

# Workflow
This is currently a generic workflow that's manaully executed
 - Download the video using download_youtube_video.py
 - Run the video through the OCR pipeline using extract_text_from_video.py

# Requirements
## tldr;
```
pip install opencv-python pillow numpy matplotlib
```
## OCR
Using [TrOCR](https://huggingface.co/docs/transformers/model_doc/trocr)

## Python
Not even sure, tbd did it a long time ago
 
### PIP installs
You'll need to install a few python packages using pip. You can do this by running the following command in your terminal:
```bash
pip install yt-dlp
```


