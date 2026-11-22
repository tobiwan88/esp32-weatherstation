# Placement, EMI and stacked boards (read when placing or reviewing a layout)

## Floorplan rules (each gets a datasheet or guideline citation in `BOARD.md`)
- Radio module: antenna at the board edge, overhang or a full-layer keepout (no copper, vias or parts on any layer in a strip
  under the antenna); the vendor's hardware guideline lists the allowed positions. Nothing metal, no cable and no other
  board over the antenna. Overhang needs fab confirmation (edge rails, routing).
- USB-C at an edge, level with the MCU's USB pins; ESD array right at the connector (before the series resistors); series
  resistors at the MCU; leave a free lane for the pair before placing anything near it.
- Sensors: opposite the heat sources, away from board edges and mounting holes when the datasheet says (stress, airflow),
  with a rule area where the datasheet wants no copper under the body (outer layers; ask about inner planes).
  When a datasheet rule contradicts the requested position, follow the datasheet and list it.
- Cell thermistor next to the cell, far from the charger and inductor (`thermal_distance`).
- Connectors where cables leave; connector families with a keepout for the mating plug; pin-1 marks and polarity on silk.
- Regulators: caps and inductor from the datasheet layout example; the switch node smallest; sensitive nets away.
- Row of fine-pitch power pins: reserve escape bands beside the signal pins; draw the power stage by hand.
- Bulk caps of one rail next to each other; test points and tweezer pads (reset, boot) at edges, not under modules.
- Mounting holes: a pattern with no mirror or 180-degree symmetry when two boards stack (a turned board cannot be screwed on).

## Stacked boards (two boards joined by a keyed header)
- Same outline and hole pattern, header at the same position; both footprints unmirrored on the top copper layer so a
  flipped board cannot land SYS on a GPIO; key the header (pin removed, socket hole blocked) and test wrong matings.
- Connector bodies: the upper board's back faces the lower board, so its through-hole and tall parts go on the FRONT; the
  lower board's back-side parts need standoffs. Write gap, header height and standoff height as UNVERIFIED until measured.
- Antenna overhang must not be covered by the other board; heat from the lower board's regulators through the gap to the
  upper board's sensor (`stack_check` row); header pin current per pin.
- Alternative: side by side with a ribbon; then the supply rail needs a local reservoir cap at the header and the cable
  carries the bus (length and capacitance matter for I2C).
- Gate: a stack check (outline, holes, header pads and nets identical) and a mating-error check run without KiCad.

## EMI review (`calc/emi_check.py`, settings in `emi.yaml` or `critical.yaml` `emi:`)
- Pair rows: layer, length per path, skew (with and without via barrels), stubs, vias, spacing of other nets, crossings
  of the main run in plan view, stub round trip against the signal edge time (lumped limit about 10 % of the edge).
  Full-speed USB tolerates far more skew than a target set for high speed; keep the tighter number as the target and
  say which limit the standard actually sets.
- Edge: a GND via fence along the board edge, largest gap against the pitch; exempt spans with reasons (antenna, holes,
  overhangs, module pad columns that leave no room, corners where a via would float).
- Planes: longest signal run over a void of its reference plane.
- Loops: VIN cap to VIN pin to GND pin to cap, loop length and switch-node copper area per regulator.
- Parallel: victim nets (I2C, FB, sense, analog) against aggressors (switch nodes, USB, clocks): gap and longest run.
  An analog net 1 mm from a pair for 9 mm of run was a real finding; moving it to 1.7 mm fixed it.
- Known items go to `known:` with the reason; a limit is never loosened to pass.

## Routing review section in `BOARD.md` (after routing)
Numbers per item: pair skew and spacing, loop lengths, switch-node areas, plane voids, edge gaps, longest detours with
the nets and why accepted, neck-down widths and via sizes at the fab floor, residual risks that only a bench can answer
(eye quality, charger detection, ringing, thermal rise at pin necks). The first thing for the human to look at, by render name.
