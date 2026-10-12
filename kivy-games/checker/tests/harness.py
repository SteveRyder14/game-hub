import os, sys, time, traceback
MAIN = sys.argv[1]
sys.argv = ['main.py']
os.chdir(os.path.dirname(os.path.abspath(MAIN)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakewin
from fakewin import _fw
# ---- Load the game module ----
import importlib.util
spec = importlib.util.spec_from_file_location("game", MAIN)
game = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(game)
except Exception:
    traceback.print_exc()
    sys.exit(2)

from kivy.clock import Clock
from kivy.app import App

app = game.CheckersApp()
App._running_app = app
app._app_window = _fw
try:
    root = app.build()
except Exception:
    traceback.print_exc()
    sys.exit(3)
_fw.add_widget(root)
app.root = root
app.dispatch('on_start')

ERRORS = []

def tick_for(seconds):
    end = time.time() + seconds
    while time.time() < end:
        try:
            Clock.tick()
        except Exception:
            ERRORS.append(traceback.format_exc())
        time.sleep(0.005)


def simulate_touch(x, y):
    """Dispatch a synthetic touch to the root widget."""
    from kivy.input.motionevent import MotionEvent
    class T(MotionEvent):
        def depack(self, args):
            self.is_touch = True
            self.sx, self.sy = args[0] / _fw.width, args[1] / _fw.height
            self.profile = ['pos']
            super().depack(args)
    t = T('harness', 1, (x, y))
    t.scale_for_screen(_fw.width, _fw.height)
    t.grab_current = None
    root.dispatch('on_touch_down', t)
    root.dispatch('on_touch_up', t)
    return t


def square_center(bw, r, c):
    return (bw.offset_x + (c + 0.5) * bw.sq_size, bw.offset_y + (7 - r + 0.5) * bw.sq_size)


def report(name, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + name + ((' - ' + extra) if extra else ''))
    if not ok:
        ERRORS.append(name)


# Expose for scenario scripts
ctx = dict(app=app, game=game, Clock=Clock, tick_for=tick_for, simulate_touch=simulate_touch,
           square_center=square_center, report=report, ERRORS=ERRORS, root=root, fw=_fw)

if len(sys.argv) > 1 or os.environ.get('SCENARIO'):
    exec(open(os.environ['SCENARIO']).read(), ctx)

if ERRORS:
    print("\n==== ERRORS ====")
    for e in ERRORS:
        print(e)
    sys.exit(1)
print("ALL OK")
