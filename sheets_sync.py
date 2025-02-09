# sheets_sync.py
import pandas as pd
import numpy as np
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
import glob
import os

class SheetsSync:
    def __init__(self, credentials_file, spreadsheet_id):
        try:
            self.spreadsheet_id = spreadsheet_id
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=self.credentials)
            self.sheets = self.service.spreadsheets()
            logging.info("Successfully initialized Google Sheets connection")
        except Exception as e:
            logging.error(f"Failed to initialize Google Sheets connection: {str(e)}")
            raise

    def ensure_sheet_exists(self, sheet_name):
        """Ensure the specified sheet exists, create if it doesn't"""
        try:
            sheet_metadata = self.sheets.get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = sheet_metadata.get('sheets', '')
            sheet_exists = any(s['properties']['title'] == sheet_name for s in sheets)
            
            if not sheet_exists:
                request = {
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }
                self.sheets.batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': [request]}
                ).execute()
                logging.info(f"Created new sheet: {sheet_name}")
                
        except Exception as e:
            logging.error(f"Error checking/creating sheet: {str(e)}")
            raise

    def clean_data_for_sheets(self, df):
        """Clean DataFrame to ensure compatibility with Google Sheets"""
        # Create a copy to avoid modifying the original
        df_clean = df.copy()

        # Format timestamps consistently
        timestamp_columns = ['scrape_timestamp', 'posting_time', 'first_seen', 'last_updated']
        for col in timestamp_columns:
            if col in df_clean.columns:
                try:
                    # Handle various timestamp formats
                    df_clean[col] = pd.to_datetime(df_clean[col]).apply(
                        lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(x) else ''
                    )
                except Exception as e:
                    logging.warning(f"Error formatting {col}: {str(e)}")
                    # If conversion fails, try cleaning the data first
                    df_clean[col] = df_clean[col].astype(str).apply(
                        lambda x: x.split('.')[0] if '.' in x else x
                    )

        # Format URLs as hyperlinks
        if 'video_url' in df_clean.columns:
            df_clean['video_url'] = df_clean['video_url'].apply(
                lambda x: f'=HYPERLINK("{x}")' if pd.notnull(x) else ''
            )
        
        # Replace NaN values with empty string
        df_clean = df_clean.replace({np.nan: '', 'NaN': '', 'nan': ''})
        
        # Convert boolean values to strings
        df_clean = df_clean.replace({True: 'TRUE', False: 'FALSE'})
        
        # Convert all values to strings and strip problematic characters
        for column in df_clean.columns:
            df_clean[column] = df_clean[column].astype(str).apply(
                lambda x: x.strip() if isinstance(x, str) else x
            )
        
        # Remove any null bytes or other problematic characters
        for column in df_clean.columns:
            df_clean[column] = df_clean[column].replace({
                r'\x00': '',
                r'\n': ' ',
                r'\r': ' '
            }, regex=True)
        
        return df_clean

    def dataframe_to_sheets_values(self, df):
        """Convert DataFrame to format suitable for Google Sheets"""
        # Clean the data first
        df_clean = self.clean_data_for_sheets(df)
        
        # Convert to list of lists format that Sheets API expects
        headers = df_clean.columns.tolist()
        values = df_clean.values.tolist()
        
        # Ensure all values are strings
        values = [[str(cell) for cell in row] for row in values]
        
        return [headers] + values

    def update_video_metrics(self, account_name, csv_file):
        """Sync video metrics to Google Sheets with improved timestamp handling"""
        sheet_name = f'{account_name}_videos'
        
        try:
            # Ensure sheet exists
            self.ensure_sheet_exists(sheet_name)
            
            # Read CSV data
            df = pd.read_csv(csv_file)
            
            # Clean timestamps before processing
            timestamp_columns = ['scrape_timestamp', 'posting_time', 'first_seen', 'last_updated']
            for col in timestamp_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).apply(
                        lambda x: x.split('.')[0] if '.' in x else x
                    )
            
            # Convert data to sheets format
            values = self.dataframe_to_sheets_values(df)
            
            # Update sheet
            range_name = f'{sheet_name}!A1'
            body = {'values': values}
            
            # Clear existing content
            self.sheets.values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            # Update with new content
            self.sheets.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logging.info(f"Successfully updated video metrics for {account_name}")
            
        except Exception as e:
            logging.error(f"Error updating video metrics: {str(e)}")
            raise
        
    def update_all_account_metrics(self, data_dir):
        """Sync all account metrics to a single sheet"""
        sheet_name = 'account_metrics'
        
        try:
            # Ensure sheet exists
            self.ensure_sheet_exists(sheet_name)
            
            # Find all account metric CSV files
            all_metrics_files = glob.glob(os.path.join(data_dir, "*_account_metrics.csv"))
            
            if not all_metrics_files:
                logging.warning("No account metrics files found")
                return
            
            # Combine all CSV files into a single DataFrame
            all_metrics = []
            for file in all_metrics_files:
                try:
                    df = pd.read_csv(file)
                    all_metrics.append(df)
                except Exception as e:
                    logging.error(f"Error reading file {file}: {str(e)}")
                    continue
            
            if not all_metrics:
                logging.warning("No valid metrics data found")
                return
            
            # Combine all metrics
            combined_df = pd.concat(all_metrics, ignore_index=True)
            
            # Sort by timestamp and account name
            combined_df['scrape_timestamp'] = pd.to_datetime(combined_df['scrape_timestamp'])
            combined_df = combined_df.sort_values(['scrape_timestamp', 'account_name'], ascending=[False, True])
            
            # Convert data to sheets format
            values = self.dataframe_to_sheets_values(combined_df)
            
            # Update sheet
            range_name = f'{sheet_name}!A1'
            body = {'values': values}
            
            # Clear existing content
            self.sheets.values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            # Update with new content
            self.sheets.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logging.info("Successfully updated combined account metrics")
            
        except Exception as e:
            logging.error(f"Error updating combined account metrics: {str(e)}")
            raise