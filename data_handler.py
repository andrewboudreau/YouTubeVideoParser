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
        valid_entry = True
        try:
            current_credits = float(results[selection_types.CREDITS])
            current_bet = float(results[selection_types.BET])
            current_win = float(results[selection_types.WIN])
            
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
        # Get previous values from CSV if it exists
        previous_credits = None
        previous_bet = None
        previous_win = None
        
        if os.path.exists(self.csv_file):
            try:
                df = pd.read_csv(self.csv_file)
                if not df.empty:
                    last_row = df.iloc[-1]
                    if 'Credits' in last_row and not pd.isna(last_row['Credits']):
                        previous_credits = float(last_row['Credits'])
                    if 'Bet' in last_row and not pd.isna(last_row['Bet']):
                        previous_bet = float(last_row['Bet'])
                    if 'Win' in last_row and not pd.isna(last_row['Win']):
                        previous_win = float(last_row['Win'])
            except Exception as e:
                print(f"Error reading previous values: {e}")
                return True  # If we can't validate, assume it's valid
        
        # If we don't have previous values, we can't validate
        if previous_credits is None or previous_bet is None or previous_win is None:
            return True
        
        # Calculate expected credit change
        expected_decrease = previous_bet
        expected_increase = previous_win
        
        # Calculate actual change
        actual_change = current_credits - previous_credits
        
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
