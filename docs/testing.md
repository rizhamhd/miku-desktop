# Testing

Headless tests (no graphical session or downloads needed):

```bash
python -m unittest discover -s tests -v
node tests/physics.test.cjs
```

Opt-in graphical smoke test, from Hyprland with `zenity` installed:

```bash
python tests/live_smoke.py --sprites /path/to/hatsune-miku
```

It starts the standalone application with Midnight integration disabled, creates a
real Wayland popup surface, verifies the automatic hop and return to the desktop
layer, then verifies a real window perch. Its temporary window, popup, config, and
pet process are cleaned up. Do not run it while another copy of this same checkout's
pet is active: the test owns that instance. Existing desktop-shell pets are untouched.

The renderer-independent layer adapter is tested with a controlled notification
surface; Mako, Dunst, SwayNC, and every shell version have not all been manually
certified. Their popup-surface requirements are documented rather than assumed.
Multi-monitor coordinate conversion, occlusion, settings validation, adapter
fallback, and installer backup/restore paths are covered by the headless tests.

An additional real lifecycle test installs and updates the program in temporary
XDG directories, runs its doctor/status commands, then uninstalls it and checks
that the temporary Hyprland config is restored:

```bash
python tests/integration_install.py --archive /path/to/the-pinned-webmeji.zip
```

It requires the exact archive specified by `assets.json` and a live Hyprland
session. It does not edit your real Hyprland config or replace your shell.
