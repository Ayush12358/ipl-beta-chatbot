"""
WPL Cricket Chatbot API
========================
FastAPI server with step-by-step progress tracking.

Run locally:
    uvicorn api:app --reload --port 8000
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import asyncio

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent / "agents"))

# Load environment
load_dotenv()

# =============================================================================
# App Setup
# =============================================================================

app = FastAPI(
    title="WPL Cricket Chatbot API",
    description="Ask questions about Women's Premier League cricket statistics",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Models
# =============================================================================

class QueryRequest(BaseModel):
    query: str


class StepResponse(BaseModel):
    step: str
    status: str  # "started", "completed", "error"
    data: Optional[dict] = None
    error: Optional[str] = None


# =============================================================================
# Global Instances (lazy loaded)
# =============================================================================

_decomposer = None
_generator = None
_executor = None
_formatter = None


def get_decomposer():
    global _decomposer
    if _decomposer is None:
        from query_decomposer import QueryDecomposer
        _decomposer = QueryDecomposer(data_dir=Path("data"))
    return _decomposer


def get_generator():
    global _generator
    if _generator is None:
        from code_generator import CodeGenerator
        _generator = CodeGenerator()
    return _generator


def get_executor():
    global _executor
    if _executor is None:
        from code_executor import CodeExecutor
        _executor = CodeExecutor(data_dir=Path("data"))
    return _executor


def get_formatter():
    global _formatter
    if _formatter is None:
        from response_formatter import ResponseFormatter
        _formatter = ResponseFormatter()
    return _formatter


# =============================================================================
# Streaming Response Generator
# =============================================================================

async def process_query_stream(query: str):
    """Process query and yield step-by-step updates."""
    
    # Step 1: Decomposing
    yield json.dumps({
        "step": "decompose",
        "status": "started",
        "message": "Analyzing your query..."
    }) + "\n"
    
    try:
        decomposer = get_decomposer()
        decomposed = decomposer.decompose(query)
        
        yield json.dumps({
            "step": "decompose",
            "status": "completed",
            "data": {
                "query_type": decomposed.query_type.value,
                "players": [p.name for p in decomposed.players],
                "teams": [t.name for t in decomposed.teams],
                "phase": decomposed.phase.value,
                "seasons": decomposed.season_filter.seasons,
                "metrics": [m.value for m in decomposed.metrics],
                "full_json": decomposed.model_dump()
            }
        }) + "\n"
        
    except Exception as e:
        yield json.dumps({
            "step": "decompose",
            "status": "error",
            "error": str(e)
        }) + "\n"
        return
    
    await asyncio.sleep(0.1)  # Small delay for UI
    
    # Step 2: Generating Code
    yield json.dumps({
        "step": "generate",
        "status": "started",
        "message": "Generating Python code..."
    }) + "\n"
    
    try:
        generator = get_generator()
        code = generator.generate(query, decomposed)
        
        yield json.dumps({
            "step": "generate",
            "status": "completed",
            "data": {
                "code": code,
                "lines": len(code.split("\n"))
            }
        }) + "\n"
        
    except Exception as e:
        yield json.dumps({
            "step": "generate",
            "status": "error",
            "error": str(e)
        }) + "\n"
        return
    
    await asyncio.sleep(0.1)
    
    # Step 3: Executing Code
    yield json.dumps({
        "step": "execute",
        "status": "started",
        "message": "Running analysis..."
    }) + "\n"
    
    try:
        executor = get_executor()
        result = executor.execute(code)
        
        if result.success:
            yield json.dumps({
                "step": "execute",
                "status": "completed",
                "data": {
                    "result": result.result
                }
            }) + "\n"
        else:
            yield json.dumps({
                "step": "execute",
                "status": "error",
                "error": result.error
            }) + "\n"
            return
            
    except Exception as e:
        yield json.dumps({
            "step": "execute",
            "status": "error",
            "error": str(e)
        }) + "\n"
        return
    
    await asyncio.sleep(0.1)
    
    # Step 4: Formatting Response
    yield json.dumps({
        "step": "format",
        "status": "started",
        "message": "Preparing your answer..."
    }) + "\n"
    
    try:
        formatter = get_formatter()
        formatted = formatter.format(query, decomposed, result.result)
        
        yield json.dumps({
            "step": "format",
            "status": "completed",
            "data": {
                "summary": formatted.summary,
                "insights": formatted.insights,
                "tables": [t.model_dump() for t in formatted.tables],
                "follow_up_suggestions": formatted.follow_up_suggestions
            }
        }) + "\n"
        
    except Exception as e:
        # Fallback to simple formatting
        yield json.dumps({
            "step": "format",
            "status": "completed",
            "data": {
                "summary": f"Here are the results: {json.dumps(result.result, default=str)}",
                "insights": [],
                "tables": [],
                "follow_up_suggestions": []
            }
        }) + "\n"
    
    # Done
    yield json.dumps({
        "step": "done",
        "status": "completed"
    }) + "\n"


# =============================================================================
# Endpoints
# =============================================================================

@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """Stream query processing steps."""
    return StreamingResponse(
        process_query_stream(request.query),
        media_type="application/x-ndjson"
    )


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the chatbot UI."""
    return HTML_CONTENT


