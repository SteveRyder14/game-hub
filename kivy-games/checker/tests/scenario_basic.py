# Baseline scenario: exercised by harness via exec(); ctx names available.
tick_for(0.3)
report('app built', app.screen_manager.current == 'start_screen', app.screen_manager.current)
print('maxfps at startup:', Clock._max_fps, '| settings_fps:', app.settings_fps)

# Visit every screen
for s in ['settings_screen', 'aimenu_screen', 'difficulty_screen', 'campaign_screen', 'pause_screen', 'game_over_screen', 'matchmaking_screen', 'start_screen']:
    app.switch_screen(s); tick_for(0.15)
    report('switch ' + s, app.screen_manager.current == s)

# FPS cycling
before = Clock._max_fps
app.cycle_fps(); tick_for(0.05)
print('after cycle_fps: settings_fps=', app.settings_fps, 'Clock._max_fps=', Clock._max_fps)
report('fps setting applied live', abs(Clock._max_fps - app.settings_fps) < 0.01)

# Start a local game and make a legal move via touch
app.start_game('local'); tick_for(0.4)
bw = app.board_widget
report('board sized', bw.sq_size > 0, 'sq=%.1f' % bw.sq_size)
# Blue (player 1) moves from row 2 -> row 3. Piece at (2,1) can go to (3,0) or (3,2)
simulate_touch(*square_center(bw, 2, 1)); tick_for(0.1)
report('piece selected', bw.selected_piece_coords == (2, 1), str(bw.selected_piece_coords))
simulate_touch(*square_center(bw, 3, 2)); tick_for(1.0)
report('move applied', app.board_state[3][2] == 1 and app.board_state[2][1] == 0 and app.current_turn == 2,
       'turn=%s' % app.current_turn)
report('not stuck animating', bw.is_animating is False)
# Undo
app.trigger_undo(); tick_for(0.2)
report('undo works', app.board_state[2][1] == 1 and app.current_turn == 1)

# AI game: easy, human is blue, so AI (red) replies after human move
app.start_ai_game('easy'); tick_for(0.4)
simulate_touch(*square_center(bw, 2, 1)); tick_for(0.1)
simulate_touch(*square_center(bw, 3, 2)); tick_for(2.5)
red_moved = any(app.board_state[4][c] == 2 for c in range(8))
report('easy AI replied', red_moved and app.current_turn == 1, 'turn=%s thinking=%s' % (app.current_turn, app.is_thinking))

# Hard AI (threaded minimax)
app.start_ai_game('hard'); tick_for(0.4)
simulate_touch(*square_center(bw, 2, 1)); tick_for(0.1)
simulate_touch(*square_center(bw, 3, 2)); tick_for(4.0)
red_moved = any(app.board_state[4][c] == 2 for c in range(8))
report('hard AI replied', red_moved and app.current_turn == 1, 'turn=%s thinking=%s' % (app.current_turn, app.is_thinking))

# Hint
app.trigger_hint(); tick_for(0.2)
report('hint shown', len(bw.hint_targets) == 1)

# Blitz timer forces a move
app.settings_blitz = '3 SEC'
app.start_game('local'); tick_for(3.8)
report('blitz forced move', app.current_turn == 2, 'turn=%s' % app.current_turn)
app.settings_blitz = 'OFF'; app.stop_timer()

# Surrender -> game over
app.start_ai_game('easy'); tick_for(0.3)
app.surrender_match(); tick_for(1.0)
report('game over screen', app.screen_manager.current == 'game_over_screen', app.screen_manager.current)
app.quit_to_menu(); tick_for(0.3)
report('back to menu', app.screen_manager.current == 'start_screen')

# Theme / board / visuals cycling do not crash
for _ in range(4): app.cycle_theme(); tick_for(0.05)
for _ in range(4): app.cycle_board(); tick_for(0.05)
for _ in range(2): app.cycle_visuals(); tick_for(0.05)
report('cycles ok', True)

# ---- v1.1 additions ----
# UI style / glass toggles rebuild tokens without errors
app.cycle_ui_style(); tick_for(0.1)
report('ui style -> classic', app.settings_ui_style == 'CLASSIC' and app.ui_material is False)
app.toggle_setting('glass', False); tick_for(0.1)
report('glass off', app.sheen_alpha == 0 and app.panel_fill[3] > 0.9)
app.toggle_setting('glass', True); tick_for(0.1)
report('glass on', app.sheen_alpha == 1 and app.panel_fill[3] < 0.7)
app.cycle_ui_style(); tick_for(0.1)
report('ui style -> material', app.ui_material is True)
app.toggle_setting('show_fps', True); tick_for(0.6)
report('fps overlay', app.fps_overlay.opacity == 1 and 'FPS' in app.fps_overlay.text, app.fps_overlay.text)
app.toggle_setting('show_fps', False)

