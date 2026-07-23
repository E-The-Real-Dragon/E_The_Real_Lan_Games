#!/usr/bin/env python3
"""
LAN Cribbage — 2-player host-authoritative multiplayer.

Private hands, discard-to-crib, pegging play to 31, hand/crib show scoring.
Race to 121. Standard 52-card deck with original (non-branded) card faces.
"""

from __future__ import annotations

import itertools
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pygame

WIDTH, HEIGHT = 920, 720
CARD_W, CARD_H = 70, 106
CARD_W_SM, CARD_H_SM = 50, 76

SUITS = ("S", "H", "D", "C")  # spades hearts diamonds clubs
SUIT_SYM = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
RANK_NAME = {
    1: "A",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "10",
    11: "J",
    12: "Q",
    13: "K",
}
WIN_SCORE = 121


@dataclass
class Card:
    cid: int
    rank: int  # 1-13
    suit: str

    def to_dict(self) -> Dict[str, Any]:
        return {"cid": self.cid, "rank": self.rank, "suit": self.suit}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Card":
        return Card(int(d["cid"]), int(d["rank"]), str(d["suit"]))

    def pip(self) -> str:
        return RANK_NAME[self.rank]

    def count_val(self) -> int:
        return min(self.rank, 10)

    def is_red(self) -> bool:
        return self.suit in ("H", "D")


def build_deck() -> List[Card]:
    cards: List[Card] = []
    cid = 0
    for suit in SUITS:
        for rank in range(1, 14):
            cards.append(Card(cid, rank, suit))
            cid += 1
    return cards


# ---- Scoring helpers ----
def score_fifteens(cards: List[Card]) -> int:
    pts = 0
    for r in range(2, len(cards) + 1):
        for combo in itertools.combinations(cards, r):
            if sum(c.count_val() for c in combo) == 15:
                pts += 2
    return pts


def score_pairs(cards: List[Card]) -> int:
    pts = 0
    ranks = [c.rank for c in cards]
    for r in set(ranks):
        n = ranks.count(r)
        if n == 2:
            pts += 2
        elif n == 3:
            pts += 6
        elif n == 4:
            pts += 12
    return pts


def score_runs(cards: List[Card]) -> int:
    """Score runs in a 4 or 5 card hand (including starter)."""
    ranks = sorted(c.rank for c in cards)
    # Count multiplicity
    from collections import Counter

    cnt = Counter(ranks)
    uniq = sorted(cnt.keys())
    # Find longest consecutive sequence length >= 3
    best = 0
    best_start = None
    i = 0
    while i < len(uniq):
        j = i
        while j + 1 < len(uniq) and uniq[j + 1] == uniq[j] + 1:
            j += 1
        length = j - i + 1
        if length >= 3 and length > best:
            best = length
            best_start = i
        i = j + 1
    if best < 3 or best_start is None:
        return 0
    seq = uniq[best_start : best_start + best]
    # Multiplier for pairs in run
    mult = 1
    for r in seq:
        mult *= cnt[r]
    return best * mult


def score_flush(cards: List[Card], is_crib: bool, starter: Optional[Card]) -> int:
    """Hand cards only for flush check; starter may extend."""
    if not cards:
        return 0
    suits = [c.suit for c in cards]
    if len(set(suits)) != 1:
        return 0
    suit = suits[0]
    if is_crib:
        # Crib flush only if starter matches too (all 5)
        if starter and starter.suit == suit:
            return 5
        return 0
    # Hand: 4 same suit = 4, +1 if starter matches
    if starter and starter.suit == suit:
        return 5
    return 4


def score_nobs(hand: List[Card], starter: Optional[Card]) -> int:
    if not starter:
        return 0
    for c in hand:
        if c.rank == 11 and c.suit == starter.suit:
            return 1
    return 0


def score_hand(hand: List[Card], starter: Card, is_crib: bool = False) -> Tuple[int, str]:
    cards = hand + [starter]
    parts = []
    total = 0
    f15 = score_fifteens(cards)
    if f15:
        parts.append(f"15s={f15}")
        total += f15
    pr = score_pairs(cards)
    if pr:
        parts.append(f"pairs={pr}")
        total += pr
    rn = score_runs(cards)
    if rn:
        parts.append(f"runs={rn}")
        total += rn
    fl = score_flush(hand, is_crib, starter)
    if fl:
        parts.append(f"flush={fl}")
        total += fl
    if not is_crib:
        nb = score_nobs(hand, starter)
        if nb:
            parts.append("nobs=1")
            total += nb
    detail = ", ".join(parts) if parts else "0"
    return total, detail


def peg_run_points(played: List[Card]) -> int:
    """Points for run ending at last card (any order of last n cards)."""
    n = len(played)
    for length in range(min(n, 7), 2, -1):
        chunk = played[-length:]
        ranks = sorted(c.rank for c in chunk)
        # must be unique consecutive
        if len(set(ranks)) != length:
            continue
        if ranks[-1] - ranks[0] == length - 1 and len(ranks) == length:
            return length
    return 0


