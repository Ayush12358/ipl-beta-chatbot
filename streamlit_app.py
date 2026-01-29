"""
IPL Cricket Chatbot - Streamlit App
====================================
A simple MVP chatbot for IPL cricket statistics.

Run:
    streamlit run streamlit_app.py
"""

import streamlit as st
import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent / "agents"))

from agents.database import init_db, log_interaction_to_db

from dotenv import load_dotenv
load_dotenv()


# =============================================================================
# Logging Setup
# =============================================================================

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler(LOGS_DIR / "chatbot.log")  # File output
    ]
)
logger = logging.getLogger("IPL_Chatbot")

# Query log file (separate for easy analysis)
QUERY_LOG_FILE = LOGS_DIR / "queries.jsonl"


def log_query(query: str, result: Dict[str, Any]):
    """Log query and result to JSONL file for analysis."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "success": result.get("success", False),
        "error": result.get("error"),
        "stages_completed": list(result.get("stages", {}).keys())
    }
    
    with open(QUERY_LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    logger.info(f"Query logged to {QUERY_LOG_FILE}")
    
    # Log to SQLite Database (HANDLED IN process_query_with_live_updates NOW)
    # try:
    #     log_interaction_to_db(query, result)
    #     logger.info("Query logged to database")
    # except Exception as e:
    #     logger.error(f"Failed to log to database: {e}")


# =============================================================================
# Page Config
# =============================================================================

st.set_page_config(
    page_title="IPL Cricket Chatbot",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background-color: #0f0f1a;
    }
    
    .main-title {
        text-align: center;
        background: linear-gradient(135deg, #6c5ce7, #a29bfe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        text-align: center;
        color: #888;
        margin-bottom: 2rem;
    }
    
    .success-box {
        background-color: #1a3d2e;
        border-left: 4px solid #00b894;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    .error-box {
        background-color: #3d1a1a;
        border-left: 4px solid #ff6b6b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    .insight-item {
        background-color: #1a1a2e;
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 3px solid #6c5ce7;
    }
    
    .step-progress {
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
        background-color: #1a1a2e;
    }
    
    .step-active {
        border-left: 3px solid #f39c12;
    }
    
    .step-done {
        border-left: 3px solid #00b894;
    }
    
    .step-error {
        border-left: 3px solid #ff6b6b;
    }
    
    .feedback-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Initialize Session State
# =============================================================================

if "current_result" not in st.session_state:
    st.session_state.current_result = None

if "show_result" not in st.session_state:
    st.session_state.show_result = False

if "processing" not in st.session_state:
    st.session_state.processing = False

if "query_text" not in st.session_state:
    st.session_state.query_text = ""


# =============================================================================
# Load Agents (Cached)
# =============================================================================

@st.cache_resource
def load_agents():
    """Load all agents (cached for performance)."""
    logger.info("Loading agents...")
    
    from agents.query_decomposer import QueryDecomposer
    from agents.code_generator import CodeGenerator
    from agents.code_executor import CodeExecutor
    from agents.response_formatter import ResponseFormatter
    from agents.query_expander import QueryExpander
    
    agents = {
        "expander": QueryExpander(),
        "decomposer": QueryDecomposer(data_dir=Path("data")),
        "generator": CodeGenerator(),
        "executor": CodeExecutor(data_dir=Path("data")),
        "formatter": ResponseFormatter()
    }
    
    logger.info("All agents loaded successfully")
    return agents




# =============================================================================
# Query Processing with Live Updates
# =============================================================================

def process_query_with_live_updates(query: str, progress_container):
    """
    Process a query through the complete pipeline with live UI updates.
    """
    logger.info(f"=" * 60)
    logger.info(f"NEW QUERY: {query}")
    logger.info(f"=" * 60)
    
    agents = load_agents()
    
    result = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "stages": {},
        "success": False,
        "error": None,
        "answer": None
    }
    
    # Metadata containers for detailed logging
    expander_meta = None
    decomposer_meta = None
    generator_meta = None
    formatter_meta = None
    
    # Create main "Thinking" expander with placeholders for each stage inside
    with progress_container:
        thinking_expander = st.expander("Thinking...", expanded=False)
        with thinking_expander:
            stage0_placeholder = st.empty()
            stage0_detail = st.empty()
            stage1_placeholder = st.empty()
            stage1_detail = st.empty()
            stage2_placeholder = st.empty()
            stage2_detail = st.empty()
            stage3_placeholder = st.empty()
            stage3_detail = st.empty()
            stage4_placeholder = st.empty()
            stage4_detail = st.empty()
    
    # =========================================================================
    # Stage 1: Expand Query
    # =========================================================================
    stage0_placeholder.markdown("🔄 **Step 1: Expanding Query...**")
    logger.info("Stage 1: Expanding query...")
    
    try:
        expanded_query, expander_meta = agents["expander"].expand(query, return_metadata=True)
        result["stages"]["expand"] = {
            "success": True,
            "original": query,
            "expanded": expanded_query
        }
        
        logger.info(f"  ✓ Original: {query}")
        logger.info(f"  ✓ Expanded: {expanded_query[:100]}...")
        
        stage0_placeholder.markdown("✅ **Step 1: Query Expanded**")
        with stage0_detail.expander("View expanded query", expanded=False):
            st.markdown(f"**Original:** {query}")
            st.markdown(f"**Expanded:** {expanded_query}")
            
    except Exception as e:
        logger.error(f"  ✗ Expansion failed: {e}")
        result["stages"]["expand"] = {"success": False, "error": str(e)}
        # Don't fail - use original query
        expanded_query = query
        stage0_placeholder.markdown("⚠️ **Step 1: Using original query**")
        stage0_detail.warning(f"Expansion failed: {str(e)}")
    
    # =========================================================================
    # Stage 2: Decompose Query
    # =========================================================================
    stage1_placeholder.markdown("🔄 **Step 2: Analyzing Query...**")
    logger.info("Stage 2: Decomposing query...")
    
    try:
        decomposed, decomposer_meta = agents["decomposer"].decompose(expanded_query, return_metadata=True)
        result["stages"]["decompose"] = {
            "success": True,
            "data": decomposed.model_dump()
        }
        
        logger.info(f"  ✓ Query type: {decomposed.query_type.value}")
        logger.info(f"  ✓ Players: {[p.name for p in decomposed.players]}")
        logger.info(f"  ✓ Metrics: {[m.value for m in decomposed.metrics]}")
        
        stage1_placeholder.markdown("✅ **Step 2: Query Analyzed**")
        with stage1_detail.expander("View decomposed query", expanded=False):
            st.json(decomposed.model_dump())
            
    except Exception as e:
        logger.error(f"  ✗ Decomposition failed: {e}")
        result["stages"]["decompose"] = {"success": False, "error": str(e)}
        result["error"] = f"Failed to understand the query: {str(e)}"
        stage1_placeholder.markdown("❌ **Step 2: Failed to analyze query**")
        stage1_detail.error(str(e))
        
        # Log failure with available metadata
        log_interaction_to_db(query, result, expander_meta, decomposer_meta)
        log_query(query, result)
        return result
    
    # =========================================================================
    # Stage 3: Generate Code
    # =========================================================================
    stage2_placeholder.markdown("🔄 **Step 3: Generating Analysis Code...**")
    logger.info("Stage 3: Generating code...")
    
    try:
        # Use expanded_query for generation
        code, generator_meta = agents["generator"].generate(expanded_query, decomposed, return_metadata=True)
        result["stages"]["generate"] = {
            "success": True,
            "code": code
        }
        
        logger.info(f"  ✓ Generated {len(code.split(chr(10)))} lines of code")
        logger.debug(f"  Code:\n{code}")
        
        stage2_placeholder.markdown("✅ **Step 3: Code Generated**")
        with stage2_detail.expander("View generated code", expanded=False):
            st.code(code, language="python")
            
    except Exception as e:
        logger.error(f"  ✗ Code generation failed: {e}")
        result["stages"]["generate"] = {"success": False, "error": str(e)}
        result["error"] = f"Failed to generate analysis code: {str(e)}"
        stage2_placeholder.markdown("❌ **Step 3: Failed to generate code**")
        stage2_detail.error(str(e))
        
        # Log failure with available metadata
        log_interaction_to_db(query, result, expander_meta, decomposer_meta, generator_meta)
        log_query(query, result)
        return result
    
    # =========================================================================
    # Stage 4: Execute Code
    # =========================================================================
    stage3_placeholder.markdown("🔄 **Step 4: Running Analysis...**")
    logger.info("Stage 4: Executing code...")
    
    try:
        exec_result = agents["executor"].execute(code)
        
        if exec_result.success:
            result["stages"]["execute"] = {
                "success": True,
                "data": exec_result.result
            }
            logger.info(f"  ✓ Execution successful")
            logger.info(f"  ✓ Result type: {type(exec_result.result).__name__}")
            
            stage3_placeholder.markdown("✅ **Step 4: Analysis Complete**")
            with stage3_detail.expander("View raw results", expanded=False):
                st.json(exec_result.result)
        else:
            result["stages"]["execute"] = {
                "success": False,
                "error": exec_result.error
            }
            result["error"] = f"Code execution failed"
            
            logger.error(f"  ✗ Execution failed: {exec_result.error[:200]}")
            
            stage3_placeholder.markdown("❌ **Step 4: Execution Failed**")
            stage3_detail.error(exec_result.error)
            
            # Show the code that failed
            with stage3_detail.expander("Failed code (for debugging)"):
                st.code(code, language="python")
            
            # Log failure with available metadata
            log_interaction_to_db(query, result, expander_meta, decomposer_meta, generator_meta)
            log_query(query, result)
            return result
            
    except Exception as e:
        logger.error(f"  ✗ Execution error: {e}")
        result["stages"]["execute"] = {"success": False, "error": str(e)}
        result["error"] = f"Execution error: {str(e)}"
        
        stage3_placeholder.markdown("❌ **Step 4: Execution Error**")
        stage3_detail.error(str(e))
        
        # Show the code that failed
        with stage3_detail.expander("Failed code (for debugging)"):
            st.code(code, language="python")
        
        # Log failure with available metadata
        log_interaction_to_db(query, result, expander_meta, decomposer_meta, generator_meta)    
        log_query(query, result)
        return result
    
    # =========================================================================
    # Stage 5: Format Response
    # =========================================================================
    stage4_placeholder.markdown("🔄 **Step 5: Formatting Response...**")
    logger.info("Stage 5: Formatting response...")
    
    try:
        formatted, formatter_meta = agents["formatter"].format(query, decomposed, exec_result.result, return_metadata=True)
        result["stages"]["format"] = {
            "success": True,
            "data": {
                "summary": formatted.summary,
                "insights": formatted.insights,
                "tables": [t.model_dump() for t in formatted.tables],
                "follow_up_suggestions": formatted.follow_up_suggestions
            }
        }
        result["answer"] = result["stages"]["format"]["data"]
        result["success"] = True
        
        logger.info(f"  ✓ Response formatted successfully")
        logger.info(f"  ✓ Summary length: {len(formatted.summary)} chars")
        logger.info(f"  ✓ Insights: {len(formatted.insights)}")
        
        stage4_placeholder.markdown("✅ **Step 5: Response Ready**")
        
    except Exception as e:
        logger.warning(f"  ⚠ Formatting failed, using fallback: {e}")
        # Fallback: just show raw results
        result["stages"]["format"] = {"success": False, "error": str(e)}
        result["answer"] = {
            "summary": f"Here are the results: {json.dumps(exec_result.result, default=str)}",
            "insights": [],
            "tables": [],
            "follow_up_suggestions": []
        }
        result["success"] = True
        stage4_placeholder.markdown("⚠️ **Step 5: Using simplified format**")
    
    # Log the complete query to JSONL (legacy)
    log_query(query, result)
    
    # Log detailed interaction to SQLite
    try:
        log_interaction_to_db(
            query=query, 
            result_data=result,
            expander_data=expander_meta,
            decomposer_data=decomposer_meta,
            generator_data=generator_meta,
            formatter_data=formatter_meta
        )
        logger.info("Detailed interaction logged to database")
    except Exception as e:
        logger.error(f"Database logging failed: {e}")
        
    logger.info(f"Query completed successfully: {result['success']}")
    
    return result


def create_download_content(result: Dict[str, Any], include_reasoning: bool = True) -> str:
    """Create downloadable content from result."""
    content = {
        "query": result["query"],
        "timestamp": result["timestamp"],
        "success": result["success"],
    }
    
    if result["answer"]:
        content["answer"] = {
            "summary": result["answer"]["summary"],
            "insights": result["answer"]["insights"]
        }
    
    if result["error"]:
        content["error"] = result["error"]
    
    if include_reasoning:
        content["reasoning"] = {
            "decomposed_query": result["stages"].get("decompose", {}).get("data"),
            "generated_code": result["stages"].get("generate", {}).get("code"),
            "execution_result": result["stages"].get("execute", {}).get("data")
        }
    
    return json.dumps(content, indent=2, default=str)


# =============================================================================
# UI Components
# =============================================================================
@st.cache_data
def get_latest_match_info():
    """Get the most recent match info from the database."""
    try:
        import pandas as pd
        matches_df = pd.read_parquet(Path("data") / "matches.parquet")
        
        # Sort by date and get the most recent
        matches_df['match_date'] = pd.to_datetime(matches_df['match_date'])
        latest = matches_df.sort_values('match_date', ascending=False).iloc[0]
        
        match_date = latest['match_date'].strftime('%B %d, %Y')
        team1 = latest['team1']
        team2 = latest['team2']
        
        return {
            "date": match_date,
            "team1": team1,
            "team2": team2
        }
    except Exception as e:
        logger.warning(f"Could not get latest match info: {e}")
        return None

def render_header():
    """Render the header with contact info."""
    st.markdown('<h1 class="main-title">🏏 IPL Cricket Chatbot</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Ask anything about Indian Premier League statistics</p>', unsafe_allow_html=True)
        # Show latest match info
    latest_match = get_latest_match_info()
    if latest_match:
        st.markdown(f'''
        <p style="text-align: center; color: #666; font-size: 0.8rem; font-style: italic;">
            Database updated until {latest_match['date']}. Most recent match: {latest_match['team1']} vs {latest_match['team2']}
        </p>
        ''', unsafe_allow_html=True)
    
    st.markdown('''
    <p style="text-align: center; color: #888; font-size: 0.85rem;">
        Built by Tanish Taneja • 
        <a href="mailto:tanishtaneja1729@gmail.com" style="color: #a29bfe;"> tanishtaneja1729@gmail.com</a> • 
        <a href="https://x.com/taniiishh" target="_blank" style="color: #a29bfe;">𝕏 @taniiishh</a>
    </p>
    ''', unsafe_allow_html=True)


def render_footer():
    """Render the footer with contact info."""
    st.markdown("---")
    st.markdown('''
    <div style="text-align: center; color: #666; font-size: 0.8rem; padding: 1rem 0;">
        <p>
            <strong>IPL Cricket Chatbot</strong> • MVP Version
        </p>
        <p>
            For bug reports, feature requests, or general feedback:
        </p>
        <p>
            <a href="mailto:tanishtaneja1729@gmail.com" style="color: #a29bfe;">📧 tanishtaneja1729@gmail.com</a> • 
            <a href="https://x.com/taniiishh" target="_blank" style="color: #a29bfe;">𝕏 @taniiishh</a>
        </p>
        <p style="margin-top: 0.5rem; font-size: 0.75rem;">
            Data sourced from Cricsheet • Currently using gpt-oss-120b via HuggingFace
        </p>
    </div>
    ''', unsafe_allow_html=True)


def render_input():
    """Render the query input with form for Enter key support."""
    
    # Use a form so Enter key submits
    with st.form(key="query_form", clear_on_submit=False):
        col1, col2 = st.columns([5, 1])
        
        with col1:
            query = st.text_input(
                "Your question",
                value=st.session_state.query_text,
                placeholder="e.g., How many times has Virat Kohli scored more than 50 runs in a match?",
                label_visibility="collapsed",
                key="query_input"
            )
        
        with col2:
            submit = st.form_submit_button("Ask 🏏", use_container_width=True, type="primary")
    
    # Example queries as helpful text
    st.markdown("""
    <div style="color: #888; font-size: 0.9rem; margin-top: 0.5rem;">
        <strong>💡 Try asking:</strong>
        <em>Virat Kohli's batting stats in death overs</em> • 
        <em>Wickets taken by Jasprit Bumrah in powerplay</em> • 
        <em>Top 5 run scorers in IPL 2024</em>
    </div>
    """, unsafe_allow_html=True)
    
    if submit and query:
        st.session_state.query_text = query  # Store for display
        return query
    
    return None




def render_action_buttons(result: Dict[str, Any]):
    """Render save and reset buttons at the top after query completes."""
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        answer_content = create_download_content(result, include_reasoning=False)
        st.download_button(
            label="📥 Download Answer",
            data=answer_content,
            file_name=f"ipl_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            width="stretch"
        )
    
    with col2:
        full_content = create_download_content(result, include_reasoning=True)
        st.download_button(
            label="📥 Download Full Report",
            data=full_content,
            file_name=f"ipl_query_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            width="stretch"
        )
    
    with col3:
        if st.button("🔄 New Query", width="stretch"):
            st.session_state.current_result = None
            st.session_state.show_result = False
            st.session_state.query_text = ""  # Clear the input text
            st.rerun()


def render_results(result: Dict[str, Any]):
    """Render the final results."""
    
    st.markdown("---")
    
    if result["success"] and result["answer"]:
        # Success: Show answer
        st.markdown("### 📊 Answer")
        st.markdown(result["answer"]["summary"])
        
        # Insights
        if result["answer"]["insights"]:
            st.markdown("#### 💡 Key Insights")
            for insight in result["answer"]["insights"]:
                st.markdown(f'<div class="insight-item">{insight}</div>', unsafe_allow_html=True)
        
        # Tables
        if result["answer"]["tables"]:
            for table_data in result["answer"]["tables"]:
                st.markdown(f"**{table_data['title']}**")
                if table_data["rows"]:
                    import pandas as pd
                    df = pd.DataFrame(table_data["rows"], columns=table_data["columns"])
                    st.dataframe(df, width="stretch")
        
        if result["answer"]["follow_up_suggestions"]:
            st.markdown("#### 🔮 You might also ask:")
            for suggestion in result["answer"]["follow_up_suggestions"]:
                st.markdown(f"- {suggestion}")
    
    elif result["error"]:
        # Error case
        st.markdown("### ❌ Query Failed")
        st.error(result["error"])
        
        # Show code for debugging if available
        code = result.get("stages", {}).get("generate", {}).get("code")
        if code:
            with st.expander("View Generated Code (Debugging)", expanded=False):
                st.code(code, language="python")
    
    st.markdown("---")
    
    # Action buttons at the bottom
    render_action_buttons(result)


# =============================================================================
# Main App
# =============================================================================

def main():
    logger.info("App started")
    
    # Initialize Database
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    render_header()
    
    # Input section
    query = render_input()
    
    # Process query if submitted
    if query:
        logger.info(f"Processing query: {query}")
        st.session_state.last_query = query
        st.session_state.show_result = True
        
        # Create container for progress updates
        progress_container = st.container()
        
        # Process with live updates
        result = process_query_with_live_updates(query, progress_container)
        st.session_state.current_result = result
        
        # Show final results
        render_results(result)
    
    elif st.session_state.current_result and st.session_state.show_result:
        # Show previous result (but with the processing steps hidden)
        result = st.session_state.current_result
        
        # Show a simplified view of the progress
        st.markdown("---")
        with st.expander("📋 Processing Steps (completed)", expanded=False):
            for stage_name, stage_data in result.get("stages", {}).items():
                if stage_data.get("success"):
                    st.markdown(f"✅ {stage_name.title()}")
                else:
                    st.markdown(f"❌ {stage_name.title()}")
        
        render_results(result)
    
    else:
        # Empty state
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; padding: 3rem; color: #666;">
            <h3>👋 Welcome!</h3>
            <p>Ask any question about Indian Premier League cricket statistics.</p>
            <p>I can help you with player stats, team comparisons, match analysis, and more!</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Always show footer
    render_footer()


if __name__ == "__main__":
    main()
