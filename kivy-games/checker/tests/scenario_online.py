import threading, json, websocket as wsc
tick_for(0.2)
events = []
def opponent():
    ws = wsc.create_connection(game.WEBSOCKET_URL, timeout=10)
    ws.send(json.dumps({"action":"join_queue","color":2,"mandatory_jump":True,"blitz":"OFF"}))
    events.append(json.loads(ws.recv()))               # match_start
    events.append(json.loads(ws.recv()))               # our move
    ws.send(json.dumps({"action":"submit_move","start":[5,0],"end":[4,1]}))
    import time; time.sleep(1.5)
    ws.send(json.dumps({"action":"leave_match"}))
    time.sleep(0.5); ws.close()
threading.Thread(target=opponent, daemon=True).start()
app.human_player = 1
app.start_online_match(); tick_for(2.0)
report('matched online', app.screen_manager.current == 'game_screen' and app.game_mode == 'online' and app.online_player_id == 1, app.screen_manager.current)
bw = app.board_widget
simulate_touch(*square_center(bw, 2, 1)); tick_for(0.1)
simulate_touch(*square_center(bw, 3, 2)); tick_for(2.0)
report('opponent received our move', any(e.get('action') == 'state_update' for e in events), str(events))
report('opponent move applied locally', app.board_state[4][1] == 2 and app.current_turn == 1, 'turn=%s' % app.current_turn)
tick_for(2.5)
report('opponent leaving -> game over with win', app.screen_manager.current == 'game_over_screen' and app.opponent_left, app.screen_manager.current)
go = app.screen_manager.get_screen('game_over_screen')
print('result text:', repr(go.ids.winner_label.text), '| title:', go.ids.over_title.text, '| rematch disabled:', go.ids.rematch_btn.disabled)
app.quit_to_menu(); tick_for(0.3)
# cancel during matchmaking must not produce a false "offline"/"disconnected" later
app.start_online_match(); tick_for(0.3)
app.cancel_matchmaking(); tick_for(1.0)
report('cancel matchmaking clean', app.screen_manager.current == 'start_screen' and not app.network.connected)
tick_for(0.5)
report('no stale callbacks', app.screen_manager.current == 'start_screen')
