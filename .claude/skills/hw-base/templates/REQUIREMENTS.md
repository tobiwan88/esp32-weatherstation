# Requirements: <project>   (version, date, accepted by <engineer> on <date>)

Each requirement: number, statement, source (engineer's words with date, datasheet section, or `assumption`), check
(script row or `(review)`). Evidence level for researched facts: page / snippet / estimate.

## 1 Purpose and environment
R1.1 <who uses the data, where it goes; own use first>            source: <engineer, date>          check: (review)
R1.2 <site, temperature range, exposure (outdoor, rain, sun), lifetime>

## 2 Cost model
R2.1 Cost cap per assembly order: <USD>, quantity per order: <n>; whole project: <USD>      check: calc/bom_check.py
R2.2 Cost per finished unit including off-board modules, cell, panel, enclosure: <USD>        check: BOARD.md cost table
R2.3 Fee table used (fab, date): loading fee per unique Extended part, setup, stencil. Hand-soldering allowed: <yes/no/fallback>

## 3 Power cycle and autonomy
| Load | Warm-up | Min on-time | Sampling needed | Current | Fits deep sleep? |
|---|---|---|---|---|---|
R3.1 Default cycle <min>, fast mode <min> and its trigger                                  check: calc/power_budget.py
R3.2 Autonomy >= <days> from <fraction> of the cell; solar margin >= <x> in the worst month (<site, irradiance source>)   check: FAIL threshold
R3.3 Sleep current of the whole stack < <uA>                                                check: power_budget sleep sum
R3.4 Cell: chemistry, temperature window for charge and discharge, protection thresholds

## 4 Sensors, ports and expansion
<priority by information per cost; standard connector family and pinout per port; supply pin for every port class>

## 5 Boards and interfaces
<one board or split, why, cost delta; header pin table lives in ARCHITECTURE.md; stack or side by side>
Pins reserved before the pin map: deep-sleep pins, strapping pins, native USB, boot/reset.

## 6 Fab limits
Layers <n>, outline <= <w x h> mm, tier, finish, assembly side, hand-soldered parts.

## 7 Firmware hand-off
Rules the hardware depends on go to FIRMWARE-RULES.md.

## 8 Open items
| # | Item | Owner | Needed by |
