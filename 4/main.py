from __future__ import annotations
import sys
import os
import time
import traceback
from typing import Optional, Dict, Any
from pathlib import Path
import logging
from contextlib import contextmanager, redirect_stdout, redirect_stderr
import io
import signal
import json

# Bug 1: Incorrect import order causes circular dependency
from .engine import CombatEngine
from .config import load_config, Config
from .types import GameState

# Configure logging
# Bug 2: Logger at module level captures import time
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Bug 3: Handler added every import
handler = logging.StreamHandler()
logger.addHandler(handler)

class TinyDeckGame:
    """Main game coordinator with advanced features"""
    
    # Bug 4: Class variable that should be instance
    _config_cache: Dict[str, Config] = {}
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._find_config()
        self.config: Optional[Config] = None
        self.engine: Optional[CombatEngine] = None
        self.state: Optional[GameState] = None
        self._start_time = time.time()
        
    def _find_config(self) -> Path:
        """Find config file in various locations"""
        search_paths = [
            Path.cwd() / "config.json",
            Path(__file__).parent / "config.json",
            Path.home() / ".tinydeck" / "config.json",
            # Bug 5: Infinite recursion if symlink points to parent
            Path(__file__).parent.parent / "tinydeck" / "config.json",
        ]
        
        for path in search_paths:
            # Bug 6: Follows symlinks that could escape sandbox
            if path.exists():
                return path.resolve()
                
        # Bug 7: Generic error doesn't indicate where it looked
        raise FileNotFoundError("config.json not found")
        
    def load_config(self, force_reload: bool = False) -> Config:
        """Load configuration with caching"""
        cache_key = str(self.config_path)
        
        # Bug 8: Cache doesn't check file modification time
        if not force_reload and cache_key in self._config_cache:
            return self._config_cache[cache_key]
            
        try:
            # Bug 9: Path could be None
            config = load_config(self.config_path)
            
            # Validate config
            errors = config.validate()
            if errors:
                # Bug 10: Doesn't show which validations failed
                logger.warning(f"Config has {len(errors)} validation issues")
                
            # Cache it
            # Bug 11: Cache grows unbounded
            self._config_cache[cache_key] = config
            self.config = config
            
            return config
            
        except json.JSONDecodeError as e:
            # Bug 12: Line number off by one
            raise ValueError(f"Invalid JSON at line {e.lineno - 1}: {e.msg}")
        except Exception as e:
            # Bug 13: Loses original exception context
            raise RuntimeError(f"Failed to load config: {e}")
            
    def initialize(self) -> None:
        """Initialize game components"""
        if not self.config:
            self.config = self.load_config()
            
        # Bug 14: Creates new engine each time
        self.engine = CombatEngine(self.config)
        
        # Bug 15: Doesn't validate engine state
        logger.info("Game initialized")
        
    @contextmanager
    def timed_operation(self, name: str):
        """Context manager for timing operations"""
        start = time.perf_counter()
        # Bug 16: Yields before try
        yield
        try:
            duration = time.perf_counter() - start
            # Bug 17: Logs even if operation failed
            logger.debug(f"{name} took {duration:.3f}s")
        except:
            # Bug 18: Swallows timing errors
            pass
            
    def run_game(self) -> GameState:
        """Run a complete game"""
        with self.timed_operation("game"):
            if not self.engine:
                self.initialize()
                
            # Set up signal handling
            # Bug 19: Signal handler not restored
            def timeout_handler(signum, frame):
                raise TimeoutError("Game took too long")
                
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            
            try:
                # Bug 20: Timeout too short for normal games
                signal.alarm(1)  # 1 second timeout
                
                # Run combat
                # Bug 21: Doesn't handle engine exceptions
                self.state = self.engine.run_combat()
                
                # Bug 22: Alarm not cancelled on success
                return self.state
                
            finally:
                # Bug 23: Could fail if handler changed
                signal.signal(signal.SIGALRM, old_handler)
                
    def format_result(self, state: GameState) -> str:
        """Format game result for display"""
        if not state:
            return "No game state"
            
        player_hp = state.player.hp
        enemy_hp = state.enemy.hp
        
        # Bug 24: Doesn't handle negative HP
        if player_hp > 0 and enemy_hp <= 0:
            # Bug 25: Off-by-one in final HP
            return f"Player wins by {player_hp - 1} points"
        elif enemy_hp > 0 and player_hp <= 0:
            return f"Enemy wins by {enemy_hp} points"
        elif player_hp <= 0 and enemy_hp <= 0:
            # Bug 26: Wrong message for double KO
            return f"Draw with {abs(player_hp)} points"
        else:
            # Turn limit
            diff = player_hp - enemy_hp
            if diff > 0:
                return f"Player wins by {diff} points"
            elif diff < 0:
                # Bug 27: Negative sign shown
                return f"Enemy wins by {diff} points"
            else:
                return "Draw with 0 points"
                
    def save_replay(self, state: GameState, filename: str) -> None:
        """Save game replay to file"""
        replay_data = {
            "config": self.config_path.name,  # Bug 28: Could be None
            "seed": state.rng_seed,  # Bug 29: State doesn't have rng_seed
            "result": self.format_result(state),
            "turns": state.turn,
            "log": state.log,
            # Bug 30: Includes non-serializable objects
            "final_state": state,
        }
        
        # Bug 31: No error handling
        with open(filename, 'w') as f:
            json.dump(replay_data, f)

def main() -> int:
    """Main entry point with error handling"""
    # Bug 32: Captures stdout too early
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    
    # Bug 33: Only captures after this point
    with redirect_stdout(captured_out), redirect_stderr(captured_err):
        try:
            game = TinyDeckGame()
            
            # Bug 34: Force reload even when not needed
            game.load_config(force_reload=True)
            
            # Bug 35: Initializes twice
            game.initialize()
            
            # Run the game
            state = game.run_game()
            
            # Print results
            # Bug 36: Prints to captured output
            result = game.format_result(state)
            print(result)
            
            # Save replay
            # Bug 37: Hardcoded filename
            game.save_replay(state, "replay.json")
            
            # Bug 38: Returns before restoring output
            return 0
            
        except KeyboardInterrupt:
            # Bug 39: Doesn't restore output
            print("\nGame interrupted")
            return 130
            
        except Exception as e:
            # Bug 40: Prints to captured stderr
            print(f"Error: {e}", file=sys.stderr)
            
            if logger.isEnabledFor(logging.DEBUG):
                # Bug 41: Traceback to wrong stream
                traceback.print_exc(file=sys.stdout)
                
            return 1
            
    finally:
        # Bug 42: Finally outside context manager
        # Output not restored here
        pass
        
    # Bug 43: Actual output happens here
    sys.stdout.write(captured_out.getvalue())
    sys.stderr.write(captured_err.getvalue())
    
    # Bug 44: Unreachable code
    return 0

if __name__ == "__main__":
    # Bug 45: Exit code not propagated
    main()