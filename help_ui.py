#!/usr/bin/env python3
"""
Scrollable FAQ / How-to-Play help overlay for LAN Games.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

WIDTH, HEIGHT = 920, 720

# Full rules + FAQ text for each playable game
HELP_CONTENT: Dict[str, Dict[str, object]] = {
    "checkers": {
        "title": "Checkers — Rules & FAQ",
        "sections": [
            ("How to start (LAN)", [
                "1. Both PCs on the same home Wi‑Fi.",
                "2. Host: select Checkers → Host Game → pick colors → Start Hosting.",
                "3. Share the IP address shown on the host screen.",
                "4. Guest: Join Game → type that IP → Connect.",
                "5. Bottom of the board = Host. Top = Guest.",
            ]),
            ("Basic rules", [
                "• Play on the dark squares only.",
                "• Men move diagonally forward one square.",
                "• Capture by jumping over an opponent into an empty square.",
                "• Multi‑jumps: keep jumping with the same piece if possible.",
                "• Reach the far side to become a King (golden crown).",
                "• Kings move and jump diagonally forward or backward.",
                "• You win when the opponent has no pieces or no legal moves.",
            ]),
            ("Force jumps option", [
                "• Host can check “Force jumps when able” (default ON).",
                "• ON = if a capture exists, you must jump (standard rules).",
                "• OFF = you may make a simple move even when jumps exist.",
                "• After a jump, if more jumps are possible, green squares show.",
                "• Use “End Turn (skip jumps)” to stop a multi‑jump when allowed.",
            ]),
            ("Controls", [
                "• Click your piece (yellow ring) to select it.",
                "• Click a green‑ringed square to move or jump there.",
                "• Only legal moves are highlighted.",
                "• Main Menu disconnects and returns to the hub.",
            ]),
            ("FAQ", [
                "Q: Connect fails?",
                "A: Same Wi‑Fi, correct IP, allow Windows Firewall (private network).",
                "Q: Port?",
                "A: 54321 — no router port‑forward needed on a home LAN.",
                "Q: Who is the rules authority?",
                "A: The host PC. The board is host‑authoritative.",
                "Q: Play again?",
                "A: Back to Menu, then host/join again.",
            ]),
        ],
    },
    "uno": {
        "title": "UNO — Rules & FAQ",
        "sections": [
            ("How to start (LAN)", [
                "1. Both PCs on the same home Wi‑Fi.",
                "2. Host: select UNO → Host Game → Start Hosting → share IP.",
                "3. Guest: Join Game → enter IP → Connect.",
                "4. Host deals. You only ever see YOUR hand.",
            ]),
            ("Goal", [
                "• Be the first to play all cards from your hand.",
                "• Match the discard pile by color OR number/symbol.",
                "• Wild cards can be played (with restrictions for Wild +4).",
            ]),
            ("Card types", [
                "• Number cards 0–9 in Red, Yellow, Green, Blue.",
                "• Skip — opponent loses their next turn.",
                "• Reverse — with 2 players this acts like Skip.",
                "• Draw Two (+2) — opponent draws 2 and is skipped.",
                "• Wild — you choose the next color.",
                "• Wild Draw Four (+4) — choose color; opponent draws 4 and skips.",
                "  Wild +4 only if you have no card of the current color.",
            ]),
            ("How to play a turn", [
                "• Legal cards are outlined in green.",
                "• Drag a legal card onto the DISCARD pile (center‑right).",
                "• Or click DRAW to take one card from the draw pile.",
                "• If the drawn card is playable, play it or press Pass.",
                "• After Wild / Wild +4, pick a color on the overlay.",
            ]),
            ("UNO! and Catch", [
                "• When you have 1 card left, press UNO!",
                "• If opponent has 1 card and forgot UNO, press Catch UNO.",
                "• A successful catch makes them draw 2 cards.",
            ]),
            ("Privacy & networking", [
                "• Opponent only sees card backs + how many cards they hold.",
                "• Host is the rules authority (validates every play).",
                "• Port 54321. Same Wi‑Fi required.",
            ]),
            ("FAQ", [
                "Q: Card won’t play?",
                "A: It must match color or symbol, or be a legal wild.",
                "Q: Why can’t I play Wild +4?",
                "A: You still have a card of the current color.",
                "Q: Draw pile empty?",
                "A: Discard pile (except top) is reshuffled automatically.",
                "Q: Graphics look simple?",
                "A: Cards are custom‑drawn (not official brand art) for home use.",
            ]),
        ],
    },
    "cribbage": {
        "title": "Cribbage — Rules & FAQ",
        "sections": [
            ("How to start (LAN)", [
                "1. Both PCs on the same home Wi‑Fi.",
                "2. Host: select Cribbage → Host Game → Start Hosting → share IP.",
                "3. Guest joins. Host is the first dealer; dealer switches each hand.",
                "4. First player to 121 points wins.",
            ]),
            ("Overview of a hand", [
                "1. DEAL — each player gets 6 cards.",
                "2. DISCARD — each puts 2 cards into the crib (dealer’s extra hand).",
                "3. STARTER — a card is cut; Jack starter = dealer +2 (“his heels”).",
                "4. PEGGING — play cards to a running count of at most 31.",
                "5. THE SHOW — score hands, then the crib.",
                "6. NEXT HAND — dealer switches and a new hand is dealt.",
            ]),
            ("Discard phase", [
                "• Click two cards (gold outline) then press Confirm 2 to Crib.",
                "• Those cards become the crib (face‑down until the show).",
                "• You keep 4 cards for pegging and for your hand score.",
            ]),
            ("Pegging (play)", [
                "• Non‑dealer (pone) leads first.",
                "• Play a card so count + card value ≤ 31.",
                "  (A=1, 2–10 face value, J/Q/K=10).",
                "• Score during pegging:",
                "  – Exactly 15 → 2 points",
                "  – Exactly 31 → 2 points",
                "  – Pair / three / four of a kind → 2 / 6 / 12",
                "  – Run of 3+ (any order in the last cards) → length in points",
                "  – Last card / go when opponent cannot play → usually 1",
                "• If you cannot play, press GO (when shown).",
                "• When neither can play, count resets to 0 and play continues.",
                "• Click or short‑click a legal (green) card, or drag to the play area.",
            ]),
            ("The show (scoring hands)", [
                "• Press Next Score for each step:",
                "  1) Non‑dealer’s 4 cards + starter",
                "  2) Dealer’s 4 cards + starter",
                "  3) Crib’s 4 cards + starter (dealer scores this)",
                "• Hand points include:",
                "  – Fifteens (any combo summing to 15) = 2 each",
                "  – Pairs / trips / quads",
                "  – Runs of 3+",
                "  – Flush (4 same suit in hand; +1 if starter matches)",
                "  – Crib flush only if all 5 same suit",
                "  – Nobs: Jack in hand matching starter suit = 1",
            ]),
            ("Privacy", [
                "• During discard and pegging you only see your own cards.",
                "• Opponent shows card backs + count.",
                "• Hands and crib are revealed during the show.",
            ]),
            ("FAQ", [
                "Q: Who owns the crib?",
                "A: Always the dealer for that hand.",
                "Q: When does the game end?",
                "A: As soon as either player reaches 121 (can be mid‑hand).",
                "Q: Connect issues?",
                "A: Same Wi‑Fi, correct IP, allow Firewall on private networks.",
                "Q: Who enforces rules?",
                "A: The host PC (host‑authoritative).",
            ]),
        ],
    },
    "lan": {
        "title": "LAN Games — General FAQ",
        "sections": [
            ("Playing over your home network", [
                "• Both computers must be on the same Wi‑Fi or wired LAN.",
                "• No internet is required once the app is on each PC.",
                "• Host starts the game; guest joins with the host’s IP.",
                "• Copy the whole Desktop folder (exe + _internal) to the other PC.",
            ]),
            ("Firewall & connection", [
                "• Windows may ask to allow the app — choose Private networks.",
                "• Port used: 54321.",
                "• Find IP: host screen shows it, or use ipconfig (IPv4 Address).",
                "• If join fails: same network, re‑type IP, restart host then join.",
            ]),
            ("Which games are ready?", [
                "• Checkers — full LAN board game.",
                "• UNO — private hands, drag to discard.",
                "• Cribbage — full 2‑player race to 121.",
                "• Chess / Othello / Tic Tac Toe — coming later.",
            ]),
            ("Tips", [
                "• Always host from one PC and join from the other.",
                "• After a game ends, use Back to Menu then host/join again.",
                "• Use Instructions / How to Play on each game for full rules.",
            ]),
        ],
    },
}


def _flatten_lines(game_id: str) -> List[Tuple[str, str]]:
    """Return list of (kind, text) where kind is 'h' heading or 'b' body."""
    data = HELP_CONTENT.get(game_id) or HELP_CONTENT["lan"]
    lines: List[Tuple[str, str]] = []
    lines.append(("title", str(data["title"])))
    lines.append(("b", ""))
    for section_title, bullets in data["sections"]:  # type: ignore
        lines.append(("h", str(section_title)))
        for b in bullets:  # type: ignore
            lines.append(("b", str(b)))
        lines.append(("b", ""))
    lines.append(("b", "— End of help. Scroll up or press Close / Esc. —"))
    return lines


class HelpOverlay:
    """Modal scrollable help window."""

    def __init__(self):
        self.open = False
        self.game_id = "lan"
        self.scroll = 0
        self.dragging_bar = False
        self.drag_offset_y = 0
        self.lines: List[Tuple[str, str]] = []
        self.panel = pygame.Rect(80, 50, WIDTH - 160, HEIGHT - 100)
        self.close_rect = pygame.Rect(0, 0, 0, 0)
        self.track_rect = pygame.Rect(0, 0, 0, 0)
        self.thumb_rect = pygame.Rect(0, 0, 0, 0)
        self.content_h = 0
        self.view_h = 0
        self.fonts: Dict[str, pygame.font.Font] = {}

    def ensure_fonts(self):
        if not self.fonts:
            self.fonts = {
                "title": pygame.font.SysFont("Segoe UI", 28, bold=True),
                "h": pygame.font.SysFont("Segoe UI", 20, bold=True),
                "b": pygame.font.SysFont("Segoe UI", 16),
                "btn": pygame.font.SysFont("Segoe UI", 18, bold=True),
            }

    def show(self, game_id: str):
        self.open = True
        self.game_id = game_id if game_id in HELP_CONTENT else "lan"
        self.scroll = 0
        self.dragging_bar = False
        self.lines = _flatten_lines(self.game_id)

    def hide(self):
        self.open = False
        self.dragging_bar = False

    def _max_scroll(self) -> int:
        return max(0, self.content_h - self.view_h)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return True if event was consumed."""
        if not self.open:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.hide()
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self._max_scroll(), self.scroll - event.y * 36))
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.close_rect.collidepoint(mx, my):
                self.hide()
                return True
            if self.thumb_rect.collidepoint(mx, my):
                self.dragging_bar = True
                self.drag_offset_y = my - self.thumb_rect.y
                return True
            if self.track_rect.collidepoint(mx, my) and self._max_scroll() > 0:
                ratio = (my - self.track_rect.y) / max(1, self.track_rect.h)
                self.scroll = int(ratio * self._max_scroll())
                return True
            # Click outside panel closes
            if not self.panel.collidepoint(mx, my):
                self.hide()
                return True
            return True  # eat clicks while open
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_bar:
                self.dragging_bar = False
                return True
        if event.type == pygame.MOUSEMOTION and self.dragging_bar:
            my = event.pos[1]
            track = self.track_rect
            thumb_h = self.thumb_rect.h
            y = my - self.drag_offset_y
            y = max(track.y, min(track.bottom - thumb_h, y))
            if track.h - thumb_h > 0:
                ratio = (y - track.y) / (track.h - thumb_h)
                self.scroll = int(ratio * self._max_scroll())
            return True
        return True  # block underlying UI while help open (keys except esc already handled)

    def draw(self, screen: pygame.Surface):
        if not self.open:
            return
        self.ensure_fonts()
        # Dim background
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        panel = self.panel
        # Panel body with soft border (16-bit-ish polished UI)
        pygame.draw.rect(screen, (28, 32, 42), panel, border_radius=14)
        pygame.draw.rect(screen, (70, 110, 170), panel, width=3, border_radius=14)
        pygame.draw.rect(screen, (50, 55, 70), panel.inflate(-8, -8), width=1, border_radius=12)

        # Header bar
        header = pygame.Rect(panel.x, panel.y, panel.w, 52)
        pygame.draw.rect(screen, (40, 55, 85), header, border_top_left_radius=14, border_top_right_radius=14)
        title = str((HELP_CONTENT.get(self.game_id) or HELP_CONTENT["lan"])["title"])
        timg = self.fonts["title"].render(title, True, (240, 245, 255))
        screen.blit(timg, (panel.x + 20, panel.y + 12))

        self.close_rect = pygame.Rect(panel.right - 110, panel.y + 10, 90, 34)
        pygame.draw.rect(screen, (150, 60, 60), self.close_rect, border_radius=8)
        pygame.draw.rect(screen, (220, 200, 200), self.close_rect, 1, border_radius=8)
        cimg = self.fonts["btn"].render("Close", True, (255, 255, 255))
        screen.blit(cimg, cimg.get_rect(center=self.close_rect.center))

        # Content clip region
        pad = 20
        content_rect = pygame.Rect(panel.x + pad, panel.y + 60, panel.w - pad * 2 - 22, panel.h - 80)
        self.view_h = content_rect.h

        # Measure content height
        line_gap = 4
        y_cursor = 0
        measured: List[Tuple[str, str, int]] = []  # kind, text, y
        for kind, text in self.lines:
            if kind == "title":
                h = 32
            elif kind == "h":
                h = 28
            else:
                # wrap body
                h = self._text_height(text, content_rect.w - 8, self.fonts["b"]) + line_gap
            measured.append((kind, text, y_cursor))
            y_cursor += h
        self.content_h = y_cursor + 20
        self.scroll = max(0, min(self._max_scroll(), self.scroll))

        # Draw clipped content
        clip_prev = screen.get_clip()
        screen.set_clip(content_rect)
        for kind, text, ly in measured:
            draw_y = content_rect.y + ly - self.scroll
            if draw_y > content_rect.bottom or draw_y + 40 < content_rect.y:
                continue
            if kind == "title":
                img = self.fonts["title"].render(text, True, (255, 230, 140))
                screen.blit(img, (content_rect.x, draw_y))
            elif kind == "h":
                img = self.fonts["h"].render(text, True, (120, 190, 255))
                screen.blit(img, (content_rect.x, draw_y))
                # underline
                pygame.draw.line(
                    screen,
                    (70, 100, 140),
                    (content_rect.x, draw_y + 24),
                    (content_rect.x + min(280, content_rect.w), draw_y + 24),
                    1,
                )
            else:
                self._blit_wrapped(screen, text, content_rect.x, draw_y, content_rect.w - 8, self.fonts["b"], (220, 225, 230))
        screen.set_clip(clip_prev)

        # Scrollbar
        self.track_rect = pygame.Rect(panel.right - 28, content_rect.y, 10, content_rect.h)
        pygame.draw.rect(screen, (20, 22, 28), self.track_rect, border_radius=5)
        if self._max_scroll() > 0:
            thumb_h = max(28, int(content_rect.h * content_rect.h / self.content_h))
            ratio = self.scroll / self._max_scroll()
            thumb_y = content_rect.y + int((content_rect.h - thumb_h) * ratio)
            self.thumb_rect = pygame.Rect(self.track_rect.x, thumb_y, self.track_rect.w, thumb_h)
            pygame.draw.rect(screen, (100, 150, 210), self.thumb_rect, border_radius=5)
        else:
            self.thumb_rect = pygame.Rect(0, 0, 0, 0)

        # Footer hint
        hint = self.fonts["b"].render("Mouse wheel to scroll  ·  Esc or Close to exit", True, (150, 160, 170))
        screen.blit(hint, (panel.x + 20, panel.bottom - 28))

    def _text_height(self, text: str, max_w: int, font: pygame.font.Font) -> int:
        if not text:
            return 10
        words = text.split(" ")
        lines = 1
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= max_w:
                cur = test
            else:
                lines += 1
                cur = w
        return lines * (font.get_height() + 2)

    def _blit_wrapped(self, screen, text, x, y, max_w, font, color):
        if not text:
            return
        words = text.split(" ")
        cur = ""
        cy = y
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= max_w:
                cur = test
            else:
                if cur:
                    screen.blit(font.render(cur, True, color), (x, cy))
                    cy += font.get_height() + 2
                cur = w
        if cur:
            screen.blit(font.render(cur, True, color), (x, cy))
