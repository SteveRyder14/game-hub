# Headless regression tests for the Checkers client

These run `main.py` without a display (mock GL + fake window), drive the real
Kivy clock, screens, touch handling, AI and network code, and print PASS/FAIL
lines.

```bash
python3 -m venv .venv && .venv/bin/pip install kivy websocket-client websockets==12.0
cd kivy-games/checker

# screens, FPS cap, local/AI play, undo, hint, blitz, UI style, glass,
# move dots, capture animation, online packet handling, back key, ...
SCENARIO=tests/scenario_basic.py .venv/bin/python tests/harness.py main.py

# the previous run saved fps=30 -> this checks the cap is honoured at boot
SCENARIO=tests/scenario_relaunch.py .venv/bin/python tests/harness.py main.py
CHECKERS_NO_BOXSHADOW=1 SCENARIO=tests/scenario_relaunch.py .venv/bin/python tests/harness.py main.py

# full online match against a locally running server.py (PORT=8766 python server.py)
CHECKERS_SERVER_URL=ws://127.0.0.1:8766/checkerboard \
  SCENARIO=tests/scenario_online.py .venv/bin/python tests/harness.py main.py
rm -f checkers_data.json
```
