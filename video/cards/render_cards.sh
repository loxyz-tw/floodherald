#!/bin/bash
# Render the video title cards to 1920x1080 PNG with headless Chrome (fonts from Google Fonts).
# Usage (from video/cards): ./render_cards.sh [GITHUB_URL]
set -e
cd "$(dirname "$0")"
url="${1:-github.com/loxyz-tw/floodherald}"
for name in opening arch scenario1 scenario2 closing; do
  src="$name.html"
  if [ "$name" = closing ]; then sed "s#GITHUB_URL#${url}#" closing.html > _closing.html; src=_closing.html; fi
  extra=""; [ "$name" = opening ] && extra="--default-background-color=00000000"
  google-chrome --headless=new --disable-gpu --hide-scrollbars $extra --virtual-time-budget=8000 \
    --window-size=1920,1080 --screenshot="$PWD/$name.png" "file://$PWD/$src" 2>/dev/null
  echo "$name.png"
done
rm -f _closing.html
