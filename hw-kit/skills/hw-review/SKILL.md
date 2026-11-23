---
name: hw-review
description: Use to organise reviews and subagents on a hardware project - parts and circuit review against datasheets, independent reviewers, consolidating findings (A/B/C), taking decisions to the engineer, applying a fix round, delegating long build jobs, and writing research prompts. Read hw-base first; the reviewer and builder agents are in .claude/agents.
---

# Hardware review and delegation

Read `hw-base`. The engineer owns decisions (topology, part, chemistry, outline, cost); agents find, build and report.
Human review is the main quality gate; this skill makes it cheap and keeps it from being skipped.

## Roles
| Role | Agent | Model | Job |
|---|---|---|---|
| researcher | `hw-researcher` | small | gather evidence for one question; never decides |
| extractor, lookup, triage, one-image check | `hw-datasheet-extractor`, `hw-part-lookup`, `hw-drc-triage`, `hw-visual-check` | small | one datasheet / one part / one report / one image, JSON answer |
| builder | `hw-builder` | strong | one long job (split, fix round, placement, routing, fab files) in its own context |
| reviewers | `hw-datasheet-reviewer`, `hw-consistency-reviewer`, `hw-render-reviewer` | strong | independent, read-only, fresh context |
| re-reviewer | any reviewer, mid-size model | mid | only what changed in a fix round |
| brainstorm when blocked | mid-size model | mid | options for a stuck step; the owner decides |
| engineer | human | - | decisions, KiCad review, fab preview, payment |

## Review protocol
1. Builder finishes. You rerun the gate, the tests and the privacy check yourself; a builder's "passes" is a claim, not a result.
2. Start the reviewers in parallel, read-only, each with a scope and the list of what changed: datasheet review per board,
   consistency review across boards, render review per sheet set. Give each the questions that worry you.
3. Hold every fix until all reviews are in: they can touch the same netlist, and one finding can void another.
4. Consolidate into `hardware/REVIEW-<date>.md`: id, rank, where, finding, evidence, proposed fix, cost, decision, status.
   Rank A = wrong or can damage; B = thin margin or a corner; C = drawing, naming, cleanup.
5. Check the findings that drive a decision against the source yourself (open the datasheet page, run the script row).
6. Bring the engineer the decisions: options with cost per unit and a recommendation, numbered, one line each. Change no
   topology, part or value before the answer. Record the answers with their date in the review file and `BOARD.md`.
7. Apply the decided fixes through one builder with the verbatim decisions; one commit per fix; update the status column.
   Unapplied items stay listed with the reason.
8. Second round, cheaper: a mid-size reviewer on exactly what changed, same checklist. Done when no A and no unexplained B remain.
9. Before ordering: the engineer's KiCad review (`hw-fab-order`).

## What the checklist must cover (`references/checklist.md`)
Default states with a partner board absent, corner cases of protection and charging, sleep leakage, switched-rail behaviour,
mating errors, thermal windows, stale text, unverified inputs. Each has found a real fault on a real board.

## Delegating a build job
- The prompt carries: the job and its exit check (a command that prints OK), the paths the agent may change, decisions
  already taken (verbatim, with dates), decisions not to take, the reference designs and datasheets to use.
- One agent, one owner of each file; two agents never edit the same file. Shared tools change only backwards compatibly.
- The agent commits locally after each step; a usage limit or reset can end it at any moment. Resume the same agent with
  its id instead of starting cold. You push after verifying.
- Agents do not edit `CLAUDE.md`, `README` or plan files; they propose the wording. You apply it in the same round, or
  these entry documents stay wrong (after a split they kept naming the old board as active).
- Ask for the final report in the `hw-builder` format: commits, checks as run, open decisions, unverified items.

## Research prompts (small models)
- One question per agent; state the constraints and the answer format. Ask for `page` / `snippet` / `estimate` per number.
- Tell them to open pages, to use the fab stock tool before writing "not on the fab", and to write "not found".
- They miss the supply chain's own language: ask for Chinese-language searches by name (sites in `hw-researcher`).
- Sanity-check every price and spec against a second source; an agent quoted a price 100x too high for one sensor.
- Verify the numbers that drive a decision before they enter a profile or card; treat the rest as leads.
- Web research on how others do it (routing, checks) is allowed when stuck; mark what you could not verify.

## Pitfalls
| Symptom | Cause | Fix |
|---|---|---|
| Review is all style, no faults | reviewer saw the builder's summary | make it rebuild netlists and rerun scripts |
| Findings contradict each other | fixes applied between reviews | hold fixes until all reviews are in |
| Gate OK but a requirement is broken | the check row has no threshold | add the threshold from the requirement (`hw-base`) |
| Work lost at a usage limit | nothing committed | commit per step; resume the agent |
| Entry docs name the old design | agents were told not to edit them, nobody did | apply the proposed wording in the same round |
| Reviewer "confirms everything" | it only read docs | the report must list what it ran itself |
| Reviewer follows the user's wish against the datasheet | wish stated as a rule | follow the datasheet, report the conflict as a decision |
