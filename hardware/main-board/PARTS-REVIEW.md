# Main board: parts and circuit review, 2026-11-21

Scope: the split (J10 contract, the board alone) and the phase B additions. Circuit carried over from weatherstation-v1
is reviewed in `../weatherstation-v1/PARTS-REVIEW.md`. Nothing below changes the topology silently: each fix is a decision.

## A: probably wrong
None found in the split.

## B: works, margin or rule broken
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| B1 | USB: USB_VBUS | USB_VBUS has no capacitor on this board: C1 0.1 uF moved to the power board with the ACFET pair. The USBLC6 U4 VBUS pin and the J1 contacts see the cable and the header inductance without local decoupling; ESD on VBUS returns through U4 only. | Add 100 nF (C307331, Basic, already on the BOM) at J1 VBUS; optionally 1-10 uF, but stay under the USB 10 uF inrush limit together with the power board's VBUS caps behind the ACFET (they are behind M1, so they do not count while M1 is off). | USB 2.0 spec 7.2.4.1 (10 uF max at attach); USBLC6-2 DS4260 application (VBUS cap at the pin) |
| B2 | Rails: SYS from J10 | U2 and U7 have their input caps (C40 10 uF, C44) but the SYS bulk (5x10 uF) is now on the other board, behind about 50-80 mm of header and trace when side-by-side. | Keep C40/C44 at the pins; if the boards go side by side with a cable, add 22 uF at J10 SYS. Decide with the mechanics (REQUIREMENTS-system.md 10.5). | TPS63802 SLVSEU9D 8.3 (effective CIN >= 4 uF) and 10.2.2 input capacitor selection |
| B3 | Header: CE and INT pull-ups | R20/R22/R54/R55 hang on +3V3 and are now the only pull-ups for the charger. Correct for this pair; a second host or a bought module with its own pull-ups adds in parallel. | None now; note in ARCHITECTURE.md (done). | BQ25798 7.3.11.2, 7.3.14 |
| B5 (applied in phase B, confirm) | Sensors: R50/R51 | 10k sensor-bus pull-ups with the outdoor SHT cable (2 m assumed, 100 pF/m) and up to 7 devices: Cb about 276 pF, rise time 2.3 us, over the 1 us standard-mode limit. | Changed to 2.2k (C25879 Basic): 514 ns; with one bought 2.2k module in parallel the low level sinks 2.64 mA (limit 3 mA). Rule: at most one external 2.2k pull-up pair on the bus; measure the cable capacitance. | NXP UM10204 rev 7 table 10, section 7.1; `calc/i2c_bus.py hardware/main-board` |
| B4 | USB: BC1.2 and enumeration | D+/D- stubs now run to the power board through J10; the BQ25798 drives D+/D- during detection (DCD, primary/secondary) while the ESP32 USB PHY is attached. Same coexistence as v1 B5, longer stubs. | Firmware: AUTO_INDET_EN = 0 after the first detection; keep the J10 to U3 stub short (stacked). | BQ25798 7.3.4.5.1 |

## C: cleanup
| # | Where | Finding | Proposed fix | Source |
|---|---|---|---|---|
| C1 | Header: bench supply | Main board alone needs SYS from a bench supply; above 5.5 V U2 and U7 leave their ratings (abs max 6 V / 7 V). | Bring-up note (ARCHITECTURE.md); a TVS on SYS is not needed with the power board. | TPS63802 8.1/8.3; TPS61023 6.1/6.3 |
| C2 | Dev jumper USB_VBUS -> SYS | With USB only the main board stays dark. A DNP 0 ohm or solder jumper USB_VBUS -> SYS would power it from USB on the bench (5 V is inside U2/U7 ranges) but must never be closed with a power board plugged (USB_VBUS straight onto SYS bypasses the charger). | Engineer decision; default: no jumper, bench supply. | ARCHITECTURE.md bring-up |
