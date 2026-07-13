
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1350
MARGIN = 80
CONTENT_W = WIDTH - 2 * MARGIN
INNER_PAD = 32
BOTTOM_LIMIT = HEIGHT - 70

BG = "#0B0E14"
PANEL = "#121826"
PANEL_ALT = "#152033"
TEXT = "#E8EEF9"
MUTED = "#8AA0C5"
BORDER = "#243047"

CATEGORY_COLORS = {
    "official": "#6C5CE7",
    "research": "#00B894",
    "open_source": "#0984E3",
    "community": "#7AB7FF",
    "media": "#FDCB6E",
    "model_release": "#6C5CE7",
    "tooling_sdk": "#0984E3",
    "general": "#7AB7FF",
}

# Qualitative priority styling — deliberately no raw numbers here. The badge
# color + label + one plain-English reason line are the entire signal; a
# reader shouldn't need to know how the score was computed to act on it.
# No emoji: color fonts aren't reliably available across dev (Windows) and
# prod (Vercel's Linux container), so glyphs render as tofu boxes on at
# least one of the two — color-coding alone carries the signal instead.
PRIORITY_STYLE = {
    "Read Now": {"color": "#FF6B6B"},
    "Read This Week": {"color": "#FDCB6E"},
    "Skim": {"color": "#7AB7FF"},
    "Ignore": {"color": "#5C6B84"},
}


def _load_font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


class Fonts:
    hero = None
    h2 = None
    body = None
    body_sm = None
    tag = None
    caption = None

    @classmethod
    def load(cls):
        if cls.hero is None:
            cls.hero = _load_font(56, bold=True)
            cls.h2 = _load_font(38, bold=True)
            cls.body = _load_font(30, bold=False)
            cls.body_sm = _load_font(25, bold=False)
            cls.tag = _load_font(23, bold=True)
            cls.caption = _load_font(21, bold=False)
        return cls


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    if not text:
        return []
    words = str(text).split()
    lines: list[str] = []
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _draw_lines(draw: ImageDraw.ImageDraw, x: int, y: int, lines: list[str], font, fill: str, line_height: int) -> int:
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def _base(draw: ImageDraw.ImageDraw, accent: str):
    draw.rectangle([0, 0, WIDTH, 14], fill=accent)
    draw.rounded_rectangle([40, 40, WIDTH - 40, HEIGHT - 40], radius=36, outline=BORDER, width=2)


def _pill(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font, fill: str, text_color: str = "white", pad_x: int = 20, pad_y: int = 10) -> int:
    w = draw.textbbox((0, 0), text, font=font)[2]
    draw.rounded_rectangle([x, y, x + w + pad_x * 2, y + font.size + pad_y * 2], radius=(font.size + pad_y * 2) // 2, fill=fill)
    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=text_color)
    return x + w + pad_x * 2


