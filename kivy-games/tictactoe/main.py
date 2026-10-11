# =========================================================================
# 1. CORE ANDROID GRAPHICS SAFETY (MUST BE AT THE VERY TOP)
# =========================================================================
import os
import sys

# Completely disable multisampling to prevent eglChooseConfig crashes on Android
from kivy.config import Config
Config.set('graphics', 'multisamples', '0')

# PyInstaller Path Resolver
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# =========================================================================
# 2. IMPORTS & AUDIO CONSTANTS
# =========================================================================
import random
import traceback
import threading
import json
import ssl  

ENABLE_AUDIO = True  
BG_MUSIC_FILE = resource_path('music.ogg')  
CLICK_SFX_FILE = resource_path('click.wav')
WIN_SFX_FILE = resource_path('win.wav')
TIE_OR_LOSE_SFX_FILE = resource_path('tieorlose.wav')

try:
    import websocket  
    from kivy.app import App
    from kivy.lang import Builder
    from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
    from kivy.uix.modalview import ModalView
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.label import Label
    from kivy.uix.anchorlayout import AnchorLayout
    from kivy.uix.behaviors import ButtonBehavior
    from kivy.uix.widget import Widget
    from kivy.uix.slider import Slider
    from kivy.properties import StringProperty, NumericProperty, ListProperty, DictProperty, BooleanProperty
    from kivy.clock import Clock, mainthread 
    from kivy.animation import Animation
    from kivy.metrics import dp
    from kivy.core.audio import SoundLoader 
    from kivy.graphics.texture import Texture
    from kivy.graphics import Rectangle, Color, Ellipse, Line
    from kivy.factory import Factory
except Exception as e:
    print("Failed to import Kivy modules:")
    traceback.print_exc()
    raise e

# =========================================================================
# 3. GLOBAL COLOR PALETTE (BRIGHTENED & FROSTED)
# =========================================================================
THEMES = {
    'Midnight Neon': {
        'bg_top':       [0.10, 0.12, 0.16, 1.0],  # Brighter deep blue/gray
        'bg_bot':       [0.04, 0.05, 0.08, 1.0],  
        'panel_bg':     [0.12, 0.14, 0.18, 0.85], 
        'panel_border': [1.00, 1.00, 1.00, 0.08], 
        'text_main':    [0.98, 0.98, 0.98, 1.0],  
        'text_dim':     [0.60, 0.65, 0.70, 1.0],  
        'color_x':      [0.00, 0.85, 1.00, 1.0],  
        'color_o':      [1.00, 0.20, 0.45, 1.0],  
        'color_tie':    [0.60, 0.40, 1.00, 1.0],  
        'btn_bg':       [1.00, 1.00, 1.00, 0.08], 
        'text_invert':  [0.05, 0.06, 0.08, 1.0],  
    },
    'Cyberpunk': {
        'bg_top':       [0.18, 0.05, 0.25, 1.0],  # Brighter purple glow
        'bg_bot':       [0.08, 0.02, 0.15, 1.0],
        'panel_bg':     [0.18, 0.06, 0.24, 0.85],
        'panel_border': [1.00, 1.00, 1.00, 0.10],
        'text_main':    [1.00, 0.90, 1.00, 1.0],  
        'text_dim':     [0.75, 0.60, 0.85, 1.0],
        'color_x':      [0.00, 1.00, 0.70, 1.0],  
        'color_o':      [1.00, 0.10, 0.65, 1.0],  
        'color_tie':    [1.00, 0.80, 0.00, 1.0],  
        'btn_bg':       [1.00, 1.00, 1.00, 0.10],
        'text_invert':  [0.10, 0.02, 0.15, 1.0],
    },
    'Arctic Light': {
        'bg_top':       [0.85, 0.93, 1.00, 1.0],  # Beautiful icy cyan gradient
        'bg_bot':       [0.96, 0.98, 1.00, 1.0],  # Crisp snow white
        'panel_bg':     [1.00, 1.00, 1.00, 0.65], # More translucent to let the ice shine through!
        'panel_border': [0.00, 0.00, 0.00, 0.06],
        'text_main':    [0.12, 0.15, 0.18, 1.0],  
        'text_dim':     [0.45, 0.50, 0.55, 1.0],
        'color_x':      [0.00, 0.45, 0.90, 1.0],  
        'color_o':      [0.90, 0.15, 0.25, 1.0],  
        'color_tie':    [0.10, 0.70, 0.45, 1.0],  
        'btn_bg':       [0.00, 0.00, 0.00, 0.05],
        'text_invert':  [0.98, 0.98, 0.98, 1.0],  
    },
    'Forest Mint': {
        'bg_top':       [0.08, 0.15, 0.12, 1.0],  # Lifted the dark greens
        'bg_bot':       [0.02, 0.07, 0.05, 1.0],
        'panel_bg':     [0.09, 0.16, 0.12, 0.85],
        'panel_border': [1.00, 1.00, 1.00, 0.06],
        'text_main':    [0.92, 0.98, 0.94, 1.0],
        'text_dim':     [0.60, 0.75, 0.65, 1.0],
        'color_x':      [0.25, 1.00, 0.55, 1.0],  
        'color_o':      [1.00, 0.65, 0.20, 1.0],  
        'color_tie':    [0.30, 0.85, 1.00, 1.0],  
        'btn_bg':       [1.00, 1.00, 1.00, 0.08],
        'text_invert':  [0.05, 0.10, 0.07, 1.0],
    }
}

