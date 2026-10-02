#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if (( EUID == 0 )); then
    echo 'Run ./install.sh as your desktop user; it uses sudo only for missing packages.' >&2
    exit 1
fi
miku_arch=false
[[ ! -f /etc/os-release ]] || source /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in *" arch "*) miku_arch=true ;; esac
[[ ! -f /etc/arch-release ]] || miku_arch=true
if [[ $miku_arch != true ]] || ! command -v pacman >/dev/null; then
    echo 'This installer targets Arch-based distributions. See README.md for manual setup.' >&2
    exit 1
fi
if [[ -z ${HYPRLAND_INSTANCE_SIGNATURE:-} || -z ${WAYLAND_DISPLAY:-} ]]; then
    echo 'Run this installer in a terminal inside Hyprland.' >&2
    exit 1
fi
missing=()
command -v python >/dev/null || missing+=(python)
command -v qs >/dev/null || missing+=(quickshell)
if ((${#missing[@]})); then
    echo "Installing dependencies: ${missing[*]}"
    sudo pacman -S --needed "${missing[@]}"
fi
exec python -m miku.install "$@"
