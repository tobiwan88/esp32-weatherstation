# System architecture: power board, main board, SHT head

State 2026-11-23: `power-board/` and `main-board/` (split from `weatherstation-v1/`, which stays as the single-board history)
have schematics, placement and routing done, DRC clean; no fab files yet (`GATES.md`). The sensor head is `sht45-board/`.
Requirements: `REQUIREMENTS-system.md`. Header pin map in code: `gen/boards_common.py` (`HEADER_PINS`), used by both
generators; `tools/split_check.py` proves both boards use it and that the split keeps every v1 part and net.

## Block diagram

```
 solar panel 6 V           LiFePO4 cell (26700)
     |  J5                     |  J6
+----v-------------------------v-------------------+     keyed 2x10 2.54 mm J10 (J_PWR)       +-----------------------------------------------+
| POWER BOARD  (power-board/)                      |   SYS (1,2) ------------------------->   | MAIN BOARD  (main-board/)                     |
|  PV: SMBJ10A D1, CM choke L3, ACFET2/RBFET2 M3/M4|   GND (4-6,9,10,13,14,17,18), key 3    |  SYS -> TPS63802 U2 -> +3V3 -> ESP32-S3 U1    |
|  USB: ACFET1/RBFET1 M1/M2  <---------------------|-- USB_VBUS (19,20) <-----------------   |       -> Q40 -> 3V3_SW (sensor bus, SHT head) |
|  BQ25798 U3 (VAC1 USB, VAC2 PV, BC1.2 on D+/D-)  |<- USB_DP/USB_DN (7,8) <------------   |  SYS -> TPS61023 U7 -> 5V_SW (PMS7003, O3)    |
|  cell: F1 PTC, TH1 NTC, HY2112 U6 + M60/M61      |<> CHG_SDA/CHG_SCL (11,12) <-------->   |  USB-C J1 + USBLC6 U4 (data to the ESP32)     |
|  no 3.3 V on this board                          |-> CHG_INT (15) -------------------->   |  charger pull-ups R20/R22/R54/R55 to +3V3     |
|                                                  |<- CHG_CE (16) <--------------------   |  sensor ports J2, J3/J4 (Qwiic), J11, J8, U8  |
|                                                  |                                         |  BMP580 U9, rain/wind/vane port J12           |
+--------------------------------------------------+                                         +---------------------+-------------------------+
                                                                                                                   | J3 Qwiic cable (3V3_SW, I2C)
                                                                                                         +---------v---------+
                                                                                                         | SHT HEAD          |
                                                                                                         | (sht45-board/)    |
                                                                                                         +-------------------+
```

## J10 (J_PWR) pin table

Keyed 2 x 10, 2.54 mm, through-hole, hand-soldered on both boards (same footprint `PinHeader_2x10_P2.54mm_Vertical`,
no LCSC), 20 positions, 19 used: 18 nets plus one spare GND; **pin 3 is the key**. Odd pins = row A, even pins = row B.
Direction is seen from the power board. Engineer decision 2026-11-21 (was an unkeyed 2 x 9).

| Pins | Net | Direction | Notes |
|---|---|---|---|
| 1, 2 | SYS | power -> main | BQ25798 system rail (narrow VDC, about cell voltage, 1.8-5.5 V on the main board); 2 pins, 3 A per pin class header, >= 1 A required |
| 3 | key | | no pin on the main board (pulled), hole blocked in the power-board socket; no net on either board |
| 4, 5, 6 | GND | | 4 is the spare GND |
| 7 | USB_DP | main -> power | BQ25798 D+ (BC1.2 detection only); also ESP32 IO20 via R32 on the main board |
| 8 | USB_DN | main -> power | BQ25798 D- ; also ESP32 IO19 via R33 |
| 9, 10 | GND | | |
| 11 | CHG_SDA | both | charger I2C, 0x6B; 10k pull-up R54 on the main board (ESP32 IO1, RTC I2C for the ULP) |
| 12 | CHG_SCL | main -> power | 10k pull-up R55 on the main board (IO2) |
| 13, 14 | GND | | |
| 15 | CHG_INT | power -> main | open drain (6 mA max sink), 10k pull-up R22 on the main board (IO10) |
| 16 | CHG_CE | main -> power | active low charge enable (IO9); pulled up on both boards = charge off: R20 1M to +3V3 (main), R23 330k to BAT_PACK (power) |
| 17, 18 | GND | | |
| 19, 20 | USB_VBUS | main -> power | USB-C VBUS to the ACFET1 drain (M1) and VAC1; 2 pins (USB input up to the 1.59 A ILIM clamp) |

