"""
Query Decomposer Agent
=======================
Extracts structured intent from natural language cricket queries.

Uses Pydantic for structured output validation and includes
entity lists (teams, players, venues, seasons) in the prompt context.
"""

import os
import json
from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# =============================================================================
# Pydantic Models for Structured Query Output
# =============================================================================

class QueryType(str, Enum):
    """Types of queries the system can handle."""
    PLAYER_STATS = "player_stats"           # Individual player performance
    PLAYER_VS_PLAYER = "player_vs_player"   # Batter vs bowler matchup
    PLAYER_VS_TEAM = "player_vs_team"       # Batter vs team matchup
    TEAM_STATS = "team_stats"               # Team-level statistics
    TEAM_VS_TEAM = "team_vs_team"           # Head-to-head team comparison
    MATCH_QUERY = "match_query"             # Specific match information
    LEADERBOARD = "leaderboard"             # Top N rankings
    COMPARISON = "comparison"               # Compare multiple entities
    TREND = "trend"                         # Performance over time
    VENUE_STATS = "venue_stats"             # Venue-specific statistics


class MetricType(str, Enum):
    """Cricket metrics that can be calculated."""
    # Batting metrics
    RUNS = "runs"
    BALLS_FACED = "balls_faced"
    STRIKE_RATE = "strike_rate"
    AVERAGE = "average"
    FOURS = "fours"
    SIXES = "sixes"
    BOUNDARIES = "boundaries"
    BOUNDARY_PERCENTAGE = "boundary_percentage"
    DOT_PERCENTAGE = "dot_percentage"
    
    # Bowling metrics
    WICKETS = "wickets"
    BALLS_BOWLED = "balls_bowled"
    RUNS_CONCEDED = "runs_conceded"
    ECONOMY = "economy"
    BOWLING_AVERAGE = "bowling_average"
    BOWLING_STRIKE_RATE = "bowling_strike_rate"
    DOT_BALLS = "dot_balls"
    MAIDENS = "maidens"
    
    # Match/Team metrics
    WINS = "wins"
    LOSSES = "losses"
    WIN_PERCENTAGE = "win_percentage"
    TOTAL_SCORE = "total_score"


class MatchPhase(str, Enum):
    """Phases of a T20 match."""
    POWERPLAY = "powerplay"     # Overs 1-6 (0-5 in 0-indexed)
    MIDDLE = "middle"           # Overs 7-15 (6-14 in 0-indexed)
    DEATH = "death"             # Overs 16-20 (15-19 in 0-indexed)
    ALL = "all"                 # All phases


class PlayerFilter(BaseModel):
    """Filter criteria for a specific player."""
    name: str = Field(description="Player name as mentioned in query (use abbreviated format like 'H Kaur' for Harmanpreet Kaur)")
    role: Optional[Literal["batter", "bowler", "all_rounder", "any"]] = Field(
        default="any",
        description="Role context: are we looking at batting or bowling stats?"
    )


class TeamFilter(BaseModel):
    """Filter criteria for a team."""
    name: str = Field(description="Full team name (e.g., 'Mumbai Indians', not 'MI')")
    context: Optional[Literal["batting", "bowling", "fielding", "overall"]] = Field(
        default="overall",
        description="Context of team analysis"
    )


class SeasonFilter(BaseModel):
    """Filter for specific season(s)."""
    seasons: List[str] = Field(
        default_factory=list,
        description="List of seasons mentioned in format 'IPL 20XX' (e.g., ['IPL 2024', 'IPL 2023'])"
    )


class VenueFilter(BaseModel):
    """Filter for specific venue(s)."""
    venues: List[str] = Field(
        default_factory=list,
        description="Venue names mentioned in query"
    )
    cities: List[str] = Field(
        default_factory=list,
        description="City names mentioned (will map to venues)"
    )


class InningsFilter(BaseModel):
    """Filter for innings context."""
    innings_number: Optional[Literal[1, 2]] = Field(
        default=None,
        description="1 for batting first, 2 for chasing"
    )
    batting_first: Optional[bool] = Field(
        default=None,
        description="True if asking about batting first scenarios"
    )
    chasing: Optional[bool] = Field(
        default=None,
        description="True if asking about chasing scenarios"
    )


class AggregationType(str, Enum):
    """How to aggregate the results."""
    TOTAL = "total"             # Sum/aggregate across all matches
    PER_MATCH = "per_match"     # Show per-match breakdown
    PER_INNINGS = "per_innings" # Show per-innings breakdown
    PER_SEASON = "per_season"   # Group by season


class SortOrder(str, Enum):
    """Sort order for results."""
    ASCENDING = "asc"
    DESCENDING = "desc"


