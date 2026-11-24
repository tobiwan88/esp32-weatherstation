# Main board: parts and circuit review, 2026-11-21

Scope: the split (J10 contract, the board alone) and the phase B additions. Circuit carried over from weatherstation-v1
is reviewed in `../weatherstation-v1/PARTS-REVIEW.md`. Nothing below changes the topology silently: each fix is a decision.

## A: probably wrong
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| A1 (**2026-11-21:** USD 85.60 at qty 5 with U9 = BMP580, `calc/bom_check.py --stock --qty 5`; see the open list below) | Cost: PCBA order at qty 5 | After phase B the main-board order is about USD 96.95 before the bare 4-layer PCB, SMT joints and shipping: parts USD 11.92 per board (BMP585 alone USD 3.58) + setup 8.18 + stencil 1.53 + 9 Extended x 3.07. With the PCB it lands above the USD 100 limit. Phase A alone was USD 73.16. | Engineer decision, cheapest first: (1) BMP585 off the PCBA (DNP footprint, or keep it on the Qwiic add-on board): saves about USD 21 per order; (2) fewer boards per order is no help (fixed fees dominate); (3) check the cart quote first, the first-tier prices here are upper bounds. Keep the Ports layout either way. | `tools/jlcparts.py` prices 2026-11-21; fee table REQUIREMENTS-system.md 10.4 |

## B: works, margin or rule broken
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| B1 (**done 2026-11-21**: C35) | USB: USB_VBUS | USB_VBUS has no capacitor on this board: C1 0.1 uF moved to the power board with the ACFET pair. The USBLC6 U4 VBUS pin and the J1 contacts see the cable and the header inductance without local decoupling; ESD on VBUS returns through U4 only. | Add 100 nF (C307331, Basic, already on the BOM) at J1 VBUS; optionally 1-10 uF, but stay under the USB 10 uF inrush limit together with the power board's VBUS caps behind the ACFET (they are behind M1, so they do not count while M1 is off). | USB 2.0 spec 7.2.4.1 (10 uF max at attach); USBLC6-2 DS4260 application (VBUS cap at the pin) |
| B2 | Rails: SYS from J10 | U2 and U7 have their input caps (C40 10 uF, C44) but the SYS bulk (5x10 uF) is now on the other board, behind about 50-80 mm of header and trace when side-by-side. | Keep C40/C44 at the pins; if the boards go side by side with a cable, add 22 uF at J10 SYS. Decide with the mechanics (REQUIREMENTS-system.md 10.5). | TPS63802 SLVSEU9D 8.3 (effective CIN >= 4 uF) and 10.2.2 input capacitor selection |
| B3 | Header: CE and INT pull-ups | R20/R22/R54/R55 hang on +3V3 and are now the only pull-ups for the charger. Correct for this pair; a second host or a bought module with its own pull-ups adds in parallel. | None now; note in ARCHITECTURE.md (done). | BQ25798 7.3.11.2, 7.3.14 |
| B5 (applied in phase B, confirm) | Sensors: R50/R51 | 10k sensor-bus pull-ups with the outdoor SHT cable (2 m assumed, 100 pF/m) and up to 7 devices: Cb about 276 pF, rise time 2.3 us, over the 1 us standard-mode limit. | Changed to 2.2k (C25879 Basic): 514 ns; with one bought 2.2k module in parallel the low level sinks 2.64 mA (limit 3 mA). Rule: at most one external 2.2k pull-up pair on the bus; measure the cable capacitance. | NXP UM10204 rev 7 table 10, section 7.1; `calc/i2c_bus.py hardware/main-board` |
| B4 | USB: BC1.2 and enumeration | D+/D- stubs now run to the power board through J10; the BQ25798 drives D+/D- during detection (DCD, primary/secondary) while the ESP32 USB PHY is attached. Same coexistence as v1 B5, longer stubs. | Firmware: AUTO_INDET_EN = 0 after the first detection; keep the J10 to U3 stub short (stacked). | BQ25798 7.3.4.5.1 |

| B6 | Ports: pulse port debounce | The brief asked for 100 nF + series R on the pulse inputs. With a leakage-safe 1M pull-up, 100 nF gives a 139 ms release edge (about 3.6 Hz max, the anemometer reaches 42 Hz at 100 km/h). Chosen: 1k + 4.7 nF (C1538 Basic): 6.5 ms, 77 Hz; contact bounce beyond that is filtered in the ULP/firmware (dead time per edge). The vane input keeps 100 nF (slow analog). | Confirm the anemometer type and its maximum rate; firmware debounce of about 2 ms. | `calc/i2c_bus.py` pulse rows; ESP32-S3-WROOM-1 v1.8 table 6-3 (VIH 0.75 VDD) |

