"""Color palette for birthdays: Google Calendar's 11 event colors, plus 10
extra popular colors for more variety. Telegram messages can't render
arbitrary hex colors, so each entry maps to an emoji swatch as the closest
visual stand-in, alongside the real hex value for reference.
"""

GOOGLE_CALENDAR_COLORS = {
    # --- Google Calendar's 11 official event colors ---
    1: {"name": "Lavender", "hex": "#7986CB", "emoji": "\U0001F7E3"},
    2: {"name": "Sage", "hex": "#33B679", "emoji": "\U0001F7E2"},
    3: {"name": "Grape", "hex": "#8E24AA", "emoji": "\U0001F7EA"},
    4: {"name": "Flamingo", "hex": "#E67C73", "emoji": "\U0001F338"},
    5: {"name": "Banana", "hex": "#F6BF26", "emoji": "\U0001F7E1"},
    6: {"name": "Tangerine", "hex": "#F4511E", "emoji": "\U0001F7E0"},
    7: {"name": "Peacock", "hex": "#039BE5", "emoji": "\U0001F535"},
    8: {"name": "Graphite", "hex": "#616161", "emoji": "\u26AB"},
    9: {"name": "Blueberry", "hex": "#3F51B5", "emoji": "\U0001F539"},
    10: {"name": "Basil", "hex": "#0B8043", "emoji": "\U0001F7E9"},
    11: {"name": "Tomato", "hex": "#D50000", "emoji": "\U0001F534"},
    # --- 10 extra popular colors ---
    12: {"name": "Red", "hex": "#E53935", "emoji": "\U0001F7E5"},
    13: {"name": "Black", "hex": "#000000", "emoji": "\u2B1B"},
    14: {"name": "White", "hex": "#FFFFFF", "emoji": "\u2B1C"},
    15: {"name": "Brown", "hex": "#795548", "emoji": "\U0001F7E4"},
    16: {"name": "Turquoise", "hex": "#1ABC9C", "emoji": "\U0001FA75"},
    17: {"name": "Pink", "hex": "#FF69B4", "emoji": "\U0001FA77"},
    18: {"name": "Gold", "hex": "#FFD700", "emoji": "\U0001F7E8"},
    19: {"name": "Navy", "hex": "#1A237E", "emoji": "\U0001F499"},
    20: {"name": "Mint", "hex": "#98FF98", "emoji": "\U0001F343"},
    21: {"name": "Coral", "hex": "#FF7F50", "emoji": "\U0001F9E1"},
}


def color_label(color_id: int) -> str:
    c = GOOGLE_CALENDAR_COLORS.get(color_id)
    if not c:
        return ""
    return f"{c['emoji']} {c['name']}"
