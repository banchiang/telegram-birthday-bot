"""Google Calendar's 11-color event palette, mapped to Telegram-friendly emoji
swatches (Telegram messages can't render arbitrary hex colors, so an emoji is
the closest visual stand-in) plus the real hex value for reference/export.
"""

GOOGLE_CALENDAR_COLORS = {
    1: {"name": "Lavender", "hex": "#7986CB", "emoji": "🟣"},
    2: {"name": "Sage", "hex": "#33B679", "emoji": "🟢"},
    3: {"name": "Grape", "hex": "#8E24AA", "emoji": "🟪"},
    4: {"name": "Flamingo", "hex": "#E67C73", "emoji": "🌸"},
    5: {"name": "Banana", "hex": "#F6BF26", "emoji": "🟡"},
    6: {"name": "Tangerine", "hex": "#F4511E", "emoji": "🟠"},
    7: {"name": "Peacock", "hex": "#039BE5", "emoji": "🔵"},
    8: {"name": "Graphite", "hex": "#616161", "emoji": "⚫"},
    9: {"name": "Blueberry", "hex": "#3F51B5", "emoji": "🔷"},
    10: {"name": "Basil", "hex": "#0B8043", "emoji": "🟩"},
    11: {"name": "Tomato", "hex": "#D50000", "emoji": "🔴"},
}


def color_label(color_id: int) -> str:
    c = GOOGLE_CALENDAR_COLORS.get(color_id)
    if not c:
        return ""
    return f"{c['emoji']} {c['name']}"
