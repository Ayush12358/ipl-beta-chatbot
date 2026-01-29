"""
Entity Linking Layer
====================
Handles fuzzy matching of entities (Players) using rapidfuzz.
Decouples extraction from normalization.
"""

import json
import pandas as pd
from pathlib import Path
from rapidfuzz import process, fuzz
from typing import List, Dict, Any, Optional

class EntityLinker:
    """
    Loads entity databases and provides fuzzy matching capabilities.
    """
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self._load_entities()
        
    def _load_entities(self):
        """Load all entity tables from parquet files and JSON mappings."""
        # Load DataFrames
        self.players_df = pd.read_parquet(self.data_dir / "players.parquet")
        
        # Load Player Full Names Mapping
        self.player_full_names: Dict[str, str] = {}
        mapping_path = self.data_dir / "player_full_names.json"
        if mapping_path.exists():
            with open(mapping_path, "r") as f:
                self.player_full_names = json.load(f)
        
        # Create entity lists for matching
        self.player_names = self.players_df['full_name'].tolist() 
        
        # Create reverse mapping for full name search
        # List of (Full Name, DB Name) tuples
        self.full_name_list = list(self.player_full_names.values())
        self.full_name_map = {v.lower(): k for k, v in self.player_full_names.items()}

    def normalize_player(self, extracted_name: str, threshold: int = 60) -> Optional[str]:
        """
        Specialized normalization for players using Full Name mapping.
        """
        if not extracted_name:
            return None
            
        clean_name = extracted_name.strip()
        
        # 1. Try matching against Full Names first (e.g. "Suryakumar Yadav")
        best_full_match = process.extractOne(
            clean_name,
            self.full_name_list,
            scorer=fuzz.token_sort_ratio
        )
        
        # 2. Try matching against DB names (e.g. "SA Yadav")
        # best_db_match = process.extractOne(
        #     clean_name,
        #     self.player_names,
        #     scorer=fuzz.token_sort_ratio
        # )
        
        # Logic to pick the best match
        full_score = best_full_match[1] if best_full_match else 0
        # db_score = best_db_match[1] if best_db_match else 0
        
        # If full name match is very strong, use it and map back to DB name
        # if full_score > db_score and full_score >= threshold:
        matched_full_name = best_full_match[0]
        # Retrieve DB name from reverse map
        return self.full_name_map.get(matched_full_name.lower())
            
        # Otherwise fallback to DB name match
        # if db_score >= threshold:
            # return best_db_match[0]
            
        return None

    def normalize_query(self, decomposed_query: Any) -> Any:
        """
        In-place normalization of a DecomposedQuery object.
        Iterates through extracted entities and updates them with DB-normalized names.
        """
        # Normalize Players
        if hasattr(decomposed_query, 'players'):
            for p in decomposed_query.players:
                db_name = self.normalize_player(p.name)
                if db_name:
                    p.name = db_name

        # Normalize Opponent Players
        if hasattr(decomposed_query, 'opponent_players'):
            for p in decomposed_query.opponent_players:
                db_name = self.normalize_player(p.name)
                if db_name:
                    p.name = db_name

        return decomposed_query
