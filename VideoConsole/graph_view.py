import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk

class GraphView:
    def __init__(self, parent_frame):
        # Graph area
        self.frame = tk.Frame(parent_frame, bg="#f0f0f0", height=300)
        self.frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, pady=10)
        
        # Graph title
        tk.Label(self.frame, text="Values Over Time:", bg="#f0f0f0", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # Create two separate frames for the graphs
        self.credits_frame = tk.Frame(self.frame, bg="#f0f0f0")
        self.credits_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.bet_win_frame = tk.Frame(self.frame, bg="#f0f0f0")
        self.bet_win_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create matplotlib figures and canvases for both graphs
        self.credits_fig = Figure(figsize=(5, 2), dpi=100)
        self.credits_plot = self.credits_fig.add_subplot(111)
        self.credits_canvas = FigureCanvasTkAgg(self.credits_fig, master=self.credits_frame)
        self.credits_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.bet_win_fig = Figure(figsize=(5, 2), dpi=100)
        self.bet_win_plot = self.bet_win_fig.add_subplot(111)
        self.bet_win_canvas = FigureCanvasTkAgg(self.bet_win_fig, master=self.bet_win_frame)
        self.bet_win_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize empty graphs
        self.initialize_graph()
    
    def initialize_graph(self):
        """Initialize empty graphs"""
        # Credits graph
        self.credits_plot.clear()
        self.credits_plot.set_xlabel('Frame')
        self.credits_plot.set_ylabel('Credits', color='r')
        self.credits_plot.tick_params(axis='y', labelcolor='r')
        self.credits_plot.set_title('Credits Over Time')
        self.credits_plot.grid(True)
        self.credits_fig.tight_layout()
        
        # Bet and Win graph
        self.bet_win_plot.clear()
        self.bet_win_plot.set_xlabel('Frame')
        self.bet_win_plot.set_ylabel('Value')
        self.bet_win_plot.set_title('Bet and Win Over Time')
        self.bet_win_plot.grid(True)
        self.bet_win_fig.tight_layout()
        
        # Draw both canvases
        self.credits_canvas.draw()
        self.bet_win_canvas.draw()
    
    def update_graph(self, data_df):
        """Update both graphs with data from the dataframe"""
        if data_df is None or len(data_df) == 0:
            return "No data to graph yet."
            
        try:
            # Clear both plots
            self.credits_plot.clear()
            self.bet_win_plot.clear()
            
            # Plot Credits on the first graph
            if not data_df['Credits'].isna().all():
                self.credits_plot.plot(data_df['Frame'], data_df['Credits'], 'r-', label='Credits')
                self.credits_plot.set_xlabel('Frame')
                self.credits_plot.set_ylabel('Credits', color='r')
                self.credits_plot.set_title('Credits Over Time')
                self.credits_plot.grid(True)
                self.credits_plot.legend(loc='upper left')
            
            # Plot Bet and Win on the second graph
            has_bet_or_win = False
            
            if not data_df['Bet'].isna().all():
                self.bet_win_plot.plot(data_df['Frame'], data_df['Bet'], 'b-', label='Bet')
                has_bet_or_win = True
                
            if not data_df['Win'].isna().all():
                self.bet_win_plot.plot(data_df['Frame'], data_df['Win'], 'g-', label='Win')
                has_bet_or_win = True
            
            if has_bet_or_win:
                self.bet_win_plot.set_xlabel('Frame')
                self.bet_win_plot.set_ylabel('Value')
                self.bet_win_plot.set_title('Bet and Win Over Time')
                self.bet_win_plot.grid(True)
                self.bet_win_plot.legend(loc='upper left')
            
            # Adjust layout and redraw both canvases
            self.credits_fig.tight_layout()
            self.bet_win_fig.tight_layout()
            self.credits_canvas.draw()
            self.bet_win_canvas.draw()
            
            return f"Graphs updated with {len(data_df)} data points."
            
        except Exception as e:
            error_msg = f"Error updating graphs: {str(e)}"
            print(error_msg)
            return error_msg
