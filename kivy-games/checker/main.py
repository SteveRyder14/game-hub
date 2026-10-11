# ==============================================================================
# HIGH-RES ANIMATED CHECKERS - ONLINE PVP EDITION (GOLDEN MASTER)
# ==============================================================================

import os
import json
import random
import threading 
from kivy.config import Config

Config.set('graphics', 'multisamples', '0')
Config.set('graphics', 'maxfps', '60')
Config.set('kivy', 'exit_on_escape', '0')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Ellipse, Line, PushMatrix, PopMatrix, Scale, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.core.audio import SoundLoader 
from kivy.clock import Clock, mainthread
from kivy.animation import Animation
from kivy.properties import NumericProperty, BooleanProperty, StringProperty, ListProperty
from kivy.metrics import dp, sp
from kivy.utils import platform
from kivy.storage.jsonstore import JsonStore

try:
    from plyer import vibrator
except ImportError:
    vibrator = None

try:
    import websocket
except ImportError:
    websocket = None

if platform not in ('android', 'ios'):
    Window.size = (390, 800) 

ROWS = 8
COLS = 8
BLUE = 1 
RED = 2  
EMPTY = 0
WEBSOCKET_URL = "wss://tictactoe-server-ql1y.onrender.com/checkerboard"

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

class NetworkManager:
    def __init__(self, app):
        self.app = app
        self.ws = None
        self.connected = False

    def connect(self):
        if not websocket:
            self.app.show_error("WEBSOCKET LIBRARY MISSING")
            return

        self.app.matchmaking_status = "CONNECTING..."
        self.app.switch_screen('matchmaking_screen')

        def run_ws():
            try:
                self.ws = websocket.WebSocketApp(
                    WEBSOCKET_URL,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_close=self.on_close,
                    on_error=self.on_error
                )
                self.ws.run_forever(ping_interval=20, ping_timeout=15)
            except Exception:
                pass

        threading.Thread(target=run_ws, daemon=True).start()
        Clock.schedule_once(self.check_waking, 4.0)
        Clock.schedule_once(self.check_timeout, 15.0)

    def check_waking(self, dt):
        if not self.connected and self.app.screen_manager.current == 'matchmaking_screen' and self.app.matchmaking_status == "CONNECTING...":
            self.app.matchmaking_status = "WAKING UP SERVER..."

    def check_timeout(self, dt):
        if not self.connected and self.app.screen_manager.current == 'matchmaking_screen':
            self.app.show_error("SERVER IS OFFLINE")
            if self.ws: self.ws.close()

    def on_open(self, ws):
        self.connected = True
        self.app.matchmaking_status = "SEARCHING FOR MATCH..."
        payload = {
            "action": "join_queue",
            "color": self.app.human_player,
            "mandatory_jump": self.app.settings_mandatory_jump,
            "blitz": self.app.settings_blitz
        }
        self.ws.send(json.dumps(payload))

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            Clock.schedule_once(lambda dt: self.app.handle_network_data(data))
        except Exception:
            pass

    def on_error(self, ws, error):
        Clock.schedule_once(lambda dt: self.app.show_error("CONNECTION LOST"))

    def on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        self.ws = None
        Clock.schedule_once(lambda dt: self.app.handle_disconnect())

    def send_move(self, start, end):
        if self.connected and self.ws:
            try:
                payload = json.dumps({"action": "submit_move", "start": start, "end": end})
                self.ws.send(payload)
            except Exception:
                pass

    def request_rematch(self):
        if self.connected and self.ws:
            try:
                self.ws.send(json.dumps({"action": "request_rematch"}))
            except Exception:
                pass

    def send_leave_match(self):
        if self.connected and self.ws:
            try:
                self.ws.send(json.dumps({"action": "leave_match"}))
            except Exception:
                pass

    def disconnect(self):
        if self.connected and self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self.connected = False
        self.ws = None

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
        if not (0 <= end_r < ROWS and 0 <= end_c < COLS): return {'valid': False}
        if board_array[end_r][end_c] != EMPTY: return {'valid': False}
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
                if not is_king and row_diff != direction * 2: return {'valid': False} 
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
            if piece_type > 0: piece_type = -piece_type
        temp_board[er][ec] = piece_type

    @staticmethod
    def evaluate_board(board_array, ai_player):
        score = 0
        opponent = RED if ai_player == BLUE else BLUE
        for r in range(ROWS):
            for c in range(COLS):
                piece = board_array[r][c]
                if piece == EMPTY: continue
                
                abs_piece = abs(piece)
                is_king = piece < 0
                edge_bonus = 2 if c == 0 or c == COLS - 1 else 0
                center_bonus = 3 if (2 <= r <= 5 and 2 <= c <= 5) else 0
                advancement = 0 if is_king else (r if abs_piece == BLUE else 7 - r)

                piece_val = (25 + center_bonus) if is_king else (10 + advancement + edge_bonus)
                if abs_piece == ai_player: score += piece_val
                elif abs_piece == opponent: score -= piece_val
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
                if beta <= alpha: break
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
                if beta <= alpha: break
            return {'score': min_eval, 'move': best_move}

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
            buf = bytes([b_rgba[0], b_rgba[1], b_rgba[2], b_rgba[3], t_rgba[0], t_rgba[1], t_rgba[2], t_rgba[3]])
            self._texture.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
            self.update_rect()
        except Exception: pass

    def update_rect(self, *args):
        self.canvas.before.clear()
        if self.width <= 0 or self.height <= 0: return
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size, texture=self._texture)

class AmbientFlair(Widget):
    orb1_scale = NumericProperty(1.0)
    orb2_scale = NumericProperty(1.0)
    orb3_scale = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.start_breathing, 0.5)

    def start_breathing(self, dt):
        a1 = Animation(orb1_scale=1.15, duration=4.5, transition='in_out_sine') + Animation(orb1_scale=0.9, duration=4.5, transition='in_out_sine')
        a1.repeat = True; a1.start(self)
        a2 = Animation(orb2_scale=1.2, duration=6.0, transition='in_out_sine') + Animation(orb2_scale=0.85, duration=6.0, transition='in_out_sine')
        a2.repeat = True; a2.start(self)
        a3 = Animation(orb3_scale=1.1, duration=5.2, transition='in_out_sine') + Animation(orb3_scale=0.95, duration=5.2, transition='in_out_sine')
        a3.repeat = True; a3.start(self)

class CompactPlayerCard(BoxLayout):
    player_name = StringProperty("PLAYER")
    piece_count = NumericProperty(12)
    theme_color = ListProperty([1, 1, 1, 1])
    is_active = BooleanProperty(False)
    aura_scale = NumericProperty(1.0)
    aura_alpha = NumericProperty(0.0)

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

class AnimBtn(Button):
    anim_scale = NumericProperty(1.0)
    def on_press(self):
        super().on_press()
        App.get_running_app().play_click_sound()
        App.get_running_app().trigger_haptic(0.02)
        Animation.cancel_all(self, 'anim_scale')
        Animation(anim_scale=0.92, duration=0.03, transition='out_quad').start(self)
    def on_release(self):
        super().on_release()
        Animation.cancel_all(self, 'anim_scale')
        Animation(anim_scale=1.0, duration=0.1, transition='out_elastic').start(self)

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
            Animation(thumb_progress=target, duration=0.15, transition='out_cubic').start(self)
            return True
        return super().on_touch_down(touch)
    def on_kv_post(self, base_widget):
        app = App.get_running_app()
        if app: self.thumb_progress = 0.0 if app.human_player == BLUE else 1.0

class HintTargetWidget(Widget):
    anim_alpha = NumericProperty(0.0)
    def start_anim(self):
        self.anim_alpha = 0.2
        anim = Animation(anim_alpha=0.6, duration=0.6, transition='in_out_sine')
        anim += Animation(anim_alpha=0.2, duration=0.6, transition='in_out_sine')
        anim.repeat = True
        anim.start(self)

class RadarPing(Widget):
    ping_scale = NumericProperty(1.0)
    ping_alpha = NumericProperty(0.8)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_ping()
    def start_ping(self):
        anim = Animation(ping_scale=3.0, ping_alpha=0.0, duration=1.5, transition='out_sine')
        anim += Animation(ping_scale=1.0, ping_alpha=0.8, duration=0.0)
        anim.repeat = True
        anim.start(self)

