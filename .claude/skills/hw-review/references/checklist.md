# Review checklist (board-neutral)

Each line is a question. A finding names the pin, net or file, the evidence (datasheet section, script row) and a fix.
Every item below found a real fault, a wrong-by-default state or a wasted budget on a past board.

## Defaults and absent partners
- Every enable, chip-enable, reset and strap pin: what level does it have with the partner board unplugged, with the MCU
  unpowered, in reset, in deep sleep, and during the first milliseconds of power-up? A floating enable on a charger runs
  it at its power-on defaults (voltage, current, input limits).
- The chip's power-on register defaults against the cell and the panel: charge voltage above the cell limit, input
  over-voltage threshold below a cold panel's open-circuit voltage, current limit above a protection trip. List each
  register the firmware must write before the first charge, in `FIRMWARE-RULES.md`.
- Pull to a rail or to the cell, and is that rail alive when the pin matters (cell below the regulator's dropout)?
- Pin voltage with another chemistry or a full cell against the MCU pin's absolute maximum.
- First insertion of a protected cell: the protection IC may start with discharge disabled until a charger connects.

## Protection and charging corners
- Worst-case FET resistance (hot, high Vgs-limited) times the charge current against the protection IC's overcurrent trip.
- Charge window in sleep: if only the charger's own temperature thresholds act (no firmware), what are the real cell
  temperatures at which it still charges? Cold and hot side, with the thermistor divider actually fitted.
- Minimum system voltage or similar setting that holds a pass element in linear mode: dissipation and lost energy.
- Reverse-wired panel or cell: which part conducts (a TVS forward-biased), at what current, what heats.
- Panel open-circuit voltage at the coldest temperature against the input clamp and the capacitor ratings (DC bias).
- Inductor saturation current against the peak current at the worst corner; capacitor derating at the operating voltage.

## Switched rails
- Soft start: inrush from `calc/rail_switch.py`, ramp time, the dip it causes on the parent rail.
- Turn-off: without a bleed the rail floats for tens of seconds near a valid level; the firmware's re-enable wait must
  cover it (or reset the sensors). Bleed current while on is a sleep or active load; add it to the budget.
- Back-feed through I/O pins and pull-ups into an off rail; cold start with the parent rail still ramping.

## Budget
- Sleep sum: every pull-up and divider (3.3 V across 100 k is 33 uA), ESD array leakage, regulator Iq, charger Iq,
  protection IC, MCU deep sleep with the coprocessor running. The gate's row compares the sum with the requirement.
- Autonomy: days from the real cycle against the required days, worst-month solar margin, fast mode alone vs the default.
  A budget row with no threshold passes silently; give it a FAIL level from the requirement.
- Cost: fees per unique Extended part, setup, stencil, joints, bare board, shipping, at the order quantity's price tier;
  a split into two boards pays a second setup and doubles shared Extended parts.

## Interfaces
- Header or connector between boards: pin table identical in the architecture doc, both generators and both netlists.
- Wrong matings: rotated 180 degrees, mirrored, one row off, one board flipped (a mirrored footprint lands on the bottom
  side). What touches what; can a supply meet a GPIO. Fix by keying (a pin removed and its socket hole blocked, or a
  shrouded header); script it (`header_check.py` pattern) and add it to the gate.
- Contact current per pin; connector polarity written on the sheet; a pin for every supply an add-on needs (an active
  Hall sensor needs a supply pin).
- Bus pull-ups for the real cable length and capacitance; unique addresses; ESD at every connector that leaves the board.
- Mounting: connector side after stacking, board gap, standoff height, antenna overhang not covered by the other board.

## Datasheet traps
- Datasheet pin numbering that contradicts itself (a choke's windings): check with a meter on arrival; write it in the bring-up list.
- Maker of the fab listing differs from the datasheet's maker.
- A substitute datasheet (sibling part) used for a part without a public one: every value tagged unverified; the bring-up
  list gets a check (address ACK, chip-id read) that proves the pin map.
- Value in a note or comment older than the value on the sheet.

## Bring-up list
Generate it from the review: first power with no cell, which pin to measure, which register to read, which address must
ACK, what proves each UNVERIFIED item. It goes into the order notes.
