#!/usr/bin/env python3
"""
LAN UNO — host-authoritative multiplayer card game.

Each client only receives their own hand. Cards are drawn procedurally to look
like real plastic playing cards (original art; not official UNO trademarks).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pygame

# ---- Layout (matches main window 920x720) ----
WIDTH, HEIGHT = 920, 720
CARD_W, CARD_H = 78, 118
CARD_W_SM, CARD_H_SM = 56, 84

COLORS = ("R", "Y", "G", "B")
COLOR_RGB = {
    "R": (210, 45, 45),
    "Y": (230, 190, 30),
    "G": (40, 160, 70),
    "B": (40, 100, 210),
}
COLOR_NAME = {"R": "Red", "Y": "Yellow", "G": "Green", "B": "Blue"}

# Kinds: 0-9, skip, reverse, draw2, wild, wild4
Kind = str


@dataclass
class Card:
    cid: int
    color: Optional[str]  # None for wilds
    kind: Kind  # "0"-"9", "skip", "reverse", "draw2", "wild", "wild4"

    def to_dict(self) -> Dict[str, Any]:
        return {"cid": self.cid, "color": self.color, "kind": self.kind}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Card":
        return Card(int(d["cid"]), d.get("color"), str(d["kind"]))

    def label(self) -> str:
        if self.kind == "skip":
            return "SKIP"
        if self.kind == "reverse":
            return "REV"
        if self.kind == "draw2":
            return "+2"
        if self.kind == "wild":
            return "WILD"
        if self.kind == "wild4":
            return "+4"
        return self.kind

    def is_wild(self) -> bool:
        return self.kind in ("wild", "wild4")


def build_deck() -> List[Card]:
    """Classic 108-card deck."""
    cards: List[Card] = []
    cid = 0
    for color in COLORS:
        cards.append(Card(cid, color, "0"))
        cid += 1
        for n in range(1, 10):
            for _ in range(2):
                cards.append(Card(cid, color, str(n)))
                cid += 1
        for kind in ("skip", "reverse", "draw2"):
            for _ in range(2):
                cards.append(Card(cid, color, kind))
                cid += 1
    for _ in range(4):
        cards.append(Card(cid, None, "wild"))
        cid += 1
    for _ in range(4):
        cards.append(Card(cid, None, "wild4"))
        cid += 1
    return cards


# ---- Surface cache ----
_face_cache: Dict[Tuple[Any, ...], pygame.Surface] = {}
_back_cache: Dict[Tuple[int, int], pygame.Surface] = {}


def _rounded_rect(surf: pygame.Surface, rect: pygame.Rect, color, radius: int = 10):
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def render_card_face(card: Card, w: int = CARD_W, h: int = CARD_H) -> pygame.Surface:
    key = (card.cid, card.color, card.kind, w, h)
    if key in _face_cache:
        return _face_cache[key]

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Shadow-ish outer dark edge
    _rounded_rect(surf, pygame.Rect(0, 0, w, h), (20, 20, 25), 12)
    # White body
    _rounded_rect(surf, pygame.Rect(2, 2, w - 4, h - 4), (248, 246, 240), 11)

    # Color oval / wild multicolor
    cx, cy = w // 2, h // 2
    oval = pygame.Rect(10, 18, w - 20, h - 36)
    if card.is_wild():
        # Four-color diamond
        mid_x, mid_y = cx, cy
        quads = [
            ((mid_x, 22), (w - 12, mid_y), (mid_x, mid_y), (12, mid_y), COLOR_RGB["R"]),
            ((mid_x, 22), (w - 12, mid_y), (mid_x, mid_y), (mid_x, mid_y), COLOR_RGB["Y"]),
        ]
        # Draw four triangles from center
        pts = {
            "R": [(cx, 20), (w - 12, cy), (cx, cy)],
            "Y": [(cx, 20), (12, cy), (cx, cy)],
            "G": [(cx, h - 20), (w - 12, cy), (cx, cy)],
            "B": [(cx, h - 20), (12, cy), (cx, cy)],
        }
        # Fix: four proper wedges
        pygame.draw.polygon(surf, COLOR_RGB["R"], [(cx, cy), (cx, 18), (w - 10, cy)])
        pygame.draw.polygon(surf, COLOR_RGB["Y"], [(cx, cy), (cx, 18), (10, cy)])
        pygame.draw.polygon(surf, COLOR_RGB["G"], [(cx, cy), (cx, h - 18), (w - 10, cy)])
        pygame.draw.polygon(surf, COLOR_RGB["B"], [(cx, cy), (cx, h - 18), (10, cy)])
        pygame.draw.ellipse(surf, (248, 246, 240), pygame.Rect(cx - 18, cy - 22, 36, 44))
    else:
        col = COLOR_RGB.get(card.color or "R", (180, 180, 180))
        pygame.draw.ellipse(surf, col, oval)
        # Inner highlight
        hi = pygame.Rect(oval.x + 8, oval.y + 6, oval.w - 16, oval.h // 3)
        pygame.draw.ellipse(surf, tuple(min(255, c + 40) for c in col), hi)

    # Text
    font_big = pygame.font.SysFont("Segoe UI", max(18, h // 4), bold=True)
    font_sm = pygame.font.SysFont("Segoe UI", max(12, h // 7), bold=True)
    label = card.label()
    text_col = (25, 25, 30) if card.kind == "Y" or (card.color == "Y") else (255, 255, 255)
    if card.is_wild():
        text_col = (30, 30, 35)

    if card.kind in ("skip", "reverse"):
        # Symbol-ish
        if card.kind == "skip":
            # Circle with slash
            pygame.draw.circle(surf, text_col, (cx, cy), h // 7, width=3)
            pygame.draw.line(surf, text_col, (cx - h // 9, cy + h // 9), (cx + h // 9, cy - h // 9), 3)
        else:
            # Two curved arrows approximated as arcs + heads
            pygame.draw.arc(surf, text_col, pygame.Rect(cx - 16, cy - 14, 28, 28), 0.4, 2.8, 3)
            pygame.draw.arc(surf, text_col, pygame.Rect(cx - 12, cy - 10, 28, 28), 3.5, 5.9, 3)
            pygame.draw.polygon(surf, text_col, [(cx + 14, cy - 10), (cx + 6, cy - 16), (cx + 8, cy - 4)])
            pygame.draw.polygon(surf, text_col, [(cx - 14, cy + 10), (cx - 6, cy + 16), (cx - 8, cy + 4)])
    else:
        img = font_big.render(label, True, text_col)
        surf.blit(img, img.get_rect(center=(cx, cy)))

    # Corner pips
    pip = font_sm.render(label if len(label) <= 3 else label[:2], True, COLOR_RGB.get(card.color or "R", (80, 80, 80)) if not card.is_wild() else (80, 80, 90))
    if card.is_wild():
        pip = font_sm.render(label[:2], True, (60, 60, 70))
    surf.blit(pip, (8, 6))
    pip2 = pygame.transform.rotate(pip, 180)
    surf.blit(pip2, (w - pip2.get_width() - 8, h - pip2.get_height() - 6))

    # Gloss
    gloss = pygame.Surface((w - 10, h // 4), pygame.SRCALPHA)
    gloss.fill((255, 255, 255, 35))
    surf.blit(gloss, (5, 6))

    _face_cache[key] = surf
    return surf


def render_card_back(w: int = CARD_W, h: int = CARD_H) -> pygame.Surface:
    key = (w, h)
    if key in _back_cache:
        return _back_cache[key]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    _rounded_rect(surf, pygame.Rect(0, 0, w, h), (15, 15, 20), 12)
    _rounded_rect(surf, pygame.Rect(2, 2, w - 4, h - 4), (25, 55, 120), 11)
    _rounded_rect(surf, pygame.Rect(8, 10, w - 16, h - 20), (35, 70, 145), 8)
    # Pattern
    for i in range(4):
        for j in range(5):
            x = 14 + i * ((w - 28) // 3)
            y = 16 + j * ((h - 32) // 4)
            pygame.draw.circle(surf, (50, 95, 175), (x, y), 3)
    font = pygame.font.SysFont("Segoe UI", max(14, h // 7), bold=True)
    t = font.render("LAN", True, (220, 230, 255))
    surf.blit(t, t.get_rect(center=(w // 2, h // 2 - 8)))
    t2 = font.render("UNO", True, (255, 220, 80))
    surf.blit(t2, t2.get_rect(center=(w // 2, h // 2 + 12)))
    _back_cache[key] = surf
    return surf


class UnoMatch:
    """Host-side authoritative UNO match (2 players)."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed if seed is not None else time.time_ns())
        self.deck: List[Card] = []
        self.discard: List[Card] = []
        self.hands: List[List[Card]] = [[], []]
        self.current: int = 0
        self.direction: int = 1  # +1 or -1
        self.active_color: Optional[str] = None
        self.awaiting_color: bool = False
        self.color_chooser: Optional[int] = None
        self.winner: Optional[int] = None
        self.message: str = ""
        self.drew_this_turn: Optional[Card] = None  # must play this or pass
        self.uno_called: Dict[int, bool] = {0: False, 1: False}
        self.penalty_pending: int = 0  # draws next player must take (before their play)
        self._next_cid = 0

    def start_new_game(self):
        self.deck = build_deck()
        self.rng.shuffle(self.deck)
        self.discard = []
        self.hands = [[], []]
        self.current = 0
        self.direction = 1
        self.active_color = None
        self.awaiting_color = False
        self.color_chooser = None
        self.winner = None
        self.message = "Match started — Host goes first"
        self.drew_this_turn = None
        self.uno_called = {0: False, 1: False}
        self.penalty_pending = 0

        for _ in range(7):
            self.hands[0].append(self.deck.pop())
            self.hands[1].append(self.deck.pop())

        # Flip first non-wild for discard (if wild, keep flipping)
        while self.deck:
            c = self.deck.pop()
            if c.is_wild():
                # reshuffle wilds back later — put under deck
                self.deck.insert(0, c)
                # pick another
                if all(x.is_wild() for x in self.deck):
                    break
                continue
            self.discard.append(c)
            self.active_color = c.color
            # Action cards on start: apply lightly
            if c.kind == "skip":
                self.current = 1  # skip host, guest starts
                self.message = "Opening SKIP — Guest starts"
            elif c.kind == "reverse":
                self.direction *= -1
                self.current = 1  # 2p reverse = skip
                self.message = "Opening REVERSE — Guest starts"
            elif c.kind == "draw2":
                self._give_cards(0, 2)
                self.current = 1
                self.message = "Opening +2 — Host drew 2, Guest starts"
            break

        if not self.discard and self.deck:
            c = self.deck.pop()
            self.discard.append(c)
            self.active_color = c.color or "R"
            if c.is_wild():
                self.awaiting_color = True
                self.color_chooser = 0

    def top(self) -> Optional[Card]:
        return self.discard[-1] if self.discard else None

    def _reshuffle_if_needed(self):
        if self.deck:
            return
        if len(self.discard) <= 1:
            return
        top = self.discard.pop()
        self.deck = self.discard[:]
        self.discard = [top]
        self.rng.shuffle(self.deck)

    def _give_cards(self, player: int, n: int):
        for _ in range(n):
            self._reshuffle_if_needed()
            if not self.deck:
                break
            self.hands[player].append(self.deck.pop())
        self.uno_called[player] = False

    def _next_player(self, from_p: Optional[int] = None) -> int:
        p = self.current if from_p is None else from_p
        return (p + self.direction) % 2

    def _advance(self, skip: bool = False):
        self.drew_this_turn = None
        self.current = self._next_player()
        if skip:
            self.current = self._next_player()

    def effective_color(self) -> Optional[str]:
        return self.active_color

    def can_play(self, card: Card, player: int) -> bool:
        if self.winner is not None:
            return False
        if self.awaiting_color:
            return False
        if player != self.current:
            return False
        if self.drew_this_turn is not None:
            return card.cid == self.drew_this_turn.cid and self._matches(card)
        return self._matches(card)

    def _matches(self, card: Card) -> bool:
        top = self.top()
        if not top:
            return True
        if card.is_wild():
            if card.kind == "wild4":
                # Official-ish: only if no other playable non-wild4
                # We'll enforce on play attempt for wild4
                return True
            return True
        col = self.active_color or top.color
        if card.color == col:
            return True
        if card.kind == top.kind and not top.is_wild():
            return True
        # Match number/symbol on wild color already handled by color
        if top.is_wild() and card.color == self.active_color:
            return True
        return False

    def _has_color_match(self, player: int) -> bool:
        col = self.active_color
        for c in self.hands[player]:
            if not c.is_wild() and c.color == col:
                return True
            if c.kind in ("skip", "reverse", "draw2") and self.top() and c.kind == self.top().kind:
                return True
            if self.top() and not self.top().is_wild() and c.kind == self.top().kind and c.kind.isdigit():
                return True
            if self.top() and not c.is_wild() and c.kind == self.top().kind:
                return True
        return False

    def legal_cards(self, player: int) -> List[Card]:
        return [c for c in self.hands[player] if self.can_play(c, player)]

    def play_card(self, player: int, cid: int) -> Tuple[bool, str]:
        if self.winner is not None:
            return False, "Game over"
        if self.awaiting_color:
            return False, "Choose a color first"
        if player != self.current:
            return False, "Not your turn"

        hand = self.hands[player]
        card = next((c for c in hand if c.cid == cid), None)
        if not card:
            return False, "Card not in hand"
        if not self.can_play(card, player):
            return False, "Illegal card"

        if card.kind == "wild4" and self.drew_this_turn is None:
            # Restrict wild4 if player has a matching color card
            if any(
                (not c.is_wild() and c.color == self.active_color)
                for c in hand
                if c.cid != card.cid
            ):
                return False, "Wild +4 only when you have no matching color"

        hand.remove(card)
        self.discard.append(card)
        self.drew_this_turn = None

        if len(hand) == 1 and not self.uno_called[player]:
            self.message = f"Player {player + 1} has 1 card — call UNO!"
        if len(hand) == 0:
            self.winner = player
            self.message = f"Player {player + 1} wins!"
            return True, "win"

        if card.is_wild():
            self.awaiting_color = True
            self.color_chooser = player
            self.active_color = None
            if card.kind == "wild4":
                self.penalty_pending = 4
            else:
                self.penalty_pending = 0
            self.message = "Choose a color"
            return True, "need_color"

        self.active_color = card.color
        self._resolve_action(card)
        return True, "ok"

    def _resolve_action(self, card: Card):
        """Apply non-wild card effects and advance turn."""
        if card.kind == "skip":
            self.message = "SKIP!"
            self._advance(skip=True)
        elif card.kind == "reverse":
            # 2 players: reverse acts as skip
            self.direction *= -1
            self.message = "REVERSE!"
            self._advance(skip=True)
        elif card.kind == "draw2":
            victim = self._next_player()
            self._give_cards(victim, 2)
            self.message = f"+2 — opponent draws 2"
            self._advance(skip=True)
        else:
            self.message = f"Played {COLOR_NAME.get(card.color or '', '')} {card.label()}"
            self._advance(skip=False)

    def choose_color(self, player: int, color: str) -> Tuple[bool, str]:
        if not self.awaiting_color or self.color_chooser != player:
            return False, "Not choosing color"
        if color not in COLORS:
            return False, "Bad color"
        self.active_color = color
        self.awaiting_color = False
        self.color_chooser = None
        pend = self.penalty_pending
        self.penalty_pending = 0
        if pend:
            victim = self._next_player()
            self._give_cards(victim, pend)
            self.message = f"Color {COLOR_NAME[color]} — opponent draws {pend}"
            self._advance(skip=True)
        else:
            self.message = f"Color set to {COLOR_NAME[color]}"
            self._advance(skip=False)
        return True, "ok"

    def draw_card(self, player: int) -> Tuple[bool, str]:
        if self.winner is not None:
            return False, "Game over"
        if self.awaiting_color:
            return False, "Choose a color first"
        if player != self.current:
            return False, "Not your turn"
        if self.drew_this_turn is not None:
            return False, "Already drew — play it or pass"

        # If you have legal plays, still allow draw (house friendly)
        self._reshuffle_if_needed()
        if not self.deck:
            return False, "Deck empty"
        card = self.deck.pop()
        self.hands[player].append(card)
        self.uno_called[player] = False

        if self._matches(card) and not (
            card.kind == "wild4"
            and any(not c.is_wild() and c.color == self.active_color for c in self.hands[player] if c.cid != card.cid)
        ):
            self.drew_this_turn = card
            self.message = "Drew a playable card — play it or Pass"
            return True, "may_play"
        # Not playable: end turn
        self.message = "Drew a card"
        self._advance(skip=False)
        return True, "drew"

    def pass_after_draw(self, player: int) -> Tuple[bool, str]:
        if player != self.current or self.drew_this_turn is None:
            return False, "Nothing to pass"
        self.drew_this_turn = None
        self.message = "Passed after draw"
        self._advance(skip=False)
        return True, "ok"

    def call_uno(self, player: int) -> Tuple[bool, str]:
        if len(self.hands[player]) == 1:
            self.uno_called[player] = True
            self.message = f"Player {player + 1} called UNO!"
            return True, "ok"
        return False, "You must have exactly 1 card"

    def catch_uno(self, catcher: int, target: int) -> Tuple[bool, str]:
        """If opponent has 1 card and didn't call UNO, they draw 2."""
        if target == catcher:
            return False, "Invalid"
        if len(self.hands[target]) == 1 and not self.uno_called[target]:
            self._give_cards(target, 2)
            self.message = f"UNO catch! Player {target + 1} draws 2"
            return True, "ok"
        return False, "Cannot catch"

    def state_for(self, player: int) -> Dict[str, Any]:
        top = self.top()
        return {
            "type": "uno_state",
            "hand": [c.to_dict() for c in self.hands[player]],
            "hand_counts": [len(self.hands[0]), len(self.hands[1])],
            "discard_top": top.to_dict() if top else None,
            "active_color": self.active_color,
            "current": self.current,
            "direction": self.direction,
            "awaiting_color": self.awaiting_color,
            "color_chooser": self.color_chooser,
            "winner": self.winner,
            "message": self.message,
            "draw_count": len(self.deck),
            "drew_cid": self.drew_this_turn.cid if self.drew_this_turn else None,
            "uno_called": {str(k): v for k, v in self.uno_called.items()},
            "you": player,
        }

    def apply_public_state(self, msg: Dict[str, Any], my_player: int):
        """Client applies host snapshot (includes private hand for `you`)."""
        self.hands[my_player] = [Card.from_dict(c) for c in msg.get("hand", [])]
        # Opponent hand unknown — only count
        counts = msg.get("hand_counts", [0, 0])
        opp = 1 - my_player
        # Placeholder backs only — keep empty real cards
        self.hands[opp] = []
        self._opp_count = counts[opp] if len(counts) > opp else 0
        self._counts = counts
        top = msg.get("discard_top")
        self.discard = [Card.from_dict(top)] if top else []
        self.active_color = msg.get("active_color")
        self.current = int(msg.get("current", 0))
        self.direction = int(msg.get("direction", 1))
        self.awaiting_color = bool(msg.get("awaiting_color", False))
        self.color_chooser = msg.get("color_chooser")
        self.winner = msg.get("winner")
        self.message = msg.get("message", "")
        self._draw_count = int(msg.get("draw_count", 0))
        drew = msg.get("drew_cid")
        if drew is not None:
            self.drew_this_turn = next((c for c in self.hands[my_player] if c.cid == drew), None)
        else:
            self.drew_this_turn = None
        uc = msg.get("uno_called", {})
        self.uno_called = {0: bool(uc.get("0", False)), 1: bool(uc.get("1", False))}


