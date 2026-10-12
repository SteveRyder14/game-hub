# ==============================================================================
# CHECKERS - GRANDMASTER EDITION  (v1.1 "Material" update)
#
# What changed vs 1.0 (short version, details in the repo PR description):
#   * FPS limit actually works now (it is applied before Kivy's Clock boots AND
#     live when you change it; the 1.0 build only wrote the config after the
#     Clock had already read it, so the setting never did anything).
#   * Two switchable looks in Settings:  Material 3  /  Classic
#   * Glassmorphism panels that can be switched on/off in Settings
#   * New animation layer: screen fade-through transitions, staggered panel
#     reveals, ripple + press feedback on every button, piece "hop" moves,
#     capture bursts, promotion rings, legal-move dots, last-move highlight,
#     piece intro drop-in, confetti on victory, M3 switches & sliders.
#   * Stability: single shared animated background (was 9 copies), network
#     callbacks are tied to a connection id (no stale "offline"/"disconnected"
#     events), opponent moves are queued instead of dropped while animating or
#     paused, board can never get stuck in "animating", back button handling,
#     settings validation, FPS counter overlay for verification.
# ==============================================================================

import os
import json
import math
import random
import threading
import time

SAVE_FILE = 'checkers_data.json'
FPS_OPTIONS = [30, 60, 90, 120]


def _sanitize_fps(value, default=60):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if value in FPS_OPTIONS else default


def _peek_saved_settings():
    """Read the JsonStore file *before* Kivy is imported.

    Kivy's Clock copies ``graphics.maxfps`` out of Config exactly once, when the
    kivy.clock module is imported.  So the only way to honour the saved FPS cap
    at start-up is to read it before anything from Kivy is imported.
    """
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        return data.get('settings', {}) or {}
    except Exception:
        return {}


_BOOT_SETTINGS = _peek_saved_settings()
_BOOT_FPS = _sanitize_fps(_BOOT_SETTINGS.get('fps', 60))

from kivy.config import Config  # noqa: E402

Config.set('graphics', 'multisamples', '0')
Config.set('graphics', 'maxfps', str(_BOOT_FPS))
Config.set('kivy', 'exit_on_escape', '0')

from kivy.app import App  # noqa: E402
from kivy.lang import Builder  # noqa: E402
from kivy.factory import Factory  # noqa: E402
from kivy.logger import Logger  # noqa: E402
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition  # noqa: E402
from kivy.uix.widget import Widget  # noqa: E402
from kivy.uix.button import Button  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.floatlayout import FloatLayout  # noqa: E402
from kivy.uix.scrollview import ScrollView  # noqa: E402,F401  (used by KV)
from kivy.graphics import (Color, Rectangle, Ellipse, Line, PushMatrix, PopMatrix,  # noqa: E402
                           Scale, Rotate, Translate, RoundedRectangle)
from kivy.graphics.texture import Texture  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.core.audio import SoundLoader  # noqa: E402
from kivy.clock import Clock, mainthread  # noqa: E402
from kivy.animation import Animation  # noqa: E402
from kivy.properties import (NumericProperty, BooleanProperty, StringProperty,  # noqa: E402
                             ListProperty, ObjectProperty)
from kivy.metrics import dp, sp  # noqa: E402,F401
from kivy.utils import platform  # noqa: E402
from kivy.storage.jsonstore import JsonStore  # noqa: E402

try:
    from plyer import vibrator
except ImportError:
    vibrator = None

try:
    import websocket
except ImportError:
    websocket = None

# --- Soft shadows -------------------------------------------------------------
# Kivy >= 2.2 ships a GPU BoxShadow instruction.  Older builds fall back to a
# plain offset rounded rectangle so the KV never breaks.
if os.environ.get('CHECKERS_NO_BOXSHADOW'):
    _BoxShadow = None
else:
    try:
        from kivy.graphics import BoxShadow as _BoxShadow
    except Exception:  # pragma: no cover - depends on Kivy version
        _BoxShadow = None

if _BoxShadow is not None:
    SoftShadow = _BoxShadow
    HAS_REAL_SHADOWS = True
else:
    HAS_REAL_SHADOWS = False

    class SoftShadow(RoundedRectangle):
        """Fallback used when BoxShadow is unavailable (Kivy < 2.2)."""

        def __init__(self, **kw):
            self._offset = tuple(kw.pop('offset', (0, 0)))
            kw.pop('blur_radius', None)
            kw.pop('spread_radius', None)
            kw.pop('inset', None)
            br = kw.pop('border_radius', None)
            self._raw_pos = tuple(kw.get('pos', (0, 0)))
            if br is not None:
                kw['radius'] = [br[0]] if isinstance(br, (list, tuple)) else [br]
            kw['pos'] = (self._raw_pos[0] + self._offset[0], self._raw_pos[1] + self._offset[1])
            super().__init__(**kw)

        def _apply(self):
            RoundedRectangle.pos.__set__(self, (self._raw_pos[0] + self._offset[0],
                                                self._raw_pos[1] + self._offset[1]))

        def _get_offset(self):
            return self._offset

        def _set_offset(self, v):
            self._offset = tuple(v)
            self._apply()

        offset = property(_get_offset, _set_offset)

        def _get_pos(self):
            return self._raw_pos

        def _set_pos(self, v):
            self._raw_pos = tuple(v)
            self._apply()

        pos = property(_get_pos, _set_pos)

        def _get_br(self):
            return self.radius

        def _set_br(self, v):
            self.radius = [v[0]] if isinstance(v, (list, tuple)) else [v]

        border_radius = property(_get_br, _set_br)
        blur_radius = property(lambda s: 0, lambda s, v: None)
        spread_radius = property(lambda s: (0, 0), lambda s, v: None)
        inset = property(lambda s: False, lambda s, v: None)

Factory.register('SoftShadow', cls=SoftShadow)

if platform not in ('android', 'ios'):
    Window.size = (390, 800)

ROWS = 8
COLS = 8
BLUE = 1
RED = 2
EMPTY = 0
# Override with CHECKERS_SERVER_URL=ws://127.0.0.1:8000/checkerboard to test against a local server.
WEBSOCKET_URL = os.environ.get("CHECKERS_SERVER_URL", "wss://tictactoe-server-ql1y.onrender.com/checkerboard")

THEMES = {
    'ROYAL': {
        'p1': {'name': 'NAVY', 'light': [0.4, 0.6, 0.85, 1], 'main': [0.15, 0.35, 0.55, 1], 'dark': [0.08, 0.2, 0.35, 1], 'star': [1, 1, 1, 1], 'text': [1, 1, 1, 1]},
        'p2': {'name': 'CRIMSON', 'light': [0.95, 0.45, 0.5, 1], 'main': [0.75, 0.15, 0.25, 1], 'dark': [0.45, 0.05, 0.15, 1], 'star': [1, 1, 1, 1], 'text': [1, 1, 1, 1]},
        'ui': {'accent': [0.95, 0.75, 0.25, 1], 'accent_text': [0.1, 0.1, 0.1, 1], 'panel': [0.08, 0.1, 0.12, 0.85], 'bg_top': [0.05, 0.08, 0.14, 1], 'bg_bot': [0.01, 0.02, 0.04, 1]}
    },
    'MIDNIGHT': {
        'p1': {'name': 'SILVER', 'light': [0.9, 0.9, 0.9, 1], 'main': [0.6, 0.6, 0.6, 1], 'dark': [0.3, 0.3, 0.3, 1], 'star': [0.1, 0.1, 0.1, 1], 'text': [0.05, 0.05, 0.05, 1]},
        'p2': {'name': 'ONYX', 'light': [0.4, 0.4, 0.4, 1], 'main': [0.15, 0.15, 0.15, 1], 'dark': [0.05, 0.05, 0.05, 1], 'star': [1, 1, 1, 1], 'text': [1, 1, 1, 1]},
        'ui': {'accent': [1.0, 1.0, 1.0, 1], 'accent_text': [0.05, 0.05, 0.05, 1], 'panel': [0.12, 0.12, 0.12, 0.9], 'bg_top': [0.12, 0.12, 0.14, 1], 'bg_bot': [0.02, 0.02, 0.02, 1]}
    },
    'CHERRY': {
        'p1': {'name': 'PEARL', 'light': [1.0, 1.0, 1.0, 1], 'main': [0.92, 0.92, 0.92, 1], 'dark': [0.75, 0.75, 0.75, 1], 'star': [0.85, 0.3, 0.45, 1], 'text': [0.15, 0.05, 0.05, 1]},
        'p2': {'name': 'ROSE', 'light': [1.0, 0.65, 0.75, 1], 'main': [0.85, 0.3, 0.45, 1], 'dark': [0.6, 0.15, 0.25, 1], 'star': [1, 1, 1, 1], 'text': [1, 1, 1, 1]},
        'ui': {'accent': [1.0, 0.5, 0.65, 1], 'accent_text': [0.15, 0.05, 0.05, 1], 'panel': [0.18, 0.12, 0.14, 0.85], 'bg_top': [0.18, 0.05, 0.08, 1], 'bg_bot': [0.06, 0.01, 0.02, 1]}
    },
    'EMERALD': {
        'p1': {'name': 'MINT', 'light': [0.6, 0.95, 0.75, 1], 'main': [0.25, 0.75, 0.5, 1], 'dark': [0.1, 0.45, 0.25, 1], 'star': [1, 1, 1, 1], 'text': [1, 1, 1, 1]},
        'p2': {'name': 'SLATE', 'light': [0.55, 0.6, 0.65, 1], 'main': [0.25, 0.3, 0.35, 1], 'dark': [0.1, 0.15, 0.2, 1], 'star': [1, 1, 1, 1], 'text': [1, 1, 1, 1]},
        'ui': {'accent': [0.4, 0.9, 0.6, 1], 'accent_text': [0.05, 0.15, 0.1, 1], 'panel': [0.06, 0.1, 0.08, 0.85], 'bg_top': [0.05, 0.15, 0.10, 1], 'bg_bot': [0.01, 0.04, 0.02, 1]}
    }
}

BOARD_STYLES = {
    'CLASSIC': {'light': [0.92, 0.85, 0.75, 1], 'dark': [0.6, 0.4, 0.2, 1], 'border': [0.35, 0.2, 0.1, 1]},
    'WOOD': {'light': [0.75, 0.55, 0.35, 1], 'dark': [0.35, 0.2, 0.1, 1], 'border': [0.2, 0.1, 0.05, 1]},
    'MARBLE': {'light': [0.95, 0.95, 0.95, 1], 'dark': [0.45, 0.5, 0.55, 1], 'border': [0.2, 0.25, 0.3, 1]},
    'DARK': {'light': [0.4, 0.4, 0.4, 1], 'dark': [0.15, 0.15, 0.15, 1], 'border': [0.08, 0.08, 0.08, 1]},
}

UI_STYLES = ['MATERIAL 3', 'CLASSIC']
VISUAL_OPTIONS = ['HIGH', 'LOW']
BLITZ_OPTIONS = ['OFF', '3 SEC', '5 SEC', '8 SEC']
MATCHMAKING_BUSY = ("SEARCHING FOR MATCH...", "CONNECTING...", "WAKING UP SERVER...")


# ==============================================================================
# 1. NETWORK
# ==============================================================================
class NetworkManager:
    """Thin websocket-client wrapper.

    Every connection gets an id; callbacks coming from an older socket (after a
    cancel / reconnect) are ignored so the UI can never receive a stale
    "connection lost" or "opponent disconnected" event.
    """

    def __init__(self, app):
        self.app = app
        self.ws = None
        self.connected = False
        self._conn_id = 0
        self._events = []

    # -- helpers ---------------------------------------------------------------
    def _cancel_events(self):
        for ev in self._events:
            try:
                ev.cancel()
            except Exception:
                pass
        self._events = []

    def _is_current(self, cid):
        return cid == self._conn_id

    # -- lifecycle -------------------------------------------------------------
    def connect(self):
        if not websocket:
            self.app.show_error("WEBSOCKET LIBRARY MISSING")
            return

        self.disconnect()
        self._conn_id += 1
        cid = self._conn_id

        self.app.matchmaking_status = "CONNECTING..."
        self.app.switch_screen('matchmaking_screen')

        def run_ws():
            try:
                ws = websocket.WebSocketApp(
                    WEBSOCKET_URL,
                    on_open=lambda w: self._on_open(w, cid),
                    on_message=lambda w, m: self._on_message(w, m, cid),
                    on_close=lambda w, c, m: self._on_close(w, c, m, cid),
                    on_error=lambda w, e: self._on_error(w, e, cid),
                )
                self.ws = ws
                ws.run_forever(ping_interval=20, ping_timeout=15)
            except Exception as exc:
                Logger.warning("Network: run_forever ended: %s", exc)

        threading.Thread(target=run_ws, daemon=True).start()
        self._events = [
            Clock.schedule_once(lambda dt: self._check_waking(cid), 4.0),
            Clock.schedule_once(lambda dt: self._check_timeout(cid), 15.0),
        ]

    def _check_waking(self, cid):
        if not self._is_current(cid) or self.connected:
            return
        if self.app.screen_manager.current == 'matchmaking_screen' and self.app.matchmaking_status == "CONNECTING...":
            self.app.matchmaking_status = "WAKING UP SERVER..."

    def _check_timeout(self, cid):
        if not self._is_current(cid) or self.connected:
            return
        if self.app.screen_manager.current == 'matchmaking_screen':
            self.app.show_error("SERVER IS OFFLINE")

    # -- socket callbacks (worker thread) ----------------------------------------
    def _on_open(self, ws, cid):
        if not self._is_current(cid):
            return
        self.connected = True
        payload = {
            "action": "join_queue",
            "color": self.app.human_player,
            "mandatory_jump": self.app.settings_mandatory_jump,
            "blitz": self.app.settings_blitz,
        }
        try:
            ws.send(json.dumps(payload))
        except Exception as exc:
            Logger.warning("Network: join_queue failed: %s", exc)

        def ui(dt):
            if self._is_current(cid):
                self.app.matchmaking_status = "SEARCHING FOR MATCH..."
        Clock.schedule_once(ui)

    def _on_message(self, ws, message, cid):
        if not self._is_current(cid):
            return
        try:
            data = json.loads(message)
        except Exception:
            return
        Clock.schedule_once(lambda dt: self._is_current(cid) and self.app.handle_network_data(data))

    def _on_error(self, ws, error, cid):
        if not self._is_current(cid):
            return
        Logger.warning("Network: error %s", error)
        Clock.schedule_once(lambda dt: self._is_current(cid) and self.app.show_error("CONNECTION LOST"))

    def _on_close(self, ws, close_status_code, close_msg, cid):
        if not self._is_current(cid):
            return
        self.connected = False
        self.ws = None
        Clock.schedule_once(lambda dt: self._is_current(cid) and self.app.handle_disconnect())

    # -- outgoing ----------------------------------------------------------------
    def _send(self, payload):
        if self.connected and self.ws:
            try:
                self.ws.send(json.dumps(payload))
                return True
            except Exception as exc:
                Logger.warning("Network: send failed: %s", exc)
        return False

    def send_move(self, start, end):
        return self._send({"action": "submit_move", "start": list(start), "end": list(end)})

    def request_rematch(self):
        return self._send({"action": "request_rematch"})

    def send_leave_match(self):
        return self._send({"action": "leave_match"})

    def disconnect(self):
        """Close the socket and make every pending callback from it a no-op."""
        self._cancel_events()
        self._conn_id += 1
        ws = self.ws
        self.ws = None
        self.connected = False
        if ws:
            try:
                ws.close()
            except Exception:
                pass


