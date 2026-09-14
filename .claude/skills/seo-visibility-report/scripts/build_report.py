"""
SEO Visibility & Opportunity Report -- PDF Generator
Usage: python build_report.py <path_to_data.json>
"""

import sys, json, os, math

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Unicode font registration ─────────────────────────────────────────────────
_FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
pdfmetrics.registerFont(TTFont("DejaVu",       os.path.join(_FONTS_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold",  os.path.join(_FONTS_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Oblique", os.path.join(_FONTS_DIR, "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Oblique")

PW, PH = A4
MARGIN = 18 * mm

# ── Neutral theme (no agency branding) ───────────────────────────────────────

T = {
    "primary": HexColor("#1F2937"),
    "accent":  HexColor("#2563EB"),
    "success": HexColor("#16A34A"),
    "danger":  HexColor("#DC2626"),
    "warn":    HexColor("#D97706"),
    "bg":      HexColor("#F3F4F6"),
    "muted":   HexColor("#6B7280"),
    "grid":    HexColor("#E5E7EB"),
    "white":   colors.white,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_int(v, d=0):
    try: return int(v) if v is not None else d
    except: return d

def safe_float(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def fmt_num(n):
    try: return f"{int(n):,}"
    except: return str(n) if n is not None else "n/a"

def delta_color(d):
    return T["success"] if d >= 0 else T["danger"]

def cell(val, bold=False, color=None, size=7.5, align="LEFT", italic=False):
    if isinstance(val, Paragraph):
        return val
    txt  = str(val) if val is not None else "n/a"
    font = "DejaVu-Bold" if bold else ("DejaVu-Oblique" if italic else "DejaVu")
    col  = color or T["primary"]
    amap = {"LEFT": 0, "CENTER": 1, "RIGHT": 2}
    return Paragraph(txt, ParagraphStyle(
        "tc", fontName=font, fontSize=size, textColor=col,
        leading=size * 1.35, alignment=amap.get(align, 0), wordWrap="LTR",
    ))

def hcell(val, size=7.5):
    return cell(val, bold=True, color=colors.white, size=size, align="CENTER")

def make_styles():
    s = {}
    s["h3"]    = ParagraphStyle("h3",   fontName="DejaVu-Bold",    fontSize=10,
                                 textColor=T["accent"], spaceAfter=2*mm, leading=13)
    s["h4"]    = ParagraphStyle("h4",   fontName="DejaVu-Bold",    fontSize=8.5,
                                 textColor=T["primary"], spaceAfter=1.5*mm, leading=12)
    s["body"]  = ParagraphStyle("body", fontName="DejaVu",         fontSize=9,
                                 textColor=T["primary"], leading=13, spaceAfter=2*mm)
    s["muted"] = ParagraphStyle("muted",fontName="DejaVu",         fontSize=8,
                                 textColor=T["muted"], leading=11)
    s["small"] = ParagraphStyle("small",fontName="DejaVu",         fontSize=7,
                                 textColor=T["muted"], leading=10)
    return s

def std_table(headers, rows, ratios, accent=False):
    hdr_bg = T["accent"] if accent else T["primary"]
    cw = [(PW - 2*MARGIN) * r for r in ratios]
    data = [[hcell(h) for h in headers]] + rows
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  hdr_bg),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, T["bg"]]),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("GRID",          (0,0),(-1,-1), 0.3, T["grid"]),
        ("TOPPADDING",    (0,0),(-1,-1), 2*mm),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2*mm),
        ("LEFTPADDING",   (0,0),(-1,-1), 2*mm),
        ("RIGHTPADDING",  (0,0),(-1,-1), 2*mm),
    ]))
    return t

def insight_box(text, styles):
    t = Table([[Paragraph(f"Takeaway: {text}",
                ParagraphStyle("ins", fontName="DejaVu-Oblique", fontSize=9,
                               textColor=T["primary"], leading=13, wordWrap="LTR"))]],
              colWidths=[PW - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), HexColor("#EFF6FF")),
        ("LEFTPADDING", (0,0),(-1,-1), 4*mm),
        ("TOPPADDING",  (0,0),(-1,-1), 2.5*mm),
        ("BOTTOMPADDING",(0,0),(-1,-1),2.5*mm),
        ("LINEAFTER",   (0,0),(0,-1),  2.5, T["accent"]),
    ]))
    return [t, Spacer(1, 3*mm)]

def no_data_box(section):
    t = Table([[Paragraph(
        f"No data available for {section}. Check DataForSEO MCP and retry.",
        ParagraphStyle("nd", fontName="DejaVu-Oblique", fontSize=9,
                       textColor=T["muted"]))]],
        colWidths=[PW - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), HexColor("#FEF9EC")),
        ("LEFTPADDING", (0,0),(-1,-1), 4*mm),
        ("TOPPADDING",  (0,0),(-1,-1), 3*mm),
        ("BOTTOMPADDING",(0,0),(-1,-1),3*mm),
        ("BOX",         (0,0),(-1,-1), 0.5, T["warn"]),
    ]))
    return [t, Spacer(1, 3*mm)]

def section_header(title, number, styles):
    t = Table([[
        cell(str(number),
             bold=True, color=colors.white, size=11, align="CENTER"),
        cell(title, bold=True, color=colors.white, size=13),
    ]], colWidths=[12*mm, PW - 2*MARGIN - 12*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), T["primary"]),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (1,0),(1,-1),  3*mm),
        ("TOPPADDING",    (0,0),(-1,-1), 2.5*mm),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2.5*mm),
    ]))
    return [Spacer(1, 4*mm), t, Spacer(1, 4*mm)]


# ── KPI Card ──────────────────────────────────────────────────────────────────

class KPICard(Flowable):
    def __init__(self, label, value, delta=None, positive=True,
                 width=38*mm, height=26*mm, sub=None, small_value=False):
        super().__init__()
        self.label       = label
        self.value       = str(value) if value is not None else "n/a"
        self.delta       = delta
        self.positive    = positive
        self.width       = width
        self.height      = height
        self.sub         = sub
        self.small_value = small_value  # wrap long text at smaller font size

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.setFillColor(T["bg"])
        c.roundRect(0, 0, w, h, 3*mm, fill=1, stroke=0)
        c.setFillColor(T["accent"])
        c.roundRect(0, h - 2*mm, w, 2*mm, 1, fill=1, stroke=0)
        c.setFillColor(T["muted"])
        c.setFont("DejaVu", 6.5)
        c.drawString(3*mm, h - 9*mm, self.label.upper())
        c.setFillColor(T["primary"])
        if self.small_value:
            # wrap long text (e.g. address) across multiple lines
            c.setFont("DejaVu", 7.5)
            max_w = w - 6*mm
            words = self.value.split()
            lines, cur = [], ""
            for word in words:
                test = (cur + " " + word).strip()
                if c.stringWidth(test, "DejaVu", 7.5) <= max_w:
                    cur = test
                else:
                    if cur: lines.append(cur)
                    cur = word
            if cur: lines.append(cur)
            y = h - 16*mm
            for line in lines[:3]:
                c.drawString(3*mm, y, line)
                y -= 9
        else:
            c.setFont("DejaVu-Bold", 14)
            c.drawString(3*mm, h - 17*mm, self.value)
        if self.sub:
            c.setFillColor(T["muted"])
            c.setFont("DejaVu", 5.5)
            c.drawString(3*mm, h - 20.5*mm, self.sub)
        if self.delta:
            col = T["success"] if self.positive else T["danger"]
            c.setFillColor(col)
            c.setFont("DejaVu", 7.5)
            c.drawString(3*mm, 3*mm, str(self.delta))


# ── Simple Bar Chart Flowable ─────────────────────────────────────────────────

