"""Route a board with Freerouting on F.Cu/B.Cu only (run with $KICAD_PYTHON).

board -> Specctra DSN (pcbnew; kicad-cli 10 has no DSN export) -> inner layers marked as planes (they stay solid GND,
REQUIREMENTS E2) -> Freerouting 2.5 headless -> SES -> board. Locked copper (hand-drawn blocks, KRT plane vias) goes into
the DSN as protected wiring, so Freerouting routes around it and never moves it.
Usage: route_fr.py in.kicad_pcb out.kicad_pcb [max_passes]   (env JAVA, FREEROUTING_JAR override the defaults)
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pcbnew

src, out = sys.argv[1], sys.argv[2]
passes = sys.argv[3] if len(sys.argv) > 3 else "100"
here = Path(__file__).resolve().parent.parent
java = os.environ.get("JAVA", "/opt/homebrew/opt/openjdk/bin/java")
jar = os.environ.get("FREEROUTING_JAR", str(here / ".tools" / "freerouting-2.5.0" / "freerouting-2.5.0.jar"))
base = os.path.splitext(out)[0]
dsn, ses, log = base + ".dsn", base + ".ses", base + ".freerouting.log"

board = pcbnew.LoadBoard(src)
if not pcbnew.ExportSpecctraDSN(board, dsn):
    sys.exit("DSN export failed")
text = Path(dsn).read_text()
# inner copper = GND planes: no signal routing there (Freerouting only routes on layers of type signal)
text, n = re.subn(r"\(layer (In[12]\.Cu)\s*\(type signal\)", r"(layer \1 (type power)", text)
if n != 2:
    sys.exit(f"expected 2 inner signal layers in the DSN, patched {n}")
Path(dsn).write_text(text)
run = subprocess.run([java, "-jar", jar, "-de", dsn, "-do", ses, "-mp", passes, "--gui.enabled=false"],
                     capture_output=True, text=True, timeout=3600)
Path(log).write_text(run.stdout + run.stderr)
if run.returncode != 0 or not os.path.exists(ses):
    sys.exit(f"freerouting failed ({run.returncode}), see {log}")
if not pcbnew.ImportSpecctraSES(board, ses):
    sys.exit("SES import failed")
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(out)
print(f"routed {out}: {len(board.GetTracks())} track/via items")