# =============================================================================
# HTML/CSS/JS UI
# =============================================================================

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WPL Cricket Chatbot</title>
    <style>
        :root {
            --bg-primary: #0f0f1a;
            --bg-secondary: #1a1a2e;
            --bg-tertiary: #252540;
            --accent: #6c5ce7;
            --accent-light: #a29bfe;
            --text-primary: #ffffff;
            --text-secondary: #b0b0c0;
            --success: #00b894;
            --error: #ff6b6b;
            --border: #3d3d5c;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 30px;
        }
        
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, var(--accent), var(--accent-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }
        
        /* Input Section */
        .input-section {
            background: var(--bg-secondary);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid var(--border);
        }
        
        .input-wrapper {
            display: flex;
            gap: 12px;
        }
        
        #query-input {
            flex: 1;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
            font-size: 1rem;
            color: var(--text-primary);
            transition: border-color 0.3s, box-shadow 0.3s;
        }
        
        #query-input:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.2);
        }
        
        #query-input::placeholder {
            color: var(--text-secondary);
        }
        
        #submit-btn {
            background: linear-gradient(135deg, var(--accent), var(--accent-light));
            border: none;
            border-radius: 12px;
            padding: 16px 32px;
            font-size: 1rem;
            font-weight: 600;
            color: white;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        #submit-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(108, 92, 231, 0.4);
        }
        
        #submit-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        /* Thinking Section */
        .thinking-section {
            display: none;
            margin-bottom: 24px;
        }
        
        .thinking-section.active {
            display: block;
        }
        
        .thinking-dropdown {
            background: var(--bg-secondary);
            border-radius: 16px;
            border: 1px solid var(--border);
            overflow: hidden;
        }
        
        .thinking-header {
            padding: 20px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            user-select: none;
        }
        
        .thinking-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 600;
        }
        
        .spinner {
            width: 24px;
            height: 24px;
            border: 3px solid var(--bg-tertiary);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .thinking-toggle {
            font-size: 1.2rem;
            color: var(--text-secondary);
            transition: transform 0.3s;
        }
        
        .thinking-dropdown.expanded .thinking-toggle {
            transform: rotate(180deg);
        }
        
        .thinking-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }
        
        .thinking-dropdown.expanded .thinking-content {
            max-height: 2000px;
        }
        
        .step-container {
            padding: 0 24px 24px;
        }
        
        .step {
            padding: 16px;
            background: var(--bg-tertiary);
            border-radius: 12px;
            margin-bottom: 12px;
            border-left: 4px solid var(--border);
            transition: border-color 0.3s;
        }
        
        .step.active {
            border-left-color: var(--accent);
        }
        
        .step.completed {
            border-left-color: var(--success);
        }
        
        .step.error {
            border-left-color: var(--error);
        }
        
        .step-header {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .step-icon {
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .step-icon.loading {
            width: 16px;
            height: 16px;
            border: 2px solid var(--bg-primary);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        .step-content {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        
        .code-block {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 16px;
            margin-top: 12px;
            overflow-x: auto;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.85rem;
            line-height: 1.6;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .json-block {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 16px;
            margin-top: 12px;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }
        
        /* Answer Section */
        .answer-section {
            display: none;
            background: var(--bg-secondary);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid var(--border);
        }
        
        .answer-section.active {
            display: block;
        }
        
        .answer-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--accent-light);
        }
        
        .answer-summary {
            font-size: 1.1rem;
            line-height: 1.8;
            margin-bottom: 24px;
        }
        
        .insights-section {
            margin-bottom: 24px;
        }
        
        .insights-title {
            font-weight: 600;
            margin-bottom: 12px;
            color: var(--accent-light);
        }
        
        .insight-item {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 10px 0;
            color: var(--text-secondary);
        }
        
        .insight-bullet {
            color: var(--success);
            font-size: 1.2rem;
        }
        
        /* Tables */
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            background: var(--bg-tertiary);
            border-radius: 12px;
            overflow: hidden;
        }
        
        .data-table caption {
            padding: 12px;
            font-weight: 600;
            text-align: left;
            background: var(--bg-primary);
        }
        
        .data-table th,
        .data-table td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        
        .data-table th {
            background: var(--bg-primary);
            font-weight: 600;
            color: var(--accent-light);
        }
        
        .data-table tr:last-child td {
            border-bottom: none;
        }
        
        /* Follow-up Suggestions */
        .suggestions {
            margin-top: 24px;
            padding-top: 24px;
            border-top: 1px solid var(--border);
        }
        
        .suggestions-title {
            font-weight: 600;
            margin-bottom: 12px;
            color: var(--text-secondary);
        }
        
        .suggestion-chip {
            display: inline-block;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 8px 16px;
            margin: 4px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .suggestion-chip:hover {
            border-color: var(--accent);
            background: rgba(108, 92, 231, 0.1);
        }
        
        /* Example Queries */
        .examples {
            margin-top: 16px;
        }
        
        .examples-title {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }
        
        .example-chip {
            display: inline-block;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 8px 12px;
            margin: 4px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .example-chip:hover {
            border-color: var(--accent);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏏 WPL Cricket Chatbot</h1>
            <p class="subtitle">Ask anything about Women's Premier League statistics</p>
        </header>
        
        <div class="input-section">
            <div class="input-wrapper">
                <input 
                    type="text" 
                    id="query-input" 
                    placeholder="e.g., How did Harmanpreet perform in the powerplay?" 
                    autocomplete="off"
                />
                <button id="submit-btn">Ask</button>
            </div>
            <div class="examples">
                <p class="examples-title">Try these:</p>
                <span class="example-chip" onclick="setQuery(this.textContent)">Smriti Mandhana's strike rate in powerplay</span>
                <span class="example-chip" onclick="setQuery(this.textContent)">Top 5 six hitters in WPL 2024</span>
                <span class="example-chip" onclick="setQuery(this.textContent)">MI vs DC head to head</span>
            </div>
        </div>
        
        <div class="thinking-section" id="thinking-section">
            <div class="thinking-dropdown" id="thinking-dropdown">
                <div class="thinking-header" onclick="toggleThinking()">
                    <div class="thinking-title">
                        <div class="spinner" id="main-spinner"></div>
                        <span id="thinking-status">Thinking...</span>
                    </div>
                    <span class="thinking-toggle">▼</span>
                </div>
                <div class="thinking-content">
                    <div class="step-container">
                        <div class="step" id="step-decompose">
                            <div class="step-header">
                                <span class="step-icon" id="icon-decompose">1</span>
                                <span>Analyzing Query</span>
                            </div>
                            <div class="step-content" id="content-decompose">Waiting...</div>
                        </div>
                        
                        <div class="step" id="step-generate">
                            <div class="step-header">
                                <span class="step-icon" id="icon-generate">2</span>
                                <span>Generating Code</span>
                            </div>
                            <div class="step-content" id="content-generate">Waiting...</div>
                        </div>
                        
                        <div class="step" id="step-execute">
                            <div class="step-header">
                                <span class="step-icon" id="icon-execute">3</span>
                                <span>Running Analysis</span>
                            </div>
                            <div class="step-content" id="content-execute">Waiting...</div>
                        </div>
                        
                        <div class="step" id="step-format">
                            <div class="step-header">
                                <span class="step-icon" id="icon-format">4</span>
                                <span>Formatting Response</span>
                            </div>
                            <div class="step-content" id="content-format">Waiting...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="answer-section" id="answer-section">
            <div class="answer-title">📊 Answer</div>
            <div class="answer-summary" id="answer-summary"></div>
            
            <div class="insights-section" id="insights-section" style="display: none;">
                <div class="insights-title">💡 Key Insights</div>
                <div id="insights-list"></div>
            </div>
            
            <div id="tables-container"></div>
            
            <div class="suggestions" id="suggestions-section" style="display: none;">
                <div class="suggestions-title">🔮 You might also want to ask:</div>
                <div id="suggestions-list"></div>
            </div>
        </div>
    </div>
    
    <script>
        const queryInput = document.getElementById('query-input');
        const submitBtn = document.getElementById('submit-btn');
        const thinkingSection = document.getElementById('thinking-section');
        const thinkingDropdown = document.getElementById('thinking-dropdown');
        const answerSection = document.getElementById('answer-section');
        
        function setQuery(text) {
            queryInput.value = text;
            queryInput.focus();
        }
        
        function toggleThinking() {
            thinkingDropdown.classList.toggle('expanded');
        }
        
        function resetSteps() {
            ['decompose', 'generate', 'execute', 'format'].forEach(step => {
                document.getElementById(`step-${step}`).className = 'step';
                document.getElementById(`icon-${step}`).className = 'step-icon';
                document.getElementById(`icon-${step}`).innerHTML = step === 'decompose' ? '1' : 
                    step === 'generate' ? '2' : step === 'execute' ? '3' : '4';
                document.getElementById(`content-${step}`).innerHTML = 'Waiting...';
            });
            
            answerSection.classList.remove('active');
            document.getElementById('insights-section').style.display = 'none';
            document.getElementById('suggestions-section').style.display = 'none';
            document.getElementById('tables-container').innerHTML = '';
        }
        
        function updateStep(step, status, data = null, error = null) {
            const stepEl = document.getElementById(`step-${step}`);
            const iconEl = document.getElementById(`icon-${step}`);
            const contentEl = document.getElementById(`content-${step}`);
            
            stepEl.className = 'step';
            
            if (status === 'started') {
                stepEl.classList.add('active');
                iconEl.className = 'step-icon loading';
                iconEl.innerHTML = '';
                contentEl.innerHTML = data?.message || 'Processing...';
            } else if (status === 'completed') {
                stepEl.classList.add('completed');
                iconEl.className = 'step-icon';
                iconEl.innerHTML = '✓';
                
                if (step === 'decompose' && data) {
                    contentEl.innerHTML = `
                        <strong>Type:</strong> ${data.query_type}<br>
                        <strong>Players:</strong> ${data.players.join(', ') || 'None'}<br>
                        <strong>Phase:</strong> ${data.phase}<br>
                        <strong>Metrics:</strong> ${data.metrics.join(', ')}
                        <div class="json-block">${JSON.stringify(data.full_json, null, 2)}</div>
                    `;
                } else if (step === 'generate' && data) {
                    contentEl.innerHTML = `
                        Generated ${data.lines} lines of Python code
                        <div class="code-block"><pre>${escapeHtml(data.code)}</pre></div>
                    `;
                } else if (step === 'execute' && data) {
                    contentEl.innerHTML = `
                        Analysis complete
                        <div class="json-block">${JSON.stringify(data.result, null, 2)}</div>
                    `;
                } else if (step === 'format') {
                    contentEl.innerHTML = 'Response ready!';
                }
            } else if (status === 'error') {
                stepEl.classList.add('error');
                iconEl.className = 'step-icon';
                iconEl.innerHTML = '✗';
                contentEl.innerHTML = `<span style="color: var(--error)">Error: ${error}</span>`;
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function showAnswer(data) {
            answerSection.classList.add('active');
            document.getElementById('answer-summary').innerHTML = data.summary;
            
            // Insights
            if (data.insights && data.insights.length > 0) {
                document.getElementById('insights-section').style.display = 'block';
                document.getElementById('insights-list').innerHTML = data.insights
                    .map(i => `<div class="insight-item"><span class="insight-bullet">•</span>${i}</div>`)
                    .join('');
            }
            
            // Tables
            if (data.tables && data.tables.length > 0) {
                document.getElementById('tables-container').innerHTML = data.tables
                    .map(t => createTable(t))
                    .join('');
            }
            
            // Suggestions
            if (data.follow_up_suggestions && data.follow_up_suggestions.length > 0) {
                document.getElementById('suggestions-section').style.display = 'block';
                document.getElementById('suggestions-list').innerHTML = data.follow_up_suggestions
                    .map(s => `<span class="suggestion-chip" onclick="setQuery('${s}')">${s}</span>`)
                    .join('');
            }
        }
        
        function createTable(tableData) {
            let html = `<table class="data-table">`;
            if (tableData.title) {
                html += `<caption>${tableData.title}</caption>`;
            }
            html += `<thead><tr>${tableData.columns.map(c => `<th>${c}</th>`).join('')}</tr></thead>`;
            html += `<tbody>`;
            tableData.rows.forEach(row => {
                html += `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`;
            });
            html += `</tbody></table>`;
            return html;
        }
        
        async function submitQuery() {
            const query = queryInput.value.trim();
            if (!query) return;
            
            // Reset and show thinking
            resetSteps();
            thinkingSection.classList.add('active');
            thinkingDropdown.classList.add('expanded');
            submitBtn.disabled = true;
            document.getElementById('main-spinner').style.display = 'block';
            document.getElementById('thinking-status').textContent = 'Thinking...';
            
            try {
                const response = await fetch('/query/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query })
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const lines = decoder.decode(value).split('\\n').filter(l => l.trim());
                    
                    for (const line of lines) {
                        try {
                            const data = JSON.parse(line);
                            
                            if (data.step === 'done') {
                                document.getElementById('main-spinner').style.display = 'none';
                                document.getElementById('thinking-status').textContent = 'Complete!';
                            } else if (data.step === 'format' && data.status === 'completed') {
                                showAnswer(data.data);
                            }
                            
                            updateStep(data.step, data.status, data.data, data.error);
                            
                        } catch (e) {
                            console.error('Parse error:', e);
                        }
                    }
                }
                
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('main-spinner').style.display = 'none';
                document.getElementById('thinking-status').textContent = 'Error occurred';
            } finally {
                submitBtn.disabled = false;
            }
        }
        
        // Event listeners
        submitBtn.addEventListener('click', submitQuery);
        queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') submitQuery();
        });
        
        // Expand thinking by default
        thinkingDropdown.classList.add('expanded');
    </script>
</body>
</html>
"""


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
