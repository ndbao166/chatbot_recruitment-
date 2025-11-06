"""Knowledge base setup for Recruitment Chatbot"""
import os
import logging
from pathlib import Path
from agno.knowledge import Knowledge
# from agno.knowledge.embedder.google import GeminiEmbedder
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.lancedb import LanceDb
from agno.knowledge.chunking.row import RowChunking
from agno.knowledge.reader.csv_reader import CSVReader
from google_sheets_loader import GoogleSheetsLoader

# Configure logging
logger = logging.getLogger(__name__)


def setup_knowledge_base(
    lancedb_path: str = "tmp/lancedb",
    csv_file: str = "data/recruitment_knowledge.csv",
    table_name: str = "recruitment_knowledge",
    use_google_sheets: bool = True,
    force_reload: bool = False,
) -> Knowledge:
    """
    Setup knowledge base with LanceDB and data from Google Sheets or CSV.
    
    Args:
        lancedb_path: Path to LanceDB storage
        csv_file: Path to CSV file with recruitment knowledge (fallback)
        table_name: Name of the LanceDB table
        use_google_sheets: Whether to load data from Google Sheets (default: True)
        force_reload: If True, always reload from Google Sheets even if CSV exists (default: False)
    
    Returns:
        Knowledge: Configured knowledge base
    """
    # Create directories if they don't exist
    Path(lancedb_path).parent.mkdir(parents=True, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Initialize knowledge base with LanceDB
    knowledge = Knowledge(
        vector_db=LanceDb(
            uri=lancedb_path,
            table_name=table_name,
            embedder=OpenAIEmbedder(),
        ),
        max_results=1
    )
    
    # Try to load from Google Sheets only if CSV cache doesn't exist or force_reload is True
    # This avoids unnecessary API calls on every initialization
    if use_google_sheets and (force_reload or not os.path.exists(csv_file)):
        try:
            logger.info("CSV cache not found. Attempting to load knowledge from Google Sheets...")
            sheets_loader = GoogleSheetsLoader()
            
            # Load data from Google Sheets
            df = sheets_loader.load_knowledge_data()
            
            if df is not None:
                # Save to CSV as cache
                sheets_loader.save_knowledge_to_csv(csv_file)
                logger.info("✅ Loaded knowledge from Google Sheets and cached to %s", csv_file)
            else:
                logger.warning("⚠️ Could not load from Google Sheets, will try local CSV if exists")
        except Exception as e:
            logger.warning("⚠️ Error loading from Google Sheets: %s. Will try local CSV if exists", e)
    elif use_google_sheets and os.path.exists(csv_file):
        logger.info("Using cached CSV file: %s (skip Google Sheets to improve performance)", csv_file)
    
    # Load CSV data (either from cache or original file)
    if os.path.exists(csv_file):
        try:
            # Add CSV content with row-based chunking
            knowledge.add_content(
                path=csv_file,
                reader=CSVReader(
                    chunking_strategy=RowChunking(),
                ),
            )
            logger.info("✅ Loaded knowledge from %s", csv_file)
        except Exception as e:
            logger.error("❌ Error loading CSV file: %s", e)
    else:
        logger.warning("⚠️ CSV file not found at %s", csv_file)
    
    return knowledge


def add_additional_knowledge(knowledge: Knowledge, urls: list = None, files: list = None):
    """
    Add additional knowledge from URLs or files.
    
    Args:
        knowledge: Knowledge base instance
        urls: List of URLs to add
        files: List of file paths to add
    """
    if urls:
        for url in urls:
            try:
                knowledge.add_content(url=url)
                print(f"✅ Added knowledge from {url}")
            except Exception as e:
                print(f"⚠️ Warning: Could not load URL {url}: {e}")
    
    if files:
        for file_path in files:
            if os.path.exists(file_path):
                try:
                    knowledge.add_content(path=file_path)
                    print(f"✅ Added knowledge from {file_path}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not load file {file_path}: {e}")
            else:
                print(f"⚠️ Warning: File not found at {file_path}")

