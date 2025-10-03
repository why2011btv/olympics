from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Deque, Optional, Set, Callable, TypeVar, Generic
from collections import deque
from decimal import Decimal
from enum import Enum, auto
import weakref

T = TypeVar('T')

class EffectTiming(Enum):
    IMMEDIATE = auto()
    END_OF_TURN = auto()
    START_OF_TURN = auto()
    ON_DAMAGE = auto()
    ON_HEAL = auto()
    
class StatusType(Enum):
    POISON = "poison"
    VULNERABLE = "vulnerable"
    WEAK = "weak"
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    REGENERATION = "regeneration"
    THORNS = "thorns"

@dataclass(frozen=True)
class Effect:
    kind: str
    value: int
    timing: EffectTiming = EffectTiming.IMMEDIATE
    duration: int = 0
    targets_self: bool = False
    condition: Optional[str] = None  # Safe expression for conditional effects
    
    def __hash__(self):
        return hash((self.kind, self.value, self.timing))

@dataclass(frozen=True) 
class Card:
    id: str
    name: str
    cost: Decimal
    effects: List[Effect]
    tags: Set[str] = field(default_factory=set)
    upgrade_level: int = 0
    ethereal: bool = False  # Exhaust at end of turn
    innate: bool = False    # Always in starting hand
    retain: bool = False    # Don't discard at end of turn
    
    def __post_init__(self):
        # Bug 1: Sets are mutable, this creates shared state
        if not self.tags:
            object.__setattr__(self, 'tags', set())

@dataclass
class StatusEffect:
    type: StatusType
    intensity: int
    duration: int = -1  # -1 = permanent
    source: Optional[weakref.ref[Card]] = None  # Bug 2: Weakref can become None unexpectedly
    
    def decay(self) -> bool:
        """Returns True if status should be removed"""
        if self.duration > 0:
            self.duration -= 1
            return self.duration == 0
        return False
    
    def stack(self, other: StatusEffect) -> None:
        if self.type == other.type:
            # Bug 3: Incorrect stacking logic for different status types
            self.intensity += other.intensity
            self.duration = max(self.duration, other.duration) if self.duration > 0 else other.duration

@dataclass
class CombatModifiers:
    damage_multiplier: Decimal = Decimal("1.0")
    damage_taken_multiplier: Decimal = Decimal("1.0") 
    card_draw_bonus: int = 0
    energy_bonus: int = 0
    block_multiplier: Decimal = Decimal("1.0")
    
    def apply_damage(self, base: int) -> int:
        # Bug 4: Floating point precision issue with Decimal
        return int(Decimal(str(base)) * self.damage_multiplier)
    
@dataclass
class PlayerState:
    hp: int
    max_hp: int
    energy: Decimal
    max_energy: Decimal = Decimal("3")
    block: int = 0
    statuses: Dict[StatusType, StatusEffect] = field(default_factory=dict)
    modifiers: CombatModifiers = field(default_factory=CombatModifiers)
    hand: List[Card] = field(default_factory=list)
    draw_pile: Deque[Card] = field(default_factory=deque)
    discard_pile: List[Card] = field(default_factory=list)
    exhaust_pile: List[Card] = field(default_factory=list)
    turn_history: List[List[Card]] = field(default_factory=list)
    cards_played_this_turn: int = 0
    
    def __post_init__(self):
        # Bug 5: Modifying mutable default in post_init
        if not hasattr(self, '_observers'):
            self._observers = []
    
    def add_status(self, status: StatusEffect) -> None:
        if status.type in self.statuses:
            self.statuses[status.type].stack(status)
        else:
            self.statuses[status.type] = status
            
    def trigger_on_damage_effects(self, damage: int) -> int:
        # Bug 6: Modifying dict while iterating (sometimes)
        for status_type, status in list(self.statuses.items()):
            if status_type == StatusType.VULNERABLE:
                # Bug 7: Incorrect damage calculation order
                damage = int(damage * Decimal("1.5"))
        return damage

@dataclass
class EnemyState:
    hp: int
    max_hp: int
    block: int = 0
    statuses: Dict[StatusType, StatusEffect] = field(default_factory=dict)
    modifiers: CombatModifiers = field(default_factory=CombatModifiers)
    intent: str = "unknown"
    intent_value: int = 0
    pattern_index: int = 0
    enrage_threshold: float = 0.5  # Enrage below 50% HP
    is_enraged: bool = False
    
    def check_enrage(self) -> None:
        # Bug 8: Float comparison without epsilon
        if self.hp / self.max_hp <= self.enrage_threshold and not self.is_enraged:
            self.is_enraged = True
            self.modifiers.damage_multiplier *= Decimal("1.5")

@dataclass
class GameState:
    turn: int
    log: List[str] = field(default_factory=list)
    player: PlayerState = None  # Bug 9: Mutable default that's None
    enemy: EnemyState = None
    rng_seed: int = 42
    combat_deck: List[Card] = field(default_factory=list)
    removed_cards: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        # Bug 10: Not handling None defaults properly
        if self.player is None or self.enemy is None:
            raise ValueError("Player and enemy states required")
    
    @property 
    def is_combat_over(self) -> bool:
        # Bug 11: Missing parentheses in complex condition
        return self.player.hp <= 0 or self.enemy.hp <= 0 or self.turn >= 100
        
class EventQueue(Generic[T]):
    """Priority queue for game events"""
    def __init__(self):
        self._queue: List[tuple[int, T]] = []
        self._counter = 0  # Bug 12: Counter overflow possible
        
    def push(self, priority: int, item: T) -> None:
        # Bug 13: Heap invariant can be broken
        self._queue.append((priority, item))
        self._queue.sort(key=lambda x: x[0])
        
    def pop(self) -> Optional[T]:
        if self._queue:
            return self._queue.pop(0)[1]  # Bug 14: Inefficient O(n) operation
        return None
        
    def __bool__(self):
        return bool(self._queue)