# ==============================================================================
# 2. GAME ENGINE (rules + AI)  -- unchanged from 1.0
# ==============================================================================
class GameEngine:
    @staticmethod
    def get_initial_board(boss_level=0):
        board = [
            [0, 1, 0, 1, 0, 1, 0, 1],
            [1, 0, 1, 0, 1, 0, 1, 0],
            [0, 1, 0, 1, 0, 1, 0, 1],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [2, 0, 2, 0, 2, 0, 2, 0],
            [0, 2, 0, 2, 0, 2, 0, 2],
            [2, 0, 2, 0, 2, 0, 2, 0]
        ]
        if boss_level == 3:
            board[7][0] = -2
            board[7][4] = -2
        elif boss_level == 4:
            board[7][0] = -2
            board[7][2] = -2
            board[7][4] = -2
            board[7][6] = -2
        return board

    @staticmethod
    def is_valid_move(start_r, start_c, end_r, end_c, player, board_array):
        if not (0 <= end_r < ROWS and 0 <= end_c < COLS):
            return {'valid': False}
        if board_array[end_r][end_c] != EMPTY:
            return {'valid': False}
        piece_type = board_array[start_r][start_c]
        row_diff = end_r - start_r
        col_diff = abs(end_c - start_c)
        is_king = piece_type < 0
        direction = 1 if player == BLUE else -1

        if not is_king and row_diff == direction and col_diff == 1:
            return {'valid': True, 'type': 'normal'}
        if is_king and abs(row_diff) == 1 and col_diff == 1:
            return {'valid': True, 'type': 'normal'}

        if abs(row_diff) == 2 and col_diff == 2:
            jumped_r = (start_r + end_r) // 2
            jumped_c = (start_c + end_c) // 2
            jumped_piece = board_array[jumped_r][jumped_c]

            if jumped_piece != EMPTY and abs(jumped_piece) != player:
                if not is_king and row_diff != direction * 2:
                    return {'valid': False}
                return {'valid': True, 'type': 'jump', 'jumped_r': jumped_r, 'jumped_c': jumped_c}
        return {'valid': False}

    @staticmethod
    def get_valid_moves(player, board_array, force_jump=False):
        moves = []
        for r in range(ROWS):
            for c in range(COLS):
                if board_array[r][c] != EMPTY and abs(board_array[r][c]) == player:
                    for er in range(ROWS):
                        for ec in range(COLS):
                            info = GameEngine.is_valid_move(r, c, er, ec, player, board_array)
                            if info['valid']:
                                moves.append({'start': (r, c), 'end': (er, ec), 'info': info})
        if force_jump:
            jump_moves = [m for m in moves if m['info']['type'] == 'jump']
            if jump_moves:
                return jump_moves
        return moves

    @staticmethod
    def apply_temp_move(temp_board, move_obj, player):
        sr, sc = move_obj['start']
        er, ec = move_obj['end']
        info = move_obj['info']
        piece_type = temp_board[sr][sc]
        temp_board[sr][sc] = EMPTY

        if info['type'] == 'jump':
            temp_board[info['jumped_r']][info['jumped_c']] = EMPTY

        if (player == BLUE and er == ROWS - 1) or (player == RED and er == 0):
            if piece_type > 0:
                piece_type = -piece_type
        temp_board[er][ec] = piece_type

    @staticmethod
    def evaluate_board(board_array, ai_player):
        score = 0
        opponent = RED if ai_player == BLUE else BLUE
        for r in range(ROWS):
            for c in range(COLS):
                piece = board_array[r][c]
                if piece == EMPTY:
                    continue

                abs_piece = abs(piece)
                is_king = piece < 0
                edge_bonus = 2 if c == 0 or c == COLS - 1 else 0
                center_bonus = 3 if (2 <= r <= 5 and 2 <= c <= 5) else 0
                advancement = 0 if is_king else (r if abs_piece == BLUE else 7 - r)

                piece_val = (25 + center_bonus) if is_king else (10 + advancement + edge_bonus)
                if abs_piece == ai_player:
                    score += piece_val
                elif abs_piece == opponent:
                    score -= piece_val
        return score + random.uniform(-0.4, 0.4)

    @staticmethod
    def minimax(board_array, depth, alpha, beta, is_maximizing, ai_player, opponent, force_jump):
        if depth == 0:
            return {'score': GameEngine.evaluate_board(board_array, ai_player), 'move': None}

        current_player = ai_player if is_maximizing else opponent
        valid_moves = GameEngine.get_valid_moves(current_player, board_array, force_jump)

        if not valid_moves:
            return {'score': -10000 if is_maximizing else 10000, 'move': None}
        valid_moves.sort(key=lambda m: 1 if m['info']['type'] == 'jump' else 0, reverse=True)

        best_move = None
        if is_maximizing:
            max_eval = float('-inf')
            for move in valid_moves:
                temp_board = [row[:] for row in board_array]
                GameEngine.apply_temp_move(temp_board, move, current_player)
                evaluation = GameEngine.minimax(temp_board, depth - 1, alpha, beta, False, ai_player, opponent, force_jump)['score']
                if evaluation > max_eval:
                    max_eval = evaluation
                    best_move = move
                alpha = max(alpha, evaluation)
                if beta <= alpha:
                    break
            return {'score': max_eval, 'move': best_move}
        else:
            min_eval = float('inf')
            for move in valid_moves:
                temp_board = [row[:] for row in board_array]
                GameEngine.apply_temp_move(temp_board, move, current_player)
                evaluation = GameEngine.minimax(temp_board, depth - 1, alpha, beta, True, ai_player, opponent, force_jump)['score']
                if evaluation < min_eval:
                    min_eval = evaluation
                    best_move = move
                beta = min(beta, evaluation)
                if beta <= alpha:
                    break
            return {'score': min_eval, 'move': best_move}


# ==============================================================================
# 3. VISUAL BUILDING BLOCKS
# ==============================================================================
class GradientBackground(Widget):
    top_color = ListProperty([0, 0, 0, 1])
    bot_color = ListProperty([0, 0, 0, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._texture = Texture.create(size=(1, 2), colorfmt='rgba')
        self.bind(pos=self.update_rect, size=self.update_rect, top_color=self.update_texture, bot_color=self.update_texture)
        Clock.schedule_once(self.update_texture, 0)

    def update_texture(self, *args):
        try:
            tc = list(self.top_color) + [1, 1, 1, 1]
            bc = list(self.bot_color) + [1, 1, 1, 1]
            t_rgba = [max(0, min(255, int(c * 255))) for c in tc[:4]]
            b_rgba = [max(0, min(255, int(c * 255))) for c in bc[:4]]
            buf = bytes(b_rgba + t_rgba)
            self._texture.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
            self.update_rect()
        except Exception:
            pass

    def update_rect(self, *args):
        self.canvas.before.clear()
        if self.width <= 0 or self.height <= 0:
            return
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size, texture=self._texture)


class AmbientFlair(Widget):
    """Three slowly breathing colour orbs. Only ever ONE instance exists now
    (shared behind all screens) and it stops animating in LOW visual mode."""
    orb1_scale = NumericProperty(1.0)
    orb2_scale = NumericProperty(1.0)
    orb3_scale = NumericProperty(1.0)
    animating = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self._auto_start, 0.5)

    def _auto_start(self, dt):
        app = App.get_running_app()
        self.set_animating(bool(app.fx_high) if app else True)

    def set_animating(self, value):
        if value == self.animating:
            return
        self.animating = value
        Animation.cancel_all(self, 'orb1_scale', 'orb2_scale', 'orb3_scale')
        if not value:
            Animation(orb1_scale=1.0, orb2_scale=1.0, orb3_scale=1.0, duration=0.6).start(self)
            return
        a1 = Animation(orb1_scale=1.15, duration=4.5, transition='in_out_sine') + Animation(orb1_scale=0.9, duration=4.5, transition='in_out_sine')
        a1.repeat = True
        a1.start(self)
        a2 = Animation(orb2_scale=1.2, duration=6.0, transition='in_out_sine') + Animation(orb2_scale=0.85, duration=6.0, transition='in_out_sine')
        a2.repeat = True
        a2.start(self)
        a3 = Animation(orb3_scale=1.1, duration=5.2, transition='in_out_sine') + Animation(orb3_scale=0.95, duration=5.2, transition='in_out_sine')
        a3.repeat = True
        a3.start(self)


class GlassPanel(BoxLayout):
    """Card surface. Looks like frosted glass or a solid M3 container depending
    on the app's settings (all styling lives in the KV rule)."""
    reveal_dy = NumericProperty(0.0)


class CompactPlayerCard(BoxLayout):
    player_name = StringProperty("PLAYER")
    piece_count = NumericProperty(12)
    theme_color = ListProperty([1, 1, 1, 1])
    is_active = BooleanProperty(False)
    aura_scale = NumericProperty(1.0)
    aura_alpha = NumericProperty(0.0)
    count_bump = NumericProperty(1.0)

    def on_is_active(self, instance, value):
        Animation.cancel_all(self, 'aura_scale', 'aura_alpha')
        if value:
            self.aura_scale = 1.0
            self.aura_alpha = 0.5
            anim = Animation(aura_scale=1.8, aura_alpha=0.0, duration=1.5, transition='out_sine')
            anim += Animation(aura_scale=1.0, aura_alpha=0.5, duration=0.0)
            anim.repeat = True
            anim.start(self)
        else:
            self.aura_scale = 1.0
            self.aura_alpha = 0.0

    def on_piece_count(self, instance, value):
        Animation.cancel_all(self, 'count_bump')
        self.count_bump = 1.25
        Animation(count_bump=1.0, duration=0.35, transition='out_back').start(self)


class AnimBtn(Button):
    """Button with press scale + Material ripple (ripple is drawn by the KV rule)."""
    anim_scale = NumericProperty(1.0)
    ripple_x = NumericProperty(0.0)
    ripple_y = NumericProperty(0.0)
    ripple_r = NumericProperty(0.0)
    ripple_alpha = NumericProperty(0.0)
    fill = ListProperty([0, 0, 0, 0])
    fill_down = ListProperty([0, 0, 0, 0])
    outline = ListProperty([0, 0, 0, 0])
    shadow_mul = NumericProperty(1.0)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and not self.disabled:
            self.ripple_x, self.ripple_y = touch.pos
        return super().on_touch_down(touch)

    def on_press(self):
        super().on_press()
        app = App.get_running_app()
        if app:
            app.play_click_sound()
            app.trigger_haptic(0.02)
        Animation.cancel_all(self, 'anim_scale', 'ripple_r', 'ripple_alpha')
        Animation(anim_scale=0.96, duration=0.08, transition='out_quad').start(self)
        if app and app.fx_high:
            self.ripple_r = 0
            self.ripple_alpha = 0.22
            Animation(ripple_r=max(self.width, self.height) * 1.1, duration=0.45, transition='out_quad').start(self)
        else:
            self.ripple_alpha = 0

    def on_release(self):
        super().on_release()
        Animation.cancel_all(self, 'anim_scale')
        Animation(anim_scale=1.0, duration=0.28, transition='out_back').start(self)
        Animation(ripple_alpha=0.0, duration=0.35, transition='out_quad').start(self)


class PlayerToggle(Widget):
    thumb_progress = NumericProperty(0.0)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            app.play_click_sound()
            app.trigger_haptic(0.03)
            app.human_player = RED if app.human_player == BLUE else BLUE
            target = 0.0 if app.human_player == BLUE else 1.0
            Animation.cancel_all(self, 'thumb_progress')
            Animation(thumb_progress=target, duration=0.22, transition='out_cubic').start(self)
            return True
        return super().on_touch_down(touch)

    def on_kv_post(self, base_widget):
        app = App.get_running_app()
        if app:
            self.thumb_progress = 0.0 if app.human_player == BLUE else 1.0


class M3Switch(Widget):
    """Material 3 style switch (track grows thumb when on). Replaces the dated
    image-based Kivy Switch."""
    active = BooleanProperty(False)
    progress = NumericProperty(0.0)
    press_scale = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(52), dp(32))
        self.progress = 1.0 if self.active else 0.0

    def on_active(self, instance, value):
        Animation.cancel_all(self, 'progress')
        Animation(progress=1.0 if value else 0.0, duration=0.2, transition='out_cubic').start(self)

    def on_touch_down(self, touch):
        if self.disabled or not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        app = App.get_running_app()
        if app:
            app.play_click_sound()
            app.trigger_haptic(0.02)
        Animation.cancel_all(self, 'press_scale')
        self.press_scale = 1.18
        Animation(press_scale=1.0, duration=0.3, transition='out_back').start(self)
        self.active = not self.active
        return True


class M3Slider(Widget):
    min = NumericProperty(0.0)
    max = NumericProperty(100.0)
    value = NumericProperty(0.0)
    dragging = BooleanProperty(False)
    track_color = ListProperty([0.95, 0.75, 0.25, 1])

    def _set_from_touch(self, touch):
        pad = dp(12)
        usable = max(self.width - 2 * pad, 1)
        ratio = (touch.x - self.x - pad) / usable
        ratio = max(0.0, min(1.0, ratio))
        self.value = self.min + ratio * (self.max - self.min)

    def on_touch_down(self, touch):
        if self.disabled or not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        touch.grab(self)
        self.dragging = True
        self._set_from_touch(touch)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self._set_from_touch(touch)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self.dragging = False
            app = App.get_running_app()
            if app:
                app.play_click_sound()
            return True
        return super().on_touch_up(touch)

    @property
    def ratio(self):
        span = (self.max - self.min) or 1.0
        return max(0.0, min(1.0, (self.value - self.min) / span))


class HintTargetWidget(Widget):
    anim_alpha = NumericProperty(0.0)

    def start_anim(self):
        self.anim_alpha = 0.2
        anim = Animation(anim_alpha=0.6, duration=0.6, transition='in_out_sine')
        anim += Animation(anim_alpha=0.2, duration=0.6, transition='in_out_sine')
        anim.repeat = True
        anim.start(self)


class MoveDot(Widget):
    """Legal-move indicator: dot for a step, ring for a capture."""
    is_jump = BooleanProperty(False)
    dot_scale = NumericProperty(0.0)
    dot_alpha = NumericProperty(0.0)

    def show(self, animated=True, delay=0.0):
        Animation.cancel_all(self, 'dot_scale', 'dot_alpha')
        if not animated:
            self.dot_scale = 1.0
            self.dot_alpha = 1.0
            return
        self.dot_scale = 0.3
        self.dot_alpha = 0.0
        anim = Animation(duration=delay) + Animation(dot_scale=1.0, dot_alpha=1.0, duration=0.22, transition='out_back')
        anim.start(self)


class BurstRing(Widget):
    """Expanding ring used for promotions and captures."""
    ring_scale = NumericProperty(0.2)
    ring_alpha = NumericProperty(0.0)
    color = ListProperty([1, 0.84, 0, 1])
    line_width = NumericProperty(dp(3))

    def play(self, duration=0.5, max_scale=1.9):
        self.ring_scale = 0.3
        self.ring_alpha = 0.9
        anim = Animation(ring_scale=max_scale, ring_alpha=0.0, duration=duration, transition='out_cubic')
        anim.bind(on_complete=lambda *a: self.parent and self.parent.remove_widget(self))
        anim.start(self)


