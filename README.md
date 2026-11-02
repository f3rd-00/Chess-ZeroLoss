<div align="center">♞ Chess-ZeroLoss
A Python bridge between Stockfish and a browser-based chessboard.

♔ ♕ ♖ ♗ ♘ ♙  ·  ♚ ♛ ♜ ♝ ♞ ♟

Python · Stockfish · Selenium · python-chess
</div>
# ♟ About
Chess-ZeroLoss is a small Windows-based Python experiment that connects a local Stockfish engine to a Chess.com board through Chrome automation.

It follows the moves on the page, reconstructs the position using python-chess, and asks Stockfish to calculate a reply. The goal was to experiment with engine integration, board synchronization, and browser automation in one project.

Fair-play note: This code is intended for personal experimentation and authorized testing only. Do not use it to play moves or receive engine assistance against other people on Chess.com. Doing so violates the site's fair-play rules.
# ♜ How it works
1. Selenium opens a dedicated Chrome session and waits for a Chess.com board.
2. You choose whether the engine controls White or Black.
3. The script reads the move list and, when available, the board's current FEN.
4. python-chess rebuilds and checks the position.
5. Stockfish calculates a move locally using the UCI protocol.
6. Selenium can click the move on the board and handle pawn promotion.
The script also watches for board updates, retries moves that were not confirmed, and can detect the start of another game after being paused.
# ♙ What's included
- Local Stockfish integration through python-chess
- Chrome automation using Selenium
- White or Black selection at startup
- Move-list parsing with a live-board FEN fallback
- Promotion handling for queens, rooks, bishops, and knights
- Board synchronization and status messages in the terminal
- F3 pause with detection of a subsequent game
- PowerShell setup script for downloading a Windows Stockfish executable
# ♘ Requirements
- Windows (the script uses msvcrt and the setup script uses PowerShell)
- Python 3
- Google Chrome
- Internet access for the browser page and the initial Stockfish download
Install the Python dependencies:
python -m pip install python-chess selenium
# ♗ Installation
Clone the repository:
git clone https://github.com/f3rd-00/Chess-ZeroLoss.git
cd Chess-ZeroLoss
Install the Stockfish executable into the path expected by main.py:
.\setup.ps1
If PowerShell blocks local scripts, review your execution policy before running the setup script. You can also download Stockfish from the official project and place the executable at the path configured in ENGINE_PATH.

Run the application:
python main.py
A Chrome window will open with a separate browser profile. The program waits for a visible chessboard and then asks which color the engine should control.
For permitted tests, use a controlled environment where every participant has agreed to engine-driven play. The project's Chess.com selectors may need updating if that website changes.

# ♖ Controls and configuration
Setting	Behavior
F3	Pause the engine and wait for the next game
ENGINE_MOVE_DELAY	Delay before the script clicks a calculated move
SQUARE_CLICK_GAP	Delay between selecting the source and destination squares
BOARD_UPDATE_WAIT	Wait after attempting a move
POLL_INTERVAL	Interval for checking board changes
ENGINE_PATH	Location of the Stockfish executable

# ♛ Performance & Testing

During testing, Chess-ZeroLoss was put up against a chess computer rated at 3200 Elo and successfully won the match.
The test demonstrated the project's ability to execute Stockfish's moves through the browser and complete a game against a high-rated computer opponent.
Test result:
Opponent: 3200 Elo chess computer
Result: Victory
Engine: Stockfish
Automation: Python + Selenium

Note: This was an individual test, not an official engine benchmark. The opponent's displayed rating does not represent Chess-ZeroLoss's own Elo rating.

Stockfish is currently asked to think for 0.5 seconds per move (chess.engine.Limit(time=0.5)). You can adjust that value in play_engine_move().
# ♛ Project files
Chess-ZeroLoss/
├── main.py       # Browser automation, board tracking and engine moves
└── setup.ps1     # Downloads and installs the Stockfish executable
The setup script creates the engine directory locally, and Chrome creates a persistent profile directory when launched.
# ♚ Notes
- This project depends on Chess.com's page structure, including selectors such as wc-chess-board. Site updates can break compatibility.
- The script is designed for Windows; it is not currently a cross-platform application.
- The Stockfish executable is downloaded separately from the official release source.
- This is an experimental project, not an official Chess.com or Stockfish integration.
# Acknowledgments
- Stockfish — the open-source chess engine
- python-chess — chess rules, positions and UCI engine communication
- Selenium — browser automation
<div align="center">♔ Every move counts. ♚
</div>