class BarChart(Flowable):
    """Draws a vertical grouped bar chart (up to 2 series) using raw canvas calls."""
    def __init__(self, labels, series, series_labels, series_colors,
                 width, height, title=None):
        super().__init__()
        self.labels        = labels
        self.series        = series
        self.series_labels = series_labels
        self.series_colors = series_colors
        self.width         = width
        self.height        = height
        self.title         = title

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        pad_left  = 14*mm
        pad_bot   = 8*mm
        pad_top   = 8*mm if not self.title else 12*mm
        pad_right = 4*mm

        chart_w = w - pad_left - pad_right
        chart_h = h - pad_bot - pad_top

        if self.title:
            c.setFillColor(T["primary"])
            c.setFont("DejaVu-Bold", 7.5)
            c.drawString(pad_left, h - 7*mm, self.title)

        c.setFillColor(T["bg"])
        c.rect(pad_left, pad_bot, chart_w, chart_h, fill=1, stroke=0)

        all_vals = [v for s in self.series for v in s if v is not None]
        max_val  = max(all_vals) if all_vals else 1
        if max_val == 0: max_val = 1

        n_bars   = len(self.labels)
        n_series = len(self.series)
        grp_w    = chart_w / max(n_bars, 1)
        bar_w    = (grp_w * 0.7) / max(n_series, 1)
        gap      = grp_w * 0.15

        c.setStrokeColor(T["grid"])
        c.setLineWidth(0.3)
        for i in range(1, 5):
            y = pad_bot + (chart_h * i / 4)
            c.line(pad_left, y, pad_left + chart_w, y)
            val_label = fmt_num(int(max_val * i / 4))
            c.setFillColor(T["muted"])
            c.setFont("DejaVu", 5.5)
            c.drawRightString(pad_left - 1*mm, y - 2, val_label)

        for gi, label in enumerate(self.labels):
            x_grp = pad_left + gi * grp_w + gap
            for si, (series, color) in enumerate(zip(self.series, self.series_colors)):
                val = series[gi] if gi < len(series) else 0
                if val is None: val = 0
                bar_h = (val / max_val) * chart_h
                x = x_grp + si * bar_w
                c.setFillColor(color)
                c.rect(x, pad_bot, bar_w * 0.85, bar_h, fill=1, stroke=0)

            c.setFillColor(T["muted"])
            c.setFont("DejaVu", 5.5)
            c.drawCentredString(pad_left + gi * grp_w + grp_w / 2,
                                pad_bot - 5, str(label)[-7:])

        # legend -- measure each item width then centre the whole group
        c.setFont("DejaVu", 6)
        swatch = 7   # colour square size (pt)
        gap_inner = 4   # between swatch and text
        gap_outer = 16  # between legend items
        item_widths = [swatch + gap_inner + c.stringWidth(sl, "DejaVu", 6)
                       for sl in self.series_labels]
        total_w = sum(item_widths) + gap_outer * (len(item_widths) - 1)
        lx = (self.width - total_w) / 2
        ly = 2.5
        for sl, color, iw in zip(self.series_labels, self.series_colors, item_widths):
            c.setFillColor(color)
            c.rect(lx, ly, swatch, swatch, fill=1, stroke=0)
            c.setFillColor(T["muted"])
            c.drawString(lx + swatch + gap_inner, ly + 1, sl)
            lx += iw + gap_outer


# ── Cover page ────────────────────────────────────────────────────────────────

def draw_cover(canvas, doc, cfg):
    canvas.saveState()
    w, h = A4
    framing     = cfg.get("framing", {})
    cover_title = framing.get("cover_title", "SEO Visibility Report")
    settings    = cfg.get("report_settings", {})
    purpose     = settings.get("purpose", "existing_client")

    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)

    canvas.setFillColor(T["primary"])
    canvas.rect(0, h - 14*mm, w, 14*mm, fill=1, stroke=0)

    canvas.setFillColor(colors.white)
    canvas.setFont("DejaVu-Bold", 9)
    canvas.drawString(MARGIN, h - 8.5*mm, cfg.get("client_domain", "").upper())
    canvas.setFont("DejaVu", 8)
    canvas.drawRightString(w - MARGIN, h - 8.5*mm, cfg.get("period_current", ""))

    canvas.setFillColor(T["accent"])
    canvas.rect(0, 0, 5*mm, h - 14*mm, fill=1, stroke=0)

    canvas.setFillColor(T["primary"])
    canvas.setFont("DejaVu-Bold", 28)
    canvas.drawString(14*mm, h * 0.62, cover_title)

    canvas.setFillColor(T["accent"])
    canvas.rect(14*mm, h * 0.62 - 3*mm, 55*mm, 1.5, fill=1, stroke=0)

    canvas.setFillColor(T["accent"])
    canvas.setFont("DejaVu-Bold", 12)
    canvas.drawString(14*mm, h * 0.62 - 10*mm, cfg.get("period_current", ""))

    canvas.setFillColor(HexColor("#E5E7EB"))
    canvas.rect(14*mm, h * 0.49, w - 14*mm - MARGIN, 0.5, fill=1, stroke=0)

    canvas.setFillColor(T["muted"])
    canvas.setFont("DejaVu", 8)
    canvas.drawString(14*mm, h * 0.465, "ANALYSED DOMAIN")
    canvas.setFillColor(T["primary"])
    canvas.setFont("DejaVu-Bold", 20)
    canvas.drawString(14*mm, h * 0.43, cfg.get("client_name", cfg.get("client_domain", "")))
    canvas.setFillColor(T["muted"])
    canvas.setFont("DejaVu", 10)
    canvas.drawString(14*mm, h * 0.405, cfg.get("client_domain", ""))


    canvas.restoreState()


# ── Inner page template ───────────────────────────────────────────────────────