# ==============================================================================
# 5. KV DESIGN LANGUAGE
# ==============================================================================
KV = '''
<BackgroundLayer@FloatLayout>:
    GradientBackground:
        top_color: app.theme_bg_top
        bot_color: app.theme_bg_bot
        pos: self.pos
        size: self.size
    AmbientFlair:
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
            size: (self.width * 0.9 if self.width > dp(1) else dp(1), self.width * 0.9 if self.width > dp(1) else dp(1))
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
            size: (self.width * 0.8 if self.width > dp(1) else dp(1), self.width * 0.8 if self.width > dp(1) else dp(1))
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
            size: (self.width * 0.7 if self.width > dp(1) else dp(1), self.width * 0.7 if self.width > dp(1) else dp(1))
        PopMatrix:
        
    canvas:
        Color:
            rgba: 1, 1, 1, 0.03
        Line:
            circle: [self.right - dp(20), self.top - dp(50), self.width * 0.4 if self.width > dp(1) else dp(1)]
            width: dp(1.5)
            cap: 'round'
            joint: 'round'
        Line:
            circle: [self.x + dp(40), self.y + dp(100), self.width * 0.5 if self.width > dp(1) else dp(1)]
            width: dp(1)
            cap: 'round'
            joint: 'round'

<PieceWidget>:
    canvas.before:
        PushMatrix:
        Scale:
            x: self.piece_scale
            y: self.piece_scale
            z: 1.0
            origin: self.center
    canvas:
        Color:
            rgba: 0, 0, 0, 0.15 * self.opacity
        Ellipse:
            pos: (self.x - dp(2), self.y - dp(6))
            size: (self.width + dp(4) if self.width > dp(1) else dp(1), self.height + dp(4) if self.height > dp(1) else dp(1))
        Color:
            rgba: 0, 0, 0, 0.3 * self.opacity
        Ellipse:
            pos: (self.x, self.y - dp(3))
            size: self.size

        # King's Aura
        Color:
            rgba: (1, 0.84, 0, (1.5 - self.king_pulse) * self.opacity) if self.piece_type < 0 else (0,0,0,0)
        Line:
            circle: [self.center_x, self.center_y, (self.width * self.king_pulse) / 2 if self.width > dp(1) else dp(1)]
            width: dp(2)
            cap: 'round'

        # Selection Highlight
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], (self.highlight_alpha * self.opacity) * 0.25
        Ellipse:
            pos: self.center_x - (self.width * self.highlight_scale)/2, self.center_y - (self.height * self.highlight_scale)/2
            size: (self.width * self.highlight_scale if self.width > dp(1) else dp(1), self.height * self.highlight_scale if self.height > dp(1) else dp(1))
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], self.highlight_alpha * self.opacity
        Line:
            ellipse: [self.center_x - (self.width * self.highlight_scale)/2, self.center_y - (self.height * self.highlight_scale)/2, self.width * self.highlight_scale if self.width > dp(1) else dp(1), self.height * self.highlight_scale if self.height > dp(1) else dp(1)]
            width: dp(2)
            cap: 'round'
            joint: 'round'

        # Main Piece Color
        Color:
            rgba: (app.theme_p1_dark[0], app.theme_p1_dark[1], app.theme_p1_dark[2], self.opacity) if abs(self.piece_type) == 1 else (app.theme_p2_dark[0], app.theme_p2_dark[1], app.theme_p2_dark[2], self.opacity)
        Ellipse:
            pos: self.pos
            size: self.size

        Color:
            rgba: (app.theme_p1_main[0], app.theme_p1_main[1], app.theme_p1_main[2], self.opacity) if abs(self.piece_type) == 1 else (app.theme_p2_main[0], app.theme_p2_main[1], app.theme_p2_main[2], self.opacity)
        Ellipse:
            pos: (self.x + dp(2), self.y + dp(2))
            size: (self.width - dp(4) if self.width > dp(4) else dp(0.1), self.height - dp(4) if self.height > dp(4) else dp(0.1))

        Color:
            rgba: (app.theme_p1_light[0], app.theme_p1_light[1], app.theme_p1_light[2], self.opacity) if abs(self.piece_type) == 1 else (app.theme_p2_light[0], app.theme_p2_light[1], app.theme_p2_light[2], self.opacity)
        Ellipse:
            pos: (self.x + dp(8), self.y + dp(8))
            size: (self.width - dp(16) if self.width > dp(16) else dp(0.1), self.height - dp(16) if self.height > dp(16) else dp(0.1))

        Color:
            rgba: 1, 1, 1, 0.2 * self.opacity
        Line:
            ellipse: [self.x + dp(4), self.y + dp(4), self.width - dp(8) if self.width > dp(8) else dp(0.1), self.height - dp(8) if self.height > dp(8) else dp(0.1)]
            width: dp(1.2)
            cap: 'round'
            joint: 'round'

        # Star Symbol
        Color:
            rgba: (app.theme_p1_star[0], app.theme_p1_star[1], app.theme_p1_star[2], 0.9 * self.opacity) if abs(self.piece_type) == 1 and self.piece_type < 0 else ((app.theme_p2_star[0], app.theme_p2_star[1], app.theme_p2_star[2], 0.9 * self.opacity) if abs(self.piece_type) == 2 and self.piece_type < 0 else (1, 1, 1, 0))
        Ellipse:
            pos: (self.x + (self.width - self.width * 0.35)/2, self.y + (self.height - self.height * 0.35)/2)
            size: (self.width * 0.35 if self.width > dp(1) else dp(1), self.height * 0.35 if self.height > dp(1) else dp(1))
            
    canvas.after:
        PopMatrix:

<HintTargetWidget>:
    canvas.before:
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], self.anim_alpha * 0.2
        RoundedRectangle:
            pos: (self.x + dp(4), self.y + dp(4))
            size: (self.width - dp(8) if self.width > dp(8) else dp(1), self.height - dp(8) if self.height > dp(8) else dp(1))
            radius: [dp(10)]
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], self.anim_alpha * 0.8
        Line:
            rounded_rectangle: [self.x + dp(4), self.y + dp(4), self.width - dp(8) if self.width > dp(8) else dp(1), self.height - dp(8) if self.height > dp(8) else dp(1), dp(10)]
            width: dp(1.5)
            cap: 'round'
            joint: 'round'

<GlassPanel@BoxLayout>:
    orientation: 'vertical'
    size_hint: None, None
    width: dp(320)
    height: self.minimum_height
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.25
        RoundedRectangle:
            pos: (self.x - dp(5), self.y - dp(8))
            size: (self.width + dp(10) if self.width > dp(1) else dp(1), self.height + dp(10) if self.height > dp(1) else dp(1))
            radius: [dp(22)]
        Color:
            rgba: app.theme_panel[0], app.theme_panel[1], app.theme_panel[2], app.theme_panel[3]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(20)]
        Color:
            rgba: 1, 1, 1, 0.08
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(20)]
            width: dp(1.2)
            cap: 'round'
            joint: 'round'

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
            size: (self.width + dp(4) if self.width > dp(1) else dp(1), self.height + dp(4) if self.height > dp(1) else dp(1))
            radius: [dp(14)]
        Color:
            rgba: 0, 0, 0, 0.25
        RoundedRectangle:
            pos: (self.x - dp(3), self.y - dp(4))
            size: (self.width + dp(6) if self.width > dp(1) else dp(1), self.height + dp(6) if self.height > dp(1) else dp(1))
            radius: [dp(14)]
        Color:
            rgba: app.theme_panel[0], app.theme_panel[1], app.theme_panel[2], app.theme_panel[3]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
        Color:
            rgba: (self.theme_color[0], self.theme_color[1], self.theme_color[2], 0.8) if self.is_active else (1, 1, 1, 0.08)
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(12)]
            width: dp(1.5) if self.is_active else dp(1)
            cap: 'round'
            joint: 'round'
            
    Widget:
        size_hint_x: None
        width: dp(26)
        canvas.before:
            Color:
                rgba: root.theme_color[0], root.theme_color[1], root.theme_color[2], root.aura_alpha
            Ellipse:
                pos: (self.center_x - (dp(13) * root.aura_scale), self.center_y - (dp(13) * root.aura_scale))
                size: (dp(26) * root.aura_scale if root.aura_scale > 0.1 else dp(1), dp(26) * root.aura_scale if root.aura_scale > 0.1 else dp(1))
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
        Label:
            text: "[b]YOUR TURN[/b]  •  " + str(root.piece_count) + " LEFT" if root.is_active else str(root.piece_count) + " LEFT"
            markup: True
            font_size: '10sp'
            color: (root.theme_color[0], root.theme_color[1], root.theme_color[2], 1) if root.is_active else (0.5, 0.5, 0.5, 1)
            text_size: self.size
            halign: 'left'
            valign: 'top'


<PremiumBtn@AnimBtn>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    bold: True
    font_size: '14sp'
    size_hint_y: None
    height: dp(54) 
    canvas.before:
        PushMatrix:
        Scale:
            x: self.anim_scale
            y: self.anim_scale
            z: 1.0
            origin: self.center
    canvas.after:
        PopMatrix:

<MenuBtnP1@PremiumBtn>:
    color: app.theme_p1_text
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.2
        RoundedRectangle:
            pos: (self.x, self.y - dp(3)) if self.state == 'normal' else self.pos
            size: self.size
            radius: [dp(14)]
        Color:
            rgba: (app.theme_p1_main[0], app.theme_p1_main[1], app.theme_p1_main[2], 1) if self.state == 'normal' else (app.theme_p1_dark[0], app.theme_p1_dark[1], app.theme_p1_dark[2], 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]

<MenuBtnAccent@PremiumBtn>:
    color: app.theme_accent_text
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.2
        RoundedRectangle:
            pos: (self.x, self.y - dp(3)) if self.state == 'normal' else self.pos
            size: self.size
            radius: [dp(14)]
        Color:
            rgba: (app.theme_accent[0]*0.9, app.theme_accent[1]*0.9, app.theme_accent[2]*0.9, 1) if self.state == 'normal' else (app.theme_accent[0]*0.7, app.theme_accent[1]*0.7, app.theme_accent[2]*0.7, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]

<MenuBtnP2@PremiumBtn>:
    color: app.theme_p2_text
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.2
        RoundedRectangle:
            pos: (self.x, self.y - dp(3)) if self.state == 'normal' else self.pos
            size: self.size
            radius: [dp(14)]
        Color:
            rgba: (app.theme_p2_main[0], app.theme_p2_main[1], app.theme_p2_main[2], 1) if self.state == 'normal' else (app.theme_p2_dark[0], app.theme_p2_dark[1], app.theme_p2_dark[2], 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]

<MenuBtnDark@PremiumBtn>:
    color: app.theme_p1_light
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.2
        RoundedRectangle:
            pos: (self.x, self.y - dp(3)) if self.state == 'normal' else self.pos
            size: self.size
            radius: [dp(14)]
        Color:
            rgba: (0.15, 0.15, 0.15, 0.95) if self.state == 'normal' else (0.05, 0.05, 0.05, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]
        Color:
            rgba: 1, 1, 1, 0.05
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(14)]
            width: dp(1)
            cap: 'round'
            joint: 'round'

<PillBtn@AnimBtn>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    bold: True
    font_size: '13sp'
    canvas.before:
        PushMatrix:
        Scale:
            x: self.anim_scale
            y: self.anim_scale
            z: 1.0
            origin: self.center
        Color:
            rgba: (1, 1, 1, 0.1) if self.state == 'normal' else (1, 1, 1, 0.04)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height/2] 
    canvas.after:
        PopMatrix:

<HintPillBtn@PillBtn>:
    color: app.theme_accent
    canvas.before:
        PushMatrix:
        Scale:
            x: self.anim_scale
            y: self.anim_scale
            z: 1.0
            origin: self.center
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], 0.2 if self.state == 'normal' else 0.1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height/2] 
    canvas.after:
        PopMatrix:

<SettingRow@BoxLayout>:
    size_hint_y: None
    height: dp(60) 
    padding: [dp(20), 0, dp(15), 0]
    canvas.before:
        Color:
            rgba: 1, 1, 1, 0.06
        Line:
            points: [self.x + dp(20), self.y, self.right, self.y]
            width: dp(1)

<VolumeControls@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(130) 
    spacing: dp(8)
    padding: [dp(20), dp(15), dp(20), dp(10)]
    Label:
        text: "MUSIC VOLUME: " + str(int(music_slider.value)) + "%"
        font_size: '11sp'
        bold: True
        size_hint_y: None
        height: dp(20)
        color: app.theme_p1_light
        text_size: self.size
        halign: 'left'
    Slider:
        id: music_slider
        min: 0
        max: 100
        value: app.music_volume * 100
        on_value: app.set_music_volume(self.value)
        size_hint_y: None
        height: dp(30)
        value_track: True
        value_track_color: app.theme_p1_light
    Label:
        text: "SFX VOLUME: " + str(int(sfx_slider.value)) + "%"
        font_size: '11sp'
        bold: True
        size_hint_y: None
        height: dp(20)
        color: app.theme_p2_light
        text_size: self.size
        halign: 'left'
    Slider:
        id: sfx_slider
        min: 0
        max: 100
        value: app.sfx_volume * 100
        on_value: app.set_sfx_volume(self.value)
        size_hint_y: None
        height: dp(30)
        value_track: True
        value_track_color: app.theme_p2_light

<PlayerToggle>:
    size_hint: None, None
    width: dp(260) 
    height: dp(48)
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.5
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height/2]
        Color:
            rgba: 0, 0, 0, 0.4
        RoundedRectangle:
            pos: (self.x + (self.width / 2) * self.thumb_progress + dp(2), self.y - dp(2))
            size: (self.width / 2 - dp(4) if self.width > dp(8) else dp(1), self.height)
            radius: [self.height/2]
        Color:
            rgba: (app.theme_p1_main[0], app.theme_p1_main[1], app.theme_p1_main[2], 1) if app.human_player == 1 else (app.theme_p2_main[0], app.theme_p2_main[1], app.theme_p2_main[2], 1)
        RoundedRectangle:
            pos: (self.x + (self.width / 2) * self.thumb_progress + dp(4), self.y + dp(4))
            size: (self.width / 2 - dp(8) if self.width > dp(8) else dp(1), self.height - dp(8) if self.height > dp(8) else dp(1))
            radius: [self.height/2]
            
    Label:
        text: app.p1_name
        bold: True
        font_size: '13sp'
        pos: root.x, root.y
        size: root.width / 2, root.height
        color: app.theme_p1_text if app.human_player == 1 else (0.6,0.6,0.6,1)
    Label:
        text: app.p2_name
        bold: True
        font_size: '13sp'
        pos: root.center_x, root.y
        size: root.width / 2, root.height
        color: app.theme_p2_text if app.human_player == 2 else (0.6,0.6,0.6,1)

<RadarPing>:
    canvas.before:
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], self.ping_alpha
        Line:
            circle: [self.center_x, self.center_y, dp(30) * self.ping_scale]
            width: dp(2)
        Color:
            rgba: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], 1
        Ellipse:
            pos: self.center_x - dp(15), self.center_y - dp(15)
            size: dp(30), dp(30)

# --- MAIN MENU SCREEN ---
<StartScreen>:
    BackgroundLayer:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320) 
            height: self.minimum_height
            spacing: dp(25)
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
                    text: "GRANDMASTER EDITION"
                    font_size: '11sp'
                    bold: True
                    color: app.theme_accent[0], app.theme_accent[1], app.theme_accent[2], 0.8

            GlassPanel:
                padding: [dp(20), dp(20), dp(20), dp(20)]
                Label:
                    text: "MATCH STATS (VS AI)"
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
                            text: "EASY"
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
                            text: "MED"
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
                            text: "HARD"
                            font_size: '10sp'
                            bold: True
                            color: 0.6, 0.6, 0.6, 1
                        Label:
                            text: "[color=" + app.p1_hex + "]" + str(app.stat_wins_hard) + "W[/color] - [color=" + app.p2_hex + "]" + str(app.stat_loss_hard) + "L[/color]"
                            markup: True
                            font_size: '14sp'
                            bold: True

            GlassPanel:
                padding: [dp(20), dp(20), dp(20), dp(25)]
                spacing: dp(15)
                Label:
                    text: "STARTING PLAYER"
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
                    spacing: dp(15)
                    size_hint_y: None
                    height: self.minimum_height
                    padding: [0, dp(10), 0, 0]
                    
                    MenuBtnAccent:
                        text: "ONLINE PVP"
                        on_release: app.start_online_match()
                    MenuBtnP1:
                        text: "VS AI MENU"
                        on_release: app.switch_screen('aimenu_screen')
                    MenuBtnP2:
                        text: "LOCAL MULTIPLAYER"
                        on_release: app.start_game('local')
                        
                    BoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(54)
                        spacing: dp(15)
                        MenuBtnDark:
                            text: "SETTINGS"
                            on_release: app.switch_screen('settings_screen')
                        MenuBtnDark:
                            text: app.server_status_text
                            color: (0.4, 1, 0.4, 1) if app.server_online else ((1, 0.4, 0.4, 1) if app.server_status_text != "CHECK SERVER" else app.theme_p1_light)
                            on_release: app.ping_server()

# --- MATCHMAKING SCREEN ---
<MatchmakingScreen>:
    BackgroundLayer:
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
                opacity: 1 if app.matchmaking_status in ("SEARCHING FOR MATCH...", "CONNECTING...", "WAKING UP SERVER...") else 0

            Label:
                text: app.matchmaking_status
                font_size: '16sp'
                bold: True
                color: app.theme_accent if app.matchmaking_status in ("SEARCHING FOR MATCH...", "CONNECTING...", "WAKING UP SERVER...") else (1, 0.3, 0.3, 1)
                size_hint_y: None
                height: dp(30)
                halign: 'center'
                
            MenuBtnDark:
                text: "CANCEL" if app.matchmaking_status in ("SEARCHING FOR MATCH...", "CONNECTING...", "WAKING UP SERVER...") else "BACK TO MENU"
                on_release: app.cancel_matchmaking()

# --- VS AI MENU SCREEN ---
<AiMenuScreen>:
    BackgroundLayer:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320)
            height: self.minimum_height
            spacing: dp(35)
            Label:
                text: "VERSUS A.I."
                font_size: '26sp'
                bold: True
                size_hint_y: None
                height: dp(50)
            GlassPanel:
                padding: [dp(20), dp(30), dp(20), dp(30)]
                spacing: dp(20)
                MenuBtnAccent:
                    text: "BOSS RUSH CAMPAIGN"
                    on_release: app.switch_screen('campaign_screen')
                MenuBtnP1:
                    text: "QUICK MATCH"
                    on_release: app.switch_screen('difficulty_screen')
                Widget:
                    size_hint_y: None
                    height: dp(15)
                MenuBtnDark:
                    text: "BACK"
                    on_release: app.switch_screen('start_screen')

# --- DIFFICULTY SELECTION SCREEN ---
<DifficultyScreen>:
    BackgroundLayer:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320)
            height: self.minimum_height
            spacing: dp(35)
            Label:
                text: "QUICK MATCH"
                font_size: '26sp'
                bold: True
                size_hint_y: None
                height: dp(50)
            GlassPanel:
                padding: [dp(20), dp(30), dp(20), dp(30)]
                spacing: dp(20)
                MenuBtnP1:
                    text: "EASY"
                    on_release: app.start_ai_game('easy', 0)
                MenuBtnAccent:
                    text: "MEDIUM"
                    on_release: app.start_ai_game('medium', 0)
                MenuBtnP2:
                    text: "HARD"
                    on_release: app.start_ai_game('hard', 0)
                Widget:
                    size_hint_y: None
                    height: dp(15)
                MenuBtnDark:
                    text: "BACK"
                    on_release: app.switch_screen('aimenu_screen')

# --- BOSS RUSH CAMPAIGN SCREEN ---
<CampaignScreen>:
    BackgroundLayer:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, 1.0
            width: dp(340) 
            spacing: dp(15)
            padding: [0, dp(45), 0, dp(15)]
            
            Label:
                text: "CAMPAIGN"
                font_size: '26sp'
                bold: True
                size_hint_y: None
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
                    
                    GlassPanel:
                        padding: dp(20)
                        spacing: dp(10)
                        width: dp(330) 
                        Label:
                            text: "TIER I : THE ROOKIE"
                            font_size: '14sp'
                            bold: True
                            color: app.theme_p1_light
                            size_hint_y: None
                            height: dp(20)
                            halign: 'left'
                            text_size: self.size
                        Label:
                            text: "Standard Rules. Easy AI."
                            font_size: '11sp'
                            color: 0.6, 0.6, 0.6, 1
                            size_hint_y: None
                            height: dp(20)
                            halign: 'left'
                            text_size: self.size
                        MenuBtnP1:
                            text: "FIGHT"
                            height: dp(45)
                            on_release: app.start_campaign_boss(1)

                    GlassPanel:
                        padding: dp(20)
                        spacing: dp(10)
                        width: dp(330) 
                        Label:
                            text: "TIER II : THE TACTICIAN"
                            font_size: '14sp'
                            bold: True
                            color: app.theme_accent if app.campaign_progress >= 2 else [0.4,0.4,0.4,1]
                            size_hint_y: None
                            height: dp(20)
                            halign: 'left'
                            text_size: self.size
                        Label:
                            text: "Standard Rules. Medium AI." if app.campaign_progress >= 2 else "LOCKED"
                            font_size: '11sp'
                            color: 0.6, 0.6, 0.6, 1
                            size_hint_y: None
                            height: dp(20)
                            halign: 'left'
                            text_size: self.size
                        MenuBtnAccent:
                            text: "FIGHT"
                            height: dp(45)
                            disabled: app.campaign_progress < 2
                            on_release: app.start_campaign_boss(2)
                            
                    GlassPanel:
                        padding: dp(20)
                        spacing: dp(10)
                        width: dp(330) 
                        Label:
                            text: "TIER III : THE AWAKENED"
                            font_size: '14sp'
                            bold: True
                            color: app.theme_p2_light if app.campaign_progress >= 3 else [0.4,0.4,0.4,1]
                            size_hint_y: None
                            height: dp(20)
                            halign: 'left'
                            text_size: self.size
                        Label:
                            text: "Hard AI. Starts with 2 Kings on Board." if app.campaign_progress >= 3 else "LOCKED"
                            font_size: '11sp'
                            color: 0.6, 0.6, 0.6, 1
                            size_hint_y: None
                            height: dp(20)
                            halign: 'left'
                            text_size: self.size
                        MenuBtnP2:
                            text: "FIGHT"
                            height: dp(45)
                            disabled: app.campaign_progress < 3
                            on_release: app.start_campaign_boss(3)
                            
                    GlassPanel:
                        padding: dp(20)
                        spacing: dp(10)
                        width: dp(330) 
                        Label:
                            text: "TIER IV : THE OVERLORD"
                            font_size: '14sp'
                            bold: True
                            color: [1, 0.3, 0.3, 1] if app.campaign_progress >= 4 else [0.4,0.4,0.4,1]
                            size_hint_y: None
                            height: dp(20)
                            halign: 'left'
                            text_size: self.size
                        Label:
                            text: "Grandmaster AI. Starts with 4 Kings." if app.campaign_progress >= 4 else "LOCKED"
                            font_size: '11sp'
                            color: 0.6, 0.6, 0.6, 1
                            size_hint_y: None
                            height: dp(20)
                            halign: 'left'
                            text_size: self.size
                        MenuBtnDark:
                            text: "FINAL FIGHT"
                            height: dp(45)
                            color: [1, 0.5, 0.5, 1]
                            disabled: app.campaign_progress < 4
                            on_release: app.start_campaign_boss(4)

                    Widget:
                        size_hint_y: None
                        height: dp(10)
                    MenuBtnDark:
                        text: "BACK TO MENU"
                        on_release: app.switch_screen('aimenu_screen')

# --- SECTIONED SETTINGS SCREEN ---
<SettingsScreen>:
    BackgroundLayer:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, 1.0
            width: dp(340) 
            spacing: dp(15)
            padding: [0, dp(45), 0, dp(15)]
            
            Label:
                text: "SETTINGS"
                font_size: '26sp'
                bold: True
                size_hint_y: None
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
                    spacing: dp(25)
                    padding: [dp(5), dp(10), dp(5), dp(30)]
                    
                    Label:
                        text: "THEMES & VISUALS"
                        font_size: '12sp'
                        bold: True
                        color: app.theme_accent
                        size_hint_y: None
                        height: dp(20)
                        text_size: self.size
                        halign: 'left'
                        valign: 'bottom'

                    GlassPanel:
                        padding: 0
                        spacing: 0
                        width: dp(330) 
                        SettingRow:
                            Label:
                                text: "Theme"
                                text_size: self.size
                                halign: 'left'
                                valign: 'middle'
                                bold: True
                                font_size: '14sp'
                            MenuBtnDark:
                                text: app.settings_theme
                                size_hint_x: None
                                width: dp(110)
                                height: dp(40)
                                pos_hint: {'center_y': 0.5}
                                on_release: app.cycle_theme()

                        SettingRow:
                            Label:
                                text: "Board Style"
                                text_size: self.size
                                halign: 'left'
                                valign: 'middle'
                                bold: True
                                font_size: '14sp'
                            MenuBtnDark:
                                text: app.settings_board
                                size_hint_x: None
                                width: dp(110)
                                height: dp(40)
                                pos_hint: {'center_y': 0.5}
                                on_release: app.cycle_board()

                        SettingRow:
                            canvas.before:
                                Color:
                                    rgba: 0,0,0,0
                                Line:
                                    points: [0,0,0,0]
                            Label:
                                text: "Visual Quality"
                                text_size: self.size
                                halign: 'left'
                                valign: 'middle'
                                bold: True
                                font_size: '14sp'
                            MenuBtnDark:
                                text: app.settings_visuals
                                size_hint_x: None
                                width: dp(110)
                                height: dp(40)
                                pos_hint: {'center_y': 0.5}
                                on_release: app.cycle_visuals()

                    Label:
                        text: "GAMEPLAY RULES"
                        font_size: '12sp'
                        bold: True
                        color: app.theme_p1_light
                        size_hint_y: None
                        height: dp(20)
                        text_size: self.size
                        halign: 'left'
                        valign: 'bottom'

                    GlassPanel:
                        padding: 0
                        spacing: 0
                        width: dp(330)
                        SettingRow:
                            Label:
                                text: "Blitz Timer"
                                text_size: self.size
                                halign: 'left'
                                valign: 'middle'
                                bold: True
                                font_size: '14sp'
                            MenuBtnDark:
                                text: app.settings_blitz
                                size_hint_x: None
                                width: dp(110)
                                height: dp(40)
                                pos_hint: {'center_y': 0.5}
                                on_release: app.cycle_blitz()

                        SettingRow:
                            canvas.before:
                                Color:
                                    rgba: 0,0,0,0
                                Line:
                                    points: [0,0,0,0]
                            Label:
                                text: "Show Undo Button"
                                text_size: self.size
                                halign: 'left'
                                valign: 'middle'
                                bold: True
                                font_size: '14sp'
                            Switch:
                                active: app.settings_undo
                                on_active: app.toggle_setting('undo', self.active)
                                
                        SettingRow:
                            canvas.before:
                                Color:
                                    rgba: 0,0,0,0
                                Line:
                                    points: [0,0,0,0]
                            Label:
                                text: "Show Hint Button"
                                text_size: self.size
                                halign: 'left'
                                valign: 'middle'
                                bold: True
                                font_size: '14sp'
                            Switch:
                                active: app.settings_hint
                                on_active: app.toggle_setting('hint', self.active)
                        
                        SettingRow:
                            canvas.before:
                                Color:
                                    rgba: 0,0,0,0
                                Line:
                                    points: [0,0,0,0]
                            Label:
                                text: "Mandatory Jumps"
                                text_size: self.size
                                halign: 'left'
                                valign: 'middle'
                                bold: True
                                font_size: '14sp'
                            Switch:
                                active: app.settings_mandatory_jump
                                on_active: app.toggle_setting('mandatory_jump', self.active)

                    Label:
                        text: "AUDIO & PERFORMANCE"
                        font_size: '12sp'
                        bold: True
                        color: app.theme_p2_light
                        size_hint_y: None
                        height: dp(20)
                        text_size: self.size
                        halign: 'left'
                        valign: 'bottom'

                    GlassPanel:
                        padding: 0
                        spacing: 0
                        width: dp(330)

                        SettingRow:
                            Label:
                                text: "FPS Target"
                                text_size: self.size
                                halign: 'left'
                                valign: 'middle'
                                bold: True
                                font_size: '14sp'
                            MenuBtnDark:
                                text: str(app.settings_fps) + " FPS"
                                size_hint_x: None
                                width: dp(110)
                                height: dp(40)
                                pos_hint: {'center_y': 0.5}
                                on_release: app.cycle_fps()

                        VolumeControls:
                        
                    MenuBtnDark:
                        text: "BACK TO MENU"
                        on_release: app.switch_screen('start_screen')

# --- PAUSE SCREEN ---
<PauseScreen>:
    BackgroundLayer:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320)
            height: self.minimum_height
            spacing: dp(35)
            Label:
                text: "PAUSED"
                font_size: '34sp'
                bold: True
                size_hint_y: None
                height: dp(50)
            GlassPanel:
                padding: [dp(20), dp(30), dp(20), dp(30)]
                spacing: dp(20)
                MenuBtnP1:
                    text: "RESUME GAME"
                    on_release: app.resume_game()
                MenuBtnAccent:
                    text: "RESTART MATCH"
                    opacity: 1 if app.game_mode != 'online' else 0
                    disabled: app.game_mode == 'online'
                    on_release: app.start_game(app.game_mode, app.current_boss_level)
                MenuBtnDark:
                    text: "SURRENDER MATCH"
                    color: [1, 0.3, 0.3, 1]
                    on_release: app.surrender_match()
                Widget:
                    size_hint_y: None
                    height: dp(15)
                MenuBtnDark:
                    text: "QUIT TO MENU"
                    on_release: app.quit_to_menu()

# --- GAME OVER SCREEN ---
<GameOverScreen>:
    BackgroundLayer:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            width: dp(320)
            height: self.minimum_height
            spacing: dp(35)
            Label:
                text: "MATCH OVER"
                font_size: '34sp'
                bold: True
                size_hint_y: None
                height: dp(50)
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
                    text: "PLAY AGAIN" if app.game_mode != 'online' else "REQUEST REMATCH"
                    opacity: 1 if not app.opponent_left else 0.5
                    disabled: app.opponent_left
                    on_release: 
                        if app.game_mode == 'online': app.network.request_rematch(); self.text = "WAITING..."
                        else: app.start_game(app.game_mode, app.current_boss_level)
                MenuBtnDark:
                    text: "MAIN MENU"
                    on_release: app.quit_to_menu()

# --- GAME SCREEN ---
<GameScreen>:
    BackgroundLayer:
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
                        rgba: (1, 0.2, 0.2, 1) if (app.current_time_left / (app.max_time if app.max_time > 0 else 0.001)) < 0.3 else ((1, 0.8, 0.2, 1) if (app.current_time_left / (app.max_time if app.max_time > 0 else 0.001)) < 0.6 else app.theme_accent)
                    RoundedRectangle:
                        pos: self.pos
                        size: (self.width * (app.current_time_left / (app.max_time if app.max_time > 0 else 0.001)) if self.width > dp(1) else dp(1), self.height)
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
                        size: (self.width + dp(8) if self.width > dp(1) else dp(1), self.height + dp(8) if self.height > dp(1) else dp(1))
                        radius: [dp(34)]
                    Color:
                        rgba: 0, 0, 0, 0.45
                    RoundedRectangle:
                        pos: (self.x, self.y - dp(6))
                        size: self.size
                        radius: [dp(32.5)]
                    Color:
                        rgba: app.theme_panel[0], app.theme_panel[1], app.theme_panel[2], 0.95
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(32.5)]
                    Color:
                        rgba: 1, 1, 1, 0.15
                    Line:
                        rounded_rectangle: [self.x, self.y, self.width, self.height, dp(32.5)]
                        width: dp(1)
                
                PillBtn:
                    text: "UNDO"
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
                                rgba: ((app.theme_p1_light[0], app.theme_p1_light[1], app.theme_p1_light[2], 1) if app.current_turn == 1 else (app.theme_p2_light[0], app.theme_p2_light[1], app.theme_p2_light[2], 1)) if not app.is_thinking else (0,0,0,0)
                            Ellipse:
                                pos: (self.center_x - dp(4), self.center_y - dp(4))
                                size: (dp(8), dp(8))
                    Label:
                        id: turn_indicator
                        text: "Waiting for Opponent's Turn..." if (app.game_mode == 'online' and app.current_turn != app.online_player_id) else ("AI Thinking..." if app.is_thinking else (f"{app.p1_name}'s Turn" if app.current_turn == 1 else f"{app.p2_name}'s Turn"))
                        color: (0.6, 0.6, 0.6, 1) if app.is_thinking else ((app.theme_p1_light[0], app.theme_p1_light[1], app.theme_p1_light[2], 1) if app.current_turn == 1 else (app.theme_p2_light[0], app.theme_p2_light[1], app.theme_p2_light[2], 1))
                        font_size: '13sp'
                        bold: True
                        text_size: self.size
                        halign: 'left'
                        valign: 'middle'
                
                HintPillBtn:
                    text: "HINT"
                    size_hint_x: None
                    width: dp(60)
                    opacity: 1 if (app.settings_hint and app.game_mode not in ('campaign', 'online')) else 0
                    disabled: app.is_thinking or (not app.settings_hint) or app.game_mode in ('campaign', 'online')
                    on_release: app.trigger_hint()

                PillBtn:
                    text: "MENU"
                    size_hint_x: None
                    width: dp(65)
                    on_release: app.switch_screen('pause_screen')
'''

