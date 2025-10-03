# Deterministic Card Battle Simulation

## Goal
Run a deterministic card battle simulation where **all gameplay parameters** come from `config.json`. This is a repeatable simulation for testing game mechanics - the same configuration always produces identical results.

## How to Run
```bash
python -m tinydeck.main
```

- The program **must** read `tinydeck/config.json` located next to the code.
- No other inputs, flags, or arguments are allowed.

## What You’re Given
- `tinydeck/main.py` — simulation entrypoint (no arguments).
- `tinydeck/engine.py` — battle simulation engine and turn logic.
- `tinydeck/ai.py` — player's deterministic strategy implementation.
- `tinydeck/cards.py` — card mechanics, effects, and deck management.
- `tinydeck/config.py` — configuration loader (reads `config.json`).
- `tinydeck/safeexpr.py` — safe expression evaluator for enemy damage scaling.
- `tinydeck/types.py` — data structures for the simulation state.
- `tinydeck/config.json` — **all gameplay parameters and player strategy configuration**.

## Requirements
- **No hard-coded gameplay values** in code. All numbers and policies must come from `config.json`.
- **Determinism:** Same code + same `config.json` → identical logs and final result.
- **No arguments:** Running `python -m tinydeck.main` is the only supported invocation.

## Expected Output Format
When you run `python -m tinydeck.main`, the program will output a single line:
- `Player wins by X points` - where X is the player's remaining HP
- `Enemy wins by X points` - where X is the enemy's remaining HP  
- `Draw with 0 points` - if both reach 0 HP simultaneously or at turn limit

This deterministic output is used for grading. The same config.json must always produce the exact same result.

## Deliverables
1. The `tinydeck/` folder with all code files intact.
2. A single `tinydeck/config.json` with your chosen values.
3. The console output produced by `python -m tinydeck.main` (see format above).