# Miku Desktop

A small Hatsune Miku companion for **Hyprland on Arch-based Linux**, independent of your desktop shell.

![Tests](https://github.com/rizhamhd/miku-desktop/actions/workflows/test.yml/badge.svg)
![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)

<img src="https://raw.githubusercontent.com/lars-rooij/webmeji/1300e8dd8a12daa646ef272d271fbe8bd25b6748/miku/shime1.png" width="128" alt="Hatsune Miku desktop sprite">

Miku walks and rests on the desktop, behind your apps. Drag and throw her around,
place her on a window edge, or let her jump onto an arriving notification. She
returns to the desktop when her perch disappears.

## Install

Run these commands **inside your Hyprland session**, as your normal user:

```bash
sudo pacman -S --needed git
git clone https://github.com/rizhamhd/miku-desktop.git
cd miku-desktop
./install.sh
```

The installer installs missing Python/Quickshell dependencies, downloads a pinned
Miku sprite pack, installs into your user account, adds a managed autostart stanza
to your Hyprland config, and starts Miku. Existing `quickshell-git` installations
are used as-is. It does not install a desktop shell or replace your notification daemon.

Requires **Hyprland, Quickshell 0.3.1+, and Python 3.10+**. Works with Waybar, Midnight,
Noctalia, DankMaterialShell, other shells, or no shell for desktop/window behavior.
This is not a GNOME, KDE/KWin, Sway, or X11 app.

### Notifications: read this once

**Automatic notification perching depends on your notification renderer.**

| Renderer | Notification support |
| --- | --- |
| Mako / Dunst under Wayland | Uses the notification surface's outer edge; needs 128 px of space above it. |
| SwayNC | Compact popup surfaces only; full-screen popup surfaces need a bridge. |
| Midnight Shell | Included optional bridge reports individual cards; the installer attempts to add it with backups. Restart Midnight once if the bridge was newly installed. |
| Noctalia / DMS / other full-screen shells | Desktop and window behavior works. Exact notification perching requires a custom geometry bridge. |

The notification protocol does not expose popup rectangles. Miku therefore cannot
promise notification perching on every shell without an adapter. It never steals
the `org.freedesktop.Notifications` service. See [notification setup](docs/notifications.md).

## Controls

| Action | Behavior |
| --- | --- |
| Drag and release | Drop or throw Miku; she bounces and lands on visible edges. |
| Right-click | Hop onto an available window or notification. |
| Left-click | Eat; click again to sleep. |
| New supported notification | Hop onto it once, after its entrance animation. |
| Window or notification closes | Fall to the desktop and go behind apps again. |

Ordinary windows never cause automatic hops. Window tops need 128 logical pixels
of headroom; internal browser tabs are not separate surfaces. Covered window edges
and windows on inactive workspaces are ignored. Only Miku's small input region
accepts clicks; the surrounding desktop remains usable.

## Commands

```bash
~/.local/bin/miku-desktop status
~/.local/bin/miku-desktop doctor
~/.local/bin/miku-desktop stop
~/.local/bin/miku-desktop start
~/.local/bin/miku-desktop perch
~/.local/bin/miku-desktop home
```

`perch` and `home` accept `--screen DP-1`. If `~/.local/bin` is on your PATH, omit
the directory. Both classic `hyprland.conf` and Lua `hyprland.lua` autostart are supported.
A custom Hyprland config can be selected with `./install.sh --hyprland-config /path/to/config`.

## Configuration

Edit `~/.config/miku-desktop/config.json`, then stop and start Miku:

```json
{
  "autoNotificationHop": true,
  "notificationDelayMs": 600,
  "pollIntervalMs": 150,
  "excludedScreens": [],
  "spritePath": "",
  "midnightBridge": true,
  "notificationNamespaces": ["notifications", "mako", "dunst", "swaync-notification-window"],
  "notificationBridgeCommand": []
}
```

An empty `spritePath` uses the downloaded Miku pack. Custom packs need transparent
128×128 PNGs named `shime1.png` through `shime46.png`. XDG config/data/state paths
are respected. The installer supports `--no-start`, `--no-autostart`, and
`--no-midnight-bridge`.

## Update and uninstall

```bash
cd miku-desktop
git pull --ff-only
./install.sh

# Remove the user installation and its managed autostart entry:
~/.local/bin/miku-desktop uninstall
```

Settings, downloaded sprites, and backups are retained. Uninstall removes the
managed Midnight bridge if its files are unchanged; later edits are preserved and
require manual reconciliation. Shell restarts are needed after bridge removal.
For an alternative pacman-managed installation, see [Arch packaging](docs/packaging.md).

## Development

```bash
python -m unittest discover -s tests -v
node tests/physics.test.cjs
./bin/miku-desktop run
```

Node is only needed for development tests. Runtime uses Python's standard library,
Quickshell/Qt, and Hyprland IPC. Live desktop checks are described in
[testing](docs/testing.md). CI verifies geometry, collision behavior, settings,
notification adapters, and reversible installation logic; graphical integration
is also tested manually on Hyprland. Other distro/renderer combinations need testing.

Code: GPL-3.0-only. Sprites: downloaded from Webmeji at a pinned revision;
see [attribution](NOTICE.md). This is an unofficial fan project.