def page_template(canvas, doc, cfg):
    canvas.saveState()
    domain = cfg.get("client_domain", "")
    period = cfg.get("period_current", "")

    canvas.setFillColor(T["primary"])
    canvas.rect(0, PH - 12*mm, PW, 12*mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("DejaVu", 8)
    canvas.drawString(MARGIN, PH - 7.5*mm, domain)
    canvas.drawRightString(PW - MARGIN, PH - 7.5*mm, period)

    canvas.setFillColor(T["bg"])
    canvas.rect(0, 0, PW, 11*mm, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#D1D5DB"))
    canvas.rect(0, 11*mm, PW, 0.4, fill=1, stroke=0)
    canvas.setFillColor(T["muted"])
    canvas.setFont("DejaVu", 7)
    canvas.drawRightString(PW - MARGIN, 7*mm, f"Page {doc.page}")
    canvas.restoreState()


# ── Executive TL;DR page ──────────────────────────────────────────────────────

def build_tldr(sec, cfg, styles):
    """Single-page TL;DR: key numbers + one-line story + top 3 actions."""
    els = []
    cur  = sec.get("current_period",  {}) or {}
    prev = sec.get("previous_period", {}) or {}

    banner = Table([[cell("AT A GLANCE", bold=True, color=colors.white, size=13)]],
                   colWidths=[PW - 2*MARGIN])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), T["accent"]),
        ("TOPPADDING",    (0,0),(-1,-1), 3*mm),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3*mm),
        ("LEFTPADDING",   (0,0),(-1,-1), 4*mm),
    ]))
    els += [banner, Spacer(1, 5*mm)]

    vi_c   = safe_float(cur.get("vi", 0))
    vi_p   = safe_float(prev.get("vi", 0))
    etv_c  = safe_int(cur.get("etv", 0))
    etv_p  = safe_int(prev.get("etv", 0))
    kws_c  = safe_int(cur.get("keywords_count", 0))
    kws_p  = safe_int(prev.get("keywords_count", 0))
    top3_c = safe_int(cur.get("pos_1", 0)) + safe_int(cur.get("pos_2_3", 0))
    top3_p = safe_int(prev.get("pos_1", 0)) + safe_int(prev.get("pos_2_3", 0))
    has_prev = bool(prev)

    vi_sub = "0-100 quality-weighted score"
    kpis = [
        KPICard("Visibility Index (VI)", f"{vi_c:.1f}",
                f"{vi_c - vi_p:+.1f} pts" if has_prev else None, vi_c >= vi_p,
                sub=vi_sub, width=44*mm, height=30*mm),
        KPICard("Est. Organic Traffic", fmt_num(etv_c),
                f"{etv_c - etv_p:+,}" if has_prev else None, etv_c >= etv_p,
                sub="modeled estimate", width=44*mm, height=30*mm),
        KPICard("Ranked Keywords", fmt_num(kws_c),
                f"{kws_c - kws_p:+d} MoM" if has_prev else None, kws_c >= kws_p,
                width=44*mm, height=30*mm),
        KPICard("Top-3 Rankings", str(top3_c),
                f"{top3_c - top3_p:+d}" if has_prev else None, top3_c >= top3_p,
                width=44*mm, height=30*mm),
    ]
    kpi_t = Table([[k for k in kpis]], colWidths=[44*mm]*4, rowHeights=[30*mm])
    kpi_t.setStyle(TableStyle([
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0),(-1,-1), 1*mm),
        ("RIGHTPADDING", (0,0),(-1,-1), 1*mm),
    ]))
    els += [kpi_t, Spacer(1, 5*mm)]

    insight = sec.get("insight", "")
    if insight:
        story_t = Table([[
            cell("THE STORY", bold=True, color=T["accent"], size=7),
            cell(insight, italic=True, size=10),
        ]], colWidths=[22*mm, PW - 2*MARGIN - 22*mm])
        story_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), HexColor("#EFF6FF")),
            ("TOPPADDING",    (0,0),(-1,-1), 3*mm),
            ("BOTTOMPADDING", (0,0),(-1,-1), 3*mm),
            ("LEFTPADDING",   (0,0),(-1,-1), 4*mm),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ]))
        els += [story_t, Spacer(1, 5*mm)]

    tldr_actions = sec.get("tldr", []) or []
    if tldr_actions:
        els.append(Paragraph("TOP 3 ACTIONS", ParagraphStyle(
            "ta", fontName="DejaVu-Bold", fontSize=8, textColor=T["accent"],
            spaceAfter=2*mm)))
        for i, action in enumerate(tldr_actions[:3], 1):
            row = Table([[
                cell(str(i), bold=True, color=colors.white, size=10, align="CENTER"),
                cell(str(action), size=9),
            ]], colWidths=[10*mm, PW - 2*MARGIN - 10*mm])
            row.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(0,-1),  T["accent"]),
                ("BACKGROUND",    (1,0),(1,-1),  colors.white if i%2==0 else T["bg"]),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                ("TOPPADDING",    (0,0),(-1,-1), 2.5*mm),
                ("BOTTOMPADDING", (0,0),(-1,-1), 2.5*mm),
                ("LEFTPADDING",   (1,0),(1,-1),  3*mm),
                ("LINEBELOW",     (0,0),(-1,-1), 0.3, T["grid"]),
            ]))
            els.append(row)

    els.append(PageBreak())
    return els


# ── Section 01 -- Executive Summary ──────────────────────────────────────────

def build_s1(sec, cfg, styles):
    framing = cfg.get("framing", {})
    header  = framing.get("s1_header", "Executive Summary")
    els = section_header(header, 1, styles)
    cur  = sec.get("current_period",  {}) or {}
    prev = sec.get("previous_period", {}) or {}
    if not cur:
        return els + no_data_box("Executive Summary")

    vi_c  = safe_float(cur.get("vi",  0))
    vi_p  = safe_float(prev.get("vi", 0)) if prev else None
    etv_c = safe_int(cur.get("etv",   0))
    etv_p = safe_int(prev.get("etv",  0)) if prev else None
    kws_c = safe_int(cur.get("keywords_count", cur.get("keywords", 0)))
    kws_p = safe_int(prev.get("keywords_count", prev.get("keywords", 0))) if prev else None
    top3_c = safe_int(cur.get("pos_1",0)) + safe_int(cur.get("pos_2_3",0))
    top3_p = (safe_int(prev.get("pos_1",0)) + safe_int(prev.get("pos_2_3",0))) if prev else None
    has_prev = bool(prev)

    kpis = [
        KPICard("Visibility Index (VI)", f"{vi_c:.1f}",
                f"{vi_c - vi_p:+.1f} pts" if has_prev and vi_p is not None else None,
                vi_c >= (vi_p or 0), sub="0-100 quality-weighted score"),
        KPICard("Est. Organic Traffic (modeled)", fmt_num(etv_c),
                f"{etv_c - etv_p:+,}" if has_prev and etv_p is not None else None,
                etv_c >= (etv_p or 0), sub="not analytics data"),
        KPICard("Ranked Keywords", fmt_num(kws_c),
                f"{kws_c - (kws_p or 0):+d} MoM" if has_prev else None,
                kws_c >= (kws_p or 0)),
        KPICard("Top-3 Rankings", str(top3_c),
                f"{top3_c - (top3_p or 0):+d}" if has_prev else None,
                top3_c >= (top3_p or 0)),
        KPICard("4-10 Rankings", str(safe_int(cur.get("pos_4_10", 0))), None, True),
    ]
    kpi_t = Table([[k for k in kpis]], colWidths=[37*mm]*5, rowHeights=[28*mm])
    kpi_t.setStyle(TableStyle([
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0),(-1,-1), 1*mm),
        ("RIGHTPADDING", (0,0),(-1,-1), 1*mm),
    ]))
    els += [kpi_t, Spacer(1, 4*mm)]

    els.append(Paragraph(
        "Visibility Index (VI): 0-100 quality-weighted score. "
        "Formula: (pos1 x1.0 + pos2-3 x0.85 + pos4-10 x0.5 + pos11-20 x0.2 + pos21-30 x0.05) "
        "/ total ranked keywords x 100. A rising VI with flat traffic indicates quality improving "
        "before clicks follow -- this is normal and expected.",
        styles["small"]))
    els.append(Spacer(1, 3*mm))

    narrative = sec.get("narrative", "")
    if narrative:
        els += [Paragraph("Performance Narrative", styles["h3"]),
                Paragraph(narrative, styles["body"])]

    if has_prev:
        els.append(Paragraph("Month-on-Month Summary", styles["h3"]))
        pc = cfg.get("period_current", "Current")
        pp = cfg.get("period_prev",    "Previous")

        def ch(vc, vp):
            if vc is None or vp is None: return cell("n/a", align="CENTER")
            d = vc - vp
            s = f"{d:+.1f}" if isinstance(d, float) else f"{int(d):+d}"
            return cell(s, bold=True, color=delta_color(d), align="CENTER")

        p4c  = safe_int(cur.get("pos_4_10",  0)); p4p  = safe_int(prev.get("pos_4_10",  0))
        p11c = safe_int(cur.get("pos_11_20", 0)); p11p = safe_int(prev.get("pos_11_20", 0))
        p21c = safe_int(cur.get("pos_21_30", 0)); p21p = safe_int(prev.get("pos_21_30", 0))
        p31c = safe_int(cur.get("pos_31_100",0)); p31p = safe_int(prev.get("pos_31_100",0))

        rows = [
            [cell("Visibility Index"),              cell(f"{vi_c:.1f}",    align="CENTER"), cell(f"{vi_p:.1f}",    align="CENTER"), ch(vi_c, vi_p)],
            [cell("Est. Organic Traffic (modeled)"),cell(fmt_num(etv_c),   align="CENTER"), cell(fmt_num(etv_p),   align="CENTER"), ch(etv_c, etv_p)],
            [cell("Keywords Top 3"),                cell(str(top3_c),      align="CENTER"), cell(str(top3_p),      align="CENTER"), ch(top3_c, top3_p)],
            [cell("Keywords 4-10"),                 cell(str(p4c),         align="CENTER"), cell(str(p4p),         align="CENTER"), ch(p4c,   p4p)],
            [cell("Keywords 11-20"),                cell(str(p11c),        align="CENTER"), cell(str(p11p),        align="CENTER"), ch(p11c,  p11p)],
            [cell("Keywords 21-30"),                cell(str(p21c),        align="CENTER"), cell(str(p21p),        align="CENTER"), ch(p21c,  p21p)],
            [cell("Keywords 31-100"),               cell(str(p31c),        align="CENTER"), cell(str(p31p),        align="CENTER"), ch(p31c,  p31p)],
            [cell("Total Ranked Keywords"),         cell(fmt_num(kws_c),   align="CENTER"), cell(fmt_num(kws_p),   align="CENTER"), ch(kws_c, kws_p)],
        ]
        t = std_table([" Metric", pc, pp, "Change"], rows, [0.45, 0.18, 0.18, 0.19])
        els += [t, Spacer(1, 3*mm)]

    ins = sec.get("insight", "")
    if ins: els += insight_box(ins, styles)
    return els


