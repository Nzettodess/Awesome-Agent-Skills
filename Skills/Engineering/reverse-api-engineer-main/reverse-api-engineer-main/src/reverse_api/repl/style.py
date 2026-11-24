"""Design tokens for the interactive session, from design/design-system.md (dark terminal)."""

from __future__ import annotations

import re
import shutil

from pygments.style import Style as PygmentsStyle
from pygments.token import Comment, Keyword, Name, Number, Operator, Punctuation, String
from pygments.token import Text as TextToken
from rich.highlighter import RegexHighlighter
from rich.style import Style as RichStyle
from rich.syntax import PygmentsSyntaxTheme
from rich.theme import Theme

from ..theme import COLOR_INK, COLOR_INK_SOFT, COLOR_MINT, COLOR_PRIMARY, COLOR_SKY, THEME_DIM

INK = COLOR_INK
INK_SOFT = COLOR_INK_SOFT
DIM = THEME_DIM
PINK = COLOR_PRIMARY
MINT = COLOR_MINT
SKY = COLOR_SKY
AMBER = "#e8b86d"
HAIRLINE = "#3a332d"

# Tool steps take the website's pastel section colors, one per kind of action.
PASTEL_READ = "#bfe0ff"
PASTEL_WRITE = "#c3ecd2"
PASTEL_RUN = "#ffd6b8"
PASTEL_OTHER = "#d9cff0"

# Status chips: the lavender band and the yellow post-it.
CHIP_LAVENDER = "#e8e3f0"
CHIP_YELLOW = "#fdf08a"
CHIP_INK = "#1f1f1f"
GAUGE_EMPTY = "#a89fba"

PULSE = ["#5a2a3c", "#8a2f55", "#c2346f", "#ff3d8b", "#c2346f", "#8a2f55"]


class RaeCode(PygmentsStyle):
    """Code colors from the design tokens."""

    styles = {
        TextToken: INK,
        Keyword: f"bold {PINK}",
        Keyword.Constant: SKY,
        Keyword.Namespace: PINK,
        Name: INK,
        Name.Function: f"bold {AMBER}",
        Name.Class: f"bold {AMBER}",
        Name.Builtin: PASTEL_OTHER,
        Name.Builtin.Pseudo: f"italic {SKY}",
        Name.Decorator: AMBER,
        Name.Namespace: INK_SOFT,
        String: MINT,
        String.Doc: f"italic {DIM}",
        String.Interpol: AMBER,
        String.Escape: AMBER,
        Number: SKY,
        Comment: f"italic {DIM}",
        Operator: INK_SOFT,
        Operator.Word: f"bold {PINK}",
        Punctuation: INK_SOFT,
    }


CODE_THEME = PygmentsSyntaxTheme(RaeCode)

THEME = Theme(
    {
        "markdown.paragraph": INK,
        "markdown.text": INK,
        "markdown.strong": f"bold {INK}",
        "markdown.em": f"italic {PINK}",
        "markdown.code": MINT,
        "markdown.item.bullet": DIM,
        "markdown.item.number": DIM,
        "markdown.link": SKY,
        "markdown.link_url": f"underline {SKY}",
        "markdown.hr": HAIRLINE,
        "markdown.h1": f"bold {INK}",
        "markdown.h2": f"bold {INK}",
        "markdown.h3": f"bold {INK_SOFT}",
        "markdown.block_quote": f"italic {INK_SOFT}",
        "rae.method": f"bold {SKY}",
        "rae.ok": f"bold {MINT}",
        "rae.fail": f"bold {PINK}",
        "rae.url": f"underline {INK_SOFT}",
        "rae.number": SKY,
        "rae.string": MINT,
        "rae.key": AMBER,
        "rae.file": f"underline {INK}",
    }
)


class ReceiptHighlighter(RegexHighlighter):
    """Colors what is worth spotting in a tool result: methods, statuses, URLs, numbers, JSON."""

    base_style = "rae."
    highlights = [
        r"^(?P<ok>[23]\d\d)\b",
        r"^(?P<fail>[45]\d\d)\b",
        r"\b(?P<method>GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b",
        r"(?P<url>https?://[^\s·]+|(?<![\w/])/[\w\-./?=&%{}]+)",
        r"(?P<string>\"[^\"]*\")",
        r"(?P<key>\b\w+)(?=: )",
        r"(?P<file>\b[\w\-]+\.(?:py|json|md|ts|js|csv|go|java|rb|php|cs|c|psm1)\b)",
        r"(?P<number>(?<![\w/.])\d[\d,.]*(?:\s?(?:kB|MB|ms|s))?\b)",
    ]


RECEIPT_HL = ReceiptHighlighter()


def width() -> int:
    """The terminal's real width; layouts that need room clamp their own sizes."""
    return max(1, shutil.get_terminal_size().columns)


def height() -> int:
    return max(10, shutil.get_terminal_size().lines)


def pt_style(style: RichStyle | None) -> str:
    """A rich style as a prompt_toolkit fragment style."""
    if style is None:
        return ""
    parts = []
    if style.color is not None and not style.color.is_default:
        parts.append(f"fg:{style.color.get_truecolor().hex}")
    if style.bgcolor is not None and not style.bgcolor.is_default:
        parts.append(f"bg:{style.bgcolor.get_truecolor().hex}")
    # Many terminals ignore SGR dim, so dim text gets an explicit color.
    if style.dim and (style.color is None or style.color.is_default):
        parts.append(f"fg:{DIM}")
    for attr in ("bold", "italic", "underline", "reverse", "strike"):
        if getattr(style, attr):
            parts.append(attr)
    return " ".join(parts)


def rich_style(pt: str) -> str | None:
    """A prompt_toolkit fragment style as a rich style, for printing the session to the terminal."""
    fg = re.search(r"fg:(#[0-9a-fA-F]{6})", pt)
    bg = re.search(r"bg:(#[0-9a-fA-F]{6})", pt)
    attrs = [a for a in ("bold", "italic", "underline") if a in pt.split()]
    out = " ".join(attrs + ([fg.group(1)] if fg else []) + ([f"on {bg.group(1)}"] if bg else []))
    return out or None
