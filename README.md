# 🏏 WPL Cricket Chatbot (V0)

An AI-powered chatbot for Women's Premier League (WPL) cricket statistics and analysis.

## Features

- **Natural Language Queries**: Ask questions about WPL statistics in plain English
- **Player Statistics**: Get detailed batting and bowling stats for any player
- **Match Analysis**: Analyze performances across different match phases (powerplay, middle overs, death overs)
- **AI-Powered Insights**: Intelligent code generation and response formatting

## 🚀 Live Demo

_This section will be updated after deployment._

## 🛠️ Tech Stack (currently, just MVP)

- **Frontend**: Streamlit
- **Backend**: Python with Pandas
- **LLM**: Gemma 3, using Hugging Face
- **Data**: WPL Ball-by-Ball data from Cricsheet

## 📦 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/wpl-cricket-chatbot.git
   cd wpl-cricket-chatbot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

5. Run the app:
   ```bash
   streamlit run streamlit_app.py
   ```

## 🔑 Environment Variables

Create a `.env` file with the following variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `HF_API_KEY` | HuggingFace access token for LLM inference ([Get one here](https://huggingface.co/settings/tokens)) | ✅ Yes (unless using Gemini) |
| `GEMINI_API_KEY` | Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey)) | ✅ Yes (if using Gemini) |
| `LLM_PROVIDER` | Set to `gemini` to use Gemini by default | ❌ No |

## 📁 Project Structure

```
wpl/
├── streamlit_app.py      # Main Streamlit application
├── api.py                # FastAPI backend (optional)
├── requirements.txt      # Python dependencies
├── agents/               # AI agents for query processing
│   ├── query_decomposer.py
│   ├── code_generator.py
│   ├── code_executor.py
│   └── response_formatter.py
├── data/                 # Data files
└── Match Data JSON/      # Raw match data
```

## 🤔 Example Queries

- "Smriti Mandhana's batting stats in middle overs"
- "Wickets taken by Marizanne Kapp in powerplay"
- "Top 5 run scorers in WPL 2024"
- "How many times has Ellyse Perry scored 30 runs and taken 1 wicket?"