# ── Section 02 -- Keyword Rankings ───────────────────────────────────────────

def build_s2(sec, cfg, styles):
    framing = cfg.get("framing", {})
    header  = framing.get("s2_header", "Keyword Rankings")
    reader  = cfg.get("report_settings", {}).get("reader", "manager")
    els = [PageBreak()]
    els += section_header(header, 2, styles)

    keywords = sec.get("keywords",       []) or []
    groups   = sec.get("keyword_groups", {}) or {}
    opps     = sec.get("opportunities",  []) or []

    if not keywords:
        return els + no_data_box("Keyword Rankings")

    STATUS_CLR = {
        "WIN":    T["success"], "RISK":   T["danger"],
        "WATCH":  T["warn"],    "STABLE": T["muted"],
        "NEW":    T["accent"],  "LOST":   T["danger"],
    }
    INTENT_LABELS = {
        "commercial":    "Commercial",
        "informational": "Informational",
        "local":         "Local",
        "branded":       "Branded",
        "navigational":  "Navigational",
    }

    # 2A -- Distribution summary
    els.append(Paragraph("2A - Position Distribution", styles["h3"]))
    buckets = {"Top 3": [0,0], "4-10": [0,0], "11-20": [0,0],
               "21-30": [0,0], "31-100": [0,0]}
    def bl(pos):
        if pos is None: return None
        p = safe_int(pos)
        if p <= 3:  return "Top 3"
        if p <= 10: return "4-10"
        if p <= 20: return "11-20"
        if p <= 30: return "21-30"
        return "31-100"
    for kw in keywords:
        bc = bl(kw.get("pos_current")); bp = bl(kw.get("pos_previous"))
        if bc: buckets[bc][0] += 1
        if bp: buckets[bp][1] += 1

    has_prev = any(v[1] > 0 for v in buckets.values())
    dist_rows = []
    for label, (c, p) in buckets.items():
        d = c - p
        row = [cell(label), cell(str(c), align="CENTER")]
        if has_prev:
            row += [cell(str(p), align="CENTER"),
                    cell(f"{d:+d}", bold=True, color=delta_color(d), align="CENTER")]
        dist_rows.append(row)

    if has_prev:
        pc = cfg.get("period_current", "Now"); pp2 = cfg.get("period_prev", "Prev")
        dist_t = std_table(["Bucket", pc, pp2, "Delta"], dist_rows, [0.40, 0.20, 0.20, 0.20])
    else:
        dist_t = std_table(["Bucket", "Keywords"], dist_rows, [0.60, 0.40])
    els += [dist_t, Spacer(1, 4*mm)]

    # 2B -- Opportunity block
    if opps:
        els.append(Paragraph(
            f"2B - Opportunities ({len(opps)} target keywords not ranking or stuck on page 2+)",
            styles["h3"]))
        opp_rows = []
        for o in sorted(opps, key=lambda x: -safe_int(x.get("volume", 0)))[:10]:
            pos = o.get("pos_current")
            pos_str = str(pos) if pos else "Not ranking"
            pt = safe_int(o.get("potential_traffic", 0))
            opp_rows.append([
                cell(o.get("keyword", "")),
                cell(fmt_num(o.get("volume")), align="CENTER"),
                cell(pos_str, align="CENTER"),
                cell(f"~{fmt_num(pt)}/mo" if pt else "n/a", align="CENTER"),
            ])
        opp_t = std_table(
            ["Opportunity Keyword", "Vol/mo", "Current Position", "Est. Traffic if Ranked #5"],
            opp_rows, [0.38, 0.16, 0.22, 0.24], accent=True)
        els += [opp_t, Spacer(1, 4*mm)]

    # 2C -- Keyword groups (by intent)
    els.append(Paragraph("2C - Rankings by Intent Group", styles["h3"]))
    if groups:
        for intent_key, intent_label in INTENT_LABELS.items():
            group_kws = groups.get(intent_key, []) or []
            if not group_kws: continue
            els.append(Paragraph(f"{intent_label} ({len(group_kws)} keywords)",
                                 styles["h4"]))
            kw_rows = _keyword_rows(group_kws, reader, STATUS_CLR, has_prev)
            kw_t    = _keyword_table(kw_rows, has_prev)
            els += [kw_t, Spacer(1, 2*mm)]
    else:
        movers = [kw for kw in keywords if kw.get("status") in ("WIN","RISK","LOST")]
        if reader == "exec":
            els.append(Paragraph("Top Movers This Period", styles["h4"]))
            kw_rows = _keyword_rows(movers[:15], reader, STATUS_CLR, has_prev)
            kw_t    = _keyword_table(kw_rows, has_prev)
            els += [kw_t, Spacer(1, 3*mm)]
            els.append(Paragraph("Full keyword table in Appendix.", styles["muted"]))
        else:
            kw_rows = _keyword_rows(keywords, reader, STATUS_CLR, has_prev)
            kw_t    = _keyword_table(kw_rows, has_prev)
            els += [kw_t, Spacer(1, 3*mm)]

    ins = sec.get("insight", "")
    if ins: els += insight_box(ins, styles)
    return els

def _keyword_rows(keywords, reader, STATUS_CLR, has_prev):
    rows = []
    for kw in keywords:
        pc_ = kw.get("pos_current"); pp_ = kw.get("pos_previous")
        delta = "n/a"; dcol = T["muted"]
        if pc_ is not None and pp_ is not None:
            d = safe_int(pp_) - safe_int(pc_); delta = f"{d:+d}"; dcol = delta_color(d)
        elif pc_ is not None and pp_ is None:
            delta = "NEW"; dcol = T["accent"]
        status = kw.get("status", "")
        feats  = ", ".join(kw.get("serp_features") or []) or "n/a"
        vol    = fmt_num(kw.get("volume")) if kw.get("volume") else "n/a"
        row = [
            cell(kw.get("keyword", "")),
            cell(vol, align="CENTER"),
            cell(str(pc_) if pc_ is not None else "n/a", align="CENTER"),
        ]
        if has_prev:
            row.append(cell(str(pp_) if pp_ is not None else "n/a", align="CENTER"))
            row.append(cell(delta, bold=True, color=dcol, align="CENTER"))
        if reader == "manager":
            row.append(cell(feats))
        row.append(cell(status, bold=True, color=STATUS_CLR.get(status, T["muted"]), align="CENTER"))
        rows.append(row)
    return rows

def _keyword_table(rows, has_prev):
    if not rows: return Spacer(1, 1*mm)
    n = len(rows[0])
    if n == 4:
        return std_table(["Keyword","Vol","Now","Status"], rows, [0.40,0.14,0.14,0.18])
    elif n == 5 and not has_prev:
        return std_table(["Keyword","Vol","Now","SERP Features","Status"],
                         rows, [0.28,0.10,0.10,0.32,0.10])
    elif n == 5 and has_prev:
        return std_table(["Keyword","Vol","Now","Prev","Delta"],
                         rows, [0.36,0.12,0.12,0.12,0.12])
    elif n == 6:
        return std_table(["Keyword","Vol","Now","Prev","Delta","Status"],
                         rows, [0.32,0.10,0.10,0.10,0.10,0.13])
    elif n == 7:
        return std_table(["Keyword","Vol","Now","Prev","Delta","SERP Features","Status"],
                         rows, [0.24,0.09,0.08,0.08,0.08,0.27,0.11])
    else:
        return std_table(["Keyword","Vol","Now","Status"], rows, [0.40,0.14,0.14,0.18])