class DecomposedQuery(BaseModel):
    """
    Complete structured representation of a cricket query.
    This is the output of the Query Decomposer agent.
    """
    
    # Query classification
    query_type: QueryType = Field(
        description="Primary type/intent of the query"
    )
    original_query: str = Field(
        description="The original natural language query"
    )
    
    # Entity filters
    players: List[PlayerFilter] = Field(
        default_factory=list,
        description="Players mentioned in the query"
    )
    teams: List[TeamFilter] = Field(
        default_factory=list,
        description="Teams mentioned in the query"
    )
    
    # Opponent/matchup context
    opponent_players: List[PlayerFilter] = Field(
        default_factory=list,
        description="Opponent players (for vs matchups)"
    )
    opponent_teams: List[TeamFilter] = Field(
        default_factory=list,
        description="Opponent teams (for vs matchups)"
    )
    
    # Contextual filters
    phase: MatchPhase = Field(
        default=MatchPhase.ALL,
        description="Match phase filter (powerplay/middle/death/all)"
    )
    season_filter: SeasonFilter = Field(
        default_factory=SeasonFilter,
        description="Season/time period filter"
    )
    venue_filter: VenueFilter = Field(
        default_factory=VenueFilter,
        description="Venue/location filter"
    )
    innings_filter: InningsFilter = Field(
        default_factory=InningsFilter,
        description="Innings context filter"
    )
    
    # Metrics to calculate
    metrics: List[MetricType] = Field(
        default_factory=list,
        description="Metrics to calculate/return"
    )
    primary_metric: Optional[MetricType] = Field(
        default=None,
        description="Main metric for ranking/comparison"
    )
    
    # Result formatting
    aggregation: AggregationType = Field(
        default=AggregationType.TOTAL,
        description="How to aggregate results"
    )
    limit: Optional[int] = Field(
        default=None,
        description="Limit on results (for top N queries)"
    )
    sort_by: Optional[MetricType] = Field(
        default=None,
        description="Metric to sort by"
    )
    sort_order: SortOrder = Field(
        default=SortOrder.DESCENDING,
        description="Sort order"
    )
    
    # Additional context
    requires_comparison: bool = Field(
        default=False,
        description="Does the query ask for comparison between entities?"
    )
    time_trend: bool = Field(
        default=False,
        description="Does the query ask for trend/progression over time?"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Any additional notes or ambiguities in understanding the query"
    )


from .entity_linker import EntityLinker
from .llm_client import get_llm_client
from .config import AGENT_MODELS
from .prompts import DECOMPOSER_SYSTEM_PROMPT

def call_decomposer_llm(messages, model=None):
    """
    Traced LLM call specifically for query decomposition.
    """
    if model is None:
        model = AGENT_MODELS["decomposer"]
    
    client = get_llm_client()
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=1.0,
    )
    return completion


# =============================================================================
# Query Decomposer Agent
# =============================================================================

