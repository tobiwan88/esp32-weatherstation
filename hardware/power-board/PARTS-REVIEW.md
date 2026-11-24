# Power board: parts and circuit review, 2026-11-21

Scope: the split itself (J10 contract, what changes when the power board is alone or paired with other boards). The
circuit inside the board is unchanged from weatherstation-v1; its earlier findings and fixes are in
`../weatherstation-v1/PARTS-REVIEW.md` (A1-A7 fixed, B1-B8 status there). Status 2026-11-24: A1, B2, B4 and B5 (R23 330k) are done
(marked in their rows) and A6 is done (section "Changes from the independent review"); B1, B3, the B5 follow-up
(released-GPIO voltage) and the C items are open or firmware rules. Each open fix is a decision for the engineer.

## A: probably wrong
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| A1 (**done 2026-11-21**: R23 1M CE to BAT_PACK, C26083 Basic; 330k C25778 since 2026-11-24, B5; ARCHITECTURE.md d) | Header: CHG_CE | CE has no pull on this board: the pull-up R20 moved to the main board with the +3V3 rail. Power board alone (bench, cell plugged, panel or USB on), or with a bought host that lacks the pull-up: CE floats, and with the POR VREG of 4.2 V the cell (LFP, 3.75 V maximum) can be overcharged until HY2112 trips at 3.75 V. | Add a local CE pull-up that keeps charge off: e.g. 1 M to BAT_PACK (cell voltage, below 3.6 V for LFP; weak enough that the main board's 100k to +3V3 and the ESP32 GPIO win) or a 100k/200k divider from REGN (about 3.3 V). Not REGN directly (5 V on the ESP32 pin). One extra 0402 Basic resistor. | BQ25798 SLUSDV2C 6.5 VIH_CE 1.3 V, 7.3 "CE must be pulled HIGH or LOW, do not leave floating"; TI BQ25798EVM user guide SLUUCB5E jumper JP17 (CE pulled up on the charger board, jumper to GND enables charging) |

## B: works, margin or rule broken
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| B1 | Header: SYS pins | With the main board unplugged SYS is live at cell voltage on two bare pins; a dropped power board can short SYS to GND (BQ25798 SYS short protection limits, the cell side is protected by HY2112 short detection 0.55-1.15 V across M60/M61, 200-400 us). | Socket (female) on the power board side if it is the board that is handled alone; document in the bring-up notes. | BQ25798 7.3.13.1.5; HY2112 DS-HY2112-V08 9.1/9.2 |
| B2 | Header: misplug | A rotated cable (pin 1 to 18) puts SYS on CHG_CE/CHG_INT of the main board (ESP32 3.6 V abs max) and USB_VBUS on CHG_SDA/SCL. | **Done 2026-11-21 (engineer decision, review A2):** keyed 2x10, pin 3 removed and its socket hole blocked, asymmetric mounting holes; `tools/header_check.py` proves every rotation, mirror and column offset blocked and the row offsets power-safe. The earlier claim that stacking prevents rotation was wrong. | ESP32-S3-WROOM-1 v1.8 6.1; ARCHITECTURE.md J10 |
| B3 | Charger: HVDCP | USB_VBUS now leaves this board to the main board's USBLC6 U4 (VBR 6 V minimum). An enabled HVDCP handshake would raise VBUS to 9/12 V. | Firmware rule: EN_HVDCP stays 0 (POR default). Note in the firmware design. | BQ25798 7.3.4.5.2; USBLC6-2 DS4260 Rev 7 |
| B5 (**DECIDED 2026-11-24 by the engineer: option 2, R23 330k (C25778)**; review follow-up B2 2026-11-21) | Header: CHG_CE with both boards mated and +3V3 dead | Before: R20 1M (main board, to +3V3) and R23 1M (here, to BAT_PACK) formed a divider when +3V3 is dead (ESP32 unpowered): CE = BAT/2, below VIH_CE 1.3 V for BAT under 2.6 V (3.6 V with the 1 uA maximum CE leakage through 500k); CE undefined, the charger could charge from its POR registers (VREG 4.2 V) until the firmware runs or HY2112 stops at 3.75 V. **Now (R23 330k, `calc/ce_pullup.py`):** +3V3 dead: CE = 0.752 x BAT, high above BAT 1.73 V, 2.06 V with 1 uA leakage through 248k (HY2112 floor 2.10 V: defined over the whole range). Power board alone: high above BAT 1.63 V with leakage. Both boards, +3V3 up, GPIO released: CE 2.15-3.59 V over BAT 2.1-3.685 V, 3.64 V at the HY2112 trip 3.75 V (**new margin item**: at or above the 3.6 V ESP32 module abs max, VDD33 table 6-1; the GPIO pin limit is not in the module card; open-circuit value, the pad clamp takes at most about 1.4 uA). CE held low in sleep: 9.70 uA (BAT 3.2 V, 11.2 uA at 3.685 V) instead of 3.2 uA; sleep sum 74.7 uA typ / 85.1 uA max (was 68.2 / 78.6), average 11.8 mA, autonomy 11.1 days, solar margin 2.33x (`calc/power_budget.py`). Not covered by the arithmetic: the unpowered ESP32 pad's ESD diode to the dead +3V3 rail can hold CE near that rail + one diode drop; measure CE with +3V3 off at bring-up. | Applied: R23 330k 0402 C25778 (UNI-ROYAL 0402WGF3303TCE, JLC Extended **preferred**, stock 683638, USD 0.0013, `tools/jlcparts.py` 2026-11-24: `bom_check.py --stock` charges no loading fee for it, the offline count shows 8 Extended); same footprint, board value-only update (`tools/sync_from_netlist.py`), routing unchanged. Open (engineer): the released-GPIO voltage at a full cell. Options: (a) firmware drives IO9 high as an output while awake (CE 3.3 V, 1.2 uA from the cell), no hardware change, FIRMWARE-RULES.md 2; (b) R20 to 470k (C25790, preferred Extended) lowers the top to 3.53 V but breaks the +3V3-dead case again (CE = 0.588 x BAT, high only above 2.54 V with leakage) and adds 3.7 uA on +3V3: not recommended (`calc/ce_pullup.py` with r_host 470k); (c) accept (injection about 1.4 uA). Rejected: R20 DNP with the power board; accept B2. | BQ25798 SLUSDV2C 6.5 (VIH_CE 1.3 V, CE leakage 1 uA max); ESP32-S3-WROOM-1 6.1; numbers: `calc/ce_pullup.py hardware/power-board` |
| B4 | Energy budget | With the system inputs (5 W panel, 15 min cycle, 90 s PM window) the worst-month yield is 2.10 Wh/day for 1.70 Wh/day: 1.24x, below the 1.5x target; REQUIREMENTS-system.md says about 2x (that holds at a 30 min cycle). | **Done 2026-11-21:** cycle 30 min (15 min only with USB or sun), `autonomy_days_min: 7` as a FAIL threshold and a sleep-current sum in power_budget.py: 11.1 days, 2.33x. | `calc/power_budget.py hardware/power-board` |

## C: cleanup
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| C1 | Header: J10 | No LCSC part (hand-soldered), so its cost is outside the PCBA estimate. | Buy 2x10 2.54 mm male headers and 2x10 sockets with the cells (pull pin 3, block socket hole 3). | board.yaml fab |
| C2 | AO3400A in the ACFET/RBFET pairs | ACDRV gate voltage vs VGS +/-12 V not entered in the card. | Read BQ25798 7.3.5.1 ACDRV level, tick the AO3400A card. | parts/AO3400A.yaml |

## Checked and fine
- No back-feed from VBUS/PV to the USB_VBUS pins with the main board unplugged: RBFET1 M2 blocks (BQ25798 figure 8-2, 7.3.5.3).
- USB_VBUS has its 0.1 uF C1 at the ACFET1 drain on this board; VBUS 2x10 uF + 0.1 uF unchanged (table 5-1, 6.3 CVBUS 2 uF).
- D+/D- reach the BQ25798 over J10 (ARCHITECTURE.md b); abs max 6 V on D+/D-, the lines carry 3.3 V USB signalling.
- HY2112 R60/C60/R61 inside the section 10 ranges; AO3400A VGS(th) 1.45 V max below VDL 2.10 V (section 10 note *4).

## Changes from the independent review (2026-11-21, `../REVIEW-2026-11-21.md`)
| Review # | Change |
|---|---|
| A1 | R23 1M CE pull-up to BAT_PACK (C26083 Basic); 2026-11-24: 330k (C25778, preferred Extended), B5 |
| A6 | D1 drawn with a unidirectional symbol (Device:D_Zener: pin 1 K on PV_RAW, pin 2 A); netlist unchanged |
| B7 | Bring-up note: HY2112 may start with discharge off when the cell is first inserted (HY2112 datasheet 11.1 as cited by the review; not re-read here, UNVERIFIED). If SYS stays dead with a good cell, connect USB or PV once: the charger voltage releases the protection. No test pads added (CS/VSS are reachable on U6) |
| B19/B20 | Polarity in the connector values ("PV IN 1+ 2-", "CELL 1+ 2-") and on the silkscreen (BOARD.md layout rules) |
| C | C5 REGN 4.7 uF 0603 10 V (C19666) -> 0805 25 V (C1779 Basic); TP3 on QON; 5 W panel values in board.yaml (assumption until the panel is bought); title-block date per board |

### Incoming inspection and bring-up (review C, not changed in the design)
- L3 (EMTEK CMC): the datasheet's pin numbering conflicts between drawing and schematic: ohmmeter check of the two windings (1-2 and 4-3) before assembly.
- J10 socket: hole 3 must be blocked (plastic plug or a cut pin glued in) before the boards are first mated (`tools/header_check.py`).

## Open decisions after the review (2026-11-21, for the engineer)
| Review # | Decision | Numbers / options |
|---|---|---|
| B5 | ICHG vs the HY2112 charge-overcurrent trip: at a hot cell the trip can be about 1.48 A (AO3400A 48 mOhm x 1.2 per FET) | **Decided 2026-11-21: ICHG stays 1.5 A** (cell allows 0.5C-2C); measure the trip and FET temperature on the first board. `calc/power_budget.py` checks 1.5 A at 25 C (board.yaml) |
| Cost | Order at qty 5: USD 55.03 before the bare PCB, joints and shipping: parts 23.83 (4.77 per board) + 7 Extended x 3.07 + setup 8.18 + stencil 1.53 (`calc/bom_check.py --stock --qty 5`) | no action needed |
