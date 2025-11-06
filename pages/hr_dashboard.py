"""HR Dashboard - View all conversations"""
import os
import streamlit as st
from datetime import datetime as dt
from dotenv import load_dotenv
from agent import get_all_sessions_from_db

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="HR Dashboard - Chatbot Tuyển Dụng",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .session-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: #f9f9f9;
    }
    .message-user {
        background-color: #e3f2fd;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .message-assistant {
        background-color: #f5f5f5;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# HR Password
HR_PASSWORD = "123123"

def check_hr_auth():
    """Check if user is authenticated as HR"""
    if "hr_authenticated" not in st.session_state:
        st.session_state.hr_authenticated = False
    return st.session_state.hr_authenticated

def login_page():
    """Display login page"""
    st.markdown('<div class="main-header">👥 HR Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; color: #666; font-size: 1.2rem; margin-bottom: 2rem;">Đăng nhập để xem lịch sử cuộc trò chuyện</div>', unsafe_allow_html=True)
    
    with st.form("hr_login_form"):
        username = st.text_input("👤 Tên đăng nhập", placeholder="Nhập tên đăng nhập (bất kỳ)")
        password = st.text_input("🔒 Mật khẩu", type="password", placeholder="Nhập mật khẩu")
        
        submitted = st.form_submit_button("🔑 Đăng nhập", use_container_width=True)
        
        if submitted:
            if password == HR_PASSWORD:
                st.session_state.hr_authenticated = True
                st.session_state.hr_username = username
                st.rerun()
            else:
                st.error("❌ Mật khẩu không đúng! Vui lòng thử lại.")
    

def format_datetime(datetime_value):
    """Format datetime to readable string"""
    if datetime_value:
        if isinstance(datetime_value, str):
            return datetime_value
        elif isinstance(datetime_value, (int, float)):
            # Handle unix timestamp
            try:
                return dt.fromtimestamp(datetime_value).strftime("%d/%m/%Y %H:%M:%S")
            except:
                return str(datetime_value)
        elif hasattr(datetime_value, 'strftime'):
            return datetime_value.strftime("%d/%m/%Y %H:%M:%S")
    return "N/A"

def display_conversation_detail(session):
    """Display detailed conversation view"""
    session_id = getattr(session, 'session_id', 'N/A')
    st.subheader("📋 Chi tiết cuộc trò chuyện")
    st.code(f"Session ID: {session_id}")
    
    runs = getattr(session, 'runs', [])
    if not runs:
        st.info("Không có tin nhắn nào trong cuộc trò chuyện này.")
        return
    
    # Collect all messages from all runs
    all_messages = []
    for run in runs:
        messages = getattr(run, 'messages', [])
        if messages:
            for msg in messages:
                role = getattr(msg, 'role', None) or getattr(msg, 'name', 'unknown')
                if role not in ['user', 'assistant']:
                    continue
                all_messages.append(msg)
    
    if not all_messages:
        st.info("Không có tin nhắn nào trong cuộc trò chuyện này.")
        return
    
    # Display messages
    for msg in all_messages:
        role = getattr(msg, 'role', None) or getattr(msg, 'name', 'unknown')
        content = getattr(msg, 'content', '') or getattr(msg, 'text', '')
        
        # Skip system messages
        if role == 'system':
            continue
        
        if role == 'user' or role == 'human':
            with st.chat_message("user", avatar="👤"):
                st.markdown(content)
        elif role == 'assistant':
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(content)
        else:
            # For other message types
            st.markdown(f"**{role}:** {content}")

def dashboard_page():
    """Display HR dashboard with all conversations"""
    st.markdown('<div class="main-header">👥 HR Dashboard</div>', unsafe_allow_html=True)
    
    # Get database file path (no need to initialize full agent)
    if "db_file" not in st.session_state:
        st.session_state.db_file = os.getenv("DB_FILE", "tmp/recruitment_db.db")
    
    # Initialize viewing session state
    if "viewing_session_id" not in st.session_state:
        st.session_state.viewing_session_id = None
    if "selected_session" not in st.session_state:
        st.session_state.selected_session = None
    
    # Sidebar
    with st.sidebar:
        st.header(f"👋 Xin chào, {st.session_state.get('hr_username', 'HR')}!")
        
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.hr_authenticated = False
            st.session_state.hr_username = None
            st.session_state.viewing_session_id = None
            st.session_state.selected_session = None
            st.rerun()
        
        st.divider()
        
        # Conversations list in sidebar
        st.subheader("📚 Lịch sử cuộc trò chuyện")
        try:
            sessions = get_all_sessions_from_db(db_file=st.session_state.db_file)
            
            if sessions:
                # Sort by created_at descending (newest first)
                try:
                    sessions = sorted(
                        sessions,
                        key=lambda x: getattr(x, 'created_at', 0) or 0,
                        reverse=True
                    )
                except:
                    pass
                
                # Show sessions list (limit to 20 most recent)
                for session in sessions[:20]:
                    session_id = getattr(session, 'session_id', 'N/A')
                    created_at = format_datetime(getattr(session, 'created_at', None))
                    runs = getattr(session, 'runs', [])
                    
                    # Get preview text
                    preview_text = ""
                    for run in runs:
                        messages = getattr(run, 'messages', [])
                        for msg in messages:
                            role = getattr(msg, 'role', '')
                            if role == 'user':
                                content = getattr(msg, 'content', '') or getattr(msg, 'text', '')
                                if content:
                                    preview_text = content[:25] + "..." if len(content) > 25 else content
                                    break
                        if preview_text:
                            break
                    
                    # Check if this session is selected
                    is_selected = st.session_state.viewing_session_id == session_id
                    button_label = f"{'✓ ' if is_selected else ''}{preview_text or 'Session'}"
                    
                    if st.button(button_label, key=f"sidebar_session_{session_id}", use_container_width=True):
                        st.session_state.viewing_session_id = session_id
                        st.session_state.selected_session = session
                        st.rerun()
            else:
                st.info("📭 Chưa có cuộc trò chuyện nào")
        except Exception as e:
            st.error(f"Lỗi: {str(e)}")
        
        # Button to go back to list view
        if st.session_state.viewing_session_id:
            st.divider()
            if st.button("🔙 Quay lại danh sách", use_container_width=True):
                st.session_state.viewing_session_id = None
                st.session_state.selected_session = None
                st.rerun()
    
    # Main content area
    if st.session_state.viewing_session_id and st.session_state.selected_session:
        # Display selected conversation in main chat area
        selected_session = st.session_state.selected_session
        session_id = getattr(selected_session, 'session_id', 'N/A')
        user_id = getattr(selected_session, 'user_id', 'N/A')
        created_at = format_datetime(getattr(selected_session, 'created_at', None))
        
        st.info(f"📋 **Đang xem cuộc trò chuyện:** Session {session_id[:8]}... | User {user_id[:8] if user_id != 'N/A' else 'N/A'}... | {created_at}")
        st.divider()
        
        display_conversation_detail(selected_session)
    else:
        # List view
        try:
            # Get all sessions
            sessions = get_all_sessions_from_db(db_file=st.session_state.db_file)
            
            if not sessions:
                st.info("📭 Chưa có cuộc trò chuyện nào được lưu.")
                return
            
            # Filter/search
            col1, col2 = st.columns([3, 1])
            with col1:
                search_term = st.text_input("🔍 Tìm kiếm", placeholder="Tìm theo session ID hoặc user ID...")
            with col2:
                sort_option = st.selectbox("📊 Sắp xếp", ["Mới nhất", "Cũ nhất"])
            
            # Filter sessions
            filtered_sessions = sessions
            if search_term:
                search_term = search_term.lower()
                filtered_sessions = [
                    s for s in sessions
                    if search_term in str(getattr(s, 'session_id', '')).lower()
                    or search_term in str(getattr(s, 'user_id', '')).lower()
                ]
            
            # Sort sessions
            if sort_option == "Mới nhất":
                try:
                    filtered_sessions = sorted(
                        filtered_sessions,
                        key=lambda x: getattr(x, 'created_at', 0) or 0,
                        reverse=True
                    )
                except:
                    pass
            else:
                try:
                    filtered_sessions = sorted(
                        filtered_sessions,
                        key=lambda x: getattr(x, 'created_at', float('inf')) or float('inf'),
                        reverse=False
                    )
                except:
                    pass
            
            st.info(f"📊 Hiển thị {len(filtered_sessions)}/{len(sessions)} cuộc trò chuyện")
            
            # Display sessions as cards
            for session in filtered_sessions:
                session_id = getattr(session, 'session_id', 'N/A')
                user_id = getattr(session, 'user_id', 'N/A')
                created_at = format_datetime(getattr(session, 'created_at', None))
                runs = getattr(session, 'runs', [])
                num_runs = len(runs) if runs else 0
                
                # Count total messages across all runs
                total_messages = 0
                for run in runs:
                    messages = getattr(run, 'messages', [])
                    if messages:
                        # Count non-system messages
                        total_messages += len([m for m in messages if getattr(m, 'role', '') != 'system'])
                
                # Get first user message for preview
                preview_text = ""
                for run in runs:
                    messages = getattr(run, 'messages', [])
                    for msg in messages:
                        role = getattr(msg, 'role', '')
                        if role not in ['user', 'assistant']:
                            continue

                        if role == 'user':
                            content = getattr(msg, 'content', '') or getattr(msg, 'text', '')
                            if content:
                                preview_text = content[:50] + "..." if len(content) > 50 else content
                                break
                    if preview_text:
                        break
                
                # Card display
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{preview_text or 'Cuộc trò chuyện'}**")
                        st.caption(f"Session: {session_id[:8]}... | User: {user_id[:8] if user_id != 'N/A' else 'N/A'}... | {created_at} | {total_messages} tin nhắn")
                    with col2:
                        if st.button("👁️ Xem", key=f"view_list_{session_id}", use_container_width=True):
                            st.session_state.viewing_session_id = session_id
                            st.session_state.selected_session = session
                            st.rerun()
                    st.divider()
        
        except Exception as e:
            st.error(f"❌ Lỗi khi tải danh sách cuộc trò chuyện: {str(e)}")
            st.exception(e)

def main():
    """Main application"""
    if not check_hr_auth():
        login_page()
    else:
        dashboard_page()

if __name__ == "__main__":
    main()

