"""
Google Sheets Integration Service
Used to sync board game catalog data with Google Sheets
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings
import json
from datetime import datetime


class GoogleSheetsService:
    """Service to sync data with Google Sheets"""
    
    def __init__(self):
        self.client = None
        self.sheet = None
        self.worksheet = None
    
    def authenticate(self, credentials_file=None):
        """
        Authenticate with Google Sheets API using service account
        
        Args:
            credentials_file (str): Path to service account JSON file
        """
        try:
            if not credentials_file:
                credentials_file = settings.GOOGLE_SHEETS_CREDENTIALS_FILE
            
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
            self.client = gspread.authorize(creds)
            return True
        
        except Exception as e:
            print(f"Error authenticating with Google Sheets: {e}")
            return False
    
    def get_or_create_spreadsheet(self, sheet_name=None):
        """
        Get existing spreadsheet or create a new one
        
        Args:
            sheet_name (str): Name of the spreadsheet
        """
        try:
            if not sheet_name:
                sheet_name = settings.GOOGLE_SHEETS_NAME
            
            # Try to open existing spreadsheet
            try:
                self.sheet = self.client.open(sheet_name)
            except gspread.SpreadsheetNotFound:
                # Create new spreadsheet
                self.sheet = self.client.create(sheet_name)
                # Share with your email (optional)
                if hasattr(settings, 'GOOGLE_SHEETS_SHARE_EMAIL'):
                    self.sheet.share(settings.GOOGLE_SHEETS_SHARE_EMAIL, perm_type='user', role='writer')
            
            # Get or create first worksheet
            try:
                self.worksheet = self.sheet.get_worksheet(0)
            except:
                self.worksheet = self.sheet.add_worksheet(title="Board Games", rows=1000, cols=20)
            
            # Setup headers if empty
            if not self.worksheet.row_values(1):
                self._setup_headers()
            
            return True
        
        except Exception as e:
            print(f"Error accessing spreadsheet: {e}")
            return False
    
    def _setup_headers(self):
        """Setup column headers in the spreadsheet"""
        headers = [
            'ID',
            'BGG ID',
            'Name',
            'Year Published',
            'Designer',
            'Min Players',
            'Max Players',
            'Min Playtime',
            'Max Playtime',
            'Min Age',
            'Condition',
            'MSRP Price',
            'Discount %',
            'Final Price',
            'Stock Quantity',
            'Is Sold',
            'Sold Date',
            'Thumbnail URL',
            'Description',
            'Notes',
            'Created At',
            'Updated At',
        ]
        self.worksheet.update('A1:V1', [headers])
        # Format header row
        self.worksheet.format('A1:V1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}
        })
    
    def sync_game_to_sheet(self, game):
        """
        Sync a single board game to Google Sheets
        
        Args:
            game: BoardGame model instance
        """
        try:
            row_data = [
                game.id,
                game.bgg_id or '',
                game.name,
                game.year_published or '',
                game.designer or '',
                game.min_players or '',
                game.max_players or '',
                game.min_playtime or '',
                game.max_playtime or '',
                game.min_age or '',
                game.get_condition_display(),
                float(game.msrp_price) if game.msrp_price else '',
                float(game.discount_percentage) if game.discount_percentage else '',
                float(game.final_price) if game.final_price else '',
                game.stock_quantity,
                'Yes' if game.is_sold else 'No',
                game.sold_date.strftime('%Y-%m-%d %H:%M') if game.sold_date else '',
                game.thumbnail_url or '',
                game.description[:500] if game.description else '',  # Truncate long descriptions
                game.notes or '',
                game.created_at.strftime('%Y-%m-%d %H:%M'),
                game.updated_at.strftime('%Y-%m-%d %H:%M'),
            ]
            
            # Find row by ID
            try:
                cell = self.worksheet.find(str(game.id), in_column=1)
                row_number = cell.row
                # Update existing row
                self.worksheet.update(f'A{row_number}:V{row_number}', [row_data])
            except gspread.CellNotFound:
                # Append new row
                self.worksheet.append_row(row_data)
            
            return True
        
        except Exception as e:
            print(f"Error syncing game to sheet: {e}")
            return False
    
    def sync_all_games(self, games):
        """
        Sync all board games to Google Sheets
        
        Args:
            games: QuerySet of BoardGame instances
        """
        try:
            # Clear existing data (keep headers)
            if self.worksheet.row_count > 1:
                self.worksheet.delete_rows(2, self.worksheet.row_count)
            
            # Prepare all rows
            rows_data = []
            for game in games:
                row_data = [
                    game.id,
                    game.bgg_id or '',
                    game.name,
                    game.year_published or '',
                    game.designer or '',
                    game.min_players or '',
                    game.max_players or '',
                    game.min_playtime or '',
                    game.max_playtime or '',
                    game.min_age or '',
                    game.get_condition_display(),
                    float(game.msrp_price) if game.msrp_price else '',
                    float(game.discount_percentage) if game.discount_percentage else '',
                    float(game.final_price) if game.final_price else '',
                    game.stock_quantity,
                    'Yes' if game.is_sold else 'No',
                    game.sold_date.strftime('%Y-%m-%d %H:%M') if game.sold_date else '',
                    game.thumbnail_url or '',
                    game.description[:500] if game.description else '',
                    game.notes or '',
                    game.created_at.strftime('%Y-%m-%d %H:%M'),
                    game.updated_at.strftime('%Y-%m-%d %H:%M'),
                ]
                rows_data.append(row_data)
            
            # Batch update
            if rows_data:
                self.worksheet.update(f'A2:V{len(rows_data) + 1}', rows_data)
            
            return True
        
        except Exception as e:
            print(f"Error syncing all games to sheet: {e}")
            return False
    
    def delete_game_from_sheet(self, game_id):
        """
        Delete a game from Google Sheets by ID
        
        Args:
            game_id (int): BoardGame ID
        """
        try:
            cell = self.worksheet.find(str(game_id), in_column=1)
            self.worksheet.delete_rows(cell.row)
            return True
        except gspread.CellNotFound:
            return True  # Already deleted
        except Exception as e:
            print(f"Error deleting game from sheet: {e}")
            return False
