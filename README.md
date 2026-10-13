# UNiQ Games

A browser-based game hub featuring **Tic-Tac-Toe** and **Checkers**. The site is built with HTML, CSS, and JavaScript, with a Python WebSocket server powering multiplayer Tic-Tac-Toe.

## Games

- **Tic-Tac-Toe** — play on a classic 3×3 board or a larger 5×5 board. The server supports multiplayer rooms, optional game modes, rematches, and turn timers.
- **Checkers** — open the Checkers page from the game hub and play in your browser.

## Run locally

You’ll need Python 3. Install the server dependency and start the app:

```bash
python -m pip install -r requirements.txt
python server.py
```

The server uses the `PORT` environment variable when set, and otherwise listens on port `8000`. Open the local address for the chosen port in your browser (for example, `http://localhost:8000`).

## Deploy

The included `Procfile` uses this start command:

```text
web: python server.py
```

Set the deployment service’s `PORT` environment variable as required by your host.

## Project structure

```text
.
├── server.py          # Python server and WebSocket game handling
├── requirements.txt   # Python dependencies
├── Procfile           # Deployment start command
└── public/
    ├── index.html     # Game hub page
    ├── tictactoe.html # Tic-Tac-Toe game
    ├── checkers.html  # Checkers game
    ├── site.js        # Shared site scripts
    ├── style.css      # Shared styles
    └── images/        # Game artwork and screenshots
```

## Technology

- HTML, CSS, and JavaScript for the browser interface
- Python for the server
- [`websockets`](https://websockets.readthedocs.io/) for real-time connections

## Release

The repository includes the **Stable v1.0** release.