# ── Local SEO Section ─────────────────────────────────────────────────────────

def _render_location_block(loc, styles):
    """Renders GBP + pack rankings + pack competitors for one location."""
    els = []
    gbp        = loc.get("gbp",  {}) or {}
    packs      = loc.get("local_pack_rankings",   []) or []
    pack_comps = loc.get("local_pack_competitors", []) or []

    # GBP
    els.append(Paragraph("Google Business Profile", styles["h3"]))
    if gbp:
        rating  = safe_float(gbp.get("rating"))
        reviews = safe_int(gbp.get("review_count"))
        claimed = gbp.get("is_claimed", False)
        address = gbp.get("address", "n/a")
        kpis = [
            KPICard("Google Rating", f"{rating:.1f} / 5.0" if rating else "n/a",
                    None, True, width=56*mm, height=24*mm),
            KPICard("Total Reviews", fmt_num(reviews), None, True,
                    width=56*mm, height=24*mm),
            KPICard("GBP Status",    "Claimed" if claimed else "UNCLAIMED",
                    None, claimed, width=56*mm, height=24*mm),
        ]
        kpi_t = Table([[k for k in kpis]], colWidths=[56*mm]*3, rowHeights=[24*mm])
        kpi_t.setStyle(TableStyle([
            ("ALIGN",        (0,0),(-1,-1), "CENTER"),
            ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
            ("LEFTPADDING",  (0,0),(-1,-1), 1*mm),
            ("RIGHTPADDING", (0,0),(-1,-1), 1*mm),
        ]))
        els += [kpi_t, Spacer(1, 4*mm)]
    else:
        els.append(Paragraph("No Google Business Profile listing found for this location.",
                             styles["muted"]))
        els.append(Spacer(1, 3*mm))

    # Pack rankings
    if packs:
        els.append(Paragraph("Local Pack Rankings", styles["h3"]))
        pack_rows = []
        for p in packs:
            pack_pos = p.get("pack_position")
            org_pos  = p.get("organic_position")
            pack_rows.append([
                cell(p.get("keyword", "")),
                cell(str(pack_pos) if pack_pos else "Not in pack", align="CENTER",
                     bold=pack_pos is not None and pack_pos <= 3,
                     color=T["success"] if pack_pos and pack_pos <= 3 else T["primary"]),
                cell(str(org_pos) if org_pos else "n/a", align="CENTER"),
            ])
        pack_t = std_table(["Keyword", "Local Pack Position", "Organic Position"],
                           pack_rows, [0.52, 0.24, 0.24])
        els += [pack_t, Spacer(1, 3*mm)]

    # Pack competitors
    if pack_comps:
        els.append(Paragraph("Local Pack Competitors", styles["h3"]))
        comp_rows = []
        for c in pack_comps:
            avg_pos = safe_float(c.get("avg_pack_position"))
            avg_rat = safe_float(c.get("avg_rating"))
            kw_cnt  = safe_int(c.get("keywords_in_pack"))
            comp_rows.append([
                cell(c.get("name", c.get("domain", ""))),
                cell(c.get("domain", "n/a"), italic=True, color=T["muted"]),
                cell(f"{avg_pos:.1f}" if avg_pos else "n/a", align="CENTER"),
                cell(f"{avg_rat:.1f}" if avg_rat else "n/a", align="CENTER",
                     bold=avg_rat >= 4.5 if avg_rat else False,
                     color=T["success"] if avg_rat and avg_rat >= 4.5 else T["primary"]),
                cell(fmt_num(c.get("total_reviews")), align="CENTER"),
                cell(str(kw_cnt), align="CENTER"),
            ])
        comp_t = std_table(
            ["Business", "Domain", "Avg Pack Pos.", "Rating", "Reviews", "Keywords in Pack"],
            comp_rows, [0.22, 0.22, 0.13, 0.10, 0.13, 0.20])
        els += [comp_t, Spacer(1, 3*mm)]

    return els


def build_local(sec, cfg, styles):
    els = [PageBreak()]
    els += section_header("Local SEO Overview", "L", styles)
    if not sec:
        return els + no_data_box("Local SEO")

    locations = sec.get("locations", []) or []

    # Backwards compat: old single-location format
    if not locations and sec.get("gbp"):
        locations = [sec]

    if not locations:
        return els + no_data_box("Local SEO")

    if len(locations) == 1:
        els += _render_location_block(locations[0], styles)
    else:
        # Per-location detail blocks
        for loc in locations:
            loc_name = loc.get("location_name", "")
            loc_hdr = Table([[cell(loc_name, bold=True, color=colors.white, size=10)]],
                            colWidths=[PW - 2*MARGIN])
            loc_hdr.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), T["accent"]),
                ("TOPPADDING",    (0,0),(-1,-1), 2.5*mm),
                ("BOTTOMPADDING", (0,0),(-1,-1), 2.5*mm),
                ("LEFTPADDING",   (0,0),(-1,-1), 4*mm),
            ]))
            els += [loc_hdr, Spacer(1, 3*mm)]
            els += _render_location_block(loc, styles)

    ins = sec.get("insight", "")
    if ins: els += insight_box(ins, styles)
    return els


# ── Section 03 -- Competitor Snapshot ────────────────────────────────────────

def build_s3(sec, cfg, styles):
    els = [PageBreak()]
    els += section_header("Competitor Snapshot", 3, styles)
    competitors = sec.get("competitors", []) or []
    if not competitors:
        return els + no_data_box("Competitor Snapshot")

    els.append(Paragraph(
        "Light overview of key competitors' estimated visibility. "
        "For a full competitive breakdown, commission a dedicated Competitor Analysis report.",
        styles["muted"]))
    els.append(Spacer(1, 3*mm))

    client_domain = cfg.get("client_domain", "")
    client_data   = sec.get("client", {}) or {}
    CLIENT_BG     = HexColor("#EFF6FF")
    cw            = [(PW - 2*MARGIN) * r for r in [0.38, 0.22, 0.22, 0.18]]

    client_etv = fmt_num(client_data.get("etv")) if client_data.get("etv") else "n/a"
    client_pos = str(round(safe_float(client_data.get("avg_position")), 1)) \
                 if client_data.get("avg_position") else "n/a"

    header_row = [hcell(h) for h in
                  ["Domain", "Est. Organic Traffic (modeled)", "Shared Keywords", "Avg. Position"]]
    client_row = [
        cell(f"{client_domain}  (you)", bold=True, color=T["accent"]),
        cell(client_etv, bold=True, color=T["accent"], align="CENTER"),
        cell("—",        bold=True, color=T["muted"],  align="CENTER"),
        cell(client_pos, bold=True, color=T["accent"], align="CENTER"),
    ]

    comp_rows = []
    for comp in sorted(competitors, key=lambda x: -safe_int(x.get("etv", 0))):
        comp_rows.append([
            cell(comp.get("domain", "")),
            cell(fmt_num(comp.get("etv")),           align="CENTER"),
            cell(fmt_num(comp.get("intersections")), align="CENTER"),
            cell(str(round(safe_float(comp.get("avg_position")), 1))
                 if comp.get("avg_position") else "n/a", align="CENTER"),
        ])

    t = Table([header_row, client_row] + comp_rows, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  T["primary"]),
        ("BACKGROUND",    (0,1),(-1,1),  CLIENT_BG),
        ("LINEBELOW",     (0,1),(-1,1),  1.5, T["accent"]),
        ("ROWBACKGROUNDS",(0,2),(-1,-1), [colors.white, T["bg"]]),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("GRID",          (0,0),(-1,-1), 0.3, T["grid"]),
        ("TOPPADDING",    (0,0),(-1,-1), 2*mm),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2*mm),
        ("LEFTPADDING",   (0,0),(-1,-1), 2*mm),
        ("RIGHTPADDING",  (0,0),(-1,-1), 2*mm),
    ]))
    els += [t, Spacer(1, 3*mm)]

    ins = sec.get("insight", "")
    if ins: els += insight_box(ins, styles)
    return els


