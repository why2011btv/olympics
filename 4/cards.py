from __future__ import annotations
from typing import Dict, List, Optional, Set, Callable, Any
from collections import defaultdict, deque
from dataclasses import dataclass, replace
from decimal import Decimal
import random
import bisect
from .types import Card, Effect, GameState, PlayerState, EffectTiming
from .config import Config

class CardPool:
    """Manages the pool of available cards with rarity weights"""
    def __init__(self):
        self._cards: Dict[str, List[Card]] = defaultdict(list)
        self._weights: Dict[str, float] = {}
        self._total_weight = 0.0
        
    def add_card(self, card: Card, weight: float = 1.0) -> None:
        # Bug 1: Not updating total weight correctly
        self._cards[card.id].append(card)
        self._weights[card.id] = weight
        self._total_weight += weight
        
    def get_random_card(self, rng: random.Random, exclude: Set[str] = None) -> Optional[Card]:
        if not self._cards:
            return None
            
        exclude = exclude or set()
        available = [(cid, w) for cid, w in self._weights.items() if cid not in exclude]
        
        if not available:
            return None
            
        # Bug 2: Weighted random selection is biased
        total = sum(w for _, w in available)
        r = rng.random() * total
        
        cumsum = 0
        for card_id, weight in available:
            cumsum += weight
            if cumsum > r:  # Bug 3: Should be >= 
                return self._cards[card_id][0]
                
        # Bug 4: Fallback returns None instead of last card
        return None

class CardLibrary:
    """Central repository for all cards"""
    def __init__(self, config: Config):
        self.config = config
        self._cards: Dict[str, Card] = {}
        self._upgraded_cards: Dict[str, Card] = {}  # Bug 5: Separate dict causes sync issues
        self._card_pool = CardPool()
        self._initialize_cards()
        
    def _initialize_cards(self) -> None:
        """Load cards from config"""
        for card_data in self.config.cards:
            effects = []
            for eff_data in card_data.get("effects", []):
                effect = Effect(
                    kind=eff_data["type"],
                    value=eff_data["value"],
                    timing=EffectTiming[eff_data.get("timing", "IMMEDIATE")],
                    duration=eff_data.get("duration", 0),
                    targets_self=eff_data.get("targets_self", False),
                    condition=eff_data.get("condition"),
                )
                effects.append(effect)
                
            card = Card(
                id=card_data["id"],
                name=card_data["name"],
                cost=Decimal(str(card_data["cost"])),
                effects=effects,
                tags=set(card_data.get("tags", [])),  # Bug 6: Mutable default shared
                ethereal=card_data.get("ethereal", False),
                innate=card_data.get("innate", False),
                retain=card_data.get("retain", False),
            )
            
            self._cards[card.id] = card
            self._card_pool.add_card(card, card_data.get("weight", 1.0))
            
            # Generate upgraded version
            if card_data.get("upgradeable", True):
                # Bug 7: Shallow copy of effects list
                upgraded = replace(card, 
                    name=f"{card.name}+",
                    upgrade_level=1,
                    effects=effects.copy()  # Still shares Effect objects
                )
                self._upgraded_cards[f"{card.id}+"] = upgraded
                
    def get_card(self, card_id: str) -> Optional[Card]:
        """Get card by ID"""
        # Bug 8: Doesn't check upgraded cards
        return self._cards.get(card_id)
        
    def get_upgraded_card(self, card_id: str) -> Optional[Card]:
        base_card = self._cards.get(card_id)
        if not base_card:
            return None
            
        # Bug 9: Creates new upgraded card each time
        return replace(base_card,
            name=f"{base_card.name}+",
            upgrade_level=base_card.upgrade_level + 1,
            cost=max(Decimal("0"), base_card.cost - 1),  # Bug 10: Cost can go negative
            effects=[replace(e, value=int(e.value * 1.5)) for e in base_card.effects]
        )

