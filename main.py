#!/usr/bin/env python3
"""
E The Real LAN Games — household multiplayer games over local Wi-Fi.

Currently includes LAN Checkers, UNO, and Cribbage (host-authoritative multiplayer).
More games can be added via the in-app game picker.

Checkers: click a piece, then a highlighted square. Only legal moves.
Realistic pieces with crowns for kings. Custom colors + optional mandatory jumps.
"""

import pygame
import socket
import json
import select
import time
import sys
from typing import Optional, Tuple, List, Dict, Any

import uno_game
import cribbage_game

# ----------------------------- CONFIG -----------------------------
WIDTH, HEIGHT = 920, 720
BOARD_X, BOARD_Y = 40, 80
SQ = 72
BOARD_PX = 8 * SQ
PORT = 54321
FPS = 60

# Colors for UI
BG = (30, 33, 38)
PANEL_BG = (42, 46, 52)
LIGHT_SQ = (220, 195, 160)
DARK_SQ = (140, 95, 55)
WHITE = (255, 255, 255)
DARK_TEXT = (20, 20, 20)
ACCENT = (70, 130, 200)
HIGHLIGHT = (255, 220, 80)
VALID_MOVE = (60, 200, 80)
SELECT_RING = (255, 240, 120)

# Piece color palette (name, rgb for pieces)
PALETTE: List[Tuple[str, Tuple[int, int, int]]] = [
    ("Red", (185, 35, 35)),
    ("Blue", (35, 95, 185)),
    ("Green", (35, 145, 55)),
    ("Black", (35, 35, 35)),
    ("White", (225, 225, 225)),
]

# ----------------------------- GAME SELECTION -----------------------------
AVAILABLE_GAMES: List[Dict[str, Any]] = [
    {"id": "checkers", "label": "Checkers", "enabled": True},
    {"id": "uno", "label": "UNO", "enabled": True},
    {"id": "cribbage", "label": "Cribbage", "enabled": True},
    {"id": "chess", "label": "Chess", "enabled": False},
    {"id": "othello", "label": "Othello", "enabled": False},
    {"id": "tic_tac_toe", "label": "Tic Tac Toe", "enabled": False},
    {"id": None, "label": "More to come...", "enabled": False},
]

PLAYABLE_GAMES = {"checkers", "uno", "cribbage"}

# ----------------------------- GAME LOGIC -----------------------------
def new_board() -> List[List[Optional[Tuple[int, bool]]]]:
    """Standard 8x8 checkers setup. 0=bottom (host), 1=top (client)."""
    b: List[List[Optional[Tuple[int, bool]]]] = [[None] * 8 for _ in range(8)]
    # Top player (player 1) - rows 0-2
    for r in range(3):
        for c in range(8):
            if (r + c) % 2 == 1:
                b[r][c] = (1, False)
    # Bottom player (player 0) - rows 5-7
    for r in range(5, 8):
        for c in range(8):
            if (r + c) % 2 == 1:
                b[r][c] = (0, False)
    return b

def get_dirs(owner: int, is_king: bool) -> List[Tuple[int, int]]:
    all_d = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    if is_king:
        return all_d
    # player 0 at bottom moves toward smaller row (up)
    return [(-1, -1), (-1, 1)] if owner == 0 else [(1, -1), (1, 1)]

def get_possible_jumps(board: List[List], r: int, c: int, owner: int) -> List[Tuple]:
    """Return list of jump actions from (r,c): (sr,sc,er,ec, (mr,mc)) """
    res = []
    piece = board[r][c]
    if not piece or piece[0] != owner:
        return res
    is_king = piece[1]
    for dr, dc in get_dirs(owner, is_king):
        mr, mc = r + dr, c + dc
        er, ec = r + 2 * dr, c + 2 * dc
        if 0 <= er < 8 and 0 <= ec < 8:
            mid = board[mr][mc]
            if mid and mid[0] != owner and board[er][ec] is None:
                res.append((r, c, er, ec, (mr, mc)))
    return res

def get_all_legal_actions(board: List[List], owner: int, force_jumps: bool) -> Tuple[List[Tuple], bool]:
    """Return (list_of_actions, is_jumps_only). Each action: (sr,sc,er,ec, cap_or_None)"""
    jumps: List[Tuple] = []
    for r in range(8):
        for c in range(8):
            jumps.extend(get_possible_jumps(board, r, c, owner))
    simples: List[Tuple] = []
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if not piece or piece[0] != owner:
                continue
            for dr, dc in get_dirs(owner, piece[1]):
                er, ec = r + dr, c + dc
                if 0 <= er < 8 and 0 <= ec < 8 and board[er][ec] is None:
                    simples.append((r, c, er, ec, None))
    if jumps:
        if force_jumps:
            return jumps, True
        else:
            return jumps + simples, False
    return simples, False

def apply_action(board: List[List], action: Tuple) -> Tuple[int, int]:
    """Apply move/jump. Return the landing (er, ec). Mutates board."""
    sr, sc, er, ec, cap = action
    piece = board[sr][sc]
    board[sr][sc] = None
    owner, is_king = piece
    # King promotion
    if not is_king:
        if (owner == 0 and er == 0) or (owner == 1 and er == 7):
            is_king = True
    board[er][ec] = (owner, is_king)
    if cap:
        board[cap[0]][cap[1]] = None
    return er, ec

def count_pieces(board: List[List], owner: Optional[int] = None) -> int:
    n = 0
    for row in board:
        for p in row:
            if p and (owner is None or p[0] == owner):
                n += 1
    return n