# Legal-move dots appear on selection
app.start_game('local'); tick_for(0.5)
simulate_touch(*square_center(bw, 2, 1)); tick_for(0.1)
report('move dots shown', len(bw.move_dots) == 2, str(len(bw.move_dots)))
simulate_touch(*square_center(bw, 2, 1)); tick_for(0.1)
report('move dots cleared on deselect', len(bw.move_dots) == 0)

# Capture animation + last-move highlight + game over victory path
app.board_state = [[0]*8 for _ in range(8)]
app.board_state[2][1] = 1; app.board_state[3][2] = 2
app.current_turn = 1; bw.render_board_background(); bw.render_pieces(); tick_for(0.1)
simulate_touch(*square_center(bw, 2, 1)); tick_for(0.1)
simulate_touch(*square_center(bw, 4, 3)); tick_for(1.5)
report('capture applied', app.board_state[4][3] == 1 and app.board_state[3][2] == 0, str(app.board_state[4][3]))
report('last move recorded', bw.last_move == ((2, 1), (4, 3)), str(bw.last_move))
tick_for(1.0)
report('game over after capture (no red moves)', app.screen_manager.current == 'game_over_screen', app.screen_manager.current)
app.quit_to_menu(); tick_for(0.3)

# Online: simulated opponent move queued while paused, applied on resume
app.game_mode = 'online'; app.online_player_id = 2
app.start_game('online'); tick_for(0.4)
app.switch_screen('pause_screen'); tick_for(0.3)
app.handle_network_data({'action': 'state_update', 'start': [2, 1], 'end': [3, 2]}); tick_for(0.1)
report('net move accepted while paused', bw.is_animating or app.board_state[3][2] == 1)
app.resume_game(); tick_for(1.0)
report('net move applied after resume', app.board_state[3][2] == 1 and app.current_turn == 2)
# stale/duplicate packet is ignored, no crash
app.handle_network_data({'action': 'state_update', 'start': [2, 1], 'end': [3, 2]}); tick_for(0.3)
report('stale packet ignored', app.current_turn == 2)
# bad payload tolerated
app.handle_network_data({'action': 'state_update'}); app.handle_network_data("junk"); tick_for(0.1)
report('bad payload tolerated', True)
# opponent disconnect -> game over w/ win
app.handle_network_data({'action': 'opponent_disconnected'}); tick_for(1.2)
report('disconnect -> game over', app.screen_manager.current == 'game_over_screen' and app.opponent_left)
app.quit_to_menu(); tick_for(0.3)

# Back key behaviour
app.on_keyboard(None, 27, None, None, None); tick_for(0.1)
report('back on start shows toast', app.toast.opacity > 0 or 'exit' in app.toast.text.lower())
app.switch_screen('settings_screen'); tick_for(0.3)
app.on_keyboard(None, 27, None, None, None); tick_for(0.3)
report('back from settings', app.screen_manager.current == 'start_screen')

# Confetti + animation guard
go = app.screen_manager.get_screen('game_over_screen')
go.ids.confetti.size = (390, 800); go.ids.confetti.burst([[1,1,1,1]]); tick_for(0.3)
report('confetti running', go.ids.confetti._event is not None)
go.ids.confetti.stop()
bw.is_animating = True; bw._arm_guard(0.2); tick_for(0.5)
report('animation guard unlocks board', bw.is_animating is False)

# LOW visuals path works end to end
app.settings_visuals = 'LOW'; app.refresh_ui_tokens(); tick_for(0.1)
app.start_ai_game('easy'); tick_for(0.4)
simulate_touch(*square_center(bw, 2, 1)); tick_for(0.1)
simulate_touch(*square_center(bw, 3, 2)); tick_for(2.0)
report('LOW visuals game works', app.current_turn == 1 and not bw.is_animating)
app.settings_visuals = 'HIGH'; app.refresh_ui_tokens()
app.quit_to_menu(); tick_for(0.3)

# Persist fps=30 and check the file for the relaunch test
app.settings_fps = 30; app.apply_fps_limit(); app.save_settings()
print('saved fps 30; Clock._max_fps =', Clock._max_fps)
