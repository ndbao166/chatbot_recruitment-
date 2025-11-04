"""Custom tools for Recruitment Chatbot"""
import os
import json
import logging
from typing import Optional
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import requests
from agno.tools import Toolkit

# Configure logging
logger = logging.getLogger(__name__)


class CollectUserInfoTool(Toolkit):
    """Tool to collect and save user information to Google Sheets"""
    
    def __init__(
        self,
        credentials_file: Optional[str] = None,
        spreadsheet_id: Optional[str] = None,
        user_info_sheet_name: Optional[str] = None,
        name: str = "collect_user_info_tool",
    ):
        super().__init__(name=name)
        self.credentials_file = credentials_file or os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
        self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        self.user_info_sheet_name = user_info_sheet_name or os.getenv("INFO_SHEET_ID", "UserInfo")
        
        # Log configuration
        logger.info("[GOOGLE SHEETS TOOL] Initialized with:")
        logger.info("[GOOGLE SHEETS TOOL]   - Credentials file: %s", self.credentials_file)
        logger.info("[GOOGLE SHEETS TOOL]   - Spreadsheet ID: %s", self.spreadsheet_id)
        logger.info("[GOOGLE SHEETS TOOL]   - User Info Sheet: %s", self.user_info_sheet_name)
        logger.info("[GOOGLE SHEETS TOOL]   - Credentials file exists: %s", 
                   os.path.exists(self.credentials_file) if self.credentials_file else False)
        
        # Register the function
        self.register(self.save_user_info)
    
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
    
    def _get_google_sheets_client(self):
        """Initialize Google Sheets client"""
        try:
            logger.info("Initializing Google Sheets client...")
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Try to use credentials from environment variables first
            creds_dict = self._get_credentials_from_env()
            if creds_dict.get("client_email") and creds_dict.get("private_key"):
                logger.info("[GOOGLE SHEETS TOOL] Using credentials from environment variables")
                creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
                client = gspread.authorize(creds)
                logger.info("Google Sheets client initialized successfully with env vars")
                return client
            # Fallback to JSON file if environment variables not set
            elif self.credentials_file and os.path.exists(self.credentials_file):
                logger.info("[GOOGLE SHEETS TOOL] Using credentials from JSON file: %s", self.credentials_file)
                creds = Credentials.from_service_account_file(self.credentials_file, scopes=scope)
                client = gspread.authorize(creds)
                logger.info("Google Sheets client initialized successfully with JSON file")
                return client
            else:
                logger.error("[GOOGLE SHEETS TOOL] No valid credentials found (neither env vars nor JSON file)")
                return None
                
        except Exception as e:
            logger.error("Error connecting to Google Sheets: %s", e)
            return None
    
    def save_user_info(
        self,
        name: str,
        email: str,
        phone: Optional[str] = None,
        profile_link: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> str:
        """
        Save user information to Google Sheets.
        
        Args:
            name: User's full name (required)
            email: User's email address (required)
            phone: User's phone number (optional)
            profile_link: User's profile link (LinkedIn, CV, etc.) (optional)
        
        Returns:
            str: Success or error message
        """
        logger.info("[GOOGLE SHEETS TOOL] Called save_user_info with name='%s', email='%s', phone='%s', profile_link='%s', job_id='%s'", name, email, phone, profile_link, job_id)
        
        try:
            # Validate required fields
            if not name or not email:
                logger.warning("[GOOGLE SHEETS TOOL] Validation failed: missing required fields (name='%s', email='%s')", name, email)
                return "Lỗi: Tên và email là bắt buộc. Vui lòng cung cấp đầy đủ thông tin."
            
            # If credentials not configured, save to local file as fallback
            logger.debug("[GOOGLE SHEETS TOOL] Checking credentials file: %s", self.credentials_file)
            logger.debug("[GOOGLE SHEETS TOOL] Credentials file exists: %s", 
                        os.path.exists(self.credentials_file) if self.credentials_file else False)
            
            if not self.credentials_file:
                logger.warning("[GOOGLE SHEETS TOOL] Credentials file path is None, falling back to local file")
                return self._save_to_local_file(name, email, phone, profile_link, job_id)
            
            if not os.path.exists(self.credentials_file):
                logger.warning("[GOOGLE SHEETS TOOL] Credentials file does not exist at path: %s, falling back to local file", 
                             self.credentials_file)
                return self._save_to_local_file(name, email, phone, profile_link, job_id)
            
            # Connect to Google Sheets
            client = self._get_google_sheets_client()
            if not client:
                logger.warning("[GOOGLE SHEETS TOOL] Failed to get Google Sheets client, falling back to local file")
                return self._save_to_local_file(name, email, phone, profile_link, job_id)
            
            # Open spreadsheet and get the user info sheet
            logger.info("[GOOGLE SHEETS TOOL] Opening spreadsheet with ID: %s, sheet: %s", 
                       self.spreadsheet_id, self.user_info_sheet_name)
            spreadsheet = client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(self.user_info_sheet_name)

            # Prepare data
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row_data = [timestamp, name, email, phone or "", profile_link or "", job_id or ""]

            # Tìm hàng trống đầu tiên trong cột A
            all_values = worksheet.col_values(1)  # Lấy tất cả giá trị cột A
            next_row = len(all_values) + 1

            # Insert vào hàng cụ thể, bắt đầu từ cột A
            logger.info("[GOOGLE SHEETS TOOL] Inserting row at position %d: %s", next_row, row_data)
            worksheet.insert_row(row_data, next_row, value_input_option='USER_ENTERED')

            logger.info("[GOOGLE SHEETS TOOL] Successfully saved user info for '%s' to Google Sheets", name)
            return f"✅ Đã lưu thông tin của {name} thành công! Bộ phận tuyển dụng sẽ liên hệ với bạn sớm nhất."
            
        except Exception as e:
            logger.error("[GOOGLE SHEETS TOOL] Error saving to Google Sheets: %s", e, exc_info=True)
            return self._save_to_local_file(name, email, phone, profile_link, job_id)
    
    def _save_to_local_file(
        self,
        name: str,
        email: str,
        phone: Optional[str] = None,
        profile_link: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> str:
        """Fallback: Save to local JSON file if Google Sheets is not available"""
        logger.info("[GOOGLE SHEETS TOOL] Using fallback: saving to local file for user '%s'", name)
        try:
            os.makedirs("tmp", exist_ok=True)
            file_path = "tmp/user_info.json"
            
            # Load existing data
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = []
            
            # Append new data
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_data = {
                "timestamp": timestamp,
                "name": name,
                "email": email,
                "phone": phone or "",
                "profile_link": profile_link or "",
                "job_id": job_id or ""
            }
            data.append(user_data)
            
            # Save data
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info("[GOOGLE SHEETS TOOL] Successfully saved user info to local file: %s", file_path)
            logger.debug("[GOOGLE SHEETS TOOL] Saved data: %s", user_data)
            return f"✅ Đã lưu thông tin của {name} thành công! Bộ phận tuyển dụng sẽ liên hệ với bạn sớm nhất."
            
        except Exception as e:
            logger.error("[GOOGLE SHEETS TOOL] Error saving to local file: %s", e, exc_info=True)
            return f"❌ Lỗi khi lưu thông tin: {str(e)}"


class GetCurrentJobsTool(Toolkit):
    """Tool to get current job openings from Google Sheets or local file"""
    
    def __init__(
        self, 
        jobs_file: str = "data/jobs.json", 
        name: str = "get_current_jobs_tool",
        use_google_sheets: bool = True
    ):
        super().__init__(name=name)
        self.jobs_file = jobs_file
        self.use_google_sheets = use_google_sheets
        self._jobs_cache = None
        
        # Register the function
        self.register(self.get_current_jobs)
    
    def _load_jobs(self) -> list:
        """Load jobs from Google Sheets or local file"""
        # Return cached jobs if available
        if self._jobs_cache is not None:
            return self._jobs_cache
        
        jobs = []
        
        # Try to load from Google Sheets first
        if self.use_google_sheets:
            try:
                logger.info("[GET JOBS TOOL] Attempting to load jobs from Google Sheets...")
                from google_sheets_loader import GoogleSheetsLoader
                
                sheets_loader = GoogleSheetsLoader()
                jobs = sheets_loader.load_jobs_data()
                
                if jobs:
                    # Save to local file as cache
                    sheets_loader.save_jobs_to_json(self.jobs_file)
                    logger.info("[GET JOBS TOOL] ✅ Loaded %d jobs from Google Sheets", len(jobs))
                    self._jobs_cache = jobs
                    return jobs
                else:
                    logger.warning("[GET JOBS TOOL] ⚠️ No jobs loaded from Google Sheets, trying local file")
            except Exception as e:
                logger.warning("[GET JOBS TOOL] ⚠️ Error loading from Google Sheets: %s. Trying local file", e)
        
        # Fallback to local file
        try:
            if os.path.exists(self.jobs_file):
                with open(self.jobs_file, "r", encoding="utf-8") as f:
                    jobs_data = json.load(f)
                jobs = jobs_data.get("jobs", [])
                logger.info("[GET JOBS TOOL] ✅ Loaded %d jobs from local file: %s", len(jobs), self.jobs_file)
                self._jobs_cache = jobs
            else:
                logger.warning("[GET JOBS TOOL] ⚠️ Local jobs file not found: %s", self.jobs_file)
        except Exception as e:
            logger.error("[GET JOBS TOOL] ❌ Error loading from local file: %s", e)
        
        return jobs
    
    def get_current_jobs(self, position: Optional[str] = None, skills: Optional[str] = None) -> str:
        """
        Get current job openings based on position or skills.
        
        Args:
            position: Job position/title to search for (e.g., "Python Developer", "Data Analyst")
            skills: Required skills (e.g., "Python, SQL, Machine Learning")
        
        Returns:
            str: List of matching jobs or message if no jobs found
        """
        try:
            # Load jobs
            jobs = self._load_jobs()
            
            if not jobs:
                return self._get_default_message()
            
            # Filter jobs based on criteria
            matching_jobs = []
            search_terms = []
            
            if position:
                search_terms.extend(position.lower().split())
            if skills:
                search_terms.extend(skills.lower().split(","))
            
            # Clean search terms
            search_terms = [term.strip() for term in search_terms if term.strip()]
            
            for job in jobs:
                if not search_terms:
                    # No filter, return all jobs
                    matching_jobs.append(job)
                else:
                    # Check if any search term matches
                    job_text = f"{job.get('title', '')} {job.get('description', '')} {' '.join(job.get('skills', []))}".lower()
                    if any(term in job_text for term in search_terms):
                        matching_jobs.append(job)
            
            if not matching_jobs:
                return self._get_default_message()
            
            # Format results
            result = "🎯 **Các vị trí tuyển dụng phù hợp:**\n\n"
            for idx, job in enumerate(matching_jobs, 1):
                result += f"**{idx}. {job.get('title', 'N/A')}**\n"
                result += f"   - 📍 Địa điểm: {job.get('location', 'N/A')}\n"
                result += f"   - 💼 Loại hình: {job.get('type', 'N/A')}\n"
                result += f"   - 💰 Mức lương: {job.get('salary', 'Thỏa thuận')}\n"
                result += f"   - 📝 Mô tả: {job.get('description', 'N/A')}\n"
                
                if job.get('skills'):
                    result += f"   - 🔧 Kỹ năng: {', '.join(job.get('skills', []))}\n"
                
                if job.get('contact'):
                    result += f"   - 📧 Liên hệ: {job.get('contact', '')}\n"
                
                result += "\n"
            
            result += "\n💡 Bạn có quan tâm đến vị trí nào không? Hãy để lại thông tin để chúng tôi liên hệ với bạn nhé!"
            
            return result
            
        except Exception as e:
            logger.error("[GET JOBS TOOL] ❌ Error in get_current_jobs: %s", e)
            return self._get_default_message()
    
    def _get_default_message(self) -> str:
        """Return default message when no jobs found"""
        return (
            "😔 Rất tiếc, hiện tại mình không có vị trí nào phù hợp với yêu cầu của bạn.\n\n"
            "Bạn có thể để lại thông tin (tên, email, số điện thoại, link profile) "
            "để bộ phận tuyển dụng của chúng tôi phản hồi lại nếu có job phù hợp nhé! 🙏"
        )


class RecruitmentSearchTool(Toolkit):
    """
    Custom Google Search tool using Google Custom Search JSON API.
    Focused on recruitment websites (TopCV, VietnamWorks, TopDev, v.v.).
    """

    def __init__(self, name: str = "recruitment_search_tool"):
        super().__init__(name=name)
        self.api_key = os.getenv("GOOGLE_CSE_API_KEY") or os.getenv("GOOGLE_SEARCH_API_KEY")
        self.cx = os.getenv("GOOGLE_CSE_CX") or os.getenv("GOOGLE_SEARCH_CX")
        self.recruitment_sites = [
            "site:vti.com.vn",
            "site:topcv.vn",
            "site:vietnamworks.com",
            "site:indeed.com",
            "site:jobstreet.com",
            "site:careerbuilder.com",
            "site:ziprecruiter.com",
            "site:glassdoor.com",
            "site:monster.com",
            "site:careerjet.com",
            "site:jobrapido.com",
            "site:topdev.vn",
        ]
        # Register tool function for the agent
        self.register(self.search_recruitment_info)

    def _build_site_scope(self) -> str:
        # Combine site scopes with OR to bias results to recruitment sites
        # Example: (site:a OR site:b) query terms
        return "(" + " OR ".join(self.recruitment_sites) + ")"

    def _call_google_cse(self, q: str, num: int) -> dict:
        if not self.api_key or not self.cx:
            raise ValueError(
                "Thiếu cấu hình GOOGLE_CSE_API_KEY hoặc GOOGLE_CSE_CX. Vui lòng thiết lập biến môi trường."
            )
        # Cap per-request results to API limit (max 10)
        n = max(1, min(int(num or 5), 10))
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": q,
            "num": n,
            # Optional: safer defaults
            "safe": "off",
            "hl": "vi",
            "gl": "vn",
        }
        resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def search_recruitment_info(self, query: str, max_results: int = 5) -> str:
        """
        Tìm kiếm thông tin tuyển dụng từ các trang việc làm uy tín bằng Google CSE.

        Args:
            query: Nội dung cần tìm
            max_results: Số kết quả tối đa (<=10)

        Returns:
            Chuỗi kết quả đã định dạng kèm liên kết nguồn.
        """
        try:
            data = self._call_google_cse(query, max_results)
            items = data.get("items", [])
            if not items:
                return "Không tìm thấy kết quả phù hợp. Bạn có thể thử mô tả cụ thể hơn."

            lines = ["🔎 Kết quả tìm kiếm liên quan:", ""]
            citations = []
            for idx, item in enumerate(items, 1):
                title = item.get("title", "(Không tiêu đề)")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                lines.append(f"**{idx}. {title}**")
                if snippet:
                    lines.append(f"   - {snippet}")
                if link:
                    lines.append(f"   - 🔗 {link}")
                    citations.append(link)
                lines.append("")

            if citations:
                lines.append("Nguồn:")
                for c in citations[:3]:
                    lines.append(f"- {c}")

            return "\n".join(lines)
        except Exception as e:
            logger.error("[RECRUITMENT SEARCH TOOL] Error: %s", e, exc_info=True)
            return f"Không thể tìm kiếm thông tin: {str(e)}"