# ----------------------------- DRAWING -----------------------------
def draw_piece(surf: pygame.Surface, cx: int, cy: int, rad: int, rgb: Tuple[int, int, int], is_king: bool):
    """Nice 3D-looking checker with highlight and optional crown."""
    # Shadow
    pygame.draw.circle(surf, (18, 18, 18), (cx + 5, cy + 6), rad)
    # Main body
    pygame.draw.circle(surf, rgb, (cx, cy), rad)
    # Dark rim/bevel
    dark = tuple(max(0, int(v * 0.52)) for v in rgb)
    pygame.draw.circle(surf, dark, (cx, cy), rad, width=max(4, rad // 5))
    # Inner ring groove
    pygame.draw.circle(surf, dark, (cx, cy), int(rad * 0.68), width=2)
    # Specular highlight (top-left)
    light = tuple(min(255, int(v * 1.25) + 55) for v in rgb)
    hl_rect = pygame.Rect(cx - int(rad * 0.52), cy - int(rad * 0.62), int(rad * 0.58), int(rad * 0.34))
    pygame.draw.ellipse(surf, light, hl_rect)
    # Crown for king
    if is_king:
        gold = (255, 210, 40)
        gold_d = (175, 130, 10)
        base_y = cy - int(rad * 0.52)
        # Crown bar
        bar_h = max(4, rad // 6)
        bar_rect = pygame.Rect(cx - int(rad * 0.42), base_y - bar_h // 2, int(rad * 0.84), bar_h)
        pygame.draw.rect(surf, gold, bar_rect, border_radius=2)
        pygame.draw.rect(surf, gold_d, bar_rect, width=1, border_radius=2)
        # Three points
        tips = []
        for sign, hmul in [(-1, 0.18), (0, 0.28), (1, 0.18)]:
            tx = cx + int(sign * rad * 0.26)
            ty = base_y - int(rad * hmul)
            tips.append((tx, ty))
            # left/right base of spike
            bx = cx + int(sign * rad * 0.12)
            pygame.draw.polygon(surf, gold, [
                (cx + int(sign * rad * 0.36), base_y - bar_h // 2 - 1),
                (tx, ty),
                (cx + int(sign * rad * 0.10), base_y - bar_h // 2 - 1),
            ])
        # Tip dots
        for tx, ty in tips:
            pygame.draw.circle(surf, gold_d, (tx, ty), max(2, rad // 9))
        # Outline on bar
        pygame.draw.lines(surf, gold_d, False, [
            (cx - int(rad * 0.42), base_y - bar_h // 2),
            (cx + int(rad * 0.42), base_y - bar_h // 2),
        ], 1)

def draw_board(surf: pygame.Surface, board: List[List], colors: Dict[int, Tuple[int, int, int]],
               selected: Optional[Tuple[int, int]], legal_actions: List[Tuple]):
    """Draw the 8x8 board + pieces + highlights."""
    # Board background shadow
    pygame.draw.rect(surf, (10, 10, 10), (BOARD_X - 8, BOARD_Y - 8, BOARD_PX + 16, BOARD_PX + 16), border_radius=6)
    pygame.draw.rect(surf, (55, 48, 40), (BOARD_X - 4, BOARD_Y - 4, BOARD_PX + 8, BOARD_PX + 8), border_radius=4)

    rad = SQ // 2 - 7
    for r in range(8):
        for c in range(8):
            x = BOARD_X + c * SQ
            y = BOARD_Y + r * SQ
            sq_col = DARK_SQ if (r + c) % 2 == 1 else LIGHT_SQ
            pygame.draw.rect(surf, sq_col, (x, y, SQ, SQ))
            # subtle inner border
            pygame.draw.rect(surf, (0, 0, 0), (x, y, SQ, SQ), width=1)

            piece = board[r][c]
            if piece:
                owner, king = piece
                px = x + SQ // 2
                py = y + SQ // 2
                draw_piece(surf, px, py, rad, colors[owner], king)

    # Selection ring + valid move markers
    if selected:
        sr, sc = selected
        sx = BOARD_X + sc * SQ + SQ // 2
        sy = BOARD_Y + sr * SQ + SQ // 2
        pygame.draw.circle(surf, SELECT_RING, (sx, sy), rad + 7, width=4)

    for action in legal_actions:
        _, _, er, ec, _ = action
        ex = BOARD_X + ec * SQ + SQ // 2
        ey = BOARD_Y + er * SQ + SQ // 2
        # Green ring + small filled
        pygame.draw.circle(surf, VALID_MOVE, (ex, ey), rad - 2, width=3)
        pygame.draw.circle(surf, (30, 120, 50), (ex, ey), 8)

def draw_text(surf: pygame.Surface, font: pygame.font.Font, text: str, x: int, y: int,
              color=WHITE, center=False, bold=False):
    img = font.render(text, True, color)
    if center:
        rect = img.get_rect(center=(x, y))
        surf.blit(img, rect)
    else:
        surf.blit(img, (x, y))

def draw_button(surf: pygame.Surface, font: pygame.font.Font, rect: pygame.Rect, text: str,
                bg=(70, 95, 140), fg=WHITE, hover=False):
    col = tuple(min(255, c + 25) for c in bg) if hover else bg
    pygame.draw.rect(surf, col, rect, border_radius=8)
    pygame.draw.rect(surf, (20, 20, 20), rect, width=2, border_radius=8)
    draw_text(surf, font, text, rect.centerx, rect.centery, fg, center=True)

def draw_color_swatch(surf: pygame.Surface, x: int, y: int, size: int, rgb: Tuple[int, int, int],
                      name: str, selected: bool, font: pygame.font.Font):
    r = size // 2 - 2
    cx, cy = x + size // 2, y + size // 2
    # swatch
    pygame.draw.circle(surf, (10, 10, 10), (cx + 2, cy + 2), r + 2)
    pygame.draw.circle(surf, rgb, (cx, cy), r)
    dark = tuple(max(0, int(v * 0.5)) for v in rgb)
    pygame.draw.circle(surf, dark, (cx, cy), r, width=3)
    if selected:
        pygame.draw.circle(surf, HIGHLIGHT, (cx, cy), r + 6, width=3)
    # label
    draw_text(surf, font, name, cx, y + size + 12, WHITE, center=True)

# ----------------------------- NETWORK HELPERS -----------------------------
def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def send_msg(sock: socket.socket, obj: Dict[str, Any]):
    if sock is None:
        return
    try:
        data = (json.dumps(obj) + "\n").encode("utf-8")
        sock.sendall(data)
    except Exception:
        pass

def recv_lines(buffer: bytearray, data: bytes) -> List[Dict[str, Any]]:
    """Accumulate and return complete \n terminated json objects."""
    if data:
        buffer.extend(data)
    lines = []
    while b"\n" in buffer:
        idx = buffer.find(b"\n")
        line = buffer[:idx]
        del buffer[:idx + 1]
        if line.strip():
            try:
                lines.append(json.loads(line.decode("utf-8")))
            except Exception:
                pass  # ignore bad
    return lines

# ----------------------------- MAIN -----------------------------
def main():
    pygame.init()
    pygame.display.set_caption("E The Real LAN Games")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    # Fonts
    font_title = pygame.font.SysFont("Segoe UI", 36, bold=True)
    font_big = pygame.font.SysFont("Segoe UI", 24, bold=True)
    font_med = pygame.font.SysFont("Segoe UI", 18)
    font_small = pygame.font.SysFont("Segoe UI", 15)

    # Game state
    screen_name = "main_menu"  # main_menu, host_setup, join_setup, hosting, joining, playing, gameover
    board = new_board()
    colors: Dict[int, Tuple[int, int, int]] = {0: PALETTE[0][1], 1: PALETTE[1][1]}  # 0 bottom, 1 top
    force_jumps = True
    selected: Optional[Tuple[int, int]] = None
    legal_actions: List[Tuple] = []
    jump_chain_active = False   # True only after executing a capture this turn (for End Turn button during multi-jumps)
    current_player = 0
    my_player = 0          # 0 for host, 1 for client
    is_host = False
    winner: Optional[int] = None

    # Networking
    server_sock: Optional[socket.socket] = None
    sock: Optional[socket.socket] = None
    net_buffer = bytearray()
    connect_ip = "192.168.1."
    connecting = False
    last_net_error = ""

    # UI state
    host_color_idx = 0   # index in PALETTE for player 0
    opp_color_idx = 1
    checkbox_rect = pygame.Rect(0, 0, 0, 0)
    input_active = False

    selected_game = "checkers"  # checkers | uno | cribbage | ...

    # UNO match state (host is authoritative; client mirrors snapshots)
    uno_match: Optional[uno_game.UnoMatch] = None
    uno_view: Optional[uno_game.UnoView] = None

    # Cribbage match state
    crib_match: Optional[cribbage_game.CribbageMatch] = None
    crib_view: Optional[cribbage_game.CribbageView] = None

    buttons: List[Tuple[pygame.Rect, str]] = []  # (rect, id) for current screen
    game_selections: List[Tuple[pygame.Rect, Optional[str]]] = []  # (rect, game_id) populated by draw_main_menu

    def reset_game_state():
        nonlocal board, selected, legal_actions, jump_chain_active, current_player, winner
        nonlocal uno_match, uno_view, crib_match, crib_view
        board = new_board()
        selected = None
        legal_actions = []
        jump_chain_active = False
        current_player = 0
        winner = None
        uno_match = None
        uno_view = None
        crib_match = None
        crib_view = None

    def start_uno_match_host():
        nonlocal uno_match, uno_view, winner
        uno_match = uno_game.UnoMatch()
        uno_match.start_new_game()
        uno_view = uno_game.UnoView(match=uno_match, my_player=0, is_host=True)
        winner = None

    def push_uno_states():
        """Host: refresh local view + send private snapshot to client."""
        nonlocal winner, screen_name
        if not is_host or uno_match is None:
            return
        if uno_match.winner is not None:
            winner = uno_match.winner
            screen_name = "gameover"
        if sock:
            send_msg(sock, uno_match.state_for(1))

    def apply_uno_action(player: int, action: Dict[str, Any]) -> bool:
        nonlocal winner, screen_name
        if uno_match is None or not is_host:
            return False
        if action.get("action") == "menu":
            return False
        changed = uno_game.process_host_action(uno_match, player, action)
        if changed:
            if uno_match.winner is not None:
                winner = uno_match.winner
                screen_name = "gameover"
                if sock:
                    send_msg(sock, {"type": "game_over", "winner": winner, "game": "uno"})
            push_uno_states()
        return changed

    def start_crib_match_host():
        nonlocal crib_match, crib_view, winner
        crib_match = cribbage_game.CribbageMatch()
        crib_match.start_match()
        crib_view = cribbage_game.CribbageView(match=crib_match, my_player=0, is_host=True)
        winner = None

    def push_crib_states():
        nonlocal winner, screen_name
        if not is_host or crib_match is None:
            return
        if crib_match.winner is not None:
            winner = crib_match.winner
            screen_name = "gameover"
        if sock:
            send_msg(sock, crib_match.state_for(1))

    def apply_crib_action(player: int, action: Dict[str, Any]) -> bool:
        nonlocal winner, screen_name
        if crib_match is None or not is_host:
            return False
        if action.get("action") == "menu":
            return False
        changed = cribbage_game.process_host_action(crib_match, player, action)
        if changed:
            if crib_match.winner is not None:
                winner = crib_match.winner
                screen_name = "gameover"
                if sock:
                    send_msg(sock, {"type": "game_over", "winner": winner, "game": "cribbage"})
            push_crib_states()
        return changed

    def start_hosting():
        nonlocal server_sock, sock, screen_name, is_host, my_player, last_net_error
        last_net_error = ""
        try:
            if server_sock:
                server_sock.close()
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(("", PORT))
            server_sock.listen(1)
            server_sock.setblocking(False)
            screen_name = "hosting"
            is_host = True
            my_player = 0
        except Exception as e:
            last_net_error = f"Host failed: {e}"
            screen_name = "host_setup"

    def do_connect():
        nonlocal sock, screen_name, connecting, last_net_error, net_buffer, is_host, my_player
        last_net_error = ""
        net_buffer.clear()
        try:
            if sock:
                sock.close()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)
            err = sock.connect_ex((connect_ip.strip(), PORT))
            connecting = True
            is_host = False
            my_player = 1
            screen_name = "joining"
            if err == 0:
                # Connected immediately — wait for host settings (do not run host setup)
                connecting = False
        except Exception as e:
            last_net_error = str(e)
            connecting = False
            screen_name = "join_setup"

    def on_client_connected():
        nonlocal screen_name, sock, is_host, my_player, colors, force_jumps
        nonlocal uno_match, uno_view, crib_match, crib_view, selected_game
        # Client just connected to us (host)
        if is_host and sock is None:
            # accept happened in loop
            pass
        screen_name = "playing"
        if selected_game == "uno":
            start_uno_match_host()
            if is_host and sock:
                payload = {
                    "type": "settings",
                    "game": "uno",
                    "you_are": 1,
                }
                send_msg(sock, payload)
                push_uno_states()
            return
        if selected_game == "cribbage":
            start_crib_match_host()
            if is_host and sock:
                payload = {
                    "type": "settings",
                    "game": "cribbage",
                    "you_are": 1,
                }
                send_msg(sock, payload)
                push_crib_states()
            return

        reset_game_state()
        # send settings to client (checkers)
        if is_host and sock:
            payload = {
                "type": "settings",
                "game": selected_game,
                "colors": {0: list(colors[0]), 1: list(colors[1])},
                "force_jumps": force_jumps,
                "you_are": 1,
            }
            send_msg(sock, payload)
            # host starts as player 0
            recompute_legals()

    def on_settings_received(msg: Dict):
        nonlocal colors, force_jumps, my_player, screen_name, selected_game
        nonlocal uno_match, uno_view, crib_match, crib_view
        selected_game = msg.get("game", "checkers")
        my_player = msg.get("you_are", 1)
        screen_name = "playing"

        if selected_game == "uno":
            uno_match = uno_game.UnoMatch()
            uno_view = uno_game.UnoView(match=uno_match, my_player=my_player, is_host=False)
            # Full snapshot arrives as uno_state right after settings
            return
        if selected_game == "cribbage":
            crib_match = cribbage_game.CribbageMatch()
            crib_view = cribbage_game.CribbageView(match=crib_match, my_player=my_player, is_host=False)
            return

        cols = msg.get("colors", {})
        if "0" in cols:
            colors[0] = tuple(cols["0"])
        if "1" in cols:
            colors[1] = tuple(cols["1"])
        force_jumps = bool(msg.get("force_jumps", True))
        reset_game_state()
        recompute_legals()

    def recompute_legals():
        nonlocal legal_actions, selected, jump_chain_active
        if screen_name != "playing":
            return
        legal_actions, _ = get_all_legal_actions(board, current_player, force_jumps)
        selected = None
        jump_chain_active = False

    def is_my_turn() -> bool:
        return current_player == my_player

    def apply_remote_move(action: Tuple):
        nonlocal current_player, selected, legal_actions
        er, ec = apply_action(board, action)
        # Only continue the turn (multi-jump / "another turn") if the *chosen action* was a 2-step capture.
        # This is the ground truth from the legal action the player selected.
        # A 1-step move (simple, including one that promotes to king and now "could jump next turn")
        # must always end the turn, even if the landing position now has jumps available as a king.
        # The cap field and post-apply position are not used for this decision.
        sr, sc, act_er, act_ec, _ = action
        is_jump_move = (abs(act_er - sr) == 2)
        more = get_possible_jumps(board, er, ec, current_player) if is_jump_move else []
        if more:
            selected = (er, ec)
            legal_actions = more
            jump_chain_active = True
        else:
            selected = None
            jump_chain_active = False
            current_player = 1 - current_player
            legal_actions, _ = get_all_legal_actions(board, current_player, force_jumps)
        check_win_after_move()

    def check_win_after_move():
        nonlocal winner, screen_name
        if not legal_actions and screen_name == "playing":
            # current_player has no moves
            winner = 1 - current_player
            screen_name = "gameover"
            if is_host and sock:
                send_msg(sock, {"type": "game_over", "winner": winner})

    def do_local_move(action: Tuple):
        """Used by host for own moves and by client for its moves (after validation on host)."""
        nonlocal current_player, selected, legal_actions
        er, ec = apply_action(board, action)
        # Only continue the turn if the chosen action (from legals at selection time) was a 2-step capture.
        # 1-step moves (incl. promotion to king) always end the turn here.
        sr, sc, act_er, act_ec, _ = action
        is_jump_move = (abs(act_er - sr) == 2)
        more = get_possible_jumps(board, er, ec, current_player) if is_jump_move else []
        if more:
            selected = (er, ec)
            legal_actions = more
            jump_chain_active = True
        else:
            selected = None
            jump_chain_active = False
            current_player = 1 - current_player
            legal_actions, _ = get_all_legal_actions(board, current_player, force_jumps)
        check_win_after_move()
        # send to peer
        if sock:
            send_msg(sock, {"type": "move", "from": [action[0], action[1]], "to": [action[2], action[3]]})

    def end_turn_sequence():
        """End the current player's turn voluntarily (e.g. after a jump, decline further captures)."""
        nonlocal current_player, selected, legal_actions, jump_chain_active
        selected = None
        jump_chain_active = False
        current_player = 1 - current_player
        legal_actions, _ = get_all_legal_actions(board, current_player, force_jumps)
        check_win_after_move()
        if sock:
            send_msg(sock, {"type": "end_jump_sequence"})

    def handle_click_play(mx: int, my: int):
        nonlocal selected, legal_actions
        if not is_my_turn() or screen_name != "playing":
            return
        br = (my - BOARD_Y) // SQ
        bc = (mx - BOARD_X) // SQ
        if not (0 <= br < 8 and 0 <= bc < 8):
            return
        piece_here = board[br][bc]

        # If we have a selection, see if clicked a valid destination
        if selected:
            for act in legal_actions:
                if act[2] == br and act[3] == bc:
                    # legal destination clicked
                    if is_host or my_player == 0:  # host authoritative or local
                        do_local_move(act)
                    else:
                        # client: send request to host
                        req = {"type": "move_request", "from": [selected[0], selected[1]], "to": [br, bc]}
                        if sock:
                            send_msg(sock, req)
                        # Optimistic: clear selection locally until confirmed
                        selected = None
                        jump_chain_active = False
                    return
            # clicked elsewhere - try to reselect own piece if has moves
            if piece_here and piece_here[0] == my_player:
                poss = [a for a in legal_actions if a[0] == br and a[1] == bc]
                if poss:
                    selected = (br, bc)
            else:
                selected = None
            return

        # No selection yet: select own piece that has legal actions
        if piece_here and piece_here[0] == my_player:
            poss = [a for a in legal_actions if a[0] == br and a[1] == bc]
            if poss:
                selected = (br, bc)

    def handle_net_message(msg: Dict[str, Any]):
        nonlocal sock, server_sock, screen_name, winner, last_net_error, current_player, selected, legal_actions
        nonlocal uno_match, uno_view, crib_match, crib_view, selected_game
        mtype = msg.get("type")
        if mtype == "settings":
            on_settings_received(msg)
        elif mtype == "uno_state":
            if uno_view is None:
                uno_match = uno_game.UnoMatch()
                uno_view = uno_game.UnoView(match=uno_match, my_player=my_player, is_host=is_host)
            uno_view.sync_from_state_msg(msg)
            if msg.get("winner") is not None:
                winner = msg.get("winner")
                screen_name = "gameover"
        elif mtype == "uno_action":
            # Client -> host action request
            if is_host and uno_match is not None:
                apply_uno_action(1, msg)
        elif mtype == "crib_state":
            if crib_view is None:
                crib_match = cribbage_game.CribbageMatch()
                crib_view = cribbage_game.CribbageView(match=crib_match, my_player=my_player, is_host=is_host)
            crib_view.sync_from_state_msg(msg)
            if msg.get("winner") is not None:
                winner = msg.get("winner")
                screen_name = "gameover"
        elif mtype == "crib_action":
            if is_host and crib_match is not None:
                apply_crib_action(1, msg)
        elif mtype == "move":
            fr = tuple(msg.get("from", [0, 0]))
            to = tuple(msg.get("to", [0, 0]))
            # reconstruct action by searching legal (or just apply if we trust, but recompute cap)
            # For simplicity we re-find the jump or simple
            sr, sc = fr
            er, ec = to
            # Try to find matching action from current legals or compute
            found = None
            for a in legal_actions:
                if a[0] == sr and a[1] == sc and a[2] == er and a[3] == ec:
                    found = a
                    break
            if not found:
                # compute cap if it was a jump
                dr = (er - sr) // 2 if abs(er - sr) == 2 else 0
                dc = (ec - sc) // 2 if abs(ec - sc) == 2 else 0
                cap = (sr + dr, sc + dc) if dr else None
                found = (sr, sc, er, ec, cap)
            apply_remote_move(found)
        elif mtype == "move_request":
            if is_host and current_player == 1:  # client turn
                sr, sc = msg.get("from", [0, 0])
                tr, tc = msg.get("to", [0, 0])
                legals, _ = get_all_legal_actions(board, 1, force_jumps)
                for a in legals:
                    if a[0] == sr and a[1] == sc and a[2] == tr and a[3] == tc:
                        # valid, apply and broadcast
                        er, ec = apply_action(board, a)
                        send_msg(sock, {"type": "move", "from": [sr, sc], "to": [tr, tc]})
                        # Only chain on 2-step capture actions chosen by the client.
                        # 1-step (incl. king promo) always end the sub-turn for the client.
                        _, _, act_er, act_ec, _ = a
                        is_jump_move = (abs(act_er - sr) == 2)
                        more = get_possible_jumps(board, er, ec, 1) if is_jump_move else []
                        if more:
                            selected = (er, ec)
                            legal_actions = more
                            jump_chain_active = True
                        else:
                            selected = None
                            jump_chain_active = False
                            current_player = 0
                            legal_actions, _ = get_all_legal_actions(board, 0, force_jumps)
                        check_win_after_move()
                        return
                # invalid request - ignore or send error (simple: do nothing)
        elif mtype == "end_jump_sequence":
            # Opponent voluntarily ended their jump sequence / turn
            selected = None
            jump_chain_active = False
            current_player = 1 - current_player
            legal_actions, _ = get_all_legal_actions(board, current_player, force_jumps)
            check_win_after_move()
        elif mtype == "game_over":
            winner = msg.get("winner", 0)
            screen_name = "gameover"
            if uno_match is not None:
                uno_match.winner = winner
            if crib_match is not None:
                crib_match.winner = winner

    def poll_network():
        nonlocal sock, server_sock, connecting, last_net_error, screen_name, net_buffer
        # 1. Host: accept new client
        if is_host and server_sock and sock is None:
            try:
                client, addr = server_sock.accept()
                client.setblocking(False)
                sock = client
                on_client_connected()
            except BlockingIOError:
                pass
            except Exception as e:
                last_net_error = str(e)

        # 2. Any connected socket: receive
        if sock:
            try:
                ready = select.select([sock], [], [], 0)[0]
                if ready:
                    data = sock.recv(4096)
                    if not data:
                        # closed
                        last_net_error = "Opponent disconnected"
                        cleanup_net()
                        screen_name = "main_menu"
                        return
                    for msg in recv_lines(net_buffer, data):
                        handle_net_message(msg)
            except BlockingIOError:
                pass
            except Exception as e:
                last_net_error = str(e)
                cleanup_net()
                if screen_name == "playing":
                    screen_name = "main_menu"

        # 3. Client connecting state
        if connecting and sock and screen_name == "joining":
            try:
                # poll writable or error
                r, w, e = select.select([], [sock], [sock], 0)
                if sock in e:
                    last_net_error = "Connect failed (refused or timeout)"
                    cleanup_net()
                    connecting = False
                    screen_name = "join_setup"
                elif sock in w:
                    connecting = False
                    # Connected — wait for settings from host before showing a game board
                    screen_name = "joining"
                    last_net_error = ""
                    # Host will send settings + (for UNO) state snapshots immediately
            except Exception as e:
                last_net_error = str(e)
                connecting = False
                screen_name = "join_setup"

    def cleanup_net():
        nonlocal sock, server_sock, connecting
        connecting = False
        if sock:
            try:
                sock.close()
            except:
                pass
            sock = None
        if server_sock:
            try:
                server_sock.close()
            except:
                pass
            server_sock = None

    def draw_main_menu():
        nonlocal buttons, game_selections
        buttons = []
        game_selections = []
        screen.fill(BG)

        # Title (now multi-game)
        draw_text(screen, font_title, "E THE REAL LAN GAMES", WIDTH // 2, 70, WHITE, center=True)
        draw_text(screen, font_med, "Play with your son over your home network", WIDTH // 2, 110, (180, 180, 180), center=True)

        # ---- LEFT: Game selection list ----
        list_x = 55
        list_y = 175
        item_h = 50
        item_w = 295
        header_y = list_y - 28

        draw_text(screen, font_big, "Select Game", list_x + 5, header_y, WHITE)

        # Subtle divider
        pygame.draw.line(screen, (55, 58, 65), (370, 155), (370, 560), 2)

        for g in AVAILABLE_GAMES:
            gid = g["id"]
            label = g["label"]
            enabled = g["enabled"]
            r = pygame.Rect(list_x, list_y, item_w, item_h)

            is_selected = (gid == selected_game) if gid else False

            if enabled:
                if is_selected:
                    pygame.draw.rect(screen, (55, 75, 105), r, border_radius=8)
                    pygame.draw.rect(screen, ACCENT, r, width=3, border_radius=8)
                    # left accent bar
                    pygame.draw.rect(screen, (90, 170, 255), (list_x, list_y + 4, 5, item_h - 8), border_radius=3)
                    text_col = WHITE
                else:
                    pygame.draw.rect(screen, (46, 50, 58), r, border_radius=8)
                    pygame.draw.rect(screen, (65, 70, 80), r, width=1, border_radius=8)
                    text_col = WHITE
            else:
                pygame.draw.rect(screen, (36, 38, 44), r, border_radius=8)
                text_col = (125, 125, 130)

            # Game name
            draw_text(screen, font_med, label, list_x + 16, list_y + 14, text_col)

            if not enabled:
                draw_text(screen, font_small, "Coming soon", list_x + 16, list_y + 32, (95, 95, 100))

            if enabled and gid:
                game_selections.append((r, gid))

            list_y += item_h + 9

        # ---- RIGHT / ACTIONS ----
        action_x = 400
        y = 195
        bw, bh = 310, 52

        # Selection status
        if selected_game in PLAYABLE_GAMES:
            labels = {"checkers": "Checkers", "uno": "UNO", "cribbage": "Cribbage"}
            status = f"{labels.get(selected_game, selected_game)} selected — full LAN support"
            status_col = (70, 200, 110)
        else:
            status = "That game is not ready yet — pick Checkers, UNO, or Cribbage"
            status_col = (200, 190, 100)
        draw_text(screen, font_med, status, action_x, y - 18, status_col)

        # Host (Checkers + UNO)
        host_enabled = (selected_game in PLAYABLE_GAMES)
        host_bg = (55, 120, 80) if host_enabled else (65, 75, 70)
        host_rect = pygame.Rect(action_x, y, bw, bh)
        draw_button(screen, font_big, host_rect, "Host Game", host_bg)
        buttons.append((host_rect, "host"))

        y += 68

        # Join (always allowed — you join whatever the host started)
        join_rect = pygame.Rect(action_x, y, bw, bh)
        draw_button(screen, font_big, join_rect, "Join Game", (55, 90, 140))
        buttons.append((join_rect, "join"))

        y += 68

        # Quit
        quit_rect = pygame.Rect(action_x, y, bw, bh)
        draw_button(screen, font_big, quit_rect, "Quit", (120, 55, 55))
        buttons.append((quit_rect, "quit"))

        # Helpful footer
        draw_text(screen, font_small, "Click a game on the left to select it.", WIDTH // 2, HEIGHT - 92, (155, 155, 160), center=True)
        draw_text(screen, font_small, "Checkers, UNO, and Cribbage are ready for LAN play. More games coming soon!", WIDTH // 2, HEIGHT - 70, (130, 130, 135), center=True)

        if last_net_error:
            draw_text(screen, font_small, last_net_error, WIDTH // 2, HEIGHT - 42, (220, 90, 90), center=True)

    def draw_host_setup():
        nonlocal buttons, checkbox_rect
        buttons = []
        screen.fill(BG)
        draw_text(screen, font_title, "Host a Game", WIDTH // 2, 55, WHITE, center=True)
        # Show which game (menu is ready for other games later)
        game_label = "Checkers"
        for g in AVAILABLE_GAMES:
            if g["id"] == selected_game:
                game_label = g["label"]
                break
        draw_text(screen, font_med, f"Game: {game_label}", WIDTH // 2, 95, (120, 200, 140), center=True)

        if selected_game == "uno":
            draw_text(screen, font_big, "LAN UNO — 2 players", WIDTH // 2, 180, WHITE, center=True)
            lines = [
                "Each player only sees their own cards.",
                "Drag a card onto the discard pile to play.",
                "Click the draw pile if you cannot (or choose not to) play.",
                "Wild cards: pick a color after playing.",
                "Host deals and is the rules authority.",
            ]
            yy = 230
            for line in lines:
                draw_text(screen, font_med, line, WIDTH // 2, yy, (190, 195, 200), center=True)
                yy += 32
            bw, bh = 260, 50
            start_rect = pygame.Rect((WIDTH - bw) // 2, 430, bw, bh)
            draw_button(screen, font_big, start_rect, "Start Hosting", (40, 130, 70))
            buttons.append((start_rect, "start_host"))
            back_rect = pygame.Rect((WIDTH - bw) // 2, 500, bw, bh)
            draw_button(screen, font_big, back_rect, "Back", (90, 90, 95))
            buttons.append((back_rect, "back"))
            if last_net_error:
                draw_text(screen, font_small, last_net_error, WIDTH // 2, 580, (220, 80, 80), center=True)
            return

        if selected_game == "cribbage":
            draw_text(screen, font_big, "LAN CRIBBAGE — 2 players", WIDTH // 2, 170, WHITE, center=True)
            lines = [
                "Race to 121. Host is first dealer.",
                "Each gets 6 cards — discard 2 to the crib.",
                "Pegging: play cards up to 31 (pairs, runs, 15s).",
                "Then score hands + crib (the show).",
                "Private hands until the show. Host is rules authority.",
            ]
            yy = 220
            for line in lines:
                draw_text(screen, font_med, line, WIDTH // 2, yy, (190, 195, 200), center=True)
                yy += 32
            bw, bh = 260, 50
            start_rect = pygame.Rect((WIDTH - bw) // 2, 420, bw, bh)
            draw_button(screen, font_big, start_rect, "Start Hosting", (40, 130, 70))
            buttons.append((start_rect, "start_host"))
            back_rect = pygame.Rect((WIDTH - bw) // 2, 490, bw, bh)
            draw_button(screen, font_big, back_rect, "Back", (90, 90, 95))
            buttons.append((back_rect, "back"))
            if last_net_error:
                draw_text(screen, font_small, last_net_error, WIDTH // 2, 570, (220, 80, 80), center=True)
            return

        # Color pickers (Checkers)
        draw_text(screen, font_big, "Your color (bottom)", 120, 120, WHITE)
        sw = 58
        for i, (name, rgb) in enumerate(PALETTE):
            x = 80 + i * (sw + 18)
            draw_color_swatch(screen, x, 150, sw, rgb, name, i == host_color_idx, font_small)

        draw_text(screen, font_big, "Opponent color (top)", 120, 250, WHITE)
        for i, (name, rgb) in enumerate(PALETTE):
            x = 80 + i * (sw + 18)
            draw_color_swatch(screen, x, 280, sw, rgb, name, i == opp_color_idx, font_small)

        # Force jumps checkbox
        cy = 390
        checkbox_rect = pygame.Rect(120, cy, 26, 26)
        pygame.draw.rect(screen, (200, 200, 200), checkbox_rect, border_radius=3)
        if force_jumps:
            pygame.draw.rect(screen, (30, 160, 60), checkbox_rect.inflate(-6, -6), border_radius=2)
        draw_text(screen, font_med, "Force jumps when able (mandatory captures)", 160, cy + 4, WHITE)

        # Start button
        bw, bh = 260, 50
        start_rect = pygame.Rect((WIDTH - bw) // 2, 470, bw, bh)
        draw_button(screen, font_big, start_rect, "Start Hosting", (40, 130, 70))
        buttons.append((start_rect, "start_host"))

        back_rect = pygame.Rect((WIDTH - bw) // 2, 535, bw, bh)
        draw_button(screen, font_big, back_rect, "Back", (90, 90, 95))
        buttons.append((back_rect, "back"))

        if last_net_error:
            draw_text(screen, font_small, last_net_error, WIDTH // 2, 600, (220, 80, 80), center=True)

    def draw_join_setup():
        nonlocal buttons, input_active
        buttons = []
        screen.fill(BG)
        draw_text(screen, font_title, "Join a Game", WIDTH // 2, 55, WHITE, center=True)

        draw_text(screen, font_big, "Enter Host IP Address", WIDTH // 2, 140, WHITE, center=True)

        # IP input box
        ip_rect = pygame.Rect(WIDTH // 2 - 160, 180, 320, 44)
        pygame.draw.rect(screen, (50, 54, 60) if not input_active else (65, 70, 80), ip_rect, border_radius=6)
        pygame.draw.rect(screen, ACCENT if input_active else (90, 90, 95), ip_rect, width=2, border_radius=6)
        draw_text(screen, font_big, connect_ip, ip_rect.centerx, ip_rect.centery, WHITE, center=True)

        # Connect
        bw, bh = 240, 50
        conn_rect = pygame.Rect((WIDTH - bw) // 2, 260, bw, bh)
        draw_button(screen, font_big, conn_rect, "Connect", (55, 100, 160))
        buttons.append((conn_rect, "connect"))

        back_rect = pygame.Rect((WIDTH - bw) // 2, 325, bw, bh)
        draw_button(screen, font_big, back_rect, "Back", (90, 90, 95))
        buttons.append((back_rect, "back"))

        draw_text(screen, font_small, "Ask the host for their IP (shown on their screen).", WIDTH//2, 420, (180,180,180), center=True)
        draw_text(screen, font_small, "Both computers must be on the same WiFi/LAN.", WIDTH//2, 442, (180,180,180), center=True)

        if last_net_error:
            draw_text(screen, font_small, last_net_error, WIDTH // 2, 490, (220, 80, 80), center=True)

    def draw_hosting_screen():
        screen.fill(BG)
        draw_text(screen, font_title, "Waiting for Opponent...", WIDTH // 2, 120, WHITE, center=True)

        ip = get_local_ip()
        draw_text(screen, font_big, f"Your IP:  {ip}", WIDTH // 2, 200, (120, 220, 140), center=True)
        draw_text(screen, font_med, f"Port: {PORT}", WIDTH // 2, 235, (170, 170, 170), center=True)

        draw_text(screen, font_med, "Tell your son this IP address.", WIDTH // 2, 300, (200, 200, 200), center=True)
        draw_text(screen, font_med, "He should choose 'Join Game' and enter it.", WIDTH // 2, 330, (200, 200, 200), center=True)

        # Cancel
        bw, bh = 220, 46
        cancel = pygame.Rect((WIDTH - bw) // 2, 420, bw, bh)
        draw_button(screen, font_big, cancel, "Cancel", (140, 70, 70))
        # store for click
        nonlocal buttons
        buttons = [(cancel, "cancel_host")]

        if last_net_error:
            draw_text(screen, font_small, last_net_error, WIDTH // 2, 500, (220, 100, 100), center=True)

    def draw_joining_screen():
        screen.fill(BG)
        if sock and not connecting:
            draw_text(screen, font_title, "Connected!", WIDTH // 2, 180, WHITE, center=True)
            draw_text(screen, font_med, "Waiting for host to start the game...", WIDTH // 2, 240, (180, 200, 220), center=True)
        else:
            draw_text(screen, font_title, "Connecting...", WIDTH // 2, 180, WHITE, center=True)
            draw_text(screen, font_med, f"To {connect_ip}:{PORT}", WIDTH // 2, 240, (180, 200, 220), center=True)

        bw, bh = 220, 46
        cancel = pygame.Rect((WIDTH - bw) // 2, 340, bw, bh)
        draw_button(screen, font_big, cancel, "Cancel", (140, 70, 70))
        nonlocal buttons
        buttons = [(cancel, "cancel_join")]

        if last_net_error:
            draw_text(screen, font_small, last_net_error, WIDTH // 2, 420, (220, 100, 100), center=True)

    def draw_play_screen():
        screen.fill(BG)

        # Side panel
        pygame.draw.rect(screen, PANEL_BG, (BOARD_X + BOARD_PX + 20, 40, 240, HEIGHT - 80), border_radius=8)

        # Title
        draw_text(screen, font_big, "LAN Checkers", BOARD_X + BOARD_PX + 140, 70, WHITE, center=True)

        # Player boxes
        my_col = colors[my_player]
        opp_col = colors[1 - my_player]
        my_name = "You" if my_player == 0 else "You (joined)"
        opp_name = "Opponent"

        # You
        yb = 110
        pygame.draw.rect(screen, (55, 60, 68), (BOARD_X + BOARD_PX + 35, yb, 210, 70), border_radius=6)
        draw_piece(screen, BOARD_X + BOARD_PX + 65, yb + 35, 22, my_col, False)
        draw_text(screen, font_med, my_name, BOARD_X + BOARD_PX + 95, yb + 22, WHITE)
        draw_text(screen, font_small, f"Pieces: {count_pieces(board, my_player)}", BOARD_X + BOARD_PX + 95, yb + 45, (190, 190, 190))

        # Opponent
        yb = 195
        pygame.draw.rect(screen, (55, 60, 68), (BOARD_X + BOARD_PX + 35, yb, 210, 70), border_radius=6)
        draw_piece(screen, BOARD_X + BOARD_PX + 65, yb + 35, 22, opp_col, False)
        draw_text(screen, font_med, opp_name, BOARD_X + BOARD_PX + 95, yb + 22, WHITE)
        draw_text(screen, font_small, f"Pieces: {count_pieces(board, 1 - my_player)}", BOARD_X + BOARD_PX + 95, yb + 45, (190, 190, 190))

        # Turn / rules
        yb = 290
        turn_txt = "YOUR TURN" if is_my_turn() else "OPPONENT'S TURN"
        turn_col = (80, 220, 120) if is_my_turn() else (220, 180, 80)
        draw_text(screen, font_big, turn_txt, BOARD_X + BOARD_PX + 140, yb, turn_col, center=True)

        fj = "Jumps are MANDATORY" if force_jumps else "Jumps are OPTIONAL"
        draw_text(screen, font_small, fj, BOARD_X + BOARD_PX + 140, yb + 30, (170, 170, 170), center=True)

        # Legend
        draw_text(screen, font_small, "Click piece -> click square", BOARD_X + BOARD_PX + 140, yb + 70, (150, 150, 150), center=True)
        draw_text(screen, font_small, "Green rings = legal moves", BOARD_X + BOARD_PX + 140, yb + 90, (150, 150, 150), center=True)
        if is_my_turn() and selected is not None and (jump_chain_active or not force_jumps):
            draw_text(screen, font_small, "More jumps available — click a green or End Turn", BOARD_X + BOARD_PX + 140, yb + 112, (255, 200, 120), center=True)

        # Menu button
        bw, bh = 160, 40
        mrect = pygame.Rect(BOARD_X + BOARD_PX + 55, HEIGHT - 120, bw, bh)
        draw_button(screen, font_med, mrect, "Main Menu", (130, 70, 70))
        nonlocal buttons
        buttons = [(mrect, "menu")]

        # End Turn button (only during jump continuation on your turn) — use this to stop
        # after a jump (incl. one that promoted to king) instead of being forced to continue.
        if is_my_turn() and selected is not None and (jump_chain_active or not force_jumps):
            et_rect = pygame.Rect(BOARD_X + BOARD_PX + 55, HEIGHT - 170, bw, bh)
            draw_button(screen, font_med, et_rect, "End Turn (skip jumps)", (200, 140, 40))
            buttons.append((et_rect, "end_turn"))

        # Draw board + pieces
        draw_board(screen, board, colors, selected, legal_actions)

        # Top status bar
        pygame.draw.rect(screen, (25, 27, 32), (0, 0, WIDTH, 60))
        status = f"{'You' if is_my_turn() else 'Opponent'} to move  |  {'Mandatory jumps' if force_jumps else 'Free moves'}"
        draw_text(screen, font_med, status, 60, 22, (210, 210, 210))

    def draw_gameover_screen():
        screen.fill(BG)
        draw_board(screen, board, colors, None, [])  # final position

        # Overlay panel
        ov = pygame.Rect(WIDTH // 2 - 200, 140, 400, 280)
        pygame.draw.rect(screen, (35, 38, 45), ov, border_radius=12)
        pygame.draw.rect(screen, (80, 80, 90), ov, width=2, border_radius=12)

        you_won = (winner == my_player)
        title = "YOU WIN!" if you_won else "OPPONENT WINS"
        tcol = (80, 220, 100) if you_won else (220, 90, 90)
        draw_text(screen, font_title, title, WIDTH // 2, 195, tcol, center=True)

        draw_text(screen, font_med, "Game Over", WIDTH // 2, 245, (200, 200, 200), center=True)

        # Buttons
        bw, bh = 180, 46
        again = pygame.Rect(WIDTH // 2 - bw - 12, 310, bw, bh)
        menu = pygame.Rect(WIDTH // 2 + 12, 310, bw, bh)
        draw_button(screen, font_med, again, "Back to Menu", (60, 110, 160))
        draw_button(screen, font_med, menu, "Quit", (140, 60, 60))

        nonlocal buttons
        buttons = [(again, "back_menu"), (menu, "quit")]

    # ----------------------------- MAIN LOOP -----------------------------
    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        hover_buttons = []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Click handling per screen
                if screen_name == "main_menu":
                    # Game list selection first (left side)
                    for rect, gid in game_selections:
                        if rect.collidepoint(mx, my) and gid:
                            selected_game = gid
                            last_net_error = ""  # clear any previous message
                            break

                    # Action buttons (right side)
                    for rect, bid in buttons:
                        if rect.collidepoint(mx, my):
                            if bid == "host":
                                if selected_game in PLAYABLE_GAMES:
                                    screen_name = "host_setup"
                                else:
                                    last_net_error = "Select Checkers, UNO, or Cribbage to host"
                            elif bid == "join":
                                screen_name = "join_setup"
                                input_active = False
                            elif bid == "quit":
                                running = False

                elif screen_name == "host_setup":
                    if selected_game == "checkers":
                        # color swatches
                        sw = 58
                        for i in range(len(PALETTE)):
                            x = 80 + i * (sw + 18)
                            if pygame.Rect(x, 150, sw, sw + 20).collidepoint(mx, my):
                                host_color_idx = i
                                colors[0] = PALETTE[i][1]
                                if host_color_idx == opp_color_idx:
                                    opp_color_idx = (opp_color_idx + 1) % len(PALETTE)
                                    colors[1] = PALETTE[opp_color_idx][1]
                            if pygame.Rect(x, 280, sw, sw + 20).collidepoint(mx, my):
                                opp_color_idx = i
                                colors[1] = PALETTE[i][1]
                                if opp_color_idx == host_color_idx:
                                    host_color_idx = (host_color_idx + 1) % len(PALETTE)
                                    colors[0] = PALETTE[host_color_idx][1]
                        # checkbox
                        if checkbox_rect.collidepoint(mx, my):
                            force_jumps = not force_jumps
                    # buttons
                    for rect, bid in buttons:
                        if rect.collidepoint(mx, my):
                            if bid == "start_host":
                                if selected_game == "checkers":
                                    colors[0] = PALETTE[host_color_idx][1]
                                    colors[1] = PALETTE[opp_color_idx][1]
                                start_hosting()
                            elif bid == "back":
                                screen_name = "main_menu"

                elif screen_name == "join_setup":
                    ip_rect = pygame.Rect(WIDTH // 2 - 160, 180, 320, 44)
                    if ip_rect.collidepoint(mx, my):
                        input_active = True
                    else:
                        input_active = False
                    for rect, bid in buttons:
                        if rect.collidepoint(mx, my):
                            if bid == "connect":
                                do_connect()
                            elif bid == "back":
                                screen_name = "main_menu"
                                input_active = False

                elif screen_name == "playing":
                    if selected_game == "uno" and uno_view is not None:
                        action = uno_view.handle_mouse_down((mx, my))
                        if action:
                            if action.get("action") == "menu":
                                cleanup_net()
                                screen_name = "main_menu"
                                reset_game_state()
                            elif is_host:
                                apply_uno_action(my_player, action)
                            else:
                                if sock:
                                    payload = dict(action)
                                    payload["type"] = "uno_action"
                                    send_msg(sock, payload)
                    elif selected_game == "cribbage" and crib_view is not None:
                        action = crib_view.handle_mouse_down((mx, my))
                        if action:
                            if action.get("action") == "menu":
                                cleanup_net()
                                screen_name = "main_menu"
                                reset_game_state()
                            elif is_host:
                                apply_crib_action(my_player, action)
                            else:
                                if sock:
                                    payload = dict(action)
                                    payload["type"] = "crib_action"
                                    send_msg(sock, payload)
                    else:
                        for rect, bid in buttons:
                            if rect.collidepoint(mx, my):
                                if bid == "menu":
                                    cleanup_net()
                                    screen_name = "main_menu"
                                    reset_game_state()
                                elif bid == "end_turn":
                                    if is_my_turn() and selected is not None and (jump_chain_active or not force_jumps):
                                        end_turn_sequence()
                        handle_click_play(mx, my)

                elif screen_name == "hosting":
                    for rect, bid in buttons:
                        if rect.collidepoint(mx, my) and bid == "cancel_host":
                            cleanup_net()
                            screen_name = "main_menu"

                elif screen_name == "joining":
                    for rect, bid in buttons:
                        if rect.collidepoint(mx, my) and bid == "cancel_join":
                            cleanup_net()
                            screen_name = "main_menu"

                elif screen_name == "gameover":
                    for rect, bid in buttons:
                        if rect.collidepoint(mx, my):
                            if bid == "back_menu":
                                cleanup_net()
                                screen_name = "main_menu"
                                reset_game_state()
                            elif bid == "quit":
                                running = False

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if screen_name == "playing" and selected_game == "uno" and uno_view is not None:
                    action = uno_view.handle_mouse_up((mx, my))
                    if action:
                        if is_host:
                            apply_uno_action(my_player, action)
                        else:
                            if sock:
                                payload = dict(action)
                                payload["type"] = "uno_action"
                                send_msg(sock, payload)
                elif screen_name == "playing" and selected_game == "cribbage" and crib_view is not None:
                    action = crib_view.handle_mouse_up((mx, my))
                    if action:
                        if is_host:
                            apply_crib_action(my_player, action)
                        else:
                            if sock:
                                payload = dict(action)
                                payload["type"] = "crib_action"
                                send_msg(sock, payload)

            elif event.type == pygame.KEYDOWN:
                if screen_name == "join_setup" and input_active:
                    if event.key == pygame.K_RETURN:
                        do_connect()
                    elif event.key == pygame.K_BACKSPACE:
                        connect_ip = connect_ip[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        input_active = False
                    else:
                        ch = event.unicode
                        if ch and (ch.isdigit() or ch == ".") and len(connect_ip) < 21:
                            connect_ip += ch

            elif event.type == pygame.MOUSEMOTION:
                if screen_name == "playing" and selected_game == "uno" and uno_view is not None:
                    uno_view.handle_mouse_motion((mx, my))
                elif screen_name == "playing" and selected_game == "cribbage" and crib_view is not None:
                    crib_view.handle_mouse_motion((mx, my))

        # Network polling every frame
        poll_network()

        # Recompute legals at start of turn if needed (after net moves)
        if screen_name == "playing" and selected_game == "checkers" and not selected and not legal_actions:
            legal_actions, _ = get_all_legal_actions(board, current_player, force_jumps)
            jump_chain_active = False

        # Draw current screen
        buttons = []
        if screen_name == "main_menu":
            draw_main_menu()
        elif screen_name == "host_setup":
            draw_host_setup()
        elif screen_name == "join_setup":
            draw_join_setup()
        elif screen_name == "hosting":
            draw_hosting_screen()
        elif screen_name == "joining":
            draw_joining_screen()
        elif screen_name == "playing":
            if selected_game == "uno" and uno_view is not None:
                uno_view.draw(screen)
            elif selected_game == "uno":
                screen.fill((28, 70, 48))
                draw_text(screen, font_big, "Starting UNO...", WIDTH // 2, HEIGHT // 2, WHITE, center=True)
            elif selected_game == "cribbage" and crib_view is not None:
                crib_view.draw(screen)
            elif selected_game == "cribbage":
                screen.fill((25, 55, 40))
                draw_text(screen, font_big, "Starting Cribbage...", WIDTH // 2, HEIGHT // 2, WHITE, center=True)
            else:
                draw_play_screen()
        elif screen_name == "gameover":
            if selected_game in ("uno", "cribbage") and (
                (selected_game == "uno" and uno_view is not None)
                or (selected_game == "cribbage" and crib_view is not None)
            ):
                if selected_game == "uno" and uno_view is not None:
                    uno_view.draw(screen)
                elif crib_view is not None:
                    crib_view.draw(screen)
                ov = pygame.Rect(WIDTH // 2 - 200, 140, 400, 200)
                pygame.draw.rect(screen, (35, 38, 45), ov, border_radius=12)
                pygame.draw.rect(screen, (80, 80, 90), ov, width=2, border_radius=12)
                you_won = (winner == my_player)
                title = "YOU WIN!" if you_won else "OPPONENT WINS"
                tcol = (80, 220, 100) if you_won else (220, 90, 90)
                draw_text(screen, font_title, title, WIDTH // 2, 195, tcol, center=True)
                bw, bh = 180, 46
                again = pygame.Rect(WIDTH // 2 - bw - 12, 250, bw, bh)
                menu = pygame.Rect(WIDTH // 2 + 12, 250, bw, bh)
                draw_button(screen, font_med, again, "Back to Menu", (60, 110, 160))
                draw_button(screen, font_med, menu, "Quit", (140, 60, 60))
                buttons = [(again, "back_menu"), (menu, "quit")]
            else:
                draw_gameover_screen()

        # Hover effect for buttons (simple visual)
        for rect, _ in buttons:
            if rect.collidepoint(mx, my):
                # re-draw slightly brighter? but draw already handles in some, skip complex
                pass

        pygame.display.flip()
        clock.tick(FPS)

    # Cleanup on exit
    cleanup_net()
    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