# =========================================================================
# 4. KIVY UI LAYOUT (KV BLUEPRINTS)
# =========================================================================
KV = '''
# -------------------------------------------------------------
# LIQUID UI: GLASS PANEL COMPONENT
# -------------------------------------------------------------
<GlassPanel@BoxLayout>:
    canvas.before:
        Color:
            rgba: app.theme_panel_bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(24)]
            
    canvas.after:
        Color:
            rgba: app.theme_panel_border
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(24))
            width: dp(1.2)
            cap: 'round'
            joint: 'round'

# -------------------------------------------------------------
# PREMIUM KINETIC BUTTON COMPONENT (SMOOTH iOS STYLE)
# -------------------------------------------------------------
<AnimBtn>:
    font_size: '14sp'
    bold: True
    text_color: app.theme_text_main
    color: self.text_color
    is_selectable: False
    selected: False
    
    canvas.before:
        PushMatrix
        Scale:
            origin: self.center
            x: self.anim_scale
            y: self.anim_scale
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(24)]
    canvas.after:
        Color:
            rgba: app.theme_panel_border
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(24))
            width: dp(1.2)
        PopMatrix

<SegmentBtn@AnimBtn>:
    selected: False
    bg_color: app.theme_text_main if self.selected else app.theme_btn_bg
    text_color: app.theme_text_invert if self.selected else app.theme_text_main

<CellButton>:
    font_size: dp(10)
    bold: True

<FlatToggle>:
    size_hint: None, None
    size: dp(48), dp(26)
    canvas.before:
        Color:
            rgba: app.theme_color_x if self.active else app.theme_text_dim
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height / 2]
        Color:
            rgba: app.theme_bg_bot if self.active else app.theme_text_main
        Ellipse:
            pos: (self.x + self.width - self.height + dp(2) if self.active else self.x + dp(2)), self.y + dp(2)
            size: self.height - dp(4), self.height - dp(4)

# -------------------------------------------------------------
# SCREENS
# -------------------------------------------------------------
<MenuScreen>:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        
        BoxLayout:
            orientation: 'vertical'
            size_hint_x: None
            width: self.parent.width - dp(40) if self.parent.width < dp(380) else dp(340)
            spacing: dp(16)
            
            AnchorLayout:
                size_hint_y: None
                height: dp(90)
                Label:
                    text: '[color=#00E5FF]TIC[/color] [color=#FFFFFF]TAC[/color] [color=#FF3366]TOE[/color]' if app.theme_name == 'Midnight Neon' else 'TIC TAC TOE'
                    markup: True
                    font_size: '34sp'
                    bold: True
                    color: app.theme_text_main

            GlassPanel:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(210)
                padding: dp(20)
                spacing: dp(12)
                
                Label:
                    text: "PLAYER 1 MARK"
                    font_size: '12sp'
                    bold: True
                    color: app.theme_text_dim
                    size_hint_y: 0.2
                    
                BoxLayout:
                    spacing: dp(15)
                    size_hint_y: 0.35
                    SegmentBtn:
                        text: 'X'
                        font_size: '18sp'
                        selected: app.player_symbol == 'X'
                        on_release: app.set_symbol('X')
                    SegmentBtn:
                        text: 'O'
                        font_size: '18sp'
                        selected: app.player_symbol == 'O'
                        on_release: app.set_symbol('O')
                        
                Label:
                    text: "BOARD SIZE"
                    font_size: '11sp'
                    bold: True
                    color: app.theme_text_dim
                    size_hint_y: 0.2
                    
                BoxLayout:
                    spacing: dp(15)
                    size_hint_y: 0.25
                    SegmentBtn:
                        text: '3 x 3'
                        font_size: '15sp'
                        selected: app.board_size == 3
                        on_release: app.board_size = 3
                    SegmentBtn:
                        text: '5 x 5'
                        font_size: '15sp'
                        selected: app.board_size == 5
                        on_release: app.board_size = 5

            Label:
                text: 'REMEMBER: X ALWAYS GOES FIRST'
                font_size: '10sp'
                color: app.theme_text_dim
                size_hint_y: None
                height: dp(20)

            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(220)
                spacing: dp(12)
                AnimBtn:
                    text: 'NEW GAME (VS AI)'
                    font_size: '15sp'
                    bg_color: app.theme_text_main
                    text_color: app.theme_text_invert
                    on_release: app.switch_screen('difficulty', 'left')
                AnimBtn:
                    text: 'LOCAL PVP (PASS & PLAY)'
                    font_size: '15sp'
                    bg_color: app.theme_btn_bg
                    on_release: app.start_game('multi')
                AnimBtn:
                    text: 'ONLINE MULTIPLAYER (CLOUD)'
                    font_size: '15sp'
                    bg_color: app.theme_btn_bg
                    text_color: app.theme_color_x
                    on_release: app.start_online_matchmaking()
                AnimBtn:
                    text: 'LIFETIME STATISTICS'
                    font_size: '13sp'
                    bg_color: [0,0,0,0]
                    text_color: app.theme_text_dim
                    on_release: app.show_stats_popup()
                    canvas.after:
                        Color:
                            rgba: [0,0,0,0]

    # TOP QUICK ACTIONS 
    BoxLayout:
        size_hint: None, None
        size: dp(220), dp(40) 
        pos_hint: {'top': 0.97, 'right': 0.95}
        spacing: dp(10)
        AnimBtn:
            id: network_btn
            text: 'NETWORK'
            font_size: '11sp'
            bg_color: app.theme_panel_bg
            text_color: app.theme_text_main
            on_release: app.run_ping_test()
        AnimBtn:
            text: 'SETTINGS'
            font_size: '11sp'
            bg_color: app.theme_panel_bg
            text_color: app.theme_text_main
            on_release: app.show_settings_popup()

<DifficultyScreen>:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        GlassPanel:
            orientation: 'vertical'
            size_hint_x: None
            width: self.parent.width - dp(40) if self.parent.width < dp(380) else dp(340)
            size_hint_y: None
            height: dp(340)
            padding: dp(24)
            spacing: dp(16)

            Label:
                text: "SELECT DIFFICULTY"
                font_size: '18sp'
                bold: True
                color: app.theme_text_main
                size_hint_y: 0.25

            AnimBtn:
                text: 'EASY'
                font_size: '15sp'
                bg_color: app.theme_btn_bg
                on_release: app.start_game('easy')

            AnimBtn:
                text: 'MEDIUM'
                font_size: '15sp'
                bg_color: app.theme_btn_bg
                on_release: app.start_game('medium')

            AnimBtn:
                text: 'HARD'
                font_size: '15sp'
                bg_color: app.theme_text_main
                text_color: app.theme_text_invert
                on_release: app.start_game('hard')

            Widget:
                size_hint_y: 0.1

            AnimBtn:
                text: 'BACK TO MENU'
                font_size: '14sp'
                bg_color: [0,0,0,0]
                text_color: app.theme_text_dim
                on_release: app.switch_screen('menu', 'right')
                canvas.after:
                    Color:
                        rgba: [0,0,0,0]

<GameScreen>:
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'
        BoxLayout:
            orientation: 'vertical'
            size_hint_x: None
            width: self.parent.width - dp(30) if self.parent.width < dp(400) else dp(380)
            padding: dp(10)
            spacing: dp(16)

            BoxLayout:
                size_hint_y: None
                height: dp(54)
                spacing: dp(10)
                
                Label:
                    text: '[color=#00E5FF]X[/color] [color=#FF3366]O[/color]' if app.theme_name == 'Midnight Neon' else 'X O'
                    markup: True
                    font_size: '28sp'
                    bold: True
                    color: app.theme_text_main
                    size_hint_x: 0.25

                GlassPanel:
                    size_hint_x: 0.55
                    orientation: 'vertical'
                    padding: dp(4)
                    AnchorLayout:
                        anchor_x: 'center'
                        anchor_y: 'center'
                        size_hint_y: 0.6 if app.blitz_setting == 1 else 1.0
                        Label:
                            text: "AI IS THINKING..." if app.ai_thinking else (("YOUR MARK (" + app.player_symbol + ")" if app.current_player == app.player_symbol else "OPPONENT (" + app.current_player + ")") if app.game_mode == 'online' else app.current_player + " TURN")
                            font_size: '12sp'
                            bold: True
                            color: app.theme_text_main

                    BoxLayout:
                        orientation: 'vertical'
                        size_hint_y: 0.4 if app.blitz_setting == 1 else None
                        height: dp(0) if app.blitz_setting == 0 else self.minimum_height
                        opacity: 1.0 if app.blitz_setting == 1 else 0.0
                        disabled: True if app.blitz_setting == 0 else False
                        Label:
                            text: "TIMER: " + str(app.blitz_timer) + "s" if app.blitz_setting == 1 else ""
                            font_size: '11sp'
                            bold: True
                            color: app.theme_color_o if app.blitz_timer <= 2 else app.theme_text_dim
                            halign: 'center'
                            valign: 'middle'

                AnimBtn:
                    size_hint_x: 0.2
                    text: 'QUIT'
                    font_size: '12sp'
                    bg_color: app.theme_btn_bg
                    text_color: app.theme_text_dim
                    on_release: app.quit_to_menu()

            BoxLayout:
                size_hint_y: None
                height: dp(40)
                spacing: dp(8) if app.undo_setting == 1 and app.game_mode != 'online' else dp(0)
                
                AnimBtn:
                    text: 'UNDO' if app.undo_setting == 1 and app.game_mode != 'online' else ''
                    font_size: '12sp'
                    size_hint_x: 1 if app.undo_setting == 1 and app.game_mode != 'online' else None
                    width: dp(0) if app.undo_setting == 0 or app.game_mode == 'online' else dp(1)
                    opacity: 1 if app.undo_setting == 1 and app.game_mode != 'online' else 0
                    bg_color: app.theme_btn_bg
                    disabled: (True if len(app.move_history) == 0 or app.game_over else False) if app.undo_setting == 1 else True
                    on_release: app.undo_last_move()

                GlassPanel:
                    AnchorLayout:
                        anchor_x: 'center'
                        anchor_y: 'center'
                        Label:
                            text: ('CLOUD MATCH ' if app.game_mode == 'online' else app.game_mode.upper() + ' ') + str(app.board_size) + 'x' + str(app.board_size) + (' (INF)' if app.infinity_setting == 1 else '')
                            font_size: '12sp'
                            bold: True
                            color: app.theme_text_dim
                    
                AnimBtn:
                    text: 'RESET'
                    font_size: '12sp'
                    bg_color: app.theme_btn_bg
                    disabled: True if app.game_mode == 'online' else False
                    opacity: 0.3 if app.game_mode == 'online' else 1.0
                    on_release: app.reset_board()

            FloatLayout:
                id: grid_container
                size_hint_y: 0.65
                GridLayout:
                    id: board_grid
                    cols: app.board_size
                    spacing: dp(10) if app.board_size == 5 else dp(14)
                    size_hint: None, None
                    size: (grid_container.width if grid_container.width < grid_container.height else grid_container.height), (grid_container.width if grid_container.width < grid_container.height else grid_container.height)
                    pos_hint: {'center_x': 0.5, 'center_y': 0.5}
                
                Widget:
                    id: strike_overlay
                    size_hint: 1, 1

            BoxLayout:
                size_hint_y: None
                height: dp(70)
                spacing: dp(12)

                GlassPanel:
                    orientation: 'vertical'
                    Label:
                        text: 'PLAYER X'
                        color: app.theme_color_x
                        font_size: '12sp'
                        bold: True
                    Label:
                        text: str(app.x_score)
                        font_size: '22sp'
                        bold: True
                        color: app.theme_text_main

                GlassPanel:
                    orientation: 'vertical'
                    Label:
                        text: 'TIES'
                        color: app.theme_color_tie
                        font_size: '12sp'
                        bold: True
                    Label:
                        text: str(app.ties)
                        font_size: '22sp'
                        bold: True
                        color: app.theme_text_main

                GlassPanel:
                    orientation: 'vertical'
                    Label:
                        text: 'PLAYER O'
                        color: app.theme_color_o
                        font_size: '12sp'
                        bold: True
                    Label:
                        text: str(app.o_score)
                        font_size: '22sp'
                        bold: True
                        color: app.theme_text_main
'''

