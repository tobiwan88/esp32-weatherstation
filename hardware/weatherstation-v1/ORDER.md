# weatherstation-v1: JLCPCB order checklist (draft, pre-layout)

Adapt from `hardware/reference/desk_notifier/notifier-v1-profile/ORDER.md` (gerber settings, order-number mark, preview checks).

## Before ordering
1. `scripts/hw-check.sh --strict --stock --qty 5` prints `hardware checks: OK` (no MISSING, stock covers 5 boards, class known).
2. Human review in KiCad of schematic and layout; both ground planes solid; antenna keepout on all layers.
3. Commit everything under `hardware/`, clean tree, then build the fab package (gerbers zip, `bom.csv` in JLCPCB columns, CPL).

## PCB options
- 4 layers, size at most 50 x 50 mm, 1.6 mm, stackup JLC04161H-7628, 5 boards. Impedance control not needed (no fast signals).
- Finish: lead-free HASL is enough for the parts used; ENIG costs extra (flat pads, optional).
- Tented vias, order-number mark "specify a location" if the layout leaves room.

## Assembly options
- Economic PCBA, one side, SMT only. If the quote forces Standard for the ESP32 module, expect about +$40-50 (see REQUIREMENTS.md 5a).
- Hand-soldered after delivery: JST-PH J5/J6, UART header J7, battery holder/cell leads. Off-board: SEN66, SHT45 (Qwiic cable), solar panel.
- Placement preview: check U1, U2, U3, U6, J1, J3, L1 (J2, J5-J8 are hand-soldered from the back) orientation; fix in the fab package rotation table, never in the CPL.

## Cost (see REQUIREMENTS.md 5a)
5 boards: about $72-112 plus shipping and VAT; about EUR 240-300 for the first batch plus one complete station.

## Bring-up (first board)
1. Power from USB only (no cell): rail 3.3 V, USB enumerates, flash an LED/serial test.
2. Cell without sun: sleep current (target below 100 uA with sensors off), 3V3_SW switching, battery divider reading.
3. USB charge: TP4056 current about 400 mA, CHRG/STDBY readable, solar charger inhibited while USB is plugged.
4. Solar charge with the real panel: MPPT set point vs panel Vmp, charge current, cold inhibit (Q3/Q5), TP4056 and LDO temperature rise.
5. SEN66 + SHT45 readings over I2C, 3V3_SW droop at fan start; EMC pre-compliance scan; WiFi range in the enclosure.
