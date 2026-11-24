#!/usr/bin/env bash
# Status LED current and brightness on the main board (D10/D11 side-view red behind R34/R35 1k on IO41/IO42):
# numbers from hardware/calc/led_current.py (inputs: main-board/board.yaml design.leds).
PY=${PYTHON:-python3}
$PY hardware/calc/led_current.py --selftest || exit 1
$PY hardware/calc/led_current.py hardware/main-board | tail -1
