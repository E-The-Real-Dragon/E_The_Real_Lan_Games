#!/usr/bin/env python3
"""
Realistic plastic playing-card art for LAN Games.

Drawn procedurally (no copyrighted brand scans): glossy plastic stock,
beveled edges, corner indices, suit pips, and specular highlights.
Used by Cribbage (standard 52) and UNO-style color cards.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pygame

# Slightly larger cards read more "physical"
STD_W, STD_H = 86, 128
SM_W, SM_H = 58, 88

SUIT_SYM = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
RANK_PIP = {
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

# Classic UNO-ish palette (original, not brand assets)
UNO_RGB = {
    "R": (196, 30, 42),
    "Y": (236, 190, 28),
    "G": (28, 148, 68),
    "B": (28, 90, 200),
}

_face_std: Dict[Tuple[Any, ...], pygame.Surface] = {}
_face_uno: Dict[Tuple[Any, ...], pygame.Surface] = {}
_back_std: Dict[Tuple[int, int, str], pygame.Surface] = {}


def _clamp(v: int) -> int:
    return max(0, min(255, v))


def _shade(rgb: Tuple[int, int, int], mul: float, add: int = 0) -> Tuple[int, int, int]:
    return tuple(_clamp(int(c * mul) + add) for c in rgb)  # type: ignore


def _rounded(surf: pygame.Surface, rect: pygame.Rect, color, radius: int = 12):
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def _plastic_shell(w: int, h: int, face_rgb: Tuple[int, int, int] = (248, 246, 241)) -> pygame.Surface:
    """Blank glossy plastic card (exactly w x h) with soft shadow and edge bevel."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    # Soft multi-layer drop shadow (inside bounds)
    for i, a in enumerate((28, 45)):
        _rounded(
            surf,
            pygame.Rect(2 + i, 3 + i, w - 4 - i, h - 4 - i),
            (0, 0, 0, a),
            13,
        )

    # Dark plastic edge (thickness of stock)
    _rounded(surf, pygame.Rect(0, 0, w - 1, h - 1), (42, 44, 50), 13)
    # Mid rim
    _rounded(surf, pygame.Rect(1, 1, w - 3, h - 3), (75, 77, 84), 12)

    # Face fill with vertical gradient (warm white plastic)
    _rounded(surf, pygame.Rect(2, 2, w - 5, h - 5), face_rgb, 11)
    for yy in range(4, h - 6):
        t = (yy - 4) / max(1, h - 12)
        col = (
            _clamp(int(face_rgb[0] - t * 12)),
            _clamp(int(face_rgb[1] - t * 14)),
            _clamp(int(face_rgb[2] - t * 16)),
        )
        pygame.draw.line(surf, col, (6, yy), (w - 8, yy))

    # Inner hairline
    pygame.draw.rect(surf, (222, 220, 214), pygame.Rect(3, 3, w - 7, h - 7), width=1, border_radius=10)

    # Specular gloss (top-left shine on plastic)
    gloss = pygame.Surface((w - 12, max(10, h // 3)), pygame.SRCALPHA)
    gh = gloss.get_height()
    for yy in range(gh):
        a = int(65 * (1.0 - yy / max(1, gh - 1)) ** 1.35)
        pygame.draw.line(gloss, (255, 255, 255, a), (0, yy), (gloss.get_width(), yy))
    surf.blit(gloss, (5, 5))

    return surf


def _draw_corner_index(
    surf: pygame.Surface,
    rank_txt: str,
    suit_txt: str,
    ink: Tuple[int, int, int],
    x: int,
    y: int,
    scale: float = 1.0,
    flip: bool = False,
):
    fr = max(12, int(18 * scale))
    fs = max(14, int(20 * scale))
    font_r = pygame.font.SysFont("Segoe UI", fr, bold=True)
    font_s = pygame.font.SysFont("Segoe UI", fs, bold=True)
    r_img = font_r.render(rank_txt, True, ink)
    s_img = font_s.render(suit_txt, True, ink)
    if flip:
        r_img = pygame.transform.rotate(r_img, 180)
        s_img = pygame.transform.rotate(s_img, 180)
        surf.blit(r_img, (x - r_img.get_width(), y - r_img.get_height()))
        surf.blit(s_img, (x - s_img.get_width(), y - r_img.get_height() - s_img.get_height() + 2))
    else:
        surf.blit(r_img, (x, y))
        surf.blit(s_img, (x + max(0, (r_img.get_width() - s_img.get_width()) // 2), y + r_img.get_height() - 2))


def _pip_positions(rank: int, cx: int, cy: int, dx: int, dy: int) -> List[Tuple[int, int]]:
    """Standard-ish pip layouts for 1-10."""
    # relative grid
    cols = {
        1: [(0, 0)],
        2: [(0, -1), (0, 1)],
        3: [(0, -1), (0, 0), (0, 1)],
        4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
        5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
        6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)],
        7: [(-1, -1), (1, -1), (0, -0.45), (-1, 0.15), (1, 0.15), (-1, 1), (1, 1)],
        8: [(-1, -1), (1, -1), (0, -0.5), (-1, 0), (1, 0), (0, 0.5), (-1, 1), (1, 1)],
        9: [(-1, -1), (1, -1), (-1, -0.25), (1, -0.25), (0, 0), (-1, 0.55), (1, 0.55), (-1, 1.15), (1, 1.15)],
        10: [
            (-1, -1.1),
            (1, -1.1),
            (0, -0.7),
            (-1, -0.25),
            (1, -0.25),
            (-1, 0.35),
            (1, 0.35),
            (0, 0.7),
            (-1, 1.15),
            (1, 1.15),
        ],
    }
    pts = cols.get(rank, [(0, 0)])
    return [(int(cx + px * dx), int(cy + py * dy)) for px, py in pts]


def render_standard_face(rank: int, suit: str, w: int = STD_W, h: int = STD_H) -> pygame.Surface:
    """Poker-style plastic face card (A–K)."""
    key = (rank, suit, w, h, "plastic3")
    if key in _face_std:
        return _face_std[key]

    red = suit in ("H", "D")
    ink = (185, 28, 38) if red else (22, 24, 30)
    card = _plastic_shell(w, h)

    pip = RANK_PIP.get(rank, str(rank))
    sym = SUIT_SYM.get(suit, "?")
    scale = w / 86.0
    _draw_corner_index(card, pip, sym, ink, 7, 5, scale=scale, flip=False)
    _draw_corner_index(card, pip, sym, ink, w - 7, h - 5, scale=scale, flip=True)

    cx, cy = w // 2, h // 2
    font_big = pygame.font.SysFont("Segoe UI", max(22, int(34 * scale)), bold=True)
    font_face = pygame.font.SysFont("Georgia", max(28, int(42 * scale)), bold=True)

    if rank in (11, 12, 13):
        # Face card: large letter on soft plate + suit
        plate = pygame.Rect(cx - int(22 * scale), cy - int(30 * scale), int(44 * scale), int(60 * scale))
        pygame.draw.ellipse(card, (255, 255, 255, 100), plate)
        pygame.draw.ellipse(card, _shade(ink, 0.35, 180), plate, width=2)
        letter = {"11": "J", "12": "Q", "13": "K"}[str(rank)]
        L = font_face.render(letter, True, ink)
        card.blit(L, L.get_rect(center=(cx, cy - int(6 * scale))))
        S = font_big.render(sym, True, ink)
        card.blit(S, S.get_rect(center=(cx, cy + int(22 * scale))))
    elif rank == 1:
        S = pygame.font.SysFont("Segoe UI", max(36, int(52 * scale)), bold=True).render(sym, True, ink)
        card.blit(S, S.get_rect(center=(cx, cy)))
    else:
        dx = int(16 * scale)
        dy = int(18 * scale)
        fs = max(16, int(22 * scale))
        fsym = pygame.font.SysFont("Segoe UI", fs, bold=True)
        for px, py in _pip_positions(rank, cx, cy, dx, dy):
            img = fsym.render(sym, True, ink)
            card.blit(img, img.get_rect(center=(px, py)))

    # Final top gloss streak (plastic)
    streak = pygame.Surface((w - 14, max(6, h // 8)), pygame.SRCALPHA)
    for yy in range(streak.get_height()):
        a = int(40 * (1 - yy / max(1, streak.get_height())))
        pygame.draw.line(streak, (255, 255, 255, a), (0, yy), (streak.get_width(), yy))
    card.blit(streak, (7, 6))

    _face_std[key] = card
    return card


def render_standard_back(w: int = STD_W, h: int = STD_H, theme: str = "green") -> pygame.Surface:
    key = (w, h, theme, "plastic3")
    if key in _back_std:
        return _back_std[key]

    if theme == "blue":
        base, mid, hi = (22, 48, 110), (36, 78, 160), (70, 120, 210)
    else:
        base, mid, hi = (18, 72, 42), (28, 105, 58), (50, 150, 85)

    surf = _plastic_shell(w, h, face_rgb=(30, 30, 35))
    card = pygame.Surface((w, h), pygame.SRCALPHA)
    card.blit(surf, (0, 0))
    # Colored back panel
    _rounded(card, pygame.Rect(6, 6, w - 12, h - 12), base, 9)
    _rounded(card, pygame.Rect(10, 10, w - 20, h - 20), mid, 8)
    # Diamond lattice
    step = max(8, w // 8)
    for x in range(14, w - 14, step):
        for y in range(14, h - 14, step):
            pygame.draw.circle(card, hi, (x + (y // step % 2) * (step // 2), y), 2)
    # Center medallion
    pygame.draw.ellipse(card, _shade(base, 0.7), pygame.Rect(w // 2 - 22, h // 2 - 28, 44, 56))
    pygame.draw.ellipse(card, (240, 230, 180), pygame.Rect(w // 2 - 18, h // 2 - 24, 36, 48), width=2)
    font = pygame.font.SysFont("Segoe UI", max(11, w // 7), bold=True)
    t = font.render("LAN", True, (245, 240, 220))
    card.blit(t, t.get_rect(center=(w // 2, h // 2)))
    # Gloss
    gloss = pygame.Surface((w - 16, h // 4), pygame.SRCALPHA)
    for yy in range(gloss.get_height()):
        a = int(50 * (1 - yy / max(1, gloss.get_height())))
        pygame.draw.line(gloss, (255, 255, 255, a), (0, yy), (gloss.get_width(), yy))
    card.blit(gloss, (8, 10))

    _back_std[key] = card
    return card


def render_uno_face(
    color: Optional[str],
    kind: str,
    label: str,
    w: int = STD_W,
    h: int = STD_H,
) -> pygame.Surface:
    """Plastic color-matching game card (UNO-style original art)."""
    key = (color, kind, label, w, h, "plastic3")
    if key in _face_uno:
        return _face_uno[key]

    is_wild = kind in ("wild", "wild4")
    # Dark plastic body with thick colored border like real game cards
    if is_wild:
        border = (35, 35, 40)
        face_rgb = (245, 243, 238)
    else:
        border = UNO_RGB.get(color or "R", (180, 40, 40))
        face_rgb = (250, 248, 244)

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Shadow
    for i, a in enumerate((30, 50)):
        _rounded(surf, pygame.Rect(3 + i, 4 + i, w - 2, h - 2), (0, 0, 0, a), 14)

    # Outer black edge
    _rounded(surf, pygame.Rect(0, 0, w, h), (20, 20, 24), 13)
    # Colored plastic border
    _rounded(surf, pygame.Rect(2, 2, w - 4, h - 4), border, 12)
    # Inner cream
    _rounded(surf, pygame.Rect(8, 8, w - 16, h - 16), face_rgb, 10)
    # subtle gradient on cream
    for yy in range(10, h - 10):
        t = (yy - 10) / max(1, h - 20)
        col = (
            _clamp(int(face_rgb[0] - t * 8)),
            _clamp(int(face_rgb[1] - t * 8)),
            _clamp(int(face_rgb[2] - t * 10)),
        )
        pygame.draw.line(surf, col, (12, yy), (w - 13, yy))

    cx, cy = w // 2, h // 2
    oval = pygame.Rect(14, 22, w - 28, h - 44)

    if is_wild:
        # Four glossy color wedges
        pygame.draw.ellipse(surf, (30, 30, 35), oval)
        pygame.draw.polygon(surf, UNO_RGB["R"], [(cx, cy), (cx, oval.top + 4), (oval.right - 2, cy)])
        pygame.draw.polygon(surf, UNO_RGB["Y"], [(cx, cy), (cx, oval.top + 4), (oval.left + 2, cy)])
        pygame.draw.polygon(surf, UNO_RGB["G"], [(cx, cy), (cx, oval.bottom - 4), (oval.right - 2, cy)])
        pygame.draw.polygon(surf, UNO_RGB["B"], [(cx, cy), (cx, oval.bottom - 4), (oval.left + 2, cy)])
        # center white badge
        badge = pygame.Rect(cx - 20, cy - 24, 40, 48)
        pygame.draw.ellipse(surf, (250, 248, 244), badge)
        pygame.draw.ellipse(surf, (200, 200, 205), badge, width=2)
        text_col = (30, 30, 35)
    else:
        col = UNO_RGB.get(color or "R", (180, 40, 40))
        # Raised plastic oval
        shadow_oval = oval.move(2, 3)
        pygame.draw.ellipse(surf, _shade(col, 0.45), shadow_oval)
        pygame.draw.ellipse(surf, col, oval)
        # specular on oval
        hi = pygame.Rect(oval.x + 10, oval.y + 8, oval.w - 22, oval.h // 3)
        pygame.draw.ellipse(surf, _shade(col, 1.15, 40), hi)
        pygame.draw.ellipse(surf, _shade(col, 0.55), oval, width=3)
        text_col = (30, 30, 30) if color == "Y" else (255, 255, 255)

    # Center symbol / number with soft emboss
    font_big = pygame.font.SysFont("Segoe UI", max(20, h // 4), bold=True)
    font_sm = pygame.font.SysFont("Segoe UI", max(12, h // 7), bold=True)

    def center_symbol():
        if kind == "skip":
            r = h // 7
            pygame.draw.circle(surf, text_col, (cx, cy), r, width=4)
            pygame.draw.line(surf, text_col, (cx - r + 2, cy + r - 2), (cx + r - 2, cy - r + 2), 4)
        elif kind == "reverse":
            pygame.draw.arc(surf, text_col, pygame.Rect(cx - 18, cy - 16, 32, 32), 0.3, 2.9, 4)
            pygame.draw.arc(surf, text_col, pygame.Rect(cx - 14, cy - 12, 32, 32), 3.4, 6.0, 4)
            pygame.draw.polygon(surf, text_col, [(cx + 16, cy - 12), (cx + 6, cy - 18), (cx + 8, cy - 4)])
            pygame.draw.polygon(surf, text_col, [(cx - 16, cy + 12), (cx - 6, cy + 18), (cx - 8, cy + 4)])
        else:
            # emboss: dark under, light over, main
            img = font_big.render(label, True, text_col)
            rect = img.get_rect(center=(cx, cy))
            shadow = font_big.render(label, True, (0, 0, 0, 80) if len(text_col) == 3 else (0, 0, 0))
            # simple offset shadow
            sh_img = font_big.render(label, True, _shade(text_col, 0.3))
            surf.blit(sh_img, (rect.x + 1, rect.y + 2))
            surf.blit(img, rect)

    center_symbol()

    # Corner indices on colored border feel
    corner_col = text_col if not is_wild else (40, 40, 45)
    if not is_wild:
        # small white corner tabs
        pygame.draw.circle(surf, (250, 248, 244), (16, 18), 11)
        pygame.draw.circle(surf, (250, 248, 244), (w - 16, h - 18), 11)
        corner_col = border
    # Compact corner text (keep readable when rotated)
    if kind == "wild":
        lab = "W"
    elif kind == "wild4":
        lab = "+4"
    elif kind == "skip":
        lab = "⊘"
    elif kind == "reverse":
        lab = "⇄"
    elif kind == "draw2":
        lab = "+2"
    else:
        lab = label if len(label) <= 2 else label[:2]
    pip = font_sm.render(lab, True, corner_col)
    surf.blit(pip, pip.get_rect(center=(16, 18)))
    pip2 = pygame.transform.rotate(pip, 180)
    surf.blit(pip2, pip2.get_rect(center=(w - 16, h - 18)))

    # Glossy plastic sheen
    gloss = pygame.Surface((w - 14, h // 3), pygame.SRCALPHA)
    for yy in range(gloss.get_height()):
        a = int(55 * (1 - yy / max(1, gloss.get_height())) ** 1.3)
        pygame.draw.line(gloss, (255, 255, 255, a), (0, yy), (gloss.get_width(), yy))
    surf.blit(gloss, (7, 7))

    _face_uno[key] = surf
    return surf


def render_uno_back(w: int = STD_W, h: int = STD_H) -> pygame.Surface:
    return render_standard_back(w, h, theme="blue")


def clear_caches():
    _face_std.clear()
    _face_uno.clear()
    _back_std.clear()
