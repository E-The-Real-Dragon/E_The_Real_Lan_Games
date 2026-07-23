# E The Real LAN Games

Private household multiplayer games over your home Wi‑Fi.  
No internet required after install. Host on one PC, join from another on the same network.

**GitHub (private):** https://github.com/E-The-Real-Dragon/E_The_Real_Lan_Games

## Playable now

| Game | Status |
|------|--------|
| **Checkers** | Fully playable over LAN |
| UNO | Coming soon |
| Chess | Coming soon |
| Othello | Coming soon |
| Tic Tac Toe | Coming soon |

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
  main.py                      # App + Checkers + LAN networking
  requirements.txt
  E_The_Real_Lan_Games.spec    # PyInstaller recipe
  README.md
  LICENSE
  .gitignore
```

## Privacy

This repository is **private**. It is intended for household use and easy backup/edits, not public distribution.

## License

MIT — see [LICENSE](LICENSE).
