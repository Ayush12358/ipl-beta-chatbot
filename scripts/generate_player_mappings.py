import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
from pathlib import Path
import math

DATA_DIR = Path("data")
OUTPUT_FILE = DATA_DIR / "player_full_names.json"

# Manual overrides for tricky cases
OVERRIDES = {
    # "SA Yadav": "Suryakumar Yadav",
    # "AS Yadav": "Arjun Yadav",
    # "J Yadav": "Jayant Yadav",
    # "K Yadav": "Kuldeep Yadav",
    # "UT Yadav": "Umesh Yadav",
    # "V Kohli": "Virat Kohli",
    # "RG Sharma": "Rohit Sharma",
    # "MS Dhoni": "Mahendra Singh Dhoni",
    # "JJ Bumrah": "Jasprit Bumrah",
    # "HH Pandya": "Hardik Pandya",
    # "KH Pandya": "Krunal Pandya",
    # "KL Rahul": "KL Rahul",
    # "KD Karthik": "Dinesh Karthik",
    # "AB de Villiers": "AB de Villiers",
    # "YBK Jaiswal": "Yashasvi Jaiswal",
    # "SV Samson": "Sanju Samson", 
    # "R Parag": "Riyan Parag",
    # "Shubman Gill": "Shubman Gill"
}

def generate_mappings():
    print("Loading players...")
    players_df = pd.read_parquet(DATA_DIR / "players.parquet")
    all_names = sorted(players_df['full_name'].unique().tolist())
    
    print(f"Found {len(all_names)} unique players.")
    
    # Filter out ones we already have overrides for/don't need LLM for
    names_to_process = [n for n in all_names if n not in OVERRIDES]
    
    # Split into batches
    # BATCH_SIZE = 50
    # batches = [names_to_process[i:i + BATCH_SIZE] for i in range(0, len(names_to_process), BATCH_SIZE)]
    
        
    prompt = f"""
You are an expert cricket statistician.
I have a list of cricket player names in an abbreviated format (e.g., "V Kohli").
Your task is to provide the full popular name for each player (e.g., "Virat Kohli").

Input List:
{json.dumps(names_to_process, indent=2)}

Return a JSON object where keys are the abbreviated names from the input and values are the full names.
Do not miss any names.
Return ONLY valid JSON.
"""
    print(prompt)
                
    # # Save results
    # with open(OUTPUT_FILE, "w") as f:
    #     json.dump(mappings, f, indent=2)
        
    # print(f"\n✓ Saved {len(mappings)} mappings to {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_mappings()
