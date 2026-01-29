"""
Code Executor
==============
Safely executes generated Python code in a sandboxed environment.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Any, Dict, Optional
import traceback
import signal
import json


# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path("data")
TIMEOUT_SECONDS = 30

# Modules allowed in generated code
SAFE_BUILTINS = {
    # Types
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    # Functions
    "len": len, "sum": sum, "min": min, "max": max,
    "round": round, "abs": abs, "sorted": sorted,
    "range": range, "enumerate": enumerate, "zip": zip,
    "map": map, "filter": filter, "any": any, "all": all,
    "print": print,  # For debugging
    # Constants
    "True": True, "False": False, "None": None,
    # Exceptions (for try/except in generated code)
    "Exception": Exception, "ValueError": ValueError, 
    "KeyError": KeyError, "IndexError": IndexError,
    "ZeroDivisionError": ZeroDivisionError, "TypeError": TypeError,
}


# =============================================================================
# Data Loader
# =============================================================================

class DataLoader:
    """Loads and caches parquet data files."""
    
    _instance = None
    _data = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self, data_dir: Path = DATA_DIR) -> Dict[str, pd.DataFrame]:
        """Load all data files (cached after first load)."""
        if self._data is None:
            self._data = {
                "ball_events": pd.read_parquet(data_dir / "ball_events.parquet"),
                "matches": pd.read_parquet(data_dir / "matches.parquet"),
                "players": pd.read_parquet(data_dir / "players.parquet"),
                "teams": pd.read_parquet(data_dir / "teams.parquet"),
                "venues": pd.read_parquet(data_dir / "venues.parquet"),
                "seasons": pd.read_parquet(data_dir / "seasons.parquet"),
            }
            print(f"✓ Loaded {len(self._data)} data files")
        return self._data
    
    def get(self, name: str) -> pd.DataFrame:
        """Get a specific dataframe."""
        data = self.load()
        return data.get(name)


# =============================================================================
# Execution Result
# =============================================================================

class ExecutionResult:
    """Result of code execution."""
    
    def __init__(
        self, 
        success: bool, 
        result: Any = None, 
        error: Optional[str] = None,
        code: str = ""
    ):
        self.success = success
        self.result = result
        self.error = error
        self.code = code
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "result": self._serialize_result(self.result),
            "error": self.error,
        }
    
    def _serialize_result(self, obj: Any) -> Any:
        """Convert result to JSON-serializable format."""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, pd.DataFrame):
            return {
                "type": "dataframe",
                "columns": list(obj.columns),
                "data": obj.to_dict('records'),
                "shape": list(obj.shape)
            }
        if isinstance(obj, pd.Series):
            return {
                "type": "series",
                "name": obj.name,
                "data": obj.to_dict()
            }
        if isinstance(obj, dict):
            return {k: self._serialize_result(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._serialize_result(x) for x in obj]
        # Fallback
        return str(obj)


# =============================================================================
# Code Executor
# =============================================================================

class CodeExecutor:
    """Safely executes generated Python code."""
    
    def __init__(self, data_dir: Path = DATA_DIR, timeout: int = TIMEOUT_SECONDS):
        self.data_dir = data_dir
        self.timeout = timeout
        self.data_loader = DataLoader()
    
    def _preprocess_code(self, code: str) -> str:
        """
        Preprocess code before execution.
        Removes import statements since modules are pre-loaded.
        """
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip import statements (we pre-load pandas, etc.)
            if stripped.startswith('import ') or stripped.startswith('from '):
                continue
            # Skip Path loading (we pre-load data)
            if 'Path(' in line and 'DATA_DIR' not in line:
                continue
            # Skip read_parquet calls (data is pre-loaded)
            if 'read_parquet' in line:
                continue
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def execute(self, code: str) -> ExecutionResult:
        """
        Execute Python code in a sandboxed environment.
        
        Args:
            code: Python code to execute
        
        Returns:
            ExecutionResult with success status and result/error
        """
        import threading
        
        # Preprocess code to remove imports
        processed_code = self._preprocess_code(code)
        
        # Load data
        try:
            data = self.data_loader.load(self.data_dir)
        except Exception as e:
            return ExecutionResult(
                success=False, 
                error=f"Failed to load data: {e}",
                code=code
            )
        
        # Build execution namespace
        exec_globals = {
            "__builtins__": SAFE_BUILTINS,
            # Pre-loaded modules
            "pd": pd,
            "np": np,
            "Path": Path,
            # Pre-loaded data
            "ball_events": data["ball_events"].copy(),
            "matches": data["matches"].copy(),
            "players": data["players"].copy(),
            "teams": data["teams"].copy(),
            "venues": data["venues"].copy(),
            "seasons": data["seasons"].copy(),
            "DATA_DIR": self.data_dir,
        }
        
        # Check if we can use signal-based timeout (only in main thread on Unix)
        can_use_signal = (
            hasattr(signal, 'SIGALRM') and 
            threading.current_thread() is threading.main_thread()
        )
        
        # Set up timeout handler
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Code execution timed out after {self.timeout}s")
        
        try:
            # Set timeout only if in main thread on Unix
            if can_use_signal:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.timeout)
            
            # Execute the processed code
            exec(processed_code, exec_globals)
            
            # Get the result
            if "final_result" in exec_globals:
                result = exec_globals["final_result"]
                return ExecutionResult(success=True, result=result, code=code)
            else:
                return ExecutionResult(
                    success=False,
                    error="Code did not define 'final_result' variable",
                    code=code
                )
        
        except TimeoutError as e:
            return ExecutionResult(success=False, error=str(e), code=code)
        
        except Exception as e:
            # Get detailed traceback
            tb = traceback.format_exc()
            return ExecutionResult(
                success=False, 
                error=f"{type(e).__name__}: {e}\n\n{tb}",
                code=code
            )
        
        finally:
            # Cancel timeout only if we set it
            if can_use_signal:
                signal.alarm(0)
    
    def execute_with_retry(self, code: str, max_retries: int = 2) -> ExecutionResult:
        """Execute code with automatic retry on failure."""
        result = self.execute(code)
        
        if result.success:
            return result
        
        # Could implement code fixing logic here
        # For now, just return the error
        return result


# =============================================================================
# Testing
# =============================================================================

def test_executor():
    """Test the code executor."""
    print("=" * 70)
    print("Code Executor Test")
    print("=" * 70)
    
    executor = CodeExecutor(data_dir=Path("data"))
    
    # Test 1: Simple query
    test_code = '''
# Get Harmanpreet's batting stats
player_balls = ball_events[ball_events['batter'] == 'H Kaur']

runs = player_balls['runs_batter'].sum()
balls = player_balls['is_legal'].sum()
strike_rate = (runs / balls * 100) if balls > 0 else 0
fours = player_balls['is_four'].sum()
sixes = player_balls['is_six'].sum()

final_result = {
    "player": "H Kaur",
    "runs": int(runs),
    "balls_faced": int(balls),
    "strike_rate": round(strike_rate, 2),
    "fours": int(fours),
    "sixes": int(sixes)
}
'''
    
    print("\n--- Test 1: Player Stats ---")
    result = executor.execute(test_code)
    
    if result.success:
        print("✓ Success!")
        print(f"Result: {json.dumps(result.result, indent=2)}")
    else:
        print(f"✗ Error: {result.error}")
    
    # Test 2: Phase breakdown
    test_code_2 = '''
# Get powerplay stats for a player
player = 'S Mandhana'
pp_balls = ball_events[
    (ball_events['batter'] == player) & 
    (ball_events['phase'] == 'powerplay')
]

runs = pp_balls['runs_batter'].sum()
balls = pp_balls['is_legal'].sum()
sr = (runs / balls * 100) if balls > 0 else 0

final_result = {
    "player": player,
    "phase": "powerplay",
    "runs": int(runs),
    "balls": int(balls),
    "strike_rate": round(sr, 2)
}
'''
    
    print("\n--- Test 2: Powerplay Stats ---")
    result = executor.execute(test_code_2)
    
    if result.success:
        print("✓ Success!")
        print(f"Result: {json.dumps(result.result, indent=2)}")
    else:
        print(f"✗ Error: {result.error}")
    
    # Test 3: Error handling
    test_code_error = '''
# This should cause an error
x = 1 / 0
final_result = x
'''
    
    print("\n--- Test 3: Error Handling ---")
    result = executor.execute(test_code_error)
    
    if result.success:
        print("✓ Success (unexpected)")
    else:
        print(f"✓ Error caught correctly: {result.error.split(chr(10))[0]}")


if __name__ == "__main__":
    test_executor()
