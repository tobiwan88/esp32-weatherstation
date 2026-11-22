# <board>

Status (current state first; history below, dated): <gate reached>, <gate output>, open decisions: <where>.

## Purpose
<one paragraph; the contract with the other boards: ../ARCHITECTURE.md>

## Sheets
| Sheet | Content |

## Decisions (dated; why)
- <decision> (<engineer, date>): <reason>

## Cost (fab, date, qty, command)
| Item | USD |

## Layout
Floorplan with citations: antenna, USB, sensors vs heat, connectors, ESD, thermistor. Area share. Stack notes.

## Routing
What is hand-drawn, what the router did, frozen routes, build and reproduce commands.

## Routing review (date)
Pair numbers, loops, areas, plane voids, edge gaps, detours accepted, fab-floor tracks/vias, residual risks, where to look first.

## Commands
```
<generate schematic>   <review script>   <build board>   <route>   <freeze>
python3 hardware/calc/critical.py hardware/<board> [--placement]
python3 hardware/calc/emi_check.py hardware/<board>
python3 hardware/calc/bom_check.py hardware/<board> [--strict] [--stock --qty N]
scripts/hw-check.sh
```

## Pitfalls specific to this board
