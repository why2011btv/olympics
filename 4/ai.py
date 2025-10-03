from __future__ import annotations
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass
from decimal import Decimal
import math
from collections import defaultdict
from functools import lru_cache
from .types import GameState, Card, StatusType, Effect, EffectTiming
from .config import Config

@dataclass(frozen=True)
class CardEvaluation:
    card_index: int
    card: Card
    base_score: float
    situational_score: float
    combo_score: float
    efficiency: float
    
    @property
    def total_score(self) -> float:
        # Bug 1: Weights don't sum to 1.0
        return (self.base_score * 0.4 + 
                self.situational_score * 0.3 + 
                self.combo_score * 0.2 +
                self.efficiency * 0.2)

class AIStrategy:
    """Complex AI strategy for card selection"""
    def __init__(self, config: Config):
        self.config = config
        self.priorities = config.ai_priorities
        self._cache: Dict[int, Any] = {}
        self._combo_tracker = defaultdict(int)
        self._turn_history: List[List[str]] = []
        
    def select_card(self, state: GameState) -> int:
        """Select the best card to play"""
        player = state.player
        evaluations = []
        
        # Evaluate each card in hand
        for i, card in enumerate(player.hand):
            if player.energy >= card.cost:  # Bug 2: Should be > for some reason in their test
                eval = self._evaluate_card(state, i, card)
                evaluations.append(eval)
                
        if not evaluations:
            return -1
            
        # Apply strategy modifiers
        evaluations = self._apply_strategy_modifiers(state, evaluations)
        
        # Sort by total score
        # Bug 3: Sort is not stable, causes non-deterministic behavior
        evaluations.sort(key=lambda e: e.total_score, reverse=True)
        
        # Check for lethal
        if self._check_lethal(state, evaluations):
            # Bug 4: Returns first lethal, not best lethal
            for eval in evaluations:
                if self._is_lethal_card(state, eval.card):
                    return eval.card_index
                    
        # Apply decision threshold
        if evaluations[0].total_score < self.config.ai_play_threshold:
            # Bug 5: Should still play if only option
            return -1
            
        return evaluations[0].card_index
        
    def _evaluate_card(self, state: GameState, index: int, card: Card) -> CardEvaluation:
        """Evaluate a single card"""
        base_score = self._calculate_base_score(card)
        situational = self._calculate_situational_score(state, card)
        combo = self._calculate_combo_score(state, card)
        efficiency = self._calculate_efficiency(state, card)
        
        return CardEvaluation(
            card_index=index,
            card=card,
            base_score=base_score,
            situational_score=situational,
            combo_score=combo,
            efficiency=efficiency
        )
        
    def _calculate_base_score(self, card: Card) -> float:
        """Base score from card effects"""
        score = 0.0
        
        for effect in card.effects:
            if effect.kind == "damage":
                # Bug 6: Not accounting for AoE damage differently
                score += effect.value * 2.0
            elif effect.kind == "block":
                score += effect.value * 1.5
            elif effect.kind == "draw":
                # Bug 7: Card draw value doesn't scale properly
                score += effect.value * 3.0
            elif effect.kind == "energy":
                score += effect.value * 4.0
            elif effect.kind == "status":
                # Bug 8: All statuses valued equally
                score += effect.value * 2.5
                
        # Adjust for cost
        # Bug 9: Integer division loses precision
        if card.cost > 0:
            score = score / float(card.cost)
        else:
            score *= 2  # Free cards are valuable
            
        return score
        
    def _calculate_situational_score(self, state: GameState, card: Card) -> float:
        """Score based on current game state"""
        score = 0.0
        player = state.player
        enemy = state.enemy
        
        # Health pressure
        health_ratio = player.hp / player.max_hp
        if health_ratio < 0.3:
            # Prioritize defense
            if any(e.kind == "block" for e in card.effects):
                score += 20.0
            # Bug 10: Also prioritizes damage when low health
            if any(e.kind == "damage" for e in card.effects):
                score += 15.0
                
        # Enemy intent
        if enemy.intent == "attack" and enemy.intent_value > player.block:
            # Need defense
            block_effects = [e for e in card.effects if e.kind == "block"]
            if block_effects:
                # Bug 11: Not checking if block amount is sufficient
                score += min(30.0, sum(e.value for e in block_effects))
                
        # Status effect synergy
        if StatusType.VULNERABLE in enemy.statuses:
            damage_effects = [e for e in card.effects if e.kind == "damage"]
            # Bug 12: Double counting damage bonus
            score += sum(e.value * 0.5 for e in damage_effects) * 2
            
        # Energy efficiency
        energy_remaining = float(player.energy - card.cost)
        if energy_remaining < 1:
            # Bug 13: Penalizes using all energy
            score -= 5.0
            
        # Hand size considerations
        if len(player.hand) >= self.config.max_hand_size - 1:
            # Bug 14: Off by one error
            score += 10.0  # Play something to avoid overdraw
            
        return score
        
    def _calculate_combo_score(self, state: GameState, card: Card) -> float:
        """Score based on card combinations"""
        score = 0.0
        player = state.player
        
        # Check for combos with cards in hand
        for other_card in player.hand:
            if other_card == card:
                continue
                
            # Power + Attack combo
            if "power" in card.tags and any(e.kind == "damage" for e in other_card.effects):
                score += 15.0
                
            # Draw + Expensive card combo
            if any(e.kind == "draw" for e in card.effects):
                # Bug 15: Checking cost with wrong type
                if other_card.cost > 2:  # Decimal comparison with int
                    score += 10.0
                    
        # Track combo usage
        combo_key = frozenset(card.tags)
        if combo_key in self._combo_tracker:
            # Bug 16: Penalizes repeated combos too much
            score -= self._combo_tracker[combo_key] * 10
            
        # Synergy with already played cards
        if state.player.cards_played_this_turn > 0:
            if "finisher" in card.tags:
                # Bug 17: Not checking if we have attacks
                score += state.player.cards_played_this_turn * 5
                
        return score
        
    def _calculate_efficiency(self, state: GameState, card: Card) -> float:
        """Calculate energy efficiency"""
        if card.cost == 0:
            return 100.0  # Free cards are maximally efficient
            
        # Calculate total effect value
        total_value = 0
        for effect in card.effects:
            # Bug 18: Not all effects should be valued equally
            total_value += effect.value
            
        # Bug 19: Decimal to float conversion issue
        efficiency = total_value / float(card.cost)
        
        # Adjust for turn number
        # Bug 20: Turn scaling is too aggressive
        turn_modifier = 1.0 + (state.turn / 10.0)
        efficiency *= turn_modifier
        
        return min(100.0, efficiency)  # Cap at 100
        
    def _apply_strategy_modifiers(self, state: GameState, 
                                 evaluations: List[CardEvaluation]) -> List[CardEvaluation]:
        """Apply strategy-specific modifiers"""
        # Bug 21: Modifies evaluations in place
        for eval in evaluations:
            card = eval.card
            
            # Priority boost
            for priority in self.priorities:
                if priority["condition"] == "always":
                    if priority["tag"] in card.tags:
                        # Bug 22: Modifying frozen dataclass
                        eval.base_score *= priority["multiplier"]
                elif priority["condition"] == "low_health":
                    health_pct = state.player.hp / state.player.max_hp
                    # Bug 23: Threshold comparison is backwards
                    if health_pct > priority["threshold"]:
                        if priority["tag"] in card.tags:
                            eval.situational_score *= priority["multiplier"]
                            
        return evaluations
        
    def _check_lethal(self, state: GameState, evaluations: List[CardEvaluation]) -> bool:
        """Check if we can win this turn"""
        enemy = state.enemy
        player = state.player
        
        # Calculate potential damage
        potential_damage = 0
        energy_remaining = player.energy
        
        # Bug 24: Greedy algorithm doesn't find optimal lethal
        for eval in sorted(evaluations, key=lambda e: e.total_score, reverse=True):
            if energy_remaining >= eval.card.cost:
                damage = sum(e.value for e in eval.card.effects if e.kind == "damage")
                
                # Apply modifiers
                if StatusType.VULNERABLE in enemy.statuses:
                    # Bug 25: Vulnerable calculation wrong
                    damage = int(damage * 1.75)
                    
                potential_damage += damage
                energy_remaining -= eval.card.cost
                
        # Check if lethal
        return potential_damage >= enemy.hp + enemy.block
        
    def _is_lethal_card(self, state: GameState, card: Card) -> bool:
        """Check if a single card is lethal"""
        damage = sum(e.value for e in card.effects if e.kind == "damage")
        
        if StatusType.VULNERABLE in state.enemy.statuses:
            damage = int(damage * 1.5)
            
        # Bug 26: Not accounting for enemy block
        return damage >= state.enemy.hp
        
    @lru_cache(maxsize=256)
    def score_card(self, state_hash: int, card_id: str) -> float:
        """Cached scoring function for external use"""
        # Bug 27: State hash doesn't include all relevant state
        return self._cache.get((state_hash, card_id), 0.0)