# =========================================================================
# 5. UI COMPONENTS & DYNAMIC BACKGROUND CLASSES
# =========================================================================
class GradientBackground(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.texture = Texture.create(size=(1, 2), colorfmt='rgb')
        with self.canvas:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(texture=self.texture, pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)
        Clock.schedule_once(self.setup_bindings, 0)

    def setup_bindings(self, dt):
        app = App.get_running_app()
        app.bind(theme_bg_top=self.update_gradient, theme_bg_bot=self.update_gradient)
        self.update_gradient()

    def update_gradient(self, *args):
        app = App.get_running_app()
        buf = bytes([
            int(app.theme_bg_bot[0]*255), int(app.theme_bg_bot[1]*255), int(app.theme_bg_bot[2]*255),
            int(app.theme_bg_top[0]*255), int(app.theme_bg_top[1]*255), int(app.theme_bg_top[2]*255)
        ])
        self.texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
        self.rect.texture = self.texture

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class FlairOrb(Widget):
    scale_val = NumericProperty(1.0)
    orb_color = ListProperty([1,1,1,1])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            self.col = Color(rgba=self.orb_color)
            self.ell = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self.update_canvas, size=self.update_canvas, scale_val=self.update_canvas, orb_color=self.update_color)

    def update_color(self, *args):
        self.col.rgba = self.orb_color

    def update_canvas(self, *args):
        center_x = self.x + self.width/2
        center_y = self.y + self.height/2
        w = self.width * self.scale_val
        h = self.height * self.scale_val
        self.ell.pos = (center_x - w/2, center_y - h/2)
        self.ell.size = (w, h)

    def pulse(self, dur):
        anim = Animation(scale_val=1.4, duration=dur, transition='in_out_sine') + \
               Animation(scale_val=1.0, duration=dur, transition='in_out_sine')
        anim.repeat = True
        anim.start(self)

class AmbientFlair(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.o1 = FlairOrb(size_hint=(None,None), size=(dp(300),dp(300)), pos_hint={'center_x':0.1, 'center_y':0.8})
        self.o2 = FlairOrb(size_hint=(None,None), size=(dp(250),dp(250)), pos_hint={'center_x':0.9, 'center_y':0.2})
        self.o3 = FlairOrb(size_hint=(None,None), size=(dp(400),dp(400)), pos_hint={'center_x':0.5, 'center_y':0.5})
        self.add_widget(self.o1)
        self.add_widget(self.o2)
        self.add_widget(self.o3)
        Clock.schedule_once(self.setup_bindings, 0)
        Clock.schedule_once(lambda d: self.o1.pulse(4), 0.1)
        Clock.schedule_once(lambda d: self.o2.pulse(5), 0.2)
        Clock.schedule_once(lambda d: self.o3.pulse(6), 0.3)

    def setup_bindings(self, dt):
        app = App.get_running_app()
        app.bind(theme_color_x=self.update_colors, theme_color_o=self.update_colors, theme_color_tie=self.update_colors)
        self.update_colors()

    def update_colors(self, *args):
        app = App.get_running_app()
        self.o1.orb_color = [app.theme_color_x[0], app.theme_color_x[1], app.theme_color_x[2], 0.04]
        self.o2.orb_color = [app.theme_color_o[0], app.theme_color_o[1], app.theme_color_o[2], 0.04]
        self.o3.orb_color = [app.theme_color_tie[0], app.theme_color_tie[1], app.theme_color_tie[2], 0.03]

class RootLayout(FloatLayout):
    pass

class WinStrike(Widget):
    line_progress = NumericProperty(0)
    
    def __init__(self, p1, p2, stroke_color, **kwargs):
        super().__init__(**kwargs)
        self.p1 = p1
        self.p2 = p2
        with self.canvas:
            Color(rgba=stroke_color)
            self.line = Line(points=[p1[0], p1[1], p1[0], p1[1]], width=dp(4), cap='round')
        self.bind(line_progress=self.update_line)
        Animation(line_progress=1.0, duration=0.35, transition='out_cubic').start(self)

    def update_line(self, *args):
        cur_x = self.p1[0] + (self.p2[0] - self.p1[0]) * self.line_progress
        cur_y = self.p1[1] + (self.p2[1] - self.p1[1]) * self.line_progress
        self.line.points = [self.p1[0], self.p1[1], cur_x, cur_y]

# 5B. KINETIC UI ELEMENTS
class AnimBtn(ButtonBehavior, Label):
    anim_scale = NumericProperty(1.0)
    bg_color = ListProperty([0,0,0,0])
    text_color = ListProperty([1,1,1,1])

    def on_press(self):
        try:
            from plyer import vibrator
            vibrator.vibrate(0.015)
        except Exception:
            pass
        
        app = App.get_running_app()
        if app: app.play_click_sound()

        Animation.cancel_all(self, 'anim_scale')
        Animation(anim_scale=0.95, duration=0.05, transition='out_cubic').start(self)

    def on_release(self):
        Animation.cancel_all(self, 'anim_scale')
        Animation(anim_scale=1.0, duration=0.15, transition='out_back').start(self)

class FlatToggle(ButtonBehavior, Widget):
    active = BooleanProperty(False)
    
    def on_press(self):
        app = App.get_running_app()
        if app: app.play_click_sound()

class MenuScreen(Screen):
    pass

class DifficultyScreen(Screen):
    pass

class GameScreen(Screen):
    pass

class CellButton(AnimBtn):
    index = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.set_default_bg, 0)

    def set_default_bg(self, dt):
        app = App.get_running_app()
        self.bg_color = app.theme_panel_bg

    def on_release(self):
        super().on_release()
        App.get_running_app().handle_click(self.index)
        
    def animate_pop(self, symbol, on_complete_callback=None):
        Animation.cancel_all(self)
        app = App.get_running_app()
        self.text = symbol
        self.text_color = app.theme_color_x if symbol == 'X' else app.theme_color_o
        
        self.font_size = dp(10) 
        target_font = dp(32) if app.board_size == 5 else dp(56)
        
        anim = Animation(font_size=target_font, duration=0.25, transition='out_back')
        if on_complete_callback:
            anim.bind(on_complete=lambda a, w: on_complete_callback())
        anim.start(self)

    def animate_win(self):
        Animation.cancel_all(self, 'bg_color')
        app = App.get_running_app()
        Animation(bg_color=app.theme_btn_bg, duration=0.25, transition='out_quad').start(self)
        
    def reset_cell(self):
        Animation.cancel_all(self)
        app = App.get_running_app()
        self.text = ""
        Animation(bg_color=app.theme_panel_bg, duration=0.2, transition='out_quad').start(self)
        self.font_size = dp(1)

    def fade_cell(self):
        Animation.cancel_all(self, 'text_color')
        app = App.get_running_app()
        base = app.theme_color_x if self.text == 'X' else app.theme_color_o
        Animation(text_color=[base[0], base[1], base[2], 0.35], duration=0.2, transition='out_quad').start(self)

    def unfade_cell(self, symbol):
        Animation.cancel_all(self, 'text_color')
        app = App.get_running_app()
        base = app.theme_color_x if symbol == 'X' else app.theme_color_o
        Animation(text_color=base, duration=0.2, transition='out_quad').start(self)

