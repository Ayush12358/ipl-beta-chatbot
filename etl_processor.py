"""
Cricket Data ETL Processor
===========================
Transforms raw Cricsheet JSON files into queryable Parquet tables using a star schema.

Output Tables:
    - data/teams.parquet      : Team dimension table
    - data/venues.parquet     : Venue dimension table  
    - data/players.parquet    : Player dimension table
    - data/seasons.parquet    : Season dimension table
    - data/matches.parquet    : Match fact table
    - data/ball_events.parquet: Ball-by-ball fact table

Usage:
    python etl_processor.py
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd


# =============================================================================
# Configuration
# =============================================================================

JSON_DIR = Path("Match Data JSON")
OUTPUT_DIR = Path("data")

# Phase boundaries (0-indexed overs)
POWERPLAY_END = 6
DEATH_START = 15


# =============================================================================
# Helper Functions
# =============================================================================

def get_phase(over_num: int) -> str:
    """Determine match phase based on over number (0-indexed)."""
    if over_num < POWERPLAY_END:
        return "powerplay"
    elif over_num < DEATH_START:
        return "middle"
    else:
        return "death"


def normalize_team_name(name: str) -> str:
    """Normalize team name variations."""
    name_map = {
        # Historical team name changes
        "Delhi Daredevils": "Delhi Capitals",
        "Kings XI Punjab": "Punjab Kings",
        # RCB rebranding
        "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
        # Normalize spelling variations
        "Rising Pune Supergiants": "Rising Pune Supergiant",
    }
    return name_map.get(name, name)


def get_team_abbreviation(team_name: str) -> str:
    """Get standard abbreviation for team."""
    abbrev_map = {
        # Current IPL teams
        "Chennai Super Kings": "CSK",
        "Mumbai Indians": "MI",
        "Royal Challengers Bengaluru": "RCB",
        "Royal Challengers Bangalore": "RCB",
        "Kolkata Knight Riders": "KKR",
        "Delhi Capitals": "DC",
        "Punjab Kings": "PBKS",
        "Rajasthan Royals": "RR",
        "Sunrisers Hyderabad": "SRH",
        "Gujarat Titans": "GT",
        "Lucknow Super Giants": "LSG",
        # Historical/defunct teams
        "Deccan Chargers": "DCH",
        "Kochi Tuskers Kerala": "KTK",
        "Pune Warriors India": "PWI",
        "Rising Pune Supergiant": "RPS",
        "Gujarat Lions": "GL",
    }
    return abbrev_map.get(team_name, team_name[:3].upper())


def extract_season_from_date(date_str: str) -> str:
    """Extract IPL season from match date."""
    year = int(date_str.split("-")[0])
    return f"IPL {year}"


def generate_venue_id(venue_name: str) -> str:
    """Generate stable venue ID from name."""
    # Simple hash-based ID
    return f"venue_{abs(hash(venue_name)) % 100000:05d}"


def generate_team_id(team_name: str) -> str:
    """Generate team ID from normalized name."""
    normalized = normalize_team_name(team_name)
    return get_team_abbreviation(normalized).lower()


# =============================================================================
# Extraction Functions
# =============================================================================

def parse_json_file(filepath: Path) -> Dict[str, Any]:
    """Load and parse a single JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_match_info(data: Dict, match_id: str) -> Dict[str, Any]:
    """Extract match-level information."""
    info = data.get("info", {})
    
    # Get teams
    teams = info.get("teams", [])
    team1 = normalize_team_name(teams[0]) if len(teams) > 0 else None
    team2 = normalize_team_name(teams[1]) if len(teams) > 1 else None
    
    # Get outcome
    outcome = info.get("outcome", {})
    winner = outcome.get("winner")
    if winner:
        winner = normalize_team_name(winner)
    
    outcome_by = outcome.get("by", {})
    margin_runs = outcome_by.get("runs")
    margin_wickets = outcome_by.get("wickets")
    
    # Get date
    dates = info.get("dates", [])
    match_date = dates[0] if dates else None
    
    # Get toss info
    toss = info.get("toss", {})
    toss_winner = toss.get("winner")
    if toss_winner:
        toss_winner = normalize_team_name(toss_winner)
    
    # Get player of match
    pom = info.get("player_of_match", [])
    player_of_match = pom[0] if pom else None
    
    # Get event info
    event = info.get("event", {})
    
    return {
        "match_id": match_id,
        "match_date": match_date,
        "season": extract_season_from_date(match_date) if match_date else None,
        "venue": info.get("venue"),
        "city": info.get("city"),
        "team1": team1,
        "team2": team2,
        "team1_id": generate_team_id(team1) if team1 else None,
        "team2_id": generate_team_id(team2) if team2 else None,
        "toss_winner": toss_winner,
        "toss_winner_id": generate_team_id(toss_winner) if toss_winner else None,
        "toss_decision": toss.get("decision"),
        "outcome_winner": winner,
        "outcome_winner_id": generate_team_id(winner) if winner else None,
        "outcome_margin_runs": margin_runs,
        "outcome_margin_wickets": margin_wickets,
        "player_of_match": player_of_match,
        "match_number": event.get("match_number"),
        "overs": info.get("overs"),
    }