### Keying and mounting (layout rules)
- **Male pins on the main board, socket on the power board.** The main board's 2 x 10 male header has pin 3 pulled
  (pliers before soldering); the power board's 2 x 10 female socket has hole 3 blocked (a cut-off pin pressed in flush,
  or a drop of epoxy). The socket keeps the live SYS pins of a loose power board covered (review B17).
- Both footprints identical and **unmirrored on F.Cu**, pin 1 at the same top-view corner, through-hole pads even when
  the connector body sits on the bottom side (stack: main board above, its pins pointing down into the socket).
- **Asymmetric mounting holes**: the M3 hole pattern of both boards is not symmetric about either board axis (for
  example one hole offset by at least 3 mm), so a board turned 180 degrees or flipped does not line up with the
  standoffs. Implemented as `HOLES` in `gen/stack.py` for both boards and checked by `tools/stack_check.py`.
- Silkscreen on both boards: pin 1 mark, "KEY 3" at pin 3, "SYS" at pins 1/2.
- `tools/header_check.py` (in the gate) proves the key: a 180 degree rotation, a mirror about either axis and any
  one-column offset put a present pin onto the blocked hole (cannot mate: 22 of 35 mating errors). The 13 errors that
  still mate are one-row offsets on an unshrouded header; in each of them SYS and USB_VBUS meet only GND or each other
  (a short that the BQ25798 SYS short protection, the HY2112 short detection or the USB source limits), never a signal
  pin. A shrouded socket removes the row offsets too.

### Contract decisions
a. **Pin order.** SYS sits on column 1 (pins 1, 2), USB_VBUS on column 10 (pins 19, 20), the key on column 2, and the
   six signals on columns 4, 6 and 8 with a GND pair between every two signal pairs (columns 3, 5, 7, 9). Stacking
   alone does not prevent a 180 degree rotation or a one-pin offset (the review of 2026-11-21 corrected that claim):
   the key and the asymmetric mounting holes do. With this pin order no mating error puts a supply pin onto a signal
   pin, so the key no longer guards against ESP32 GPIO overvoltage (that was the rationale of the old unkeyed 2 x 9
   order). What the key prevents now is the SYS/USB_VBUS cross-short: without it a 180 degree rotation or a mirror puts
   SYS onto USB_VBUS (and onto GND), a short that only the BQ25798 SYS short protection, the HY2112 short detection and the
   USB source's current limit stop (`tools/header_check.py`; the one-row offsets that still mate are of that kind too).
b. **USB D+/D- (BC1.2): carried over the header (pins 7/8). ENGINEER DECISION.** Reason (BQ25798 SLUSDV2C 7.3.4.5 and
   table 7-4): detection runs only on VAC1 with AUTO_INDET_EN = 1 (the POR default). Without D+/D- the result is not an
   SDP but an unknown or non-standard source: IINDPM 3 A, clamped by ILIM to 1.59 A, drawn from a PC port that may only
   supply 0.5 A. With D+/D- the SDP case gets 500 mA, DCP 3.25 A (clamped to 1.59 A). The weatherstation-v1 note says
   chargers were not detected without it (critical.yaml). Alternative: no D+/D- on the header, firmware writes
   AUTO_INDET_EN = 0 and sets IINDPM itself (500 mA unless it knows better). Cost of the chosen route: 2 pins + 1 GND pair,
   and the D+/D- stubs reach the power board (full speed 12 Mbit/s, stubs short when stacked). Firmware still sets
   AUTO_INDET_EN = 0 after the first detection so a later re-detection does not disturb enumeration (v1 B5) and must
   never enable HVDCP (9/12 V on USB_VBUS would exceed the USBLC6 U4 VBR of 6 V on the main board).
c. **Pull-ups live on the main board** (USB sheet, beside J10): R20 CE 1M (100k until 2026-11-21), R22 INT 10k, R54/R55 I2C 10k,
   all to +3V3. Exception: the power board carries its own CE pull-up R23 330k to BAT_PACK (d). The
   power board has no 3.3 V rail; REGN (5 V) is above the ESP32's 3.6 V and is the wrong rail for INT (7.3.11.2).
   A bought charger module brings its own rail; its pull-ups then sit in parallel (10k || its value).