class StartScreen(Screen): pass
class MatchmakingScreen(Screen): pass
class AiMenuScreen(Screen): pass
class CampaignScreen(Screen): pass
class DifficultyScreen(Screen): pass
class SettingsScreen(Screen): pass
class PauseScreen(Screen): pass
class GameOverScreen(Screen): pass
class GameScreen(Screen): pass

# ==============================================================================
# 6. HIGH-PERFORMANCE GRAPHICS ENGINE 
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

    def on_is_selected(self, instance, value):
        app = App.get_running_app()
        Animation.cancel_all(self, 'highlight_scale', 'highlight_alpha')
        if value:
            if app.settings_visuals == 'HIGH':
                self.highlight_scale = 1.0
                self.highlight_alpha = 0.8
                self.pulse_anim = Animation(highlight_scale=1.15, highlight_alpha=0.2, duration=0.4, transition='in_out_sine')
                self.pulse_anim += Animation(highlight_scale=1.0, highlight_alpha=0.8, duration=0.4, transition='in_out_sine')
                self.pulse_anim.repeat = True
                self.pulse_anim.start(self)
            else:
                self.highlight_scale = 1.15
                self.highlight_alpha = 0.8
        else:
            self.highlight_scale = 1.0
            self.highlight_alpha = 0.0

