"""Build an importable Bitfocus Companion 5 page of Apple TV buttons.

    python build_page.py                         # bridge on the same computer as Companion
    python build_page.py --host 192.168.1.20     # bridge on another computer
    python build_page.py --port 8766 --text-size 28

Writes apple-tv-page.companionconfig next to this script. Import it in Companion under
Import / Export. It brings its own Generic HTTP connection ("appletv-bridge"), or you can
link it to an HTTP connection you already have.
"""
import argparse
import json
import os
import random
import string

HERE = os.path.dirname(os.path.abspath(__file__))
CONN = "appletvBridgeHttp01"

GREY, NAVY, GREEN, PURPLE, TEAL, ORANGE, RED = 0x333333, 0x1F3A68, 0x0F4D1F, 0x4B2A6B, 0x0E5E5E, 0x8A4B00, 0x6B0000

# (row, column): (label, command, color). Column 0, rows 0-2 hold Companion's page up / number / down.
BUTTONS = {
    (0, 1): ("MENU /\\nBACK", "menu", GREY),
    (1, 1): ("HOME", "home", GREY),
    (2, 1): ("CONTROL\\nCENTER", "control_center", GREY),
    (0, 4): ("UP", "up", NAVY),
    (1, 3): ("LEFT", "left", NAVY),
    (1, 4): ("SELECT", "select", GREEN),
    (1, 5): ("RIGHT", "right", NAVY),
    (2, 4): ("DOWN", "down", NAVY),
    (0, 7): ("VOL +", "volume_up", PURPLE),
    (1, 7): ("VOL -", "volume_down", PURPLE),
    (3, 0): ("PLAY /\\nPAUSE", "play_pause", TEAL),
    (3, 1): ("SKIP\\nBACK", "skip_backward", TEAL),
    (3, 2): ("SKIP\\nFWD", "skip_forward", TEAL),
    (3, 6): ("WAKE", "wake", ORANGE),
    (3, 7): ("SLEEP", "sleep", RED),
}


def nid(n=21):
    return "".join(random.choice(string.ascii_letters + string.digits + "_-") for _ in range(n))


def v(x):
    return {"value": x, "isExpression": False}


def button(text, url, bg, size):
    layers = [
        {"id": "canvas", "name": "Canvas", "usage": "auto", "type": "canvas",
         "decoration": v("default"), "showStatusIcons": v("default")},
        {"id": "box0", "name": "Background", "usage": "auto", "type": "box", "enabled": v(True),
         "opacity": v(100), "x": v(0), "y": v(0), "width": v(100), "height": v(100), "rotation": v(0),
         "color": v(bg), "borderWidth": v(0), "borderColor": v(0), "borderPosition": v("inside")},
        {"id": "image0", "name": "Image", "usage": "auto", "type": "image", "enabled": v(True),
         "opacity": v(100), "x": v(0), "y": v(0), "width": v(100), "height": v(100), "rotation": v(0),
         "base64Image": v(None), "halign": v("center"), "valign": v("center"), "fillMode": v("fit")},
        {"id": "text0", "name": "Text", "usage": "auto", "type": "text", "enabled": v(True),
         "opacity": v(100), "x": v(0), "y": v(0), "width": v(100), "height": v(100), "rotation": v(0),
         "text": v(text), "color": v(0xFFFFFF), "halign": v("center"), "valign": v("center"),
         "fontsize": v(size), "fontsizeAllowShrink": v(True), "font": v("companion-sans"),
         "outlineColor": v(4278190080)},
    ]
    action = {"type": "action", "id": nid(), "definitionId": "get", "connectionId": CONN,
              "options": {"url": v(url), "header": v("")}, "upgradeIndex": 1}
    return {"type": "button-layered", "style": {"layers": layers},
            "options": {"stepProgression": "auto", "stepExpression": "", "rotaryActions": False,
                        "canModifyStyleInApis": True, "notes": ""},
            "feedbacks": [],
            "steps": {"0": {"action_sets": {"down": [action], "up": []}, "options": {"runWhileHeld": []}}},
            "localVariables": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--host", default="127.0.0.1", help="computer running bridge.py (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="bridge port (default 8765)")
    parser.add_argument("--text-size", type=int, default=28, help="button text size (default 28)")
    parser.add_argument("--out", default=os.path.join(HERE, "apple-tv-page.companionconfig"))
    args = parser.parse_args()

    base = f"http://{args.host}:{args.port}"
    controls = {"0": {"0": {"type": "pageup"}}, "1": {"0": {"type": "pagenum"}}, "2": {"0": {"type": "pagedown"}}}
    for (r, c), (text, cmd, bg) in BUTTONS.items():
        controls.setdefault(str(r), {})[str(c)] = button(text, f"{base}/{cmd}", bg, args.text_size)

    doc = {"version": 12, "type": "page", "companionBuild": "5.0.2+9665-stable-5eb89669c6",
           "page": {"id": nid(), "name": "Apple TV", "controls": controls,
                    "gridSize": {"minColumn": 0, "maxColumn": 7, "minRow": 0, "maxRow": 3}},
           "instances": {CONN: {"label": "appletv-bridge",
                                "config": {"prefix": "", "rejectUnauthorized": True},
                                "lastUpgradeIndex": 1, "sortOrder": 0, "isFirstInit": False, "enabled": True,
                                "moduleVersionId": "2.5.0", "moduleInstanceType": "connection",
                                "moduleId": "generic-http", "updatePolicy": "stable"}},
           "connectionCollections": [], "oldPageNumber": 1, "imageLibrary": [], "imageLibraryCollections": []}
    with open(args.out, "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    print(f"Wrote {args.out} ({len(BUTTONS)} buttons calling {base})")


if __name__ == "__main__":
    main()
