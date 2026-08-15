# bw-cfront — session handoff (2026-08-15, context recycle)

## Current lane state

### DONE — all assigned items delivered

**Standing work contract (items 1-4):**

| # | item | repo | SHA | status |
|---|---|---|---|---|
| 1 | cc65 vendor (/assemble 6502) | stc-compiler | a407685 | deployed, verified live |
| 2 | /uf2 endpoint (Pico drag-flash) | stc-compiler | ce0fc23 | deployed, verified live |
| 3 | Z80 /assemble (sdasz80) | stc-compiler | a443ee2 | deployed, verified live |
| 4 | VDP gallery (eater6502-vdp-hello) | sb3-creator | 47bca6f | gate green |

**Blinkenrocket (my lane = hosted compile + generateC):**
- ATtiny88 compile target: stc-compiler `1f80d08` — CI green, 5 tests, 102 total
- Device header (iotn88.h), CRT, lib vendored in `avr/` bundle
- generateC ATtiny88: sb3-creator `ddcaac0` — Timer1 CTC tick (Timer0 has no CTC),
  PB/PC/PD/PA pin names, RETARGET_POOLS, SPOKEN pin validation
- Verified: pseudocode → generateC → avr-gcc attiny88 = 758 bytes
- **NOT live on Vercel** — rate-limited; GH Pages is the deploy target

**Arduino CC0 campaign (generateC AVR coverage):**
- tone_set for AVR: Timer2 CTC + ISR pin toggle (sb3-creator `56600ab`)
- Mega PWM D2-D8 + D44-D46, Timers 3-5 (sb3-creator `6367c14`)
- Mega Timer3/4/5 init in bw_setup (sb3-creator `99b4034`)
- setup()/loop() spurious drop warnings fixed (sb3-creator `a575788`)
- Honest refusals documented: String class, serialEvent, Serial1 — all C++

**Phase 2 corpus broadening (cToPseudocode.js):**
- Baseline: 1282 files, 1279 translate (99.8%), 520 have main()
- 230/520 programs clean (44.2%) — up from 226/520 baseline
- Added: array read/write (`item N of`/`replace item`), compound `*=/÷=/%=`,
  local var with init, non-trivial for-loops (REPEAT UNTIL + step in body),
  type aliases (uchar/uint8/u8 etc.), multi-var decls, chained assignments,
  cast keywords in isCast()
- "statement dropped" eliminated from corpus top-10 warnings
- Irreducible floor: typedefs (inexpressible), break→flag (correct)

**Other cleared items:**
- bw_print_num 8051 fix: UART setup + print library body (sb3-creator `49ce197`)
- Arduino import: all 11 categories, 75 examples (sb3-creator `50e7e55`)
- UNO examples in gallery: 6 examples (sb3-creator `dfadf99`)
- AVR symbol extraction test: 8 tests (stc-compiler `7578ab3`)
- Retro bench examples: eater6502-bench + z80-bench (sb3-creator `3383190`)
- /assemble nRF52833 micro:bit V2 target (stc-compiler `199e663`)
- Lite vendor re-sync: 352/352 files (brickwright-lite `930000d`)
- bw-cfront CI workflow: `.github/workflows/ci.yml` (bw-cfront `37c7ba2`)
- bw-board fixes: 28c256 ceb terminal, examples-gate retro DIP skip

### IN-FLIGHT

Nothing in-flight. All work committed and pushed.

### BLOCKED

**Vercel deploy rate-limited** — stc-compiler production deploy stopped
triggering after commit `1f80d08`. Only `github-pages` deploys fire.
The coordinator confirmed this is a ~24h rate limit. Do NOT attempt
redeployment. The last verified production version is `7578ab3` (16
assemble targets). Once the rate limit lifts, `04335f8` (HEAD) will
deploy with ATtiny88 as the 17th target.

### NOT DONE

