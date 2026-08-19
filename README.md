# E The Real LAN Games

Private household multiplayer games over your home Wi‑Fi.  
No internet required after install. Host on one PC, join from another on the same network.

**GitHub:** https://github.com/E-The-Real-Dragon/E_The_Real_Lan_Games

## Playable now

| Game | Status |
|------|--------|
| **Checkers** | Fully playable over LAN |
| **UNO** | Fully playable over LAN (private hands, drag-to-play) |
| **Cribbage** | Fully playable over LAN (2-player, race to 121) |
| Chess | Coming soon |
| Othello | Coming soon |
| Tic Tac Toe | Coming soon |

### UNO how to play

1. Host selects **UNO** → Host Game → Start Hosting (share your IP).
2. Guest joins with that IP.
3. **You only see your own cards** at the bottom. Opponent cards are face-down on top.
4. **Drag** a highlighted (legal) card onto the **DISCARD** pile in the middle.
5. Or **click DRAW** to take a card (if playable, you may play it or press **Pass**).
6. After a Wild / Wild +4, pick a color on the overlay.
7. Press **UNO!** when you have one card. Opponent can press **Catch UNO** if you forget.

### Cribbage how to play

1. Host selects **Cribbage** → Host Game → Start Hosting.
2. Guest joins with the host IP.
3. **Discard:** each player is dealt 6 cards — click 2 (gold outline) then **Confirm 2 to Crib**.
4. **Pegging:** play cards (click or drag) so the running count stays ≤ 31. Score 15s, pairs, runs, 31, and go.
5. **The show:** press **Next Score** to score non-dealer hand, dealer hand, then crib.
6. **Next Hand** switches dealer. First to **121** wins.
7. Hands stay private until the show. Crib stays face-down until scored.

## How to play (desktop .exe)

1. Both computers must be on the **same Wi‑Fi or wired home network**.
2. **Host** (usually your PC):
   - Open the `E_The_Real_Lan_Games` folder on the Desktop.
   - Double‑click `E_The_Real_Lan_Games.exe`.
   - On the main menu, leave **Checkers** selected.
   - Choose **Host Game**.
   - Pick your color and your opponent’s color.
   - Optional: check **Force jumps when able** (mandatory captures — standard rules).
   - Click **Start Hosting**.
   - Note the **IP address** shown (example: `192.168.1.42`) and tell the other player.
3. **Guest** (other household PC):
   - Copy the whole `E_The_Real_Lan_Games` folder to their Desktop (or USB).
   - Run `E_The_Real_Lan_Games.exe`.
   - Choose **Join Game**, type the host IP, click **Connect**.
4. Game starts automatically.
   - Bottom of the board = Host  
   - Top of the board = Guest  
   - Click your piece (yellow ring), then a green square to move.  
   - Far side promotes to **King** (golden crown). Kings move/jump backward.  
   - Multi‑jumps: keep clicking the next green landing square.

### Optional jumps mode

If **Force jumps** is unchecked:

- Quiet moves and jumps can both be legal at the start of a turn.
- A simple one‑step move always ends the turn.
- After a jump, you may continue a chain if more jumps exist.
- **End Turn (skip jumps)** appears when you may voluntarily pass remaining jumps.

### Tips

- First run may trigger Windows Firewall — allow on **private** networks.
- Port used: **54321** (no router port‑forward needed on a home LAN).
- To find your IP manually: Command Prompt → `ipconfig` → IPv4 Address.
- After game over: **Back to Menu**, then host/join again.
- Colors: Red, Blue, Green, Black, White.
- Networking is **host‑authoritative** (host is the source of truth for the board).

## For developers (optional)

You do **not** need this section to play. It is only if you edit the code later.

### Requirements

- Python 3.11+ recommended  
- `pip install -r requirements.txt`

### Run from source

```text
python main.py
```

### Build a Windows folder package

```text
pyinstaller E_The_Real_Lan_Games.spec
```

Output appears under `dist/E_The_Real_Lan_Games/`. Copy that whole folder to the Desktop to play without Python.

## Project layout

```text
E_The_Real_Lan_Games/
  main.py                      # App hub + Checkers + LAN networking
  uno_game.py                  # UNO rules, private hands, card art, drag-drop UI
  cribbage_game.py             # Cribbage rules, pegging, show scoring, UI
  requirements.txt
  E_The_Real_Lan_Games.spec    # PyInstaller recipe
  README.md
  LICENSE
  .gitignore
```

## License

**E_The_Real Source-Available License 1.0** (not MIT/GPL).

You may view, copy, and tweak this project for yourself. You may **not** publish or distribute a modified version without written consent from E_The_Real. See [LICENSE](LICENSE).
