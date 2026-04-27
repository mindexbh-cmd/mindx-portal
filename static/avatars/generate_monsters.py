"""Parametric SVG monster generator for the points-system avatars.

All monsters are 100% original artwork built from primitive shapes
(circle / ellipse / path / rect). No copied assets, no protected IP.

The 30 catalogued monsters in MONSTERS below are hand-picked
combinations from a much larger parametric space (5 body shapes x
15 colors x 3 eye styles x 4 mouths x 4 ear/horn styles x 3 cheek
accessories = 10,800 possible critters).

Usage:
    from static.avatars.generate_monsters import regenerate_all
    regenerate_all()  # writes 31 .svg files into ./svg/

Or, equivalently:
    python -m static.avatars.generate_monsters
"""

import os

# ── PALETTE ─────────────────────────────────────────────────────────
# 15 friendly, high-saturation colors. Each entry is (body, shadow,
# horn) — shadow is a slightly darker tone for the belly highlight,
# horn is a contrasting tone for ears/horns/antennas.
COLORS = [
    ("#2BC4C4", "#1F9D9D", "#FFD166"),  # turquoise
    ("#FF6F61", "#D9544C", "#FFE066"),  # coral
    ("#A8E063", "#7CB342", "#FF7043"),  # lime
    ("#B39DDB", "#8579C2", "#FFD166"),  # lavender
    ("#FFB088", "#E89370", "#7BC8C8"),  # peach
    ("#7DE2D1", "#52BFAE", "#FF8FA3"),  # mint
    ("#7CC8FF", "#4FA8E0", "#FFCC66"),  # sky blue
    ("#FFD93D", "#E0BB1F", "#7BC8C8"),  # sunshine yellow
    ("#FF6FB5", "#E04B97", "#FFE066"),  # hot pink
    ("#9B7EDE", "#7A5EC7", "#FFD166"),  # ultraviolet
    ("#FF8C42", "#E0701F", "#7BC8C8"),  # tangerine
    ("#5BC0EB", "#369AC4", "#FFB347"),  # cerulean
    ("#C589E8", "#A766CC", "#FFD166"),  # orchid
    ("#5DD39E", "#37B580", "#FF8FA3"),  # spring
    ("#F25F5C", "#D14442", "#FFE066"),  # cherry
]


def _safe_id(s):
    return "".join(c if c.isalnum() else "_" for c in str(s))


# ── BODY SHAPES ─────────────────────────────────────────────────────
def body_circle(cx, cy, fill, shadow):
    return (
        '<ellipse cx="' + str(cx) + '" cy="' + str(cy + 6) + '" rx="58" ry="10" fill="rgba(0,0,0,0.10)"/>'
        '<circle cx="' + str(cx) + '" cy="' + str(cy) + '" r="52" fill="' + fill + '"/>'
        '<path d="M' + str(cx - 42) + ' ' + str(cy + 16) + ' Q' + str(cx) + ' ' + str(cy + 60) + ' ' + str(cx + 42) + ' ' + str(cy + 16)
        + ' Q' + str(cx) + ' ' + str(cy + 38) + ' ' + str(cx - 42) + ' ' + str(cy + 16) + ' Z" fill="' + shadow + '" opacity="0.55"/>'
    )


def body_oval(cx, cy, fill, shadow):
    return (
        '<ellipse cx="' + str(cx) + '" cy="' + str(cy + 6) + '" rx="50" ry="9" fill="rgba(0,0,0,0.10)"/>'
        '<ellipse cx="' + str(cx) + '" cy="' + str(cy) + '" rx="44" ry="56" fill="' + fill + '"/>'
        '<path d="M' + str(cx - 36) + ' ' + str(cy + 18) + ' Q' + str(cx) + ' ' + str(cy + 60) + ' ' + str(cx + 36) + ' ' + str(cy + 18)
        + ' Q' + str(cx) + ' ' + str(cy + 40) + ' ' + str(cx - 36) + ' ' + str(cy + 18) + ' Z" fill="' + shadow + '" opacity="0.55"/>'
    )