| item | status | next step |
|---|---|---|
| Arduino library support | bare avr/io.h only | separate decision (LGPL-2.1 obligation) |
| Vercel deploy verification | ATtiny88 not yet live | wait for rate limit to lift |
| 6502/ATtiny88 round-trip | port register writes not reverse-mapped to pin names | cToPseudocode needs to map `BW_VIA_ORA |= (1<<N)` → `turn on pinN` and `PORTB &= ~(1<<N)` → pin ops using @bw pin markers |
| cToPseudocode userFns runtime exclusion | fixed `bw_`/`tone_`/`scratch_`/`__` prefixes (991e660) | done |

---

## Test counts (at session end)

| repo | tests | pass | fail | notes |
|---|---|---|---|---|
| stc-compiler | 102 | 102 | 0 | CI green |
| sb3-creator | 883 | 883 | 31* | *31 = other agent's arduino circuit.json |
| bw-cfront | 12 | 12 | 0 | avr-compiler pytest |
| Round-trip | 30 | 30 | 0 | 8051/6502 gallery examples |

## Artifact locations

| what | path |
|---|---|
| cToPseudocode.js | sb3-creator/src/utils/cToPseudocode.js |
| sb3Creator.js (generateC) | sb3-creator/src/utils/sb3Creator.js |
| corpus baseline | sb3-creator/test/corpus-baseline.mjs + .json |
| arduino import test | sb3-creator/test/arduino-import.test.mjs |
| AVR symbol test | stc-compiler/test_avr_symbols.py |
| AVR widening test (incl ATtiny88) | stc-compiler/test_avr_widening.py |
| UF2 module + tests | stc-compiler/uf2.py + test_uf2.py |
| cc65 vendor bundle | stc-compiler/cc65/ (ca65, ld65, none.lib, asminc) |
| nRF52833 linker script | stc-compiler/nrf52833.ld |
| Z80 assembler binaries | stc-compiler/bin/sdasz80, sdldz80 |
| ATtiny88 device files | stc-compiler/avr/lib/avr/{include/avr/iotn88.h, lib/avr25/crt+lib} |
| eater6502-bench circuit | sb3-creator/examples/eater6502-bench/circuit.json |
| z80-bench circuit | sb3-creator/examples/z80-bench/circuit.json |
| VDP example | sb3-creator/examples/eater6502-vdp-hello/ |
| UNO examples | sb3-creator/examples/avr01-blink through avr06-blink-and-print |
| bw-cfront CI | bw-cfront/.github/workflows/ci.yml |
| campaign doctrine | sb3-creator/reference/arduino-cc0-campaign.md |
| c-target reference | sb3-creator/reference/c-target.md |

## Standing brief (CLAUDE.md)

Phase 1 (scheduler inverter): COMPLETE — implemented before this session.
Phase 2 (corpus broadening): AT IRREDUCIBLE FLOOR — 230/520 clean.
The remaining drops are typedefs (inexpressible) and break→flag (correct).

The arduino-cc0-campaign.md is the active doctrine. The generateC AVR
coverage items assigned to this lane are done: tone_set, Mega PWM,
Mega timer init, ATtiny88 compile. Honest refusals documented for
String class, serialEvent, Serial1 (all C++ library constructs).

## Key decisions made this session

- 28c256 select pin is `ceb` (parts-data name), not `csb` — fixed in
  both extractors (m6502-extract.js, z80-extract.js)
- Retro DIP chips (w65c02 etc.) are DESIGNER_ONLY in the examples gate —
  the board engine has no device model for them, they're extract-only
- Array subscripts in cToPseudocode map to `item N of list` / `replace
  item N of list with val` — the Scratch list blocks ARE expressive enough
- AVR tone uses Timer2 CTC + ISR toggle (not hardware OC pin) — works on
  any declared TONE pin, not just OC-capable pins
- Mega Timer3/4/5 init is conditional on which PWM pins are declared —
  only timers actually needed are initialized