def extract_players(data: Dict) -> Dict[str, Dict[str, str]]:
    """Extract player registry from match data."""
    info = data.get("info", {})
    registry = info.get("registry", {}).get("people", {})
    players = info.get("players", {})
    
    result = {}
    for team, player_list in players.items():
        team_normalized = normalize_team_name(team)
        for player_name in player_list:
            registry_id = registry.get(player_name, "")
            result[player_name] = {
                "full_name": player_name,
                "short_name": player_name,  # Could be enhanced with name parsing
                "registry_id": registry_id,
            }
    
    return result


def extract_ball_events(data: Dict, match_id: str) -> List[Dict[str, Any]]:
    """
    Extract ball-by-ball data from innings with precise attribution.
    
    Key improvements:
    - is_bowler_wicket: Only wickets attributable to bowler (not run outs, retired hurt, etc.)
    - Granular extras: runs_wide, runs_noball, runs_bye, runs_legbye, runs_penalty
    - runs_conceded: Runs charged to bowler (runs_off_bat + wides + noballs)
    - is_batter_out: True if on-strike batter dismissed (not non-striker run out)
    """
    
    # Wickets that count for bowler's stats
    BOWLER_WICKET_TYPES = {
        'caught', 'bowled', 'lbw', 'stumped', 
        'caught and bowled', 'hit wicket'
    }
    
    # Wickets that are not real dismissals (batter not "out")
    NON_DISMISSAL_TYPES = {
        'retired hurt', 'retired not out'
    }
    
    innings_data = data.get("innings", [])
    events = []
    event_id = 0
    
    for innings_num, innings in enumerate(innings_data, start=1):
        batting_team = normalize_team_name(innings.get("team", ""))
        overs_data = innings.get("overs", [])
        
        # Check if this is a super over (NOT counted in career stats)
        is_super_over = innings.get("super_over", False)
        
        # Determine bowling team
        info = data.get("info", {})
        teams = [normalize_team_name(t) for t in info.get("teams", [])]
        bowling_team = teams[1] if teams[0] == batting_team else teams[0] if len(teams) > 1 else ""
        
        # Get target info if chasing
        target = innings.get("target", {})
        target_runs = target.get("runs")
        
        for over_data in overs_data:
            over_num = over_data.get("over", 0)
            deliveries = over_data.get("deliveries", [])
            
            for ball_idx, delivery in enumerate(deliveries):
                event_id += 1
                
                batter = delivery.get("batter")
                bowler = delivery.get("bowler")
                non_striker = delivery.get("non_striker")
                
                # ============================================================
                # EXTRAS BREAKDOWN
                # ============================================================
                extras = delivery.get("extras", {})
                runs_wide = extras.get("wides", 0)
                runs_noball = extras.get("noballs", 0)
                runs_bye = extras.get("byes", 0)
                runs_legbye = extras.get("legbyes", 0)
                runs_penalty = extras.get("penalty", 0)
                
                # Determine primary extra type for backward compatibility
                extra_type = None
                if runs_wide > 0:
                    extra_type = "wide"
                elif runs_noball > 0:
                    extra_type = "noball"
                elif runs_bye > 0:
                    extra_type = "bye"
                elif runs_legbye > 0:
                    extra_type = "legbye"
                elif runs_penalty > 0:
                    extra_type = "penalty"
                
                # ============================================================
                # RUNS EXTRACTION
                # ============================================================
                runs = delivery.get("runs", {})
                runs_off_bat = runs.get("batter", 0)  # Runs from hitting the ball
                runs_extras = runs.get("extras", 0)   # Total extra runs
                runs_total = runs.get("total", 0)     # Total runs on delivery
                
                # Runs charged to bowler (for economy calculation)
                # = runs off bat + wide runs + noball runs (not byes/legbyes/penalty)
                runs_conceded = runs_off_bat + runs_wide + runs_noball
                
                # ============================================================
                # LEGAL DELIVERY CHECK
                # ============================================================
                # A delivery is legal if it's not a wide or noball
                is_legal = (runs_wide == 0) and (runs_noball == 0)
                
                # ============================================================
                # WICKET ANALYSIS
                # ============================================================
                wickets = delivery.get("wickets", [])
                wicket_type = None
                player_out = None
                fielder = None
                is_wicket = False
                is_bowler_wicket = False
                is_batter_out = False  # True if the on-strike batter was dismissed
                
                if wickets:
                    w = wickets[0]
                    wicket_type = w.get("kind")
                    player_out = w.get("player_out")
                    fielders = w.get("fielders", [])
                    if fielders:
                        fielder = fielders[0].get("name")
                    
                    # Is this a real dismissal (not retired)?
                    is_wicket = wicket_type not in NON_DISMISSAL_TYPES
                    
                    # Is it a bowler's wicket?
                    is_bowler_wicket = wicket_type in BOWLER_WICKET_TYPES
                    
                    # Is the on-strike batter out (not non-striker run out)?
                    is_batter_out = (player_out == batter) and is_wicket
                
                # ============================================================
                # DERIVED FIELDS
                # ============================================================
                phase = get_phase(over_num)
                
                # Boundary off bat only (not overthrows)
                is_boundary = runs_off_bat in (4, 6)
                is_six = runs_off_bat == 6
                is_four = runs_off_bat == 4
                
                # Dot ball - no runs conceded to bowler on a legal delivery
                # Note: bye/legbye can happen on a dot ball for bowler
                is_dot = is_legal and runs_conceded == 0
                
                events.append({
                    "event_id": event_id,
                    "match_id": match_id,
                    "innings": innings_num,
                    "batting_team": batting_team,
                    "batting_team_id": generate_team_id(batting_team),
                    "bowling_team": bowling_team,
                    "bowling_team_id": generate_team_id(bowling_team),
                    "over_num": over_num,
                    "ball_num": ball_idx + 1,
                    "ball_id": f"{match_id}_{innings_num}_{over_num}.{ball_idx + 1}",
                    "batter": batter,
                    "bowler": bowler,
                    "non_striker": non_striker,
                    
                    # Run breakdown
                    "runs_off_bat": runs_off_bat,
                    "runs_extras": runs_extras,
                    "runs_total": runs_total,
                    "runs_conceded": runs_conceded,  # NEW: For bowler economy
                    
                    # Extras breakdown (NEW)
                    "runs_wide": runs_wide,
                    "runs_noball": runs_noball,
                    "runs_bye": runs_bye,
                    "runs_legbye": runs_legbye,
                    "runs_penalty": runs_penalty,
                    
                    # Legacy field for compatibility
                    "extra_type": extra_type,
                    
                    # Wicket info
                    "wicket_type": wicket_type,
                    "player_out": player_out,
                    "fielder": fielder,
                    "is_wicket": is_wicket,
                    "is_bowler_wicket": is_bowler_wicket,  # NEW: Bowler-attributable wicket
                    "is_batter_out": is_batter_out,        # NEW: On-strike batter dismissed
                    
                    # Derived flags
                    "phase": phase,
                    "is_legal": is_legal,
                    "is_dot": is_dot,
                    "is_boundary": is_boundary,
                    "is_four": is_four,
                    "is_six": is_six,
                    "is_super_over": is_super_over,  # NEW: Super over deliveries (exclude from career stats)
                    "target_runs": target_runs,
                    
                    # Legacy field names for backward compatibility
                    "runs_batter": runs_off_bat,
                })
    
    return events