## C: cleanup
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| C1 | Header: bench supply | Main board alone needs SYS from a bench supply; above 5.5 V U2 and U7 leave their ratings (abs max 6 V / 7 V). | Bring-up note (ARCHITECTURE.md); a TVS on SYS is not needed with the power board. | TPS63802 8.1/8.3; TPS61023 6.1/6.3 |
| C2 | Dev jumper USB_VBUS -> SYS | With USB only the main board stays dark. A DNP 0 ohm or solder jumper USB_VBUS -> SYS would power it from USB on the bench (5 V is inside U2/U7 ranges) but must never be closed with a power board plugged (USB_VBUS straight onto SYS bypasses the charger). | Engineer decision; default: no jumper, bench supply. | ARCHITECTURE.md bring-up |
| C3 | Ports: U11 | The vane line uses one of the two USBLC6 lines; the second line (pins 3/4) is unused. Same part as U4/U5/U10, so no new Extended fee (about USD 0.16). | Alternative: a single-line ESD diode (new part, maybe Extended). Keep. | USBLC6-2 DS4260 Rev 7 |
| C4 | Ports: vane excitation | R74 10k from 3V3_SW: with a SEN-15901 class vane (688 ohm to 120k) the divider draws up to 0.31 mA while 3V3_SW is on and nothing in deep sleep. The ADC reading needs a per-direction table in firmware. | None. | vane network values from the SparkFun SEN-15901 datasheet (not in datasheets/, unverified) |
| C5 | Ports: GPIO choice | RAIN IO15 and WIND IO16 are RTC GPIOs (ULP counting, ext1 wake) and the 32 kHz crystal pins: no external 32 kHz crystal may be added later. VANE IO8 = ADC1_CH7 (ADC1 works with WiFi; ADC2 does not). Not strapping (0, 3, 45, 46), not USB (19, 20), free in v1. | Note in the firmware pin map. | ESP32-S3-WROOM-1 v1.8 3.2 pin description, 4 table 4-1 |

## Changes from the independent review (2026-11-21, `../REVIEW-2026-11-21.md`)
| Review # | Change | Numbers (script) |
|---|---|---|
| A3 | Q40 slowed: R76 10k (C25744) from the Q41 drain to the gate node, C48 22 nF X7R 0402 (C1532, Basic) gate to drain; Q40 drawn source up | `calc/rail_switch.py hardware/main-board`: ramp 0.28-0.42 ms, inrush 0.23-0.54 A (Vth and C spread), +3V3 dip about 27-64 mV (scaled from TPS63802 figure 10-22), final gate drive 3.02 V (Rds(on) specified at 2.5 V); old circuit: charge sharing pulled +3V3 to about 1.65 V |
| B1 | R20 100k -> 1M (C26083, already on the BOM): 3.3 uA with CE held low in deep sleep | `calc/power_budget.py hardware/power-board` sleep sum |
| B11 | R77 100 ohm 1206 (C17901, Basic) in the J3 supply (outdoor cable). **No Basic resettable fuse exists at JLCPCB** (searched 2026-11-21: SMD0805P020TF C20976, SMD0603P020TF C20785, ASMD0805-020 C135327, JK-SMD0805-020-30V C516070 and all others are Extended: +USD 3.07 per order plus about 0.03-0.12 per part). A PTC on J4/J11 (or on 3V3_SW as a whole) stays **OPEN** for the engineer: it would cost one more Extended type; a series resistor there would break a SEN0460 (up to 100 mA) on Qwiic | `calc/rail_switch.py` cable rows: short 33 mA, 110 mW of 250 mW; drop 200 mV at 2 mA |
| A7 | Sensor I2C note says 2.2k; GAS_SW/GAS_FB renamed BOOST_SW/BOOST_FB (the boost feeds the PMS7003 too; board.yaml net class updated, v1 keeps the old names); Q40 and TP1/TP2 drawn with the rails pointing up | |
| follow-up B1 | R78 22k 0402 (C25768, Basic) 3V3_SW to GND: the rail held about 3 V for about 30 s after Q40 turned off (no bleed), so a quick re-enable gave no sensor power-on reset; at cold start Q40 conducts weakly while +3V3 ramps (C48 holds the gate). FIRMWARE-RULES.md 4: wait 5 tau or soft-reset the sensors, scope 3V3_SW at first power-up | `calc/rail_switch.py`: tau 0.63-1.02 s, 5 tau 3.1-5.1 s; 151 uA only while the rail is on (`calc/power_budget.py hardware/power-board` rail-on loads: +183 uA at the cell for 90 s per cycle, average still 11.7 mA, sleep sum unchanged 68.2 uA) |
| B12 | C40 TPS63802 input 10 uF 0603 -> 22 uF 0805 (C45783, Basic, already on the BOM) | |
| B14 | C35 100 nF (C307331) on USB_VBUS at J1 | |
| B16 | U9 INT to GND (done with the BMP580 change, eae8360) | |
| C | C47 not fitted (fit with U8); J3 value text "SHT head cable (Qwiic)"; J7 value "pin 1 3V3 only"; C90/C91 0402 C307331 (eae8360) | |

