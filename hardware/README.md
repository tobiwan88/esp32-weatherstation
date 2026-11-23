# Hardware: where to look

Boards (one folder each, profile in `board.yaml`, notes in `BOARD.md`). Gate output: `scripts/hw-check.sh`.

| Board | Role | State (details in its `BOARD.md`) |
|---|---|---|
| `power-board/` | charger, protection, solar and USB inputs, header to the main board | routed 2026-11-22, DRC 0 at all severities; no fab files yet |
| `main-board/` | MCU, 3.3 V and 5 V rails, USB-C, sensor ports | routed 2026-11-22, DRC clean (waived silk warnings listed there), EMI check OK; no fab files yet |
| `sht45-board/` | outdoor temperature and humidity head, Qwiic chain-out | layout done 2026-11-04: ERC 0, DRC 0 incl. warnings, parity clean |
| `bmp585-board/`, `veml6030-board/` | pressure and light add-ons on the same base | DRC clean, parity clean (2026-11-04) |
| `weatherstation-v1/` | first single-board design, kept as history, fab files and parts cards | superseded by the split |

| What | Where |
|---|---|
| System requirements, architecture, decisions that must not be lost | `REQUIREMENTS-system.md`, `ARCHITECTURE.md`, `DECISIONS.md` |
| Plan, review rounds, order notes | `PLAN.md`, `REVIEW-*.md`, `ORDER-sensor-boards.md`, `<board>/ORDER.md` |
| Board profile files read by the scripts | `<board>/board.yaml`, `critical.yaml`, `emi.yaml`, `parts/` |
| Board-neutral checks, tools, fab rules | `calc/`, `tools/`, `rules/` (installed from `../hw-kit/tooling`) |
| Generators and project build scripts | `gen/`, `tools/build_*.sh`, `tools/route_*.sh` |
| Skills and agents | `../.claude/` (installed from `../hw-kit`; read `hw-base` first) |
| Earlier project's pipeline to copy from | `reference/desk_notifier/` |

New board: `scripts/new-board.sh <name>`. The kit and how to reuse it in another project: `../hw-kit/README.md`.
