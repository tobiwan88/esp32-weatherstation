# Source me: puts kicad-cli on PATH and points to KiCad's Python and libraries (macOS app, or Linux packages).
_mac=/Applications/KiCad/KiCad.app/Contents
if [ -d "$_mac" ]; then
    export PATH="$_mac/MacOS:$PATH"
    export KICAD_PYTHON="$_mac/Frameworks/Python.framework/Versions/Current/bin/python3"
    export KICAD_SYMBOL_DIR="$_mac/SharedSupport/symbols"
    export KICAD_FOOTPRINT_DIR="$_mac/SharedSupport/footprints"
else
    export KICAD_PYTHON="$(command -v python3)"   # Linux: apt kicad ships pcbnew for the system python3
    export KICAD_SYMBOL_DIR="/usr/share/kicad/symbols"
    export KICAD_FOOTPRINT_DIR="/usr/share/kicad/footprints"
fi
unset _mac