## Changes 2026-11-24 (engineer decisions)
| Item | Change | Numbers (script) |
|---|---|---|
| D10/D11 status LEDs | 0603 red (C2286, Basic) -> side-view red Lite-On LTST-S270KRKT (C125114, Extended, USD 0.032, stock 29060 on 2026-11-24) at the right board edge, lens out of the edge, so the LEDs show from the side of the stack. Same nets (LED1_A/LED2_A anodes, cathodes GND), R34/R35 1k unchanged. Footprint `weatherstation:LED_LiteOn_LTST-S270_SideView` from the data sheet land pattern (DS22-2000-210 rev G p7: 1.10 x 1.10 pads, 0.90 gap); JLC's footprint fits by pad number (pad 1 = cathode, 0.10 mm pad offset, `tools/fab_package.py --fit-only`). Other red side-view candidates (jlcparts 2026-11-24, all Extended): TJ-S1706SW6TGLC2R-A5 (C273612, 0.045, stock 29875), E6X0602URAC1UDA (C375465, 0.017, stock 3456: thin stock), LTST-S220KRKT (C284935, 0.040, stock 9886, larger body). No Basic side-view LED exists. | `calc/led_current.py hardware/main-board`: 0.90-1.55 mA (Vf 2.4 V max at 20 mA, 1.75 V read off fig. 2 at 1-2 mA), about 2.4-4.2 mcd typical, 0.8 mcd for the lowest bin; order +USD 3.31 at qty 5 (`calc/bom_check.py --stock --qty 5`: USD 88.91) |

### Inspection and bring-up (review C, not changed in the design)
- J8 (ZE25-O3) pinout and pitch are not verified against a datasheet (none in the repo): check against the bought module before soldering J8.
- J2 (PMS7003) row orientation: check against the real cable before soldering.
- U9 pad 9 is a laser-mark pad without copper function on Bosch parts (BMP581 land pattern); it is tied to GND here, which is harmless.
- U9 (0x46) and the BMP585 add-on board (0x46) share an address: never fit both on one bus.

## Open decisions after the review (2026-11-21, for the engineer)
| Review # | Decision | Numbers / options |
|---|---|---|
| A5 cost | Order at qty 5 now USD 88.91 (2026-11-24, side-view LEDs; was 85.60) before the bare 4-layer PCB, SMT joints and shipping: parts 48.50 (9.70 per board, first price tier) + 10 Extended x 3.07 + setup 8.18 + stencil 1.53 (`calc/bom_check.py --stock --qty 5`). The PCB (est. 5-15) decides whether it stays under 100. | Cheapest further step: hand-solder J3/J4 (JST SH, C160404, one of the 10 Extended types): saves the 3.07 fee plus the part cost on the PCBA; **not applied** (no new hand-soldering without your decision) |
| B11 | Current limit for J4/J11 (bought Qwiic modules, SEN0460 up to 100 mA) | PTC SMD0805P020TF (C20976) or similar: Extended, +3.07 per order. A series resistor would break a 100 mA module. J3 (outdoor cable) already has R77 |
| B13 | L4 Isat 4.0 A below the TPS63802 5 A switch limit; L5 Isat 3.22 A below the TPS61023 valley limit (matters only in a short) | accept, or VLS252010HBX-R47M-1 (C88530) for L4 |
| B15 | Pulse port: 1M / 4.7 nF supports 77 Hz only with at least 6.5 ms reed open time; no supply pin for an active Hall anemometer | measure the anemometer; consider 330-470k; add a 3V3 pin to J12 if needed |
| B18 | "USB programming without the power board" only partly met: USB_VBUS reaches only J10, the main board is dark on USB alone | state it in the requirements, or an optional USB_VBUS-to-SYS dev jumper |
| B22 | R50/R51 2.2k assume 2 m of cable at 100 pF/m | measure the real cable |
