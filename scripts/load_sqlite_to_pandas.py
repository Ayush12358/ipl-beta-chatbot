import sqlite3
import pandas as pd
import sys
import os

def load_db_to_df(db_path, query=None, table=None):
    """
    Load data from a SQLite database into a pandas DataFrame.
    
    Args:
        db_path (str): Path to the SQLite database file.
        query (str, optional): SQL query to execute.
        table (str, optional): Table name to load entire content from.
        
    Returns:
        pd.DataFrame: DataFrame containing the result, or None if error.
    """
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return None

    try:
        # Create a connection to the database
        conn = sqlite3.connect(db_path)
        
        if query:
            print(f"Executing query: {query}")
            df = pd.read_sql_query(query, conn)
        elif table:
            print(f"Loading table: {table}")
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        else:
            # If no query or table specified, list tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            print(f"Connected to {db_path}")
            print("Tables found in database:")
            for t in tables:
                print(f" - {t[0]}")
            
            if not tables:
                print("No tables found.")
                conn.close()
                return None
                
            # Default to loading the first table if available
            first_table = tables[0][0]
            print(f"\nNo table or query specified. Loading first table: '{first_table}'")
            df = pd.read_sql_query(f"SELECT * FROM {first_table}", conn)

        conn.close()
        return df

    except Exception as e:
        print(f"Error reading database: {e}")
        if 'conn' in locals():
            conn.close()
        return None

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python scripts/load_sqlite_to_pandas.py <path_to_db> [table_name]")
        print("Example: python scripts/load_sqlite_to_pandas.py data/chatbot_history.db interactions")
        sys.exit(1)

    db_path = sys.argv[1]
    table_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Load the data
    df = load_db_to_df(db_path, table=table_name)
    
    # Init display
    if df is not None:
        print("\n" + "="*50)
        print("Successfully loaded DataFrame")
        print("="*50)
        print(f"Shape: {df.shape}")
        print("-" * 20)
        print("Columns:")
        for col in df.columns:
            print(f" - {col}")
        print("-" * 20)
        print("First 5 rows:")
        print(df.head())
        print("="*50)
