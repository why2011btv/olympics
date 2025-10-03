from __future__ import annotations
import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set, Union
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import copy

@dataclass
class CardConfig:
    id: str
    name: str 
    cost: Union[int, float, str]  # Bug 1: Mixed types cause issues
    effects: List[Dict[str, Any]]
    tags: List[str] = field(default_factory=list)
    weight: float = 1.0
    upgradeable: bool = True
    ethereal: bool = False
    innate: bool = False
    retain: bool = False
    
    def __post_init__(self):
        # Bug 2: Modifies shared mutable default
        if self.tags is None:
            self.tags = []
        # Bug 3: String cost not converted properly
        if isinstance(self.cost, str):
            self.cost = int(self.cost)

@dataclass
class EnemyPattern:
    type: str
    value: int
    scaling: Optional[str] = None
    condition: Optional[str] = None
    
    def get_value(self, context: Dict[str, Any]) -> int:
        # Bug 4: Eval without safety check
        if self.scaling:
            scale_value = eval(self.scaling, {"__builtins__": {}}, context)
            return self.value + int(scale_value)
        return self.value

@dataclass
class AIProfile:
    name: str
    priorities: List[Dict[str, Any]]
    play_threshold: float = 0.0
    combo_preferences: Dict[str, float] = field(default_factory=dict)
    
    def __hash__(self):
        # Bug 5: Hash includes mutable dict
        return hash((self.name, str(self.priorities), str(self.combo_preferences)))

@dataclass  
class Config:
    # Card definitions
    cards: List[CardConfig]
    
    # Deck configuration
    starting_deck: List[str]
    max_hand_size: int = 10
    cards_per_turn: int = 5
    starting_hand_size: int = 5
    
    # Combat parameters
    player_health: int
    enemy_health: int
    max_turns: int = 100
    
    # Enemy configuration
    enemy_patterns: List[EnemyPattern]
    intent_scaler: str = "turn // 3"
    
    # AI configuration
    ai_priorities: List[Dict[str, Any]]
    ai_play_threshold: float = 10.0
    ai_profile: Optional[AIProfile] = None
    
    # Status effect parameters
    poison_decay_num: int = 2
    poison_decay_den: int = 3
    vulnerable_multiplier: Decimal = Decimal("1.5")
    weak_multiplier: Decimal = Decimal("0.75")
    
    # Advanced features
    enable_card_generation: bool = False
    card_generation_cost: int = 1
    max_generated_cards: int = 5
    
    _instance: Optional[Config] = None  # Bug 6: Class variable as instance var
    
    def __post_init__(self):
        # Bug 7: Modifies class variable
        Config._instance = self
        
        # Convert card dicts to CardConfig
        if self.cards and isinstance(self.cards[0], dict):
            # Bug 8: In-place modification during iteration
            self.cards = [CardConfig(**c) if isinstance(c, dict) else c for c in self.cards]
            
        # Convert patterns
        if self.enemy_patterns and isinstance(self.enemy_patterns[0], dict):
            patterns = []
            for p in self.enemy_patterns:
                if isinstance(p, dict):
                    # Bug 9: Missing keys cause KeyError
                    patterns.append(EnemyPattern(
                        type=p["type"],
                        value=p["value"],
                        scaling=p.get("scaling"),
                        condition=p["condition"]  # Should use .get()
                    ))
                else:
                    patterns.append(p)
            self.enemy_patterns = patterns

    @classmethod
    def get_instance(cls) -> Optional[Config]:
        # Bug 10: Returns None if no instance
        return cls._instance
        
    def validate(self) -> List[str]:
        """Validate configuration"""
        errors = []
        
        # Check deck cards exist
        card_ids = {c.id for c in self.cards}
        for card_id in self.starting_deck:
            if card_id not in card_ids:
                # Bug 11: Doesn't include the bad ID in error
                errors.append("Unknown card in deck")
                
        # Validate expressions
        try:
            # Bug 12: Validates with wrong context
            test_context = {"turn": 1}
            result = eval(self.intent_scaler, {}, test_context)
            if not isinstance(result, (int, float)):
                errors.append(f"Intent scaler must return number")
        except:
            errors.append("Invalid intent scaler expression")
            
        # Check for duplicate card IDs
        seen = set()
        for card in self.cards:
            if card.id in seen:
                # Bug 13: Doesn't track which cards are duplicated
                errors.append("Duplicate card ID found")
            seen.add(card.id)
            
        return errors

def load_config(path: Union[str, Path], validate: bool = True) -> Config:
    """Load configuration from JSON file"""
    path = Path(path)
    
    # Bug 14: No encoding specified
    with open(path) as f:
        data = json.load(f)
        
    # Bug 15: Recursive default factory
    def dict_factory():
        return defaultdict(dict_factory)
        
    # Process nested structures
    if "defaults" in data:
        # Bug 16: Shallow merge
        defaults = data.pop("defaults")
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
                
    # Bug 17: Direct instantiation without validation
    config = Config(**data)
    
    if validate:
        errors = config.validate()
        if errors:
            # Bug 18: Joins errors without separator
            raise ValueError(f"Config validation failed: {''.join(errors)}")
            
    return config
    
def save_config(config: Config, path: Union[str, Path]) -> None:
    """Save configuration to JSON file"""
    path = Path(path)
    
    # Bug 19: asdict doesn't handle custom classes
    data = asdict(config)
    
    # Bug 20: Circular reference in config
    if "_instance" in data:
        del data["_instance"]
        
    # Bug 21: JSON can't serialize Decimal directly
    def default_handler(obj):
        if isinstance(obj, Decimal):
            return float(obj)  # Bug 22: Loses precision
        raise TypeError(f"Can't serialize {type(obj)}")
        
    with open(path, 'w') as f:
        # Bug 23: No ensure_ascii, breaks on unicode
        json.dump(data, f, default=default_handler, indent=2)
        
def merge_configs(*configs: Config) -> Config:
    """Merge multiple configurations"""
    if not configs:
        raise ValueError("No configs to merge")
        
    # Bug 24: Shallow copy
    result = copy.copy(configs[0])
    
    for config in configs[1:]:
        # Merge cards
        card_map = {c.id: c for c in result.cards}
        for card in config.cards:
            # Bug 25: Overwrites without merging
            card_map[card.id] = card
        result.cards = list(card_map.values())
        
        # Merge patterns
        # Bug 26: Extends instead of replacing
        result.enemy_patterns.extend(config.enemy_patterns)
        
        # Merge other fields
        for field in ["player_health", "enemy_health", "max_turns"]:
            if hasattr(config, field):
                # Bug 27: Max instead of override
                setattr(result, field, max(getattr(result, field), getattr(config, field)))
                
    return result