"""XDG paths and validated, user-editable settings."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {
    "spritePath": "",
    "autoNotificationHop": True,
    "notificationDelayMs": 600,
    "pollIntervalMs": 150,
    "excludedScreens": [],
    "notificationNamespaces": ["notifications", "mako", "dunst", "swaync-notification-window"],
    "notificationBridgeCommand": [],
    "midnightBridge": True,
}

def xdg(kind):
    defaults = {"config": ".config", "data": ".local/share", "state": ".local/state"}
    return Path(os.environ.get("XDG_" + kind.upper() + "_HOME", Path.home() / defaults[kind]))

def config_path(): return xdg("config") / "miku-desktop/config.json"
def sprite_path(): return xdg("data") / "miku-desktop-sprites/hatsune-miku"

def load():
    path = config_path()
    user = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(user, dict): raise ValueError("Config must be a JSON object")
    cfg = dict(DEFAULTS, **user)
    for key in ("autoNotificationHop", "midnightBridge"):
        if not isinstance(cfg[key], bool): raise ValueError(f"{key} must be true or false")
    for key in ("excludedScreens", "notificationNamespaces", "notificationBridgeCommand"):
        if not isinstance(cfg[key], list) or not all(isinstance(x,str) for x in cfg[key]):
            raise ValueError(f"{key} must be a list of strings")
    for key,low,high in (("pollIntervalMs",75,2000),("notificationDelayMs",0,5000)):
        if type(cfg[key]) is not int or not low <= cfg[key] <= high:
            raise ValueError(f"{key} must be between {low} and {high}")
    if not isinstance(cfg['spritePath'],str): raise ValueError('spritePath must be a path string')
    cfg["spritePath"] = str(Path(cfg["spritePath"]).expanduser() if cfg["spritePath"] else sprite_path()) + "/"
    return cfg

def write_default():
    path=config_path()
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(DEFAULTS,indent=2)+"\n")