# ── Section 04 -- Backlink Profile ────────────────────────────────────────────

def build_s4(sec, cfg, styles):
    els = [PageBreak()]
    els += section_header("Backlink Profile", 4, styles)
    cur  = sec.get("current",  {}) or {}
    prev = sec.get("previous", {}) or {}
    if not cur:
        return els + no_data_box("Backlink Profile")

    has_prev = bool(prev)
    dr_c  = safe_float(cur.get("dr", 0))
    dr_p  = safe_float(prev.get("dr")) if has_prev else None
    bl_c  = safe_int(cur.get("total_backlinks",  cur.get("backlinks",  0)))
    bl_p  = safe_int(prev.get("total_backlinks", prev.get("backlinks", 0))) if has_prev else None
    rd_c  = safe_int(cur.get("referring_domains", 0))
    rd_p  = safe_int(prev.get("referring_domains", 0)) if has_prev else None
    new_n = safe_int(sec.get("new_domains_count", len(sec.get("new_domains",  []) or [])))
    lost_n= safe_int(sec.get("lost_domains_count",len(sec.get("lost_domains", []) or [])))

    kpis = [
        KPICard("Domain Rating (0-100)", str(dr_c),
                f"{dr_c - dr_p:+.1f}" if dr_p is not None else None,
                dr_c >= (dr_p or 0)),
        KPICard("Referring Domains", fmt_num(rd_c),
                f"{rd_c - rd_p:+,}" if rd_p is not None else None, rd_c >= (rd_p or 0)),
        KPICard("Total Backlinks",   fmt_num(bl_c),
                f"{bl_c - bl_p:+,}" if bl_p is not None else None, bl_c >= (bl_p or 0)),
        KPICard("New Ref. Domains",  str(new_n), cfg.get("period_current",""), True),
        KPICard("Lost Ref. Domains", str(lost_n), cfg.get("period_current",""), lost_n == 0),
    ]
    kpi_t = Table([[k for k in kpis]], colWidths=[37*mm]*5, rowHeights=[28*mm])
    kpi_t.setStyle(TableStyle([
        ("ALIGN",        (0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",  (0,0),(-1,-1),1*mm),("RIGHTPADDING",(0,0),(-1,-1),1*mm),
    ]))
    els += [Paragraph("4A - Link Profile Overview", styles["h3"]), kpi_t, Spacer(1, 5*mm)]

    timeline = sec.get("timeline", []) or []
    if timeline:
        els.append(Paragraph("Referring Domains -- 6-Month Trend", styles["h3"]))
        tl_labels = [str(entry.get("date", ""))[-7:] for entry in timeline]
        tl_new    = [safe_int(entry.get("new",  entry.get("new_referring_domains",  0))) for entry in timeline]
        tl_lost   = [safe_int(entry.get("lost", entry.get("lost_referring_domains", 0))) for entry in timeline]
        chart = BarChart(
            labels        = tl_labels,
            series        = [tl_new, tl_lost],
            series_labels = ["New domains", "Lost domains"],
            series_colors = [T["success"], T["danger"]],
            width         = PW - 2*MARGIN,
            height        = 40*mm,
        )
        els += [chart, Spacer(1, 4*mm)]

    new_domains = sec.get("new_domains", []) or []
    if new_domains:
        els.append(Paragraph(
            f"4B - New Referring Domains: {cfg.get('period_current','')}", styles["h3"]))
        nd_rows = []
        for d in new_domains:
            anchor = d.get("anchor", "n/a"); src = d.get("source_url", "")
            label  = f"{anchor}  ({src})" if src else anchor
            nd_rows.append([
                cell(d.get("domain", "")),
                cell(str(safe_int(d.get("dr", 0))), align="CENTER"),
                cell(fmt_num(d.get("ref_domains", d.get("referring_domains", 0))), align="CENTER"),
                cell("Dofollow" if d.get("dofollow", True) else "Nofollow", align="CENTER"),
                cell(label),
            ])
        nd_t = std_table(
            ["Domain","DR (0-100)","Ref. Domains","Type","Anchor / Source"],
            nd_rows, [0.22, 0.12, 0.15, 0.13, 0.38], accent=True)
        els += [nd_t, Spacer(1, 3*mm)]

    lost_domains = sec.get("lost_domains", []) or []
    if lost_domains:
        els.append(Paragraph(f"Lost Referring Domains: {cfg.get('period_current','')}", styles["h3"]))
        ld_rows = []
        for d in lost_domains:
            ld_rows.append([
                cell(d.get("domain", "")),
                cell(str(safe_int(d.get("dr", 0))), align="CENTER"),
                cell(d.get("lost_date", d.get("last_seen", "n/a")), align="CENTER"),
                cell(d.get("reason", "n/a")),
            ])
        ld_t = Table(
            [[hcell("Domain"), hcell("DR"), hcell("Last Seen"), hcell("Likely Reason")]] + ld_rows,
            colWidths=[(PW - 2*MARGIN) * r for r in [0.28, 0.12, 0.18, 0.42]])
        ld_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0),  HexColor("#991B1B")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, HexColor("#FEF2F2")]),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("GRID",          (0,0),(-1,-1), 0.3, T["grid"]),
            ("TOPPADDING",    (0,0),(-1,-1), 2*mm),("BOTTOMPADDING",(0,0),(-1,-1),2*mm),
            ("LEFTPADDING",   (0,0),(-1,-1), 2*mm),("RIGHTPADDING", (0,0),(-1,-1),2*mm),
        ]))
        els += [ld_t, Spacer(1, 3*mm)]

    ins = sec.get("insight", "")
    if ins: els += insight_box(ins, styles)
    return els


# ── Section 05 -- Technical Health ───────────────────────────────────────────

def build_s5(sec, cfg, styles):
    els = [PageBreak()]
    els += section_header("Technical Health", 5, styles)
    pages  = sec.get("pages",  []) or []
    issues = sec.get("issues", []) or []
    reader = cfg.get("report_settings", {}).get("reader", "manager")

    if not pages and not issues:
        return els + no_data_box("Technical Health")

    if pages:
        els.append(Paragraph("5A - Lighthouse Scores (Mobile, Lab Diagnostic)", styles["h3"]))
        STATUS_CLR = {"GOOD": T["success"], "NEEDS WORK": T["warn"], "POOR": T["danger"]}
        cwv_rows = []
        for p in pages:
            perf = safe_int(p.get("performance"))
            if perf >= 90:   label = "GOOD"
            elif perf >= 50: label = "NEEDS WORK"
            else:            label = "POOR"
            cwv_rows.append([
                cell(p.get("label", p.get("url", "n/a"))),
                cell(p.get("lcp", "n/a"), align="CENTER"),
                cell(p.get("cls", "n/a"), align="CENTER"),
                cell(str(perf) if perf else "n/a", align="CENTER"),
                cell(str(safe_int(p.get("seo_score"))) if p.get("seo_score") else "n/a", align="CENTER"),
                cell(label, bold=True, color=STATUS_CLR.get(label, T["muted"]), align="CENTER"),
            ])
        cwv_t = std_table(
            ["Page", "LCP (lab)", "CLS (lab)", "Lighthouse Perf", "Lighthouse SEO", "Status"],
            cwv_rows, [0.28, 0.12, 0.12, 0.17, 0.17, 0.14])
        els += [cwv_t, Spacer(1, 3*mm)]

    if issues:
        SEV_ORD = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        if reader == "exec":
            show_issues = [i for i in issues if i.get("severity") in ("CRITICAL", "HIGH")]
            if len(show_issues) < len(issues):
                els.append(Paragraph(
                    f"Exec view: CRITICAL and HIGH issues only. "
                    f"{len(issues) - len(show_issues)} MEDIUM/LOW issues not shown.",
                    styles["muted"]))
        else:
            show_issues = issues

        els.append(Paragraph("5B - On-Page Issues", styles["h3"]))
        SEV_CLR = {"CRITICAL": HexColor("#991B1B"), "HIGH": T["danger"],
                   "MEDIUM": T["warn"], "LOW": T["accent"]}
        iss_rows = []
        for iss in sorted(show_issues,
                          key=lambda x: SEV_ORD.index(x.get("severity","LOW"))
                          if x.get("severity","LOW") in SEV_ORD else 99):
            sev = iss.get("severity", "")
            iss_rows.append([
                cell(iss.get("issue", "")),
                cell(sev, bold=True, color=SEV_CLR.get(sev, T["warn"]), align="CENTER"),
                cell(str(safe_int(iss.get("pages_affected", iss.get("pages", 1)))), align="CENTER"),
                cell(iss.get("impact", "")),
                cell(iss.get("fix", "")),
            ])
        iss_t = std_table(
            ["Issue","Severity","Pages","Impact","Recommended Fix"],
            iss_rows, [0.27, 0.11, 0.08, 0.16, 0.38])
        els += [iss_t, Spacer(1, 3*mm)]

    ins = sec.get("insight", "")
    if ins: els += insight_box(ins, styles)
    return els