# =============================================================================
# Main ETL Pipeline
# =============================================================================

def run_etl():
    """Execute the full ETL pipeline."""
    print("=" * 60)
    print("Cricket Data ETL Processor")
    print("=" * 60)
    
    # Initialize collectors
    all_matches = []
    all_ball_events = []
    all_players = {}
    all_venues = set()
    all_seasons = set()
    all_teams = set()
    
    # Find all JSON files
    json_files = list(JSON_DIR.glob("*.json"))
    print(f"\nFound {len(json_files)} JSON files to process")
    
    # Process each file
    for i, filepath in enumerate(sorted(json_files)):
        match_id = filepath.stem  # filename without extension
        
        try:
            # Parse JSON
            data = parse_json_file(filepath)
            
            # Extract match info
            match_info = extract_match_info(data, match_id)
            all_matches.append(match_info)
            
            # Collect unique entities
            if match_info["venue"]:
                all_venues.add((match_info["venue"], match_info["city"]))
            if match_info["season"]:
                all_seasons.add(match_info["season"])
            if match_info["team1"]:
                all_teams.add(match_info["team1"])
            if match_info["team2"]:
                all_teams.add(match_info["team2"])
            
            # Extract players
            players = extract_players(data)
            all_players.update(players)
            
            # Extract ball events
            events = extract_ball_events(data, match_id)
            all_ball_events.extend(events)
            
            if (i + 1) % 20 == 0:
                print(f"  Processed {i + 1}/{len(json_files)} files...")
                
        except Exception as e:
            print(f"  Error processing {filepath.name}: {e}")
    
    print(f"\nExtraction complete:")
    print(f"  - Matches: {len(all_matches)}")
    print(f"  - Ball events: {len(all_ball_events)}")
    print(f"  - Players: {len(all_players)}")
    print(f"  - Venues: {len(all_venues)}")
    print(f"  - Seasons: {len(all_seasons)}")
    print(f"  - Teams: {len(all_teams)}")
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # ==========================================================================
    # Build Dimension Tables
    # ==========================================================================
    
    print("\nBuilding dimension tables...")
    
    # Teams dimension
    teams_df = pd.DataFrame([
        {
            "team_id": generate_team_id(team),
            "team_name": team,
            "abbreviation": get_team_abbreviation(team),
        }
        for team in sorted(all_teams)
    ])
    teams_df.to_parquet(OUTPUT_DIR / "teams.parquet", index=False)
    print(f"  - teams.parquet: {len(teams_df)} rows")
    
    # Venues dimension
    venues_df = pd.DataFrame([
        {
            "venue_id": generate_venue_id(venue),
            "venue_name": venue,
            "city": city,
        }
        for venue, city in sorted(all_venues, key=lambda x: (x[0] or "", x[1] or ""))
    ])
    venues_df.to_parquet(OUTPUT_DIR / "venues.parquet", index=False)
    print(f"  - venues.parquet: {len(venues_df)} rows")
    
    # Seasons dimension
    seasons_df = pd.DataFrame([
        {
            "season_id": season.lower().replace(" ", "_"),
            "season_name": season,
            "year": int(season.split()[-1]),
        }
        for season in sorted(all_seasons)
    ])
    seasons_df.to_parquet(OUTPUT_DIR / "seasons.parquet", index=False)
    print(f"  - seasons.parquet: {len(seasons_df)} rows")
    
    # Players dimension
    players_df = pd.DataFrame([
        {
            "player_id": info["registry_id"] if info["registry_id"] else f"player_{abs(hash(name)) % 100000:05d}",
            "full_name": info["full_name"],
            "short_name": info["short_name"],
            "registry_id": info["registry_id"],
        }
        for name, info in sorted(all_players.items())
    ])
    players_df.to_parquet(OUTPUT_DIR / "players.parquet", index=False)
    print(f"  - players.parquet: {len(players_df)} rows")
    
    # ==========================================================================
    # Build Fact Tables
    # ==========================================================================
    
    print("\nBuilding fact tables...")
    
    # Matches fact table
    matches_df = pd.DataFrame(all_matches)
    
    # Add venue ID
    venue_id_map = {row["venue_name"]: row["venue_id"] for _, row in venues_df.iterrows()}
    matches_df["venue_id"] = matches_df["venue"].map(venue_id_map)
    
    # Add season ID
    matches_df["season_id"] = matches_df["season"].apply(
        lambda x: x.lower().replace(" ", "_") if x else None
    )
    
    # Convert date
    matches_df["match_date"] = pd.to_datetime(matches_df["match_date"])
    
    matches_df.to_parquet(OUTPUT_DIR / "matches.parquet", index=False)
    print(f"  - matches.parquet: {len(matches_df)} rows")
    
    # Ball events fact table
    ball_events_df = pd.DataFrame(all_ball_events)
    
    # Add player IDs (lookup from players_df)
    player_id_map = {row["full_name"]: row["player_id"] for _, row in players_df.iterrows()}
    ball_events_df["batter_id"] = ball_events_df["batter"].map(player_id_map)
    ball_events_df["bowler_id"] = ball_events_df["bowler"].map(player_id_map)
    ball_events_df["non_striker_id"] = ball_events_df["non_striker"].map(player_id_map)
    
    ball_events_df.to_parquet(OUTPUT_DIR / "ball_events.parquet", index=False)
    print(f"  - ball_events.parquet: {len(ball_events_df)} rows")
    
    # ==========================================================================
    # Summary Statistics
    # ==========================================================================
    
    print("\n" + "=" * 60)
    print("ETL Complete!")
    print("=" * 60)
    print(f"\nOutput directory: {OUTPUT_DIR.absolute()}")
    print("\nFiles created:")
    for f in sorted(OUTPUT_DIR.glob("*.parquet")):
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name}: {size_kb:.1f} KB")
    
    # Print some quick stats
    print("\n--- Quick Statistics ---")
    print(f"Seasons covered: {sorted(all_seasons)}")
    print(f"Teams: {sorted([get_team_abbreviation(t) for t in all_teams])}")
    print(f"Total matches: {len(matches_df)}")
    print(f"Total deliveries: {len(ball_events_df)}")
    print(f"Unique players: {len(players_df)}")
    
    # Matches by season
    print("\nMatches by season:")
    for season, count in matches_df.groupby("season").size().items():
        print(f"  {season}: {count} matches")
    
    return {
        "teams": teams_df,
        "venues": venues_df,
        "seasons": seasons_df,
        "players": players_df,
        "matches": matches_df,
        "ball_events": ball_events_df,
    }


if __name__ == "__main__":
    run_etl()