def body_blob(cx, cy, fill, shadow):
    return (
        '<ellipse cx="' + str(cx) + '" cy="' + str(cy + 6) + '" rx="58" ry="10" fill="rgba(0,0,0,0.10)"/>'
        '<path d="M' + str(cx - 50) + ' ' + str(cy - 20)
        + ' Q' + str(cx - 60) + ' ' + str(cy + 30) + ' ' + str(cx - 30) + ' ' + str(cy + 56)
        + ' Q' + str(cx) + ' ' + str(cy + 70) + ' ' + str(cx + 30) + ' ' + str(cy + 56)
        + ' Q' + str(cx + 60) + ' ' + str(cy + 30) + ' ' + str(cx + 50) + ' ' + str(cy - 20)
        + ' Q' + str(cx + 30) + ' ' + str(cy - 50) + ' ' + str(cx) + ' ' + str(cy - 50)
        + ' Q' + str(cx - 30) + ' ' + str(cy - 50) + ' ' + str(cx - 50) + ' ' + str(cy - 20) + ' Z" fill="' + fill + '"/>'
        '<path d="M' + str(cx - 38) + ' ' + str(cy + 20) + ' Q' + str(cx) + ' ' + str(cy + 56) + ' ' + str(cx + 38) + ' ' + str(cy + 20)
        + ' Q' + str(cx) + ' ' + str(cy + 38) + ' ' + str(cx - 38) + ' ' + str(cy + 20) + ' Z" fill="' + shadow + '" opacity="0.55"/>'
    )


def body_pear(cx, cy, fill, shadow):
    # Wider at bottom, narrower at top
    return (
        '<ellipse cx="' + str(cx) + '" cy="' + str(cy + 6) + '" rx="60" ry="10" fill="rgba(0,0,0,0.10)"/>'
        '<path d="M' + str(cx - 32) + ' ' + str(cy - 38)
        + ' Q' + str(cx - 58) + ' ' + str(cy + 18) + ' ' + str(cx - 38) + ' ' + str(cy + 56)
        + ' Q' + str(cx) + ' ' + str(cy + 70) + ' ' + str(cx + 38) + ' ' + str(cy + 56)
        + ' Q' + str(cx + 58) + ' ' + str(cy + 18) + ' ' + str(cx + 32) + ' ' + str(cy - 38)
        + ' Q' + str(cx) + ' ' + str(cy - 50) + ' ' + str(cx - 32) + ' ' + str(cy - 38) + ' Z" fill="' + fill + '"/>'
        '<path d="M' + str(cx - 38) + ' ' + str(cy + 22) + ' Q' + str(cx) + ' ' + str(cy + 58) + ' ' + str(cx + 38) + ' ' + str(cy + 22)
        + ' Q' + str(cx) + ' ' + str(cy + 40) + ' ' + str(cx - 38) + ' ' + str(cy + 22) + ' Z" fill="' + shadow + '" opacity="0.55"/>'
    )


def body_squareish(cx, cy, fill, shadow):
    # Rounded rectangle with arms hint
    return (
        '<ellipse cx="' + str(cx) + '" cy="' + str(cy + 6) + '" rx="52" ry="10" fill="rgba(0,0,0,0.10)"/>'
        '<rect x="' + str(cx - 46) + '" y="' + str(cy - 48) + '" width="92" height="100" rx="32" ry="32" fill="' + fill + '"/>'
        '<path d="M' + str(cx - 36) + ' ' + str(cy + 18) + ' Q' + str(cx) + ' ' + str(cy + 56) + ' ' + str(cx + 36) + ' ' + str(cy + 18)
        + ' Q' + str(cx) + ' ' + str(cy + 38) + ' ' + str(cx - 36) + ' ' + str(cy + 18) + ' Z" fill="' + shadow + '" opacity="0.55"/>'
    )


BODIES = [body_circle, body_oval, body_blob, body_pear, body_squareish]


