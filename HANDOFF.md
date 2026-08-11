# bw-cfront — session handoff (2026-08-11)

## What this repo contains

Two things, in order of half-life:

1. **cToPseudocode.js** — the C-to-Brickwright-pseudocode front end, making the
   C target two-way. Lives in sb3-creator but was developed and tested from here.
   Phase 1 (cooperative-scheduler inversion) and Phase 2 (corpus-driven broadening)
   are both done. **512 of 515 corpus files translate (98.3%).**

2. **avr-compiler/** — a FastAPI endpoint that wraps avr-gcc. POST C source, get
   back Intel HEX + listing + size + version + fcpu + optional symbols. Mirrors
   the stc-compiler pattern.

---

## The six non-translating cases and their classification

This is the part with the longest half-life. 3 of 515 files do not translate, and
none are translator bugs.

| # | file | construct | class | owner |
|---|---|---|---|---|
| 1 | `带闹钟…时钟.c` | `if(UpdateTimeFlag=1)` — `=` not `==` | **source bug** | nobody (C is wrong) |
| 2 | `WaveForm_Rom.c` | `if((fp = fopen(…)))` — assignment-in-condition | **out of scope** | nobody (desktop utility, not firmware) |
| 3 | `WaveForm_Rom.c.gbk.c` | same as #2 | **duplicate** | nobody |
| 4 | `串口控制/main.c` | `for(i=0; buzzc[i]!='\0'; i++)` — array subscript in condition | **dialect gap** | **sb3-creator / bw-blocks** |
| 5 | `寻址/IIC.c` | `lcdshow(0,0,(a==0?"y":"n"),1)` — ternary inside call arg | **architectural limit** | ours, not worth the cost (1 file) |
| 6 | `高精度PWM/main.c` | `SetMotoangle(SWdir?angle++:angle--)` — ternary with side effects in call arg | **architectural limit** | ours, not worth the cost (1 file) |

**Cases 1-3**: the translator is correct to refuse. No action.

**Case 4**: filed as `spec-updates/array-subscript-dialect.md`. Needs indexed table
reads (`item i of buzzc`) in the pseudocode dialect. **This request has not been read
by bw-blocks / sb3-creator.** The sb3-creator session hit its limit at 15:50 UTC on
2026-08-11. This is an open cross-repo request with a named owner — do not let it
depend on someone remembering it.

**Cases 5-6**: expression-to-statement hoisting (ternary inside a function call
argument). The fix requires propagating ternary info out of the expression parser
into statement-level code generation, then splitting the call into an if/else with
duplicated call sites. Disproportionate to 2 files. The translator warns honestly
rather than guessing. Deliberately left.

---

## AVR compile endpoint — what exists and what does not

### What exists

- `app.py`: compiles C via avr-gcc, returns hex/listing/size/version/fcpu/symbols
- `runtime/avr_runtime.h`: Timer0 CTC cooperative scheduler, same Duff's-device as STC12
- `AVR-COMPILE-CONTRACT.md`: F_CPU is a contract between compiler and simulator
- `CALLING.md`: recorded (not mocked) response, absence policy documented

### Key decisions and their reasons

- **Determinism claim qualified**: "same source + same flags + **same compiler version**
  = same hex". Not just "same source = same hex". `__DATE__`/`__TIME__` are not used;
  the qualification is the compiler version, which is pinned and reported.
- **`errors` is the discriminator**: if `errors` is null the compile succeeded; if it is
  a string the compile failed. No partial success. This matches stc-compiler.
- **`fcpu` in the response**: the simulator reads it from the compile response, never
  hard-codes it. Same contract shape as the STC12 1T/12T clock.
- **`source: "endpoint"` vs `"local"`**: so tests can assert which path produced the hex.
- **Absence policy**: report loudly, never fall back silently. A green suite that compiled
  locally while the contract went untested is the shape of every gate-that-passes-by-not-
  checking failure.

### What does NOT exist / is NOT verified

- **avr8js integration**: the hex has never been fed into avr8js. The two halves exist
  separately. That test requires bw-board's adapter running.
- **Vercel deployment**: avr-gcc may exceed free-tier function size. Never tested.
- **Arduino library support**: bare `avr/io.h` + `util/delay.h` only. Adding Arduino
  core is a separate decision (LGPL-2.1, ~100KB source).
- **Symbol extraction end-to-end test**: `_extract_symbols` is implemented (avr-nm,
  filters to bw_* symbols, returns `{name: {addr, type}}`) but there is no test that
  compiles a cooperative-scheduler program with `symbols: true` and asserts the response
  contains `bw_task0_state` etc. The function works — it was validated manually against
  avr-nm output — but the assertion is missing.

---

## What was ruled out and why

| thing | why ruled out |
|---|---|
| Expression→statement hoisting for ternary-in-call-arg | costs more than the 2 files it serves; translator warns honestly |
| `goto` translation | genuinely impossible in structured blocks; 3 corpus files, correct to refuse |
| Assignment-in-condition (`fp = fopen(…)`) | valid C but no pseudocode equivalent; out of scope (desktop utility) |
| Arduino library bundling | LGPL-2.1 obligation, ~100KB, separate decision |
| Inflating the translate rate by guessing | standing rule: a file that translates wrongly is worse than one that reports it cannot |

---

## Licence — settled

**MPL-2.0, owner-confirmed.** The owner was asked directly, given MPL-2.0, MIT and
AGPL-3.0 as options with trade-offs, and chose MPL-2.0 explicitly for bw-cfront,
bw-circuit-ui, bw-parts, bw-bundle and sb3-creator.

Why MPL-2.0: requires attribution, keeps improvements to the licensed files open at
file level, permits combination into a larger work under other terms, and section 3.3
leaves the door open to GPL or AGPL later while the reverse would not. The specific
trigger was sb3-creator's relicensing from AGPL-3.0 to MPL-2.0 — brickwright-lite
vendors ten of its files into a BSD-3 tree, and AGPL anywhere in a bundle blocks
app-store distribution.

The licence files appeared in repos via direct ssh commit by the coordinator, which
is why they arrived without explanation. That was a failure to announce, not an
unsettled decision. Do not reopen it.

**Repos that are NOT MPL-2.0** are constrained by upstream, not chosen:

| repo | licence | why |
|---|---|---|
| ucsim-stc | GPL-2.0 | inherited from ucsim |
| emu8051-stc | MIT | inherited from Jari Komppa |
| brickwright-lite | BSD-3-Clause | inherited from upstream |
| stc (lab) | MIT + Apache-2.0 NOTICE | MIT overall; Apache-2.0 notice for two derived examples |

---

## Commits in this session

```
14495a0  avr-compiler: add debug symbol extraction via avr-nm
9da0fde  make compile path visible; document absence policy
16202b3  characterise the six non-translating cases; file case 4 as spec-update
bd80435  verify determinism, document error shape, qualify the claim
3b0810f  avr-compiler: CALLING.md with recorded response — fcpu confirmed
7b18dbe  avr-compiler: cooperative-scheduler variant + AVR runtime header
```