d. **CE default: high (charge off)** through R20 until the firmware has written VREG 3.65 V (POR default 4.2 V is
   above the LFP limit 3.75 V). Main board without a power board: nothing on SYS, the board is unpowered unless a bench
   supply feeds SYS (bring-up below); the I2C pull-ups and R20 hang on +3V3 with nothing behind the header.
   **Power board without a main board:** R23 330k from CHG_CE to BAT_PACK holds CE high (review A1, done 2026-11-21 with
   1M; 330k since 2026-11-24, review B2; the TI EVM also keeps its CE pull-up on the charger board, SLUUCB5 JP17).
   BAT_PACK (2.1-3.75 V for LFP) is inside the CE abs max of 6 V (SLUSDV2C 6.1) and above VIH_CE 1.3 V (6.5) down to
   BAT 1.63 V even with the 1 uA maximum CE leakage through 330k, below the HY2112 floor of 2.10 V.
   **Both boards, GPIO released, +3V3 up:** R20 1M (+3V3) and R23 330k (BAT_PACK) in parallel give CE 2.15-3.59 V over
   BAT 2.1 V to 3.685 V (the highest regulated voltage, VREG 3.65 V + 35 mV) and 3.64 V at the HY2112 trip (3.75 V). The
   top of that range reaches the 3.6 V the ESP32 module datasheet gives as VDD33 abs max (a GPIO input limit is not in
   the module card; the pad's clamp to VDD takes at most about 1.4 uA through 330k). Driving CE high as an output instead
   of releasing it holds CE at 3.3 V and takes 1.2 uA from BAT into the pin (FIRMWARE-RULES.md 2, open decision in
   `power-board/PARTS-REVIEW.md` B5). A 4.1 V sodium cell would give more: then fit R23 to REGN through a divider.
   The ESP32 GPIO overrides both; holding CE low in deep sleep costs 3.3 uA (R20, +3V3) + 9.7 uA (R23 at BAT 3.2 V)
   (`calc/power_budget.py` sleep sum; `calc/ce_pullup.py` for all cases).
   **Both boards, +3V3 dead (review follow-up B2, DECIDED 2026-11-24: R23 330k):** TPS63802 not running and the ESP32
   unpowered leave R20 (1M to about 0 V) and R23 (330k to BAT_PACK) as a divider: CE = 0.752 x BAT, high (VIH_CE 1.3 V)
   above BAT 1.73 V, 2.06 V with the 1 uA maximum CE leakage through 248k, so CE is defined over the whole LFP range
   above the HY2112 floor (2.10 V). With R23 1M it was BAT/2: undefined below BAT 2.6 V (3.6 V with leakage). Not in this
   arithmetic: the unpowered ESP32 pad's ESD diode to the dead +3V3 rail can pull CE to that rail + one diode drop
   (bench check: measure CE with +3V3 off, `calc/ce_pullup.py` WARN row). Rejected options: R20 DNP with the power board;
   accept (firmware takes CE within a boot). Details: `power-board/PARTS-REVIEW.md` B5.
e. **No back-feed with the main board unplugged:** USB_VBUS pins connect only to the ACFET1 drain and VAC1; RBFET1 M2
   blocks VBUS/PV from the USB_VBUS pins (figure 8-2). SYS pins stay live (cell voltage through the BQ25798 BATFET);
   exposed SYS pins on a loose power board are a short risk, not a back-feed.
f. **Future compatibility:** the main board needs only SYS (1.8-5.5 V, >= 1 A) and GND on J10. A bought charger module
   that supplies SYS can replace the power board; pins 7-20 then stay open (CE pulled high by R20, INT high, I2C idle,
   the firmware sees no device at 0x6B and runs without charger control). USB charging then needs the module's own input.

### Bring-up: main board alone
Bench supply on J10 pins 1/2 (SYS) and a GND pin (4): 3.3-4.2 V, current limit 0.5 A. **Never above 5.5 V** (TPS63802
recommended VIN maximum, abs max 6 V; TPS61023 5.5 V). USB-C then works for programming and USB-JTAG, but USB VBUS
alone does not power the main board: VBUS goes only to J10. (Optional dev jumper USB_VBUS -> SYS: decision in
main-board/PARTS-REVIEW.md C2.)

**Warning (review B17): never feed a bench supply into SYS of a power board with a cell fitted.** SYS connects to the
cell through the BQ25798 BATFET, so a supply on SYS charges the cell without the charger's voltage or current
regulation (only HY2112 at 3.75 V stops it). Bench-feed SYS only on the main board alone, or remove the cell. The
socket on the power-board side covers its live SYS pins when the board is handled alone.

### Mechanics
Stacked: the main board carries J10 as male pins (pin 3 pulled) at the same top-view position as the power board's
socket with pin 1 on the same corner, so the mapping is 1:1 (keying and mounting rules above). Stack versus side-by-side is open (REQUIREMENTS-system.md 10.5).
