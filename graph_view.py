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
        
        # Create matplotlib figure and canvas
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.plot = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize empty graph
        self.initialize_graph()
    
    def initialize_graph(self):
        """Initialize an empty graph"""
        self.plot.clear()
        self.plot.set_xlabel('Frame')
        self.plot.set_ylabel('Credits', color='r')
        self.plot.tick_params(axis='y', labelcolor='r')
        
        # Create a second y-axis
        ax2 = self.plot.twinx()
        ax2.set_ylabel('Bet / Win', color='g')
        ax2.tick_params(axis='y', labelcolor='g')
        
        self.plot.set_title('Credits, Bet, and Win Over Time')
        self.plot.grid(True)
        self.fig.tight_layout()
        self.canvas.draw()
    
    def update_graph(self, data_df):
        """Update the graph with data from the dataframe"""
        if data_df is None or len(data_df) == 0:
            return "No data to graph yet."
            
        try:
            # Clear the plot
            self.plot.clear()
            
            # Create a second y-axis for Bet and Win
            ax1 = self.plot
            ax2 = ax1.twinx()
            
            # Plot Credits on the left y-axis
            if not data_df['Credits'].isna().all():
                ax1.plot(data_df['Frame'], data_df['Credits'], 'r-', label='Credits')
                ax1.set_ylabel('Credits', color='r')
                ax1.tick_params(axis='y', labelcolor='r')
            
            # Plot Bet and Win on the right y-axis
            if not data_df['Bet'].isna().all():
                ax2.plot(data_df['Frame'], data_df['Bet'], 'b-', label='Bet')
            if not data_df['Win'].isna().all():
                ax2.plot(data_df['Frame'], data_df['Win'], 'g-', label='Win')
            
            if not data_df['Bet'].isna().all() or not data_df['Win'].isna().all():
                ax2.set_ylabel('Bet / Win', color='g')
                ax2.tick_params(axis='y', labelcolor='g')
            
            # Add labels and title
            ax1.set_xlabel('Frame')
            ax1.set_title('Credits, Bet, and Win Over Time')
            ax1.grid(True)
            
            # Create a combined legend
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            
            # Adjust layout and redraw
            self.fig.tight_layout()
            self.canvas.draw()
            
            return f"Graph updated with {len(data_df)} data points."
            
        except Exception as e:
            error_msg = f"Error updating graph: {str(e)}"
            print(error_msg)
            return error_msg
