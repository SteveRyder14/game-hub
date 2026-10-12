"""Headless harness: runs the Kivy checkers app logic without a GL window.

Usage: python harness.py path/to/main.py
"""
import os, sys, time, types, traceback

os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_GL_BACKEND'] = 'mock'
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['KIVY_NO_CONSOLELOG'] = '1'
os.environ['KIVY_METRICS_DENSITY'] = '2'
os.environ['KIVY_DPI'] = '320'


from kivy.config import Config
Config.set('kivy', 'log_level', 'warning')

# ---- Stub window, installed BEFORE anything imports kivy.core.window ----
from kivy.event import EventDispatcher
from kivy.properties import ListProperty, NumericProperty, BooleanProperty, StringProperty, ObjectProperty
from kivy.graphics import cgl as _cgl
_cgl.cgl_init()
from kivy.graphics import Canvas
from kivy.base import EventLoop


class FakeWindow(EventDispatcher):
    size = ListProperty([390, 800])
    width = NumericProperty(390)
    height = NumericProperty(800)
    system_size = ListProperty([390, 800])
    clearcolor = ListProperty([0, 0, 0, 1])
    rotation = NumericProperty(0)
    softinput_mode = StringProperty('')
    keyboard_height = NumericProperty(0)
    mouse_pos = ListProperty([0, 0])
    focus = BooleanProperty(True)
    fullscreen = BooleanProperty(False)
    borderless = BooleanProperty(False)
    allow_screensaver = BooleanProperty(True)
    minimum_width = NumericProperty(0)
    minimum_height = NumericProperty(0)
    dpi = 320
    _density = 2.0

    def __init__(self, **kw):
        self.register_event_type('on_keyboard')
        self.register_event_type('on_key_down')
        self.register_event_type('on_key_up')
        self.register_event_type('on_resize')
        self.register_event_type('on_draw')
        self.register_event_type('on_flip')
        self.register_event_type('on_touch_down')
        self.register_event_type('on_touch_move')
        self.register_event_type('on_touch_up')
        self.register_event_type('on_request_close')
        self.register_event_type('on_textinput')
        self.register_event_type('on_motion')
        super().__init__(**kw)
        self.canvas = Canvas()
        self.children = []
        self.parent = None
        self.initialized = True
        self.pos = (0, 0)
        self.center = (195, 400)
        self._keyboards = {}

    def on_keyboard(self, *a): pass
    def on_key_down(self, *a): pass
    def on_key_up(self, *a): pass
    def on_resize(self, *a): pass
    def on_draw(self, *a): pass
    def on_flip(self, *a): pass
    def on_touch_down(self, *a): pass
    def on_touch_move(self, *a): pass
    def on_touch_up(self, *a): pass
    def on_request_close(self, *a): pass
    def on_textinput(self, *a): pass
    def on_motion(self, *a): pass

    def add_widget(self, w, canvas=None):
        self.children.insert(0, w)
        w.parent = self
        w.size = self.size
        w.pos = (0, 0)
        self.canvas.add(w.canvas)

    def remove_widget(self, w):
        if w in self.children:
            self.children.remove(w)
            self.canvas.remove(w.canvas)
            w.parent = None

    def to_widget(self, x, y, **kw): return x, y
    def to_window(self, x, y, **kw): return x, y
    def release_all_keyboards(self): pass
    def request_keyboard(self, *a, **kw): return None
    def release_keyboard(self, *a, **kw): pass
    def close(self): pass
    def flip(self): pass
    def update_viewport(self): pass
    def set_title(self, t): pass
    def set_icon(self, i): pass
    def raise_window(self): pass
    def show(self): pass
    def hide(self): pass
    def maximize(self): pass
    def minimize(self): pass
    def restore(self): pass
    def grab_mouse(self): pass
    def ungrab_mouse(self): pass
    def set_system_cursor(self, *a): return True
    def show_cursor(self, *a): pass
    def create_window(self, *a, **kw): pass
    def mainloop(self): pass
    def on_motion_event(self, *a): pass
    def dispatch_motion(self, *a): pass
    def unbind_uid(self, *a, **kw): pass


import kivy.core.window as kcw
_fw = FakeWindow()
kcw.Window = _fw
kcw.WindowBase = FakeWindow
EventLoop.window = _fw

# Metrics: patch density/dpi so dp() works
import kivy.metrics as km
try:
    km.Metrics.density = 2.0
    km.Metrics.dpi = 320
except Exception:
    pass

