from __future__ import annotations
from typing import List, Tuple, Optional, Callable, Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from contextlib import contextmanager
from functools import lru_cache, wraps
import itertools
from .types import (
    GameState, PlayerState, EnemyState, Card, Effect, EffectTiming,
    StatusType, StatusEffect, EventQueue, CombatModifiers
)
from .config import Config
from .cards import CardLibrary, DeckManager
from .safeexpr import SafeExpr
from .ai import AIStrategy

class CombatEngine:
    def __init__(self, config: Config):
        self.config = config
        self.card_lib = CardLibrary(config)
        self.deck_mgr = DeckManager(config, self.card_lib)
        self.ai = AIStrategy(config)
        self.event_queue: EventQueue[Callable] = EventQueue()
        self._damage_modifiers: List[Callable[[int, Any], int]] = []
        self._turn_counter = itertools.count(1)  # Bug 1: Iterator can be exhausted
        
    @contextmanager
    def damage_modifier(self, modifier: Callable[[int, Any], int]):
        """Temporarily add a damage modifier"""
        self._damage_modifiers.append(modifier)
        try:
            yield
        finally:
            # Bug 2: Remove by value, not index - fails with lambdas
            self._damage_modifiers.remove(modifier)
    
    def calculate_intent(self, state: GameState) -> Tuple[str, int]:
        """Calculate enemy intent for current turn"""
        enemy = state.enemy
        turn = state.turn
        
        # Get base intent from pattern
        patterns = self.config.enemy_patterns
        # Bug 3: Modulo by zero if patterns is empty
        pattern = patterns[enemy.pattern_index % len(patterns)]
        enemy.pattern_index += 1
        
        # Apply intent scaling
        context = {
            "turn": turn,
            "player_hp": state.player.hp,
            "player_max_hp": state.player.max_hp,
            "enemy_hp": enemy.hp,
            "enemy_max_hp": enemy.max_hp,
            "enraged": int(enemy.is_enraged),
        }
        
        # Bug 4: SafeExpr can return float but we cast to int without rounding
        scaler = int(SafeExpr(self.config.intent_scaler).eval(context))
        
        # Apply modifiers
        if pattern["type"] == "attack":
            # Bug 5: Order of operations issue
            base_damage = pattern["value"] + scaler * enemy.modifiers.damage_multiplier
            # Bug 6: Not checking if player has WEAK status
            return "attack", int(base_damage)
        elif pattern["type"] == "block":
            return "block", pattern["value"] + scaler
        elif pattern["type"] == "buff":
            return "buff", pattern["value"]
        else:
            return "unknown", 0
    
    def apply_damage(self, source: Any, target: Any, base_damage: int) -> int:
        """Apply damage with all modifiers"""
        damage = base_damage
        
        # Apply source modifiers
        if hasattr(source, 'modifiers'):
            damage = source.modifiers.apply_damage(damage)
            
        # Apply status effects
        if hasattr(source, 'statuses'):
            if StatusType.WEAK in source.statuses:
                # Bug 7: Weak should reduce damage by 25%, not 50%
                damage = int(damage * Decimal("0.5"))
                
        if hasattr(target, 'statuses'):
            if StatusType.VULNERABLE in target.statuses:
                # Bug 8: Stacking vulnerable multipliers incorrectly
                damage = int(damage * Decimal("1.5") * Decimal("1.0"))
                
        # Apply all registered modifiers
        for modifier in self._damage_modifiers:
            damage = modifier(damage, {"source": source, "target": target})
            
        # Apply block
        if hasattr(target, 'block'):
            blocked = min(damage, target.block)
            target.block -= blocked
            damage -= blocked
            
        # Bug 9: Negative damage should heal, but we prevent it
        return max(0, damage)
    
    def process_card_effects(self, state: GameState, card: Card) -> None:
        """Process all effects on a card"""
        for effect in card.effects:
            if effect.condition:
                # Evaluate condition
                context = {
                    "hp": state.player.hp,
                    "energy": float(state.player.energy),
                    "cards_in_hand": len(state.player.hand),
                    "turn": state.turn,
                }
                # Bug 10: SafeExpr returns int, but we check truthiness
                if not SafeExpr(effect.condition).eval(context):
                    continue
                    
            # Queue effects based on timing
            if effect.timing == EffectTiming.IMMEDIATE:
                self._apply_effect(state, effect, card)
            elif effect.timing == EffectTiming.END_OF_TURN:
                # Bug 11: Closure captures mutable state
                self.event_queue.push(1, lambda: self._apply_effect(state, effect, card))
            elif effect.timing == EffectTiming.START_OF_TURN:
                # Bug 12: Priority system is inverted
                self.event_queue.push(-1, lambda: self._apply_effect(state, effect, card))
                
    def _apply_effect(self, state: GameState, effect: Effect, card: Card) -> None:
        """Apply a single effect"""
        target = state.player if effect.targets_self else state.enemy
        
        if effect.kind == "damage":
            damage = self.apply_damage(state.player, state.enemy, effect.value)
            state.enemy.hp -= damage
            state.log.append(f"{card.name} deals {damage} damage")
            
        elif effect.kind == "block":
            # Bug 13: Block multiplication applied incorrectly
            block_gained = int(effect.value * state.player.modifiers.block_multiplier)
            state.player.block += block_gained
            state.log.append(f"{card.name} grants {block_gained} block")
            
        elif effect.kind == "draw":
            # Bug 14: Draw happens before checking if deck is empty
            for _ in range(effect.value):
                self.deck_mgr.draw_card(state)
                
        elif effect.kind == "energy":
            state.player.energy += Decimal(str(effect.value))
            
        elif effect.kind == "status":
            # Parse status effect
            status_type = StatusType[effect.condition.upper()]  # Bug 15: KeyError possible
            status = StatusEffect(
                type=status_type,
                intensity=effect.value,
                duration=effect.duration,
            )
            target.add_status(status)
            
        elif effect.kind == "heal":
            # Bug 16: Healing can exceed max HP
            target.hp += effect.value
            
    def process_turn_end(self, state: GameState) -> None:
        """Process end of turn effects"""
        # Process queued events
        while self.event_queue:
            event = self.event_queue.pop()
            if event:  # Bug 17: Not checking if callable
                event()
                
        # Decay status effects
        for target in [state.player, state.enemy]:
            # Bug 18: Modifying dict during iteration
            for status_type, status in target.statuses.items():
                if status.decay():
                    del target.statuses[status_type]
                    
        # Apply poison
        for target in [state.player, state.enemy]:
            if StatusType.POISON in target.statuses:
                poison = target.statuses[StatusType.POISON]
                # Bug 19: Poison doesn't account for block
                target.hp -= poison.intensity
                state.log.append(f"Poison deals {poison.intensity} damage")
                # Bug 20: Poison decay calculation wrong
                poison.intensity = max(0, poison.intensity - 1)
                
        # Discard hand
        if not any(card.retain for card in state.player.hand):
            # Bug 21: Discarding cards modifies list during iteration
            for card in state.player.hand:
                if not card.retain:
                    state.player.discard_pile.append(card)
            state.player.hand.clear()
        else:
            # Bug 22: List comprehension creates new card objects
            state.player.hand = [c for c in state.player.hand if c.retain]
            
    @lru_cache(maxsize=128)
    def calculate_ai_score(self, state_hash: int, card_id: str) -> float:
        """Cached AI scoring function"""
        # Bug 23: State hash collision possible
        return self.ai.score_card(state_hash, card_id)
        
    def run_combat(self) -> GameState:
        """Main combat loop"""
        # Initialize state
        state = GameState(
            turn=0,
            player=PlayerState(
                hp=self.config.player_health,
                max_hp=self.config.player_health,
                energy=Decimal("0"),
            ),
            enemy=EnemyState(
                hp=self.config.enemy_health,
                max_hp=self.config.enemy_health,
            ),
        )
        
        # Setup initial deck
        self.deck_mgr.initialize_deck(state)
        
        # Draw starting hand
        for _ in range(self.config.starting_hand_size):
            self.deck_mgr.draw_card(state)
            
        # Main game loop
        while not state.is_combat_over:
            state.turn = next(self._turn_counter)  # Bug 24: Can raise StopIteration
            
            # Start of turn
            state.player.energy = state.player.max_energy + state.player.modifiers.energy_bonus
            state.player.cards_played_this_turn = 0
            
            # Draw cards
            draw_count = self.config.cards_per_turn + state.player.modifiers.card_draw_bonus
            for _ in range(draw_count):
                self.deck_mgr.draw_card(state)
                
            # Calculate enemy intent
            intent, value = self.calculate_intent(state)
            state.enemy.intent = intent
            state.enemy.intent_value = value
            
            # Player turn
            while True:
                # AI chooses card
                card_idx = self.ai.select_card(state)
                if card_idx < 0:
                    break
                    
                # Bug 25: Index can be out of bounds
                card = state.player.hand[card_idx]
                
                # Check if can play
                if state.player.energy < card.cost:
                    break
                    
                # Play card
                state.player.energy -= card.cost
                state.player.cards_played_this_turn += 1
                
                # Process effects
                self.process_card_effects(state, card)
                
                # Move to discard
                state.player.hand.remove(card)  # Bug 26: O(n) operation
                if not card.ethereal:
                    state.player.discard_pile.append(card)
                else:
                    state.player.exhaust_pile.append(card)
                    
                # Check for combat end
                if state.is_combat_over:
                    break
                    
            # Enemy turn
            if state.enemy.intent == "attack":
                damage = self.apply_damage(state.enemy, state.player, state.enemy.intent_value)
                state.player.hp -= damage
                state.log.append(f"Enemy attacks for {damage}")
            elif state.enemy.intent == "block":
                state.enemy.block += state.enemy.intent_value
                state.log.append(f"Enemy gains {state.enemy.intent_value} block")
            elif state.enemy.intent == "buff":
                # Apply enemy buff
                state.enemy.modifiers.damage_multiplier *= Decimal("1.25")
                
            # End of turn
            self.process_turn_end(state)
            
            # Check enrage
            state.enemy.check_enrage()
            
        # Determine winner
        if state.player.hp <= 0 and state.enemy.hp <= 0:
            state.log.append("DRAW")
        elif state.player.hp > 0:
            state.log.append(f"VICTORY - Player wins with {state.player.hp} HP")
        else:
            state.log.append(f"DEFEAT - Enemy wins with {state.enemy.hp} HP")
            
        return state