# ── AI / LLM Visibility Section ───────────────────────────────────────────────

def build_ai_llm(sec, cfg, styles):
    els = [PageBreak()]
    els += section_header("AI & LLM Visibility (GEO Readiness)", "AI", styles)
    if not sec:
        return els + no_data_box("AI / LLM Visibility")

    metrics        = sec.get("metrics",             {}) or {}
    google_mentions= sec.get("google_mentions",     []) or []
    chatgpt_mentions=sec.get("chatgpt_mentions",    []) or []
    ai_kws         = sec.get("ai_overview_keywords",[]) or []

    els.append(Paragraph(
        "GEO (Generative Engine Optimization) tracks how often this domain appears as a "
        "source or mention in AI-generated answers (ChatGPT, Gemini, Perplexity, etc.). "
        "Powered by DataForSEO AI Optimization API.",
        styles["muted"]))
    els.append(Spacer(1, 3*mm))

    kpis = [
        KPICard("Total LLM Mentions",  fmt_num(metrics.get("total_mentions")),  None, True),
        KPICard("Citations",           fmt_num(metrics.get("citations_count")), None, True,
                sub="cited as source in AI answers"),
        KPICard("Avg. Mention Position",
                str(round(safe_float(metrics.get("avg_position")), 1))
                if metrics.get("avg_position") else "n/a", None, True),
        KPICard("LLM Models Tracked",  str(metrics.get("models_count", "n/a")), None, True),
    ]
    kpi_t = Table([[k for k in kpis]], colWidths=[44*mm]*4, rowHeights=[26*mm])
    kpi_t.setStyle(TableStyle([
        ("ALIGN",        (0,0),(-1,-1),"CENTER"),
        ("VALIGN",       (0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",  (0,0),(-1,-1),1*mm),
        ("RIGHTPADDING", (0,0),(-1,-1),1*mm),
    ]))
    els += [kpi_t, Spacer(1, 4*mm)]

    if ai_kws:
        els.append(Paragraph(
            f"Keywords triggering AI Overview in SERP ({len(ai_kws)} of tracked set):",
            styles["h3"]))
        els.append(Paragraph(", ".join(ai_kws[:20]), styles["body"]))
        els.append(Spacer(1, 3*mm))

    if google_mentions or chatgpt_mentions:
        els.append(Paragraph("AI Mentions: ChatGPT + AI Overviews", styles["h3"]))

    if google_mentions:
        els.append(Paragraph("Google AI Overviews", styles["h4"]))
        g_rows = []
        for m in google_mentions[:8]:
            g_rows.append([
                cell(m.get("query", "")),
                cell(m.get("mention_type", m.get("type", "n/a")), align="CENTER"),
            ])
        g_t = std_table(["Query", "Mention Type"], g_rows, [0.72, 0.28])
        els += [g_t, Spacer(1, 3*mm)]

    if chatgpt_mentions:
        els.append(Paragraph("ChatGPT", styles["h4"]))
        c_rows = []
        for m in chatgpt_mentions[:8]:
            c_rows.append([
                cell(m.get("query", "")),
                cell(m.get("mention_type", m.get("type", "n/a")), align="CENTER"),
            ])
        c_t = std_table(["Query", "Mention Type"], c_rows, [0.72, 0.28])
        els += [c_t, Spacer(1, 3*mm)]

    ins = sec.get("insight", "")
    if ins: els += insight_box(ins, styles)
    return els


# ── Section 06 -- Next Actions ────────────────────────────────────────────────

def build_s6(sec, cfg, styles):
    framing      = cfg.get("framing", {})
    header       = framing.get("s6_header",  "Next Actions")
    framing_note = framing.get("s6_framing", "")
    els = [PageBreak()]
    els += section_header(header, 6, styles)

    actions = sec.get("actions", []) or []
    if not actions:
        return els + no_data_box("Next Actions")

    if framing_note:
        els.append(Paragraph(framing_note, styles["muted"]))
        els.append(Spacer(1, 3*mm))

    IMPACT_CLR = {"Very High": T["success"], "High": T["success"],
                  "Medium": T["warn"], "Low": T["accent"]}

    for idx, action in enumerate(actions, 1):
        title  = action.get("title", "")
        why    = action.get("why", "")
        acts   = action.get("actions", "")
        effort = action.get("effort", "n/a")
        impact = action.get("impact", "")
        owner  = action.get("owner",  "n/a")

        hdr = Table([[
            Paragraph(f"<b>{idx}</b>", ParagraphStyle(
                "an", fontName="DejaVu-Bold", fontSize=12,
                textColor=colors.white, alignment=TA_CENTER)),
            Paragraph(f"<b>{title}</b>", ParagraphStyle(
                "at", fontName="DejaVu-Bold", fontSize=10,
                textColor=colors.white, leading=14, wordWrap="LTR")),
        ]], colWidths=[12*mm, PW - 2*MARGIN - 12*mm])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), T["accent"]),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 2.5*mm),
            ("BOTTOMPADDING", (0,0),(-1,-1), 2.5*mm),
            ("LEFTPADDING",   (1,0),(1,-1),  3*mm),
            ("RIGHTPADDING",  (1,0),(1,-1),  3*mm),
        ]))
        els.append(hdr)

        bs = ParagraphStyle("wb", fontName="DejaVu", fontSize=9,
                            textColor=T["primary"], leading=13, wordWrap="LTR")
        if why:
            bt = Table([[Paragraph(f"<b>Why:</b>  {why}", bs)]],
                       colWidths=[PW - 2*MARGIN])
            bt.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), T["bg"]),
                ("LEFTPADDING",   (0,0),(-1,-1), 4*mm),("RIGHTPADDING",(0,0),(-1,-1),4*mm),
                ("TOPPADDING",    (0,0),(-1,-1), 2*mm),("BOTTOMPADDING",(0,0),(-1,-1),1.5*mm),
            ]))
            els.append(bt)

        if acts:
            act_str = acts if isinstance(acts, str) else "\n".join(acts)
            at = Table([[Paragraph(f"<b>Actions:</b>  {act_str}", bs)]],
                       colWidths=[PW - 2*MARGIN])
            at.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), colors.white),
                ("LEFTPADDING",   (0,0),(-1,-1), 4*mm),("RIGHTPADDING",(0,0),(-1,-1),4*mm),
                ("TOPPADDING",    (0,0),(-1,-1), 1.5*mm),("BOTTOMPADDING",(0,0),(-1,-1),2*mm),
            ]))
            els.append(at)

        imp_key = next((k for k in IMPACT_CLR if impact.startswith(k)), None)
        imp_col = IMPACT_CLR.get(imp_key, T["muted"])
        ms = ParagraphStyle("m", fontName="DejaVu", fontSize=8,
                            textColor=T["muted"], wordWrap="LTR")
        mt = Table([[
            Paragraph(f"<b>Effort:</b>  {effort}", ms),
            Paragraph(f"<b>Impact:</b>  {impact}", ParagraphStyle(
                "imp", fontName="DejaVu-Bold", fontSize=8,
                textColor=imp_col, wordWrap="LTR")),
            Paragraph(f"<b>Owner:</b>  {owner}", ms),
        ]], colWidths=[(PW - 2*MARGIN) / 3] * 3)
        mt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), HexColor("#EFF6FF")),
            ("LEFTPADDING",   (0,0),(-1,-1), 4*mm),("RIGHTPADDING",(0,0),(-1,-1),3*mm),
            ("TOPPADDING",    (0,0),(-1,-1), 1.5*mm),("BOTTOMPADDING",(0,0),(-1,-1),1.5*mm),
            ("LINEABOVE",     (0,0),(-1,0),  0.5, T["grid"]),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ]))
        els += [mt, Spacer(1, 4*mm)]
    return els


