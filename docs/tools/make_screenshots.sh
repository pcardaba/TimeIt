#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2024 Pablo Cardaba
#
# Regenerate the screenshots of the user guide (docs/screenshots/*.png).
#
# Everything runs on a private virtual X display (Xvfb) with its own window
# manager (xfwm4, "Default" theme) and its own session bus, so the desktop of
# the user is not touched and the result does not depend on its theme or
# scaling. TimeIt runs unscaled (TIMEIT_SCALE=1) with the theme of main.py.
#
# Requirements (Linux): Xvfb, xfwm4, dbus-run-session, xrdb, xsetroot,
# ImageMagick (import) and Python Pillow.
#
# Usage, from anywhere:
#   TimeIt/docs/tools/make_screenshots.sh            # every screenshot
#   TimeIt/docs/tools/make_screenshots.sh NAME...    # only these
#   TimeIt/docs/tools/make_screenshots.sh --list     # list the names
#   OUT=/some/dir TimeIt/docs/tools/make_screenshots.sh   # write elsewhere

set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
PARENT="$(dirname "$REPO")"
PKG="$(basename "$REPO")"
## A free display number (one Xvfb lock file per display in use).
N=77
while [ -e "/tmp/.X$N-lock" ]; do N=$((N + 1)); done
DISPLAY_NUM=":$N"
OUT="${OUT:-$REPO/docs/screenshots}"

if [ "$1" = "--inner" ]; then
    ## Inside the private session bus: window manager, then the shots.
    shift
    echo "Xft.dpi: 96" | xrdb -merge
    ## It ends with the X server (killed on exit of the outer script).
    xfwm4 --compositor=off >/dev/null 2>&1 &
    sleep 2
    xsetroot -solid white
    cd "$PARENT"
    status=0
    python3 -m "$PKG.docs.tools.screenshots" --out "$OUT" "$@" || status=$?
    exit $status
fi

if [ "$1" = "--list" ]; then
    cd "$PARENT" && exec python3 -m "$PKG.docs.tools.screenshots" --list
fi

CFG="$(mktemp -d)"
trap 'kill $XVFB 2>/dev/null || true; rm -rf "$CFG"' EXIT
## The window manager reads its theme from this private configuration.
mkdir -p "$CFG/xfce4/xfconf/xfce-perchannel-xml"
cat > "$CFG/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="Default"/>
    <property name="title_font" type="string" value="Sans Bold 9"/>
    <property name="use_compositing" type="bool" value="false"/>
  </property>
</channel>
EOF

Xvfb "$DISPLAY_NUM" -screen 0 1800x1200x24 -nolisten tcp >/dev/null 2>&1 &
XVFB=$!
sleep 1
DISPLAY="$DISPLAY_NUM" XDG_CONFIG_HOME="$CFG" TIMEIT_SCALE=1 \
    dbus-run-session -- "$0" --inner "$@" 2> >(grep -v -e dbus-daemon \
        -e fusermount -e SpiRegistry -e xfconfd -e "connection to the bus" >&2)