# ── EYES ────────────────────────────────────────────────────────────
def eye_one_big(cx, cy):
    return (
        '<circle cx="' + str(cx) + '" cy="' + str(cy - 6) + '" r="22" fill="#FFFFFF"/>'
        '<circle cx="' + str(cx) + '" cy="' + str(cy - 6) + '" r="22" fill="none" stroke="#212121" stroke-width="2.5" opacity="0.4"/>'
        '<circle cx="' + str(cx + 2) + '" cy="' + str(cy - 4) + '" r="11" fill="#212121"/>'
        '<circle cx="' + str(cx + 6) + '" cy="' + str(cy - 8) + '" r="4" fill="#FFFFFF"/>'
    )


def eye_two(cx, cy):
    out = ''
    for ox in (-16, 16):
        out += (
            '<circle cx="' + str(cx + ox) + '" cy="' + str(cy - 4) + '" r="11" fill="#FFFFFF"/>'
            '<circle cx="' + str(cx + ox) + '" cy="' + str(cy - 4) + '" r="11" fill="none" stroke="#212121" stroke-width="1.6" opacity="0.4"/>'
            '<circle cx="' + str(cx + ox + 1) + '" cy="' + str(cy - 3) + '" r="6" fill="#212121"/>'
            '<circle cx="' + str(cx + ox + 3) + '" cy="' + str(cy - 5) + '" r="2.2" fill="#FFFFFF"/>'
        )
    return out


def eye_three(cx, cy):
    out = ''
    for ox, oy, r in ((-22, 0, 8), (0, -10, 9), (22, 0, 8)):
        out += (
            '<circle cx="' + str(cx + ox) + '" cy="' + str(cy + oy) + '" r="' + str(r) + '" fill="#FFFFFF"/>'
            '<circle cx="' + str(cx + ox) + '" cy="' + str(cy + oy) + '" r="' + str(r) + '" fill="none" stroke="#212121" stroke-width="1.4" opacity="0.4"/>'
            '<circle cx="' + str(cx + ox + 1) + '" cy="' + str(cy + oy + 1) + '" r="' + str(r - 4) + '" fill="#212121"/>'
            '<circle cx="' + str(cx + ox + 2) + '" cy="' + str(cy + oy - 1) + '" r="1.6" fill="#FFFFFF"/>'
        )
    return out


EYES = [eye_one_big, eye_two, eye_three]


# ── MOUTHS ──────────────────────────────────────────────────────────
def mouth_smile(cx, cy):
    return (
        '<path d="M' + str(cx - 14) + ' ' + str(cy + 22) + ' Q' + str(cx) + ' ' + str(cy + 36) + ' ' + str(cx + 14) + ' ' + str(cy + 22)
        + '" stroke="#212121" stroke-width="3" fill="none" stroke-linecap="round"/>'
    )


def mouth_open_teeth(cx, cy):
    return (
        '<path d="M' + str(cx - 18) + ' ' + str(cy + 22) + ' Q' + str(cx) + ' ' + str(cy + 40) + ' ' + str(cx + 18) + ' ' + str(cy + 22)
        + ' Q' + str(cx) + ' ' + str(cy + 30) + ' ' + str(cx - 18) + ' ' + str(cy + 22) + ' Z" fill="#5D2F36"/>'
        '<rect x="' + str(cx - 10) + '" y="' + str(cy + 22) + '" width="6" height="6" fill="#FFFFFF"/>'
        '<rect x="' + str(cx + 4) + '" y="' + str(cy + 22) + '" width="6" height="6" fill="#FFFFFF"/>'
    )


def mouth_tiny(cx, cy):
    return (
        '<path d="M' + str(cx - 6) + ' ' + str(cy + 24) + ' Q' + str(cx) + ' ' + str(cy + 30) + ' ' + str(cx + 6) + ' ' + str(cy + 24)
        + '" stroke="#212121" stroke-width="2.4" fill="none" stroke-linecap="round"/>'
    )


def mouth_o(cx, cy):
    return (
        '<ellipse cx="' + str(cx) + '" cy="' + str(cy + 26) + '" rx="6" ry="8" fill="#5D2F36"/>'
        '<ellipse cx="' + str(cx + 1) + '" cy="' + str(cy + 24) + '" rx="2.5" ry="3" fill="#FFFFFF" opacity="0.5"/>'
    )


