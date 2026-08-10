# bw-cfront

The **C front-end** for the BrickWright dialect: the direction that reads C
*back* into blocks, rather than emitting it.

This repository holds the plan and the results. **The implementation does not
live here** — it was written into the repositories that own the code it
touches:

| Where the work landed | What |
|---|---|
| [`sb3-creator`](https://github.com/CrispStrobe/sb3-creator) | the inverter itself, and the round-trip tests |
| [`stc12c5a60s2-lab`](https://github.com/CrispStrobe/stc) | the example corpus and the gallery entries |

So this repo is a record, not a library. There is nothing here to install.

## What was actually established

`PLAN.md` carries the detail. The short version:

- **98.3 %** of the measured corpus translates. The remaining cases are
  characterised individually, and **none of them are translator bugs** — they
  are source-language constructs with no block equivalent, plus three defects
  in the source programs themselves.
- The cooperative-scheduler inversion works: the `switch (task_state)` state
  machines that `generateC` emits for multi-script projects are recognised
  structurally and recovered back into `FOREVER`, `REPEAT n`,
  `REPEAT UNTIL`, and `wait` blocks.
- The C round-trip is 5/5 with a symmetry test enforcing it.
- 20 pure-circuit examples exist with computed expectations — current, voltage
  and brightness — rather than placeholder text.

## What it does not establish

Nothing here has run on real silicon. Translation correctness means the block
program and the C program agree under two emulators, which is **category 2b**
in this project's evidence scale — not proof that either matches hardware. The
bench sessions named in the `stc` repo's runbook are what would settle that.

Coverage percentages are against the corpus that was measured, not against C
in general. A construct nobody wrote is not a construct that translates.

## Licence

MPL-2.0 — see [LICENSE](LICENSE).
