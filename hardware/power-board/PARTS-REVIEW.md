# Power board: parts and circuit review, 2026-11-21

Scope: the split itself (J10 contract, what changes when the power board is alone or paired with other boards). The
circuit inside the board is unchanged from weatherstation-v1; its earlier findings and fixes are in
`../weatherstation-v1/PARTS-REVIEW.md` (A1-A7 fixed, B1-B8 status there). Nothing below is applied yet: each fix is a
decision for the engineer (topology unchanged in phase A).

## A: probably wrong
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| A1 | Header: CHG_CE | CE has no pull on this board: the pull-up R20 moved to the main board with the +3V3 rail. Power board alone (bench, cell plugged, panel or USB on), or with a bought host that lacks the pull-up: CE floats, and with the POR VREG of 4.2 V the cell (LFP, 3.75 V maximum) can be overcharged until HY2112 trips at 3.75 V. | Add a local CE pull-up that keeps charge off: e.g. 1 M to BAT_PACK (cell voltage, below 3.6 V for LFP; weak enough that the main board's 100k to +3V3 and the ESP32 GPIO win) or a 100k/200k divider from REGN (about 3.3 V). Not REGN directly (5 V on the ESP32 pin). One extra 0402 Basic resistor. | BQ25798 SLUSDV2C 6.5 VIH_CE 1.3 V, 7.3 "CE must be pulled HIGH or LOW, do not leave floating"; TI BQ25798EVM user guide SLUUCB5E jumper JP17 (CE pulled up on the charger board, jumper to GND enables charging) |

## B: works, margin or rule broken
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| B1 | Header: SYS pins | With the main board unplugged SYS is live at cell voltage on two bare pins; a dropped power board can short SYS to GND (BQ25798 SYS short protection limits, the cell side is protected by HY2112 short detection 0.55-1.15 V across M60/M61, 200-400 us). | Socket (female) on the power board side if it is the board that is handled alone; document in the bring-up notes. | BQ25798 7.3.13.1.5; HY2112 DS-HY2112-V08 9.1/9.2 |
| B2 | Header: misplug | A rotated cable (pin 1 to 18) puts SYS on CHG_CE/CHG_INT of the main board (ESP32 3.6 V abs max) and USB_VBUS on CHG_SDA/SCL. | Stacked boards: rotation impossible by mechanics. Cable: keyed/shrouded 2x9 (Extended or hand-soldered). | ESP32-S3-WROOM-1 v1.8 6.1 |
| B3 | Charger: HVDCP | USB_VBUS now leaves this board to the main board's USBLC6 U4 (VBR 6 V minimum). An enabled HVDCP handshake would raise VBUS to 9/12 V. | Firmware rule: EN_HVDCP stays 0 (POR default). Note in the firmware design. | BQ25798 7.3.4.5.2; USBLC6-2 DS4260 Rev 7 |
| B4 | Energy budget | With the system inputs (5 W panel, 15 min cycle, 90 s PM window) the worst-month yield is 2.10 Wh/day for 1.70 Wh/day: 1.24x, below the 1.5x target; REQUIREMENTS-system.md says about 2x (that holds at a 30 min cycle). | Confirm the cycle (30 min in winter) or the panel; power_budget.py WARN row. | `calc/power_budget.py hardware/power-board` |

## C: cleanup
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| C1 | Header: J10 | No LCSC part (hand-soldered), so its cost is outside the PCBA estimate. | Buy 2x9 2.54 mm headers/sockets with the cells. | board.yaml fab |
| C2 | AO3400A in the ACFET/RBFET pairs | ACDRV gate voltage vs VGS +/-12 V not entered in the card. | Read BQ25798 7.3.5.1 ACDRV level, tick the AO3400A card. | parts/AO3400A.yaml |

## Checked and fine
- No back-feed from VBUS/PV to the USB_VBUS pins with the main board unplugged: RBFET1 M2 blocks (BQ25798 figure 8-2, 7.3.5.3).
- USB_VBUS has its 0.1 uF C1 at the ACFET1 drain on this board; VBUS 2x10 uF + 0.1 uF unchanged (table 5-1, 6.3 CVBUS 2 uF).
- D+/D- reach the BQ25798 over J10 (ARCHITECTURE.md b); abs max 6 V on D+/D-, the lines carry 3.3 V USB signalling.
- HY2112 R60/C60/R61 inside the section 10 ranges; AO3400A VGS(th) 1.45 V max below VDL 2.10 V (section 10 note *4).