MOUTHS = [mouth_smile, mouth_open_teeth, mouth_tiny, mouth_o]


# ── HORNS / EARS / ANTENNAS ────────────────────────────────────────
def horn_small(cx, cy, accent):
    # Two small horns on top.
    return (
        '<path d="M' + str(cx - 24) + ' ' + str(cy - 50) + ' L' + str(cx - 18) + ' ' + str(cy - 70) + ' L' + str(cx - 12) + ' ' + str(cy - 50)
        + ' Z" fill="' + accent + '" stroke="#212121" stroke-width="1.4" stroke-linejoin="round"/>'
        '<path d="M' + str(cx + 12) + ' ' + str(cy - 50) + ' L' + str(cx + 18) + ' ' + str(cy - 70) + ' L' + str(cx + 24) + ' ' + str(cy - 50)
        + ' Z" fill="' + accent + '" stroke="#212121" stroke-width="1.4" stroke-linejoin="round"/>'
    )


def ears_floppy(cx, cy, accent):
    return (
        '<ellipse cx="' + str(cx - 50) + '" cy="' + str(cy - 18) + '" rx="14" ry="22" fill="' + accent + '" stroke="#212121" stroke-width="1.4" transform="rotate(-22 ' + str(cx - 50) + ' ' + str(cy - 18) + ')"/>'
        '<ellipse cx="' + str(cx + 50) + '" cy="' + str(cy - 18) + '" rx="14" ry="22" fill="' + accent + '" stroke="#212121" stroke-width="1.4" transform="rotate(22 ' + str(cx + 50) + ' ' + str(cy - 18) + ')"/>'
    )


def antenna_ball(cx, cy, accent):
    return (
        '<line x1="' + str(cx) + '" y1="' + str(cy - 50) + '" x2="' + str(cx) + '" y2="' + str(cy - 78) + '" stroke="#212121" stroke-width="2.6" stroke-linecap="round"/>'
        '<circle cx="' + str(cx) + '" cy="' + str(cy - 84) + '" r="8" fill="' + accent + '" stroke="#212121" stroke-width="1.6"/>'
        '<circle cx="' + str(cx - 2) + '" cy="' + str(cy - 86) + '" r="2.4" fill="#FFFFFF" opacity="0.7"/>'
    )


def horn_none(cx, cy, accent):
    return ''


HORNS = [horn_small, ears_floppy, antenna_ball, horn_none]


# ── ACCESSORIES ────────────────────────────────────────────────────
def acc_blush(cx, cy):
    return (
        '<ellipse cx="' + str(cx - 28) + '" cy="' + str(cy + 14) + '" rx="8" ry="5" fill="#FF6FB5" opacity="0.55"/>'
        '<ellipse cx="' + str(cx + 28) + '" cy="' + str(cy + 14) + '" rx="8" ry="5" fill="#FF6FB5" opacity="0.55"/>'
    )


def acc_freckles(cx, cy):
    out = ''
    for dx, dy in ((-22, 12), (-14, 16), (14, 16), (22, 12), (-18, 20), (18, 20)):
        out += '<circle cx="' + str(cx + dx) + '" cy="' + str(cy + dy) + '" r="1.4" fill="#212121" opacity="0.4"/>'
    return out


def acc_none(cx, cy):
    return ''


ACCS = [acc_blush, acc_freckles, acc_none]


# ── COMPOSITION ─────────────────────────────────────────────────────
SVG_HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" '
    'role="img" aria-label="MONSTER_LABEL">'
)
SVG_FOOTER = '</svg>'


def generate_monster_svg(body_idx, color_idx, eye_idx, mouth_idx, horn_idx, acc_idx, label="monster"):
    """Build one monster SVG from parametric components."""
    cx, cy = 100, 100
    color = COLORS[color_idx % len(COLORS)]
    fill, shadow, accent = color
    parts = [SVG_HEADER.replace("MONSTER_LABEL", label)]
    parts.append(HORNS[horn_idx % len(HORNS)](cx, cy, accent))
    parts.append(BODIES[body_idx % len(BODIES)](cx, cy, fill, shadow))
    parts.append(ACCS[acc_idx % len(ACCS)](cx, cy))
    parts.append(EYES[eye_idx % len(EYES)](cx, cy))
    parts.append(MOUTHS[mouth_idx % len(MOUTHS)](cx, cy))
    parts.append(SVG_FOOTER)
    return "".join(parts)


