#!/usr/bin/env bash
# Routed-board checks of this project: the power board's charger rows (they include emi_check with its known: waivers) and
# the main board's EMI rows. Both boards are routed; add a board here when it gets copper.
PY=${PYTHON:-python3}
rc=0
echo "-- power-board routed checks"
$PY hardware/calc/power_route_check.py hardware/power-board | tail -1 || rc=1
echo "-- main-board EMI"
$PY hardware/calc/emi_check.py hardware/main-board | tail -1 || rc=1
exit $rc
