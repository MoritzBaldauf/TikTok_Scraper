# data_manager.py
import pandas as pd
from datetime import datetime
import os
import logging

class DataManager:
    def __init__(self, base_dir="tiktok_data"):
        self.base_dir = base_dir
        self.snapshots_dir = os.path.join(base_dir, "snapshots")
        self.ensure_directories()

    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.base_dir, exist_ok=True)

    def save_video_metrics(self, account_name, videos_data):
        """Save video metrics with consistent column ordering"""
        if not videos_data:
            logging.warning(f"No video data provided for {account_name}")
            return
            
        timestamp = datetime.now()
        
        # Define expected columns in specific order
        expected_columns = [
            'date',
            'video_id',
            'video_url',
            'posting_time',
            'views',
            'likes',
            'comments',
            'shares',
            'description',
            'hashtags',
            'is_new',
            'is_pinned',
            'scrape_timestamp',
            'first_seen',
            'last_updated'
        ]
        
        # Create directory paths
        snapshots_dir = os.path.join(self.snapshots_dir, account_name)
        os.makedirs(snapshots_dir, exist_ok=True)
        
        # Define file paths
        snapshot_file = os.path.join(
            snapshots_dir, 
            f"videos_{timestamp.strftime('%Y%m%d_%H%M')}.csv"
        )
        tracking_file = os.path.join(self.base_dir, f"{account_name}_video_tracking.csv")
        
        try:
            # Save current snapshot with ordered columns
            df = pd.DataFrame(videos_data)
            df['scrape_timestamp'] = timestamp
            # Add date column based on posting_time
            df['date'] = pd.to_datetime(df['posting_time']).dt.strftime('%Y-%m-%d')
            
            # Ensure all expected columns exist
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = None
                    
            # Reorder columns
            df = df[expected_columns]
            df.to_csv(snapshot_file, index=False)
            logging.info(f"Saved snapshot to {snapshot_file}")
            
            # Update tracking file
            if os.path.exists(tracking_file):
                try:
                    existing_df = pd.read_csv(tracking_file)
                    if len(existing_df) == 0:
                        self._create_new_tracking_file(tracking_file, df, timestamp)
                    else:
                        self._update_existing_tracking_file(existing_df, df, timestamp, tracking_file, expected_columns)
                except pd.errors.EmptyDataError:
                    self._create_new_tracking_file(tracking_file, df, timestamp)
                except Exception as e:
                    backup_file = f"{tracking_file}.backup_{timestamp.strftime('%Y%m%d_%H%M')}"
                    logging.warning(f"Error reading tracking file, creating backup at {backup_file}")
                    if os.path.exists(tracking_file):
                        os.rename(tracking_file, backup_file)
                    self._create_new_tracking_file(tracking_file, df, timestamp)
            else:
                self._create_new_tracking_file(tracking_file, df, timestamp)
                
        except Exception as e:
            logging.error(f"Error saving video metrics for {account_name}: {str(e)}")
            raise
        
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
                        logging.info(f"Archived old format CSV to {archive_name}")
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
                    logging.error(f"Error reading existing CSV, archived to {archive_name}: {str(e)}")
            
            else:
                # If file doesn't exist, just write the new data
                df_new.to_csv(filename, index=False)
                
        except Exception as e:
            logging.error(f"Error saving account metrics: {str(e)}")
            raise
    
    def _create_new_tracking_file(self, tracking_file, df, timestamp):
        """Create a new video tracking file with ordered columns"""
        # Ensure timestamp columns are set
        df['first_seen'] = timestamp
        df['last_updated'] = timestamp
        df.to_csv(tracking_file, index=False)
        logging.info(f"Created new tracking file: {tracking_file}")

    def _update_existing_tracking_file(self, existing_df, new_df, timestamp, tracking_file, expected_columns):
        """Update existing tracking file with new video data, maintaining column order"""
        # Ensure existing DataFrame has all expected columns
        for col in expected_columns:
            if col not in existing_df.columns:
                existing_df[col] = None
        
        # Update existing entries and add new ones
        for _, new_row in new_df.iterrows():
            mask = existing_df['video_id'] == new_row['video_id']
            if mask.any():
                # Update existing entry
                update_cols = ['views', 'likes', 'comments', 'shares', 'last_updated']
                existing_df.loc[mask, update_cols] = [
                    new_row['views'], 
                    new_row['likes'], 
                    new_row['comments'], 
                    new_row['shares'],
                    timestamp
                ]
            else:
                # Add new entry
                new_row['first_seen'] = timestamp
                new_row['last_updated'] = timestamp
                existing_df = pd.concat([existing_df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Ensure columns are in correct order
        existing_df = existing_df[expected_columns]
        
        # Save updated tracking file
        existing_df.to_csv(tracking_file, index=False)
        logging.info(f"Updated tracking file with {len(new_df)} videos")
