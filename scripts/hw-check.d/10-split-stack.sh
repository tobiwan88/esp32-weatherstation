#!/usr/bin/env bash
# Project checks between boards (three-board split): the split keeps every part and net, header pins, stack fit.
PY=${PYTHON:-python3}
rc=0
echo "-- split"
$PY -I hardware/tools/split_check.py | tail -1 || rc=1
echo "-- header"
$PY -I hardware/tools/header_check.py --selftest >/dev/null && $PY -I hardware/tools/header_check.py | tail -2 || rc=1
echo "-- stack"
$PY -I hardware/tools/stack_check.py --selftest >/dev/null && $PY -I hardware/tools/stack_check.py | tail -1 || rc=1
exit $rc
