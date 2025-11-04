"""Recruitment Assistant Agent using Agno framework"""
import os
from typing import Optional
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb
from tools import CollectUserInfoTool, GetCurrentJobsTool, RecruitmentSearchTool
from knowledge_base import setup_knowledge_base
from agno.db.base import  SessionType

class RecruitmentAgent:
    """Recruitment Assistant Chatbot Agent"""
    
    def __init__(
        self,
        model_id: str = "gpt-4.1",
        db_file: str = "tmp/recruitment_db.db",
        lancedb_path: str = "tmp/lancedb",
        jobs_file: str = "data/jobs.json",
        knowledge_csv: str = "data/recruitment_knowledge.csv",
        use_google_sheets: bool = True,
    ):
        """
        Initialize Recruitment Agent.
        
        Args:
            model_id: OpenAI model ID to use
            db_file: Path to SQLite database for session storage
            lancedb_path: Path to LanceDB for knowledge base
            jobs_file: Path to jobs JSON file (fallback)
            knowledge_csv: Path to recruitment knowledge CSV (fallback)
            use_google_sheets: Whether to load data from Google Sheets (default: True)
        """
        # Create tmp directory if it doesn't exist
        os.makedirs("tmp", exist_ok=True)
        
        # Initialize database for session management
        self.db = SqliteDb(db_file=db_file)
        
        # Setup knowledge base (will load from Google Sheets if configured)
        self.knowledge = setup_knowledge_base(
            lancedb_path=lancedb_path,
            csv_file=knowledge_csv,
            use_google_sheets=use_google_sheets
        )
        
        # Initialize tools
        self.collect_info_tool = CollectUserInfoTool()
        self.get_jobs_tool = GetCurrentJobsTool(
            jobs_file=jobs_file,
            use_google_sheets=use_google_sheets
        )
        self.search_tool = RecruitmentSearchTool()
        
        # Create the agent
        self.agent = Agent(
            name="Recruitment Assistant",
            model=OpenAIChat(id=model_id),
            db=self.db,
            knowledge=self.knowledge,
            tools=[
                self.collect_info_tool,
                self.get_jobs_tool,
                self.search_tool,
            ],
            description=(
                "Bạn là trợ lý tuyển dụng thông minh, chuyên nghiệp và thân thiện. "
                "Nhiệm vụ của bạn là hỗ trợ ứng viên trong quá trình tìm việc và tuyển dụng."
            ),
            instructions=[
                # Greeting and behavior
                "Luôn chào hỏi thân thiện khi bắt đầu cuộc trò chuyện.",
                "Sử dụng ngôn ngữ lịch sự, chuyên nghiệp nhưng gần gũi với ứng viên.",
                "Gọi ứng viên bằng 'bạn' và tự xưng là 'mình' hoặc 'em'.",
                # Knowledge base usage and web search strictness - QnA Priority Flow
                "Đối với câu hỏi dạng QnA (Question and Answer - câu hỏi cần câu trả lời thông tin):",
                "BƯỚC 1: LUÔN LUÔN retrieve/tra cứu từ knowledge base TRƯỚC TIÊN khi trả lời câu hỏi.",
                "BƯỚC 2: Nếu knowledge base có thông tin phù hợp 100 (dù chỉ một phần), HÃY trả lời dựa trên thông tin đó Và Kết thúc.  NẾU KHÔNG ĐẠT 100% KHỚP hoặc có bất kỳ nghi ngờ nào về độ liên quan/độ phủ, LUÔN LUÔN sử dụng tool 'recruitment_search_tool' để tra cứu web ở bước BƯỚC 3.",
                "BƯỚC 3: CHỈ sử dụng tool 'recruitment_search_tool' để tra cứu web  KHI:",
                "   - Knowledge base KHÔNG có thông tin liên quan, HOẶC",
                "   - Thông tin từ knowledge base KHÔNG ĐỦ để trả lời đầy đủ câu hỏi.",
                "TUYỆT ĐỐI không suy đoán hay bịa nội dung khi bằng chứng không rõ ràng. Nếu thiếu thông tin, hãy nói rõ và đề nghị tìm kiếm/cung cấp thêm dữ liệu.",
                "Mọi câu trả lời dựa trên web search phải kèm TRÍCH DẪN nguồn dạng liên kết (URL) ở cuối câu trả lời, liệt kê 1–3 nguồn chính xác.",
                "Khi sử dụng kết quả tìm kiếm, hãy tổng hợp ngắn gọn, rõ ràng, có cấu trúc, và nêu nguồn.",
                # Job search behavior
                "Khi người dùng hỏi về tìm kiếm công việc hoặc vị trí tuyển dụng, HÃY sử dụng tool 'get_current_jobs' để tìm các vị trí phù hợp.",
                "Phân tích ý định của người dùng để xác định vị trí (position) và kỹ năng (skills) họ quan tâm.",
                "Nếu KHÔNG có vị trí nào phù hợp, HÃY trả lời: 'Rất tiếc, hiện tại mình không có vị trí nào phù hợp với yêu cầu của bạn. Bạn có thể để lại thông tin để bộ phận tuyển dụng phản hồi lại nếu có job phù hợp nhé!'",
                "Sau khi đưa ra danh sách công việc, HÃY hỏi xem người dùng có quan tâm và muốn để lại thông tin không.",
                # Collecting user information
                "Khi người dùng muốn ứng tuyển hoặc để lại thông tin, HÃY sử dụng tool 'save_user_info' để lưu thông tin.",
                "Thông tin BẮT BUỘC: Tên (name) và Email (email).",
                "Thông tin TÙY CHỌN: Số điện thoại (phone) và Link profile/CV (profile_link).",
                "Nếu người dùng chưa cung cấp đủ thông tin bắt buộc, HÃY hỏi lại một cách lịch sự.",
                "Nếu người dùng đề cập đến một vị trí cụ thể, HÃY lấy 'job_id' tương ứng từ danh sách job (qua tool 'get_current_jobs' hoặc dữ liệu đã tải) và truyền 'job_id' khi gọi 'save_user_info'.",
                "Nếu người dùng nhắc nhiều vị trí hoặc chưa rõ, HÃY hỏi lại để xác nhận vị trí trước khi lưu và chỉ truyền 'job_id' khi đã rõ ràng.",
                "Sau khi lưu thông tin thành công, HÃY cảm ơn và thông báo bộ phận tuyển dụng sẽ liên hệ sớm.",
                # General behavior
                "Nếu câu hỏi KHÔNG liên quan đến tuyển dụng, hãy lịch sự từ chối và hướng dẫn người dùng quay lại chủ đề tuyển dụng.",
                "Luôn kết thúc câu trả lời bằng một câu hỏi mở để tiếp tục cuộc trò chuyện.",
                "Sử dụng emoji một cách phù hợp để tạo sự thân thiện (nhưng không lạm dụng).",
                # Context and memory
                "Ghi nhớ thông tin người dùng đã chia sẻ trong cuộc trò chuyện để tạo trải nghiệm cá nhân hóa.",
                "Tham khảo lịch sử trò chuyện để hiểu ngữ cảnh và tránh hỏi lại thông tin đã có.",
            ],
            # Session management
            add_history_to_context=True,
            num_history_runs=5,  # Keep last 5 interactions in context
            # Response settings
            markdown=True,
            # Enable search across sessions if needed
            search_session_history=False,  # Can enable if needed
            # Storage settings
            store_media=True,
            store_tool_messages=True,
            store_history_messages=True,
        )
    
    def chat(
        self,
        message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        stream: bool = False,
    ):
        """
        Send a message to the agent and get response.
        
        Args:
            message: User message
            user_id: User ID for session management
            session_id: Session ID for conversation continuity
            stream: Whether to stream the response
        
        Returns:
            Agent response
        """
        return self.agent.run(
            input=message,
            user_id=user_id,
            session_id=session_id,
            stream=stream,
        )
    
    def get_session_history(self, session_id: str, user_id: Optional[str] = None):
        """
        Get session history.
        
        Args:
            session_id: Session ID
            user_id: User ID (optional)
        
        Returns:
            Session history
        """
        try:
            session = self.db.get_session(session_id=session_id, user_id=user_id, session_type=SessionType.AGENT)
            if session:
                return session.runs
            return []
        except Exception as e:
            print(f"Error getting session history: {e}")
            return []
    
    def clear_session(self, session_id: str, user_id: Optional[str] = None):
        """
        Clear a session.
        
        Args:
            session_id: Session ID
            user_id: User ID (optional)
        """
        try:
            # Get session and delete all runs
            session = self.db.get_session(session_id=session_id, user_id=user_id, session_type=SessionType.AGENT)
            if session:
                # Delete the session (this will cascade delete runs)
                self.db.delete_session(session_id=session_id)
                print(f"✅ Cleared session {session_id}")
        except Exception as e:
            print(f"Error clearing session: {e}")


def create_recruitment_agent(**kwargs) -> RecruitmentAgent:
    """
    Factory function to create a RecruitmentAgent.
    
    Args:
        **kwargs: Arguments to pass to RecruitmentAgent constructor
    
    Returns:
        RecruitmentAgent instance
    """
    return RecruitmentAgent(**kwargs)

