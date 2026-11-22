---
name: hw-requirements
description: Use at the start of a hardware project or a redesign, and whenever scope, cost, power cycle, sensor set, board partition or interfaces change - requirements interview, REQUIREMENTS file, cost model, power-cycle and autonomy budget, pin reservation, splitting into boards, header between boards, firmware hand-off. Gate 1. Read hw-base first.
---

# Requirements and architecture (gate 1)

Read `hw-base`. Template: `.claude/skills/hw-base/templates/REQUIREMENTS.md`. Nothing is drawn before the engineer has accepted this file.
Late cost, late power-cycle fit and late pin conflicts were the three expensive surprises of the first project.

## Interview (ask the blocking questions, in one round)
- Purpose: who uses the data and where it goes (own use first, publishing optional later), environment (outdoor, exposed,
  temperature range), lifetime, what "good enough" means (80 % of the capability at a price that gets built).
- Money: cost cap per assembly order and for the whole project, quantity (units, plus development boards), what counts
  (board, modules, sensors, cell, panel, enclosure), whether the project is dropped above a price.
- Sourcing and assembly: fab-assembled only, or hand-soldered connectors and marketplace modules allowed; hand tools.
- Flexibility the engineer wants to keep (cell chemistry, optional sensors, plug-in ports) and the one that costs a board.
- Existing hardware on hand and what it must support.
- The engineer often answers in several messages. When a message ends "I was not done", or asks "what are the options",
  answer with options and cost; do not start a build. Record the answers with the date and their own words.

## Requirements file
- Each requirement: number, statement, source or stated assumption, and the check that proves it (script row or `(review)`).
- Required sections: purpose, environment, cost model, power cycle, sensors/ports, interfaces and board partition,
  fab limits (layers, outline, tier), firmware hand-off, open items with owner.
- Uncertain facts go to research (`hw-review`, research prompts); the file marks each as `page`, `snippet` or `estimate`.
- Benchmark against a ready-made module or open design that already does the job; the board must beat it on cost, size or power.

## Cost model (script: `calc/bom_check.py`)
- Cost per finished unit including everything bought outside the fab.
- Per order: parts at the order quantity's price tier, loading fee per unique Extended part, setup, stencil, joints, bare
  board, shipping. The cheapest lever is fewer distinct parts: Basic parts first, one value reused everywhere, 0402 when it
  is Basic, drop or hand-solder the one expensive connector.
- Compare the options in numbers before the engineer chooses. A live quote cannot be scripted (the fab's API is
  partner-only, the cart endpoints need the account session and put it at risk): estimate offline with the published fee
  table, then one manual cart quote per revision.
- Splitting into boards adds a second setup, stencil and duplicated shared Extended parts; show that cost with the benefit.

## Power cycle and autonomy (script: `calc/power_budget.py`)
- Table every load: warm-up, minimum on-time, sampling rate an algorithm needs, current per phase, sleep current.
  A sensor that needs continuous sampling or a long warm-up does not fit a deep-sleep design: find it here.
- Budget: average current, energy per day, days of autonomy at the required cell fraction, solar margin in the worst
  month at the site (a cloudy winter day should still end net positive). The requirement's numbers become FAIL thresholds
  in the script; a row without a threshold prints OK while the requirement is broken.
- Decide tracking vs simple charging by energy: when the panel covers the load several times over, maximum-power tracking
  gains little; input-voltage regulation in a charger IC is enough.
- Cold: charge chemistry and the temperature window; what the chip does alone in deep sleep and what the firmware must do.
- Cycle: default period, fast mode and its trigger, measured in the budget as two rows.

## Pin and interface plan
- Before the pin map reserve: pins that work in deep sleep (coprocessor buses on fixed pins, wake pins), strapping pins,
  native USB pins, boot and reset, antenna keepout.
- Sensor and add-on ports: prefer a standard connector family with a published pinout over a custom one; every port has
  supply, ground and the signals an add-on class needs (a pulse sensor needs a supply pin).
- Board partition: split for cost, for an off-board sensor head, or for modularity. The link between boards is one keyed
  header with ONE pin table in the architecture doc, mirrored by both generators; carry supplies by current, the buses,
  interrupts, enables, and enough grounds. Decide stack or side by side with the connector side, gap, antenna overhang and
  standoffs written down. Check wrong matings (`hw-review` checklist) and align footprints with a script (gate).
- Defaults when the partner board is absent or asleep are part of the interface (`hw-review` checklist).
- Outline and layer count against the fab's cheapest tier; EMI-driven layer count (4 layers with solid ground planes is the baseline).

## Firmware hand-off
- Anything hardware cannot enforce goes to `FIRMWARE-RULES.md`: registers written before first charge, power-on defaults to
  override, charge-suspend conditions, pin states before a rail is switched off, waits after a rail turns off or on, the
  cold and hot charge policy. Each rule names the datasheet section; register addresses are checked against it.

## Exit check (gate 1)
Every requirement has a number, a source and a check; cost, power, sensors, enclosure, environment and fab limits are
written; the engineer has accepted the list; open items have owners. Add the date and the accepted version to `GATES.md`.
