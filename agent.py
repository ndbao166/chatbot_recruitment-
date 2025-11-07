"""Recruitment Assistant Agent using Agno framework"""
import os
from datetime import datetime
from typing import Optional
from agno.agent import Agent
# from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.db.sqlite import SqliteDb
from tools import CollectUserInfoTool, GetCurrentJobsTool, RecruitmentSearchTool
from knowledge_base import setup_knowledge_base
from agno.db.base import  SessionType

class RecruitmentAgent:
    """Recruitment Assistant Chatbot Agent"""
    
    def __init__(
        self,
        model_id: str = "gemini-2.5-flash", # gpt-5
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
        
        # Store db_file for later use
        self.db_file = db_file
        
        # Store parameters for knowledge base reload
        self.lancedb_path = lancedb_path
        self.knowledge_csv = knowledge_csv
        self.use_google_sheets = use_google_sheets
        
        # Initialize database for session management
        self.db = SqliteDb(db_file=db_file)
        
        # Setup knowledge base (will load from Google Sheets if configured)
        self.knowledge = setup_knowledge_base(
            lancedb_path=lancedb_path,
            csv_file=knowledge_csv,
            use_google_sheets=use_google_sheets,
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
            model=Gemini(id=model_id),
            db=self.db,
            knowledge=self.knowledge,
            telemetry=False,
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
            num_history_runs=5,
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
    
    def reload_knowledge(self):
        """
        Reload knowledge base from Google Sheets or CSV.
        This will refresh the retrieval data without recreating the entire agent.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info("🔄 Đang tải lại dữ liệu retrieval...")
            # Reload knowledge base with force_reload=True to always fetch from Google Sheets
            self.knowledge = setup_knowledge_base(
                lancedb_path=self.lancedb_path,
                csv_file=self.knowledge_csv,
                use_google_sheets=self.use_google_sheets,
                force_reload=True,  # Force reload from Google Sheets
            )
            # Update agent's knowledge
            self.agent.knowledge = self.knowledge
            logger.info("✅ Đã tải lại dữ liệu retrieval thành công")
        except Exception as e:
            logger.error("❌ Lỗi khi tải lại dữ liệu retrieval: %s", e)
            raise
    
    def get_all_sessions(self):
        """
        Get all sessions from the database.
        
        Returns:
            List of session objects
        """
        try:
            # Try to get all sessions using the database's list method
            # If list_sessions doesn't exist, we'll query directly
            if hasattr(self.db, 'list_sessions'):
                sessions = self.db.list_sessions(session_type=SessionType.AGENT)
                return sessions
            elif hasattr(self.db, 'get_sessions'):
                sessions = self.db.get_sessions(session_type=SessionType.AGENT)
                return sessions
            else:
                # Fallback: query SQLite directly
                import sqlite3
                # Use the stored db_file path
                db_path = self.db_file
                
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Query sessions table - try different possible table/column names
                try:
                    cursor.execute("""
                        SELECT session_id, user_id, created_at, updated_at
                        FROM sessions
                        WHERE session_type = ?
                        ORDER BY created_at DESC
                    """, ('agent',))
                except:
                    # Try without session_type filter
                    try:
                        cursor.execute("""
                            SELECT session_id, user_id, created_at, updated_at
                            FROM sessions
                            ORDER BY created_at DESC
                        """)
                    except:
                        conn.close()
                        return []
                
                rows = cursor.fetchall()
                
                # Get runs count for each session
                sessions = []
                for row in rows:
                    session_id = row[0]
                    # Count runs for this session
                    try:
                        cursor.execute("""
                            SELECT COUNT(*) FROM runs WHERE session_id = ?
                        """, (session_id,))
                        runs_count = cursor.fetchone()[0]
                    except:
                        runs_count = 0
                    
                    # Parse datetime strings
                    created_at = None
                    updated_at = None
                    try:
                        if row[2]:
                            date_str = str(row[2])
                            created_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except Exception as e:
                        pass
                    try:
                        if row[3]:
                            date_str = str(row[3])
                            updated_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except Exception as e:
                        pass
                    
                    session_obj = type('Session', (), {
                        'session_id': session_id,
                        'user_id': row[1],
                        'created_at': created_at,
                        'updated_at': updated_at,
                        'runs': [None] * runs_count  # Placeholder for runs count
                    })()
                    sessions.append(session_obj)
                
                conn.close()
                return sessions
        except Exception as e:
            print(f"Error getting all sessions: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_messages_for_session(self, session_id: str):
        """
        Get all messages for a specific session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of messages
        """
        try:
            messages = self.agent.get_messages_for_session(session_id=session_id)
            return messages
        except Exception as e:
            print(f"Error getting messages for session: {e}")
            return []


def create_recruitment_agent(**kwargs) -> RecruitmentAgent:
    """
    Factory function to create a RecruitmentAgent.
    
    Args:
        **kwargs: Arguments to pass to RecruitmentAgent constructor
    
    Returns:
        RecruitmentAgent instance
    """
    return RecruitmentAgent(**kwargs)


def get_all_sessions_from_db(db_file: str = "tmp/recruitment_db.db"):
    """
    Lightweight function to get all sessions from database without initializing full agent.
    This is optimized for HR dashboard to avoid unnecessary initialization.
    
    Args:
        db_file: Path to SQLite database for session storage
    
    Returns:
        List of session objects
    """
    try:
        # Only initialize database, no knowledge base, tools, or model
        db = SqliteDb(db_file=db_file)
        
        # Try to get all sessions using the database's list method
        if hasattr(db, 'list_sessions'):
            sessions = db.list_sessions(session_type=SessionType.AGENT)
            return sessions
        elif hasattr(db, 'get_sessions'):
            sessions = db.get_sessions(session_type=SessionType.AGENT)
            return sessions
        else:
            # Fallback: query SQLite directly
            import sqlite3
            
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Query sessions table - try different possible table/column names
            try:
                cursor.execute("""
                    SELECT session_id, user_id, created_at, updated_at
                    FROM sessions
                    WHERE session_type = ?
                    ORDER BY created_at DESC
                """, ('agent',))
            except:
                # Try without session_type filter
                try:
                    cursor.execute("""
                        SELECT session_id, user_id, created_at, updated_at
                        FROM sessions
                        ORDER BY created_at DESC
                    """)
                except:
                    conn.close()
                    return []
            
            rows = cursor.fetchall()
            
            # Get runs for each session
            sessions = []
            for row in rows:
                session_id = row[0]
                # Get runs for this session
                try:
                    cursor.execute("""
                        SELECT run_id FROM runs WHERE session_id = ?
                        ORDER BY created_at ASC
                    """, (session_id,))
                    run_ids = [r[0] for r in cursor.fetchall()]
                except:
                    run_ids = []
                
                # Parse datetime strings
                created_at = None
                updated_at = None
                try:
                    if row[2]:
                        date_str = str(row[2])
                        created_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except Exception as e:
                    pass
                try:
                    if row[3]:
                        date_str = str(row[3])
                        updated_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except Exception as e:
                    pass
                
                # Get session with runs using database method
                try:
                    session = db.get_session(session_id=session_id, session_type=SessionType.AGENT)
                    if session:
                        sessions.append(session)
                    else:
                        # Fallback: create minimal session object
                        session_obj = type('Session', (), {
                            'session_id': session_id,
                            'user_id': row[1],
                            'created_at': created_at,
                            'updated_at': updated_at,
                            'runs': []
                        })()
                        sessions.append(session_obj)
                except:
                    # Fallback: create minimal session object
                    session_obj = type('Session', (), {
                        'session_id': session_id,
                        'user_id': row[1],
                        'created_at': created_at,
                        'updated_at': updated_at,
                        'runs': []
                    })()
                    sessions.append(session_obj)
            
            conn.close()
            return sessions
    except Exception as e:
        print(f"Error getting all sessions: {e}")
        import traceback
        traceback.print_exc()
        return []

