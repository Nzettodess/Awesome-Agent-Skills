"""The brand asterisk, rasterized in half-block characters so it can turn."""

from __future__ import annotations

import math

LOGO_COLS, LOGO_ROWS = 24, 11  # characters; each holds two pixels stacked with half blocks
LOGO_SHADES = ["#ff5c9c", "#ff3d8b", "#e8357c", "#c92f6c", "#a8295c", "#86234d"]


def logo_rows(theta: float) -> list[list[tuple[str, str]]]:
    """rae's italic six-arm asterisk with teardrop arms, at angle ``theta``, as prompt_toolkit fragment rows."""
    w, h = LOGO_COLS, LOGO_ROWS * 2
    cx, cy = (w - 1) / 2, (h - 1) / 2
    radius = min(cx, cy) * 0.98
    tip_c, tip_r = 0.70 * radius, 0.24 * radius
    arms = [(math.cos(theta + k * math.pi / 3 + math.pi / 2), math.sin(theta + k * math.pi / 3 + math.pi / 2)) for k in range(6)]

    def pixel(px: int, py: int) -> str | None:
        x, y = px - cx, cy - py
        x -= y * 0.22  # the italic slant of the Fraunces asterisk
        r = math.hypot(x, y)
        if r <= radius * 0.13:
            return LOGO_SHADES[0]
        for ux, uy in arms:
            t = x * ux + y * uy
            d = abs(y * ux - x * uy)
            if t <= 0 or t > tip_c + tip_r:
                continue
            half = tip_r * (t / tip_c) ** 0.85 if t <= tip_c else math.sqrt(max(0.0, tip_r**2 - (t - tip_c) ** 2))
            if d <= half:
                shine = 0.5 + 0.5 * math.cos(math.atan2(y, x) + theta * 3)
                return LOGO_SHADES[min(len(LOGO_SHADES) - 1, int((r / radius) * 4 + (1 - shine) * 2))]
        return None

    rows = []
    for j in range(LOGO_ROWS):
        row = []
        for i in range(LOGO_COLS):
            top, bottom = pixel(i, 2 * j), pixel(i, 2 * j + 1)
            if top and bottom:
                row.append((f"fg:{top} bg:{bottom}", "▀"))
            elif top:
                row.append((f"fg:{top}", "▀"))
            elif bottom:
                row.append((f"fg:{bottom}", "▄"))
            else:
                row.append(("", " "))
        rows.append(row)
    return rows