# ---- View / interaction ----
@dataclass
class UnoView:
    match: UnoMatch
    my_player: int = 0
    is_host: bool = True
    fonts: Dict[str, pygame.font.Font] = field(default_factory=dict)

    # drag state
    dragging: bool = False
    drag_cid: Optional[int] = None
    drag_pos: Tuple[int, int] = (0, 0)
    drag_offset: Tuple[int, int] = (0, 0)

    # layout rects
    discard_rect: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))
    draw_rect: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))
    hand_rects: List[Tuple[pygame.Rect, int]] = field(default_factory=list)  # rect, cid
    color_rects: List[Tuple[pygame.Rect, str]] = field(default_factory=list)
    button_rects: List[Tuple[pygame.Rect, str]] = field(default_factory=list)

    # client-only counts
    opp_count: int = 0
    draw_count: int = 0

    def ensure_fonts(self):
        if not self.fonts:
            self.fonts = {
                "title": pygame.font.SysFont("Segoe UI", 28, bold=True),
                "big": pygame.font.SysFont("Segoe UI", 22, bold=True),
                "med": pygame.font.SysFont("Segoe UI", 17),
                "small": pygame.font.SysFont("Segoe UI", 14),
            }

    def sync_from_state_msg(self, msg: Dict[str, Any]):
        self.match.apply_public_state(msg, self.my_player)
        counts = msg.get("hand_counts", [0, 0])
        opp = 1 - self.my_player
        self.opp_count = counts[opp] if len(counts) > opp else 0
        self.draw_count = int(msg.get("draw_count", 0))

    def _hand_layout(self) -> List[Tuple[pygame.Rect, Card]]:
        hand = self.match.hands[self.my_player]
        n = len(hand)
        if n == 0:
            return []
        max_w = WIDTH - 80
        spacing = min(CARD_W - 10, max(28, max_w // max(n, 1)))
        total = spacing * (n - 1) + CARD_W
        start_x = (WIDTH - total) // 2
        y = HEIGHT - CARD_H - 28
        out = []
        for i, card in enumerate(hand):
            r = pygame.Rect(start_x + i * spacing, y, CARD_W, CARD_H)
            out.append((r, card))
        return out

    def draw(self, screen: pygame.Surface):
        self.ensure_fonts()
        screen.fill((28, 70, 48))  # felt table
        # vignette edges
        pygame.draw.rect(screen, (18, 40, 30), (0, 0, WIDTH, 54))
        pygame.draw.rect(screen, (18, 40, 30), (0, HEIGHT - 22, WIDTH, 22))

        f = self.fonts
        title = f["title"].render("LAN UNO", True, (245, 245, 245))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 28)))

        m = self.match
        my_turn = (m.current == self.my_player) and m.winner is None

        # Opponent hand (backs)
        if self.is_host:
            opp_n = len(m.hands[1 - self.my_player])
        else:
            opp_n = self.opp_count
        self._draw_opponent_hand(screen, opp_n)

        # Center piles
        cx = WIDTH // 2
        cy = HEIGHT // 2 - 20
        self.draw_rect = pygame.Rect(cx - CARD_W - 30, cy - CARD_H // 2, CARD_W, CARD_H)
        self.discard_rect = pygame.Rect(cx + 30, cy - CARD_H // 2, CARD_W, CARD_H)

        # Draw pile
        back = render_card_back()
        screen.blit(back, self.draw_rect.topleft)
        if (self.is_host and len(m.deck) > 1) or (not self.is_host and self.draw_count > 1):
            screen.blit(back, (self.draw_rect.x + 3, self.draw_rect.y + 3))
        dl = f["small"].render("DRAW", True, (230, 230, 240))
        screen.blit(dl, dl.get_rect(center=(self.draw_rect.centerx, self.draw_rect.bottom + 14)))
        dc = len(m.deck) if self.is_host else self.draw_count
        dcn = f["small"].render(str(dc), True, (200, 200, 210))
        screen.blit(dcn, dcn.get_rect(center=(self.draw_rect.centerx, self.draw_rect.bottom + 30)))

        # Discard
        top = m.top()
        if top:
            screen.blit(render_card_face(top), self.discard_rect.topleft)
        else:
            pygame.draw.rect(screen, (40, 90, 55), self.discard_rect, border_radius=12)
        disc_l = f["small"].render("DISCARD", True, (230, 230, 240))
        screen.blit(disc_l, disc_l.get_rect(center=(self.discard_rect.centerx, self.discard_rect.bottom + 14)))

        # Active color chip
        if m.active_color:
            rgb = COLOR_RGB[m.active_color]
            chip = pygame.Rect(cx - 40, cy + CARD_H // 2 + 48, 80, 28)
            pygame.draw.rect(screen, rgb, chip, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), chip, 2, border_radius=8)
            cn = f["small"].render(COLOR_NAME[m.active_color], True, (255, 255, 255) if m.active_color != "Y" else (30, 30, 30))
            screen.blit(cn, cn.get_rect(center=chip.center))

        # Status
        turn_txt = "YOUR TURN" if my_turn else "OPPONENT'S TURN"
        turn_col = (120, 255, 150) if my_turn else (255, 210, 120)
        if m.winner is not None:
            turn_txt = "YOU WIN!" if m.winner == self.my_player else "OPPONENT WINS"
            turn_col = (120, 255, 150) if m.winner == self.my_player else (255, 120, 120)
        tr = f["big"].render(turn_txt, True, turn_col)
        screen.blit(tr, tr.get_rect(midleft=(24, 28)))

        msg = f["med"].render(m.message[:60], True, (220, 230, 220))
        screen.blit(msg, msg.get_rect(midright=(WIDTH - 24, 28)))

        # Side help
        help_lines = [
            "Drag a card onto DISCARD to play",
            "Click DRAW pile to draw",
            "Match color or number/symbol",
            "Wild: pick color after play",
        ]
        hy = 100
        for line in help_lines:
            img = f["small"].render(line, True, (190, 210, 195))
            screen.blit(img, (WIDTH - 250, hy))
            hy += 20

        # Buttons
        self.button_rects = []
        bx = WIDTH - 200
        by = HEIGHT // 2 - 80
        for label, bid, col in [
            ("UNO!", "uno", (200, 140, 40)),
            ("Catch UNO", "catch", (160, 80, 50)),
            ("Pass", "pass", (70, 90, 120)),
            ("Main Menu", "menu", (120, 55, 55)),
        ]:
            if bid == "pass" and m.drew_this_turn is None:
                continue
            r = pygame.Rect(bx, by, 170, 40)
            pygame.draw.rect(screen, col, r, border_radius=8)
            pygame.draw.rect(screen, (20, 20, 20), r, 2, border_radius=8)
            t = f["med"].render(label, True, (255, 255, 255))
            screen.blit(t, t.get_rect(center=r.center))
            self.button_rects.append((r, bid))
            by += 52

        # Color picker overlay
        self.color_rects = []
        if m.awaiting_color and m.color_chooser == self.my_player:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (0, 0))
            box = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 - 90, 400, 180)
            pygame.draw.rect(screen, (40, 44, 52), box, border_radius=12)
            pygame.draw.rect(screen, (200, 200, 210), box, 2, border_radius=12)
            ht = f["big"].render("Choose a color", True, (255, 255, 255))
            screen.blit(ht, ht.get_rect(center=(WIDTH // 2, box.y + 36)))
            sw = 70
            for i, c in enumerate(COLORS):
                r = pygame.Rect(box.x + 40 + i * (sw + 18), box.y + 80, sw, sw)
                pygame.draw.rect(screen, COLOR_RGB[c], r, border_radius=10)
                pygame.draw.rect(screen, (255, 255, 255), r, 2, border_radius=10)
                self.color_rects.append((r, c))

        # Hand
        self.hand_rects = []
        layout = self._hand_layout()
        legal_ids = set()
        if my_turn and not m.awaiting_color:
            legal_ids = {c.cid for c in m.legal_cards(self.my_player)}

        for rect, card in layout:
            if self.dragging and self.drag_cid == card.cid:
                continue
            face = render_card_face(card)
            screen.blit(face, rect.topleft)
            if card.cid in legal_ids:
                pygame.draw.rect(screen, (80, 255, 120), rect.inflate(6, 6), 3, border_radius=14)
            self.hand_rects.append((rect, card.cid))

        # Dragging card on top
        if self.dragging and self.drag_cid is not None:
            card = next((c for c in m.hands[self.my_player] if c.cid == self.drag_cid), None)
            if card:
                face = render_card_face(card)
                screen.blit(face, (self.drag_pos[0] - self.drag_offset[0], self.drag_pos[1] - self.drag_offset[1]))

        # Highlight discard drop zone when dragging legal
        if self.dragging and self.drag_cid is not None and self.drag_cid in legal_ids:
            pygame.draw.rect(screen, (100, 255, 140), self.discard_rect.inflate(12, 12), 3, border_radius=14)

    def _draw_opponent_hand(self, screen: pygame.Surface, n: int):
        if n <= 0:
            return
        spacing = min(CARD_W_SM - 8, max(18, 500 // max(n, 1)))
        total = spacing * (n - 1) + CARD_W_SM
        start_x = (WIDTH - total) // 2
        y = 70
        back = render_card_back(CARD_W_SM, CARD_H_SM)
        for i in range(n):
            screen.blit(back, (start_x + i * spacing, y))
        f = self.fonts["small"]
        t = f.render(f"Opponent — {n} card{'s' if n != 1 else ''}", True, (220, 230, 220))
        screen.blit(t, t.get_rect(center=(WIDTH // 2, y + CARD_H_SM + 16)))

    def handle_mouse_down(self, pos: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        """Return action dict for host to process / client to send, or None."""
        mx, my = pos
        m = self.match

        # Color pick
        if m.awaiting_color and m.color_chooser == self.my_player:
            for r, col in self.color_rects:
                if r.collidepoint(mx, my):
                    return {"action": "color", "color": col}
            return None

        # Buttons
        for r, bid in self.button_rects:
            if r.collidepoint(mx, my):
                return {"action": bid}

        # Start drag from hand
        if m.winner is None:
            for r, cid in reversed(self.hand_rects):
                if r.collidepoint(mx, my):
                    self.dragging = True
                    self.drag_cid = cid
                    self.drag_pos = pos
                    self.drag_offset = (mx - r.x, my - r.y)
                    return None

        # Click draw pile
        if self.draw_rect.collidepoint(mx, my):
            return {"action": "draw"}

        return None

    def handle_mouse_up(self, pos: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        if not self.dragging or self.drag_cid is None:
            self.dragging = False
            self.drag_cid = None
            return None
        mx, my = pos
        cid = self.drag_cid
        self.dragging = False
        self.drag_cid = None

        # Drop on discard?
        drop = self.discard_rect.inflate(30, 30)
        if drop.collidepoint(mx, my):
            return {"action": "play", "cid": cid}
        return None

    def handle_mouse_motion(self, pos: Tuple[int, int]):
        if self.dragging:
            self.drag_pos = pos


def process_host_action(match: UnoMatch, player: int, action: Dict[str, Any]) -> bool:
    """Apply a player action on the host. Returns True if state changed."""
    act = action.get("action")
    if act == "play":
        ok, _ = match.play_card(player, int(action["cid"]))
        return ok
    if act == "draw":
        ok, _ = match.draw_card(player)
        return ok
    if act == "color":
        ok, _ = match.choose_color(player, action.get("color", "R"))
        return ok
    if act == "pass":
        ok, _ = match.pass_after_draw(player)
        return ok
    if act == "uno":
        ok, _ = match.call_uno(player)
        return ok
    if act == "catch":
        ok, _ = match.catch_uno(player, 1 - player)
        return ok
    return False
