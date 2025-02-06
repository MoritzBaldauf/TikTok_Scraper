# data_manager.py
import pandas as pd
from datetime import datetime
import os

class DataManager:
    def __init__(self, base_dir="tiktok_data"):
        self.base_dir = base_dir
        self.snapshots_dir = os.path.join(base_dir, "snapshots")
        self.ensure_directories()

    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.base_dir, exist_ok=True)

    def save_account_metrics(self, account_name, metrics):
        """Save account-level metrics with consistent columns"""
        filename = os.path.join(self.base_dir, f"{account_name}_account_metrics.csv")
        
        # Define expected columns in specific order
        expected_columns = [
            'date',
            'scrape_timestamp',
            'account_name',
            'follower_count',
            'total_likes'
        ]
        
        # Create DataFrame with only expected columns in specific order
        df_new = pd.DataFrame([{
            col: metrics.get(col, '') for col in expected_columns
        }])
        
        try:
            if os.path.exists(filename):
                # Try to read existing file
                try:
                    df_existing = pd.read_csv(filename)
                    
                    # If successful read but columns don't match, archive the old file and start fresh
                    if set(df_existing.columns) != set(expected_columns):
                        archive_name = f"{filename}.old"
                        os.rename(filename, archive_name)
                        df_new.to_csv(filename, index=False)
                        print(f"Archived old format CSV to {archive_name}")
                    else:
                        # Ensure columns are in the right order
                        df_existing = df_existing[expected_columns]
                        # Append new data
                        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                        df_combined.to_csv(filename, index=False)
                
                except pd.errors.EmptyDataError:
                    # File exists but is empty, write new data
                    df_new.to_csv(filename, index=False)
                
                except Exception as e:
                    # Any other read error, archive the file and start fresh
                    archive_name = f"{filename}.old"
                    os.rename(filename, archive_name)
                    df_new.to_csv(filename, index=False)
                    print(f"Error reading existing CSV, archived to {archive_name}: {str(e)}")
            
            else:
                # If file doesn't exist, just write the new data
                df_new.to_csv(filename, index=False)
                
        except Exception as e:
            print(f"Error saving account metrics: {str(e)}")
            raise

    def save_video_metrics(self, account_name, videos_data):
        """Save video metrics with change tracking"""
        timestamp = datetime.now()
        snapshot_file = os.path.join(
            self.snapshots_dir, 
            f"{account_name}_videos_{timestamp.strftime('%Y%m%d_%H%M')}.csv"
        )
        
        # Save current snapshot
        df = pd.DataFrame(videos_data)
        df['snapshot_time'] = timestamp
        df.to_csv(snapshot_file, index=False)
        
        # Update main tracking file
        tracking_file = os.path.join(self.base_dir, f"{account_name}_video_tracking.csv")
        if os.path.exists(tracking_file):
            existing_df = pd.read_csv(tracking_file)
            # Compare and update metrics
            for video in videos_data:
                mask = existing_df['video_id'] == video['video_id']
                if mask.any():
                    # Update existing entry
                    existing_df.loc[mask, ['views', 'likes', 'comments', 'shares', 'last_updated']] = [
                        video['views'], video['likes'], video['comments'], 
                        video['shares'], timestamp
                    ]
                else:
                    # Add new entry
                    new_row = pd.DataFrame([{
                        'video_id': video['video_id'],
                        'video_url': video['video_url'],
                        'posting_time': video['posting_time'],
                        'views': video['views'],
                        'likes': video['likes'],
                        'comments': video['comments'],
                        'shares': video['shares'],
                        'description': video['description'],
                        'hashtags': video['hashtags'],
                        'first_seen': timestamp,
                        'last_updated': timestamp
                    }])
                    existing_df = pd.concat([existing_df, new_row], ignore_index=True)
            
            existing_df.to_csv(tracking_file, index=False)
        else:
            # Create new tracking file
            tracking_df = pd.DataFrame(videos_data)
            tracking_df['first_seen'] = timestamp
            tracking_df['last_updated'] = timestamp
            tracking_df.to_csv(tracking_file, index=False)