class HintTargetWidget(Widget):
    anim_alpha = NumericProperty(0.0)

    def start_anim(self):
        self.anim_alpha = 0.2
        anim = Animation(anim_alpha=0.6, duration=0.6, transition='in_out_sine')
        anim += Animation(anim_alpha=0.2, duration=0.6, transition='in_out_sine')
        anim.repeat = True
        anim.start(self)

class BoardWidget(Widget):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.selected_piece_coords = None
        self.piece_widgets = [] 
        self.hint_targets = []
        self.offset_x = 0
        self.offset_y = 0
        self.sq_size = 0
        self.size_hint = (None, None) 
        self.is_animating = False
        
        self.bind(pos=self.trigger_redraw, size=self.trigger_redraw)
        self.app.bind(settings_board=self.trigger_redraw)

    def trigger_redraw(self, *args):
        Clock.unschedule(self.calculate_board_size)
        Clock.schedule_once(self.calculate_board_size, 0)

    def calculate_board_size(self, *args):
        if not self.parent: return
        board_dim = min(self.parent.width, self.parent.height) * 0.98
        if board_dim <= 0: return
        self.size = (board_dim, board_dim)
        self.offset_x = self.parent.x + (self.parent.width - board_dim) / 2.0
        self.offset_y = self.parent.y + (self.parent.height - board_dim) / 2.0
        self.sq_size = board_dim / COLS
        
        self.render_board_background()
        self.render_pieces()

    def render_board_background(self):
        self.canvas.before.clear()
        style_name = self.app.settings_board
        style_colors = BOARD_STYLES.get(style_name, BOARD_STYLES['CLASSIC'])
        img_path = f'board_{style_name.lower()}.jpg'
        has_image = os.path.isfile(img_path)

        with self.canvas.before:
            Color(0, 0, 0, 0.35)
            RoundedRectangle(pos=(self.offset_x - dp(10), self.offset_y - dp(15)),
                             size=(self.size[0] + dp(20) if self.size[0] > dp(1) else dp(1), self.size[1] + dp(25) if self.size[1] > dp(1) else dp(1)), radius=[dp(12)])
            Color(*style_colors['border'])
            RoundedRectangle(pos=(self.offset_x - dp(6), self.offset_y - dp(6)),
                             size=(self.size[0] + dp(12) if self.size[0] > dp(1) else dp(1), self.size[1] + dp(12) if self.size[1] > dp(1) else dp(1)), radius=[dp(10)])
            
            if has_image:
                Color(1, 1, 1, 1)
                Rectangle(pos=(self.offset_x, self.offset_y), size=(self.size[0] if self.size[0] > dp(1) else dp(1), self.size[1] if self.size[1] > dp(1) else dp(1)), source=img_path)
            else:
                for r in range(ROWS):
                    for c in range(COLS):
                        is_dark = (r + c) % 2 != 0
                        if is_dark:
                            Color(*style_colors['dark'])
                        else:
                            Color(*style_colors['light'])
                        
                        sq_x = self.offset_x + c * self.sq_size
                        sq_y = self.offset_y + (7 - r) * self.sq_size
                        Rectangle(pos=(sq_x, sq_y), size=(self.sq_size if self.sq_size > dp(1) else dp(1), self.sq_size if self.sq_size > dp(1) else dp(1)))

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
                        if abs(val) == 1: p1_count += 1
                        else: p2_count += 1
                        
        self.app.p1_pieces = p1_count
        self.app.p2_pieces = p2_count
                        
        while len(self.piece_widgets) < len(piece_data):
            pw = PieceWidget()
            self.piece_widgets.append(pw)
            self.add_widget(pw)
            
        for i in range(len(piece_data), len(self.piece_widgets)):
            pw = self.piece_widgets[i]
            pw.opacity = 0
            pw.pos = (-1000, -1000) 
            pw.is_selected = False
            Animation.cancel_all(pw, 'pos', 'opacity')

        for i, data in enumerate(piece_data):
            ptype, r, c = data
            pw = self.piece_widgets[i]
            pw.piece_type = ptype
            pw.row = r
            pw.col = c
            pw.opacity = 1
            pw.piece_scale = 1.0  
            pw.size = (self.sq_size * 0.8, self.sq_size * 0.8)
            margin = self.sq_size * 0.1
            pw.pos = (self.offset_x + c * self.sq_size + margin, self.offset_y + (7 - r) * self.sq_size + margin)
            
            Animation.cancel_all(pw, 'highlight_scale', 'highlight_alpha')
            pw.highlight_scale = 1.0
            pw.highlight_alpha = 0.0
            pw.is_selected = (self.selected_piece_coords == (r, c))
                    
        if hasattr(self.app, 'newly_promoted') and self.app.newly_promoted:
            nr, nc = self.app.newly_promoted
            promoted_piece = next((p for p in self.piece_widgets if p.opacity == 1 and p.row == nr and p.col == nc), None)
            if promoted_piece:
                promoted_piece.piece_scale = 1.6
                anim = Animation(piece_scale=1.0, duration=0.4, transition='out_bounce')
                anim.start(promoted_piece)
            self.app.newly_promoted = None

    def pulse_hint_piece(self, move_obj):
        self.clear_all_hints() 
        sr, sc = move_obj['start']
        er, ec = move_obj['end']
        
        piece = next((p for p in self.piece_widgets if p.opacity == 1 and p.row == sr and p.col == sc), None)
        if piece and not piece.is_selected:
            Animation.cancel_all(piece, 'highlight_scale', 'highlight_alpha')
            piece.highlight_scale = 1.0
            piece.highlight_alpha = 0.0
            if self.app.settings_visuals == 'HIGH':
                anim = Animation(highlight_scale=1.15, highlight_alpha=0.6, duration=0.6, transition='in_out_sine')
                anim += Animation(highlight_scale=1.05, highlight_alpha=0.1, duration=0.6, transition='in_out_sine')
                anim.repeat = True
                anim.start(piece)
            else:
                piece.highlight_scale = 1.15
                piece.highlight_alpha = 0.8
                
        target_pad = HintTargetWidget()
        target_pad.size = (self.sq_size, self.sq_size)
        target_pad.pos = (self.offset_x + ec * self.sq_size, self.offset_y + (7 - er) * self.sq_size)
        self.add_widget(target_pad)
        self.hint_targets.append(target_pad)
        if self.app.settings_visuals == 'HIGH': target_pad.start_anim()
        else: target_pad.anim_alpha = 0.5

    def on_touch_down(self, touch):
        if self.is_animating: return True 
        
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
        if row < 0 or row > 7 or col < 0 or col > 7: return False

        piece_type = self.app.board_state[row][col]
        must_jump = False if self.app.game_mode == 'campaign' else self.app.settings_mandatory_jump
        
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
            return True

        if self.selected_piece_coords:
            sr, sc = self.selected_piece_coords
            must_jump = False if self.app.game_mode == 'campaign' else self.app.settings_mandatory_jump
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

    def execute_move(self, move_obj):
        self.is_animating = True
        self.app.stop_timer()

        if self.app.game_mode == 'local' or self.app.current_turn == self.app.human_player:
            self.app.undo_stack.append({
                'board': [row[:] for row in self.app.board_state],
                'turn': self.app.current_turn
            })

        sr, sc = move_obj['start']
        er, ec = move_obj['end']
        piece = next((p for p in self.piece_widgets if p.opacity == 1 and p.row == sr and p.col == sc), None)
        
        if piece:
            piece.is_selected = False 
            self.remove_widget(piece)
            self.add_widget(piece) 
            
            margin = self.sq_size * 0.1
            target_x = self.offset_x + ec * self.sq_size + margin
            target_y = self.offset_y + (7 - er) * self.sq_size + margin
            
            anim = Animation(pos=(target_x, target_y), duration=0.2, transition='out_cubic')
            anim.bind(on_complete=lambda *args: self.handle_capture(move_obj))
            anim.start(piece)

    def handle_capture(self, move_obj):
        if move_obj['info']['type'] == 'jump':
            jr = move_obj['info']['jumped_r']
            jc = move_obj['info']['jumped_c']
            captured_piece = next((p for p in self.piece_widgets if p.opacity == 1 and p.row == jr and p.col == jc), None)
            
            if captured_piece:
                self.app.trigger_haptic(0.08) 
                shrink_size = (captured_piece.width * 0.2, captured_piece.height * 0.2)
                new_x = captured_piece.center_x - shrink_size[0] / 2
                new_y = captured_piece.center_y - shrink_size[1] / 2
                
                cap_anim = Animation(opacity=0, size=shrink_size, pos=(new_x, new_y), duration=0.1, transition='out_quad')
                cap_anim.bind(on_complete=lambda *args: self.finalize_move(move_obj))
                cap_anim.start(captured_piece)
                return
        self.finalize_move(move_obj)

    def finalize_move(self, move_obj):
        er, ec = move_obj['end']
        piece_type = self.app.board_state[move_obj['start'][0]][move_obj['start'][1]]
        
        if piece_type > 0:
            if (self.app.current_turn == BLUE and er == ROWS - 1) or (self.app.current_turn == RED and er == 0):
                self.app.newly_promoted = (er, ec)
                self.app.trigger_haptic(0.1) 
        
        GameEngine.apply_temp_move(self.app.board_state, move_obj, self.app.current_turn)
        self.app.current_turn = RED if self.app.current_turn == BLUE else BLUE
        self.render_pieces()
        self.is_animating = False

        if self.app.screen_manager.current not in ('game_screen', 'pause_screen'):
            return

        must_jump = False if self.app.game_mode == 'campaign' else self.app.settings_mandatory_jump
        if not GameEngine.get_valid_moves(self.app.current_turn, self.app.board_state, must_jump):
            self.app.trigger_game_over()
            return

        self.app.start_timer()

        if self.app.game_mode in ('computer', 'campaign') and self.app.current_turn != self.app.human_player:
            self.app.trigger_ai_turn()