def generate_egg_svg():
    """Default 'unhatched' purple egg with subtle hexagon pattern."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" '
        'role="img" aria-label="egg">'
        '<defs>'
        '<linearGradient id="egGrad" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#9A8FE8"/>'
        '<stop offset="0.55" stop-color="#7F77DD"/>'
        '<stop offset="1" stop-color="#5C4FB0"/>'
        '</linearGradient>'
        '<pattern id="egPat" width="22" height="20" patternUnits="userSpaceOnUse">'
        '<polygon points="11,2 20,7 20,15 11,20 2,15 2,7" fill="none" stroke="#FFFFFF" stroke-opacity="0.20" stroke-width="1.1"/>'
        '</pattern>'
        '<radialGradient id="egGloss" cx="0.3" cy="0.25" r="0.55">'
        '<stop offset="0" stop-color="#FFFFFF" stop-opacity="0.55"/>'
        '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>'
        '</radialGradient>'
        '</defs>'
        '<ellipse cx="100" cy="178" rx="56" ry="9" fill="rgba(0,0,0,0.18)"/>'
        '<g transform="rotate(-8 100 100)">'
        '<path d="M100 22 C 158 22 172 92 172 122 C 172 156 142 178 100 178 C 58 178 28 156 28 122 C 28 92 42 22 100 22 Z" fill="url(#egGrad)"/>'
        '<path d="M100 22 C 158 22 172 92 172 122 C 172 156 142 178 100 178 C 58 178 28 156 28 122 C 28 92 42 22 100 22 Z" fill="url(#egPat)"/>'
        '<path d="M100 22 C 158 22 172 92 172 122 C 172 156 142 178 100 178 C 58 178 28 156 28 122 C 28 92 42 22 100 22 Z" fill="url(#egGloss)"/>'
        '<path d="M100 22 C 158 22 172 92 172 122 C 172 156 142 178 100 178 C 58 178 28 156 28 122 C 28 92 42 22 100 22 Z" fill="none" stroke="#3D3478" stroke-width="2.5" stroke-opacity="0.55"/>'
        '<ellipse cx="78" cy="68" rx="12" ry="20" fill="#FFFFFF" opacity="0.35"/>'
        '</g>'
        '</svg>'
    )


# ── 30 hand-picked monster combinations ────────────────────────────
# (body_idx, color_idx, eye_idx, mouth_idx, horn_idx, acc_idx, name_ar, category)
# Categories: "ذكر", "أنثى", "محايد" — 10 each, distributed evenly.
MONSTERS = [
    # 1-10  (mostly "ذكر")
    (0,  0, 1, 0, 0, 0, "وحش فيروزي مبتسم",       "ذكر"),
    (2,  1, 0, 1, 0, 1, "وحش مرجاني بعين واحدة",  "ذكر"),
    (4,  6, 1, 0, 0, 0, "وحش سماوي ودود",         "ذكر"),
    (3,  9, 0, 1, 0, 1, "وحش بنفسجي بأسنان",      "ذكر"),
    (0,  4, 1, 0, 0, 0, "وحش خوخي مرح",           "ذكر"),
    (2, 10, 0, 1, 0, 0, "وحش يوسفي شجاع",         "ذكر"),
    (4, 11, 1, 0, 0, 1, "وحش سيرولين هادئ",       "ذكر"),
    (3,  2, 0, 1, 0, 0, "وحش ليموني نشيط",        "ذكر"),
    (0, 14, 1, 0, 0, 0, "وحش كرزي قوي",           "ذكر"),
    (2,  5, 1, 0, 0, 1, "وحش نعناعي لطيف",        "ذكر"),

    # 11-20  (mostly "أنثى")
    (1,  8, 1, 2, 1, 0, "وحشة وردية بأذنين",      "أنثى"),
    (1, 12, 1, 2, 1, 0, "وحشة أوركيد ناعمة",      "أنثى"),
    (3,  5, 1, 2, 1, 0, "وحشة نعناعية حالمة",     "أنثى"),
    (1,  7, 1, 2, 1, 0, "وحشة شمسية مشرقة",       "أنثى"),
    (1,  3, 1, 2, 1, 0, "وحشة لافندر هادئة",      "أنثى"),
    (3,  8, 1, 2, 1, 1, "وحشة وردية مزخرفة",      "أنثى"),
    (1, 13, 1, 2, 1, 0, "وحشة ربيعية جميلة",      "أنثى"),
    (3, 12, 1, 2, 1, 0, "وحشة أوركيد محبوبة",     "أنثى"),
    (1,  4, 1, 2, 1, 0, "وحشة خوخية لطيفة",       "أنثى"),
    (3,  3, 1, 0, 1, 1, "وحشة لافندر مبتسمة",     "أنثى"),

    # 21-30  ("محايد" — antennas / 3 eyes / no horns)
    (2,  2, 2, 1, 2, 2, "وحش ليموني بثلاث عيون",  "محايد"),
    (4, 13, 2, 1, 2, 0, "وحش ربيعي بهوائي",        "محايد"),
    (2,  6, 2, 0, 2, 2, "وحش سماوي فضولي",         "محايد"),
    (4,  9, 0, 3, 2, 0, "وحش بنفسجي مدهوش",        "محايد"),
    (2, 11, 0, 0, 3, 1, "وحش سيرولين أصلع",        "محايد"),
    (4,  0, 2, 1, 2, 0, "وحش فيروزي ذكي",          "محايد"),
    (2,  7, 0, 3, 3, 0, "وحش شمسي مفاجأ",          "محايد"),
    (4,  1, 2, 0, 2, 1, "وحش مرجاني فضائي",        "محايد"),
    (2, 14, 0, 3, 3, 0, "وحش كرزي مدهوش",          "محايد"),
    (4,  8, 2, 1, 2, 1, "وحش وردي خيالي",          "محايد"),
]


def regenerate_all(out_dir=None):
    """Write 30 monster SVGs + the egg into <out_dir>/svg/.

    Returns a dict with counts so callers can report status.
    Idempotent: existing files are overwritten.
    """
    if out_dir is None:
        out_dir = os.path.dirname(os.path.abspath(__file__))
    svg_dir = os.path.join(out_dir, "svg")
    os.makedirs(svg_dir, exist_ok=True)

    # Egg
    egg_path = os.path.join(svg_dir, "egg.svg")
    with open(egg_path, "w", encoding="utf-8") as f:
        f.write(generate_egg_svg())

    # Monsters
    written = 0
    for idx, m in enumerate(MONSTERS, start=1):
        body_i, color_i, eye_i, mouth_i, horn_i, acc_i, name_ar, _cat = m
        svg = generate_monster_svg(
            body_i, color_i, eye_i, mouth_i, horn_i, acc_i,
            label=_safe_id(name_ar) or ("monster_" + str(idx)),
        )
        path = os.path.join(svg_dir, "monster_" + str(idx).zfill(3) + ".svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        written += 1

    return {"egg": True, "monsters": written, "dir": svg_dir}


def manifest():
    """Return the catalogue used by the avatars-table seeder."""
    rows = [(0, "بيضة", "/static/avatars/svg/egg.svg", "محايد")]
    for idx, m in enumerate(MONSTERS, start=1):
        _b, _c, _e, _mo, _h, _a, name_ar, cat = m
        path = "/static/avatars/svg/monster_" + str(idx).zfill(3) + ".svg"
        rows.append((idx, name_ar, path, cat))
    return rows


if __name__ == "__main__":
    res = regenerate_all()
    print("Egg generated:", "OK" if res["egg"] else "FAIL")
    print("Monsters generated:", res["monsters"])
    print("Output dir:", res["dir"])
