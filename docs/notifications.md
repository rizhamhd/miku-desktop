# Notification adapters

Miku reads visible popup geometry, not notification titles or bodies. It never
claims the notification D-Bus service and doesn't change your notification daemon.

## Layer surfaces (Mako, Dunst, compact SwayNC)

`hyprctl -j layers` reports surface rectangles. Miku recognizes the exact namespaces
listed in `notificationNamespaces`. A matching surface is treated as one perch,
even if the daemon draws several messages inside it. One automatic jump happens
per surface appearance; replacing text in an existing surface is not a new arrival.

Surfaces covering most of the monitor are ignored: their rectangle is not the
notification's rectangle. This includes SwayNC's default full-screen popup canvas.
SwayNC can use `"layer-shell-cover-screen": false` for compact surfaces, but renderer
versions and CSS can still affect the result. Verify with `miku-desktop doctor`.

Miku needs 128 logical pixels **above** the popup. Bottom-corner placement usually
works best. For Mako, `anchor=bottom-right` is useful. For Dunst,
`origin = bottom-right` is useful. Miku does not rewrite these settings for you.
Margins and shadows may make the visible card slightly smaller than its surface.

## Midnight Shell

The installer attempts to add the bundled bridge when a compatible Midnight layout
is detected. You can also run:

```bash
miku-desktop bridge midnight install
# Restart Midnight Shell after installing the bridge.
```

The adapter adds a read-only Quickshell IPC endpoint named
`miku-notifications-MONITOR` with a `snapshot` method. It returns screen-local
rectangles for visible individual notification cards, including animation/clipping.

Only two notification QML files change. The original files are backed up under
`$XDG_STATE_HOME/miku-desktop/`. If the shell exists only in `/etc/xdg`, the bridge
creates a user override in `$XDG_CONFIG_HOME/quickshell/caelestia`. That override
will take precedence over future packaged shell updates. Remove/reinstall the
bridge when updating the shell so you can rebase on the new package.

An already customized legacy Miku shell is also recognized through its read-only
`miku-MONITOR status` endpoint. Turn off its built-in pet to avoid two companions
only after the dedicated notification bridge is active.

To remove: `miku-desktop bridge midnight remove`, then restart Midnight. If a bridge
file has changed since installation, removal stops without overwriting it and points
to the backup. This adapter is optional; an incompatible version does not prevent
the standalone pet from running.

## Any other shell: geometry bridge

Set an executable argument array in `config.json`:

```json
{"notificationBridgeCommand": ["/absolute/path/to/my-popup-geometry", "{monitor}"]}
```

The command must return a JSON array within 400 ms. It is called periodically,
with `{monitor}` replaced by the output name. It is executed directly, without a shell.
Return `[]` when there are no visible popups. Example output:

```json
[
  {"id":"message-42", "left":1450, "right":1880, "top":850, "bottom":1000}
]
```

Coordinates are **logical pixels relative to that monitor**, not global desktop or
physical pixel coordinates. IDs must be stable while a popup is visible and unique
for new arrivals. A disappearing ID releases its perch; moving rectangles carry
the pet along. Values outside the monitor are clipped; malformed rectangles are ignored.

Noctalia and DMS are not required by the pet, but their full-screen notification
canvases currently need this bridge for exact automatic perching. Contributions
adding maintained adapters are welcome.

## References

- [Freedesktop notification specification](https://specifications.freedesktop.org/notification/latest-single/)
- [Hyprland IPC source](https://github.com/hyprwm/Hyprland/tree/main/src/ipc/s1)
- [SwayNC configuration schema](https://github.com/ErikReider/SwayNotificationCenter/blob/main/src/configSchema.json)
- [Mako configuration](https://github.com/emersion/mako/blob/master/doc/mako.5.scd)
- [Dunst configuration](https://github.com/dunst-project/dunst/blob/master/dunstrc)
