from __future__ import annotations
"""
NEXUS HTML Component Builders
All functions return raw HTML strings with 100% inline styles.
No custom CSS class references — works regardless of CSS injection state.
"""
from .theme import C, FONT, FONT_MONO


# ── Primitives ────────────────────────────────────────────────────────────────

def spacer(px: int = 16) -> str:
    return f'<div style="height:{px}px"></div>'


def divider_line() -> str:
    return (
        f'<div style="height:1px;background:linear-gradient(to right,'
        f'{C.BORDER},transparent);margin:24px 0;"></div>'
    )


def badge(text: str, color: str = C.TEAL, bg: str | None = None) -> str:
    bg = bg or f"rgba({_hex_to_rgb_str(color)},0.12)"
    border = f"rgba({_hex_to_rgb_str(color)},0.25)"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'padding:3px 10px;background:{bg};border:1px solid {border};'
        f'border-radius:100px;font-size:0.65rem;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.1em;color:{color};'
        f'font-family:{FONT};">{text}</span>'
    )


def tag(text: str, color: str = C.T3) -> str:
    bg     = f"rgba({_hex_to_rgb_str(color)},0.1)"
    border = f"rgba({_hex_to_rgb_str(color)},0.22)"
    return (
        f'<span style="display:inline-block;padding:3px 10px;'
        f'background:{bg};border:1px solid {border};border-radius:6px;'
        f'font-size:0.72rem;font-weight:600;color:{color};'
        f'font-family:{FONT};">{text}</span>'
    )


# ── Section header ─────────────────────────────────────────────────────────────

def section_header(label: str, title: str, subtitle: str = "") -> str:
    sub = (
        f'<div style="font-size:0.82rem;color:{C.T4};margin-bottom:20px;'
        f'line-height:1.6;font-family:{FONT};">{subtitle}</div>'
        if subtitle else ""
    )
    return (
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
        f'  <span style="font-size:0.63rem;font-weight:700;text-transform:uppercase;'
        f'    letter-spacing:0.2em;color:{C.T4};font-family:{FONT};white-space:nowrap;">'
        f'    {label}</span>'
        f'  <div style="flex:1;height:1px;background:linear-gradient(to right,{C.BORDER},transparent);"></div>'
        f'</div>'
        f'<div style="font-size:1.35rem;font-weight:800;color:{C.T1};letter-spacing:-0.02em;'
        f'margin-bottom:4px;font-family:{FONT};">{title}</div>'
        f'{sub}'
    )


# ── Card ───────────────────────────────────────────────────────────────────────

def glass_card(content: str, padding: str = "24px", extra_style: str = "") -> str:
    return (
        f'<div style="background:{C.CARD};border:1px solid {C.BORDER};'
        f'border-radius:16px;padding:{padding};backdrop-filter:blur(12px);'
        f'-webkit-backdrop-filter:blur(12px);'
        f'box-shadow:0 4px 32px rgba(0,0,0,0.35),inset 0 1px 0 rgba(255,255,255,0.04);'
        f'{extra_style}">'
        f'{content}'
        f'</div>'
    )


# ── Metric row (for cards) ─────────────────────────────────────────────────────

def metric_row(label: str, value: str, value_color: str = C.T1,
               bottom_border: bool = True) -> str:
    border = f"border-bottom:1px solid {C.BORDER};" if bottom_border else ""
    return (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;padding:7px 0;{border}">'
        f'  <span style="font-size:0.78rem;color:{C.T4};font-family:{FONT};">{label}</span>'
        f'  <span style="font-size:0.88rem;font-weight:700;color:{value_color};'
        f'    font-family:{FONT};">{value}</span>'
        f'</div>'
    )


# ── Code chip ──────────────────────────────────────────────────────────────────

def code_chip(text: str) -> str:
    return (
        f'<code style="color:{C.TEAL};background:{C.TEAL_DIM};'
        f'border:1px solid {C.TEAL_BORDER};border-radius:5px;'
        f'padding:2px 8px;font-size:0.7rem;font-family:{FONT_MONO};">'
        f'{text}</code>'
    )


# ── Gradient text ──────────────────────────────────────────────────────────────

def gradient_text(text: str, grad: str = "linear-gradient(135deg,#00d4aa,#67e8f9)",
                  size: str = "inherit", weight: str = "inherit") -> str:
    return (
        f'<span style="background:{grad};-webkit-background-clip:text;'
        f'-webkit-text-fill-color:transparent;background-clip:text;'
        f'font-size:{size};font-weight:{weight};font-family:{FONT};">{text}</span>'
    )


# ── Progress bar ───────────────────────────────────────────────────────────────

def progress_bar(pct: int, color: str = C.GREEN, height: str = "4px") -> str:
    grad = f"linear-gradient(90deg,{color},{_lighten(color)})"
    return (
        f'<div style="height:{height};border-radius:2px;background:rgba(255,255,255,0.06);'
        f'overflow:hidden;margin-top:10px;">'
        f'  <div style="height:100%;width:{pct}%;border-radius:2px;background:{grad};'
        f'    transition:width 0.5s ease;"></div>'
        f'</div>'
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _hex_to_rgb_str(hex_color: str) -> str:
    """Convert #rrggbb to 'r,g,b' string for rgba()."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r},{g},{b}"
    return "255,255,255"


def _lighten(hex_color: str) -> str:
    """Return a slightly lighter version of the color (mix with white)."""
    return hex_color  # Simplified — gradient from same color looks good enough
