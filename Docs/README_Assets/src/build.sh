#!/bin/zsh
# Rebuilds Veil's README plates: HTML rendered by Google Chrome through Playwright (pip install playwright;
# it drives the installed Chrome). No server, no GPU. Writes docs/README_Assets/{executor,carriage,services,veil8-ingest,veil8-reverse,
# veil8-step,veil8-verdict,garde-sign,garde-wild}.png; name targets to rebuild only those (e.g. `build.sh veil8_step`).
set -euo pipefail
repo=${0:A:h:h:h:h}
cd "$repo"
python3 -I docs/README_Assets/src/plates.py docs/README_Assets "$@"
