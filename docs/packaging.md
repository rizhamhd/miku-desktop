# Arch package

The recommended `./install.sh` handles dependency checks, user autostart and sprite
setup. A PKGBUILD is also provided for users who prefer pacman ownership:

```bash
cd packaging
makepkg -si
miku-desktop fetch-sprites
miku-desktop start
```

The PKGBUILD builds from this public Git repository. No AUR submission is implied.
Assets are downloaded in the user's session, never in a root package-install hook.
The package uses `/usr/share/miku-desktop` and `/usr/bin/miku-desktop` and does not
edit your desktop configuration. Add `miku-desktop start` to your Hyprland autostart
(classic `exec-once`, or `hl.on("hyprland.start", ...)` on Lua configurations).

Do not install both the package and the user installer: they have separate app
paths and could run two companions. Remove the user install before switching.
For package removal use `sudo pacman -R miku-desktop-git`; remove your own autostart
line and stop the pet first. The per-user `uninstall` command only manages installs
made by `install.sh`.
