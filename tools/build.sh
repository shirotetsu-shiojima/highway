#!/bin/sh
# sb3 から web/data を再生成する。使い方: sh tools/build.sh path/to/project.sb3
set -e
SB3="$1"; HERE="$(cd "$(dirname "$0")" && pwd)"; TMP="$(mktemp -d)"
unzip -q -o "$SB3" -d "$TMP"
python3 -I "$HERE/extract.py" "$TMP" "$TMP/network_raw.json"
python3 -I "$HERE/facilities.py" "$TMP/network_raw.json" "$TMP/fac.json"
python3 "$HERE/build_geojson.py" "$TMP/network_raw.json" "$TMP/fac.json" "$HERE/../data" "$TMP"
rm -rf "$TMP"