class QueryDecomposer:
    """Agent that decomposes natural language queries into structured format."""
    
    def __init__(self, data_dir: Path = Path("data"), model: str = None):
        self.entity_linker = EntityLinker(data_dir)
        self.model = model or AGENT_MODELS["decomposer"]
        
        # Build system prompt with schema
        schema_json = json.dumps(DecomposedQuery.model_json_schema(), indent=2)
        self.system_prompt = DECOMPOSER_SYSTEM_PROMPT.format(
            schema=schema_json
        )
    
    def get_system_prompt(self) -> str:
        """Get the full system prompt (for debugging)."""
        return self.system_prompt
    
    def decompose(self, query: str, return_metadata: bool = False):
        """
        Decompose a natural language query into structured format.
        
        Args:
            query: Natural language query string
            return_metadata: If True, returns (DecomposedQuery, metadata_dict)
        
        Returns:
            DecomposedQuery object (or tuple if return_metadata=True)
        """
        from pydantic import ValidationError
        
        user_message = f"Decompose this cricket query into structured JSON:\n\n{query}"
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        completion = None
        try:
            # Get LLM response
            completion = call_decomposer_llm(messages, model=self.model)
            response_text = completion.choices[0].message.content
            if not response_text:
                 raise ValueError("Received empty response from LLM")
        except Exception as e:
             raise RuntimeError(f"Decomposition LLM call failed: {str(e)}") from e
        
        # Parse JSON response
        response_json = None
        try:
            # Clean response if needed (remove markdown code blocks)
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                # Handle ```json or just ```
                parts = cleaned.split("```")
                if len(parts) >= 2:
                    cleaned = parts[1]
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:]
                    cleaned = cleaned.strip()
            
            response_json = json.loads(cleaned)
            
            # Post-process: Normalize entities using EntityLinker
            decomposed_query = DecomposedQuery(**response_json)
            normalized_query = self.entity_linker.normalize_query(decomposed_query)
            
            if return_metadata:
                metadata = {
                    "model": completion.model,
                    "usage": completion.usage.model_dump() if completion.usage else {},
                    "raw_response": response_text
                }
                return normalized_query, metadata
            
            return normalized_query
            
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON Parse Error: {e}")
            print(f"\n📄 Raw LLM Response:")
            print("-" * 50)
            print(response_text[:1000] + "..." if len(response_text) > 1000 else response_text)
            print("-" * 50)
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
            
        except ValidationError as e:
            print(f"\n❌ Pydantic Validation Error:")
            print("-" * 50)
            for error in e.errors():
                field = " -> ".join(str(x) for x in error['loc'])
                msg = error['msg']
                print(f"  Field: {field}")
                print(f"  Error: {msg}")
                if 'input' in error:
                    print(f"  Got:   {error['input']}")
                print()
            
            print(f"\n📄 Parsed JSON (before validation):")
            print("-" * 50)
            print(json.dumps(response_json, indent=2)[:1500])
            print("-" * 50)
            
            # Try to return a partial result with defaults for invalid fields
            try:
                # Fix common issues
                if response_json:
                    # Ensure required fields exist
                    if 'query_type' not in response_json:
                        response_json['query_type'] = 'player_stats'
                    if 'original_query' not in response_json:
                        response_json['original_query'] = query
                    
                    # Try again with fixes
                    val = DecomposedQuery.model_validate(response_json)
                    if return_metadata:
                        metadata = {
                            "model": completion.model if completion else "unknown",
                            "usage": completion.usage.model_dump() if completion and completion.usage else {},
                            "raw_response": response_text
                        }
                        return val, metadata
                    return val
            except:
                pass
            
            raise ValueError(f"LLM response failed Pydantic validation: {e}")
            
        except Exception as e:
            print(f"\n❌ Unexpected Error: {type(e).__name__}: {e}")
            if response_json:
                print(f"\n📄 Parsed JSON:")
                print("-" * 50)
                print(json.dumps(response_json, indent=2)[:1000])
                print("-" * 50)
            raise
    
    def decompose_to_json(self, query: str) -> dict:
        """
        Decompose query and return as dictionary.
        
        Args:
            query: Natural language query string
        
        Returns:
            Dictionary representation of DecomposedQuery
        """
        result = self.decompose(query)
        return result.model_dump()
    
    def decompose_to_json_string(self, query: str, indent: int = 2) -> str:
        """
        Decompose query and return as formatted JSON string.
        
        Args:
            query: Natural language query string
            indent: JSON indentation level
        
        Returns:
            Formatted JSON string
        """
        result = self.decompose(query)
        return result.model_dump_json(indent=indent)


# =============================================================================
# Simple Testing Interface
# =============================================================================

def run_interactive_test():
    """Interactive testing mode - takes queries and returns JSON."""
    print("=" * 70)
    print("Query Decomposer - Interactive Test")
    print("=" * 70)
    print("\nInitializing...")
    
    # You can change the model here
    MODEL = None  # Uses default: google/gemma-3-27b-it
    
    try:
        decomposer = QueryDecomposer(data_dir=Path("data"), model=MODEL)
        print(f"✓ Loaded {len(decomposer.entity_linker.player_names)} players")
    except Exception as e:
        print(f"✗ Error initializing: {e}")
        return
    
    print("\nEnter cricket queries (type 'quit' to exit, 'prompt' to see system prompt):\n")
    
    while True:
        query = input("\n🏏 Query: ").strip()
        
        if query.lower() == 'quit':
            print("Goodbye!")
            break
        
        if query.lower() == 'prompt':
            print("\n" + "=" * 70)
            print("SYSTEM PROMPT:")
            print("=" * 70)
            print(decomposer.get_system_prompt())
            continue
        
        if not query:
            continue
        
        print("\n⏳ Processing...")
        
        try:
            result = decomposer.decompose(query)
            
            print("\n" + "─" * 70)
            print("📋 DECOMPOSED QUERY")
            print("─" * 70)
            print(result.model_dump_json(indent=2))
            
            print("\n" + "─" * 70)
            print("📊 SUMMARY")
            print("─" * 70)
            print(f"Type: {result.query_type.value}")
            print(f"Players: {[p.name for p in result.players]}")
            print(f"Teams: {[t.name for t in result.teams]}")
            print(f"Phase: {result.phase.value}")
            print(f"Seasons: {result.season_filter.seasons}")
            print(f"Metrics: {[m.value for m in result.metrics]}")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")


def test_single_query(query: str, model: str = None):
    """
    Test a single query and return the result.
    
    Args:
        query: The natural language query
        model: Model name (optional, uses default)
    
    Returns:
        DecomposedQuery object
    """
    decomposer = QueryDecomposer(data_dir=Path("data"), model=model)
    return decomposer.decompose(query)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    run_interactive_test()
