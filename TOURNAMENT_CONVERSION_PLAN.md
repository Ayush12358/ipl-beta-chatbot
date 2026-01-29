# Tournament Conversion Plan

## Overview

This document provides a comprehensive, step-by-step guide for converting the WPL (Women's Premier League) Cricket Chatbot codebase to work with **any cricket tournament** (e.g., IPL, Big Bash League, The Hundred, PSL, etc.).

The codebase consists of:
1. **ETL Pipeline** (`etl_processor.py`) - Converts raw Cricsheet JSON data to Parquet files
2. **Agent System** (4 agents in `/agents/`)
   - `query_decomposer.py` - Parses natural language queries
   - `code_generator.py` - Generates Python/Pandas code
   - `code_executor.py` - Executes generated code safely
   - `response_formatter.py` - Formats results for display
3. **Web Interface** (`streamlit_app.py`) - Streamlit-based chatbot UI

---

## Phase 1: Data Preparation

### 1.1 Obtain Cricsheet Data

**Location**: Raw JSON files go in `Match Data JSON/` directory

**Steps**:
1. Download match data from [Cricsheet](https://cricsheet.org/) in JSON format
2. Select your tournament (e.g., IPL, Big Bash, etc.)
3. Place all `.json` files in `Match Data JSON/` directory
4. Delete any existing WPL JSON files from this directory

**Data Format**: Cricsheet provides standardized JSON format. No changes needed if using Cricsheet data.

---

### 1.2 Update ETL Processor (`etl_processor.py`)

The ETL processor transforms raw JSON into queryable Parquet files. **Key changes required**:

#### 1.2.1 Update Team Mappings (Lines 52-71)

Replace the WPL team data with your tournament's teams:

```python
# BEFORE (WPL):
def normalize_team_name(name: str) -> str:
    name_map = {
        "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    }
    return name_map.get(name, name)

def get_team_abbreviation(team_name: str) -> str:
    abbrev_map = {
        "Mumbai Indians": "MI",
        "Delhi Capitals": "DC",
        "Gujarat Giants": "GG",
        "UP Warriorz": "UPW",
        "Royal Challengers Bengaluru": "RCB",
    }
    return abbrev_map.get(team_name, team_name[:3].upper())

# AFTER (Example for IPL):
def normalize_team_name(name: str) -> str:
    name_map = {
        "Delhi Daredevils": "Delhi Capitals",  # Historical name change
        "Deccan Chargers": "Sunrisers Hyderabad",
        # Add any historical team name changes
    }
    return name_map.get(name, name)

def get_team_abbreviation(team_name: str) -> str:
    abbrev_map = {
        "Mumbai Indians": "MI",
        "Chennai Super Kings": "CSK",
        "Royal Challengers Bengaluru": "RCB",
        "Kolkata Knight Riders": "KKR",
        "Delhi Capitals": "DC",
        "Punjab Kings": "PBKS",
        "Rajasthan Royals": "RR",
        "Sunrisers Hyderabad": "SRH",
        "Gujarat Titans": "GT",
        "Lucknow Super Giants": "LSG",
    }
    return abbrev_map.get(team_name, team_name[:3].upper())
```

#### 1.2.2 Update Season Extraction (Lines 74-78)

Modify to match your tournament's naming convention:

```python
# BEFORE (WPL):
def extract_season_from_date(date_str: str) -> str:
    year = int(date_str.split("-")[0])
    return f"WPL {year}"

# AFTER (Example for IPL):
def extract_season_from_date(date_str: str) -> str:
    year = int(date_str.split("-")[0])
    return f"IPL {year}"
```

#### 1.2.3 Match Phase Boundaries (Lines 33-35)

For T20 tournaments, keep as-is. For different formats:

```python
# T20 (current):
POWERPLAY_END = 6    # Overs 1-6
DEATH_START = 15     # Overs 16-20

# For The Hundred (100 balls per innings):
POWERPLAY_END = 25   # First 25 balls (power surge)
DEATH_START = 85     # Last 15 balls

# For ODI:
POWERPLAY_END = 10   # Overs 1-10
DEATH_START = 40     # Overs 41-50
```

#### 1.2.4 Run ETL Pipeline

```bash
python etl_processor.py
```

This will generate:
- `data/teams.parquet`
- `data/venues.parquet`
- `data/players.parquet`
- `data/seasons.parquet`
- `data/matches.parquet`
- `data/ball_events.parquet`

---

### 1.3 Update Schema Reference (`data/schema_reference.md`)

After running ETL, update the schema reference document to reflect the new data:

1. Update row counts for each table
2. Update sample values (team names, player names, season names)
3. Update the table relationships if schema changes

---

## Phase 2: Agent Prompt Updates

### 2.1 Update Query Decomposer (`agents/query_decomposer.py`)

#### 2.1.1 Update Pydantic Models (Lines 27-143)

Modify enum values if your tournament uses different terminology:

```python
# Update QueryType if needed (usually no changes)
class QueryType(str, Enum):
    PLAYER_STATS = "player_stats"
    # ... keep existing types

# Update MetricType if needed (add tournament-specific metrics)
class MetricType(str, Enum):
    # Add any tournament-specific metrics
    SUPER_OVER = "super_over"  # if applicable
    
# Update MatchPhase for different formats
class MatchPhase(str, Enum):
    POWERPLAY = "powerplay"
    MIDDLE = "middle"
    DEATH = "death"
    ALL = "all"
    # Add for The Hundred:
    # POWER_SURGE = "power_surge"
```

#### 2.1.2 Update Entity Context Prompt (Lines 267-297)

Change the tournament name in the context generation:

```python
def get_prompt_context(self) -> str:
    context = """
## Available Entities in Database

### Teams ({team_count} teams in {tournament_name})  # <-- UPDATE
{teams}

### Seasons Available
{seasons}
...
"""
```

#### 2.1.3 Update System Prompt (Lines 378-443)

**CRITICAL CHANGES REQUIRED:**

```python
DECOMPOSER_SYSTEM_PROMPT = """You are a Cricket Query Decomposer for {TOURNAMENT_NAME} data analysis.
# Change "Women's Premier League (WPL)" to your tournament

Your job is to parse natural language cricket queries and extract structured information...

## Important Guidelines

1. **Player Names**: Based on the names extracted from the query...
2. **Team Names**: Use full team names (e.g., "{EXAMPLE_TEAM}", not "{ABBREV}")
3. **Phases**: 
   - "powerplay" = overs 1-6  # Adjust for your format
   - "middle overs" = overs 7-15
   - "death overs" = overs 16-20
4. **Seasons**: Use format "{SEASON_FORMAT}" (e.g., "{EXAMPLE_SEASON}")
...

## Example Output

For query "How did {EXAMPLE_PLAYER} perform in the {EXAMPLE_YEAR} powerplay vs {EXAMPLE_OPPONENT}?":
# Update all example values
```

**Changes to make:**
- Line 378: Change "Women's Premier League (WPL)" to your tournament name
- Line 386-390: Update example entity references
- Line 399-401: Update phase definitions for your format
- Line 405: Update season format
- Lines 416-439: Update the example output with relevant player/team names

---

### 2.2 Update Code Generator (`agents/code_generator.py`)

#### 2.2.1 Update System Prompt Header (Lines 42-48)

```python
CODE_GENERATOR_SYSTEM_PROMPT = '''You are a Python Code Generator for {TOURNAMENT_NAME} cricket data analysis.
# Change "Women's Premier League (WPL)" to your tournament

Your job is to write Python code using Pandas that answers cricket queries...
```

#### 2.2.2 Update Schema Documentation (Lines 50-131)

Update the sample values in the schema documentation to reflect your data:

```python
### ball_events (XX,XXX rows, 31 columns)  # Update row count
...
| `batting_team` | object | {Team1}, {Team2}, {Team3}... |
| `batting_team_id` | object | {abbrev1}, {abbrev2}, {abbrev3}... |
| `batter` | object | {Player1}, {Player2}... |
...

### matches (XX rows, 21 columns)  # Update row count
...
| `season` | object | {SEASON_1}, {SEASON_2}... |
```

#### 2.2.3 Update Example Patterns (Lines 149-196)

Update the example code snippets with your tournament's entities:

```python
### 2. Filtering Patterns

**Filter by player (batter):**
```python
player_balls = ball_events[ball_events['batter'] == '{EXAMPLE_PLAYER}']
```

**Filter by season (join with matches):**
```python
match_ids_2024 = matches[matches['season'] == '{SEASON_FORMAT} 2024']['match_id']
```

**Filter by opponent team:**
```python
vs_team = ball_events[ball_events['bowling_team'] == '{EXAMPLE_TEAM}']
```
```

---

### 2.3 Update Response Formatter (`agents/response_formatter.py`)

#### 2.3.1 Update System Prompt (Lines 54-121)

```python
FORMATTER_SYSTEM_PROMPT = '''You are a Cricket Statistics Commentator for {TOURNAMENT_NAME}.
# Change "Women's Premier League (WPL)" to your tournament

Your job is to take raw statistical data from cricket queries...
```

Also update the context benchmarks (Lines 91-94) if they differ for your tournament:

```python
2. **Provide Context**: Don't just state numbers - interpret them
   - Strike rate of 150+ is excellent (T20)  # Adjust for format
   - Economy under 6 is very good (T20)
   - 40% boundary percentage is high
```

---

## Phase 3: Website / UI Updates

### 3.1 Update Streamlit App (`streamlit_app.py`)

#### 3.1.1 Update Page Config (Lines 68-73)

```python
st.set_page_config(
    page_title="{TOURNAMENT_NAME} Cricket Chatbot",  # Update
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="collapsed"
)
```

#### 3.1.2 Update Header (Lines 415-425)

```python
def render_header():
    st.markdown('<h1 class="main-title">🏏 {TOURNAMENT_NAME} Cricket Chatbot</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Ask anything about {TOURNAMENT_NAME} statistics</p>', unsafe_allow_html=True)
    # Update contact info and attribution
```

#### 3.1.3 Update Footer (Lines 428-447)

```python
def render_footer():
    st.markdown("""
    <div style="...">
        <p><strong>{TOURNAMENT_NAME} Cricket Chatbot</strong> • MVP Version</p>
        <p style="...">Data sourced from Cricsheet • Currently using {MODEL_NAME}</p>
    </div>
    """, unsafe_allow_html=True)
```

#### 3.1.4 Update Example Queries (Lines 470-477)

```python
st.markdown("""
<div style="...">
    <strong>💡 Try asking:</strong>
    <em>{Example query 1 with tournament-relevant player}</em> • 
    <em>{Example query 2 with tournament-relevant team}</em> • 
    <em>{Example query 3 with tournament-relevant stat}</em>
</div>
""", unsafe_allow_html=True)
```

#### 3.1.5 Update Welcome Message (Lines 608-614)

```python
st.markdown("""
<div style="...">
    <h3>👋 Welcome!</h3>
    <p>Ask any question about {TOURNAMENT_NAME} cricket statistics.</p>
    <p>I can help you with player stats, team comparisons, match analysis, and more!</p>
</div>
""", unsafe_allow_html=True)
```

#### 3.1.6 Update Logging (Lines 42, 203-205)

```python
logger = logging.getLogger("{TOURNAMENT_ABBREV}_Chatbot")  # e.g., "IPL_Chatbot"

# Update log messages
logger.info(f"=" * 60)
logger.info(f"NEW QUERY: {query}")
```

---

## Phase 4: Configuration & Environment

### 4.1 Update Environment Variables (`.env`)

```env
# Keep API keys the same
OPENROUTER_API_KEY=your_key_here

# Optionally add tournament-specific config
TOURNAMENT_NAME=IPL
TOURNAMENT_FULL_NAME=Indian Premier League
```

### 4.2 Update README.md

Update the project description, installation instructions, and usage examples to reflect the new tournament.

### 4.3 Update Requirements (if needed)

The `requirements.txt` should remain the same unless you add new functionality.

---

## Phase 5: Testing & Validation

### 5.1 Test ETL Pipeline

```bash
python etl_processor.py
```

Verify:
- All expected teams appear in `teams.parquet`
- All seasons are correctly named
- Player names are correctly extracted
- Match counts align with expected data

### 5.2 Test Query Decomposer

```bash
cd agents && python query_decomposer.py
```

Test queries:
- Player-specific: "How many runs did {Player} score?"
- Team-specific: "What is {Team}'s win percentage?"
- Season-specific: "{SEASON} top scorers"
- Phase-specific: "Powerplay strike rates"

### 5.3 Test Code Generator

```bash
cd agents && python code_generator.py
```

Verify generated code:
- Uses correct column names
- References correct entities
- Produces valid Python

### 5.4 Test Full Pipeline

```bash
streamlit run streamlit_app.py
```

Run end-to-end tests with various query types.

---

## Quick Reference: Files to Modify

| File | Changes Required | Priority |
|------|-----------------|----------|
| `Match Data JSON/` | Replace with new tournament data | **REQUIRED** |
| `etl_processor.py` | Team mappings, season format, phase boundaries | **REQUIRED** |
| `data/schema_reference.md` | Update after ETL | **REQUIRED** |
| `agents/query_decomposer.py` | System prompt, examples, entity context | **REQUIRED** |
| `agents/code_generator.py` | System prompt, schema docs, examples | **REQUIRED** |
| `agents/response_formatter.py` | System prompt, context benchmarks | **REQUIRED** |
| `streamlit_app.py` | UI text, examples, branding | **REQUIRED** |
| `.env` | Tournament config (optional) | Optional |
| `README.md` | Documentation | Recommended |

---

## Appendix A: Checklist

### Data Preparation
- [ ] Download Cricsheet data for target tournament
- [ ] Place JSON files in `Match Data JSON/`
- [ ] Update `normalize_team_name()` in ETL
- [ ] Update `get_team_abbreviation()` in ETL
- [ ] Update `extract_season_from_date()` in ETL
- [ ] Update phase boundaries (if different format)
- [ ] Run `python etl_processor.py`
- [ ] Verify generated Parquet files
- [ ] Update `data/schema_reference.md`

### Agent Updates
- [ ] Update `query_decomposer.py` system prompt
- [ ] Update entity context generation
- [ ] Update example outputs in decomposer
- [ ] Update `code_generator.py` system prompt
- [ ] Update schema documentation in code generator
- [ ] Update example code snippets
- [ ] Update `response_formatter.py` system prompt

### UI Updates
- [ ] Update page title and icon
- [ ] Update header with tournament name
- [ ] Update footer with attribution
- [ ] Update example queries
- [ ] Update welcome message
- [ ] Update logger name

### Testing
- [ ] Test ETL pipeline
- [ ] Test query decomposer with sample queries
- [ ] Test code generator
- [ ] Test code executor
- [ ] Test response formatter
- [ ] End-to-end testing via Streamlit app

---

## Appendix B: Common Issues

### Issue: Player names not matching
**Cause**: Cricsheet uses different name formats across different tournaments
**Solution**: Check `players.parquet` for actual name format, update prompts accordingly

### Issue: Season format incorrect
**Cause**: Different tournaments may use different season naming
**Solution**: Update `extract_season_from_date()` and all prompt examples

### Issue: Phase calculations wrong
**Cause**: Different formats (T20/ODI/The Hundred) have different phase definitions
**Solution**: Update `POWERPLAY_END` and `DEATH_START` constants

### Issue: Code generator produces errors
**Cause**: Schema documentation in prompts doesn't match actual data
**Solution**: Regenerate `schema_reference.md` and update code generator prompt

---

## Appendix C: Tournament-Specific Considerations

### For T20 Leagues (IPL, BBL, PSL, CPL)
- Phase definitions remain the same
- Team abbreviations need updating
- Player name formats vary by league

### For The Hundred
- Change from "overs" to "balls" terminology
- Redefine phases based on 100-ball format
- Update metric calculations

### For ODI Tournaments (World Cup)
- Extend phase definitions for 50 overs
- Add ODI-specific metrics (50s, maiden overs)
- Consider match types (group stage, knockout)

### For Test Matches
- Completely different metrics (sessions, days)
- No phases in traditional sense
- First/second innings per team
- Significant prompt restructuring required