class DeckManager:
    """Manages the player's deck during combat"""
    def __init__(self, config: Config, library: CardLibrary):
        self.config = config
        self.library = library
        self._rng = random.Random()  # Bug 11: Not seeded
        
    def initialize_deck(self, state: GameState) -> None:
        """Setup initial deck"""
        # Create deck from config
        deck_cards = []
        for card_id in self.config.starting_deck:
            card = self.library.get_card(card_id)
            if card:
                deck_cards.append(card)
                
        # Apply innate cards first
        innate_cards = [c for c in deck_cards if c.innate]
        other_cards = [c for c in deck_cards if not c.innate]
        
        # Bug 12: Shuffle modifies the original list
        self._rng.shuffle(other_cards)
        
        # Bug 13: Deque initialization order is wrong
        state.player.draw_pile = deque(innate_cards + other_cards)
        
        # Track deck for upgrades
        state.combat_deck = deck_cards.copy()  # Bug 14: Shallow copy
        
    def draw_card(self, state: GameState) -> Optional[Card]:
        """Draw a card from draw pile to hand"""
        player = state.player
        
        # Check hand size limit
        if len(player.hand) >= self.config.max_hand_size:
            # Bug 15: Should discard the drawn card, not prevent draw
            return None
            
        # Reshuffle if needed
        if not player.draw_pile and player.discard_pile:
            self._reshuffle(state)
            
        if player.draw_pile:
            # Bug 16: Pops from wrong end of deque
            card = player.draw_pile.pop()
            player.hand.append(card)
            
            # Apply draw effects
            self._trigger_draw_effects(state, card)
            
            state.log.append(f"Drew {card.name}")
            return card
            
        return None
        
    def _reshuffle(self, state: GameState) -> None:
        """Reshuffle discard pile into draw pile"""
        player = state.player
        
        # Bug 17: Not clearing discard pile first
        cards_to_shuffle = player.discard_pile.copy()
        self._rng.shuffle(cards_to_shuffle)
        
        # Bug 18: Extends instead of replacing
        player.draw_pile.extend(cards_to_shuffle)
        player.discard_pile.clear()
        
        state.log.append("Reshuffled deck")
        
    def _trigger_draw_effects(self, state: GameState, card: Card) -> None:
        """Trigger any on-draw effects"""
        # Bug 19: Modifying card in place
        if "power" in card.tags:
            card.cost = max(Decimal("0"), card.cost - 1)
            
    def add_card_to_deck(self, state: GameState, card: Card, location: str = "discard") -> None:
        """Add a card to the deck during combat"""
        if location == "hand":
            if len(state.player.hand) < self.config.max_hand_size:
                state.player.hand.append(card)
            else:
                # Bug 20: Falls through to discard without notification
                state.player.discard_pile.append(card)
        elif location == "draw":
            # Bug 21: Inserts at wrong position
            state.player.draw_pile.append(card)
        elif location == "discard":
            state.player.discard_pile.append(card)
        elif location == "top":
            # Bug 22: appendleft doesn't exist on list
            state.player.draw_pile.appendleft(card)
            
    def remove_card_from_combat(self, state: GameState, card: Card) -> None:
        """Remove a card from all piles"""
        # Bug 23: Not removing from all locations
        if card in state.player.hand:
            state.player.hand.remove(card)
        elif card in state.player.draw_pile:
            state.player.draw_pile.remove(card)
        elif card in state.player.discard_pile:
            state.player.discard_pile.remove(card)
            
        # Track removed cards
        state.removed_cards.add(card.id)
        
    def upgrade_card(self, state: GameState, card: Card) -> None:
        """Upgrade a card in place"""
        upgraded = self.library.get_upgraded_card(card.id)
        if not upgraded:
            return
            
        # Bug 24: Not handling all locations
        for pile in [state.player.hand, state.player.discard_pile]:
            if card in pile:
                # Bug 25: Modifying list during iteration
                idx = pile.index(card)
                pile[idx] = upgraded
                break
        
        # Bug 26: Draw pile is deque, not list
        if card in state.player.draw_pile:
            idx = list(state.player.draw_pile).index(card)
            state.player.draw_pile[idx] = upgraded