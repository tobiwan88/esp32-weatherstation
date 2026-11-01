# Cells: values from the vendor specifications (read 2026-11-01)

## Decision (2026-11-01, latest): CBAK 26700LT with firmware-managed cold charging
- The cell is the CBAK 26700LT (LFP, charge -10 to 50 C). The chip's own cold stop (about 0.5 C) is replaced by firmware:
  TS_IGNORE = 1 during a charge session, with the band table in `charge-policy.md`. Sleep and default use the chip's JEITA.
- The standard 0-45 C LFP 26650 option (earlier in this file's history) is dropped.
- Rules and residual risks: `charge-policy.md`.

## LFP 26700LT (variant A, samples in hand)

| Item | Value | Condition / note |
|---|---|---|
| Nominal voltage | 3.20 V | cover table |
| Capacity typical / minimum | 4000 / 3900 mAh | 0.5C, spec A/03 |
| Internal resistance | <= 20 mOhm (1 kHz) | spec A/03 |
| Mass / energy | 91.0 g, 140 Wh/kg | spec A/03 |
| Standard charge | 0.5C CC to 3.65 V, then CV until 0.05C (spec text also gives 0.01C end) | spec A/03 |
| Limited charge voltage | 3.75 V; upper limit 3.8 V (GB 47372) | spec A/03 |
| Standard discharge | 0.5C CC to 2.0 V | spec A/03 |
| **Discharge cut-off** | **2.0 V** | spec A/03 |
| Max continuous charge by cell temperature | -10 to 0 C: 0.2C (0.8 A); 0 to 20 C: 0.5C (2 A); 20 to 40 C: 1C (4 A); 40 to 50 C: 0.5C (2 A) | spec A/03 table |
| Max continuous discharge by temperature | -40 to -30 C: 1C; -30 to -20 C: 2C; -20 to 30 C: 3C; 30 to 45 C: 2C; 45 to 60 C: 1C | spec A/03 table |
| Charge temperature (cell surface) | -10 to 50 C (surface <= 55 C); stop above | spec A/03 |
| Discharge temperature | -40 to 60 C (surface <= 65 C) | spec A/03 |
| Storage | -20 to 45 C for 3 months; -10 to 25 C for 6 months | spec A/03 |
| Low-temperature capacity vs 25 C | -20 C >= 80 %, -30 C >= 70 %, -40 C >= 50 % | spec A/03 |
| Cycle life | >= 2000 cycles at 0.5C / 0.5C, residual >= 80 % | spec A/03 |
| Shelf life | 1 year | spec A/03 |
| Safety | GB 38031-style tests: temperature cycle, crush, nail, short circuit 5 mOhm at 22 C | spec A/03 |

Design values derived from this (used in the schematic and firmware plan):
- VREG 3.65 V (standard end voltage). Chip accuracy must keep the cell below the 3.75 V limit: at 3.65 V nominal the margin is
  100 mV, so measure the real end voltage with a DMM on the sample.
- ICHG 1.5 A (0.38C of the minimum 3.9 Ah; the 0 to 20 C band allows 0.5C = 1.95 A, the 20 to 40 C band 1C). Below 0 C the cell allows only 0.8 A
  (0.2C) at -10 to 0 C; the chip suspends charging below its cold threshold (about 0 C, see usb-charger-bq25798.md). Keep the
  suspend threshold at or above 0 C, the cell's own limit.
- Cell discharge cut-off 2.0 V (spec). HY2112-CB overdischarge protection at 2.10 V (release 2.30 V). Firmware turns the sensors
  off at 2.4 V (`board.yaml cell.vcutoff_firmware_v`), so the hardware protection never acts on a normal load.

## Sodium 32140NH 7 Ah (variant B): DROPPED 2026-11-01
Not used in v1 (LFP only). The values are kept for reference: the 3.35 V limit and 1.5 V cut-off are outside the HY2112-CB
thresholds, so this cell would need its own protection part.


| Item | Value | Spec section / condition |
|---|---|---|
| Material / nominal | polyanion sodium-ion, 3.0 V nominal | section 5.1 |
| Operating voltage | 1.5 to 3.3 V | section 5.1 |
| Capacity nominal / minimum | 7 Ah / 7 Ah (25 C, 0.5C) | section 5.1 |
| AC internal resistance | 1.0 mOhm <= IR < 3.0 mOhm (1 kHz, 25 % SOC) | section 5.1 |
| Mass | 246 +/- 10 g (with package) | section 5.1 |
| Energy density | >= 85 Wh/kg, >= 173 Wh/L | section 5.1 |
| Size | 32 mm dia (33.2 +/- 0.2 mm, figure A), height 140 +/- 0.3 mm | figure A |
| Standard charge | 0.5C CC to 3.3 V, then CV until 0.05C | section 5.2, 8.2 |
| **Standard end-of-charge voltage** | **3.3 V** | section 5.2 |
| **Max end-of-charge voltage** | **3.35 V** (charging must stop above this) | section 5.2 |
| Standard charge current | 0.5C (3.5 A) | section 5.2 |
| Max continuous charge | 4C (28 A), at 15 to 40 C | section 5.2 |
| Charge temperature, max range | -10 to 65 C (cell surface; stop outside) | section 5.2 |
| Charge temperature, optimum | 15 to 40 C | section 5.2 |
| Standard discharge | 0.5C CC to 1.5 V | section 5.3, 8.2 |
| **Discharge cut-off** | **1.5 V** | section 5.3 |
| Max continuous discharge | 10C at 15 to 45 C | section 5.3 |
| Max pulse discharge | 15C for 10 s, at 15 to 45 C and 100 % SOC | section 5.3 |
| Discharge temperature | -40 to 65 C (stop outside) | section 5.3 |
| Capacity retention (0.5C) | >= 95 % at -10 C, >= 90 % at -30 C, >= 85 % at -40 C (vs 25 C, cut-off 1.5 V) | section 6 |
| Storage | -20 to 45 C for 3 months; -10 to 25 C for 6 months | section 5.1 |
| Cycle life | >= 6000 cycles (25 C, 0.5C / 1C, 80 % SOH) | section 5.1 |
| Safety tests | GB 38031 (forced discharge, overcharge, short circuit, heating, crush), nail penetration (GB 43854-2024) | section 7 |

Design values derived from this:
- **VREG 3.30 V** (not 3.95 V). Firmware writes 3.30 V for variant B. Verify with a DMM on the sample: 50 mV margin to the 3.35 V
  maximum is small. Consider 3.25 V if the measured accuracy needs it.
- ICHG 1.5 A (0.21C of 7 Ah; the 0.5C standard is 3.5 A, so 1.5 A is inside the limit).
- Cell cut-off 1.5 V (spec). A 3.0 V nominal cell sits below the 3.3 V rail input for most of its discharge (the TPS63802 covers 1.3 V) HY2112-CB cannot protect this cell (see below).
- Energy: 7 Ah x 3.0 V = about 21 Wh nominal (not 30 Wh).

## Comparison (what each variant needs from the board)

| | LFP 26700LT | Sodium 32140NH 7 Ah |
|---|---|---|
| VREG (firmware) | 3.65 V | 3.30 V |
| Max cell voltage | 3.75 V (limit), 3.8 V (upper) | 3.35 V |
| Cut-off (firmware) | 2.0 V | 1.5 V |
| Charge window | -10 to 50 C (0.2C below 0 C, 0.5C 0 to 20 C) | -10 to 65 C (optimum 15 to 40 C) |
| Charge current used | 1.5 A | 1.5 A |
| Nominal energy | 12.8 Wh (min 12.5 Wh) | about 21 Wh |
| Nominal voltage | 3.2 V | 3.0 V |
| Fits the TPS63802 buck-boost (1.3 V in) | yes | yes |
| 1-cell protection in this design (HY2112-CB) | yes (3.75 V / 2.10 V) | no: its 3.35 V limit and 1.5 V cut-off are below the HY2112 thresholds; needs another part |