# ==============================================================================
# 7. CORE APPLICATION 
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

    settings_undo = BooleanProperty(True)
    settings_hint = BooleanProperty(True)
    settings_mandatory_jump = BooleanProperty(True)
    settings_fps = NumericProperty(60)
    settings_visuals = StringProperty('HIGH')
    settings_blitz = StringProperty('OFF')
    
    settings_theme = StringProperty('ROYAL')
    settings_board = StringProperty('CLASSIC')
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
        
        self.store = JsonStore('checkers_data.json')
        self.undo_stack = []
        
        self.load_settings()
        self.apply_theme()
        self.load_stats()
            
        Builder.load_string(KV)
        
        self.board_state = GameEngine.get_initial_board() 
        
        self.screen_manager = ScreenManager(transition=FadeTransition(duration=0.2))
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
        game_screen.ids.board_anchor.add_widget(self.board_widget)
        self.screen_manager.add_widget(game_screen)
        
        self.audio_queue = ['click1', 'click2', 'click3', 'click4', 'click5', 'win', 'lose', 'music']
        Clock.schedule_interval(self._load_next_audio, 0.1)

        return self.screen_manager

    def on_pause(self):
        return True

    def on_resume(self):
        pass

    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        if key == 27:
            if self.screen_manager.current == 'game_screen':
                self.switch_screen('pause_screen')
            elif self.screen_manager.current in ['difficulty_screen', 'settings_screen', 'pause_screen', 'aimenu_screen', 'campaign_screen', 'matchmaking_screen']:
                self.cancel_matchmaking()
            return True  
        return False

    def trigger_haptic(self, duration=0.03):
        if vibrator:
            try:
                vibrator.vibrate(time=duration)
            except Exception:
                pass

    def ping_server(self):
        self.server_status_text = "PINGING..."
        if not websocket:
            self._set_server_status(False, "NO LIB")
            return

        def check_conn():
            try:
                ws = websocket.create_connection(WEBSOCKET_URL, timeout=3)
                ws.close()
                Clock.schedule_once(lambda dt: self._set_server_status(True, "ONLINE"))
            except Exception:
                Clock.schedule_once(lambda dt: self._set_server_status(False, "OFFLINE"))

        threading.Thread(target=check_conn, daemon=True).start()

    def _set_server_status(self, is_online, text):
        self.server_online = is_online
        self.server_status_text = text

    def load_settings(self):
        if self.store.exists('campaign'):
            self.campaign_progress = self.store.get('campaign').get('progress', 1)
        if self.store.exists('settings'):
            s = self.store.get('settings')
            self.settings_undo = s.get('undo', True)
            self.settings_hint = s.get('hint', True)
            self.settings_mandatory_jump = s.get('mandatory_jump', True)
            self.settings_fps = s.get('fps', 60)
            self.settings_visuals = s.get('visuals', 'HIGH')
            self.settings_blitz = s.get('blitz', 'OFF')
            saved_board = s.get('board', 'CLASSIC')
            if saved_board not in BOARD_STYLES: self.settings_board = 'CLASSIC'
            else: self.settings_board = saved_board
            saved_theme = s.get('theme', 'ROYAL')
            if saved_theme not in THEMES: self.settings_theme = 'ROYAL'
            else: self.settings_theme = saved_theme
            Config.set('graphics', 'maxfps', str(self.settings_fps))

    def save_settings(self):
        self.store.put('settings', 
                       undo=self.settings_undo, 
                       hint=self.settings_hint,
                       mandatory_jump=self.settings_mandatory_jump, 
                       fps=self.settings_fps, 
                       visuals=self.settings_visuals,
                       theme=self.settings_theme,
                       board=self.settings_board,
                       blitz=self.settings_blitz)

    def toggle_setting(self, key, value):
        if key == 'undo': self.settings_undo = value
        elif key == 'hint': self.settings_hint = value
        elif key == 'mandatory_jump': self.settings_mandatory_jump = value
        self.save_settings()

    def cycle_fps(self):
        opts = [30, 60, 120]
        idx = opts.index(self.settings_fps) if self.settings_fps in opts else 1
        self.settings_fps = opts[(idx + 1) % len(opts)]
        Config.set('graphics', 'maxfps', str(self.settings_fps))
        self.save_settings()

    def cycle_blitz(self):
        opts = ['OFF', '3 SEC', '5 SEC', '8 SEC']
        idx = opts.index(self.settings_blitz) if self.settings_blitz in opts else 0
        self.settings_blitz = opts[(idx + 1) % len(opts)]
        self.save_settings()

    def cycle_visuals(self):
        opts = ['HIGH', 'LOW']
        idx = opts.index(self.settings_visuals) if self.settings_visuals in opts else 0
        self.settings_visuals = opts[(idx + 1) % len(opts)]
        if hasattr(self, 'board_widget'):
            self.board_widget.clear_all_hints()
            self.board_widget.render_pieces()
        self.save_settings()

    def rgb_to_hex(self, rgb):
        return "#{:02x}{:02x}{:02x}".format(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))

    def cycle_theme(self):
        opts = list(THEMES.keys())
        idx = opts.index(self.settings_theme) if self.settings_theme in opts else 0
        self.settings_theme = opts[(idx + 1) % len(opts)]
        self.apply_theme()
        self.save_settings()

    def cycle_board(self):
        opts = list(BOARD_STYLES.keys())
        idx = opts.index(self.settings_board) if self.settings_board in opts else 0
        self.settings_board = opts[(idx + 1) % len(opts)]
        self.save_settings()

    def apply_theme(self):
        theme = THEMES[self.settings_theme]
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
        if self.game_mode == 'online':
            self.p1_display_name = f"{self.p1_name} (YOU)" if self.online_player_id == 1 else f"{self.p1_name} (OPP)"
            self.p2_display_name = f"{self.p2_name} (YOU)" if self.online_player_id == 2 else f"{self.p2_name} (OPP)"
        elif self.game_mode == 'campaign':
            self.p1_display_name = f"{self.p1_name} (YOU)"
            self.p2_display_name = self.boss_name
        elif self.game_mode == 'computer':
            self.p1_display_name = f"{self.p1_name} (YOU)" if self.human_player == 1 else self.p1_name
            self.p2_display_name = f"{self.p2_name} (YOU)" if self.human_player == 2 else f"AI ({self.ai_mode.upper()})"
        else:
            self.p1_display_name = self.p1_name
            self.p2_display_name = self.p2_name

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
            if is_win: self.stat_wins_easy += 1
            else: self.stat_loss_easy += 1
        elif diff == 'medium':
            if is_win: self.stat_wins_medium += 1
            else: self.stat_loss_medium += 1
        elif diff == 'hard':
            if is_win: self.stat_wins_hard += 1
            else: self.stat_loss_hard += 1
        self.store.put('stats', 
            easy_w=self.stat_wins_easy, easy_l=self.stat_loss_easy,
            medium_w=self.stat_wins_medium, medium_l=self.stat_loss_medium,
            hard_w=self.stat_wins_hard, hard_l=self.stat_loss_hard
        )

    def start_timer(self):
        self.stop_timer()
        if self.settings_blitz == 'OFF': return
        if self.game_mode in ('computer', 'campaign') and self.current_turn != self.human_player: return
        if self.game_mode == 'online' and self.current_turn != self.online_player_id: return
        
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
        if self.screen_manager.current != 'game_screen': return
        if self.board_widget.is_animating: return
        self.board_widget.clear_all_hints()
        self.board_widget.selected_piece_coords = None
        must_jump = False if self.game_mode == 'campaign' else self.settings_mandatory_jump
        moves = GameEngine.get_valid_moves(self.current_turn, self.board_state, must_jump)
        if moves:
            self.play_click_sound()
            chosen = random.choice(moves)
            if self.game_mode == 'online':
                self.network.send_move(chosen['start'], chosen['end'])
            self.board_widget.execute_move(chosen)

    def trigger_undo(self):
        if not self.settings_undo or not self.undo_stack or self.game_mode in ('campaign', 'online'): return
        if self.is_thinking or self.board_widget.is_animating: return 
        last_state = self.undo_stack.pop()
        self.board_state = last_state['board']
        self.current_turn = last_state['turn']
        self.board_widget.selected_piece_coords = None
        self.board_widget.clear_all_hints()
        self.board_widget.render_pieces()
        self.board_widget.trigger_redraw()
        self.start_timer()

    def trigger_hint(self):
        if self.is_thinking or self.board_widget.is_animating: return
        if self.game_mode in ('campaign', 'online') or not self.settings_hint: return
        if self.game_mode == 'computer' and self.current_turn != self.human_player: return
        must_jump = False if self.game_mode == 'campaign' else self.settings_mandatory_jump
        possible_moves = GameEngine.get_valid_moves(self.current_turn, self.board_state, must_jump)
        if not possible_moves: return
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
        if self.screen_manager.current == 'game_over_screen':
            return
            
        self.opponent_left = disconnect
        winner_code = RED if self.current_turn == BLUE else BLUE
        winner_name = self.p2_name if winner_code == RED else self.p1_name
        winner_color = self.theme_p2_light if winner_code == RED else self.theme_p1_light
        winner_score = self.p2_pieces if winner_code == RED else self.p1_pieces
        
        if self.game_mode == 'campaign' and winner_code != self.human_player:
            winner_name = self.boss_name
        elif self.game_mode == 'online':
            if disconnect:
                winner_name = self.p1_name if self.online_player_id == 1 else self.p2_name
                winner_color = self.theme_p1_light if self.online_player_id == 1 else self.theme_p2_light
            elif winner_code != self.online_player_id:
                winner_name = "ONLINE OPPONENT"
        
        opponent_pieces = sum(1 for r in range(ROWS) for c in range(COLS) if self.board_state[r][c] != EMPTY and abs(self.board_state[r][c]) == self.current_turn)
        
        if self.game_mode == 'computer':
            is_win = (winner_code == self.human_player)
            self.record_match_result(self.ai_mode, is_win)
        elif self.game_mode == 'campaign':
            if winner_code == self.human_player:
                self.campaign_progress = max(self.campaign_progress, self.current_boss_level + 1)
                self.store.put('campaign', progress=self.campaign_progress)

        try:
            if self.sound_lose and self.game_mode in ('computer', 'campaign', 'online') and winner_code not in (self.human_player, getattr(self, 'online_player_id', -1)):
                self.sound_lose.play()
            elif self.sound_win:
                self.sound_win.play()
        except Exception:
            pass 

        gs = self.screen_manager.get_screen('game_screen')
        gs.ids.turn_indicator.text = "CHECKMATE!" if opponent_pieces > 0 else "GAME OVER!"
        gs.ids.turn_indicator.color = (1, 0.843, 0, 1) 
        
        go_screen = self.screen_manager.get_screen('game_over_screen')
        if disconnect:
            go_screen.ids.winner_label.text = f"YOU WIN!\n[size=14sp](OPPONENT DISCONNECTED)[/size]"
            go_screen.ids.winner_label.color = self.theme_accent
        else:
            if opponent_pieces > 0:
                go_screen.ids.winner_label.text = f"{winner_name} WINS BY CHECKMATE!\n[size=14sp]({winner_score} Pieces Remaining)[/size]"
            else:
                go_screen.ids.winner_label.text = f"{winner_name} WINS!\n[size=14sp]({winner_score} Pieces Remaining)[/size]"
            go_screen.ids.winner_label.color = [winner_color[0], winner_color[1], winner_color[2], 1]
        
        Clock.schedule_once(lambda dt: self.switch_screen('game_over_screen'), 0.5)

    def _load_next_audio(self, dt):
        if not self.audio_queue:
            if self.music_bg and self.music_volume > 0:
                self.music_bg.play()
            return False 
        item = self.audio_queue.pop(0)
        try:
            if 'click' in item:
                s = SoundLoader.load('click.wav')
                if s: self.click_pool.append(s)
            elif item == 'win':
                self.sound_win = SoundLoader.load('win.wav')
            elif item == 'lose':
                self.sound_lose = SoundLoader.load('tieorlose.wav')
            elif item == 'music':
                self.music_bg = SoundLoader.load('music.ogg')
                if self.music_bg:
                    self.music_bg.loop = True
                    self.music_bg.volume = self.music_volume
        except Exception:
            pass

    def set_music_volume(self, val):
        self.music_volume = val / 100.0
        try:
            if self.music_bg: self.music_bg.volume = self.music_volume
        except Exception: pass

    def set_sfx_volume(self, val):
        self.sfx_volume = val / 100.0
        try:
            for s in self.click_pool: s.volume = self.sfx_volume
            if self.sound_win: self.sound_win.volume = self.sfx_volume
            if self.sound_lose: self.sound_lose.volume = self.sfx_volume
        except Exception: pass

    def play_click_sound(self):
        if len(self.click_pool) > 0:
            try:
                sound = self.click_pool[self.click_index]
                if sound.state == 'play': sound.stop()
                sound.play()
                self.click_index = (self.click_index + 1) % len(self.click_pool)
            except Exception: pass 

    def quit_to_menu(self):
        self.match_id += 1  
        self.stop_timer()
        if self.game_mode == 'online':
            self.network.disconnect()
        self.switch_screen('start_screen')

    def switch_screen(self, screen_name):
        if hasattr(self, 'board_widget'):
            self.board_widget.clear_all_hints()
        if screen_name == 'pause_screen':
            self.stop_timer()
        self.screen_manager.current = screen_name

    def show_error(self, message):
        self.matchmaking_status = message
        self.network.disconnect()

    # --- NETWORK INTEGRATION LAYER ---
    def start_online_match(self):
        self.game_mode = 'online'
        self.network.connect()

    def cancel_matchmaking(self):
        self.network.disconnect()
        self.switch_screen('start_screen')

    def handle_network_data(self, data):
        if not data or 'action' not in data: return
        t = data['action']

        if t == 'match_start':
            self.online_player_id = int(data.get('color', BLUE))
            self.start_game('online')
            
        elif t == 'state_update':
            sr, sc = data['start']
            er, ec = data['end']
            must_jump = self.settings_mandatory_jump
            allowed_moves = GameEngine.get_valid_moves(self.current_turn, self.board_state, must_jump)
            chosen_move = next((m for m in allowed_moves if list(m['start']) == [sr, sc] and list(m['end']) == [er, ec]), None)
            if chosen_move and self.screen_manager.current == 'game_screen':
                self.board_widget.execute_move(chosen_move)
                
        elif t == 'rematch_accepted':
            self.start_game('online', rematch=True)
            
        elif t == 'opponent_disconnected':
            self.handle_disconnect()

    def handle_disconnect(self):
        if self.game_mode != 'online':
            return
            
        self.stop_timer()
        if self.screen_manager.current in ['game_screen', 'pause_screen']:
            self.trigger_game_over(disconnect=True) 
        else:
            self.switch_screen('start_screen')

    # --- MATCH STARTERS ---
    def resume_game(self):
        self.switch_screen('game_screen')
        self.start_timer()

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
        self.board_widget.is_animating = False
        self.board_state = GameEngine.get_initial_board(boss_level)
        
        if mode == 'online':
            self.current_turn = BLUE 
        else:
            self.current_turn = self.human_player
            
        self.update_display_names()
        self.newly_promoted = None
        self.undo_stack.clear()
        
        if not rematch:
            self.match_id += 1 
        
        self.board_widget.selected_piece_coords = None
        self.board_widget.clear_all_hints()
        
        screen_mng = self.screen_manager
        if screen_mng.current == 'game_over_screen':
            go_screen = screen_mng.get_screen('game_over_screen')
            go_screen.ids.rematch_btn.text = "PLAY AGAIN" if mode != 'online' else "REQUEST REMATCH"
            
        self.switch_screen('game_screen')
        Clock.schedule_once(lambda dt: self.board_widget.calculate_board_size(), 0.1)
        self.start_timer()

    def trigger_ai_turn(self):
        must_jump = False if self.game_mode == 'campaign' else self.settings_mandatory_jump
        possible_moves = GameEngine.get_valid_moves(self.current_turn, self.board_state, must_jump)
        if not possible_moves: return
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
        result = GameEngine.minimax(pure_board, depth, float('-inf'), float('inf'), True, current_turn, human_player, must_jump)
        chosen_move = result['move'] if result['move'] else possible_moves[0]
        Clock.schedule_once(lambda dt: self.apply_ai_move(chosen_move, thread_match_id), 0.5)

    @mainthread
    def apply_ai_move(self, chosen_move, thread_match_id):
        if self.match_id != thread_match_id: return
        self.is_thinking = False
        
        if self.screen_manager.current not in ('game_screen', 'pause_screen'): return
            
        self.board_widget.execute_move(chosen_move)

if __name__ == '__main__':
    CheckersApp().run()
