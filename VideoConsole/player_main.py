import tkinter as tk
from video_player import VideoTextPlayer

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTextPlayer(root)
    root.mainloop()
