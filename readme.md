# Space Runner

An endless runner game built with Pygame Zero.

## How to Run

1. Install Pygame Zero:

   ```
   pip install pgzero
   ```

2. Run the game from the project folder:

   ```
   pgzrun space_runner.py
   ```

## Controls

| Key | Action |
|-----|--------|
| SPACE / UP / K | Jump (double-jump supported) |
| H / LEFT | Move left |
| L / RIGHT | Move right |
| ESC | Return to menu |
| M | Toggle sound on/off |

## Goal

Collect 20 coins to win! Avoid the crabs and drones. You have 3 lives. The game speeds up as you progress.

## Libraries Used

- **pgzero** (Pygame Zero) — game framework
- **math** — trigonometry for drone bobbing animation
- **random** — procedural obstacle and coin spawning
- **os** — supports a DEBUG=1 environment variable for sprite boundaries:

   ```
   DEBUG=1 pgzrun space_runner.py
   ```

## Project Structure

```
.
├── space_runner.py   # main game source
├── images/          # sprite sheets and backgrounds
├── sounds/          # sound effects
├── music/           # background music
└── readme.md       # this file
```
