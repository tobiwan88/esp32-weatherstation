#!/usr/bin/env bash
# Charger CE pull-ups across the board split (power-board R23 to BAT_PACK, main-board R20 to +3V3, GPIO IO9):
# the cases of ARCHITECTURE.md d, numbers from hardware/calc/ce_pullup.py (inputs: power-board/board.yaml design.ce_pullup).
PY=${PYTHON:-python3}
$PY hardware/calc/ce_pullup.py --selftest || exit 1
$PY hardware/calc/ce_pullup.py hardware/power-board | tail -1