class CaptureBurst(Widget):
    """Small shard particles flying out of a captured piece."""
    progress = NumericProperty(0.0)
    color = ListProperty([1, 1, 1, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._parts = []
        n = 9
        with self.canvas:
            for i in range(n):
                ang = (i / n) * math.tau + random.uniform(-0.25, 0.25)
                spd = random.uniform(0.75, 1.25)
                sz = random.uniform(0.09, 0.16)
                col = Color(1, 1, 1, 0)
                ell = Ellipse(pos=(0, 0), size=(1, 1))
                self._parts.append((col, ell, ang, spd, sz))
        self.bind(pos=self._update, size=self._update, color=self._update)

    def on_progress(self, *args):
        self._update()

    def _update(self, *args):
        p = self.progress
        eased = 1 - (1 - p) ** 3
        cx, cy = self.center
        reach = self.width * 1.1
        for col, ell, ang, spd, sz in self._parts:
            dist = reach * spd * eased
            size = max(self.width * sz * (1 - p * 0.6), 0.5)
            ell.pos = (cx + math.cos(ang) * dist - size / 2, cy + math.sin(ang) * dist - size / 2 - (p ** 2) * self.height * 0.5)
            ell.size = (size, size)
            col.rgba = (self.color[0], self.color[1], self.color[2], max(0.0, 1.0 - p) * 0.95)

    def play(self, duration=0.55):
        self.progress = 0.0
        anim = Animation(progress=1.0, duration=duration, transition='linear')
        anim.bind(on_complete=lambda *a: self.parent and self.parent.remove_widget(self))
        anim.start(self)


class RadarPing(Widget):
    ping_scale = NumericProperty(1.0)
    ping_alpha = NumericProperty(0.8)
    ping2_scale = NumericProperty(1.0)
    ping2_alpha = NumericProperty(0.0)
    core_scale = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_ping()

    def start_ping(self):
        anim = Animation(ping_scale=3.0, ping_alpha=0.0, duration=1.6, transition='out_sine')
        anim += Animation(ping_scale=1.0, ping_alpha=0.8, duration=0.0)
        anim.repeat = True
        anim.start(self)
        anim2 = Animation(duration=0.8) + Animation(ping2_scale=3.0, ping2_alpha=0.0, duration=1.6, transition='out_sine')
        anim2 += Animation(ping2_scale=1.0, ping2_alpha=0.6, duration=0.0)
        anim2.repeat = True
        anim2.start(self)
        core = Animation(core_scale=1.12, duration=0.8, transition='in_out_sine') + Animation(core_scale=1.0, duration=0.8, transition='in_out_sine')
        core.repeat = True
        core.start(self)


class ConfettiLayer(Widget):
    """Lightweight confetti (no textures, ~50 rotated rectangles)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._parts = []
        self._event = None

    def burst(self, colors):
        self.stop()
        w = max(self.width, 1)
        h = max(self.height, 1)
        with self.canvas:
            for _ in range(54):
                col = random.choice(colors)
                size = (random.uniform(dp(6), dp(11)), random.uniform(dp(4), dp(7)))
                PushMatrix()
                trans = Translate(0, 0, 0)
                rot = Rotate(angle=random.uniform(0, 360), origin=(0, 0))
                c = Color(col[0], col[1], col[2], 1)
                Rectangle(pos=(-size[0] / 2, -size[1] / 2), size=size)
                PopMatrix()
                self._parts.append({
                    'x': self.x + w * random.uniform(0.3, 0.7),
                    'y': self.y + h * random.uniform(0.45, 0.6),
                    'vx': random.uniform(-w * 0.55, w * 0.55),
                    'vy': random.uniform(h * 0.6, h * 1.25),
                    'spin': random.uniform(-540, 540),
                    'trans': trans, 'rot': rot, 'col': c,
                    'life': random.uniform(2.2, 3.2), 't': 0.0,
                })
        self._event = Clock.schedule_interval(self._step, 1 / 60.0)

    def _step(self, dt):
        alive = False
        g = self.height * 1.4
        for p in self._parts:
            p['t'] += dt
            if p['t'] >= p['life']:
                p['col'].a = 0
                continue
            alive = True
            p['vy'] -= g * dt
            p['vx'] *= (1 - 1.6 * dt)
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['rot'].angle += p['spin'] * dt
            p['trans'].xy = (p['x'], p['y'])
            p['col'].a = min(1.0, (p['life'] - p['t']) / 0.6)
        if not alive:
            self.stop()

    def stop(self):
        if self._event:
            self._event.cancel()
            self._event = None
        self.canvas.clear()
        self._parts = []


class FpsOverlay(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._event = None

    def set_enabled(self, enabled):
        if self._event:
            self._event.cancel()
            self._event = None
        self.opacity = 1 if enabled else 0
        if enabled:
            self._event = Clock.schedule_interval(self._tick, 0.5)
            self._tick(0)

    def _tick(self, dt):
        try:
            self.text = "%d FPS  (cap %d)" % (round(Clock.get_fps()), int(Clock._max_fps))
        except Exception:
            self.text = "%d FPS" % round(Clock.get_fps())


class BaseScreen(Screen):
    """Screen with a Material 'fade-through' entrance and staggered panel reveal."""
    enter_scale = NumericProperty(1.0)
    enter_dy = NumericProperty(0.0)

    def play_enter(self):
        app = App.get_running_app()
        Animation.cancel_all(self, 'opacity', 'enter_scale', 'enter_dy')
        panels = [w for w in self.walk(restrict=True) if isinstance(w, GlassPanel)]
        if not app or not app.fx_high:
            self.opacity = 1
            self.enter_scale = 1.0
            self.enter_dy = 0
            for p in panels:
                Animation.cancel_all(p, 'opacity', 'reveal_dy')
                p.opacity = 1
                p.reveal_dy = 0
            return
        self.opacity = 0
        self.enter_scale = 0.96
        self.enter_dy = dp(10)
        Animation(opacity=1, enter_scale=1.0, enter_dy=0, duration=0.26, transition='out_cubic').start(self)
        for i, p in enumerate(panels[:8]):
            Animation.cancel_all(p, 'opacity', 'reveal_dy')
            p.opacity = 0
            p.reveal_dy = dp(22)
            anim = Animation(duration=0.05 * i) + Animation(opacity=1, reveal_dy=0, duration=0.34, transition='out_cubic')
            anim.start(p)


# ==============================================================================
# 4. KV DESIGN LANGUAGE
# ==============================================================================
KV = '''
#:import math math

<BackgroundLayer@FloatLayout>:
    GradientBackground:
        top_color: app.theme_bg_top
        bot_color: app.theme_bg_bot
        pos: self.pos
        size: self.size
    AmbientFlair:
        id: flair
        pos: self.pos
        size: self.size

<AmbientFlair>:
    canvas.before:
        PushMatrix:
        Scale:
            x: self.orb1_scale
            y: self.orb1_scale
            origin: (self.x + self.width * 0.15, self.top - self.width * 0.05)
        Color:
            rgba: app.theme_p1_main[0], app.theme_p1_main[1], app.theme_p1_main[2], 0.15
        Ellipse:
            pos: (self.x - self.width * 0.3, self.top - self.width * 0.5)
            size: (max(self.width * 0.9, 1), max(self.width * 0.9, 1))
        PopMatrix:
        PushMatrix:
        Scale:
            x: self.orb2_scale
            y: self.orb2_scale
            origin: (self.right - self.width * 0.4, self.center_y - self.width * 0.3)
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], 0.08
        Ellipse:
            pos: (self.right - self.width * 0.4, self.center_y - self.width * 0.3)
            size: (max(self.width * 0.8, 1), max(self.width * 0.8, 1))
        PopMatrix:
        PushMatrix:
        Scale:
            x: self.orb3_scale
            y: self.orb3_scale
            origin: (self.x - self.width * 0.1, self.y - self.width * 0.2)
        Color:
            rgba: app.theme_p2_main[0], app.theme_p2_main[1], app.theme_p2_main[2], 0.12
        Ellipse:
            pos: (self.x - self.width * 0.1, self.y - self.width * 0.2)
            size: (max(self.width * 0.7, 1), max(self.width * 0.7, 1))
        PopMatrix:
    canvas:
        Color:
            rgba: 1, 1, 1, 0.03
        Line:
            circle: [self.right - dp(20), self.top - dp(50), max(self.width * 0.4, 1)]
            width: dp(1.5)
        Line:
            circle: [self.x + dp(40), self.y + dp(100), max(self.width * 0.5, 1)]
            width: dp(1)

<BaseScreen>:
    canvas.before:
        PushMatrix:
        Translate:
            y: self.enter_dy
        Scale:
            x: self.enter_scale
            y: self.enter_scale
            origin: self.center
    canvas.after:
        PopMatrix:

<FpsOverlay>:
    size_hint: None, None
    size: dp(118), dp(22)
    pos_hint: {'x': 0.02, 'top': 0.995}
    font_size: '11sp'
    bold: True
    color: 0.6, 1, 0.6, 1
    opacity: 0
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.55 * (1 if self.opacity else 0)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(11)]

<ToastLabel@Label>:
    size_hint: None, None
    size: min(dp(320), self.texture_size[0] + dp(36)), dp(40)
    pos_hint: {'center_x': 0.5, 'y': 0.06}
    font_size: '12sp'
    bold: True
    opacity: 0
    color: app.theme_bg_top[0], app.theme_bg_top[1], app.theme_bg_top[2], 1
    canvas.before:
        Color:
            rgba: 0.93, 0.93, 0.95, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(20) if app.ui_material else dp(10)]

# ---------------- PIECES & BOARD OVERLAYS ----------------
<PieceWidget>:
    canvas.before:
        # Ground shadow (NOT scaled, so a lifted piece visibly leaves the board)
        Color:
            rgba: 0, 0, 0, (0.28 - (self.piece_scale - 1) * 0.35) * self.opacity if self.piece_scale > 0.05 else 0
        Ellipse:
            pos: (self.x - dp(1) - (self.piece_scale - 1) * dp(6), self.y - dp(4) - (self.piece_scale - 1) * dp(18))
            size: (max(self.width + dp(2) + (self.piece_scale - 1) * dp(12), 1), max(self.height + dp(2) + (self.piece_scale - 1) * dp(12), 1))
        PushMatrix:
        Scale:
            x: self.piece_scale
            y: self.piece_scale
            z: 1.0
            origin: self.center
    canvas:
        # King's Aura
        Color:
            rgba: (1, 0.84, 0, (1.5 - self.king_pulse) * self.opacity) if self.piece_type < 0 else (0, 0, 0, 0)
        Line:
            circle: [self.center_x, self.center_y, max((self.width * self.king_pulse) / 2, 1)]
            width: dp(2)
        # Selection Highlight
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], (self.highlight_alpha * self.opacity) * 0.25
        Ellipse:
            pos: self.center_x - (self.width * self.highlight_scale) / 2, self.center_y - (self.height * self.highlight_scale) / 2
            size: (max(self.width * self.highlight_scale, 1), max(self.height * self.highlight_scale, 1))
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], self.highlight_alpha * self.opacity
        Line:
            ellipse: [self.center_x - (self.width * self.highlight_scale) / 2, self.center_y - (self.height * self.highlight_scale) / 2, max(self.width * self.highlight_scale, 1), max(self.height * self.highlight_scale, 1)]
            width: dp(2)
        # Body: rim
        Color:
            rgba: (app.theme_p1_dark[0], app.theme_p1_dark[1], app.theme_p1_dark[2], self.opacity) if abs(self.piece_type) == 1 else (app.theme_p2_dark[0], app.theme_p2_dark[1], app.theme_p2_dark[2], self.opacity)
        Ellipse:
            pos: self.pos
            size: self.size
        # Body: main
        Color:
            rgba: (app.theme_p1_main[0], app.theme_p1_main[1], app.theme_p1_main[2], self.opacity) if abs(self.piece_type) == 1 else (app.theme_p2_main[0], app.theme_p2_main[1], app.theme_p2_main[2], self.opacity)
        Ellipse:
            pos: (self.x + dp(2), self.y + dp(2))
            size: (max(self.width - dp(4), 0.1), max(self.height - dp(4), 0.1))
        # Body: top face
        Color:
            rgba: (app.theme_p1_light[0], app.theme_p1_light[1], app.theme_p1_light[2], self.opacity) if abs(self.piece_type) == 1 else (app.theme_p2_light[0], app.theme_p2_light[1], app.theme_p2_light[2], self.opacity)
        Ellipse:
            pos: (self.x + dp(8), self.y + dp(8))
            size: (max(self.width - dp(16), 0.1), max(self.height - dp(16), 0.1))
        # Specular highlight
        Color:
            rgba: 1, 1, 1, 0.22 * self.opacity
        Ellipse:
            pos: (self.x + self.width * 0.28, self.y + self.height * 0.58)
            size: (max(self.width * 0.3, 0.1), max(self.height * 0.16, 0.1))
        Color:
            rgba: 1, 1, 1, 0.2 * self.opacity
        Line:
            ellipse: [self.x + dp(4), self.y + dp(4), max(self.width - dp(8), 0.1), max(self.height - dp(8), 0.1)]
            width: dp(1.2)
        # King mark
        Color:
            rgba: (app.theme_p1_star[0], app.theme_p1_star[1], app.theme_p1_star[2], 0.9 * self.opacity) if (abs(self.piece_type) == 1 and self.piece_type < 0) else ((app.theme_p2_star[0], app.theme_p2_star[1], app.theme_p2_star[2], 0.9 * self.opacity) if (abs(self.piece_type) == 2 and self.piece_type < 0) else (1, 1, 1, 0))
        Ellipse:
            pos: (self.x + (self.width - self.width * 0.35) / 2, self.y + (self.height - self.height * 0.35) / 2)
            size: (max(self.width * 0.35, 1), max(self.height * 0.35, 1))
        Line:
            circle: [self.center_x, self.center_y, max(self.width * 0.26, 1)]
            width: dp(1.2)
    canvas.after:
        PopMatrix:

<HintTargetWidget>:
    canvas.before:
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], self.anim_alpha * 0.2
        RoundedRectangle:
            pos: (self.x + dp(4), self.y + dp(4))
            size: (max(self.width - dp(8), 1), max(self.height - dp(8), 1))
            radius: [dp(10)]
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], self.anim_alpha * 0.8
        Line:
            rounded_rectangle: [self.x + dp(4), self.y + dp(4), max(self.width - dp(8), 1), max(self.height - dp(8), 1), dp(10)]
            width: dp(1.5)

<MoveDot>:
    canvas:
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], (0.0 if self.is_jump else 0.55) * self.dot_alpha
        Ellipse:
            pos: (self.center_x - self.width * 0.16 * self.dot_scale, self.center_y - self.height * 0.16 * self.dot_scale)
            size: (max(self.width * 0.32 * self.dot_scale, 1), max(self.height * 0.32 * self.dot_scale, 1))
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], (0.85 if self.is_jump else 0.0) * self.dot_alpha
        Line:
            circle: [self.center_x, self.center_y, max(self.width * 0.40 * self.dot_scale, 1)]
            width: dp(3)

<BurstRing>:
    canvas:
        Color:
            rgba: self.color[0], self.color[1], self.color[2], self.ring_alpha
        Line:
            circle: [self.center_x, self.center_y, max(self.width * 0.5 * self.ring_scale, 1)]
            width: self.line_width

# ---------------- SURFACES ----------------
<GlassPanel>:
    orientation: 'vertical'
    size_hint: None, None
    width: dp(320)
    height: self.minimum_height
    canvas.before:
        PushMatrix:
        Translate:
            y: self.reveal_dy
        Color:
            rgba: 0, 0, 0, app.shadow_alpha
        SoftShadow:
            pos: self.pos
            size: (max(self.width, 1), max(self.height, 1))
            offset: (0, -dp(6))
            blur_radius: dp(24)
            border_radius: [app.r_panel, app.r_panel, app.r_panel, app.r_panel]
        Color:
            rgba: app.panel_fill
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.r_panel]
        Color:
            rgba: 1, 1, 1, app.sheen_alpha
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.r_panel]
            texture: app.sheen_tex
        Color:
            rgba: app.panel_border
        Line:
            rounded_rectangle: [self.x, self.y, max(self.width, 1), max(self.height, 1), app.r_panel]
            width: dp(1)
        Color:
            rgba: 1, 1, 1, app.glass_edge_alpha
        Line:
            points: [self.x + app.r_panel, self.top - dp(0.6), self.right - app.r_panel, self.top - dp(0.6)]
            width: dp(1)
    canvas.after:
        PopMatrix:

<SectionLabel@Label>:
    font_size: '12sp'
    bold: True
    size_hint_y: None
    height: dp(20)
    text_size: self.size
    halign: 'left'
    valign: 'bottom'
    padding: (dp(6) if app.ui_material else 0), 0

<CompactPlayerCard>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(55)
    padding: [dp(10), dp(5), dp(10), dp(5)]
    spacing: dp(10)
    canvas.before:
        Color:
            rgba: self.theme_color[0], self.theme_color[1], self.theme_color[2], self.aura_alpha * 0.3
        RoundedRectangle:
            pos: (self.x - dp(2), self.y - dp(2))
            size: (max(self.width + dp(4), 1), max(self.height + dp(4), 1))
            radius: [app.r_card + dp(2)]
        Color:
            rgba: 0, 0, 0, app.shadow_alpha * 0.8
        SoftShadow:
            pos: self.pos
            size: (max(self.width, 1), max(self.height, 1))
            offset: (0, -dp(3))
            blur_radius: dp(12)
            border_radius: [app.r_card, app.r_card, app.r_card, app.r_card]
        Color:
            rgba: app.panel_fill
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.r_card]
        Color:
            rgba: 1, 1, 1, app.sheen_alpha
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.r_card]
            texture: app.sheen_tex
        Color:
            rgba: (self.theme_color[0], self.theme_color[1], self.theme_color[2], 0.85) if self.is_active else app.panel_border
        Line:
            rounded_rectangle: [self.x, self.y, max(self.width, 1), max(self.height, 1), app.r_card]
            width: dp(1.5) if self.is_active else dp(1)
    Widget:
        size_hint_x: None
        width: dp(26)
        canvas.before:
            Color:
                rgba: root.theme_color[0], root.theme_color[1], root.theme_color[2], root.aura_alpha
            Ellipse:
                pos: (self.center_x - (dp(13) * root.aura_scale), self.center_y - (dp(13) * root.aura_scale))
                size: (max(dp(26) * root.aura_scale, 1), max(dp(26) * root.aura_scale, 1))
            Color:
                rgba: root.theme_color
            Ellipse:
                pos: (self.center_x - dp(13), self.center_y - dp(13))
                size: (dp(26), dp(26))
            Color:
                rgba: 1, 1, 1, 0.2
            Line:
                circle: [self.center_x, self.center_y, dp(13)]
                width: dp(1.2)
    BoxLayout:
        orientation: 'vertical'
        Label:
            text: root.player_name
            font_size: '12sp'
            bold: True
            color: (1, 1, 1, 1) if root.is_active else (0.7, 0.7, 0.7, 1)
            text_size: self.size
            halign: 'left'
            valign: 'bottom'
            shorten: True
            shorten_from: 'right'
        Label:
            text: ("[b]" + app.L("Your turn", app.ui_material) + "[/b]  •  " if root.is_active else "") + str(root.piece_count) + " " + app.L("left", app.ui_material)
            markup: True
            font_size: '10sp'
            color: (root.theme_color[0], root.theme_color[1], root.theme_color[2], 1) if root.is_active else (0.5, 0.5, 0.5, 1)
            text_size: self.size
            halign: 'left'
            valign: 'top'
            canvas.before:
                PushMatrix:
                Scale:
                    x: root.count_bump
                    y: root.count_bump
                    origin: (self.x + dp(8), self.center_y)
            canvas.after:
                PopMatrix:

# ---------------- BUTTONS ----------------
<PremiumBtn@AnimBtn>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    bold: True
    font_size: '14sp'
    size_hint_y: None
    height: dp(54)
    disabled_color: 1, 1, 1, 0.38
    canvas.before:
        PushMatrix:
        Scale:
            x: self.anim_scale
            y: self.anim_scale
            z: 1.0
            origin: self.center
        Color:
            rgba: 0, 0, 0, (app.shadow_alpha * self.shadow_mul * (0 if self.disabled else 1)) * (0.6 if self.state == 'down' else 1)
        SoftShadow:
            pos: self.pos
            size: (max(self.width, 1), max(self.height, 1))
            offset: (0, app.btn_shadow_dy)
            blur_radius: app.btn_shadow_blur
            border_radius: [app.btn_r(self.height, app.ui_material)] * 4
        Color:
            rgba: app.disabled_fill if self.disabled else (self.fill_down if self.state == 'down' else self.fill)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.btn_r(self.height, app.ui_material)]
        Color:
            rgba: 1, 1, 1, app.sheen_alpha * 0.6 * (0 if self.disabled else 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.btn_r(self.height, app.ui_material)]
            texture: app.sheen_tex
        Color:
            rgba: self.outline
        Line:
            rounded_rectangle: [self.x, self.y, max(self.width, 1), max(self.height, 1), app.btn_r(self.height, app.ui_material)]
            width: dp(1)
    canvas.after:
        StencilPush:
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.btn_r(self.height, app.ui_material)]
        StencilUse:
        Color:
            rgba: 1, 1, 1, self.ripple_alpha
        Ellipse:
            pos: (self.ripple_x - self.ripple_r, self.ripple_y - self.ripple_r)
            size: (max(self.ripple_r * 2, 1), max(self.ripple_r * 2, 1))
        StencilUnUse:
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [app.btn_r(self.height, app.ui_material)]
        StencilPop:
        PopMatrix:

<MenuBtnP1@PremiumBtn>:
    color: app.theme_p1_text
    fill: app.theme_p1_main
    fill_down: app.theme_p1_dark

<MenuBtnAccent@PremiumBtn>:
    color: app.theme_accent_text
    fill: (app.theme_accent[0] * 0.92, app.theme_accent[1] * 0.92, app.theme_accent[2] * 0.92, 1)
    fill_down: (app.theme_accent[0] * 0.72, app.theme_accent[1] * 0.72, app.theme_accent[2] * 0.72, 1)

<MenuBtnP2@PremiumBtn>:
    color: app.theme_p2_text
    fill: app.theme_p2_main
    fill_down: app.theme_p2_dark

<MenuBtnDark@PremiumBtn>:
    color: app.theme_p1_light
    fill: app.btn_dark_fill
    fill_down: app.btn_dark_fill_down
    outline: app.panel_border
    shadow_mul: 0.6

<PillBtn@AnimBtn>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    bold: True
    font_size: '13sp'
    disabled_color: 1, 1, 1, 0.3
    fill: (1, 1, 1, 0.1)
    fill_down: (1, 1, 1, 0.04)
    canvas.before:
        PushMatrix:
        Scale:
            x: self.anim_scale
            y: self.anim_scale
            z: 1.0
            origin: self.center
        Color:
            rgba: self.fill_down if self.state == 'down' else self.fill
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height / 2]
    canvas.after:
        StencilPush:
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height / 2]
        StencilUse:
        Color:
            rgba: 1, 1, 1, self.ripple_alpha
        Ellipse:
            pos: (self.ripple_x - self.ripple_r, self.ripple_y - self.ripple_r)
            size: (max(self.ripple_r * 2, 1), max(self.ripple_r * 2, 1))
        StencilUnUse:
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height / 2]
        StencilPop:
        PopMatrix:

<HintPillBtn@PillBtn>:
    color: app.theme_accent
    fill: (app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], 0.2)
    fill_down: (app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], 0.1)

# ---------------- CONTROLS ----------------
<M3Switch>:
    canvas:
        PushMatrix:
        Scale:
            x: self.press_scale
            y: self.press_scale
            origin: self.center
        Color:
            rgba: (0.32 + (app.theme_accent[0] - 0.32) * self.progress, 0.34 + (app.theme_accent[1] - 0.34) * self.progress, 0.4 + (app.theme_accent[2] - 0.4) * self.progress, (0.55 + 0.45 * self.progress) if app.ui_material else 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height / 2]
        Color:
            rgba: 1, 1, 1, (1 - self.progress) * 0.35
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, self.height / 2]
            width: dp(1.5)
        Color:
            rgba: (0.8 + (app.theme_accent_text[0] - 0.8) * self.progress, 0.8 + (app.theme_accent_text[1] - 0.8) * self.progress, 0.84 + (app.theme_accent_text[2] - 0.84) * self.progress, 1)
        Ellipse:
            pos: (self.x + (self.height - (dp(16) + dp(8) * self.progress if app.ui_material else dp(24))) / 2 + (self.width - self.height) * self.progress, self.y + (self.height - (dp(16) + dp(8) * self.progress if app.ui_material else dp(24))) / 2)
            size: ((dp(16) + dp(8) * self.progress) if app.ui_material else dp(24), (dp(16) + dp(8) * self.progress) if app.ui_material else dp(24))
        PopMatrix:

<M3Slider>:
    size_hint_y: None
    height: dp(36)
    canvas:
        # inactive track
        Color:
            rgba: 1, 1, 1, 0.16
        RoundedRectangle:
            pos: (self.x + dp(12) + (self.width - dp(24)) * self.ratio + (dp(8) if app.ui_material else 0), self.center_y - (dp(7) if app.ui_material else dp(2)))
            size: (max((self.width - dp(24)) * (1 - self.ratio) - (dp(8) if app.ui_material else 0), 1), dp(14) if app.ui_material else dp(4))
            radius: [dp(7) if app.ui_material else dp(2)]
        # active track
        Color:
            rgba: self.track_color
        RoundedRectangle:
            pos: (self.x + dp(12), self.center_y - (dp(7) if app.ui_material else dp(2)))
            size: (max((self.width - dp(24)) * self.ratio - (dp(8) if app.ui_material else 0), 1), dp(14) if app.ui_material else dp(4))
            radius: [dp(7) if app.ui_material else dp(2)]
        # handle
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: (self.x + dp(12) + (self.width - dp(24)) * self.ratio - (dp(2) if app.ui_material else dp(10)), self.center_y - (dp(18) if app.ui_material else dp(10)))
            size: ((dp(4) if app.ui_material else dp(20)) * (1.25 if self.dragging else 1), (dp(36) if app.ui_material else dp(20)) * (1.1 if self.dragging else 1))
            radius: [dp(2) if app.ui_material else dp(10)]

<SettingRow@BoxLayout>:
    size_hint_y: None
    height: dp(60)
    padding: [dp(20), 0, dp(15), 0]
    show_divider: True
    canvas.before:
        Color:
            rgba: 1, 1, 1, 0.06 if self.show_divider else 0
        Line:
            points: [self.x + dp(20), self.top, self.right - dp(20), self.top]
            width: dp(1)

<SettingLabel@Label>:
    text_size: self.size
    halign: 'left'
    valign: 'middle'
    bold: not app.ui_material
    font_size: '14sp'

<SettingValueBtn@MenuBtnDark>:
    size_hint_x: None
    width: dp(118)
    height: dp(40)
    font_size: '12sp'
    pos_hint: {'center_y': 0.5}
    shadow_mul: 0.3

<VolumeControls@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(140)
    spacing: dp(6)
    padding: [dp(20), dp(15), dp(20), dp(10)]
    Label:
        text: app.L("Music volume", app.ui_material) + ": " + str(int(music_slider.value)) + "%"
        font_size: '11sp'
        bold: True
        size_hint_y: None
        height: dp(20)
        color: app.theme_p1_light
        text_size: self.size
        halign: 'left'
    M3Slider:
        id: music_slider
        min: 0
        max: 100
        value: app.music_volume * 100
        track_color: app.theme_p1_light
        on_value: app.set_music_volume(self.value)
    Label:
        text: app.L("SFX volume", app.ui_material) + ": " + str(int(sfx_slider.value)) + "%"
        font_size: '11sp'
        bold: True
        size_hint_y: None
        height: dp(20)
        color: app.theme_p2_light
        text_size: self.size
        halign: 'left'
    M3Slider:
        id: sfx_slider
        min: 0
        max: 100
        value: app.sfx_volume * 100
        track_color: app.theme_p2_light
        on_value: app.set_sfx_volume(self.value)

<PlayerToggle>:
    size_hint: None, None
    width: dp(260)
    height: dp(48)
    canvas.before:
        Color:
            rgba: (0, 0, 0, 0.5) if not app.ui_material else (1, 1, 1, 0.06)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height / 2]
        Color:
            rgba: 1, 1, 1, 0.18 if app.ui_material else 0
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, self.height / 2]
            width: dp(1)
        Color:
            rgba: 0, 0, 0, 0.4 if not app.ui_material else 0
        RoundedRectangle:
            pos: (self.x + (self.width / 2) * self.thumb_progress + dp(2), self.y - dp(2))
            size: (max(self.width / 2 - dp(4), 1), self.height)
            radius: [self.height / 2]
        Color:
            rgba: (app.theme_p1_main[0], app.theme_p1_main[1], app.theme_p1_main[2], 1) if app.human_player == 1 else (app.theme_p2_main[0], app.theme_p2_main[1], app.theme_p2_main[2], 1)
        RoundedRectangle:
            pos: (self.x + (self.width / 2) * self.thumb_progress + dp(4), self.y + dp(4))
            size: (max(self.width / 2 - dp(8), 1), max(self.height - dp(8), 1))
            radius: [self.height / 2]
    Label:
        text: app.L(app.p1_name.title(), app.ui_material)
        bold: True
        font_size: '13sp'
        pos: root.x, root.y
        size: root.width / 2, root.height
        color: app.theme_p1_text if app.human_player == 1 else (0.6, 0.6, 0.6, 1)
    Label:
        text: app.L(app.p2_name.title(), app.ui_material)
        bold: True
        font_size: '13sp'
        pos: root.center_x, root.y
        size: root.width / 2, root.height
        color: app.theme_p2_text if app.human_player == 2 else (0.6, 0.6, 0.6, 1)

<RadarPing>:
    canvas.before:
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], self.ping_alpha
        Line:
            circle: [self.center_x, self.center_y, dp(30) * self.ping_scale]
            width: dp(2)
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], self.ping2_alpha
        Line:
            circle: [self.center_x, self.center_y, dp(30) * self.ping2_scale]
            width: dp(1.5)
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], 0.25
        Ellipse:
            pos: self.center_x - dp(22) * self.core_scale, self.center_y - dp(22) * self.core_scale
            size: dp(44) * self.core_scale, dp(44) * self.core_scale
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], 1
        Ellipse:
            pos: self.center_x - dp(15) * self.core_scale, self.center_y - dp(15) * self.core_scale
            size: dp(30) * self.core_scale, dp(30) * self.core_scale

<ScreenTitle@Label>:
    font_size: '26sp'
    bold: True
    size_hint_y: None
    height: dp(50)

# ================= SCREENS =================
<StartScreen>:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320)
            height: self.minimum_height
            spacing: dp(22)
            padding: [0, dp(40), 0, dp(15)]
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(90)
                Label:
                    text: "CHECKERS"
                    font_size: '44sp'
                    bold: True
                    color: app.theme_p1_light
                Label:
                    text: app.L("Grandmaster Edition", app.ui_material)
                    font_size: '11sp'
                    bold: True
                    color: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], 0.85
            GlassPanel:
                padding: [dp(20), dp(18), dp(20), dp(18)]
                Label:
                    text: app.L("Match stats (vs AI)", app.ui_material)
                    font_size: '12sp'
                    bold: True
                    color: 0.8, 0.8, 0.8, 1
                    size_hint_y: None
                    height: dp(25)
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(45)
                    BoxLayout:
                        orientation: 'vertical'
                        Label:
                            text: app.L("Easy", app.ui_material)
                            font_size: '10sp'
                            bold: True
                            color: 0.6, 0.6, 0.6, 1
                        Label:
                            text: "[color=" + app.p1_hex + "]" + str(app.stat_wins_easy) + "W[/color] - [color=" + app.p2_hex + "]" + str(app.stat_loss_easy) + "L[/color]"
                            markup: True
                            font_size: '14sp'
                            bold: True
                    BoxLayout:
                        orientation: 'vertical'
                        Label:
                            text: app.L("Medium", app.ui_material)
                            font_size: '10sp'
                            bold: True
                            color: 0.6, 0.6, 0.6, 1
                        Label:
                            text: "[color=" + app.p1_hex + "]" + str(app.stat_wins_medium) + "W[/color] - [color=" + app.p2_hex + "]" + str(app.stat_loss_medium) + "L[/color]"
                            markup: True
                            font_size: '14sp'
                            bold: True
                    BoxLayout:
                        orientation: 'vertical'
                        Label:
                            text: app.L("Hard", app.ui_material)
                            font_size: '10sp'
                            bold: True
                            color: 0.6, 0.6, 0.6, 1
                        Label:
                            text: "[color=" + app.p1_hex + "]" + str(app.stat_wins_hard) + "W[/color] - [color=" + app.p2_hex + "]" + str(app.stat_loss_hard) + "L[/color]"
                            markup: True
                            font_size: '14sp'
                            bold: True
            GlassPanel:
                padding: [dp(20), dp(20), dp(20), dp(24)]
                spacing: dp(15)
                Label:
                    text: app.L("Starting player", app.ui_material)
                    font_size: '12sp'
                    bold: True
                    color: 0.8, 0.8, 0.8, 1
                    size_hint_y: None
                    height: dp(15)
                    halign: 'center'
                PlayerToggle:
                    pos_hint: {'center_x': 0.5}
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(14)
                    size_hint_y: None
                    height: self.minimum_height
                    padding: [0, dp(10), 0, 0]
                    MenuBtnAccent:
                        text: app.L("Online PvP", app.ui_material)
                        on_release: app.start_online_match()
                    MenuBtnP1:
                        text: app.L("Vs AI", app.ui_material)
                        on_release: app.switch_screen('aimenu_screen')
                    MenuBtnP2:
                        text: app.L("Local multiplayer", app.ui_material)
                        on_release: app.start_game('local')
                    BoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(54)
                        spacing: dp(14)
                        MenuBtnDark:
                            text: app.L("Settings", app.ui_material)
                            on_release: app.switch_screen('settings_screen')
                        MenuBtnDark:
                            text: app.L(app.server_status_text.title(), app.ui_material)
                            color: (0.4, 1, 0.4, 1) if app.server_online else ((1, 0.4, 0.4, 1) if app.server_status_text not in ("CHECK SERVER", "PINGING...") else app.theme_p1_light)
                            on_release: app.ping_server()

<MatchmakingScreen>:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320)
            height: self.minimum_height
            spacing: dp(35)
            RadarPing:
                size_hint: None, None
                size: dp(100), dp(100)
                pos_hint: {'center_x': 0.5}
                opacity: 1 if app.matchmaking_status in app.busy_states else 0
            Label:
                text: app.L(app.matchmaking_status.title() if app.ui_material else app.matchmaking_status, app.ui_material)
                font_size: '16sp'
                bold: True
                color: app.theme_accent if app.matchmaking_status in app.busy_states else (1, 0.3, 0.3, 1)
                size_hint_y: None
                height: dp(30)
                halign: 'center'
            Label:
                text: app.L("Rules: " + ("Mandatory jumps" if app.settings_mandatory_jump else "Free captures") + "  •  Blitz " + app.settings_blitz.title(), app.ui_material)
                font_size: '11sp'
                color: 0.6, 0.6, 0.65, 1
                size_hint_y: None
                height: dp(18)
                halign: 'center'
            MenuBtnDark:
                text: app.L("Cancel" if app.matchmaking_status in app.busy_states else "Back to menu", app.ui_material)
                on_release: app.cancel_matchmaking()

<AiMenuScreen>:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320)
            height: self.minimum_height
            spacing: dp(35)
            ScreenTitle:
                text: app.L("Versus A.I.", app.ui_material)
            GlassPanel:
                padding: [dp(20), dp(30), dp(20), dp(30)]
                spacing: dp(20)
                MenuBtnAccent:
                    text: app.L("Boss Rush campaign", app.ui_material)
                    on_release: app.switch_screen('campaign_screen')
                MenuBtnP1:
                    text: app.L("Quick match", app.ui_material)
                    on_release: app.switch_screen('difficulty_screen')
                Widget:
                    size_hint_y: None
                    height: dp(15)
                MenuBtnDark:
                    text: app.L("Back", app.ui_material)
                    on_release: app.switch_screen('start_screen')

<DifficultyScreen>:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320)
            height: self.minimum_height
            spacing: dp(35)
            ScreenTitle:
                text: app.L("Quick match", app.ui_material)
            GlassPanel:
                padding: [dp(20), dp(30), dp(20), dp(30)]
                spacing: dp(20)
                MenuBtnP1:
                    text: app.L("Easy", app.ui_material)
                    on_release: app.start_ai_game('easy', 0)
                MenuBtnAccent:
                    text: app.L("Medium", app.ui_material)
                    on_release: app.start_ai_game('medium', 0)
                MenuBtnP2:
                    text: app.L("Hard", app.ui_material)
                    on_release: app.start_ai_game('hard', 0)
                Widget:
                    size_hint_y: None
                    height: dp(15)
                MenuBtnDark:
                    text: app.L("Back", app.ui_material)
                    on_release: app.switch_screen('aimenu_screen')

<CampaignTier@GlassPanel>:
    padding: dp(20)
    spacing: dp(10)
    width: dp(330)
    tier_title: ""
    tier_desc: ""
    tier_color: [1, 1, 1, 1]
    unlocked: True
    Label:
        text: app.L(root.tier_title, app.ui_material)
        font_size: '14sp'
        bold: True
        color: root.tier_color if root.unlocked else [0.4, 0.4, 0.4, 1]
        size_hint_y: None
        height: dp(20)
        halign: 'left'
        text_size: self.size
    Label:
        text: root.tier_desc if root.unlocked else app.L("Locked", app.ui_material)
        font_size: '11sp'
        color: 0.6, 0.6, 0.6, 1
        size_hint_y: None
        height: dp(20)
        halign: 'left'
        text_size: self.size

<CampaignScreen>:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, 1.0
            width: dp(340)
            spacing: dp(15)
            padding: [0, dp(45), 0, dp(15)]
            ScreenTitle:
                text: app.L("Campaign", app.ui_material)
                height: dp(40)
            ScrollView:
                do_scroll_x: False
                do_scroll_y: True
                effect_cls: 'DampedScrollEffect'
                scroll_type: ['content']
                scroll_distance: dp(10)
                scroll_timeout: 200
                bar_width: 0
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(20)
                    padding: [dp(5), dp(10), dp(5), dp(30)]
                    CampaignTier:
                        tier_title: "Tier I : The Rookie"
                        tier_desc: "Standard rules. Easy AI."
                        tier_color: app.theme_p1_light
                        unlocked: True
                        MenuBtnP1:
                            text: app.L("Fight", app.ui_material)
                            height: dp(45)
                            on_release: app.start_campaign_boss(1)
                    CampaignTier:
                        tier_title: "Tier II : The Tactician"
                        tier_desc: "Standard rules. Medium AI."
                        tier_color: app.theme_accent
                        unlocked: app.campaign_progress >= 2
                        MenuBtnAccent:
                            text: app.L("Fight", app.ui_material)
                            height: dp(45)
                            disabled: app.campaign_progress < 2
                            on_release: app.start_campaign_boss(2)
                    CampaignTier:
                        tier_title: "Tier III : The Awakened"
                        tier_desc: "Hard AI. Starts with 2 kings on board."
                        tier_color: app.theme_p2_light
                        unlocked: app.campaign_progress >= 3
                        MenuBtnP2:
                            text: app.L("Fight", app.ui_material)
                            height: dp(45)
                            disabled: app.campaign_progress < 3
                            on_release: app.start_campaign_boss(3)
                    CampaignTier:
                        tier_title: "Tier IV : The Overlord"
                        tier_desc: "Grandmaster AI. Starts with 4 kings."
                        tier_color: [1, 0.3, 0.3, 1]
                        unlocked: app.campaign_progress >= 4
                        MenuBtnDark:
                            text: app.L("Final fight", app.ui_material)
                            height: dp(45)
                            color: [1, 0.5, 0.5, 1]
                            disabled: app.campaign_progress < 4
                            on_release: app.start_campaign_boss(4)
                    Widget:
                        size_hint_y: None
                        height: dp(10)
                    MenuBtnDark:
                        text: app.L("Back to menu", app.ui_material)
                        on_release: app.switch_screen('aimenu_screen')

<SettingsScreen>:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, 1.0
            width: dp(340)
            spacing: dp(15)
            padding: [0, dp(45), 0, dp(15)]
            ScreenTitle:
                text: app.L("Settings", app.ui_material)
                height: dp(40)
            ScrollView:
                do_scroll_x: False
                do_scroll_y: True
                effect_cls: 'DampedScrollEffect'
                scroll_type: ['content']
                scroll_distance: dp(10)
                scroll_timeout: 200
                bar_width: 0
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(22)
                    padding: [dp(5), dp(10), dp(5), dp(30)]

                    SectionLabel:
                        text: app.L("Appearance", app.ui_material)
                        color: app.theme_accent
                    GlassPanel:
                        padding: 0
                        spacing: 0
                        width: dp(330)
                        SettingRow:
                            show_divider: False
                            SettingLabel:
                                text: app.L("UI style", app.ui_material)
                            SettingValueBtn:
                                text: app.L(app.settings_ui_style.title(), app.ui_material)
                                on_release: app.cycle_ui_style()
                        SettingRow:
                            SettingLabel:
                                text: app.L("Glass effect", app.ui_material)
                            M3Switch:
                                pos_hint: {'center_y': 0.5}
                                active: app.settings_glass
                                on_active: app.toggle_setting('glass', self.active)
                        SettingRow:
                            SettingLabel:
                                text: app.L("Theme", app.ui_material)
                            SettingValueBtn:
                                text: app.L(app.settings_theme.title(), app.ui_material)
                                on_release: app.cycle_theme()
                        SettingRow:
                            SettingLabel:
                                text: app.L("Board style", app.ui_material)
                            SettingValueBtn:
                                text: app.L(app.settings_board.title(), app.ui_material)
                                on_release: app.cycle_board()
                        SettingRow:
                            SettingLabel:
                                text: app.L("Visual quality", app.ui_material)
                            SettingValueBtn:
                                text: app.L(app.settings_visuals.title(), app.ui_material)
                                on_release: app.cycle_visuals()

                    SectionLabel:
                        text: app.L("Gameplay rules", app.ui_material)
                        color: app.theme_p1_light
                    GlassPanel:
                        padding: 0
                        spacing: 0
                        width: dp(330)
                        SettingRow:
                            show_divider: False
                            SettingLabel:
                                text: app.L("Blitz timer", app.ui_material)
                            SettingValueBtn:
                                text: app.L(app.settings_blitz.title(), app.ui_material)
                                on_release: app.cycle_blitz()
                        SettingRow:
                            SettingLabel:
                                text: app.L("Show Undo button", app.ui_material)
                            M3Switch:
                                pos_hint: {'center_y': 0.5}
                                active: app.settings_undo
                                on_active: app.toggle_setting('undo', self.active)
                        SettingRow:
                            SettingLabel:
                                text: app.L("Show Hint button", app.ui_material)
                            M3Switch:
                                pos_hint: {'center_y': 0.5}
                                active: app.settings_hint
                                on_active: app.toggle_setting('hint', self.active)
                        SettingRow:
                            SettingLabel:
                                text: app.L("Mandatory jumps", app.ui_material)
                            M3Switch:
                                pos_hint: {'center_y': 0.5}
                                active: app.settings_mandatory_jump
                                on_active: app.toggle_setting('mandatory_jump', self.active)

                    SectionLabel:
                        text: app.L("Audio & performance", app.ui_material)
                        color: app.theme_p2_light
                    GlassPanel:
                        padding: 0
                        spacing: 0
                        width: dp(330)
                        SettingRow:
                            show_divider: False
                            SettingLabel:
                                text: app.L("FPS target", app.ui_material)
                            SettingValueBtn:
                                text: str(app.settings_fps) + " FPS"
                                on_release: app.cycle_fps()
                        SettingRow:
                            SettingLabel:
                                text: app.L("Show FPS counter", app.ui_material)
                            M3Switch:
                                pos_hint: {'center_y': 0.5}
                                active: app.settings_show_fps
                                on_active: app.toggle_setting('show_fps', self.active)
                        VolumeControls:

                    MenuBtnDark:
                        text: app.L("Back to menu", app.ui_material)
                        on_release: app.switch_screen('start_screen')

<PauseScreen>:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320)
            height: self.minimum_height
            spacing: dp(35)
            ScreenTitle:
                text: app.L("Paused", app.ui_material)
                font_size: '34sp'
            GlassPanel:
                padding: [dp(20), dp(30), dp(20), dp(30)]
                spacing: dp(20)
                MenuBtnP1:
                    text: app.L("Resume game", app.ui_material)
                    on_release: app.resume_game()
                MenuBtnAccent:
                    text: app.L("Restart match", app.ui_material)
                    opacity: 1 if app.game_mode != 'online' else 0
                    disabled: app.game_mode == 'online'
                    on_release: app.start_game(app.game_mode, app.current_boss_level)
                MenuBtnDark:
                    text: app.L("Surrender match", app.ui_material)
                    color: [1, 0.3, 0.3, 1]
                    on_release: app.surrender_match()
                Widget:
                    size_hint_y: None
                    height: dp(15)
                MenuBtnDark:
                    text: app.L("Quit to menu", app.ui_material)
                    on_release: app.quit_to_menu()

<GameOverScreen>:
    ConfettiLayer:
        id: confetti
        pos: 0, 0
        size: root.size
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320)
            height: self.minimum_height
            spacing: dp(35)
            ScreenTitle:
                id: over_title
                text: app.L("Match over", app.ui_material)
                font_size: '34sp'
                color: app.theme_accent
            GlassPanel:
                padding: [dp(20), dp(30), dp(20), dp(30)]
                spacing: dp(20)
                Label:
                    id: winner_label
                    text: "PLAYER WINS!"
                    markup: True
                    font_size: '18sp'
                    bold: True
                    halign: 'center'
                    valign: 'middle'
                    size_hint_y: None
                    height: dp(60)
                Widget:
                    size_hint_y: None
                    height: dp(10)
                MenuBtnP1:
                    id: rematch_btn
                    text: app.L("Play again" if app.game_mode != 'online' else "Request rematch", app.ui_material)
                    opacity: 1 if not app.opponent_left else 0.5
                    disabled: app.opponent_left
                    on_release: app.on_rematch_pressed(self)
                MenuBtnDark:
                    text: app.L("Main menu", app.ui_material)
                    on_release: app.quit_to_menu()

<GameScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(12), dp(45), dp(12), dp(20)]
        spacing: dp(20)
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: dp(55)
            spacing: dp(10)
            CompactPlayerCard:
                player_name: app.p1_display_name
                piece_count: app.p1_pieces
                theme_color: app.theme_p1_light
                is_active: app.current_turn == 1 and not app.is_thinking
            CompactPlayerCard:
                player_name: app.p2_display_name
                piece_count: app.p2_pieces
                theme_color: app.theme_p2_light
                is_active: app.current_turn == 2 or app.is_thinking
        AnchorLayout:
            id: board_anchor
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: dp(10)
            Widget:
                size_hint_y: None
                height: dp(6)
                opacity: 1 if app.settings_blitz != 'OFF' and not app.is_thinking and app.game_mode != 'online' else 0
                canvas.before:
                    Color:
                        rgba: 0, 0, 0, 0.3
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(3)]
                    Color:
                        rgba: (1, 0.2, 0.2, 1) if app.time_ratio < 0.3 else ((1, 0.8, 0.2, 1) if app.time_ratio < 0.6 else app.theme_accent)
                    RoundedRectangle:
                        pos: self.pos
                        size: (max(self.width * app.time_ratio, 1), self.height)
                        radius: [dp(3)]
            BoxLayout:
                orientation: 'horizontal'
                size_hint_y: None
                height: dp(65)
                spacing: dp(10)
                padding: [dp(10), dp(8), dp(10), dp(8)]
                canvas.before:
                    Color:
                        rgba: (app.theme_p1_light[0], app.theme_p1_light[1], app.theme_p1_light[2], 0.15) if app.current_turn == 1 else (app.theme_p2_light[0], app.theme_p2_light[1], app.theme_p2_light[2], 0.15)
                    RoundedRectangle:
                        pos: (self.x - dp(4), self.y - dp(4))
                        size: (max(self.width + dp(8), 1), max(self.height + dp(8), 1))
                        radius: [dp(34)]
                    Color:
                        rgba: 0, 0, 0, app.shadow_alpha
                    SoftShadow:
                        pos: self.pos
                        size: (max(self.width, 1), max(self.height, 1))
                        offset: (0, -dp(5))
                        blur_radius: dp(18)
                        border_radius: [dp(32.5), dp(32.5), dp(32.5), dp(32.5)]
                    Color:
                        rgba: app.panel_fill[0], app.panel_fill[1], app.panel_fill[2], max(app.panel_fill[3], 0.7)
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(32.5)]
                    Color:
                        rgba: 1, 1, 1, app.sheen_alpha
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(32.5)]
                        texture: app.sheen_tex
                    Color:
                        rgba: app.panel_border
                    Line:
                        rounded_rectangle: [self.x, self.y, max(self.width, 1), max(self.height, 1), dp(32.5)]
                        width: dp(1)
                PillBtn:
                    text: app.L("Undo", app.ui_material)
                    size_hint_x: None
                    width: dp(65)
                    opacity: 1 if (app.settings_undo and app.game_mode not in ('campaign', 'online')) else 0
                    disabled: (not app.settings_undo) or app.is_thinking or app.game_mode in ('campaign', 'online')
                    on_release: app.trigger_undo()
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: dp(5)
                    Widget:
                        size_hint_x: None
                        width: dp(10)
                        canvas.before:
                            Color:
                                rgba: ((app.theme_p1_light[0], app.theme_p1_light[1], app.theme_p1_light[2], 1) if app.current_turn == 1 else (app.theme_p2_light[0], app.theme_p2_light[1], app.theme_p2_light[2], 1)) if not app.is_thinking else (0, 0, 0, 0)
                            Ellipse:
                                pos: (self.center_x - dp(4), self.center_y - dp(4))
                                size: (dp(8), dp(8))
                    Label:
                        id: turn_indicator
                        text: app.turn_text
                        color: (0.6, 0.6, 0.6, 1) if app.is_thinking else ((app.theme_p1_light[0], app.theme_p1_light[1], app.theme_p1_light[2], 1) if app.current_turn == 1 else (app.theme_p2_light[0], app.theme_p2_light[1], app.theme_p2_light[2], 1))
                        font_size: '13sp'
                        bold: True
                        text_size: self.size
                        halign: 'left'
                        valign: 'middle'
                        shorten: True
                        shorten_from: 'right'
                HintPillBtn:
                    text: app.L("Hint", app.ui_material)
                    size_hint_x: None
                    width: dp(60)
                    opacity: 1 if (app.settings_hint and app.game_mode not in ('campaign', 'online')) else 0
                    disabled: app.is_thinking or (not app.settings_hint) or app.game_mode in ('campaign', 'online')
                    on_release: app.trigger_hint()
                PillBtn:
                    text: app.L("Menu", app.ui_material)
                    size_hint_x: None
                    width: dp(65)
                    on_release: app.switch_screen('pause_screen')
'''


class StartScreen(BaseScreen):
    pass


class MatchmakingScreen(BaseScreen):
    pass


class AiMenuScreen(BaseScreen):
    pass


class CampaignScreen(BaseScreen):
    pass


class DifficultyScreen(BaseScreen):
    pass


class SettingsScreen(BaseScreen):
    pass


class PauseScreen(BaseScreen):
    pass


class GameOverScreen(BaseScreen):
    pass


class GameScreen(BaseScreen):
    pass


# ==============================================================================
# 5. BOARD & PIECES
# ==============================================================================
class PieceWidget(Widget):
    piece_type = NumericProperty(1)
    row = NumericProperty(0)
    col = NumericProperty(0)
    highlight_scale = NumericProperty(1.0)
    highlight_alpha = NumericProperty(0.0)
    piece_scale = NumericProperty(1.0)
    king_pulse = NumericProperty(1.15)
    is_selected = BooleanProperty(False)

    def on_piece_type(self, instance, value):
        Animation.cancel_all(self, 'king_pulse')
        if value < 0:
            anim = Animation(king_pulse=1.3, duration=0.8, transition='in_out_sine') + Animation(king_pulse=1.1, duration=0.8, transition='in_out_sine')
            anim.repeat = True
            anim.start(self)
        else:
            self.king_pulse = 1.5  # aura invisible

    def on_is_selected(self, instance, value):
        app = App.get_running_app()
        Animation.cancel_all(self, 'highlight_scale', 'highlight_alpha')
        if value:
            if app and app.fx_high:
                self.highlight_scale = 1.0
                self.highlight_alpha = 0.8
                pulse = Animation(highlight_scale=1.15, highlight_alpha=0.25, duration=0.5, transition='in_out_sine')
                pulse += Animation(highlight_scale=1.0, highlight_alpha=0.8, duration=0.5, transition='in_out_sine')
                pulse.repeat = True
                pulse.start(self)
                Animation.cancel_all(self, 'piece_scale')
                self.piece_scale = 1.0
                Animation(piece_scale=1.08, duration=0.18, transition='out_back').start(self)
            else:
                self.highlight_scale = 1.15
                self.highlight_alpha = 0.8
        else:
            self.highlight_scale = 1.0
            self.highlight_alpha = 0.0
            if app and app.fx_high and abs(self.piece_scale - 1.0) > 0.001:
                Animation.cancel_all(self, 'piece_scale')
                Animation(piece_scale=1.0, duration=0.15, transition='out_quad').start(self)


class BoardWidget(Widget):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.selected_piece_coords = None
        self.piece_widgets = []
        self.hint_targets = []
        self.move_dots = []
        self.effects = []
        self.offset_x = 0
        self.offset_y = 0
        self.sq_size = 0
        self.size_hint = (None, None)
        self.is_animating = False
        self.last_move = None
        self._anim_guard = None

        self.bind(pos=self.trigger_redraw, size=self.trigger_redraw)
        self.app.bind(settings_board=self.trigger_redraw)

    # -- layout --------------------------------------------------------------
    def trigger_redraw(self, *args):
        Clock.unschedule(self.calculate_board_size)
        Clock.schedule_once(self.calculate_board_size, 0)

    def calculate_board_size(self, *args):
        if not self.parent:
            return
        board_dim = min(self.parent.width, self.parent.height) * 0.98
        if board_dim <= 0:
            return
        self.size = (board_dim, board_dim)
        self.offset_x = self.parent.x + (self.parent.width - board_dim) / 2.0
        self.offset_y = self.parent.y + (self.parent.height - board_dim) / 2.0
        self.sq_size = board_dim / COLS

        self.render_board_background()
        self.render_pieces()

    def square_pos(self, r, c):
        return (self.offset_x + c * self.sq_size, self.offset_y + (7 - r) * self.sq_size)

    def piece_pos(self, r, c):
        margin = self.sq_size * 0.1
        x, y = self.square_pos(r, c)
        return (x + margin, y + margin)

    def render_board_background(self):
        self.canvas.before.clear()
        style_name = self.app.settings_board
        style_colors = BOARD_STYLES.get(style_name, BOARD_STYLES['CLASSIC'])
        img_path = 'board_%s.jpg' % style_name.lower()
        has_image = os.path.isfile(img_path)
        w = max(self.size[0], 1)
        h = max(self.size[1], 1)
        r_outer = dp(16) if self.app.ui_material else dp(10)

        with self.canvas.before:
            Color(0, 0, 0, max(self.app.shadow_alpha, 0.2))
            SoftShadow(pos=(self.offset_x - dp(6), self.offset_y - dp(6)), size=(w + dp(12), h + dp(12)),
                       offset=(0, -dp(10)), blur_radius=dp(30), border_radius=[r_outer] * 4)
            Color(*style_colors['border'])
            RoundedRectangle(pos=(self.offset_x - dp(6), self.offset_y - dp(6)), size=(w + dp(12), h + dp(12)), radius=[r_outer])
            Color(1, 1, 1, 0.12)
            Line(rounded_rectangle=[self.offset_x - dp(6), self.offset_y - dp(6), w + dp(12), h + dp(12), r_outer], width=dp(1))

            if has_image:
                Color(1, 1, 1, 1)
                Rectangle(pos=(self.offset_x, self.offset_y), size=(w, h), source=img_path)
            else:
                sq = max(self.sq_size, 1)
                for r in range(ROWS):
                    for c in range(COLS):
                        if (r + c) % 2 != 0:
                            Color(*style_colors['dark'])
                        else:
                            Color(*style_colors['light'])
                        Rectangle(pos=self.square_pos(r, c), size=(sq, sq))

            # Last-move highlight (from + to squares)
            if self.last_move:
                acc = self.app.theme_accent
                for (r, c) in self.last_move:
                    Color(acc[0], acc[1], acc[2], 0.28)
                    Rectangle(pos=self.square_pos(r, c), size=(max(self.sq_size, 1), max(self.sq_size, 1)))
                (sr, sc), (er, ec) = self.last_move
                Color(acc[0], acc[1], acc[2], 0.7)
                Line(rounded_rectangle=[self.square_pos(er, ec)[0] + dp(2), self.square_pos(er, ec)[1] + dp(2),
                                        max(self.sq_size - dp(4), 1), max(self.sq_size - dp(4), 1), dp(6)], width=dp(1.5))

    # -- overlays ------------------------------------------------------------
    def clear_all_hints(self):
        for pw in self.piece_widgets:
            if not pw.is_selected:
                Animation.cancel_all(pw, 'highlight_scale', 'highlight_alpha')
                pw.highlight_scale = 1.0
                pw.highlight_alpha = 0.0
        for t in self.hint_targets:
            Animation.cancel_all(t)
            self.remove_widget(t)
        self.hint_targets.clear()
        self.clear_move_dots()

    def clear_move_dots(self):
        for d in self.move_dots:
            Animation.cancel_all(d)
            self.remove_widget(d)
        self.move_dots.clear()

    def show_move_dots(self, start_coords):
        self.clear_move_dots()
        must_jump = self.app.must_jump_rule()
        allowed = GameEngine.get_valid_moves(self.app.current_turn, self.app.board_state, must_jump)
        mine = [m for m in allowed if m['start'] == start_coords]
        for i, m in enumerate(mine):
            er, ec = m['end']
            dot = MoveDot(is_jump=(m['info']['type'] == 'jump'))
            dot.size = (self.sq_size, self.sq_size)
            dot.pos = self.square_pos(er, ec)
            self.add_widget(dot, index=len(self.children))  # behind pieces
            self.move_dots.append(dot)
            dot.show(animated=self.app.fx_high, delay=0.03 * i)

    def spawn_effect(self, widget):
        self.add_widget(widget)
        return widget

    # -- pieces --------------------------------------------------------------
    def render_pieces(self):
        piece_data = []
        p1_count = 0
        p2_count = 0

        if self.app.board_state:
            for r in range(ROWS):
                for c in range(COLS):
                    val = self.app.board_state[r][c]
                    if val != EMPTY:
                        piece_data.append((val, r, c))
                        if abs(val) == 1:
                            p1_count += 1
                        else:
                            p2_count += 1

        self.app.p1_pieces = p1_count
        self.app.p2_pieces = p2_count

        while len(self.piece_widgets) < len(piece_data):
            pw = PieceWidget()
            self.piece_widgets.append(pw)
            self.add_widget(pw)

        for i in range(len(piece_data), len(self.piece_widgets)):
            pw = self.piece_widgets[i]
            Animation.cancel_all(pw, 'pos', 'opacity', 'piece_scale')
            pw.opacity = 0
            pw.pos = (-1000, -1000)
            pw.is_selected = False

        for i, data in enumerate(piece_data):
            ptype, r, c = data
            pw = self.piece_widgets[i]
            Animation.cancel_all(pw, 'pos', 'opacity', 'piece_scale')
            pw.piece_type = ptype
            pw.row = r
            pw.col = c
            pw.opacity = 1
            pw.piece_scale = 1.0
            pw.size = (self.sq_size * 0.8, self.sq_size * 0.8)
            pw.pos = self.piece_pos(r, c)

            Animation.cancel_all(pw, 'highlight_scale', 'highlight_alpha')
            pw.highlight_scale = 1.0
            pw.highlight_alpha = 0.0
            want_selected = (self.selected_piece_coords == (r, c))
            if pw.is_selected and want_selected:
                pw.is_selected = False  # force the highlight animation to restart
            pw.is_selected = want_selected

        if self.selected_piece_coords:
            self.show_move_dots(self.selected_piece_coords)
        else:
            self.clear_move_dots()

        if getattr(self.app, 'newly_promoted', None):
            nr, nc = self.app.newly_promoted
            promoted_piece = self.find_piece(nr, nc)
            if promoted_piece:
                promoted_piece.piece_scale = 1.6
                Animation(piece_scale=1.0, duration=0.45, transition='out_bounce').start(promoted_piece)
                if self.app.fx_high:
                    ring = BurstRing(color=[1, 0.84, 0.2, 1], line_width=dp(3))
                    ring.size = (self.sq_size, self.sq_size)
                    ring.center = promoted_piece.center
                    self.spawn_effect(ring).play(duration=0.6, max_scale=2.2)
                    ring2 = BurstRing(color=self.app.theme_accent, line_width=dp(2))
                    ring2.size = (self.sq_size, self.sq_size)
                    ring2.center = promoted_piece.center
                    Clock.schedule_once(lambda dt: self.spawn_effect(ring2).play(duration=0.6, max_scale=2.6), 0.12)
            self.app.newly_promoted = None

    def find_piece(self, r, c):
        return next((p for p in self.piece_widgets if p.opacity == 1 and p.row == r and p.col == c), None)

    def play_intro(self):
        """Pieces drop in with a stagger when a match starts (HIGH visuals only)."""
        if not self.app.fx_high:
            return
        visible = [p for p in self.piece_widgets if p.opacity == 1]
        order = sorted(visible, key=lambda p: (p.row, p.col))
        for i, pw in enumerate(order):
            Animation.cancel_all(pw, 'piece_scale')
            pw.piece_scale = 0.0
            anim = Animation(duration=0.02 * i) + Animation(piece_scale=1.0, duration=0.32, transition='out_back')
            anim.start(pw)

    def pulse_hint_piece(self, move_obj):
        self.clear_all_hints()
        sr, sc = move_obj['start']
        er, ec = move_obj['end']

        piece = self.find_piece(sr, sc)
        if piece and not piece.is_selected:
            Animation.cancel_all(piece, 'highlight_scale', 'highlight_alpha')
            piece.highlight_scale = 1.0
            piece.highlight_alpha = 0.0
            if self.app.fx_high:
                anim = Animation(highlight_scale=1.15, highlight_alpha=0.6, duration=0.6, transition='in_out_sine')
                anim += Animation(highlight_scale=1.05, highlight_alpha=0.1, duration=0.6, transition='in_out_sine')
                anim.repeat = True
                anim.start(piece)
            else:
                piece.highlight_scale = 1.15
                piece.highlight_alpha = 0.8

        target_pad = HintTargetWidget()
        target_pad.size = (self.sq_size, self.sq_size)
        target_pad.pos = self.square_pos(er, ec)
        self.add_widget(target_pad)
        self.hint_targets.append(target_pad)
        if self.app.fx_high:
            target_pad.start_anim()
        else:
            target_pad.anim_alpha = 0.5

    # -- input ---------------------------------------------------------------
    def on_touch_down(self, touch):
        if self.is_animating:
            return True
        if not self.app.board_state or self.sq_size <= 0:
            return super().on_touch_down(touch)

        board_dim = self.sq_size * 8
        if not (self.offset_x <= touch.x <= self.offset_x + board_dim and
                self.offset_y <= touch.y <= self.offset_y + board_dim):
            return super().on_touch_down(touch)

        if self.app.is_thinking or (self.app.game_mode in ('computer', 'campaign') and self.app.current_turn != self.app.human_player):
            return True
        if self.app.game_mode == 'online' and self.app.current_turn != self.app.online_player_id:
            return True

        self.clear_all_hints()

        col = int((touch.x - self.offset_x) // self.sq_size)
        row = 7 - int((touch.y - self.offset_y) // self.sq_size)
        if row < 0 or row > 7 or col < 0 or col > 7:
            return False

        piece_type = self.app.board_state[row][col]
        must_jump = self.app.must_jump_rule()

        if piece_type != EMPTY and abs(piece_type) == self.app.current_turn:
            allowed_moves = GameEngine.get_valid_moves(self.app.current_turn, self.app.board_state, must_jump)
            if allowed_moves:
                can_move_this = any(m['start'] == (row, col) for m in allowed_moves)
                if can_move_this:
                    if self.selected_piece_coords == (row, col):
                        self.app.play_click_sound()
                        self.selected_piece_coords = None
                        self.clear_all_hints()
                        self.render_pieces()
                        return True
                    self.app.play_click_sound()
                    self.app.trigger_haptic(0.02)
                    self.selected_piece_coords = (row, col)
                    self.render_pieces()
                else:
                    self.shake_piece(row, col)
            return True

        if self.selected_piece_coords:
            sr, sc = self.selected_piece_coords
            allowed_moves = GameEngine.get_valid_moves(self.app.current_turn, self.app.board_state, must_jump)
            chosen_move = next((m for m in allowed_moves if m['start'] == (sr, sc) and m['end'] == (row, col)), None)

            if chosen_move:
                self.app.play_click_sound()
                self.app.trigger_haptic(0.04)
                self.selected_piece_coords = None
                if self.app.game_mode == 'online':
                    self.app.network.send_move((sr, sc), (row, col))
                self.execute_move(chosen_move)
            else:
                self.selected_piece_coords = None
                self.render_pieces()
        return True

    def shake_piece(self, r, c):
        """Feedback for tapping a piece that cannot move (e.g. a jump is mandatory)."""
        piece = self.find_piece(r, c)
        if not piece or not self.app.fx_high:
            return
        x, y = piece.pos
        d = dp(4)
        anim = (Animation(x=x - d, duration=0.04) + Animation(x=x + d, duration=0.06) +
                Animation(x=x - d * 0.6, duration=0.05) + Animation(x=x, duration=0.05))
        anim.start(piece)
        self.app.trigger_haptic(0.03)

    # -- move execution ------------------------------------------------------
    def _arm_guard(self, seconds=2.0):
        """Safety net: if an animation callback is ever lost the board
        unlocks itself instead of staying frozen forever."""
        if self._anim_guard:
            self._anim_guard.cancel()
        self._anim_guard = Clock.schedule_once(self._guard_fired, seconds)

    def _guard_fired(self, dt):
        self._anim_guard = None
        if self.is_animating:
            Logger.warning("Board: animation guard released a stuck board")
            self.is_animating = False
            self.render_pieces()

    def _disarm_guard(self):
        if self._anim_guard:
            self._anim_guard.cancel()
            self._anim_guard = None

    def execute_move(self, move_obj):
        self.is_animating = True
        self._arm_guard()
        self.app.stop_timer()
        self.clear_move_dots()

        if self.app.game_mode == 'local' or self.app.current_turn == self.app.human_player:
            self.app.undo_stack.append({
                'board': [row[:] for row in self.app.board_state],
                'turn': self.app.current_turn,
                'last_move': self.last_move,
            })

        sr, sc = move_obj['start']
        er, ec = move_obj['end']
        piece = self.find_piece(sr, sc)

        if not piece:
            # Should never happen, but never leave the board locked.
            self.handle_capture(move_obj)
            return

        piece.is_selected = False
        self.remove_widget(piece)
        self.add_widget(piece)

        target = self.piece_pos(er, ec)
        is_jump = move_obj['info']['type'] == 'jump'

        if self.app.fx_high:
            dur = 0.34 if is_jump else 0.26
            lift = 1.24 if is_jump else 1.12
            move = Animation(pos=target, duration=dur, transition='in_out_cubic' if is_jump else 'out_cubic')
            hop = (Animation(piece_scale=lift, duration=dur * 0.45, transition='out_quad') +
                   Animation(piece_scale=1.0, duration=dur * 0.55, transition='in_quad'))
            anim = move & hop
        else:
            anim = Animation(pos=target, duration=0.16, transition='out_cubic')

        anim.bind(on_complete=lambda *args: self.handle_capture(move_obj))
        anim.start(piece)

    def handle_capture(self, move_obj):
        if move_obj['info']['type'] == 'jump':
            jr = move_obj['info']['jumped_r']
            jc = move_obj['info']['jumped_c']
            captured_piece = self.find_piece(jr, jc)

            if captured_piece:
                self.app.trigger_haptic(0.08)
                captured_piece.is_selected = False
                if self.app.fx_high:
                    theme = self.app.theme_p1_light if abs(captured_piece.piece_type) == 1 else self.app.theme_p2_light
                    burst = CaptureBurst(color=list(theme))
                    burst.size = (self.sq_size * 0.8, self.sq_size * 0.8)
                    burst.center = captured_piece.center
                    self.spawn_effect(burst).play()
                    ring = BurstRing(color=list(theme), line_width=dp(2))
                    ring.size = (self.sq_size, self.sq_size)
                    ring.center = captured_piece.center
                    self.spawn_effect(ring).play(duration=0.4, max_scale=1.6)
                    cap_anim = (Animation(piece_scale=1.22, duration=0.07, transition='out_quad') +
                                Animation(piece_scale=0.0, opacity=0, duration=0.2, transition='in_quad'))
                else:
                    cap_anim = Animation(opacity=0, duration=0.1)
                Animation.cancel_all(captured_piece, 'piece_scale', 'opacity', 'pos')
                cap_anim.bind(on_complete=lambda *args: self.finalize_move(move_obj))
                cap_anim.start(captured_piece)
                return
        self.finalize_move(move_obj)

    def finalize_move(self, move_obj):
        self._disarm_guard()
        er, ec = move_obj['end']
        sr, sc = move_obj['start']
        piece_type = self.app.board_state[sr][sc]

        if piece_type > 0:
            if (self.app.current_turn == BLUE and er == ROWS - 1) or (self.app.current_turn == RED and er == 0):
                self.app.newly_promoted = (er, ec)
                self.app.trigger_haptic(0.1)

        GameEngine.apply_temp_move(self.app.board_state, move_obj, self.app.current_turn)
        self.last_move = ((sr, sc), (er, ec))
        self.app.current_turn = RED if self.app.current_turn == BLUE else BLUE
        self.render_board_background()
        self.render_pieces()
        self.is_animating = False

        if self.app.screen_manager.current not in ('game_screen', 'pause_screen'):
            return

        if not GameEngine.get_valid_moves(self.app.current_turn, self.app.board_state, self.app.must_jump_rule()):
            self.app.trigger_game_over()
            return

        self.app.start_timer()

        if self.app.game_mode in ('computer', 'campaign') and self.app.current_turn != self.app.human_player:
            self.app.trigger_ai_turn()
        elif self.app.game_mode == 'online':
            self.app.flush_pending_network_moves()


# ==============================================================================
# 6. APPLICATION
# ==============================================================================
class CheckersApp(App):
    human_player = NumericProperty(BLUE)
    current_turn = NumericProperty(BLUE)
    is_thinking = BooleanProperty(False)

    game_mode = StringProperty('local')
    ai_mode = StringProperty('easy')
    online_player_id = NumericProperty(BLUE)
    opponent_left = BooleanProperty(False)

    music_volume = NumericProperty(1.0)
    sfx_volume = NumericProperty(1.0)

    stat_wins_easy = NumericProperty(0)
    stat_loss_easy = NumericProperty(0)
    stat_wins_medium = NumericProperty(0)
    stat_loss_medium = NumericProperty(0)
    stat_wins_hard = NumericProperty(0)
    stat_loss_hard = NumericProperty(0)

    p1_pieces = NumericProperty(12)
    p2_pieces = NumericProperty(12)

    # --- settings ---
    settings_undo = BooleanProperty(True)
    settings_hint = BooleanProperty(True)
    settings_mandatory_jump = BooleanProperty(True)
    settings_fps = NumericProperty(60)
    settings_visuals = StringProperty('HIGH')
    settings_blitz = StringProperty('OFF')
    settings_theme = StringProperty('ROYAL')
    settings_board = StringProperty('CLASSIC')
    settings_ui_style = StringProperty('MATERIAL 3')
    settings_glass = BooleanProperty(True)
    settings_show_fps = BooleanProperty(False)

    # --- derived UI tokens (consumed by KV) ---
    ui_material = BooleanProperty(True)
    fx_high = BooleanProperty(True)
    r_panel = NumericProperty(dp(28))
    r_card = NumericProperty(dp(16))
    panel_fill = ListProperty([0.08, 0.1, 0.12, 0.85])
    panel_border = ListProperty([1, 1, 1, 0.08])
    sheen_alpha = NumericProperty(0.0)
    glass_edge_alpha = NumericProperty(0.0)
    shadow_alpha = NumericProperty(0.45)
    btn_shadow_dy = NumericProperty(-dp(2))
    btn_shadow_blur = NumericProperty(dp(8))
    btn_dark_fill = ListProperty([0.15, 0.15, 0.15, 0.95])
    btn_dark_fill_down = ListProperty([0.05, 0.05, 0.05, 1])
    disabled_fill = ListProperty([1, 1, 1, 0.08])
    sheen_tex = ObjectProperty(None, allownone=True)
    busy_states = ListProperty(list(MATCHMAKING_BUSY))
    turn_text = StringProperty("")
    time_ratio = NumericProperty(1.0)

    p1_name = StringProperty('NAVY')
    p2_name = StringProperty('CRIMSON')
    p1_display_name = StringProperty("PLAYER 1")
    p2_display_name = StringProperty("PLAYER 2")
    p1_hex = StringProperty('#6699D8')
    p2_hex = StringProperty('#F2737F')

    campaign_progress = NumericProperty(1)
    current_boss_level = NumericProperty(0)
    boss_name = StringProperty("")

    server_status_text = StringProperty("CHECK SERVER")
    server_online = BooleanProperty(False)
    matchmaking_status = StringProperty("SEARCHING FOR MATCH...")

    theme_p1_light = ListProperty([0.4, 0.6, 0.85, 1])
    theme_p1_main = ListProperty([0.15, 0.35, 0.55, 1])
    theme_p1_dark = ListProperty([0.08, 0.2, 0.35, 1])
    theme_p1_star = ListProperty([1, 1, 1, 1])
    theme_p1_text = ListProperty([1, 1, 1, 1])

    theme_p2_light = ListProperty([0.95, 0.45, 0.5, 1])
    theme_p2_main = ListProperty([0.75, 0.15, 0.25, 1])
    theme_p2_dark = ListProperty([0.45, 0.05, 0.15, 1])
    theme_p2_star = ListProperty([1, 1, 1, 1])
    theme_p2_text = ListProperty([1, 1, 1, 1])

    theme_accent = ListProperty([0.95, 0.75, 0.25, 1])
    theme_accent_text = ListProperty([0.1, 0.1, 0.1, 1])
    theme_panel = ListProperty([0.08, 0.1, 0.12, 0.85])

    theme_bg_top = ListProperty([0.1, 0.2, 0.35, 1])
    theme_bg_bot = ListProperty([0.02, 0.05, 0.1, 1])

    current_time_left = NumericProperty(100.0)
    max_time = NumericProperty(100.0)

    # ------------------------------------------------------------------ build
    def build(self):
        Window.bind(on_keyboard=self.on_keyboard)

        self.click_pool = []
        self.sound_win = None
        self.sound_lose = None
        self.music_bg = None
        self.click_index = 0
        self.newly_promoted = None
        self.match_id = 0
        self.blitz_event = None
        self.network = NetworkManager(self)
        self._pending_net_moves = []
        self._switch_seq = 0
        self._game_over_pending = False
        self._last_back_press = 0.0
        self._toast_event = None
        self._celebrate = False
        self._net_error = False

        self.store = JsonStore(SAVE_FILE)
        self.undo_stack = []

        self._build_sheen_texture()
        self.load_settings()
        self.apply_theme()
        self.refresh_ui_tokens()
        self.apply_fps_limit()
        self.load_stats()

        self.bind(settings_visuals=lambda *a: self.refresh_ui_tokens(),
                  settings_glass=lambda *a: self.refresh_ui_tokens(),
                  settings_ui_style=lambda *a: self.refresh_ui_tokens(),
                  current_turn=lambda *a: self.refresh_turn_text(),
                  is_thinking=lambda *a: self.refresh_turn_text(),
                  game_mode=lambda *a: self.refresh_turn_text(),
                  online_player_id=lambda *a: self.refresh_turn_text(),
                  p1_name=lambda *a: self.refresh_turn_text(),
                  p2_name=lambda *a: self.refresh_turn_text(),
                  ui_material=lambda *a: self.refresh_turn_text(),
                  current_time_left=lambda *a: self._update_time_ratio(),
                  max_time=lambda *a: self._update_time_ratio())

        Builder.load_string(KV)

        self.board_state = GameEngine.get_initial_board()

        root = FloatLayout()
        self.background = Factory.BackgroundLayer()
        root.add_widget(self.background)

        self.screen_manager = ScreenManager(transition=NoTransition())
        self.screen_manager.add_widget(StartScreen(name='start_screen'))
        self.screen_manager.add_widget(MatchmakingScreen(name='matchmaking_screen'))
        self.screen_manager.add_widget(AiMenuScreen(name='aimenu_screen'))
        self.screen_manager.add_widget(CampaignScreen(name='campaign_screen'))
        self.screen_manager.add_widget(DifficultyScreen(name='difficulty_screen'))
        self.screen_manager.add_widget(SettingsScreen(name='settings_screen'))
        self.screen_manager.add_widget(PauseScreen(name='pause_screen'))
        self.screen_manager.add_widget(GameOverScreen(name='game_over_screen'))

        game_screen = GameScreen(name='game_screen')
        self.board_widget = BoardWidget(app_ref=self)
        anchor = game_screen.ids.board_anchor
        anchor.add_widget(self.board_widget)
        anchor.bind(size=self.board_widget.trigger_redraw, pos=self.board_widget.trigger_redraw)
        self.screen_manager.add_widget(game_screen)
        root.add_widget(self.screen_manager)

        self.fps_overlay = FpsOverlay()
        root.add_widget(self.fps_overlay)
        self.fps_overlay.set_enabled(self.settings_show_fps)

        self.toast = Factory.ToastLabel()
        root.add_widget(self.toast)

        self.refresh_turn_text()
        self.audio_queue = ['click1', 'click2', 'click3', 'click4', 'click5', 'win', 'lose', 'music']
        Clock.schedule_interval(self._load_next_audio, 0.1)
        Clock.schedule_once(lambda dt: self.screen_manager.current_screen.play_enter(), 0.05)

        return root

    def on_start(self):
        self.apply_fps_limit()

    def on_pause(self):
        return True

    def on_resume(self):
        self.apply_fps_limit()

    # ------------------------------------------------------------- utilities
    def L(self, text, material):
        """Material 3 uses sentence case, the classic look uses ALL CAPS."""
        return text if material else text.upper()

    def btn_r(self, height, material):
        return (height / 2.0) if material else dp(14)

    def must_jump_rule(self):
        return False if self.game_mode == 'campaign' else self.settings_mandatory_jump

    def _build_sheen_texture(self):
        """2x2 bilinear texture = smooth diagonal highlight used for the glass sheen."""
        try:
            tex = Texture.create(size=(2, 2), colorfmt='rgba')
            # rows are bottom-up:  (bottom-left, bottom-right, top-left, top-right)
            buf = bytes([255, 255, 255, 10,
                         255, 255, 255, 0,
                         255, 255, 255, 60,
                         255, 255, 255, 26])
            tex.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
            tex.mag_filter = 'linear'
            tex.min_filter = 'linear'
            self.sheen_tex = tex
        except Exception as exc:
            Logger.warning("UI: sheen texture failed: %s", exc)
            self.sheen_tex = None

    def refresh_ui_tokens(self, *args):
        material = (self.settings_ui_style == 'MATERIAL 3')
        glass = bool(self.settings_glass)
        high = (self.settings_visuals == 'HIGH')
        self.ui_material = material
        self.fx_high = high

        self.r_panel = dp(28) if material else dp(20)
        self.r_card = dp(16) if material else dp(12)
        base = self.theme_panel

        if glass:
            lift = 0.07
            self.panel_fill = [min(1, base[0] + lift), min(1, base[1] + lift), min(1, base[2] + lift), 0.52]
            self.panel_border = [1, 1, 1, 0.20]
            self.sheen_alpha = 1.0 if self.sheen_tex is not None else 0.0
            self.glass_edge_alpha = 0.32
            self.btn_dark_fill = [1, 1, 1, 0.10]
            self.btn_dark_fill_down = [1, 1, 1, 0.04]
        else:
            self.panel_fill = [base[0], base[1], base[2], 0.97]
            self.panel_border = [1, 1, 1, 0.06 if material else 0.08]
            self.sheen_alpha = 0.0
            self.glass_edge_alpha = 0.0
            hi = 0.08
            self.btn_dark_fill = [min(1, base[0] + hi), min(1, base[1] + hi), min(1, base[2] + hi), 1]
            self.btn_dark_fill_down = [max(0, base[0] - 0.02), max(0, base[1] - 0.02), max(0, base[2] - 0.02), 1]

        self.shadow_alpha = (0.5 if glass else 0.42) if high else 0.0
        if material:
            self.btn_shadow_dy = -dp(2)
            self.btn_shadow_blur = dp(10)
        else:
            self.btn_shadow_dy = -dp(3)
            self.btn_shadow_blur = dp(1.5) if HAS_REAL_SHADOWS else 0
        self.disabled_fill = [1, 1, 1, 0.08]

        if hasattr(self, 'background'):
            try:
                self.background.ids.flair.set_animating(high)
            except Exception:
                pass
        if hasattr(self, 'board_widget'):
            self.board_widget.trigger_redraw()

    def refresh_turn_text(self, *args):
        if self.game_mode == 'online' and self.current_turn != self.online_player_id:
            txt = "Waiting for opponent..."
        elif self.is_thinking:
            txt = "AI thinking..."
        else:
            name = self.p1_name if self.current_turn == 1 else self.p2_name
            txt = "%s's turn" % (name.title() if self.ui_material else name)
        self.turn_text = txt if self.ui_material else txt.upper()

    def _update_time_ratio(self, *args):
        self.time_ratio = max(0.0, min(1.0, self.current_time_left / (self.max_time if self.max_time > 0 else 0.001)))

    def show_toast(self, text, duration=1.8):
        if not hasattr(self, 'toast'):
            return
        self.toast.text = text if self.ui_material else text.upper()
        Animation.cancel_all(self.toast, 'opacity')
        if self._toast_event:
            self._toast_event.cancel()
        Animation(opacity=1, duration=0.18).start(self.toast)
        self._toast_event = Clock.schedule_once(lambda dt: Animation(opacity=0, duration=0.3).start(self.toast), duration)

    def trigger_haptic(self, duration=0.03):
        if vibrator:
            try:
                vibrator.vibrate(time=duration)
            except Exception:
                pass

    # --------------------------------------------------------------- keyboard
    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        if key != 27:
            return False
        cur = self.screen_manager.current
        if cur == 'game_screen':
            self.switch_screen('pause_screen')
        elif cur == 'pause_screen':
            self.resume_game()
        elif cur == 'game_over_screen':
            self.quit_to_menu()
        elif cur == 'matchmaking_screen':
            self.cancel_matchmaking()
        elif cur in ('difficulty_screen', 'campaign_screen'):
            self.switch_screen('aimenu_screen')
        elif cur in ('settings_screen', 'aimenu_screen'):
            self.switch_screen('start_screen')
        elif cur == 'start_screen':
            now = time.time()
            if now - self._last_back_press < 2.0:
                self.stop()
            else:
                self._last_back_press = now
                self.show_toast("Press back again to exit")
        return True

    # ----------------------------------------------------------------- server
    def ping_server(self):
        if self.server_status_text == "PINGING...":
            return
        self.server_status_text = "PINGING..."
        if not websocket:
            self._set_server_status(False, "NO LIB")
            return

        def check_conn():
            try:
                ws = websocket.create_connection(WEBSOCKET_URL, timeout=4)
                ws.close()
                Clock.schedule_once(lambda dt: self._set_server_status(True, "ONLINE"))
            except Exception:
                Clock.schedule_once(lambda dt: self._set_server_status(False, "OFFLINE"))

        threading.Thread(target=check_conn, daemon=True).start()

    def _set_server_status(self, is_online, text):
        self.server_online = is_online
        self.server_status_text = text

    # --------------------------------------------------------------- settings
    def load_settings(self):
        if self.store.exists('campaign'):
            try:
                self.campaign_progress = int(self.store.get('campaign').get('progress', 1))
            except (TypeError, ValueError):
                self.campaign_progress = 1
        if self.store.exists('settings'):
            s = self.store.get('settings')
            self.settings_undo = bool(s.get('undo', True))
            self.settings_hint = bool(s.get('hint', True))
            self.settings_mandatory_jump = bool(s.get('mandatory_jump', True))
            self.settings_fps = _sanitize_fps(s.get('fps', 60))
            self.settings_visuals = s.get('visuals', 'HIGH') if s.get('visuals') in VISUAL_OPTIONS else 'HIGH'
            self.settings_blitz = s.get('blitz', 'OFF') if s.get('blitz') in BLITZ_OPTIONS else 'OFF'
            self.settings_board = s.get('board', 'CLASSIC') if s.get('board') in BOARD_STYLES else 'CLASSIC'
            self.settings_theme = s.get('theme', 'ROYAL') if s.get('theme') in THEMES else 'ROYAL'
            self.settings_ui_style = s.get('ui_style', 'MATERIAL 3') if s.get('ui_style') in UI_STYLES else 'MATERIAL 3'
            self.settings_glass = bool(s.get('glass', True))
            self.settings_show_fps = bool(s.get('show_fps', False))
            try:
                self.music_volume = max(0.0, min(1.0, float(s.get('music_volume', 1.0))))
                self.sfx_volume = max(0.0, min(1.0, float(s.get('sfx_volume', 1.0))))
            except (TypeError, ValueError):
                pass

    def save_settings(self):
        try:
            self.store.put('settings',
                           undo=self.settings_undo,
                           hint=self.settings_hint,
                           mandatory_jump=self.settings_mandatory_jump,
                           fps=self.settings_fps,
                           visuals=self.settings_visuals,
                           theme=self.settings_theme,
                           board=self.settings_board,
                           blitz=self.settings_blitz,
                           ui_style=self.settings_ui_style,
                           glass=self.settings_glass,
                           show_fps=self.settings_show_fps,
                           music_volume=self.music_volume,
                           sfx_volume=self.sfx_volume)
        except Exception as exc:
            Logger.warning("Settings: save failed: %s", exc)

    def toggle_setting(self, key, value):
        value = bool(value)
        if key == 'undo':
            self.settings_undo = value
        elif key == 'hint':
            self.settings_hint = value
        elif key == 'mandatory_jump':
            self.settings_mandatory_jump = value
        elif key == 'glass':
            self.settings_glass = value
        elif key == 'show_fps':
            self.settings_show_fps = value
            if hasattr(self, 'fps_overlay'):
                self.fps_overlay.set_enabled(value)
        self.save_settings()

    def apply_fps_limit(self):
        """Make the FPS cap take effect immediately (and on next launch)."""
        fps = _sanitize_fps(self.settings_fps)
        self.settings_fps = fps
        Config.set('graphics', 'maxfps', str(fps))
        try:
            Clock._max_fps = float(fps)
        except Exception as exc:  # pragma: no cover - very old Kivy
            Logger.warning("FPS: could not apply live cap: %s", exc)
        if hasattr(self, 'fps_overlay') and self.settings_show_fps:
            self.fps_overlay._tick(0)

    def cycle_fps(self):
        idx = FPS_OPTIONS.index(self.settings_fps) if self.settings_fps in FPS_OPTIONS else 1
        self.settings_fps = FPS_OPTIONS[(idx + 1) % len(FPS_OPTIONS)]
        self.apply_fps_limit()
        self.save_settings()

    def cycle_blitz(self):
        idx = BLITZ_OPTIONS.index(self.settings_blitz) if self.settings_blitz in BLITZ_OPTIONS else 0
        self.settings_blitz = BLITZ_OPTIONS[(idx + 1) % len(BLITZ_OPTIONS)]
        self.save_settings()

    def cycle_visuals(self):
        idx = VISUAL_OPTIONS.index(self.settings_visuals) if self.settings_visuals in VISUAL_OPTIONS else 0
        self.settings_visuals = VISUAL_OPTIONS[(idx + 1) % len(VISUAL_OPTIONS)]
        if hasattr(self, 'board_widget'):
            self.board_widget.clear_all_hints()
            self.board_widget.render_pieces()
        self.save_settings()

    def cycle_ui_style(self):
        idx = UI_STYLES.index(self.settings_ui_style) if self.settings_ui_style in UI_STYLES else 0
        self.settings_ui_style = UI_STYLES[(idx + 1) % len(UI_STYLES)]
        self.save_settings()

    def rgb_to_hex(self, rgb):
        return "#{:02x}{:02x}{:02x}".format(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

    def cycle_theme(self):
        opts = list(THEMES.keys())
        idx = opts.index(self.settings_theme) if self.settings_theme in opts else 0
        self.settings_theme = opts[(idx + 1) % len(opts)]
        self.apply_theme()
        self.refresh_ui_tokens()
        self.save_settings()

    def cycle_board(self):
        opts = list(BOARD_STYLES.keys())
        idx = opts.index(self.settings_board) if self.settings_board in opts else 0
        self.settings_board = opts[(idx + 1) % len(opts)]
        self.save_settings()

    def apply_theme(self):
        theme = THEMES.get(self.settings_theme, THEMES['ROYAL'])
        self.p1_name = theme['p1']['name']
        self.p2_name = theme['p2']['name']
        self.theme_p1_light = theme['p1']['light']
        self.theme_p1_main = theme['p1']['main']
        self.theme_p1_dark = theme['p1']['dark']
        self.theme_p1_star = theme['p1']['star']
        self.theme_p1_text = theme['p1']['text']
        self.theme_p2_light = theme['p2']['light']
        self.theme_p2_main = theme['p2']['main']
        self.theme_p2_dark = theme['p2']['dark']
        self.theme_p2_star = theme['p2']['star']
        self.theme_p2_text = theme['p2']['text']
        self.theme_accent = theme['ui']['accent']
        self.theme_accent_text = theme['ui']['accent_text']
        self.theme_panel = theme['ui']['panel']
        self.theme_bg_top = theme['ui']['bg_top']
        self.theme_bg_bot = theme['ui']['bg_bot']
        self.p1_hex = self.rgb_to_hex(self.theme_p1_light)
        self.p2_hex = self.rgb_to_hex(self.theme_p2_light)
        self.update_display_names()

    def update_display_names(self):
        p1 = self.p1_name.title() if self.ui_material else self.p1_name
        p2 = self.p2_name.title() if self.ui_material else self.p2_name
        you = "(You)" if self.ui_material else "(YOU)"
        opp = "(Opp)" if self.ui_material else "(OPP)"
        if self.game_mode == 'online':
            self.p1_display_name = "%s %s" % (p1, you if self.online_player_id == 1 else opp)
            self.p2_display_name = "%s %s" % (p2, you if self.online_player_id == 2 else opp)
        elif self.game_mode == 'campaign':
            self.p1_display_name = "%s %s" % (p1, you)
            self.p2_display_name = self.boss_name.title() if self.ui_material else self.boss_name
        elif self.game_mode == 'computer':
            ai = "AI (%s)" % (self.ai_mode.title() if self.ui_material else self.ai_mode.upper())
            self.p1_display_name = "%s %s" % (p1, you) if self.human_player == 1 else p1
            self.p2_display_name = "%s %s" % (p2, you) if self.human_player == 2 else ai
        else:
            self.p1_display_name = p1
            self.p2_display_name = p2

    def on_ui_material(self, *args):
        self.update_display_names()

    # ------------------------------------------------------------------ stats
    def load_stats(self):
        stats = self.store.get('stats') if self.store.exists('stats') else {}
        self.stat_wins_easy = stats.get('easy_w', 0)
        self.stat_loss_easy = stats.get('easy_l', 0)
        self.stat_wins_medium = stats.get('medium_w', 0)
        self.stat_loss_medium = stats.get('medium_l', 0)
        self.stat_wins_hard = stats.get('hard_w', 0)
        self.stat_loss_hard = stats.get('hard_l', 0)

    def record_match_result(self, diff, is_win):
        if diff == 'easy':
            if is_win:
                self.stat_wins_easy += 1
            else:
                self.stat_loss_easy += 1
        elif diff == 'medium':
            if is_win:
                self.stat_wins_medium += 1
            else:
                self.stat_loss_medium += 1
        elif diff == 'hard':
            if is_win:
                self.stat_wins_hard += 1
            else:
                self.stat_loss_hard += 1
        try:
            self.store.put('stats',
                           easy_w=self.stat_wins_easy, easy_l=self.stat_loss_easy,
                           medium_w=self.stat_wins_medium, medium_l=self.stat_loss_medium,
                           hard_w=self.stat_wins_hard, hard_l=self.stat_loss_hard)
        except Exception as exc:
            Logger.warning("Stats: save failed: %s", exc)

    # ------------------------------------------------------------------ timer
    def start_timer(self):
        self.stop_timer()
        if self.settings_blitz == 'OFF':
            return
        if self.game_mode in ('computer', 'campaign') and self.current_turn != self.human_player:
            return
        if self.game_mode == 'online' and self.current_turn != self.online_player_id:
            return

        time_map = {'3 SEC': 3.0, '5 SEC': 5.0, '8 SEC': 8.0}
        self.max_time = time_map.get(self.settings_blitz, 5.0)
        self.current_time_left = self.max_time
        self.blitz_event = Clock.schedule_interval(self.tick_timer, 0.05)

    def stop_timer(self):
        if self.blitz_event:
            self.blitz_event.cancel()
            self.blitz_event = None

    def tick_timer(self, dt):
        self.current_time_left -= dt
        if self.current_time_left <= 0:
            self.current_time_left = 0
            self.stop_timer()
            self.trigger_haptic(0.1)
            self.force_random_move()

    def force_random_move(self):
        if self.screen_manager.current != 'game_screen':
            return
        if self.board_widget.is_animating:
            Clock.schedule_once(lambda dt: self.force_random_move(), 0.1)
            return
        self.board_widget.clear_all_hints()
        self.board_widget.selected_piece_coords = None
        moves = GameEngine.get_valid_moves(self.current_turn, self.board_state, self.must_jump_rule())
        if moves:
            self.play_click_sound()
            chosen = random.choice(moves)
            if self.game_mode == 'online':
                self.network.send_move(chosen['start'], chosen['end'])
            self.board_widget.execute_move(chosen)

    # --------------------------------------------------------------- actions
    def trigger_undo(self):
        if not self.settings_undo or not self.undo_stack or self.game_mode in ('campaign', 'online'):
            return
        if self.is_thinking or self.board_widget.is_animating:
            return
        last_state = self.undo_stack.pop()
        self.board_state = last_state['board']
        self.current_turn = last_state['turn']
        self.board_widget.last_move = last_state.get('last_move')
        self.board_widget.selected_piece_coords = None
        self.board_widget.clear_all_hints()
        self.board_widget.render_board_background()
        self.board_widget.render_pieces()
        self.start_timer()

    def trigger_hint(self):
        if self.is_thinking or self.board_widget.is_animating:
            return
        if self.game_mode in ('campaign', 'online') or not self.settings_hint:
            return
        if self.game_mode == 'computer' and self.current_turn != self.human_player:
            return
        must_jump = self.must_jump_rule()
        possible_moves = GameEngine.get_valid_moves(self.current_turn, self.board_state, must_jump)
        if not possible_moves:
            return
        result = GameEngine.minimax(self.board_state, 2, float('-inf'), float('inf'), True, self.current_turn, 3 - self.current_turn, must_jump)
        chosen_move = result['move'] if result['move'] else possible_moves[0]
        self.board_widget.pulse_hint_piece(chosen_move)

    def surrender_match(self):
        if self.game_mode == 'online':
            self.network.send_leave_match()
            self.network.disconnect()
            self.quit_to_menu()
        else:
            self.current_turn = RED if self.human_player == BLUE else BLUE
            self.trigger_game_over()

    def trigger_game_over(self, disconnect=False):
        if self.screen_manager.current == 'game_over_screen' or self._game_over_pending:
            return
        self._game_over_pending = True
        self.stop_timer()

        self.opponent_left = disconnect
        winner_code = RED if self.current_turn == BLUE else BLUE
        winner_name = self.p2_name if winner_code == RED else self.p1_name
        winner_color = self.theme_p2_light if winner_code == RED else self.theme_p1_light
        winner_score = self.p2_pieces if winner_code == RED else self.p1_pieces

        if self.game_mode == 'campaign' and winner_code != self.human_player:
            winner_name = self.boss_name
        elif self.game_mode == 'online':
            if disconnect:
                winner_code = self.online_player_id
                winner_name = self.p1_name if self.online_player_id == 1 else self.p2_name
                winner_color = self.theme_p1_light if self.online_player_id == 1 else self.theme_p2_light
            elif winner_code != self.online_player_id:
                winner_name = "ONLINE OPPONENT"

        opponent_pieces = sum(1 for r in range(ROWS) for c in range(COLS)
                              if self.board_state[r][c] != EMPTY and abs(self.board_state[r][c]) == self.current_turn)

        human_won = True
        if self.game_mode == 'computer':
            human_won = (winner_code == self.human_player)
            self.record_match_result(self.ai_mode, human_won)
        elif self.game_mode == 'campaign':
            human_won = (winner_code == self.human_player)
            if human_won:
                self.campaign_progress = max(self.campaign_progress, self.current_boss_level + 1)
                try:
                    self.store.put('campaign', progress=self.campaign_progress)
                except Exception:
                    pass
        elif self.game_mode == 'online':
            human_won = (winner_code == self.online_player_id)

        try:
            if self.sound_lose and self.game_mode in ('computer', 'campaign', 'online') and not human_won:
                self.sound_lose.play()
            elif self.sound_win:
                self.sound_win.play()
        except Exception:
            pass

        gs = self.screen_manager.get_screen('game_screen')
        end_txt = "Checkmate!" if opponent_pieces > 0 else "Game over!"
        gs.ids.turn_indicator.text = end_txt if self.ui_material else end_txt.upper()
        gs.ids.turn_indicator.color = (1, 0.843, 0, 1)

        go_screen = self.screen_manager.get_screen('game_over_screen')
        m = self.ui_material
        if disconnect and self._net_error:
            human_won = False
            body = ("Connection lost\n[size=14sp](match abandoned)[/size]" if m
                    else "CONNECTION LOST\n[size=14sp](MATCH ABANDONED)[/size]")
            color = [1, 0.4, 0.4, 1]
        elif disconnect:
            body = ("You win!\n[size=14sp](opponent disconnected)[/size]" if m
                    else "YOU WIN!\n[size=14sp](OPPONENT DISCONNECTED)[/size]")
            color = list(self.theme_accent)
        else:
            name = winner_name.title() if m else winner_name
            if m:
                how = "wins by checkmate!" if opponent_pieces > 0 else "wins!"
                body = "%s %s\n[size=14sp](%s pieces remaining)[/size]" % (name, how, winner_score)
            else:
                how = "WINS BY CHECKMATE!" if opponent_pieces > 0 else "WINS!"
                body = "%s %s\n[size=14sp](%s PIECES REMAINING)[/size]" % (name, how, winner_score)
            color = [winner_color[0], winner_color[1], winner_color[2], 1]
        go_screen.ids.winner_label.text = body
        go_screen.ids.winner_label.color = color
        title = "Victory!" if (human_won and self.game_mode != 'local') else "Match over"
        go_screen.ids.over_title.text = title if m else title.upper()
        self._celebrate = human_won and self.game_mode != 'local'

        mid = self.match_id
        Clock.schedule_once(lambda dt: self._show_game_over(mid), 0.55)

    def _show_game_over(self, mid):
        self._game_over_pending = False
        if mid != self.match_id:
            return  # player already quit this match
        self.switch_screen('game_over_screen')
        if getattr(self, '_celebrate', False) and self.fx_high:
            go_screen = self.screen_manager.get_screen('game_over_screen')
            colors = [self.theme_accent, self.theme_p1_light, self.theme_p2_light, [1, 1, 1, 1]]
            Clock.schedule_once(lambda dt: go_screen.ids.confetti.burst(colors), 0.15)

    def on_rematch_pressed(self, button):
        if self.game_mode == 'online':
            if self.network.request_rematch():
                button.text = self.L("Waiting...", self.ui_material)
                button.disabled = True
            else:
                self.show_toast("Connection lost")
        else:
            self.start_game(self.game_mode, self.current_boss_level)

    # ------------------------------------------------------------------ audio
    def _load_next_audio(self, dt):
        if not self.audio_queue:
            if self.music_bg and self.music_volume > 0:
                try:
                    self.music_bg.play()
                except Exception:
                    pass
            return False
        item = self.audio_queue.pop(0)
        try:
            if 'click' in item:
                s = SoundLoader.load('click.wav')
                if s:
                    s.volume = self.sfx_volume
                    self.click_pool.append(s)
            elif item == 'win':
                self.sound_win = SoundLoader.load('win.wav')
                if self.sound_win:
                    self.sound_win.volume = self.sfx_volume
            elif item == 'lose':
                self.sound_lose = SoundLoader.load('tieorlose.wav')
                if self.sound_lose:
                    self.sound_lose.volume = self.sfx_volume
            elif item == 'music':
                self.music_bg = SoundLoader.load('music.ogg')
                if self.music_bg:
                    self.music_bg.loop = True
                    self.music_bg.volume = self.music_volume
        except Exception:
            pass

    def set_music_volume(self, val):
        self.music_volume = max(0.0, min(1.0, val / 100.0))
        try:
            if self.music_bg:
                self.music_bg.volume = self.music_volume
                if self.music_volume > 0 and self.music_bg.state != 'play':
                    self.music_bg.play()
        except Exception:
            pass
        self._schedule_settings_save()

    def set_sfx_volume(self, val):
        self.sfx_volume = max(0.0, min(1.0, val / 100.0))
        try:
            for s in self.click_pool:
                s.volume = self.sfx_volume
            if self.sound_win:
                self.sound_win.volume = self.sfx_volume
            if self.sound_lose:
                self.sound_lose.volume = self.sfx_volume
        except Exception:
            pass
        self._schedule_settings_save()

    def _schedule_settings_save(self):
        Clock.unschedule(self._deferred_save)
        Clock.schedule_once(self._deferred_save, 0.6)

    def _deferred_save(self, dt):
        self.save_settings()

    def play_click_sound(self):
        if len(self.click_pool) > 0:
            try:
                sound = self.click_pool[self.click_index]
                if sound.state == 'play':
                    sound.stop()
                sound.play()
                self.click_index = (self.click_index + 1) % len(self.click_pool)
            except Exception:
                pass

    # ------------------------------------------------------------ navigation
    def quit_to_menu(self):
        self.match_id += 1
        self.stop_timer()
        self._pending_net_moves = []
        self._game_over_pending = False
        if self.game_mode == 'online':
            self.network.disconnect()
        self.switch_screen('start_screen')

    def switch_screen(self, screen_name):
        if hasattr(self, 'board_widget'):
            self.board_widget.clear_all_hints()
        if screen_name == 'pause_screen':
            self.stop_timer()

        sm = self.screen_manager
        if not sm.has_screen(screen_name):
            return
        if sm.current == screen_name:
            return

        self._switch_seq += 1
        seq = self._switch_seq
        old = sm.current_screen

        def commit():
            sm.current = screen_name
            new = sm.get_screen(screen_name)
            new.play_enter()

        if not self.fx_high or old is None:
            if old is not None:
                old.opacity = 1
            commit()
            return

        Animation.cancel_all(old, 'opacity')
        fade = Animation(opacity=0, duration=0.09, transition='out_quad')

        def done(*args):
            if seq != self._switch_seq:
                return
            old.opacity = 1
            commit()

        fade.bind(on_complete=done)
        fade.start(old)

    def show_error(self, message):
        self.matchmaking_status = message
        self.network.disconnect()
        if self.screen_manager.current != 'matchmaking_screen' and self.game_mode == 'online':
            # An error mid-match: we lost the connection, not the opponent.
            self._net_error = True
            self.handle_disconnect()

    # ---------------------------------------------------------------- network
    def start_online_match(self):
        self.game_mode = 'online'
        self._pending_net_moves = []
        self.network.connect()

    def cancel_matchmaking(self):
        self.network.disconnect()
        self.switch_screen('start_screen')

    def handle_network_data(self, data):
        if not isinstance(data, dict) or 'action' not in data:
            return
        t = data['action']
        try:
            if t == 'match_start':
                self.online_player_id = int(data.get('color', BLUE))
                self.start_game('online')

            elif t == 'state_update':
                start = tuple(int(v) for v in data['start'])
                end = tuple(int(v) for v in data['end'])
                self._pending_net_moves.append((start, end))
                self.flush_pending_network_moves()

            elif t == 'rematch_accepted':
                self.start_game('online', rematch=True)

            elif t == 'opponent_disconnected':
                self.handle_disconnect()
        except Exception as exc:
            Logger.warning("Network: bad payload %r (%s)", data, exc)

    def flush_pending_network_moves(self):
        """Apply queued opponent moves. Moves are queued (not dropped) while an
        animation is running or the player is on the pause screen."""
        if not self._pending_net_moves or self.game_mode != 'online':
            return
        if self.screen_manager.current not in ('game_screen', 'pause_screen'):
            return
        if self.board_widget.is_animating:
            Clock.schedule_once(lambda dt: self.flush_pending_network_moves(), 0.08)
            return
        if self.current_turn == self.online_player_id:
            # Not the opponent's turn: a stale/duplicate packet, drop it.
            self._pending_net_moves.pop(0)
            return
        start, end = self._pending_net_moves.pop(0)
        allowed_moves = GameEngine.get_valid_moves(self.current_turn, self.board_state, self.settings_mandatory_jump)
        chosen_move = next((m for m in allowed_moves if m['start'] == start and m['end'] == end), None)
        if chosen_move:
            self.board_widget.execute_move(chosen_move)
        else:
            Logger.warning("Network: opponent move %s->%s is not legal locally; ignored", start, end)

    def handle_disconnect(self):
        if self.game_mode != 'online':
            return
        self.stop_timer()
        self._pending_net_moves = []
        if self.screen_manager.current in ['game_screen', 'pause_screen']:
            self.trigger_game_over(disconnect=True)
        elif self.screen_manager.current == 'game_over_screen':
            self.opponent_left = True
        else:
            self.switch_screen('start_screen')

    # ----------------------------------------------------------- match flow
    def resume_game(self):
        self.switch_screen('game_screen')
        self.start_timer()
        self.flush_pending_network_moves()

    def start_ai_game(self, diff, boss_level=0):
        self.ai_mode = diff
        self.start_game('computer', boss_level)

    def start_campaign_boss(self, level):
        self.boss_name = ["", "THE ROOKIE", "THE TACTICIAN", "THE AWAKENED", "THE OVERLORD"][level]
        diffs = ["", "easy", "medium", "hard", "hard"]
        self.ai_mode = diffs[level]
        self.start_game('campaign', level)

    def start_game(self, mode, boss_level=0, rematch=False):
        self.game_mode = mode
        self.current_boss_level = boss_level
        self.is_thinking = False
        self.opponent_left = False
        self._game_over_pending = False
        self.board_widget.is_animating = False
        self.board_widget._disarm_guard()
        self.board_widget.last_move = None
        self.board_state = GameEngine.get_initial_board(boss_level)
        self._pending_net_moves = []

        if mode == 'online':
            self.current_turn = BLUE
        else:
            self.current_turn = self.human_player

        self.update_display_names()
        self.refresh_turn_text()
        self.newly_promoted = None
        self.undo_stack.clear()

        if not rematch:
            self.match_id += 1

        self.board_widget.selected_piece_coords = None
        self.board_widget.clear_all_hints()

        go_screen = self.screen_manager.get_screen('game_over_screen')
        go_screen.ids.rematch_btn.disabled = False
        go_screen.ids.rematch_btn.text = self.L("Play again" if mode != 'online' else "Request rematch", self.ui_material)
        go_screen.ids.confetti.stop()

        gs = self.screen_manager.get_screen('game_screen')
        gs.ids.turn_indicator.color = (1, 1, 1, 1)
        gs.ids.turn_indicator.text = self.turn_text
        self._net_error = False

        self.switch_screen('game_screen')
        Clock.schedule_once(self._after_game_screen_shown, 0.2)
        self.start_timer()

    def _after_game_screen_shown(self, dt):
        self.board_widget.calculate_board_size()
        self.board_widget.play_intro()

    # ---------------------------------------------------------------- AI turn
    def trigger_ai_turn(self):
        must_jump = self.must_jump_rule()
        possible_moves = GameEngine.get_valid_moves(self.current_turn, self.board_state, must_jump)
        if not possible_moves:
            return
        self.is_thinking = True

        if self.ai_mode == 'easy':
            chosen_move = random.choice(possible_moves)
            Clock.schedule_once(lambda dt: self.apply_ai_move(chosen_move, self.match_id), 0.5)
        else:
            pure_board = [row[:] for row in self.board_state]
            threading.Thread(target=self.run_ai_math, args=(
                possible_moves,
                pure_board,
                self.ai_mode,
                self.current_turn,
                self.human_player,
                must_jump,
                self.match_id,
                self.current_boss_level
            ), daemon=True).start()

    def run_ai_math(self, possible_moves, pure_board, ai_diff, current_turn, human_player, must_jump, thread_match_id, boss_level):
        depth = 4 if (ai_diff == 'hard' or boss_level == 4) else 2
        try:
            result = GameEngine.minimax(pure_board, depth, float('-inf'), float('inf'), True, current_turn, human_player, must_jump)
            chosen_move = result['move'] if result['move'] else possible_moves[0]
        except Exception as exc:
            Logger.warning("AI: minimax failed (%s), falling back to random move", exc)
            chosen_move = random.choice(possible_moves)
        Clock.schedule_once(lambda dt: self.apply_ai_move(chosen_move, thread_match_id), 0.45)

    @mainthread
    def apply_ai_move(self, chosen_move, thread_match_id):
        if self.match_id != thread_match_id:
            return
        if self.screen_manager.current not in ('game_screen', 'pause_screen'):
            self.is_thinking = False
            return
        if self.board_widget.is_animating:
            Clock.schedule_once(lambda dt: self.apply_ai_move(chosen_move, thread_match_id), 0.1)
            return
        self.is_thinking = False
        self.board_widget.execute_move(chosen_move)


if __name__ == '__main__':
    CheckersApp().run()