# ── Keyword Appendix ──────────────────────────────────────────────────────────

def build_keyword_appendix(sec, cfg, styles):
    keywords = sec.get("keywords", []) or []
    if not keywords: return []
    els = [PageBreak()]
    t = Table([[cell("APPENDIX -- Full Keyword Table", bold=True,
                     color=colors.white, size=11)]],
              colWidths=[PW - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), T["muted"]),
        ("TOPPADDING",    (0,0),(-1,-1), 3*mm),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3*mm),
        ("LEFTPADDING",   (0,0),(-1,-1), 4*mm),
    ]))
    els += [t, Spacer(1, 4*mm)]
    has_prev = any(kw.get("pos_previous") is not None for kw in keywords)
    STATUS_CLR = {"WIN":T["success"],"RISK":T["danger"],"WATCH":T["warn"],
                  "STABLE":T["muted"],"NEW":T["accent"],"LOST":T["danger"]}
    kw_rows = _keyword_rows(keywords, "manager", STATUS_CLR, has_prev)
    els += [_keyword_table(kw_rows, has_prev)]
    return els


# ── Glossary page ─────────────────────────────────────────────────────────────

def build_glossary(styles):
    els = [PageBreak()]
    t = Table([[cell("METHODOLOGY & GLOSSARY", bold=True, color=colors.white, size=11)]],
              colWidths=[PW - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), T["primary"]),
        ("TOPPADDING",    (0,0),(-1,-1), 3*mm),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3*mm),
        ("LEFTPADDING",   (0,0),(-1,-1), 4*mm),
    ]))
    els += [t, Spacer(1, 5*mm)]

    terms = [
        ("Domain Rating (DR, 0-100)",
         "DataForSEO's authority score for a domain based on the quality and quantity "
         "of its backlinks. The `rank` field from backlinks_summary is used directly "
         "(0-100 scale). A higher score indicates stronger link authority."),
        ("Estimated Organic Traffic (modeled)",
         "A modeled estimate of monthly organic search visits, calculated from keyword "
         "rankings multiplied by click-through-rate curves. This is NOT equivalent to "
         "Google Analytics or Search Console traffic -- it is a market-side estimate "
         "for benchmarking visibility trends. Actual site traffic may differ."),
        ("Visibility Index (VI, 0-100)",
         "A quality-weighted score summarising where a domain ranks across its keyword "
         "set. Formula: (pos1 x1.0 + pos2-3 x0.85 + pos4-10 x0.5 + pos11-20 x0.2 + "
         "pos21-30 x0.05) / total_keywords x 100. A VI rising while traffic is flat "
         "means quality is improving before clicks follow -- this is normal and expected."),
        ("Core Web Vitals: Lab vs Field",
         "LCP, CLS, and performance scores in this report come from Lighthouse (lab "
         "diagnostic, for_mobile: true). Lab scores simulate a controlled page load. "
         "Field CWV from Google CrUX (used for ranking) may differ substantially. "
         "Use lab scores as a diagnostic to identify optimisation priorities."),
        ("Opportunity Keywords",
         "Keywords the domain does not rank for (or ranks beyond page 1) that have "
         "meaningful search volume. Estimated traffic at position 5 is modeled as "
         "volume x 0.065 (65th-percentile CTR for position 5 from industry benchmarks)."),
        ("GEO - Generative Engine Optimization",
         "Measures how often a domain is cited or mentioned in AI-generated answers "
         "from large language models (ChatGPT, Gemini, Perplexity, etc.), tracked via "
         "the DataForSEO AI Optimization API (ai_opt_llm_ment_agg_metrics and "
         "ai_opt_llm_ment_search endpoints)."),
        ("Data Currency",
         "Domain rank overviews and keyword data are from DataForSEO's index, typically "
         "7-14 days behind live Google data. Live SERP calls (serp_organic_live_advanced) "
         "reflect real-time results at the time of the report run."),
    ]

    for term, definition in terms:
        els.append(Paragraph(term, ParagraphStyle(
            "gt", fontName="DejaVu-Bold", fontSize=8.5,
            textColor=T["accent"], spaceAfter=1.5*mm, leading=12)))
        els.append(Paragraph(definition, ParagraphStyle(
            "gd", fontName="DejaVu", fontSize=9,
            textColor=T["primary"], leading=13, spaceAfter=4*mm, wordWrap="LTR")))

    return els


# ── Main builder ──────────────────────────────────────────────────────────────

def build_pdf(data_path: str):
    with open(data_path, encoding="utf-8") as f:
        payload = json.load(f)

    cfg      = payload.get("config",   {})
    sections = payload.get("sections", {})
    styles   = make_styles()

    settings = cfg.get("report_settings", {})
    enabled  = settings.get("enabled_modules", [
        "keyword_rankings", "backlinks", "tech_health", "next_actions"
    ])
    reader   = settings.get("reader", "manager")

    output_path = cfg.get("output_path")
    if not output_path:
        base        = os.path.splitext(data_path)[0]
        output_path = base + ".pdf"

    # TL;DR always leads; sections are conditional
    story = [PageBreak()]

    s1 = sections.get("s1_executive_summary", {}) or {}
    story += build_tldr(s1, cfg, styles)
    story += build_s1(s1, cfg, styles)

    if "keyword_rankings" in enabled:
        story += build_s2(sections.get("s2_keyword_rankings", {}), cfg, styles)

    if "local_seo" in enabled:
        story += build_local(sections.get("s_local", {}), cfg, styles)

    if "competitor_snapshot" in enabled:
        story += build_s3(sections.get("s3_competitor_snapshot", {}), cfg, styles)

    if "backlinks" in enabled:
        story += build_s4(sections.get("s4_backlinks", {}), cfg, styles)

    if "tech_health" in enabled:
        story += build_s5(sections.get("s5_technical_health", {}), cfg, styles)

    if "ai_llm_visibility" in enabled:
        story += build_ai_llm(sections.get("s_ai_llm", {}), cfg, styles)

    if "next_actions" in enabled:
        story += build_s6(sections.get("s6_next_actions", {}), cfg, styles)

    # Appendix: full keyword table for exec reader (they only get movers in body)
    if reader == "exec" and "keyword_rankings" in enabled:
        story += build_keyword_appendix(
            sections.get("s2_keyword_rankings", {}), cfg, styles)

    story += build_glossary(styles)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=16*mm, bottomMargin=14*mm,
        title=(f"{cfg.get('client_domain','')} -- "
               f"{cfg.get('framing',{}).get('cover_title','SEO Report')} -- "
               f"{cfg.get('period_current','')}"),
        subject="SEO Visibility & Opportunity Report",
    )

    def on_first(canvas, doc): draw_cover(canvas, doc, cfg)
    def on_later(canvas, doc): page_template(canvas, doc, cfg)

    doc.build(story, onFirstPage=on_first, onLaterPages=on_later)
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_report.py <data.json>")
        sys.exit(1)
    out = build_pdf(sys.argv[1])
    print(f"Report saved: {out}")