# =========================================================================
# 6. MAIN APPLICATION LOGIC & STATE MANAGEMENT
# =========================================================================
class TicTacToeApp(App):
    theme_name = StringProperty('Midnight Neon')
    theme_bg_top = ListProperty([0,0,0,1])
    theme_bg_bot = ListProperty([0,0,0,1])
    theme_panel_bg = ListProperty([0,0,0,1])
    theme_panel_border = ListProperty([0,0,0,1])
    theme_text_main = ListProperty([0,0,0,1])
    theme_text_dim = ListProperty([0,0,0,1])
    theme_color_x = ListProperty([0,0,0,1])
    theme_color_o = ListProperty([0,0,0,1])
    theme_color_tie = ListProperty([0,0,0,1])
    theme_btn_bg = ListProperty([0,0,0,1])
    theme_text_invert = ListProperty([0,0,0,1])

    player_symbol = StringProperty('X')
    ai_symbol = StringProperty('O')
    current_player = StringProperty('X')
    game_mode = StringProperty('easy')
    board_size = NumericProperty(3)
    board = ListProperty([])
    cell_widgets = DictProperty({})
    move_history = ListProperty([])
    room_id = StringProperty('')  
    
    x_pieces = ListProperty([])
    o_pieces = ListProperty([])
    
    undo_setting = NumericProperty(1)  
    blitz_setting = NumericProperty(0)  
    infinity_setting = NumericProperty(0)
    blitz_timer = NumericProperty(5)
    sfx_volume = NumericProperty(1.0)
    music_volume = NumericProperty(0.5)
    
    game_over = BooleanProperty(False)
    ai_thinking = BooleanProperty(False)
    
    x_score = NumericProperty(0)
    o_score = NumericProperty(0)
    ties = NumericProperty(0)

    def build_config(self, config):
        config.setdefaults('Preferences', {
            'theme_name': 'Midnight Neon',
            'undo_setting': '1',
            'blitz_setting': '0',
            'infinity_setting': '0',
            'sfx_volume': '1.0',
            'music_volume': '0.5'
        })
        for mode in ['Easy', 'Medium', 'Hard']:
            config.setdefaults(f'Stats{mode}', {'wins': '0', 'losses': '0', 'ties': '0'})

    def build(self):
        config = self.config
        self.theme_name = config.get('Preferences', 'theme_name')
        if self.theme_name not in THEMES:
            self.theme_name = 'Midnight Neon'
        
        t = THEMES[self.theme_name]
        self.theme_bg_top = t['bg_top']
        self.theme_bg_bot = t['bg_bot']
        self.theme_panel_bg = t['panel_bg']
        self.theme_panel_border = t['panel_border']
        self.theme_text_main = t['text_main']
        self.theme_text_dim = t['text_dim']
        self.theme_color_x = t['color_x']
        self.theme_color_o = t['color_o']
        self.theme_color_tie = t['color_tie']
        self.theme_btn_bg = t['btn_bg']
        self.theme_text_invert = t['text_invert']

        self.undo_setting = int(config.get('Preferences', 'undo_setting'))
        self.blitz_setting = int(config.get('Preferences', 'blitz_setting'))
        self.infinity_setting = int(config.get('Preferences', 'infinity_setting'))
        self.sfx_volume = float(config.get('Preferences', 'sfx_volume'))
        self.music_volume = float(config.get('Preferences', 'music_volume'))

        Builder.load_string(KV)
        
        root = RootLayout()
        bg_layer = FloatLayout()
        bg_layer.add_widget(GradientBackground())
        bg_layer.add_widget(AmbientFlair())
        root.add_widget(bg_layer)

        self.root_sm = ScreenManager(transition=SlideTransition(duration=0.25))
        self.root_sm.add_widget(MenuScreen(name='menu'))
        self.root_sm.add_widget(DifficultyScreen(name='difficulty'))
        self.root_sm.add_widget(GameScreen(name='game'))
        
        for child in self.root_sm.screens:
            child.background_color = [0,0,0,0]

        root.add_widget(self.root_sm)
        
        self.cached_lines_3x3 = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]
        self.cached_lines_5x5 = [
            [0, 1, 2, 3], [1, 2, 3, 4], [5, 6, 7, 8], [6, 7, 8, 9], [10, 11, 12, 13], 
            [11, 12, 13, 14], [15, 16, 17, 18], [16, 17, 18, 19], [20, 21, 22, 23], [21, 22, 23, 24],
            [0, 5, 10, 15], [5, 10, 15, 20], [1, 6, 11, 16], [6, 11, 16, 21], [2, 7, 12, 17], 
            [7, 12, 17, 22], [3, 8, 13, 18], [8, 13, 18, 23], [4, 9, 14, 19], [9, 14, 19, 24],
            [0, 6, 12, 18], [6, 12, 18, 24], [1, 7, 12, 17], [2, 8, 14, 20], [5, 11, 17, 23],
            [3, 7, 11, 15], [4, 8, 12, 16], [8, 12, 16, 20], [9, 13, 17, 21], [14, 18, 22, 24]
        ]
        
        Clock.schedule_once(self.init_safe_audio, 0)
        self.ai_event = None
        self.blitz_clock_event = None
        self.win_event = None  
        self.ws = None
        self.connect_to_cloud()
        return root

    # =====================================================================
    # THEME ENGINE (BUTTERY SMOOTH TRANSITIONS)
    # =====================================================================
    def apply_theme(self, theme_name):
        self.theme_name = theme_name
        self.config.set('Preferences', 'theme_name', theme_name)
        self.config.write()
        
        t = THEMES[theme_name]
        
        anim = Animation(
            theme_bg_top=t['bg_top'],
            theme_bg_bot=t['bg_bot'],
            theme_panel_bg=t['panel_bg'],
            theme_panel_border=t['panel_border'],
            theme_text_main=t['text_main'],
            theme_text_dim=t['text_dim'],
            theme_color_x=t['color_x'],
            theme_color_o=t['color_o'],
            theme_color_tie=t['color_tie'],
            theme_btn_bg=t['btn_bg'],
            theme_text_invert=t['text_invert'],
            duration=0.4, 
            transition='out_cubic'
        )
        anim.start(self)
        
        for idx, cell in self.cell_widgets.items():
            if self.board[idx] == "":
                Animation(bg_color=t['panel_bg'], duration=0.4, transition='out_cubic').start(cell)

    def cycle_theme(self):
        self.play_click_sound()
        keys = list(THEMES.keys())
        idx = keys.index(self.theme_name)
        next_theme = keys[(idx + 1) % len(keys)]
        self.apply_theme(next_theme)

    def set_symbol(self, sym):
        self.player_symbol = sym
        self.ai_symbol = 'O' if sym == 'X' else 'X'

    # =====================================================================
    # FULL-SCREEN POPUPS & SETTINGS (SLIM MODALVIEWS)
    # =====================================================================
    @mainthread
    def show_error_popup(self, error_message):
        if getattr(self, 'error_popup', None) and self.error_popup.parent:
            return

        layout = Factory.GlassPanel(orientation='vertical', padding=dp(24), spacing=dp(20))
        layout.add_widget(Label(text="SERVER MESSAGE", font_size='16sp', bold=True, color=self.theme_color_o, size_hint_y=0.3))
        layout.add_widget(Label(text=error_message, font_size='13sp', color=self.theme_text_dim, halign='center', size_hint_y=0.4))

        close_btn = Factory.AnimBtn(text='OK', bg_color=self.theme_btn_bg, text_color=self.theme_text_main, size_hint_y=0.3)
        layout.add_widget(close_btn)

        self.error_popup = ModalView(size_hint=(0.85, None), height=dp(220), auto_dismiss=True, background='', background_color=[0, 0, 0, 0])
        self.error_popup.add_widget(layout)
        close_btn.bind(on_release=self.error_popup.dismiss)
        self.error_popup.open()

    def show_settings_popup(self):
        layout = Factory.GlassPanel(orientation='vertical', padding=dp(24), spacing=dp(16))
        layout.add_widget(Label(text="SETTINGS", font_size='22sp', bold=True, color=self.theme_text_main, size_hint_y=0.15))
        
        row_t = BoxLayout(orientation='horizontal', size_hint_y=0.14)
        lbl_t = Label(text="Theme", font_size='15sp', bold=True, color=self.theme_text_dim, halign='left')
        lbl_t.bind(size=lbl_t.setter('text_size'))
        row_t.add_widget(lbl_t)
        theme_btn = Factory.AnimBtn(text=self.theme_name, font_size='13sp', bg_color=self.theme_btn_bg, text_color=self.theme_text_main, size_hint_x=0.6)
        theme_btn.bind(on_release=lambda x: self.cycle_theme() or setattr(theme_btn, 'text', self.theme_name))
        row_t.add_widget(theme_btn)
        layout.add_widget(row_t)
        
        row1 = BoxLayout(orientation='horizontal', size_hint_y=0.14)
        lbl1 = Label(text="Undo Button", font_size='15sp', bold=True, color=self.theme_text_dim, halign='left')
        lbl1.bind(size=lbl1.setter('text_size'))
        row1.add_widget(lbl1)
        toggle_undo = FlatToggle(active=(self.undo_setting == 1))
        def change_undo(instance):
            instance.active = not instance.active
            self.undo_setting = 1 if instance.active else 0
            self.config.set('Preferences', 'undo_setting', str(self.undo_setting))
            self.config.write()
        toggle_undo.bind(on_release=change_undo)
        anchor1 = AnchorLayout(anchor_x='right'); anchor1.add_widget(toggle_undo); row1.add_widget(anchor1)
        layout.add_widget(row1)

        row_b = BoxLayout(orientation='horizontal', size_hint_y=0.14)
        lbl_b = Label(text="Blitz Timer", font_size='15sp', bold=True, color=self.theme_text_dim, halign='left')
        lbl_b.bind(size=lbl_b.setter('text_size'))
        row_b.add_widget(lbl_b)
        toggle_blitz = FlatToggle(active=(self.blitz_setting == 1))
        def change_blitz(instance):
            instance.active = not instance.active
            self.blitz_setting = 1 if instance.active else 0
            self.config.set('Preferences', 'blitz_setting', str(self.blitz_setting))
            self.config.write()
        toggle_blitz.bind(on_release=change_blitz)
        anchor_b = AnchorLayout(anchor_x='right'); anchor_b.add_widget(toggle_blitz); row_b.add_widget(anchor_b)
        layout.add_widget(row_b)

        row_inf = BoxLayout(orientation='horizontal', size_hint_y=0.14)
        lbl_inf = Label(text="Infinity Mode", font_size='15sp', bold=True, color=self.theme_text_dim, halign='left')
        lbl_inf.bind(size=lbl_inf.setter('text_size'))
        row_inf.add_widget(lbl_inf)
        toggle_inf = FlatToggle(active=(self.infinity_setting == 1))
        def change_inf(instance):
            instance.active = not instance.active
            self.infinity_setting = 1 if instance.active else 0
            self.config.set('Preferences', 'infinity_setting', str(self.infinity_setting))
            self.config.write()
            self.reset_board()
        toggle_inf.bind(on_release=change_inf)
        anchor_inf = AnchorLayout(anchor_x='right'); anchor_inf.add_widget(toggle_inf); row_inf.add_widget(anchor_inf)
        layout.add_widget(row_inf)
        
        row2 = BoxLayout(orientation='horizontal', size_hint_y=0.14)
        lbl2 = Label(text="SFX Vol", font_size='13sp', bold=True, color=self.theme_text_dim, halign='left', size_hint_x=0.3)
        lbl2.bind(size=lbl2.setter('text_size'))
        row2.add_widget(lbl2)
        slider_sfx = Slider(min=0, max=1, value=self.sfx_volume, value_track=True, value_track_color=self.theme_color_x, size_hint_x=0.7)
        slider_sfx.bind(value=lambda inst, val: setattr(self, 'sfx_volume', val) or self.config.set('Preferences', 'sfx_volume', str(val)) or self.config.write())
        row2.add_widget(slider_sfx)
        layout.add_widget(row2)

        row3 = BoxLayout(orientation='horizontal', size_hint_y=0.14)
        lbl3 = Label(text="Music Vol", font_size='13sp', bold=True, color=self.theme_text_dim, halign='left', size_hint_x=0.3)
        lbl3.bind(size=lbl3.setter('text_size'))
        row3.add_widget(lbl3)
        slider_music = Slider(min=0, max=1, value=self.music_volume, value_track=True, value_track_color=self.theme_color_o, size_hint_x=0.7)
        slider_music.bind(value=lambda inst, val: setattr(self, 'music_volume', val) or self.config.set('Preferences', 'music_volume', str(val)) or self.config.write())
        row3.add_widget(slider_music)
        layout.add_widget(row3)
        
        layout.add_widget(Widget(size_hint_y=0.05)) # Spacer
        
        close_btn = Factory.AnimBtn(text='DONE', font_size='16sp', bg_color=self.theme_btn_bg, text_color=self.theme_text_main, size_hint_y=0.15)
        layout.add_widget(close_btn)
        
        self.settings_popup = ModalView(size_hint=(0.85, None), height=dp(520), auto_dismiss=True, background='', background_color=[0, 0, 0, 0])
        self.settings_popup.add_widget(layout)
        close_btn.bind(on_release=self.settings_popup.dismiss)
        self.settings_popup.open()

    def show_stats_popup(self):
        layout = Factory.GlassPanel(orientation='vertical', padding=dp(24), spacing=dp(16))
        layout.add_widget(Label(text="LIFETIME STATISTICS", font_size='18sp', bold=True, color=self.theme_text_main, size_hint_y=0.15))
        
        stats_container = BoxLayout(orientation='vertical', spacing=dp(12), size_hint_y=0.65)
        
        for mode in ['Easy', 'Medium', 'Hard']:
            section = f'Stats{mode}'
            w = self.config.get(section, 'wins')
            l = self.config.get(section, 'losses')
            t = self.config.get(section, 'ties')
            
            card = Factory.GlassPanel(orientation='horizontal', padding=dp(15), spacing=dp(5))
            m_color = self.theme_color_x if mode == 'Easy' else self.theme_color_tie if mode == 'Medium' else self.theme_color_o
            
            lbl_title = Label(text=mode.upper(), font_size='14sp', bold=True, color=m_color, size_hint_x=0.3, halign='left')
            lbl_title.bind(size=lbl_title.setter('text_size'))
            card.add_widget(lbl_title)
            
            stats_box = BoxLayout(spacing=dp(5), size_hint_x=0.7)
            
            def make_stat_col(title, val):
                b = BoxLayout(orientation='vertical')
                b.add_widget(Label(text=title, font_size='9sp', bold=True, color=self.theme_text_dim))
                b.add_widget(Label(text=str(val), font_size='16sp', bold=True, color=self.theme_text_main))
                return b
                
            stats_box.add_widget(make_stat_col('WINS', w))
            stats_box.add_widget(make_stat_col('LOSSES', l))
            stats_box.add_widget(make_stat_col('TIES', t))
            
            card.add_widget(stats_box)
            stats_container.add_widget(card)
            
        layout.add_widget(stats_container)
            
        close_btn = Factory.AnimBtn(text='CLOSE', font_size='15sp', bg_color=self.theme_btn_bg, text_color=self.theme_text_main, size_hint_y=0.2)
        layout.add_widget(close_btn)
        
        self.stats_popup = ModalView(size_hint=(0.85, None), height=dp(420), auto_dismiss=True, background='', background_color=[0, 0, 0, 0])
        self.stats_popup.add_widget(layout)
        close_btn.bind(on_release=self.stats_popup.dismiss)
        self.stats_popup.open()

    def show_winner_modal(self, text_msg):
        if getattr(self, 'popup', None) and self.popup.parent:
            return

        layout = Factory.GlassPanel(orientation='vertical', padding=dp(24), spacing=dp(20))
        lbl_color = self.theme_color_x if 'X' in text_msg else self.theme_color_o if 'O' in text_msg else self.theme_color_tie
        layout.add_widget(Label(text=text_msg, font_size='24sp', bold=True, color=lbl_color, halign='center'))
        
        btn_box = BoxLayout(spacing=dp(10), size_hint_y=0.4)
        
        quit_btn = Factory.AnimBtn(text='MENU', font_size='13sp', bg_color=self.theme_btn_bg)
        quit_btn.bind(on_release=lambda x: self.quit_to_menu_from_popup())
        
        next_btn = Factory.AnimBtn(text='NEXT ROUND', font_size='13sp', bg_color=self.theme_panel_bg)
        
        if self.game_mode == 'online':
            if any(word in text_msg for word in ["DISCONNECTED", "TERMINATED", "LEFT", "CLOSED"]):
                next_btn.text = 'NO REMATCH'
                next_btn.disabled = True
                next_btn.opacity = 0.4
            else:
                next_btn.text = 'REMATCH'
                def req_rematch(instance):
                    instance.text = "WAITING..."
                    instance.disabled = True
                    instance.opacity = 1.0  
                    instance.text_color = self.theme_color_x  
                    if self.ws and hasattr(self.ws, 'sock') and self.ws.sock and self.ws.sock.connected:
                        try:
                            self.ws.send(json.dumps({"action": "request_rematch"}))
                        except Exception:
                            pass
                next_btn.bind(on_release=req_rematch)
        else:
            next_btn.bind(on_release=lambda x: self.next_round())
        
        btn_box.add_widget(quit_btn)
        btn_box.add_widget(next_btn)
        layout.add_widget(btn_box)
        
        self.popup = ModalView(size_hint=(0.85, None), height=dp(220), auto_dismiss=False, background='', background_color=[0, 0, 0, 0])
        self.popup.add_widget(layout)
        self.popup.open()

    # =====================================================================
    # CLOUD MATCHMAKING & NETWORKING
    # =====================================================================
    def connect_to_cloud(self):
        def run_socket():
            import ssl
            cloud_url = "wss://tictactoe-server-ql1y.onrender.com/tictactoe" 
            
            custom_context = ssl.create_default_context()
            custom_context.check_hostname = False
            custom_context.verify_mode = ssl.CERT_NONE

            self.ws = websocket.WebSocketApp(
                cloud_url,
                on_message=self.on_cloud_message,
                on_error=self.on_cloud_error,
                on_close=self.on_cloud_close
            )
            
            self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE, "context": custom_context})

        self.net_thread = threading.Thread(target=run_socket)
        self.net_thread.daemon = True 
        self.net_thread.start()
        
        Clock.schedule_once(self.start_safe_heartbeat, 1)

    def start_safe_heartbeat(self, dt):
        if getattr(self, 'heartbeat_event', None):
            self.heartbeat_event.cancel()
        self.heartbeat_event = Clock.schedule_interval(self.send_heartbeat, 25)

    def send_heartbeat(self, dt):
        if self.ws and hasattr(self.ws, 'sock') and self.ws.sock and self.ws.sock.connected:
            try:
                self.ws.send(json.dumps({"action": "ping"}))
            except Exception:
                pass

    def run_ping_test(self):
        menu_screen = self.root_sm.get_screen('menu')
        if 'network_btn' not in menu_screen.ids:
            return
        net_btn = menu_screen.ids.network_btn

        is_connected = False
        if self.ws and hasattr(self.ws, 'sock') and self.ws.sock and self.ws.sock.connected:
            is_connected = True

        if is_connected:
            net_btn.text = "CONNECTED"
            net_btn.text_color = self.theme_text_invert
            Animation.cancel_all(net_btn, 'bg_color')
            anim = Animation(bg_color=self.theme_color_x, duration=0.2) + Animation(bg_color=self.theme_panel_bg, duration=1.5)
            
            def reset_text(*args):
                net_btn.text = "NETWORK"
                net_btn.text_color = self.theme_text_main
            anim.bind(on_complete=reset_text)
            anim.start(net_btn)
            
        else:
            net_btn.text = "RECONNECTING"
            net_btn.text_color = self.theme_text_invert
            Animation.cancel_all(net_btn, 'bg_color')
            anim = Animation(bg_color=self.theme_color_o, duration=0.2) + Animation(bg_color=self.theme_panel_bg, duration=2.5)
            
            def reset_text_bad(*args):
                net_btn.text = "NETWORK"
                net_btn.text_color = self.theme_text_main
            anim.bind(on_complete=reset_text_bad)
            anim.start(net_btn)
            
            if getattr(self, 'heartbeat_event', None):
                self.heartbeat_event.cancel()
            if self.ws:
                self.ws.close()
                self.ws = None
            self.connect_to_cloud()

    def on_cloud_message(self, ws, message):
        try:
            data = json.loads(message)
            self.process_cloud_payload(data)
        except json.JSONDecodeError:
            pass 

    @mainthread
    def on_cloud_error(self, ws, error):
        print("[CLOUD ERROR]", error)

    @mainthread
    def on_cloud_close(self, ws, status, msg):
        print("[CLOUD DISCONNECTED]")
        if self.game_mode == 'online' and not self.game_over:
            self.show_error_popup("LOST CONNECTION TO SERVER.")
            self.quit_to_menu()

    @mainthread  
    def process_cloud_payload(self, data):
        action = data.get("action", "")
        
        if action == "match_start":
            self.room_id = data.get("room_id")
            self.player_symbol = data.get("assigned_symbol")
            self.current_player = data.get("current_turn", "X")
            
            if hasattr(self, 'matchmaking_popup') and self.matchmaking_popup:
                self.matchmaking_popup.dismiss()
            
            self.game_mode = "online"
            self.reset_board_ui_only()
            self.switch_screen('game', 'left')
            
        elif action == "rematch_accepted":
            if getattr(self, 'popup', None):
                self.popup.dismiss()
                self.popup = None
            self.reset_board_ui_only()
            self.current_player = data.get("current_turn", "X")
           
        elif action == "state_update":
            idx = data.get("placed_index")
            sym = data.get("placed_symbol")
            rem_idx = data.get("removed_index")
            
            self.execute_synchronized_move(idx, sym, rem_idx)
            self.current_player = data.get("next_turn", "X")
            
        elif action in ["game_over", "opponent_disconnected"]:
            reason = data.get("reason", "disconnect")
            winner = data.get("winner", "")
            win_line = data.get("winning_line", [])
            
            if self.game_over:
                if reason == "disconnect" or action == "opponent_disconnected":
                    if getattr(self, 'popup', None):
                        self.popup.dismiss()
                        self.popup = None 
                    self.show_winner_modal("OPPONENT LEFT\nROOM CLOSED")
                return

            self.game_over = True
            self.stop_blitz_timer()
            
            if action == "opponent_disconnected" or reason == "disconnect":
                if ENABLE_AUDIO and getattr(self, 'sound_win', None): self.sound_win.play()
                self.show_winner_modal("OPPONENT DISCONNECTED\nYOU WIN!")
                
            elif reason == "win":
                if ENABLE_AUDIO:
                    if winner == self.player_symbol:
                        if getattr(self, 'sound_win', None): self.sound_win.play()
                    else:
                        if getattr(self, 'sound_tie_or_lose', None): self.sound_tie_or_lose.play()
                
                for idx in win_line:
                    if idx in self.cell_widgets: 
                        self.cell_widgets[idx].animate_win()
                
                if win_line:
                    first_cell = self.cell_widgets.get(win_line[0])
                    last_cell = self.cell_widgets.get(win_line[-1])
                    
                    if first_cell and last_cell:
                        def draw_strike(dt):
                            try:
                                overlay = self.root_sm.get_screen('game').ids.strike_overlay
                                p1 = (first_cell.center_x, first_cell.center_y)
                                p2 = (last_cell.center_x, last_cell.center_y)
                                strike = WinStrike(p1, p2, self.theme_text_main)
                                overlay.add_widget(strike)
                            except Exception:
                                pass
                        Clock.schedule_once(draw_strike, 0.2)

                if winner == 'X': self.x_score += 1
                else: self.o_score += 1
                
                self.update_lifetime_stats('win' if winner == self.player_symbol or self.game_mode == 'multi' and winner == 'X' else 'loss')
                msg = f"{winner} IS THE WINNER!" if self.board_size == 3 else f"{winner} WON (4 IN A ROW)!"
                
                self.win_event = Clock.schedule_once(lambda dt: self.show_winner_modal(msg), 1.5)
                
            elif reason == "tie":
                self.ties += 1
                if ENABLE_AUDIO and getattr(self, 'sound_tie_or_lose', None): self.sound_tie_or_lose.play()
                self.win_event = Clock.schedule_once(lambda dt: self.show_winner_modal("ROUND TIED"), 1.0)

    def start_online_matchmaking(self):
        if not self.ws or not hasattr(self.ws, 'sock') or not self.ws.sock or not self.ws.sock.connected:
            self.show_error_popup("OFFLINE\n\nPlease check your internet connection or wait for the server to wake up.")
            
            if getattr(self, 'heartbeat_event', None):
                self.heartbeat_event.cancel()
            if self.ws:
                self.ws.close()
                self.ws = None
            self.connect_to_cloud()
            return
            
        payload = json.dumps({
            "action": "join_queue", 
            "board_size": self.board_size,
            "infinity": self.infinity_setting,
            "blitz": self.blitz_setting,
            "symbol": self.player_symbol 
        })

        try:
            self.ws.send(payload)
        except Exception as e:
            print("Socket send failure:", e)
            self.show_error_popup("CONNECTION FAILED\n\nUnable to send request to the server.")
            return
        
        layout = Factory.GlassPanel(orientation='vertical', padding=dp(24), spacing=dp(16))
        layout.add_widget(Label(text="MATCHMAKING", font_size='20sp', bold=True, color=self.theme_text_main, size_hint_y=0.25))
        layout.add_widget(Label(text="SEARCHING FOR OPPONENT...", font_size='13sp', bold=True, color=self.theme_color_x, halign='center', size_hint_y=0.35))
        
        cancel_btn = Factory.AnimBtn(text='CANCEL', font_size='14sp', bg_color=self.theme_btn_bg, text_color=self.theme_text_dim, size_hint_y=0.4)
        layout.add_widget(cancel_btn)
        
        self.matchmaking_popup = ModalView(size_hint=(0.85, None), height=dp(220), auto_dismiss=False, background='', background_color=[0, 0, 0, 0])
        self.matchmaking_popup.add_widget(layout)
        
        def cancel_search(instance):
            self.matchmaking_popup.dismiss()
            if getattr(self, 'heartbeat_event', None):
                self.heartbeat_event.cancel()
            
            if self.ws and hasattr(self.ws, 'sock') and self.ws.sock and self.ws.sock.connected:
                try:
                    self.ws.send(json.dumps({"action": "leave_queue"}))
                except Exception:
                    pass
                    
            if self.ws:
                self.ws.close()
                self.ws = None
            self.connect_to_cloud()   
            
        cancel_btn.bind(on_release=cancel_search)
        self.matchmaking_popup.open()

    # =====================================================================
    # GAMEPLAY LOOP & MOVE EXECUTION
    # =====================================================================
    def init_safe_audio(self, dt):
        if not ENABLE_AUDIO: return
        try:
            self.sound_click = SoundLoader.load(CLICK_SFX_FILE)
            self.sound_win = SoundLoader.load(WIN_SFX_FILE)
            self.sound_tie_or_lose = SoundLoader.load(TIE_OR_LOSE_SFX_FILE)
            
            if getattr(self, 'sound_click', None): self.sound_click.volume = self.sfx_volume
            if getattr(self, 'sound_win', None): self.sound_win.volume = self.sfx_volume
            if getattr(self, 'sound_tie_or_lose', None): self.sound_tie_or_lose.volume = self.sfx_volume
                 
            self.bg_music = SoundLoader.load(BG_MUSIC_FILE) 
            if getattr(self, 'bg_music', None):
                self.bg_music.volume = self.music_volume
                self.bg_music.loop = True  
                self.bg_music.play()
        except Exception as e:
            print("[AUDIO BYPASS]", e)

    def play_click_sound(self):
        if ENABLE_AUDIO and getattr(self, 'sound_click', None):
            if self.sound_click.state == 'play':
                self.sound_click.stop()
            self.sound_click.play()

    def switch_screen(self, screen_name, direction='left'):
        self.root_sm.transition.direction = direction
        self.root_sm.current = screen_name

    def handle_click(self, index):
        if self.board[index] != "" or self.game_over or self.ai_thinking: return
        
        if self.game_mode == 'online':
            if self.current_player != self.player_symbol: return
            
            payload = json.dumps({
                "action": "submit_move",
                "index": index
            })
            
            try:
                if self.ws and hasattr(self.ws, 'sock') and self.ws.sock and self.ws.sock.connected:
                    self.ws.send(payload)
            except Exception as e:
                print("Failed to send online move:", e)
            return

        self.stop_blitz_timer()
        self.render_move(index, self.current_player)

    def execute_synchronized_move(self, index, symbol, removed_idx):
        self.stop_blitz_timer()
        target_list = self.x_pieces if symbol == 'X' else self.o_pieces
        
        if removed_idx is not None:
            if target_list:
                try:
                    target_list.remove(removed_idx)
                except ValueError:
                    pass
            self.board[removed_idx] = ""
            if removed_idx in self.cell_widgets:
                self.cell_widgets[removed_idx].reset_cell()
                
        target_list.append(index)
        self.board[index] = symbol
        self.move_history.append((index, symbol, removed_idx))
        self.update_faded_pieces()
        
        if index in self.cell_widgets:
            self.cell_widgets[index].animate_pop(symbol, on_complete_callback=self.evaluate_board_status)

    def start_game(self, mode):
        self.game_mode = mode
        self.reset_board()
        self.switch_screen('game', 'left')

    def reset_board_ui_only(self):
        if getattr(self, 'win_event', None):
            self.win_event.cancel()
            self.win_event = None

        self.root_sm.get_screen('game').ids.strike_overlay.clear_widgets()

        grid = self.root_sm.get_screen('game').ids.board_grid
        grid.clear_widgets()
        self.cell_widgets.clear()
        
        total_cells = self.board_size * self.board_size
        self.board = [""] * total_cells
        self.move_history = []
        self.x_pieces = []
        self.o_pieces = []
        self.game_over = False
        self.ai_thinking = False
        
        is_5x5 = (self.board_size == 5)
        for i in range(total_cells):
            cell = CellButton(index=i)
            if is_5x5: cell.radius_val = dp(10)
            grid.add_widget(cell)
            self.cell_widgets[i] = cell
        self.update_faded_pieces()
        self.start_blitz_timer()

    def reset_board(self):
        if getattr(self, 'ai_event', None):
            self.ai_event.cancel()
            self.ai_event = None
        
        if getattr(self, 'win_event', None):
            self.win_event.cancel()
            self.win_event = None

        self.stop_blitz_timer()
        self.root_sm.get_screen('game').ids.strike_overlay.clear_widgets()
            
        grid = self.root_sm.get_screen('game').ids.board_grid
        grid.clear_widgets()
        self.cell_widgets.clear()
        
        total_cells = self.board_size * self.board_size
        self.board = [""] * total_cells
        self.move_history = []
        self.x_pieces = []
        self.o_pieces = []
        self.current_player = 'X'
        self.game_over = False
        self.ai_thinking = False
        
        is_5x5 = (self.board_size == 5)
        for i in range(total_cells):
            cell = CellButton(index=i)
            if is_5x5: cell.radius_val = dp(10)
            grid.add_widget(cell)
            self.cell_widgets[i] = cell
        
        self.update_faded_pieces()

        if self.game_mode != 'multi' and self.game_mode != 'online' and self.player_symbol == 'O':
            self.current_player = self.ai_symbol
            self.ai_thinking = (self.game_mode == 'hard') 
            delay = 0.8 if self.game_mode == 'hard' else 0.1 
            self.ai_event = Clock.schedule_once(lambda dt: self.ai_move(), delay)
        else:
            self.start_blitz_timer()

    def render_move(self, index, symbol):
        removed_idx = None
        target_list = self.x_pieces if symbol == 'X' else self.o_pieces
        target_list.append(index)
        
        self.board[index] = symbol
        
        if self.infinity_setting == 1:
            max_pieces = 3 if self.board_size == 3 else 4
            if len(target_list) > max_pieces:
                removed_idx = target_list.pop(0)
                self.board[removed_idx] = ""
                if removed_idx in self.cell_widgets:
                    self.cell_widgets[removed_idx].reset_cell()
                    
        self.move_history.append((index, symbol, removed_idx))
        self.update_faded_pieces()

        if index in self.cell_widgets:
            self.cell_widgets[index].animate_pop(symbol, on_complete_callback=self.evaluate_board_status)

    def undo_last_move(self):
        if not self.move_history or self.game_over or self.game_mode == 'online' or self.ai_thinking: return
        if self.ai_event:
            self.ai_event.cancel()
            self.ai_event = None
        self.stop_blitz_timer()

        steps = 2 if self.game_mode != 'multi' and len(self.move_history) >= 2 else 1
        for _ in range(steps):
            if not self.move_history: break
            last_index, symbol, removed_index = self.move_history.pop()
            
            self.board[last_index] = ""
            if last_index in self.cell_widgets:
                self.cell_widgets[last_index].reset_cell()
            
            pieces_list = self.x_pieces if symbol == 'X' else self.o_pieces
            if last_index in pieces_list:
                pieces_list.remove(last_index)
                
            if removed_index is not None:
                self.board[removed_index] = symbol
                pieces_list.insert(0, removed_index)
                if removed_index in self.cell_widgets:
                    self.cell_widgets[removed_index].animate_pop(symbol)
                    
        self.current_player = 'X' if len(self.move_history) % 2 == 0 else 'O' if self.game_mode == 'multi' else self.player_symbol
        self.update_faded_pieces()
        self.start_blitz_timer()

    def advance_turn(self):
        if self.game_over: return
        if self.game_mode == 'multi':
            self.current_player = 'O' if self.current_player == 'X' else 'X'
            self.start_blitz_timer()
        elif self.game_mode == 'online':
            pass
        else:
            if self.current_player == self.player_symbol:
                self.current_player = self.ai_symbol
                self.stop_blitz_timer() 
                self.ai_thinking = (self.game_mode == 'hard') 
                delay = 0.8 if self.game_mode == 'hard' else 0.1 
                self.ai_event = Clock.schedule_once(lambda dt: self.ai_move(), delay)
            else:
                self.current_player = self.player_symbol
                self.start_blitz_timer()

    def quit_to_menu_from_popup(self):
        if getattr(self, 'popup', None):
            self.popup.dismiss()
            self.popup = None
        self.quit_to_menu()

    def quit_to_menu(self):
        self.stop_blitz_timer()
        self.switch_screen('menu', 'right')
        self.x_score, self.o_score, self.ties = 0, 0, 0
        
        was_online = (self.game_mode == 'online')
        self.game_mode = 'easy'
        
        if was_online:
            if getattr(self, 'heartbeat_event', None):
                self.heartbeat_event.cancel()
                
            if self.ws and hasattr(self.ws, 'sock') and self.ws.sock and self.ws.sock.connected:
                try:
                    self.ws.send(json.dumps({"action": "leave_match"}))
                except Exception:
                    pass
                    
            if self.ws:
                self.ws.close()
                self.ws = None
            self.connect_to_cloud()
            
        self.reset_board()

    def next_round(self):
        if getattr(self, 'popup', None):
            self.popup.dismiss()
            self.popup = None
        self.reset_board()

    # =====================================================================
    # GAME LOGIC, WIN DETECTION & AI
    # =====================================================================
    def evaluate_board_status(self):
        if self.game_mode == 'online':
            return  
        is_win_or_draw = self.check_winner_or_draw()
        if not is_win_or_draw:
            self.advance_turn()

    def update_faded_pieces(self):
        max_pieces = 3 if self.board_size == 3 else 4
        
        for idx, cell in self.cell_widgets.items():
            if self.board[idx] != "":
                cell.unfade_cell(self.board[idx])
                
        if self.infinity_setting == 0 or self.game_over:
            return
            
        if len(self.x_pieces) == max_pieces and self.x_pieces:
            oldest_x = self.x_pieces[0]
            if oldest_x in self.cell_widgets:
                self.cell_widgets[oldest_x].fade_cell()
                
        if len(self.o_pieces) == max_pieces and self.o_pieces:
            oldest_o = self.o_pieces[0]
            if oldest_o in self.cell_widgets:
                self.cell_widgets[oldest_o].fade_cell()

    def check_winner_or_draw(self):
        if self.game_over:
            return True

        lines = self.cached_lines_3x3 if self.board_size == 3 else self.cached_lines_5x5
        for line in lines:
            symbols = [self.board[idx] for idx in line]
            if symbols[0] != "" and symbols.count(symbols[0]) == len(line):
                self.game_over = True
                self.ai_thinking = False
                self.stop_blitz_timer()
                winner = symbols[0]
                
                if ENABLE_AUDIO:
                    if self.game_mode == 'multi' or self.game_mode == 'online':
                        if getattr(self, 'sound_win', None): self.sound_win.play()
                    else:
                        if winner == self.player_symbol:
                            if getattr(self, 'sound_win', None): self.sound_win.play()
                        else:
                            if getattr(self, 'sound_tie_or_lose', None): self.sound_tie_or_lose.play()
                    
                for idx in line:
                    if idx in self.cell_widgets: self.cell_widgets[idx].animate_win()
                
                first_cell = self.cell_widgets.get(line[0])
                last_cell = self.cell_widgets.get(line[-1])
                
                if first_cell and last_cell:
                    def draw_strike(dt):
                        try:
                            overlay = self.root_sm.get_screen('game').ids.strike_overlay
                            p1 = (first_cell.center_x, first_cell.center_y)
                            p2 = (last_cell.center_x, last_cell.center_y)
                            strike = WinStrike(p1, p2, self.theme_text_main)
                            overlay.add_widget(strike)
                        except Exception:
                            pass
                    Clock.schedule_once(draw_strike, 0.2)

                if winner == 'X': self.x_score += 1
                else: self.o_score += 1
                
                self.update_lifetime_stats('win' if winner == self.player_symbol or self.game_mode == 'multi' and winner == 'X' else 'loss')
                msg = f"{winner} IS THE WINNER!" if self.board_size == 3 else f"{winner} WON (4 IN A ROW)!"
                
                self.win_event = Clock.schedule_once(lambda dt: self.show_winner_modal(msg), 1.5)
                return True

        if "" not in self.board:
            self.game_over = True
            self.ai_thinking = False
            self.stop_blitz_timer()
            self.ties += 1
            self.update_lifetime_stats('tie')
            if ENABLE_AUDIO and getattr(self, 'sound_tie_or_lose', None): self.sound_tie_or_lose.play()
            
            self.win_event = Clock.schedule_once(lambda dt: self.show_winner_modal("ROUND TIED"), 1.0)
            return True
            
        return False

    def update_lifetime_stats(self, outcome):
        if self.game_mode == 'multi' or self.game_mode == 'online': 
            return  
            
        mapping = {'easy': 'StatsEasy', 'medium': 'StatsMedium', 'hard': 'StatsHard'}
        section = mapping.get(self.game_mode)
        if not section: return
            
        field = 'wins' if outcome == 'win' else 'losses' if outcome == 'loss' else 'ties'
        current_val = int(self.config.get(section, field))
        self.config.set(section, field, str(current_val + 1))
        self.config.write()

    def start_blitz_timer(self):
        self.stop_blitz_timer()
        if self.blitz_setting == 0 or self.game_over: return
        self.blitz_timer = 5
        self.blitz_clock_event = Clock.schedule_interval(self.blitz_tick, 1.0)

    def stop_blitz_timer(self):
        if getattr(self, 'blitz_clock_event', None):
            self.blitz_clock_event.cancel()
            self.blitz_clock_event = None

    def blitz_tick(self, dt):
        if self.game_over:
            self.stop_blitz_timer()
            return
            
        self.blitz_timer -= 1
        if self.blitz_timer <= 0:
            self.stop_blitz_timer()
            if self.game_mode == 'online':
                return
            available = [i for i, spot in enumerate(self.board) if spot == ""]
            if available:
                self.render_move(random.choice(available), self.current_player)

    def ai_move(self):
        self.ai_thinking = False
        if self.game_over or self.current_player != self.ai_symbol: return

        index = None
        if self.board_size == 3:
            if self.game_mode == 'easy': index = self.easy_ai()
            elif self.game_mode == 'medium': index = self.medium_ai(self.cached_lines_3x3, 3)
            elif self.game_mode == 'hard': index = self.hard_3x3_alpha_beta()
        else:
            if self.game_mode == 'easy': index = self.easy_ai()
            elif self.game_mode == 'medium': index = self.medium_ai(self.cached_lines_5x5, 4)
            elif self.game_mode == 'hard': index = self.hard_5x5_positional()

        if index is not None and self.board[index] == "":
            self.render_move(index, self.ai_symbol)

    def easy_ai(self):
        available = [i for i, spot in enumerate(self.board) if spot == ""]
        return random.choice(available) if available else None

    def medium_ai(self, lines_pool, target_len):
        for symbol in [self.ai_symbol, self.player_symbol]:
            for line in lines_pool:
                v = [self.board[i] for i in line]
                if v.count(symbol) == target_len - 1 and v.count("") == 1:
                    return line[v.index("")]
        return self.easy_ai()

    def hard_3x3_alpha_beta(self):
        if self.board[4] == "": return 4
        best_score, best_move = -math.inf, None
        board_copy = list(self.board)
        
        for i in range(9):
            if board_copy[i] == "":
                board_copy[i] = self.ai_symbol
                score = self.minimax_ab(board_copy, 0, -math.inf, math.inf, False)
                board_copy[i] = ""
                if score > best_score:
                    best_score, best_move = score, i
        return best_move if best_move is not None else self.easy_ai()

    def minimax_ab(self, board_state, depth, alpha, beta, is_maximizing):
        for line in self.cached_lines_3x3:
            if board_state[line[0]] == board_state[line[1]] == board_state[line[2]] != "":
                return 10 - depth if board_state[line[0]] == self.ai_symbol else depth - 10
        if "" not in board_state: return 0

        best_score = -math.inf if is_maximizing else math.inf
        symbol = self.ai_symbol if is_maximizing else self.player_symbol
        
        for i in range(9):
            if board_state[i] == "":
                board_state[i] = symbol
                score = self.minimax_ab(board_state, depth + 1, alpha, beta, not is_maximizing)
                board_state[i] = ""
                if is_maximizing:
                    best_score = max(score, best_score)
                    alpha = max(alpha, best_score)
                else:
                    best_score = min(score, best_score)
                    beta = min(beta, best_score)
                if beta <= alpha: break
        return best_score

    def hard_5x5_positional(self):
        lines = self.cached_lines_5x5
        for count, vacancies in [(3, 1), (2, 2)]:
            for symbol in [self.ai_symbol, self.player_symbol]:
                for line in lines:
                    v = [self.board[i] for i in line]
                    if v.count(symbol) == count and v.count("") == vacancies:
                        return line[v.index("")]
            
        spatial_weights = [12, 6, 7, 8, 11, 13, 16, 17, 18, 1, 2, 3, 5, 9, 15, 19, 21, 22, 23, 0, 4, 20, 24]
        for idx in spatial_weights:
            if self.board[idx] == "": return idx
        return self.easy_ai()

    def on_sfx_volume(self, instance, value):
        if ENABLE_AUDIO:
            if getattr(self, 'sound_click', None): self.sound_click.volume = value
            if getattr(self, 'sound_win', None): self.sound_win.volume = value
            if getattr(self, 'sound_tie_or_lose', None): self.sound_tie_or_lose.volume = value

    def on_music_volume(self, instance, value):
        if ENABLE_AUDIO and getattr(self, 'bg_music', None): self.bg_music.volume = value

if __name__ == '__main__':
    try:
        TicTacToeApp().run()
    except Exception as e:
        print("App crashed:")
        traceback.print_exc()
        raise e