def peg_pair_points(played: List[Card]) -> int:
    if len(played) < 2:
        return 0
    r = played[-1].rank
    count = 0
    for c in reversed(played):
        if c.rank == r:
            count += 1
        else:
            break
    if count == 2:
        return 2
    if count == 3:
        return 6
    if count >= 4:
        return 12
    return 0


# ---- Card art ----
_face_cache: Dict[Tuple[Any, ...], pygame.Surface] = {}
_back_cache: Dict[Tuple[int, int], pygame.Surface] = {}


def _rounded(surf, rect, color, radius=10):
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def render_card_face(card: Card, w: int = CARD_W, h: int = CARD_H) -> pygame.Surface:
    """Hi-res-ish card face: soft plastic look (not chunky 8-bit blocks)."""
    key = (card.cid, card.rank, card.suit, w, h, "v2")
    if key in _face_cache:
        return _face_cache[key]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Soft drop shadow
    sh = pygame.Surface((w, h), pygame.SRCALPHA)
    _rounded(sh, pygame.Rect(3, 4, w - 4, h - 4), (0, 0, 0, 70), 11)
    surf.blit(sh, (0, 0))
    _rounded(surf, pygame.Rect(0, 0, w - 2, h - 2), (22, 24, 30), 11)
    # Cream face with slight vertical gradient
    face = pygame.Surface((w - 6, h - 6), pygame.SRCALPHA)
    for yy in range(h - 6):
        t = yy / max(1, h - 7)
        r = int(252 - t * 8)
        g = int(250 - t * 10)
        b = int(244 - t * 12)
        pygame.draw.line(face, (r, g, b), (0, yy), (w - 6, yy))
    surf.blit(face, (2, 2))
    # clip corners by redrawing border radius overlay — approximate with rounded mask stroke
    _rounded(surf, pygame.Rect(2, 2, w - 6, h - 6), (0, 0, 0, 0), 9)
    pygame.draw.rect(surf, (235, 232, 225), pygame.Rect(2, 2, w - 6, h - 6), width=1, border_radius=9)

    ink = (190, 32, 42) if card.is_red() else (28, 30, 38)
    font_r = pygame.font.SysFont("Segoe UI", max(15, h // 5), bold=True)
    font_s = pygame.font.SysFont("Segoe UI", max(16, h // 4), bold=True)
    pip = card.pip()
    sym = SUIT_SYM[card.suit]
    t1 = font_r.render(pip, True, ink)
    t2 = font_s.render(sym, True, ink)
    surf.blit(t1, (8, 5))
    surf.blit(t2, (8, 5 + t1.get_height() - 2))
    big = pygame.font.SysFont("Segoe UI", max(30, h // 3), bold=True)
    ct = big.render(sym, True, ink)
    # soft center plate
    plate = pygame.Rect(w // 2 - 18, h // 2 - 22, 36, 44)
    pygame.draw.ellipse(surf, (255, 255, 255, 90), plate)
    surf.blit(ct, ct.get_rect(center=(w // 2, h // 2 + 2)))
    t1b = pygame.transform.rotate(t1, 180)
    t2b = pygame.transform.rotate(t2, 180)
    surf.blit(t1b, (w - t1b.get_width() - 10, h - t1b.get_height() - 6))
    surf.blit(t2b, (w - t2b.get_width() - 10, h - t1b.get_height() - t2b.get_height() - 4))
    gloss = pygame.Surface((w - 12, max(8, h // 4)), pygame.SRCALPHA)
    for yy in range(gloss.get_height()):
        a = int(55 * (1 - yy / max(1, gloss.get_height())))
        pygame.draw.line(gloss, (255, 255, 255, a), (0, yy), (gloss.get_width(), yy))
    surf.blit(gloss, (5, 4))
    _face_cache[key] = surf
    return surf


def render_card_back(w: int = CARD_W, h: int = CARD_H) -> pygame.Surface:
    key = (w, h)
    if key in _back_cache:
        return _back_cache[key]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    _rounded(surf, pygame.Rect(0, 0, w, h), (12, 12, 16), 10)
    _rounded(surf, pygame.Rect(2, 2, w - 4, h - 4), (30, 70, 40), 9)
    _rounded(surf, pygame.Rect(8, 10, w - 16, h - 20), (40, 95, 55), 7)
    font = pygame.font.SysFont("Segoe UI", max(12, h // 8), bold=True)
    t = font.render("LAN", True, (220, 240, 220))
    surf.blit(t, t.get_rect(center=(w // 2, h // 2)))
    _back_cache[key] = surf
    return surf


class CribbageMatch:
    """Host-side authoritative 2-player cribbage."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed if seed is not None else time.time_ns())
        self.scores = [0, 0]
        self.dealer = 0  # host starts as dealer for first hand (or cut for deal - host dealer)
        self.phase = "idle"  # discard, peg, show, between, gameover
        self.deck: List[Card] = []
        self.hands: List[List[Card]] = [[], []]
        self.crib: List[Card] = []
        self.discards_done = [False, False]
        self.pending_discard: List[List[int]] = [[], []]  # selected cids per player
        self.starter: Optional[Card] = None
        self.peg_played: List[Tuple[int, Card]] = []  # (player, card)
        self.peg_stack: List[Card] = []  # current 31 sequence
        self.peg_count = 0
        self.peg_turn = 0
        self.peg_said_go = [False, False]
        self.peg_last_scorer: Optional[int] = None
        self.cards_played_ids: set = set()
        self.show_step = 0  # 0=pone hand, 1=dealer hand, 2=crib, 3=done
        self.show_points: List[Optional[int]] = [None, None, None]  # pone, dealer, crib
        self.show_detail: List[str] = ["", "", ""]
        self.message = ""
        self.winner: Optional[int] = None
        self.last_peg_score_msg = ""
        self.hand_number = 0

    def start_match(self):
        self.scores = [0, 0]
        self.dealer = 0
        self.winner = None
        self.hand_number = 0
        self.start_hand()

    def start_hand(self):
        self.hand_number += 1
        self.deck = build_deck()
        self.rng.shuffle(self.deck)
        self.hands = [[], []]
        self.crib = []
        self.discards_done = [False, False]
        self.pending_discard = [[], []]
        self.starter = None
        self.peg_played = []
        self.peg_stack = []
        self.peg_count = 0
        self.peg_said_go = [False, False]
        self.peg_last_scorer = None
        self.cards_played_ids = set()
        self.show_step = 0
        self.show_points = [None, None, None]
        self.show_detail = ["", "", ""]
        self.last_peg_score_msg = ""
        # Deal 6 each: non-dealer first traditionally but order doesn't matter for fairness
        for _ in range(6):
            self.hands[0].append(self.deck.pop())
            self.hands[1].append(self.deck.pop())
        self.phase = "discard"
        pone = 1 - self.dealer
        self.message = f"Hand {self.hand_number}: discard 2 to the crib (dealer is P{self.dealer + 1})"
        self.peg_turn = pone  # will be used after cut

    def _add_score(self, player: int, pts: int, why: str) -> bool:
        """Add points; return True if game over."""
        if pts <= 0 or self.winner is not None:
            return self.winner is not None
        self.scores[player] = min(WIN_SCORE, self.scores[player] + pts)
        self.last_peg_score_msg = f"P{player + 1} +{pts} ({why})"
        if self.scores[player] >= WIN_SCORE:
            self.winner = player
            self.phase = "gameover"
            self.message = f"Player {player + 1} wins!"
            return True
        return False

    def select_discard(self, player: int, cid: int) -> Tuple[bool, str]:
        if self.phase != "discard" or self.discards_done[player]:
            return False, "Not discarding"
        hand = self.hands[player]
        if not any(c.cid == cid for c in hand):
            return False, "Not in hand"
        pend = self.pending_discard[player]
        if cid in pend:
            pend.remove(cid)
            return True, "unselected"
        if len(pend) >= 2:
            return False, "Already picked 2 — confirm or deselect"
        pend.append(cid)
        return True, "selected"

    def confirm_discard(self, player: int) -> Tuple[bool, str]:
        if self.phase != "discard" or self.discards_done[player]:
            return False, "Not discarding"
        pend = self.pending_discard[player]
        if len(pend) != 2:
            return False, "Select exactly 2 cards"
        hand = self.hands[player]
        moving = []
        for cid in pend:
            card = next((c for c in hand if c.cid == cid), None)
            if not card:
                return False, "Bad selection"
            moving.append(card)
        for card in moving:
            hand.remove(card)
            self.crib.append(card)
        self.pending_discard[player] = []
        self.discards_done[player] = True
        if all(self.discards_done):
            self._cut_starter()
        else:
            self.message = f"P{player + 1} discarded — waiting for opponent"
        return True, "ok"

    def _cut_starter(self):
        # Starter from remaining deck
        if not self.deck:
            self.deck = build_deck()
            self.rng.shuffle(self.deck)
        self.starter = self.deck.pop()
        self.phase = "peg"
        self.peg_stack = []
        self.peg_count = 0
        self.peg_said_go = [False, False]
        self.peg_turn = 1 - self.dealer  # pone leads
        self.message = f"Starter: {self.starter.pip()}{SUIT_SYM[self.starter.suit]}"
        # His heels: jack starter = 2 to dealer
        if self.starter.rank == 11:
            if self._add_score(self.dealer, 2, "his heels"):
                return
            self.message += " — Dealer +2 his heels"
        self.message += " — Pegging: pone leads"

    def cards_left_in_hand(self, player: int) -> List[Card]:
        return [c for c in self.hands[player] if c.cid not in self.cards_played_ids]

    def can_play_card(self, player: int, card: Card) -> bool:
        if self.phase != "peg" or player != self.peg_turn or self.winner is not None:
            return False
        if card.cid in self.cards_played_ids:
            return False
        if card not in self.hands[player] and not any(c.cid == card.cid for c in self.hands[player]):
            return False
        return self.peg_count + card.count_val() <= 31

    def legal_peg_cards(self, player: int) -> List[Card]:
        return [c for c in self.cards_left_in_hand(player) if self.peg_count + c.count_val() <= 31]

    def play_peg(self, player: int, cid: int) -> Tuple[bool, str]:
        if self.phase != "peg":
            return False, "Not pegging"
        if player != self.peg_turn:
            return False, "Not your turn"
        card = next((c for c in self.cards_left_in_hand(player) if c.cid == cid), None)
        if not card:
            return False, "Card not available"
        if not self.can_play_card(player, card):
            return False, "Would exceed 31"

        self.cards_played_ids.add(card.cid)
        self.peg_stack.append(card)
        self.peg_played.append((player, card))
        self.peg_count += card.count_val()
        self.peg_said_go = [False, False]
        self.peg_last_scorer = player

        pts = 0
        why = []
        if self.peg_count == 15:
            pts += 2
            why.append("15")
        if self.peg_count == 31:
            pts += 2
            why.append("31")
        pp = peg_pair_points(self.peg_stack)
        if pp:
            pts += pp
            why.append(f"pair{pp}")
        rp = peg_run_points(self.peg_stack)
        if rp:
            pts += rp
            why.append(f"run{rp}")

        if pts:
            if self._add_score(player, pts, "+".join(why)):
                return True, "win"

        # End of sequence at 31?
        if self.peg_count == 31:
            self._reset_peg_stack(next_from=1 - player)
        else:
            # Next player if they can play, else stay / go logic
            nxt = 1 - player
            if self.legal_peg_cards(nxt):
                self.peg_turn = nxt
                self.message = f"Count {self.peg_count} — P{nxt + 1}'s turn"
            elif self.legal_peg_cards(player):
                # opponent cannot, current continues
                self.peg_turn = player
                self.message = f"Count {self.peg_count} — opponent cannot play, go again"
            else:
                # neither can play on this count — go for last card
                if self.peg_count != 31:
                    if self._add_score(player, 1, "go/last"):
                        return True, "win"
                self._reset_peg_stack(next_from=nxt)

        if self._pegging_complete():
            self._begin_show()
        return True, "ok"

    def say_go(self, player: int) -> Tuple[bool, str]:
        if self.phase != "peg" or player != self.peg_turn:
            return False, "Not your turn"
        if self.legal_peg_cards(player):
            return False, "You can still play a card"
        self.peg_said_go[player] = True
        opp = 1 - player
        if self.legal_peg_cards(opp):
            self.peg_turn = opp
            self.message = f"GO — P{opp + 1} plays"
            return True, "ok"
        # Neither can play
        scorer = self.peg_last_scorer if self.peg_last_scorer is not None else player
        if self.peg_count != 31 and self.peg_stack:
            if self._add_score(scorer, 1, "go"):
                return True, "win"
        self._reset_peg_stack(next_from=opp if self.cards_left_in_hand(opp) else player)
        if self._pegging_complete():
            self._begin_show()
        return True, "ok"

    def _reset_peg_stack(self, next_from: int):
        self.peg_stack = []
        self.peg_count = 0
        self.peg_said_go = [False, False]
        # Next lead: player who still has cards, prefer next_from
        if self.cards_left_in_hand(next_from):
            self.peg_turn = next_from
        elif self.cards_left_in_hand(1 - next_from):
            self.peg_turn = 1 - next_from
        self.message = f"New count — P{self.peg_turn + 1} leads"

    def _pegging_complete(self) -> bool:
        return not self.cards_left_in_hand(0) and not self.cards_left_in_hand(1)

    def _begin_show(self):
        self.phase = "show"
        self.show_step = 0
        self.show_points = [None, None, None]
        self.show_detail = ["", "", ""]
        self.message = "Show: non-dealer scores first — click Next"
        # Restore full hands for show: hands currently still have all 4 cards (played not removed)
        # We never removed played cards from hands — good for show.

    def advance_show(self, player: int) -> Tuple[bool, str]:
        """Either player can click next during show (host applies)."""
        if self.phase != "show" or self.winner is not None:
            return False, "Not in show"
        if not self.starter:
            return False, "No starter"
        pone = 1 - self.dealer
        dealer = self.dealer

        if self.show_step == 0:
            pts, detail = score_hand(self.hands[pone], self.starter, is_crib=False)
            self.show_points[0] = pts
            self.show_detail[0] = detail
            if self._add_score(pone, pts, f"hand ({detail})"):
                return True, "win"
            self.show_step = 1
            self.message = f"Pone (P{pone + 1}) hand: {pts} — Next: dealer hand"
            return True, "ok"
        if self.show_step == 1:
            pts, detail = score_hand(self.hands[dealer], self.starter, is_crib=False)
            self.show_points[1] = pts
            self.show_detail[1] = detail
            if self._add_score(dealer, pts, f"hand ({detail})"):
                return True, "win"
            self.show_step = 2
            self.message = f"Dealer (P{dealer + 1}) hand: {pts} — Next: crib"
            return True, "ok"
        if self.show_step == 2:
            pts, detail = score_hand(self.crib, self.starter, is_crib=True)
            self.show_points[2] = pts
            self.show_detail[2] = detail
            if self._add_score(dealer, pts, f"crib ({detail})"):
                return True, "win"
            self.show_step = 3
            self.phase = "between"
            self.message = f"Crib: {pts}. Click Next Hand (dealer switches)."
            return True, "ok"
        return False, "Show done"

    def next_hand(self, player: int) -> Tuple[bool, str]:
        if self.phase != "between" or self.winner is not None:
            return False, "Not between hands"
        self.dealer = 1 - self.dealer
        self.start_hand()
        return True, "ok"

    def state_for(self, player: int) -> Dict[str, Any]:
        opp = 1 - player
        # During show/between, reveal all hands
        reveal = self.phase in ("show", "between", "gameover")
        hand = [c.to_dict() for c in self.hands[player]]
        opp_hand = [c.to_dict() for c in self.hands[opp]] if reveal else None
        crib = [c.to_dict() for c in self.crib] if reveal or self.phase == "discard" else None
        # During discard, crib cards not revealed — only count
        if self.phase == "discard":
            crib = None
        crib_count = len(self.crib)
        peg_seq = [{"player": p, "card": c.to_dict()} for p, c in self.peg_played]
        return {
            "type": "crib_state",
            "you": player,
            "scores": list(self.scores),
            "dealer": self.dealer,
            "phase": self.phase,
            "hand": hand,
            "opp_count": len(self.hands[opp]),
            "opp_hand": opp_hand,
            "pending_discard": list(self.pending_discard[player]),
            "discards_done": list(self.discards_done),
            "crib_count": crib_count,
            "crib": crib,
            "starter": self.starter.to_dict() if self.starter else None,
            "peg_count": self.peg_count,
            "peg_stack": [c.to_dict() for c in self.peg_stack],
            "peg_turn": self.peg_turn,
            "peg_played": peg_seq,
            "cards_played_ids": list(self.cards_played_ids),
            "show_step": self.show_step,
            "show_points": self.show_points,
            "show_detail": self.show_detail,
            "message": self.message,
            "last_peg": self.last_peg_score_msg,
            "winner": self.winner,
            "hand_number": self.hand_number,
        }

    def apply_public_state(self, msg: Dict[str, Any], my_player: int):
        self.scores = list(msg.get("scores", [0, 0]))
        self.dealer = int(msg.get("dealer", 0))
        self.phase = msg.get("phase", "discard")
        self.hands[my_player] = [Card.from_dict(c) for c in msg.get("hand", [])]
        opp = 1 - my_player
        if msg.get("opp_hand"):
            self.hands[opp] = [Card.from_dict(c) for c in msg["opp_hand"]]
        else:
            self.hands[opp] = []
        self._opp_count = int(msg.get("opp_count", 0))
        self.pending_discard[my_player] = list(msg.get("pending_discard", []))
        self.discards_done = list(msg.get("discards_done", [False, False]))
        self._crib_count = int(msg.get("crib_count", 0))
        if msg.get("crib"):
            self.crib = [Card.from_dict(c) for c in msg["crib"]]
        else:
            self.crib = []
        st = msg.get("starter")
        self.starter = Card.from_dict(st) if st else None
        self.peg_count = int(msg.get("peg_count", 0))
        self.peg_stack = [Card.from_dict(c) for c in msg.get("peg_stack", [])]
        self.peg_turn = int(msg.get("peg_turn", 0))
        self.cards_played_ids = set(msg.get("cards_played_ids", []))
        self.peg_played = []
        for item in msg.get("peg_played", []):
            self.peg_played.append((int(item["player"]), Card.from_dict(item["card"])))
        self.show_step = int(msg.get("show_step", 0))
        self.show_points = list(msg.get("show_points", [None, None, None]))
        self.show_detail = list(msg.get("show_detail", ["", "", ""]))
        self.message = msg.get("message", "")
        self.last_peg_score_msg = msg.get("last_peg", "")
        self.winner = msg.get("winner")
        self.hand_number = int(msg.get("hand_number", 1))


def process_host_action(match: CribbageMatch, player: int, action: Dict[str, Any]) -> bool:
    act = action.get("action")
    if act == "toggle_discard":
        ok, _ = match.select_discard(player, int(action["cid"]))
        return ok
    if act == "confirm_discard":
        ok, _ = match.confirm_discard(player)
        return ok
    if act == "peg":
        ok, _ = match.play_peg(player, int(action["cid"]))
        return ok
    if act == "go":
        ok, _ = match.say_go(player)
        return ok
    if act == "show_next":
        ok, _ = match.advance_show(player)
        return ok
    if act == "next_hand":
        ok, _ = match.next_hand(player)
        return ok
    return False


# ---- View ----
@dataclass
class CribbageView:
    match: CribbageMatch
    my_player: int = 0
    is_host: bool = True
    fonts: Dict[str, pygame.font.Font] = field(default_factory=dict)

    dragging: bool = False
    drag_cid: Optional[int] = None
    drag_pos: Tuple[int, int] = (0, 0)
    drag_offset: Tuple[int, int] = (0, 0)

    hand_rects: List[Tuple[pygame.Rect, int]] = field(default_factory=list)
    button_rects: List[Tuple[pygame.Rect, str]] = field(default_factory=list)
    crib_zone: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))
    play_zone: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))

    opp_count: int = 0
    crib_count: int = 0

    def ensure_fonts(self):
        if not self.fonts:
            self.fonts = {
                "title": pygame.font.SysFont("Segoe UI", 26, bold=True),
                "big": pygame.font.SysFont("Segoe UI", 20, bold=True),
                "med": pygame.font.SysFont("Segoe UI", 16),
                "small": pygame.font.SysFont("Segoe UI", 13),
            }

    def sync_from_state_msg(self, msg: Dict[str, Any]):
        self.match.apply_public_state(msg, self.my_player)
        self.opp_count = int(msg.get("opp_count", 0))
        self.crib_count = int(msg.get("crib_count", 0))

    def _layout_hand(self, cards: List[Card], y: int, highlight_ids: Optional[set] = None) -> List[Tuple[pygame.Rect, Card]]:
        n = len(cards)
        if n == 0:
            return []
        spacing = min(CARD_W - 8, max(26, (WIDTH - 100) // max(n, 1)))
        total = spacing * (n - 1) + CARD_W
        start_x = (WIDTH - total) // 2
        out = []
        for i, card in enumerate(cards):
            r = pygame.Rect(start_x + i * spacing, y, CARD_W, CARD_H)
            out.append((r, card))
        return out

    def draw(self, screen: pygame.Surface):
        self.ensure_fonts()
        screen.fill((25, 55, 40))
        pygame.draw.rect(screen, (18, 36, 28), (0, 0, WIDTH, 58))
        f = self.fonts
        m = self.match

        title = f["title"].render("LAN CRIBBAGE", True, (245, 245, 245))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 22)))

        # Scores / peg board strip
        self._draw_scores(screen)

        # Phase + message
        phase_labels = {
            "discard": "DISCARD TO CRIB",
            "peg": "PEGGING (play to 31)",
            "show": "THE SHOW",
            "between": "HAND COMPLETE",
            "gameover": "GAME OVER",
        }
        pl = f["big"].render(phase_labels.get(m.phase, m.phase), True, (255, 220, 120))
        screen.blit(pl, (20, 64))
        msg = f["med"].render((m.message or "")[:70], True, (210, 220, 210))
        screen.blit(msg, (20, 90))
        if m.last_peg_score_msg:
            lp = f["small"].render(m.last_peg_score_msg, True, (255, 200, 120))
            screen.blit(lp, (20, 112))

        dealer_txt = f"Dealer: {'You' if m.dealer == self.my_player else 'Opponent'}  |  Hand #{m.hand_number}"
        dt = f["small"].render(dealer_txt, True, (180, 200, 190))
        screen.blit(dt, (WIDTH - 280, 64))

        # Opponent hand
        if m.phase in ("show", "between", "gameover") and m.hands[1 - self.my_player]:
            opp_cards = m.hands[1 - self.my_player]
            for rect, card in self._layout_hand(opp_cards, 130):
                screen.blit(render_card_face(card, CARD_W_SM, CARD_H_SM), (rect.x, rect.y))
        else:
            n = len(m.hands[1 - self.my_player]) if self.is_host else self.opp_count
            self._draw_backs(screen, n, 130)

        ot = f["small"].render("Opponent", True, (200, 210, 200))
        screen.blit(ot, ot.get_rect(center=(WIDTH // 2, 120)))

        # Center: starter, crib, peg stack
        self.crib_zone = pygame.Rect(80, 280, CARD_W + 20, CARD_H + 30)
        self.play_zone = pygame.Rect(WIDTH // 2 - 160, 260, 320, CARD_H + 50)

        # Crib
        pygame.draw.rect(screen, (30, 70, 50), self.crib_zone, border_radius=8)
        ct = f["small"].render("CRIB", True, (220, 230, 220))
        screen.blit(ct, (self.crib_zone.x + 8, self.crib_zone.y - 18))
        cc = self.crib_count if not self.is_host else len(m.crib)
        if m.phase in ("show", "between", "gameover") and m.crib:
            for i, card in enumerate(m.crib[:4]):
                screen.blit(render_card_face(card, CARD_W_SM, CARD_H_SM), (self.crib_zone.x + 6 + i * 8, self.crib_zone.y + 10))
        else:
            back = render_card_back(CARD_W_SM, CARD_H_SM)
            for i in range(min(cc, 4)):
                screen.blit(back, (self.crib_zone.x + 10 + i * 6, self.crib_zone.y + 12))
            cnt = f["small"].render(str(cc), True, (230, 230, 230))
            screen.blit(cnt, (self.crib_zone.x + 12, self.crib_zone.bottom - 18))

        # Starter
        sx = WIDTH - 160
        sy = 280
        stl = f["small"].render("STARTER", True, (220, 230, 220))
        screen.blit(stl, (sx, sy - 18))
        if m.starter:
            screen.blit(render_card_face(m.starter), (sx, sy))
        else:
            pygame.draw.rect(screen, (40, 80, 55), (sx, sy, CARD_W, CARD_H), border_radius=8)

        # Peg play area
        pygame.draw.rect(screen, (35, 75, 55), self.play_zone, border_radius=10)
        pygame.draw.rect(screen, (80, 120, 90), self.play_zone, 2, border_radius=10)
        count_l = f["big"].render(f"Count: {m.peg_count}", True, (255, 255, 240))
        screen.blit(count_l, (self.play_zone.x + 12, self.play_zone.y + 8))
        for i, card in enumerate(m.peg_stack[-6:]):
            screen.blit(render_card_face(card, CARD_W_SM, CARD_H_SM), (self.play_zone.x + 20 + i * (CARD_W_SM - 10), self.play_zone.y + 40))

        # Show points panel
        if m.phase in ("show", "between", "gameover"):
            box = pygame.Rect(WIDTH // 2 - 200, 200, 400, 50)
            pygame.draw.rect(screen, (30, 40, 50), box, border_radius=8)
            pone = 1 - m.dealer
            labels = [
                f"Pone P{pone+1}: {m.show_points[0] if m.show_points[0] is not None else '—'}",
                f"Dealer: {m.show_points[1] if m.show_points[1] is not None else '—'}",
                f"Crib: {m.show_points[2] if m.show_points[2] is not None else '—'}",
            ]
            t = f["med"].render("  |  ".join(labels), True, (230, 230, 240))
            screen.blit(t, t.get_rect(center=box.center))

        # My hand
        my_hand = m.hands[self.my_player]
        # Hide already played during peg? Still show face-down or dim
        show_cards = []
        for c in my_hand:
            if m.phase == "peg" and c.cid in m.cards_played_ids:
                continue
            show_cards.append(c)
        if m.phase in ("show", "between", "gameover"):
            show_cards = list(my_hand)

        legal_ids = set()
        if m.phase == "peg" and m.peg_turn == self.my_player:
            legal_ids = {c.cid for c in m.legal_peg_cards(self.my_player)}
        elif m.phase == "discard" and not m.discards_done[self.my_player]:
            legal_ids = {c.cid for c in my_hand}

        pending = set(m.pending_discard[self.my_player])
        self.hand_rects = []
        layout = self._layout_hand(show_cards, HEIGHT - CARD_H - 24)
        for rect, card in layout:
            if self.dragging and self.drag_cid == card.cid:
                continue
            face = render_card_face(card)
            screen.blit(face, rect.topleft)
            if card.cid in pending:
                pygame.draw.rect(screen, (255, 200, 60), rect.inflate(8, 8), 3, border_radius=12)
            elif card.cid in legal_ids and m.phase == "peg":
                pygame.draw.rect(screen, (80, 255, 120), rect.inflate(6, 6), 3, border_radius=12)
            self.hand_rects.append((rect, card.cid))

        if self.dragging and self.drag_cid is not None:
            card = next((c for c in my_hand if c.cid == self.drag_cid), None)
            if card:
                screen.blit(
                    render_card_face(card),
                    (self.drag_pos[0] - self.drag_offset[0], self.drag_pos[1] - self.drag_offset[1]),
                )

        # Buttons
        self.button_rects = []
        bx, by = WIDTH - 190, 400
        buttons = [
            ("How to Play", "help", (70, 90, 150)),
            ("Main Menu", "menu", (120, 55, 55)),
        ]
        if m.phase == "discard" and not m.discards_done[self.my_player]:
            buttons.insert(0, ("Confirm 2 to Crib", "confirm_discard", (50, 130, 80)))
        if m.phase == "peg" and m.peg_turn == self.my_player and not m.legal_peg_cards(self.my_player):
            buttons.insert(0, ("GO", "go", (180, 120, 40)))
        if m.phase == "show":
            buttons.insert(0, ("Next Score", "show_next", (50, 100, 160)))
        if m.phase == "between":
            buttons.insert(0, ("Next Hand", "next_hand", (50, 130, 80)))

        for label, bid, col in buttons:
            r = pygame.Rect(bx, by, 170, 40)
            dark = tuple(max(0, c - 30) for c in col)
            pygame.draw.rect(screen, dark, r, border_radius=8)
            pygame.draw.rect(screen, col, r.inflate(-2, -2), border_radius=7)
            sheen = pygame.Surface((r.w - 4, r.h // 2), pygame.SRCALPHA)
            sheen.fill((255, 255, 255, 30))
            screen.blit(sheen, (r.x + 2, r.y + 2))
            pygame.draw.rect(screen, (15, 15, 15), r, 2, border_radius=8)
            t = f["med"].render(label, True, (255, 255, 255))
            screen.blit(t, t.get_rect(center=r.center))
            self.button_rects.append((r, bid))
            by += 48

        # Turn indicator
        if m.phase == "peg":
            turn = "YOUR TURN to peg" if m.peg_turn == self.my_player else "Opponent pegging"
            col = (120, 255, 150) if m.peg_turn == self.my_player else (255, 200, 120)
            t = f["big"].render(turn, True, col)
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT - CARD_H - 50))
        elif m.phase == "discard":
            if m.discards_done[self.my_player]:
                t = f["med"].render("Waiting for opponent to discard…", True, (220, 220, 180))
            else:
                t = f["med"].render("Click 2 cards (gold), then Confirm — or drag to CRIB", True, (220, 220, 180))
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT - CARD_H - 50))

        if m.winner is not None:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            screen.blit(overlay, (0, 0))

    def _draw_scores(self, screen: pygame.Surface):
        f = self.fonts
        m = self.match
        # Two score boxes
        for i, label in enumerate(("You", "Opponent")):
            p = self.my_player if i == 0 else 1 - self.my_player
            x = 20 + i * 200
            box = pygame.Rect(x, 8, 180, 42)
            pygame.draw.rect(screen, (40, 50, 45), box, border_radius=6)
            sc = m.scores[p]
            t = f["big"].render(f"{label}: {sc}", True, (255, 240, 200) if sc < WIN_SCORE else (120, 255, 140))
            screen.blit(t, (x + 10, 14))
        # Mini race bar
        bar = pygame.Rect(420, 18, 280, 22)
        pygame.draw.rect(screen, (30, 30, 30), bar, border_radius=4)
        for p, col in ((0, (80, 160, 255)), (1, (255, 120, 100))):
            w = int(bar.w * min(m.scores[p], WIN_SCORE) / WIN_SCORE)
            yoff = 0 if p == 0 else 11
            pygame.draw.rect(screen, col, (bar.x, bar.y + yoff, max(2, w), 10), border_radius=2)
        goal = f["small"].render(f"Race to {WIN_SCORE}", True, (180, 180, 180))
        screen.blit(goal, (710, 20))

    def _draw_backs(self, screen: pygame.Surface, n: int, y: int):
        if n <= 0:
            return
        spacing = min(CARD_W_SM - 6, max(16, 400 // max(n, 1)))
        total = spacing * (n - 1) + CARD_W_SM
        start = (WIDTH - total) // 2
        back = render_card_back(CARD_W_SM, CARD_H_SM)
        for i in range(n):
            screen.blit(back, (start + i * spacing, y))

    def handle_mouse_down(self, pos: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        mx, my = pos
        m = self.match
        for r, bid in self.button_rects:
            if r.collidepoint(mx, my):
                return {"action": bid}

        if m.phase == "discard" and not m.discards_done[self.my_player]:
            for r, cid in reversed(self.hand_rects):
                if r.collidepoint(mx, my):
                    # toggle select
                    return {"action": "toggle_discard", "cid": cid}

        if m.phase == "peg" and m.peg_turn == self.my_player:
            for r, cid in reversed(self.hand_rects):
                if r.collidepoint(mx, my):
                    # Start drag; short click still plays on mouse-up if legal
                    self.dragging = True
                    self.drag_cid = cid
                    self.drag_pos = pos
                    self.drag_offset = (mx - r.x, my - r.y)
                    self._drag_start = pos
                    return None

        return None

    def handle_mouse_up(self, pos: Tuple[int, int]) -> Optional[Dict[str, Any]]:
        if not self.dragging or self.drag_cid is None:
            self.dragging = False
            self.drag_cid = None
            return None
        cid = self.drag_cid
        start = getattr(self, "_drag_start", pos)
        self.dragging = False
        self.drag_cid = None
        mx, my = pos
        m = self.match
        if m.phase != "peg":
            return None
        # Dropped on play zone, or short click (play without careful drag)
        dist = abs(mx - start[0]) + abs(my - start[1])
        if self.play_zone.inflate(50, 50).collidepoint(mx, my) or dist < 12:
            legal = {c.cid for c in m.legal_peg_cards(self.my_player)}
            if cid in legal:
                return {"action": "peg", "cid": cid}
        return None

    def handle_mouse_motion(self, pos: Tuple[int, int]):
        if self.dragging:
            self.drag_pos = pos
