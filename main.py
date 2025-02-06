# main.py
from tiktok_scraper import TikTokScraper
from data_manager import DataManager
from sheets_sync import SheetsSync
from config import *
import logging
import time
from datetime import datetime, timedelta
import os
import sys
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(DATA_DIR, 'scraper.log'))
    ]
)

def setup_directories():
    """Ensure all necessary directories exist"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        logging.info(f"Ensured data directory exists at {DATA_DIR}")
    except Exception as e:
        logging.error(f"Failed to create directories: {str(e)}")
        raise

def validate_config():
    """Validate necessary configuration values"""
    required_configs = {
        'DATA_DIR': DATA_DIR,
        'ACCOUNT_METRICS_FILE': ACCOUNT_METRICS_FILE,
        'VIDEO_METRICS_FILE': VIDEO_METRICS_FILE,
        'DEFAULT_TIMEOUT': DEFAULT_TIMEOUT,
        'NEW_VIDEO_THRESHOLD': NEW_VIDEO_THRESHOLD
    }
    
    missing_configs = [k for k, v in required_configs.items() if not v]
    if missing_configs:
        raise ValueError(f"Missing required configuration values: {', '.join(missing_configs)}")

def run_scraper():
    """Execute one complete scraping run"""
    logging.info("Starting scraping process")
    
    # Initialize managers
    data_manager = DataManager(base_dir=DATA_DIR)
    try:
        sheets_sync = SheetsSync(SHEETS_CREDS, SPREADSHEET_ID)
    except Exception as e:
        logging.error(f"Failed to initialize Google Sheets sync: {str(e)}")
        raise
    
    for account in ACCOUNTS:
        scraper = None
        try:
            logging.info(f"Processing account: {account}")
            
            # Initialize and run scraper
            scraper = TikTokScraper(account)
            scraper.start_browser()
            
            # Get metrics
            account_metrics = scraper.scrape_account_metrics()
            if not account_metrics:
                logging.error(f"Failed to get account metrics for {account}")
                continue
                
            videos_data = scraper.scrape_recent_videos()
            if not videos_data:
                logging.warning(f"No videos found for {account}")
            
            # Save locally
            data_manager.save_account_metrics(account, account_metrics)
            if videos_data:
                data_manager.save_video_metrics(account, videos_data)
            
            # Sync to Google Sheets
            try:
                video_tracking_file = os.path.join(DATA_DIR, f"{account}_video_tracking.csv")
                if os.path.exists(video_tracking_file):
                    sheets_sync.update_video_metrics(account, video_tracking_file)
                    logging.info(f"Successfully synced video metrics for {account}")
                else:
                    logging.warning(f"No video tracking file found for {account}")
                    
            except Exception as e:
                logging.error(f"Failed to sync video metrics for {account}: {str(e)}")
            
            # Add delay between accounts
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            
        except Exception as e:
            logging.error(f"Error processing account {account}: {str(e)}")
        finally:
            if scraper:
                try:
                    scraper.cleanup()
                except Exception as e:
                    logging.error(f"Error during scraper cleanup for {account}: {str(e)}")
    
    try:
        # Update combined metrics
        sheets_sync.update_all_account_metrics(DATA_DIR)
        logging.info("Successfully updated combined account metrics")
    except Exception as e:
        logging.error(f"Failed to update combined account metrics: {str(e)}")

def main():
    """Main execution loop"""
    logging.info("TikTok Scraper service starting")
    
    try:
        # Initial setup
        setup_directories()
        validate_config()
        
        # Main loop
        while True:
            try:
                start_time = datetime.now()
                logging.info(f"Starting scraping run at {start_time}")
                
                # Run the scraper
                run_scraper()
                
                # Calculate next run time
                end_time = datetime.now()
                run_duration = (end_time - start_time).total_seconds()
                logging.info(f"Scraping run completed in {run_duration:.2f} seconds")
                
                next_run = start_time + timedelta(hours=INTERVAL_HOURS)
                sleep_seconds = max(0, (next_run - datetime.now()).total_seconds())
                
                logging.info(f"Next run scheduled for: {next_run}")
                time.sleep(sleep_seconds)
                
            except KeyboardInterrupt:
                logging.info("Received shutdown signal, exiting...")
                break
            except Exception as e:
                logging.error(f"Error in main loop: {str(e)}")
                # Sleep for 5 minutes before retrying in case of error
                time.sleep(300)
    
    except Exception as e:
        logging.error(f"Fatal error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()