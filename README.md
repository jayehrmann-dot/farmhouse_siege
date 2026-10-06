# Farmhouse Siege

You are trapped in a farmhouse and the dead are coming. Survive from 12:00 AM
until dawn by boarding the windows, sharing your scarce ammo and keeping the
survivors away from the breaches. Your single button repairs a barricade or
fires when a zombie is near. Every broken window makes the house harder to
defend. Retreat to the cellar for safety, but if the dead crowd the hatch you
may trap everyone inside. Atari 2600 looks, one screen, inside your terminal.

```bash
./play.sh [easy|normal|hard]
```

or `python3 -m farmhouse_siege` from this folder. Needs Python 3 (ships with
macOS) and a terminal at least 82 columns by 26 rows. A 256-colour terminal
gives the full palette; 8-colour terminals still work.

## Controls

| Key | Action |
| --- | --- |
| Arrows, WASD | move |
| SPACE, ENTER, F | the button (see below) |
| P | pause |
| Q | back to title / quit |

The button does the first thing that applies:

1. Standing on the hatch `[]`: go down to the cellar (or climb out of it)
2. A zombie within about 3 cells and you have ammo: fire
3. Next to a window with fewer than 3 boards: nail a board
4. Next to a survivor: share ammo (evens out rounds, or takes one back)

## Rules of the night

- Zombies gnaw boards off windows. At 0 boards the window is breached and they pour in.
- Every breach speeds up the horde, and a breach can only be reboarded once it is clear.
- Survivors follow you when close but wander off to board windows when you are far
  away, which puts them next to the breaches. Armed survivors `(>` shoot back.
- Ammo crates `AM` appear in the house. Ammo is scarce.
- The cellar is safe, but the night keeps passing and zombies pound the hatch. If 2-4
  (by difficulty) crowd it, or one stands on it, you are trapped and must spend ammo
  to shoot your way out. If the hatch breaks, it is over. Survivors within 3 cells
  follow you down; the rest are left upstairs.
- Outside the lantern light you only see zombie eyes. Lightning shows everything briefly.

| Level | Night | Notes |
| --- | --- | --- |
| ROOKIE | 150 s | slow ghouls, sturdy boards, extra rounds, tougher survivors |
| FARMHAND | 210 s | the intended experience |
| NIGHTMARE | 240 s | fast dead, weak boards, 4 rounds, a frail hatch |

Best score per difficulty is kept in `highscore.json`.

## Layout

| File | Contents |
| --- | --- |
| `farmhouse_siege/constants.py` | layout, tuning, difficulty table, palette, scenery, static map |
| `farmhouse_siege/engine.py` | game rules, no curses, runs headless for testing |
| `farmhouse_siege/render.py` | curses drawing and the title and end screens |
| `farmhouse_siege/__main__.py` | key handling and the main loop |
