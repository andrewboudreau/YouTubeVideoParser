import os
import csv
import pandas as pd
from datetime import timedelta
import time

class DataHandler:
    def __init__(self):
        # Create a unique filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.csv_file = f"extracted_data_{timestamp}.csv"
        self.csv_header_written = False
        
        # Store previous values as instance variables
        self.previous_credits = None
        self.previous_bet = None
        self.previous_win = None
    
    def save_to_csv(self, frame_number, timestamp, results, selection_types):
        """Save the extracted text to a CSV file"""
        # Check if we have all three values
        has_credits = selection_types.CREDITS in results
        has_bet = selection_types.BET in results
        has_win = selection_types.WIN in results
        
        # Skip if we don't have all three values
        if not (has_credits and has_bet and has_win):
            print(f"Skipping frame {frame_number} - missing values: Credits={has_credits}, Bet={has_bet}, Win={has_win}")
            return False
            
        # Validate credit changes
        try:
            current_credits = float(results[selection_types.CREDITS])
            current_bet = float(results[selection_types.BET])
            current_win = float(results[selection_types.WIN])
        
            # Update previous values after successful write
            self.previous_credits = current_credits
            self.previous_bet = current_bet
            self.previous_win = current_win

            # Validate with previous values
            if not self.validate_credit_changes(current_credits, current_bet, current_win):
                print(f"Credit validation failed for frame {frame_number} - not saving to CSV")
                return False
                
        except Exception as e:
            print(f"Error in validation: {e}")
        
        # Prepare the data row
        row = {
            'Frame': int(frame_number),
            'Timestamp': str(timestamp),
            'Credits': results.get(selection_types.CREDITS, ''),
            'Bet': results.get(selection_types.BET, ''),
            'Win': results.get(selection_types.WIN, '')
        }
        
        # Check if file exists to determine if we need to write the header
        file_exists = os.path.isfile(self.csv_file)
        
        # Write to CSV
        with open(self.csv_file, 'a', newline='') as csvfile:
            fieldnames = ['Frame', 'Timestamp', 'Credits', 'Bet', 'Win']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            writer.writerow(row)
        
        return True
    
    def validate_credit_changes(self, current_credits, current_bet, current_win):
        """Validate that credit changes follow expected patterns"""
        # If we don't have previous values, we can't validate
        if self.previous_credits is None or self.previous_bet is None or self.previous_win is None:
            return True
        
        # Calculate expected credit change
        expected_decrease = self.previous_bet
        
        # Calculate actual change
        actual_change = current_credits - self.previous_credits
        
        # If credits decreased by more than the previous bet, it's likely an error
        if actual_change < 0 and abs(actual_change) > expected_decrease * 1.1:  # Allow 10% margin for rounding
            print(f"Invalid credit decrease: {actual_change} is more than previous bet {expected_decrease}")
            return False
        
        # Credits can increase by any amount (could be a win or deposit)
        return True
    
    def get_data_for_graph(self):
        """Read the CSV file and return data for graphing"""
        if not os.path.exists(self.csv_file):
            return None
            
        try:
            # Read the CSV file
            df = pd.read_csv(self.csv_file)
            
            if len(df) == 0:
                return None
                
            # Convert string values to numeric where possible
            for col in ['Credits', 'Bet', 'Win']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            return df
        except Exception as e:
            print(f"Error reading data for graph: {e}")
            return None
