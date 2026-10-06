"""Entry point: python3 -m farmhouse_siege [easy|normal|hard]"""
import curses
import locale
import os
import sys
import time

from .constants import *  # noqa: F401,F403
from .engine import Game, load_scores, save_scores
from .render import Renderer, title_overlay, end_overlay


def read_keys(scr):
    out = []
    for _ in range(60):
        ch = scr.getch()
        if ch == -1:
            break
        if ch == curses.KEY_UP:
            out.append("up")
        elif ch == curses.KEY_DOWN:
            out.append("down")
        elif ch == curses.KEY_LEFT:
            out.append("left")
        elif ch == curses.KEY_RIGHT:
            out.append("right")
        elif ch in (32, 10, 13, curses.KEY_ENTER):
            out.append("btn")
        elif 0 <= ch < 256:
            c = chr(ch).lower()
            out.append({"w": "up", "s": "down", "a": "left", "d": "right", "f": "btn"}.get(c, c))
    return out



def run(scr, start_sel):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    scr.nodelay(True)
    scr.keypad(True)
    curses.start_color()
    ui = Renderer(scr)
    scores = load_scores()
    state, sel = "title", start_sel
    demo = Game(1, True)
    game = None
    paused = False
    nxt = time.monotonic()
    while True:
        rows, cols = scr.getmaxyx()
        keys = read_keys(scr)
        scr.erase()
        if rows < NEED_ROWS or cols < NEED_COLS:
            try:
                scr.addstr(0, 0, ("ENLARGE THE TERMINAL TO AT LEAST %dx%d (NOW %dx%d)"
                                  % (NEED_COLS, NEED_ROWS, cols, rows))[:max(1, cols - 1)])
            except curses.error:
                pass
            if "q" in keys:
                return
            scr.refresh()
            time.sleep(0.1)
            continue
        ui.layout(rows, cols)
        if state == "title":
            for k in keys:
                if k == "up":
                    sel = (sel - 1) % 3
                    demo.say("", 0)
                elif k == "down":
                    sel = (sel + 1) % 3
                elif k == "btn":
                    game, state, paused = Game(sel), "play", False
                    break
                elif k == "q":
                    return
            if state == "title":
                demo.ambient()
                ui.draw(demo)
                title_overlay(ui, demo, sel, scores)
        if state == "play":
            if "q" in keys:
                state = "title"
            else:
                if "p" in keys:
                    paused = not paused
                if not paused:
                    game.step(keys)
                ui.draw(game)
                if paused:
                    ui.box(7, 14, 25, ["", "P A U S E D", "", "P: RESUME   Q: TITLE", ""], WHITE)
                if game.result:
                    state = "over"
                    b = scores.get(game.d["name"], 0)
                    if game.score > b:
                        scores[game.d["name"]] = game.score
                        save_scores(scores)
        elif state == "over":
            for k in keys:
                if k == "btn":
                    state = "title"
                elif k == "q":
                    return
            game.ambient()
            ui.draw(game)
            end_overlay(ui, game, scores)
        scr.refresh()
        nxt += 1.0 / FPS
        delay = nxt - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        else:
            nxt = time.monotonic()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "-h" in argv or "--help" in argv:
        print("usage: python3 -m farmhouse_siege [easy|normal|hard]")
        return 0
    locale.setlocale(locale.LC_ALL, "")
    sel = 1
    if argv:
        sel = {"easy": 0, "rookie": 0, "normal": 1, "farmhand": 1, "hard": 2, "nightmare": 2}.get(argv[0].lower(), 1)
    os.environ.setdefault("ESCDELAY", "25")
    if not os.environ.get("TERM"):
        os.environ["TERM"] = "xterm-256color"
    try:
        curses.wrapper(run, sel)
    except KeyboardInterrupt:
        pass
    print("The sun is up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
