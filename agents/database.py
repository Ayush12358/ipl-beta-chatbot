import os
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError:
    pass

# Load environment variables from .env file
load_dotenv()

# Local SQLite fallback
SQLITE_DB_PATH = Path("data/chatbot_history.db")

# Logger
logger = logging.getLogger("Database")

def get_supabase_client() -> Optional['Client']:
    """
    Get Supabase client if configured.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if url and key:
        try:
            return create_client(url, key)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
    return None

def init_db():
    """Initialize the database tables."""
    # Check if we are in Cloud mode
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
        logger.info("ℹ️ Cloud Database Mode: Skipping auto-creation of tables.")
        logger.info("   Please run the SQL in 'supabase_schema.sql' in your Supabase Dashboard to create the table.")
        return

    # SQLite Fallback (Local only)
    try:
        SQLITE_DB_PATH.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            query TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            expander_output TEXT,
            decomposer_output TEXT,
            generator_output TEXT,
            formatter_output TEXT,
            final_result_json TEXT,
            error_message TEXT,
            response_summary TEXT
        )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database initialized (Local SQLite)")
    except Exception as e:
        logger.error(f"Local DB init failed: {e}")

def log_interaction_to_db(
    query: str, 
    result_data: Dict[str, Any],
    expander_data: Optional[Dict] = None,
    decomposer_data: Optional[Dict] = None,
    generator_data: Optional[Dict] = None,
    formatter_data: Optional[Dict] = None
):
    """
    Log a detailed chat interaction to the database.
    Prioritizes Supabase Client -> Postgres/SQLite Fallback.
    """
    try:
        # Prepare data
        timestamp = datetime.now().isoformat()
        success = result_data.get("success", False)
        error = result_data.get("error")
        summary = result_data.get("answer", {}).get("summary") if success else None
        
        # Serialize fields
        expander_json = json.dumps(expander_data, default=str) if expander_data else None
        decomposer_json = json.dumps(decomposer_data, default=str) if decomposer_data else None
        generator_json = json.dumps(generator_data, default=str) if generator_data else None
        formatter_json = json.dumps(formatter_data, default=str) if formatter_data else None
        final_result_json = json.dumps(result_data, default=str)
        
        # 1. Try Supabase Client
        client = get_supabase_client()
        if client:
            try:
                data = {
                    "timestamp": timestamp,
                    "query": query,
                    "success": success,
                    "expander_output": expander_json,
                    "decomposer_output": decomposer_json,
                    "generator_output": generator_json,
                    "formatter_output": formatter_json,
                    "final_result_json": final_result_json,
                    "error_message": error,
                    "response_summary": summary
                }
                client.table("interactions").insert(data).execute()
                logger.info(f"Logged to Supabase (via Client)")
                return
            except Exception as e:
                logger.error(f"Supabase Client log failed: {e}")
        
        # 2. Fallback to Local SQLite
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO interactions (
            timestamp, query, success, 
            expander_output, decomposer_output, generator_output, formatter_output,
            final_result_json, error_message, response_summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, query, success,
            expander_json, decomposer_json, generator_json, formatter_json,
            final_result_json, error, summary
        ))
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to log to database: {e}")

def get_recent_interactions(limit: int = 10):
    """Fetch recent interactions from the database."""
    try:
        # 1. Try Supabase Client
        client = get_supabase_client()
        if client:
            try:
                response = client.table("interactions").select("*").order("id", desc=True).limit(limit).execute()
                return response.data
            except Exception as e:
                logger.error(f"Supabase fetch failed: {e}")

        # 2. Fallback to SQLite
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM interactions ORDER BY id DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"Error fetching interactions: {e}")
        return []
