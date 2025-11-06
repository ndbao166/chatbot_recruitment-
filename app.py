"""Streamlit UI for Recruitment Chatbot"""
import os
import uuid
import logging
import streamlit as st
from dotenv import load_dotenv
from agent import create_recruitment_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tmp/app.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Page configuration
st.set_page_config(
    page_title="Chatbot Tuyển Dụng",
    page_icon="💼",
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
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 2rem;
    }
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_agent():
    """Initialize and cache the recruitment agent"""
    logger.info("🔄 Khởi tạo chatbot agent...")
    use_google_sheets = os.getenv("USE_GOOGLE_SHEETS", "true").lower() == "true"
    agent = create_recruitment_agent(
        db_file=os.getenv("DB_FILE", "tmp/recruitment_db.db"),
        lancedb_path=os.getenv("LANCEDB_PATH", "tmp/lancedb"),
        use_google_sheets=use_google_sheets,
    )
    logger.info("✅ Chatbot agent đã được khởi tạo thành công")
    return agent


def initialize_session_state():
    """Initialize Streamlit session state"""
    # Initialize agent - always get from cache or create new
    # Agent is cached, so knowledge base is only loaded once
    if "agent" not in st.session_state:
        st.session_state.agent = initialize_agent()
        # NOTE: Removed automatic reload_knowledge() to improve performance
        # Knowledge base is loaded once when agent is initialized and cached
        # Use manual reload button in sidebar if you need to refresh data
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    
    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False


def display_chat_history():
    """Display chat history"""
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(content)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(content)


def send_greeting():
    """Send initial greeting message"""
    if not st.session_state.conversation_started:
        greeting = (
            "Xin chào! 👋 Mình là trợ lý tuyển dụng của công ty.\n\n"
            "Mình có thể giúp bạn:\n"
            "- 📋 Tìm hiểu về quy trình tuyển dụng\n"
            "- 💼 Tìm kiếm vị trí công việc phù hợp\n"
            "- 📝 Chuẩn bị cho phỏng vấn\n"
            "- 🎯 Để lại thông tin ứng tuyển\n\n"
            "Bạn cần hỗ trợ gì hôm nay? 😊"
        )
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": greeting
        })
        st.session_state.conversation_started = True


def handle_user_input(user_input: str):
    """Handle user input and get agent response"""
    # Add user message to chat history
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Display user message
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)
    
    # Get agent response with streaming for better UX
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        
        try:
            # Use streaming for faster perceived response time
            response = st.session_state.agent.chat(
                message=user_input,
                user_id=st.session_state.user_id,
                session_id=st.session_state.session_id,
            )
            
            # Stream the response
            assistant_message = ""
            try:
                # Try to iterate over response chunks
                for chunk in response:
                    # Handle different chunk formats
                    if hasattr(chunk, 'content') and chunk.content:
                        assistant_message += chunk.content
                    elif isinstance(chunk, str):
                        assistant_message += chunk
                    elif hasattr(chunk, 'text'):
                        assistant_message += chunk.text
                    
                    # Update UI with streaming cursor
                    if assistant_message:
                        message_placeholder.markdown(assistant_message + "▌")
            except (TypeError, AttributeError):
                # If response is not iterable, treat as single response
                if hasattr(response, 'content'):
                    assistant_message = response.content
                elif isinstance(response, str):
                    assistant_message = response
                else:
                    assistant_message = str(response)
                message_placeholder.markdown(assistant_message)
            
            # Final message without cursor
            if assistant_message:
                message_placeholder.markdown(assistant_message)
            else:
                message_placeholder.markdown("⚠️ Không nhận được phản hồi từ chatbot.")
            
            # Add assistant message to chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_message
            })
            
        except Exception as e:
            logger.error("Error in chat: %s", e, exc_info=True)
            error_message = f"❌ Xin lỗi, đã có lỗi xảy ra: {str(e)}"
            message_placeholder.markdown(error_message)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_message
            })


def main():
    """Main application"""
    # Initialize agent early to ensure it's ready
    if "agent" not in st.session_state:
        with st.spinner("🔄 Đang khởi tạo chatbot..."):
            st.session_state.agent = initialize_agent()
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.markdown('<div class="main-header">💼 Chatbot Tuyển Dụng</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Trợ lý thông minh hỗ trợ tìm việc và tuyển dụng</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        # Session info
        st.subheader("📊 Thông tin phiên")
        st.text(f"Session ID: {st.session_state.session_id}")
        st.text(f"Số tin nhắn: {len(st.session_state.messages)}")
        
        st.divider()
        
        # Actions
        st.subheader("🔧 Hành động")
        
        if st.button("🔄 Bắt đầu cuộc trò chuyện mới", use_container_width=True):
            # Clear current session
            st.session_state.agent.clear_session(
                session_id=st.session_state.session_id,
                user_id=st.session_state.user_id
            )
            
            # Reset session state
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.conversation_started = False
            st.rerun()
        
        if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_started = False
            st.rerun()
        
        if st.button("🔄 Tải lại dữ liệu (nếu cần)", use_container_width=True):
            with st.spinner("Đang tải lại dữ liệu..."):
                try:
                    st.session_state.agent.reload_knowledge()
                    st.success("✅ Đã tải lại dữ liệu thành công!")
                except Exception as e:
                    st.error(f"❌ Lỗi khi tải lại: {str(e)}")
        
        st.divider()
        
        # Information
        st.subheader("ℹ️ Thông tin")
        st.info(
            "**Chatbot này có thể:**\n"
            "- Trả lời câu hỏi về tuyển dụng\n"
            "- Tìm kiếm vị trí công việc\n"
            "- Lưu thông tin ứng viên\n"
            "- Tìm kiếm thông tin trên web"
        )
        
    
    # Main chat area
    st.divider()
    
    # Send greeting if conversation not started
    send_greeting()
    
    # Display chat history
    display_chat_history()
    
    # Show suggested questions if no messages yet (only greeting)
    if len(st.session_state.messages) <= 1:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Quy trình tuyển dụng là gì?", use_container_width=True, key="q1"):
                handle_user_input("Quy trình tuyển dụng là gì?")
                st.rerun()
            
            if st.button("💼 Tôi muốn tìm việc Python Developer", use_container_width=True, key="q3"):
                handle_user_input("Tôi muốn tìm việc Python Developer")
                st.rerun()
        
        with col2:
            if st.button("🔍 Có vị trí nào đang tuyển?", use_container_width=True, key="q2"):
                handle_user_input("Có vị trí nào đang tuyển?")
                st.rerun()
            
            if st.button("📝 Cần chuẩn bị gì cho phỏng vấn?", use_container_width=True, key="q4"):
                handle_user_input("Cần chuẩn bị gì cho phỏng vấn?")
                st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Nhập tin nhắn của bạn..."):
        handle_user_input(prompt)
        st.rerun()
    

if __name__ == "__main__":
    main()

