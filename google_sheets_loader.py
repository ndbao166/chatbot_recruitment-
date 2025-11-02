"""Google Sheets Data Loader for Recruitment Chatbot"""
import os
import logging
from typing import Optional, List, Dict, Any
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)


class GoogleSheetsLoader:
    """Load data from Google Sheets"""
    
    def __init__(
        self,
        credentials_file: Optional[str] = None,
        spreadsheet_id: Optional[str] = None,
        knowledge_sheet_name: Optional[str] = None,
        job_sheet_name: Optional[str] = None,
        user_info_sheet_name: Optional[str] = None,
    ):
        """
        Initialize Google Sheets Loader.
        
        Args:
            credentials_file: Path to Google Sheets credentials JSON file
            spreadsheet_id: ID của file Google Sheets (chỉ cần 1 file)
            knowledge_sheet_name: Tên tab/sheet chứa knowledge (default: "Knowledge")
            job_sheet_name: Tên tab/sheet chứa jobs (default: "Jobs")
            user_info_sheet_name: Tên tab/sheet chứa user info (default: "UserInfo")
        """
        self.credentials_file = credentials_file or os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
        self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        self.knowledge_sheet_name = knowledge_sheet_name or os.getenv("KNOWLEDGE_BASE_SHEET_ID", "Knowledge")
        self.job_sheet_name = job_sheet_name or os.getenv("JOB_SHEET_ID", "Jobs")
        self.user_info_sheet_name = user_info_sheet_name or os.getenv("INFO_SHEET_ID", "UserInfo")
        
        logger.info("[GOOGLE SHEETS LOADER] Initialized with:")
        logger.info("[GOOGLE SHEETS LOADER]   - Credentials file: %s", self.credentials_file)
        logger.info("[GOOGLE SHEETS LOADER]   - Spreadsheet ID: %s", self.spreadsheet_id)
        logger.info("[GOOGLE SHEETS LOADER]   - Knowledge Sheet: %s", self.knowledge_sheet_name)
        logger.info("[GOOGLE SHEETS LOADER]   - Job Sheet: %s", self.job_sheet_name)
        logger.info("[GOOGLE SHEETS LOADER]   - User Info Sheet: %s", self.user_info_sheet_name)
        
        self._client = None
    
    def _get_credentials_from_env(self):
        """Build credentials dict from environment variables"""
        return {
            "type": os.getenv("GOOGLE_SHEETS_CREDENTIALS_TYPE"),
            "project_id": os.getenv("GOOGLE_SHEETS_CREDENTIALS_PROJECT_ID"),
            "private_key_id": os.getenv("GOOGLE_SHEETS_CREDENTIALS_PRIVATE_KEY_ID"),
            "private_key": os.getenv("GOOGLE_SHEETS_CREDENTIALS_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.getenv("GOOGLE_SHEETS_CREDENTIALS_CLIENT_EMAIL"),
            "client_id": os.getenv("GOOGLE_SHEETS_CREDENTIALS_CLIENT_ID"),
            "auth_uri": os.getenv("GOOGLE_SHEETS_CREDENTIALS_AUTH_URI"),
            "token_uri": os.getenv("GOOGLE_SHEETS_CREDENTIALS_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("GOOGLE_SHEETS_CREDENTIALS_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("GOOGLE_SHEETS_CREDENTIALS_CLIENT_X509_CERT_URL"),
            "universe_domain": os.getenv("GOOGLE_SHEETS_CREDENTIALS_UNIVERSE_DOMAIN", "googleapis.com")
        }
    
    def _get_client(self):
        """Get or create Google Sheets client"""
        if self._client is None:
            try:
                logger.info("[GOOGLE SHEETS LOADER] Initializing Google Sheets client...")
                
                scope = [
                    'https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive'
                ]
                
                # Try to use credentials from environment variables first
                creds_dict = self._get_credentials_from_env()
                if creds_dict.get("client_email") and creds_dict.get("private_key"):
                    logger.info("[GOOGLE SHEETS LOADER] Using credentials from environment variables")
                    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
                    self._client = gspread.authorize(creds)
                    logger.info("[GOOGLE SHEETS LOADER] Google Sheets client initialized successfully with env vars")
                # Fallback to JSON file if environment variables not set
                elif self.credentials_file and os.path.exists(self.credentials_file):
                    logger.info("[GOOGLE SHEETS LOADER] Using credentials from JSON file: %s", self.credentials_file)
                    creds = Credentials.from_service_account_file(self.credentials_file, scopes=scope)
                    self._client = gspread.authorize(creds)
                    logger.info("[GOOGLE SHEETS LOADER] Google Sheets client initialized successfully with JSON file")
                else:
                    logger.error("[GOOGLE SHEETS LOADER] No valid credentials found (neither env vars nor JSON file)")
                    raise ValueError("No valid Google Sheets credentials found")
                    
            except Exception as e:
                logger.error("[GOOGLE SHEETS LOADER] Error initializing client: %s", e, exc_info=True)
                raise
        
        return self._client
    
    def load_knowledge_data(self, sheet_name: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Load recruitment knowledge data from Google Sheets.
        
        Args:
            sheet_name: Tên tab/sheet (default: dùng giá trị từ __init__)
        
        Returns:
            DataFrame with columns: Question, Answer, Category
            Returns None if loading fails
        """
        try:
            if not self.spreadsheet_id:
                logger.warning("[GOOGLE SHEETS LOADER] Spreadsheet ID not configured")
                return None
            
            sheet_name = sheet_name or self.knowledge_sheet_name
            
            logger.info("[GOOGLE SHEETS LOADER] Loading knowledge data from spreadsheet: %s, sheet: %s", 
                       self.spreadsheet_id, sheet_name)
            
            client = self._get_client()
            spreadsheet = client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Get all records as list of dictionaries
            records = worksheet.get_all_records()
            
            if not records:
                logger.warning("[GOOGLE SHEETS LOADER] No data found in knowledge spreadsheet")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # Validate required columns
            required_columns = ['Question', 'Answer', 'Category']
            if not all(col in df.columns for col in required_columns):
                logger.error("[GOOGLE SHEETS LOADER] Missing required columns. Expected: %s, Got: %s", 
                           required_columns, df.columns.tolist())
                return None
            
            logger.info("[GOOGLE SHEETS LOADER] Successfully loaded %d knowledge records", len(df))
            return df
            
        except Exception as e:
            logger.error("[GOOGLE SHEETS LOADER] Error loading knowledge data: %s", e, exc_info=True)
            return None
    
    def load_jobs_data(self, sheet_name: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Load job listings from Google Sheets.
        
        Args:
            sheet_name: Tên tab/sheet (default: dùng giá trị từ __init__)
        
        Returns:
            List of job dictionaries with structure matching jobs.json format
            Returns None if loading fails
        """
        try:
            if not self.spreadsheet_id:
                logger.warning("[GOOGLE SHEETS LOADER] Spreadsheet ID not configured")
                return None
            
            sheet_name = sheet_name or self.job_sheet_name
            
            logger.info("[GOOGLE SHEETS LOADER] Loading jobs data from spreadsheet: %s, sheet: %s", 
                       self.spreadsheet_id, sheet_name)
            
            client = self._get_client()
            spreadsheet = client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Get all records
            records = worksheet.get_all_records()
            
            if not records:
                logger.warning("[GOOGLE SHEETS LOADER] No data found in jobs spreadsheet")
                return None
            
            # Convert to job format
            jobs = []
            for record in records:
                job = {
                    "id": record.get("id", ""),
                    "title": record.get("title", ""),
                    "location": record.get("location", ""),
                    "type": record.get("type", ""),
                    "salary": record.get("salary", ""),
                    "description": record.get("description", ""),
                    "skills": self._parse_list_field(record.get("skills", "")),
                    "requirements": self._parse_list_field(record.get("requirements", "")),
                    "benefits": self._parse_list_field(record.get("benefits", "")),
                    "contact": record.get("contact", "")
                }
                jobs.append(job)
            
            logger.info("[GOOGLE SHEETS LOADER] Successfully loaded %d job listings", len(jobs))
            return jobs
            
        except Exception as e:
            logger.error("[GOOGLE SHEETS LOADER] Error loading jobs data: %s", e, exc_info=True)
            return None
    
    def _parse_list_field(self, field_value: str) -> List[str]:
        """
        Parse comma-separated or newline-separated string into list.
        
        Args:
            field_value: String value to parse
        
        Returns:
            List of strings
        """
        if not field_value:
            return []
        
        # Try comma separation first
        if "," in field_value:
            items = [item.strip() for item in field_value.split(",")]
        # Try newline separation
        elif "\n" in field_value:
            items = [item.strip() for item in field_value.split("\n")]
        # Single item
        else:
            items = [field_value.strip()]
        
        # Filter out empty strings
        return [item for item in items if item]
    
    def save_knowledge_to_csv(self, output_file: str = "data/recruitment_knowledge.csv") -> bool:
        """
        Load knowledge from Google Sheets and save to CSV file (for backup/cache).
        
        Args:
            output_file: Path to output CSV file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            df = self.load_knowledge_data()
            if df is None:
                return False
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Save to CSV
            df.to_csv(output_file, index=False, encoding='utf-8')
            logger.info("[GOOGLE SHEETS LOADER] Saved knowledge data to: %s", output_file)
            return True
            
        except Exception as e:
            logger.error("[GOOGLE SHEETS LOADER] Error saving knowledge to CSV: %s", e, exc_info=True)
            return False
    
    def save_jobs_to_json(self, output_file: str = "data/jobs.json") -> bool:
        """
        Load jobs from Google Sheets and save to JSON file (for backup/cache).
        
        Args:
            output_file: Path to output JSON file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            
            jobs = self.load_jobs_data()
            if jobs is None:
                return False
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Save to JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({"jobs": jobs}, f, ensure_ascii=False, indent=2)
            
            logger.info("[GOOGLE SHEETS LOADER] Saved jobs data to: %s", output_file)
            return True
            
        except Exception as e:
            logger.error("[GOOGLE SHEETS LOADER] Error saving jobs to JSON: %s", e, exc_info=True)
            return False


def create_google_sheets_loader(**kwargs) -> GoogleSheetsLoader:
    """
    Factory function to create a GoogleSheetsLoader.
    
    Args:
        **kwargs: Arguments to pass to GoogleSheetsLoader constructor
    
    Returns:
        GoogleSheetsLoader instance
    """
    return GoogleSheetsLoader(**kwargs)