def _panel_block(
    draw: ImageDraw.ImageDraw,
    y: int,
    *,
    icon_title: str,
    title_color: str,
    body: str,
    font_body,
    max_lines: int,
    fill: str = PANEL,
    line_height: int = 38,
    x: int = MARGIN,
    width: int = CONTENT_W,
    gap_after: int = 20,
) -> int:
    """Draws one title+body card sized to its actual wrapped content, and
    returns the y cursor for the next element. No fixed panel height, so a
    short body never leaves a slab of empty space below it."""
    body = (body or "").strip()
    if not body:
        return y
    lines = _wrap(draw, body, font_body, width - 2 * INNER_PAD)[:max_lines]
    if not lines:
        return y
    header_h = 44
    panel_h = INNER_PAD + header_h + len(lines) * line_height + (INNER_PAD - 8)
    if y + panel_h > BOTTOM_LIMIT:
        available_lines = max(1, (BOTTOM_LIMIT - y - INNER_PAD - header_h - (INNER_PAD - 8)) // line_height)
        lines = lines[:available_lines]
        panel_h = INNER_PAD + header_h + len(lines) * line_height + (INNER_PAD - 8)
        if not lines or y + panel_h > BOTTOM_LIMIT:
            return y
    draw.rounded_rectangle([x, y, x + width, y + panel_h], radius=26, fill=fill)
    draw.text((x + INNER_PAD, y + 20), icon_title, font=Fonts.tag, fill=title_color)
    _draw_lines(draw, x + INNER_PAD, y + 20 + header_h, lines, font_body, TEXT, line_height)
    return y + panel_h + gap_after


def _bullet_cards(
    draw: ImageDraw.ImageDraw,
    y: int,
    bullets: list[str],
    *,
    font,
    accent: str,
    max_items: int,
    line_height: int = 36,
    fill: str = PANEL,
) -> int:
    for bullet in bullets[:max_items]:
        lines = _wrap(draw, bullet, font, CONTENT_W - 2 * INNER_PAD - 36)[:4]
        if not lines:
            continue
        card_h = INNER_PAD + len(lines) * line_height + (INNER_PAD - 10)
        if y + card_h > BOTTOM_LIMIT:
            break
        draw.rounded_rectangle([MARGIN, y, MARGIN + CONTENT_W, y + card_h], radius=22, fill=fill)
        draw.ellipse([MARGIN + 22, y + INNER_PAD + 6, MARGIN + 34, y + INNER_PAD + 18], fill=accent)
        _draw_lines(draw, MARGIN + 54, y + INNER_PAD, lines, font, TEXT, line_height)
        y += card_h + 16
    return y


def _priority_style(recommendation: str) -> dict:
    return PRIORITY_STYLE.get(recommendation, PRIORITY_STYLE["Skim"])


def _format_chart_value(value: float, unit: str) -> str:
    if unit in ("$", "€", "£", "¥"):
        return f"{unit}{value:g}"
    if not unit:
        return f"{value:g}"
    return f"{value:g} {unit}"


def _footer(draw: ImageDraw.ImageDraw, data: dict):
    source = data.get("source_logo_text", "")
    date = data.get("date", "")
    if not source and not date:
        return
    draw.text((MARGIN, 1255), f"{source}  •  {date}" if source and date else (source or date), font=Fonts.caption, fill=MUTED)


def render_slide(slide_type: str, data: dict, out_path: str) -> str:
    Fonts.load()
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    category = data.get("category_tag", "general")
    accent = CATEGORY_COLORS.get(category, CATEGORY_COLORS["general"])
    _base(draw, accent)

    if slide_type == "hook":
        right_edge = MARGIN + CONTENT_W
        cat_end = _pill(draw, MARGIN, 76, category.upper(), Fonts.tag, accent)

        rec = data.get("recommendation", "Skim")
        style = _priority_style(rec)
        pill_text = rec.upper()
        pill_w = draw.textbbox((0, 0), pill_text, font=Fonts.tag)[2] + 40
        _pill(draw, right_edge - pill_w, 76, pill_text, Fonts.tag, style["color"], text_color="#0B0E14")

        y = 150
        headline_lines = _wrap(draw, data.get("headline", ""), Fonts.hero, CONTENT_W)[:4]
        y = _draw_lines(draw, MARGIN, y, headline_lines, Fonts.hero, TEXT, 66) + 6

        reason = (data.get("recommendation_reason") or "").strip()
        if reason:
            reason_lines = _wrap(draw, reason, Fonts.body_sm, CONTENT_W)[:2]
            y = _draw_lines(draw, MARGIN, y + 6, reason_lines, Fonts.body_sm, style["color"], 32) + 16

        y = _panel_block(
            draw, y,
            icon_title="EXECUTIVE SUMMARY", title_color=accent,
            body=data.get("executive_summary", ""), font_body=Fonts.body, max_lines=7,
            fill=PANEL_ALT, line_height=40,
        )

        whats_new = (data.get("whats_new") or "").strip()
        if whats_new:
            y = _panel_block(
                draw, y,
                icon_title="WHAT'S NEW", title_color=accent,
                body=whats_new, font_body=Fonts.body_sm, max_lines=3,
                fill=PANEL, line_height=32,
            )

        _footer(draw, data)

    elif slide_type == "what_changed":
        draw.text((MARGIN, 80), "What Changed", font=Fonts.h2, fill=TEXT)
        y = 150

        bullets = list(data.get("bullets", []) or [])
        key_innovation = (data.get("key_innovation") or "").strip()
        if key_innovation and key_innovation not in " ".join(bullets):
            bullets = [key_innovation] + bullets

        y = _bullet_cards(draw, y, bullets, font=Fonts.body, accent=accent, max_items=4, line_height=38)
        _footer(draw, data)

    elif slide_type == "strategic_impact":
        draw.text((MARGIN, 80), "Strategic Impact", font=Fonts.h2, fill=TEXT)
        y = 150

        y = _panel_block(
            draw, y,
            icon_title="ROADMAP", title_color="#7AB7FF",
            body=data.get("roadmap_relevance", ""), font_body=Fonts.body, max_lines=5,
            fill=PANEL_ALT, line_height=38,
        )
        y = _panel_block(
            draw, y,
            icon_title="BUSINESS METRIC", title_color="#00B894",
            body=data.get("business_metric_impact", ""), font_body=Fonts.body, max_lines=5,
            fill=PANEL, line_height=38,
        )
        y = _panel_block(
            draw, y,
            icon_title="COMPETITIVE READ", title_color="#FDCB6E",
            body=data.get("competitive_impact", ""), font_body=Fonts.body_sm, max_lines=5,
            fill=PANEL_ALT, line_height=32,
        )

        extra = [b for b in (data.get("product_business_bullets") or []) if b][:2]
        if extra and y < BOTTOM_LIMIT - 80:
            draw.text((MARGIN, y + 4), "ALSO WORTH NOTING", font=Fonts.caption, fill=MUTED)
            y += 40
            y = _bullet_cards(draw, y, extra, font=Fonts.body_sm, accent=MUTED, max_items=2, line_height=30, fill=PANEL)
        _footer(draw, data)

    elif slide_type == "chart":
        chart = data.get("chart", {}) or {}
        draw.text((MARGIN, 80), chart.get("title", "Comparison"), font=Fonts.h2, fill=TEXT)
        unit = chart.get("unit", "")
        series = (chart.get("series") or [])[:5]

        y = 180
        if series:
            max_val = max((abs(p.get("value", 0)) for p in series), default=1) or 1
            label_col_w = 300
            bar_area_w = CONTENT_W - label_col_w - 140
            bar_h = 64
            gap = 46
            for point in series:
                label = str(point.get("label", ""))
                value = point.get("value", 0)
                label_lines = _wrap(draw, label, Fonts.body_sm, label_col_w)[:2]
                _draw_lines(draw, MARGIN, y + (bar_h - len(label_lines) * 30) // 2, label_lines, Fonts.body_sm, TEXT, 30)
                bar_x = MARGIN + label_col_w
                bar_w = max(10, int(bar_area_w * (abs(value) / max_val)))
                draw.rounded_rectangle([bar_x, y, bar_x + bar_w, y + bar_h], radius=14, fill=accent)
                value_text = _format_chart_value(value, unit)
                draw.text((bar_x + bar_w + 20, y + (bar_h - 30) // 2), value_text, font=Fonts.body, fill=TEXT)
                y += bar_h + gap
        draw.text((MARGIN, min(y + 10, BOTTOM_LIMIT)), "Figures as reported in the source.", font=Fonts.caption, fill=MUTED)
        _footer(draw, data)

    elif slide_type == "recommendation":
        rec = data.get("recommendation", "Skim")
        style = _priority_style(rec)
        pill_text = rec.upper()
        _pill(draw, MARGIN, 78, pill_text, Fonts.h2, style["color"], text_color="#0B0E14", pad_x=28, pad_y=14)
        y = 78 + Fonts.h2.size + 28 + 24

        reason = (data.get("recommendation_reason") or "").strip()
        if reason:
            reason_lines = _wrap(draw, reason, Fonts.body_sm, CONTENT_W)[:2]
            y = _draw_lines(draw, MARGIN, y, reason_lines, Fonts.body_sm, MUTED, 32) + 24

        y = _panel_block(
            draw, y,
            icon_title="RECOMMENDED ACTION", title_color=accent,
            body=data.get("recommended_action", ""), font_body=Fonts.body, max_lines=4,
            fill=PANEL_ALT, line_height=38,
        )
        y = _panel_block(
            draw, y,
            icon_title="PM TAKEAWAY", title_color=accent,
            body=data.get("pm_takeaway", ""), font_body=Fonts.body, max_lines=5,
            fill=PANEL, line_height=38,
        )

        links = list(dict.fromkeys([u for u in (data.get("source_links") or []) if u]))[:4]
        if links and y < BOTTOM_LIMIT - 60:
            draw.text((MARGIN, y), "SOURCES", font=Fonts.caption, fill=MUTED)
            y += 34
            for link in links:
                if y > BOTTOM_LIMIT:
                    break
                line = _wrap(draw, link, Fonts.caption, CONTENT_W - 30)[:1]
                y = _draw_lines(draw, MARGIN, y, [f"• {line[0]}" if line else f"• {link}"], Fonts.caption, accent, 30)
        _footer(draw, data)

    else:
        raise ValueError(f"Unsupported slide type: {slide_type}")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    return out_path
