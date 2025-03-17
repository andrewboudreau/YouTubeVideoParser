import tkinter as tk
from enum import Enum, auto

class SelectionType(Enum):
    CREDITS = auto()
    WIN = auto()
    BET = auto()

class SelectionManager:
    def __init__(self, canvas):
        self.video_canvas = canvas
        self.current_selection_type = None
        
        # Selection rectangle variables
        self.selection_areas = {
            SelectionType.CREDITS: {"active": False, "rect": None, 
                                   "start_x": 0, "start_y": 0, "current_x": 0, "current_y": 0,
                                   "color": "red", "label": "Credits"},
            SelectionType.WIN: {"active": False, "rect": None, 
                               "start_x": 0, "start_y": 0, "current_x": 0, "current_y": 0,
                               "color": "green", "label": "Win"},
            SelectionType.BET: {"active": False, "rect": None, 
                               "start_x": 0, "start_y": 0, "current_x": 0, "current_y": 0,
                               "color": "blue", "label": "Bet"}
        }
        
        # Scale factors for coordinate conversion
        self.scale_factor_x = 1.0
        self.scale_factor_y = 1.0
    
    def set_scale_factors(self, scale_x, scale_y):
        """Set scale factors for coordinate conversion"""
        self.scale_factor_x = scale_x
        self.scale_factor_y = scale_y
    
    def set_current_type(self, selection_str):
        """Set the current selection type based on string value"""
        if selection_str == "CREDITS":
            self.current_selection_type = SelectionType.CREDITS
        elif selection_str == "WIN":
            self.current_selection_type = SelectionType.WIN
        elif selection_str == "BET":
            self.current_selection_type = SelectionType.BET
    
    def on_mouse_down(self, event):
        """Handle mouse down event for selection creation"""
        if not self.current_selection_type:
            return
            
        # Clear existing selection of current type and create a new one
        self.clear_selection(self.current_selection_type)
        
        # Start a new selection for current type
        sel_data = self.selection_areas[self.current_selection_type]
        sel_data["active"] = True
        sel_data["start_x"] = event.x
        sel_data["start_y"] = event.y
        sel_data["current_x"] = event.x
        sel_data["current_y"] = event.y
        self.draw_selection_rectangle(self.current_selection_type)
    
    def on_mouse_drag(self, event):
        """Handle mouse drag event for selection resizing"""
        if not self.current_selection_type:
            return
            
        sel_data = self.selection_areas[self.current_selection_type]
        if not sel_data["active"]:
            return
            
        # Update the current position for drawing
        sel_data["current_x"] = max(0, min(event.x, self.video_canvas.winfo_width()))
        sel_data["current_y"] = max(0, min(event.y, self.video_canvas.winfo_height()))
            
        self.draw_selection_rectangle(self.current_selection_type)
    
    def on_mouse_up(self, event):
        """Handle mouse up event for selection completion"""
        if not self.current_selection_type:
            return
            
        sel_data = self.selection_areas[self.current_selection_type]
        # Ensure the rectangle has some minimum size
        if abs(sel_data["current_x"] - sel_data["start_x"]) < 10 or abs(sel_data["current_y"] - sel_data["start_y"]) < 10:
            self.clear_selection(self.current_selection_type)
    
    def draw_selection_rectangle(self, selection_type):
        """Draw a selection rectangle on the canvas"""
        sel_data = self.selection_areas[selection_type]
        
        # Delete existing rectangle and all associated elements
        self.video_canvas.delete(f"selection_{selection_type.name}")
            
        # Draw new rectangle
        x1 = min(sel_data["start_x"], sel_data["current_x"])
        y1 = min(sel_data["start_y"], sel_data["current_y"])
        x2 = max(sel_data["start_x"], sel_data["current_x"])
        y2 = max(sel_data["start_y"], sel_data["current_y"])
        
        # Create rectangle with a tag for easy deletion
        sel_data["rect"] = self.video_canvas.create_rectangle(
            x1, y1, x2, y2, 
            outline=sel_data["color"], 
            width=2,
            dash=(5, 5),
            tags=f"selection_{selection_type.name}"
        )
        
        # Add label to the top-left corner with the same tag
        self.video_canvas.create_text(
            x1 + 5, y1 + 5,
            text=sel_data["label"],
            fill=sel_data["color"],
            anchor=tk.NW,
            font=("Arial", 8, "bold"),
            tags=f"selection_{selection_type.name}"
        )
    
    def clear_selection(self, selection_type):
        """Clear a specific selection rectangle"""
        sel_data = self.selection_areas[selection_type]
        sel_data["active"] = False
        
        # Delete all canvas elements with this selection's tag
        self.video_canvas.delete(f"selection_{selection_type.name}")
        sel_data["rect"] = None
    
    def clear_all_selections(self):
        """Clear all selection rectangles"""
        for sel_type in self.selection_areas:
            self.clear_selection(sel_type)
    
    def redraw_all_selections(self):
        """Redraw all active selection rectangles"""
        for sel_type, sel_data in self.selection_areas.items():
            if sel_data["active"]:
                self.draw_selection_rectangle(sel_type)
    
    def nudge_selection(self, direction):
        """Nudge the current selection in the specified direction by 5 pixels"""
        if not self.current_selection_type:
            return None
            
        sel_data = self.selection_areas[self.current_selection_type]
        if not sel_data["active"]:
            return f"No active {sel_data['label']} selection to nudge"
            
        # Amount to nudge in pixels
        nudge_amount = 5
        
        # Update coordinates based on direction
        if direction == "left":
            sel_data["start_x"] -= nudge_amount
            sel_data["current_x"] -= nudge_amount
            status_msg = f"Nudged {sel_data['label']} selection left by {nudge_amount} pixels"
        elif direction == "right":
            sel_data["start_x"] += nudge_amount
            sel_data["current_x"] += nudge_amount
            status_msg = f"Nudged {sel_data['label']} selection right by {nudge_amount} pixels"
        elif direction == "up":
            sel_data["start_y"] -= nudge_amount
            sel_data["current_y"] -= nudge_amount
            status_msg = f"Nudged {sel_data['label']} selection up by {nudge_amount} pixels"
        elif direction == "down":
            sel_data["start_y"] += nudge_amount
            sel_data["current_y"] += nudge_amount
            status_msg = f"Nudged {sel_data['label']} selection down by {nudge_amount} pixels"
        else:
            return "Invalid direction"
        
        # Ensure coordinates stay within canvas bounds
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        sel_data["start_x"] = max(0, min(sel_data["start_x"], canvas_width))
        sel_data["start_y"] = max(0, min(sel_data["start_y"], canvas_height))
        sel_data["current_x"] = max(0, min(sel_data["current_x"], canvas_width))
        sel_data["current_y"] = max(0, min(sel_data["current_y"], canvas_height))
        
        # Redraw the selection rectangle
        self.draw_selection_rectangle(self.current_selection_type)
        
        return status_msg
    
    def get_selection_coordinates(self, selection_type):
        """Get the coordinates of a selection in original image coordinates"""
        sel_data = self.selection_areas[selection_type]
        if not sel_data["active"]:
            return None
            
        # Get selection coordinates
        x1 = min(sel_data["start_x"], sel_data["current_x"])
        y1 = min(sel_data["start_y"], sel_data["current_y"])
        x2 = max(sel_data["start_x"], sel_data["current_x"])
        y2 = max(sel_data["start_y"], sel_data["current_y"])
        
        # Convert to original image coordinates
        orig_x1 = int(x1 * self.scale_factor_x)
        orig_y1 = int(y1 * self.scale_factor_y)
        orig_x2 = int(x2 * self.scale_factor_x)
        orig_y2 = int(y2 * self.scale_factor_y)
        
        return (orig_x1, orig_y1, orig_x2, orig_y2)
    
    def get_active_selections(self):
        """Get a list of active selection types"""
        return [sel_type for sel_type, sel_data in self.selection_areas.items() if sel_data["active"]]
