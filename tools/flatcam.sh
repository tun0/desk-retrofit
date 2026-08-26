#!/bin/sh
# Launcher for the FlatCAM Evo install set up for this project's PCB milling
# (see conversation - svgtrace/playwright's Image Import feature is
# deliberately dropped, it pulls in a greenlet version with no cp314 wheel;
# FlatCAM's own code already handles that plugin failing to load gracefully).
cd "$(dirname "$0")/flatcam" || exit 1
. ../flatcam-env/bin/activate
exec python flatcam.py "$@"
