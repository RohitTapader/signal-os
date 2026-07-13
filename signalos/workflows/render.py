
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1350
BG = "#0B0E14"
PANEL = "#121826"
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


def _merge_context(context: str, whats_new: str) -> str:
    context = (context or "").strip()
    whats_new = (whats_new or "").strip()
    if not context and not whats_new:
        return ""
    if not whats_new or whats_new.lower() in context.lower():
        return context
    if context.lower() in whats_new.lower():
        return whats_new
    return f"{context} {whats_new}".strip()


def _base(draw: ImageDraw.ImageDraw, accent: str):
    draw.rectangle([0, 0, WIDTH, 14], fill=accent)
    draw.rounded_rectangle([40, 40, WIDTH - 40, HEIGHT - 40], radius=36, outline=BORDER, width=2)


def _panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str = PANEL):
    draw.rounded_rectangle(box, radius=26, fill=fill)


def render_slide(slide_type: str, data: dict, out_path: str) -> str:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    category = data.get("category_tag", "general")
    accent = CATEGORY_COLORS.get(category, CATEGORY_COLORS["general"])
    _base(draw, accent)

    font_xl = _load_font(50, bold=True)
    font_l = _load_font(38, bold=True)
    font_m = _load_font(26, bold=False)
    font_s = _load_font(22, bold=False)
    font_tag = _load_font(22, bold=True)
    font_sm = _load_font(18, bold=False)

    if slide_type == "title":
        score = data.get("signal_score", 0)
        rec = data.get("recommendation", "")
        draw.rounded_rectangle([80, 80, 360, 126], radius=22, fill=accent)
        draw.text((104, 90), data.get("category_tag", "GENERAL").upper(), font=font_tag, fill="white")

        draw.rounded_rectangle([840, 80, 1000, 126], radius=22, fill=PANEL)
        draw.text((866, 90), f"{score}/100", font=font_tag, fill=TEXT)

        headline = data.get("headline", "")
        y = 170
        for line in _wrap(draw, headline, font_xl, 920)[:3]:
            draw.text((90, y), line, font=font_xl, fill=TEXT)
            y += 58

        merged_context = _merge_context(data.get("context", ""), data.get("whats_new", ""))
        if merged_context:
            _panel(draw, (90, y + 10, 990, y + 200), fill="#101724")
            draw.text((120, y + 24), "Context", font=font_tag, fill=accent)
            y = _draw_lines(draw, 120, y + 54, _wrap(draw, merged_context, font_sm, 820)[:6], font_sm, TEXT, 24) + 8

        summary = data.get("executive_summary", "")
        if summary:
            _panel(draw, (90, y + 10, 990, y + 280), fill="#152033")
            draw.text((120, y + 24), "Executive summary", font=font_tag, fill=accent)
            _draw_lines(draw, 120, y + 54, _wrap(draw, summary, font_sm, 820)[:7], font_sm, TEXT, 24)

        draw.text((90, 1240), f"{data.get('source_logo_text','Source')} • {data.get('date','')}", font=font_s, fill=MUTED)
        draw.rounded_rectangle([760, 1220, 1000, 1270], radius=18, fill=PANEL)
        draw.text((784, 1232), rec or data.get("confidence_badge", ""), font=font_s, fill=TEXT)

    elif slide_type == "what_changed":
        draw.text((80, 90), "What's Changed / What's New", font=font_l, fill=TEXT)

        bullets = list(data.get("bullets", []) or [])
        key_innovation = (data.get("key_innovation") or "").strip()
        if key_innovation and key_innovation not in " ".join(bullets):
            bullets = [key_innovation] + bullets

        card_y = 160
        for bullet in bullets[:5]:
            card_h = 140
            _panel(draw, (80, card_y, 1000, card_y + card_h), fill="#101724")
            lines = _wrap(draw, f"• {bullet}", font_m, 840)[:4]
            _draw_lines(draw, 110, card_y + 18, lines, font_m, TEXT, 30)
            card_y += card_h + 14
            if card_y > 1200:
                break

        draw.text((80, 1280), data.get("source_url", ""), font=font_s, fill=MUTED)

    elif slide_type == "why_it_matters":
        draw.text((80, 90), "Why it matters", font=font_l, fill=TEXT)
        y = 160

        product_business = data.get("product_business_bullets") or []
        if not product_business:
            product = data.get("product_impact", "")
            business = data.get("business_impact", "")
            if product:
                product_business.append(product)
            if business:
                product_business.append(business)

        if product_business:
            _panel(draw, (80, y, 1000, y + 420), fill="#101724")
            draw.text((110, y + 18), "Product & business impact", font=font_tag, fill=accent)
            by = y + 52
            for point in product_business[:5]:
                lines = _wrap(draw, f"• {point}", font_sm, 820)[:3]
                by = _draw_lines(draw, 110, by, lines, font_sm, TEXT, 26) + 6
            y += 440

        competitive = data.get("competitive_impact", "")
        if competitive:
            _panel(draw, (80, y, 1000, min(y + 520, 1280)), fill="#152033")
            draw.text((110, y + 18), "Competitive intelligence", font=font_tag, fill=accent)
            draw.text((110, y + 50), "Edge, rivals & business metrics", font=font_sm, fill=MUTED)
            _draw_lines(draw, 110, y + 78, _wrap(draw, competitive, font_sm, 820)[:12], font_sm, TEXT, 26)

    elif slide_type == "recommendation":
        draw.text((80, 90), "Recommendation", font=font_l, fill=TEXT)
        rec = data.get("recommendation", "Read Later")
        why = data.get("recommendation_reason", "")
        pm_takeaway = data.get("pm_takeaway", "")
        evidence = data.get("supporting_evidence", [])

        _panel(draw, (80, 150, 1000, 260), fill="#101724")
        draw.text((110, 170), rec, font=font_xl, fill=accent)
        _draw_lines(draw, 110, 230, _wrap(draw, why, font_sm, 830)[:2], font_sm, TEXT, 24)

        y = 280
        if pm_takeaway:
            _panel(draw, (80, y, 1000, y + 280), fill="#152033")
            draw.text((110, y + 16), "PM takeaway", font=font_tag, fill=accent)
            _draw_lines(draw, 110, y + 48, _wrap(draw, pm_takeaway, font_sm, 820)[:10], font_sm, TEXT, 24)
            y += 300

        if evidence:
            _panel(draw, (80, y, 1000, min(y + 420, 1220)))
            draw.text((110, y + 16), "Evidence", font=font_tag, fill=accent)
            ey = y + 48
            for ev in evidence[:3]:
                claim = ev.get("claim", "")
                snippet = ev.get("evidence", "")
                source_url = ev.get("source_url") or ev.get("source", "")
                if claim:
                    ey = _draw_lines(draw, 110, ey, _wrap(draw, f"• {claim}", font_sm, 820)[:2], font_sm, TEXT, 22) + 2
                if snippet:
                    ey = _draw_lines(draw, 130, ey, _wrap(draw, snippet, font_sm, 800)[:2], font_sm, MUTED, 20) + 2
                if source_url and str(source_url).startswith("http"):
                    ey = _draw_lines(draw, 130, ey, _wrap(draw, str(source_url), font_sm, 800)[:1], font_sm, accent, 20) + 8

        score = data.get("signal_score", 0)
        draw.rounded_rectangle([80, 1260, 280, 1305], radius=20, fill=PANEL)
        draw.text((106, 1272), f"Signal {score}/100", font=font_s, fill=TEXT)

    else:
        raise ValueError(f"Unsupported slide type: {slide_type}")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    return out_path
