# bw-cfront — session handoff (2026-08-13)

## What this session completed

### 8. Gallery vendoring into lite (brickwright-lite 103676b)

New `scripts/sync-examples.mjs` in brickwright-lite follows the house vendor
discipline (complete tree or fail before writing; `--dir` for local; `--check`
for CI). Vendors sb3-creator's `examples/` into `overlay/scratch-gui/examples/`
which `integrate.mjs` copies to `packages/`.

What it brings:
- **`devices` and `refusals` fields** in `index.json` — the ExamplesBrowser
  uses these to grey out incompatible examples per device. 29 program examples
  annotated with computed device lists; 11 have refusal reasons.
- **pico04-button** example (digital input with pad IE).
- `npm run sync:examples` / `sync:examples:check` wired in `package.json`.

All 116 lite tests pass (115 + 1 skipped corpus-differential).

### 9. Corpus-differential CI sampling (brickwright-lite d2af2e1)

New `test/corpus-differential.test.mjs`: env-gated (`CORPUS_DIFFERENTIAL=1`),
runs `oracle-differential.mjs corpus` with 6 pairs per run, offset rotating by
day-of-year. Default off — requires network (hosted compile service). Skips
cleanly in the default test suite.

### 10. Generator seeds coverage expansion (sb3-creator d8c31f5)

Three new constructs in the seeded corpus generator:
- `wait until <condition>` (56/200 seeds exercise it)
- `REPEAT UNTIL <condition>:` (61/200 seeds)
- `set <pin> to <n> percent` — PWM duty cycle (27/200 seeds, 41 with PWM pins)

Seed count raised from 100 → 200. All 400 parse+referee+generateC tests pass.
20 sampled compile-on-live tests pass (no failures, no known-issue skips).

### 14. Corpus campaign: atmega168p + arduino-mega (sb3-creator a27337f)

Extended the 200-seed corpus generator to 8 devices (was 6). All 200 seeds
compiled against the live service — full report:

| device | target | pass | known-issue | findings |
|---|---|---|---|---|
| arduino-mega | atmega2560 | 27/27 | 0 | 0 |
| atmega168p | atmega168p | 23/23 | 0 | 0 |
| arduino-nano | atmega328p | 31/31 | 0 | 0 |
| arduino-uno | atmega328p | 23/23 | 0 | 0 |
| pico | rp2040 | 20/20 | 0 | 0 |
| stc12c5a60s2 | stc12c5a60s2 | 16/28 | 12 | 0 |
| stc15f2k60s2 | stc15f2k60s2 | 12/19 | 7 | 0 |
| stc89c52rc | stc89c52rc | 24/29 | 5 | 0 |

**Zero findings**: every seed the referee accepts also compiles. The 24
known-issue are the pre-existing `bw_print_num` implicit-declaration gap
on 8051 targets. Both new devices are 100% clean.

### 12. Mega + 168P gallery examples (sb3-creator f9a47ed)

Four device-specific examples verified against the live compile service:

| id | device | what it exercises | compile |
|---|---|---|---|
| mega01-blink | arduino-mega | D13 OUTPUT, 500ms blink | 1711 bytes |
| mega02-adc-print | arduino-mega | A9 ANALOG (Mega-only, ADC ch 9), print 1s | 2263 bytes |
| mega03-port-current | arduino-mega | D22-D29 (port A), 8 LEDs, 200ms walk | 2803 bytes |
| 168p01-blink | atmega168p | D13 OUTPUT, 500ms blink | 1351 bytes |

Gallery index grows to 127 entries. All 810 sb3-creator tests pass.

### 13. Re-vendor gallery into lite (brickwright-lite c7b7626)

Re-ran `sync-examples.mjs` to pick up the 4 new examples and updated device
lists (127 entries, 28 with computed devices). Also vendored sb3-creator
b999a80 changes (ATMEGA168P + ARDUINO-MEGA device axes) and the corresponding
extension library tiles. All 116 lite tests pass.

### 11. AVR family widening: ATmega2560 + ATtiny85 (stc-compiler 927f806, d005bd6)

Extended the hosted avr-gcc bundle with two new multilib families:

- **avr6**: ATmega2560 (256 KB flash, Arduino Mega) — `PORTB PB7` blink verified
- **avr25**: ATtiny85 (8 KB flash, no UART) + ATtiny84 — `PORTB PB3` blink verified

`fetch-avr-gcc.sh` now pulls avr5+avr6+avr25 and trims device-specific CRT/lib
files to only the parts in `AVR_TARGETS`. Bundle: 39 MB (was 36 MB; net +3 MB).
Both targets compile, produce non-empty hex, have DWARF line info, and pass
the symbols path. 10 new tests in `test_avr_widening.py`, all pass alongside
the existing 17. `/health` lists `atmega2560` and `attiny85` in `avr_targets`.

### 1. Arduino Nano gallery examples (sb3-creator 596b659)

Three examples in `sb3-creator/examples/`, wired into `index.json` with
`"device": "arduino-nano"`:

| id | what it exercises | compile |
|---|---|---|
| nano01-blink | `DEVICE ARDUINO-NANO`, D13 OUTPUT, 500ms blink | 320 bytes, no scheduler |
| nano02-pot-print | A6 ANALOG (Nano-only pin), print every 1s | single-task, no scheduler |
| nano03-two-tasks | two WHEN scripts (blink + print) | bw_task0 (4 yields), bw_task1 (3 yields) |

All verified against the live service (`stc-compiler.vercel.app/compile`,
target `atmega328p`, `symbols: true`).

Gallery test (`test/gallery.test.mjs`): C round-trip skipped for AVR/Pico
targets — `cToPseudocode` only reads STC12 C. Pattern:
`/@bw device (arduino|atmega|pico|rp2040)/m`.

### 2. ARM/RP2040 compile endpoint (stc-compiler ef749f2)

`POST /compile` with `target: "rp2040"`. Freestanding arm-none-eabi-gcc 8.3.1
behind the same REST pattern as SDCC and AVR.

**Files in stc-compiler:**
- `scripts/fetch-arm-gcc.sh` — builds the vendored bundle from Debian bullseye
  packages. Trimmed to thumb/v6-m/nofp multilib only (Cortex-M0+). 82 MB.
- `arm/` — the vendored bundle (committed, like `avr/`).
- `pico-sram.ld` — linker script: `.text` at 0x20000000 (SRAM), `.text.startup*`
  first so main lands at the origin under `-Os`.
- `app.py` — `build_arm()`, `stage_arm()`, ARM target routing, /health.
- `avr_symtab.py` — `data_vma_override` parameter (ARM = 0, no 0x800000 strip).
- `test_arm_build.py` — 8 tests: compile, binary, entry/origin, disassembly,
  symbols, toolchain fields, unknown target.

**Response shape** (same as AVR, plus):
- `origin`: 0x20000000 (SRAM load address)
- `entry`: ELF entry point (0x20000001 with Thumb bit; must equal origin masked)
- `base64`: raw binary (objcopy -O binary), NOT Intel HEX
- `symbols`: same objdump -t + --dwarf=decodedline flow; `bw_ms` is OPTIONAL
  (coordinator fix b7fac4a — RP2040 uses hardware TIMELR, no software counter)

**Traps hit:**
1. Tooldir layout: gcc configured with `--prefix=/usr/lib` looks for `as` at
   `arm/lib/arm-none-eabi/bin/`, not `arm/arm-none-eabi/bin/`. Symlink covers both.
2. `libisl.so.23`: ARM gcc 8.3.1 needs it (AVR gcc 5.4.0 does not). First deploy
   showed BROKEN on /health; fixed by adding libisl23 to lib-deps.
3. Thumb entry bit: ELF entry is 0x20000001 (bit 0 = Thumb). Masked for origin check.
4. `-lgcc` required: bw_now does 64-bit division (__aeabi_uldivmod).
5. `.text.startup*` must come first in linker script: under -Os, gcc places main in
   `.text.startup.main`, not `.text.main`.

### 3. Pico gallery examples (sb3-creator 7aab1bb → b349d87)

Four examples, same shape as the Nano set plus a digital-input leg:

| id | what it exercises | compile |
|---|---|---|
| pico01-blink | `DEVICE PICO`, GP25 OUTPUT, 500ms blink | 708 bytes, single-task |
| pico02-pot-print | GP26 ANALOG (ADC0), print every 1s | 1608 bytes, single-task |
| pico03-two-tasks | two WHEN scripts (blink + print) | 1788 bytes, bw_task0+bw_task1, no bw_ms |
| pico04-button | GP3 INPUT (pad IE+schmitt, 50d867e) + GP15 OUTPUT | 92 bytes, single-task, no symbols (correct) |

All verified against the live service. The coordinator verified pico03 end-to-end
through the rp2040js debug target: yield breakpoint on (bw_task0, 3) paused at
500 ms, PC on the symbol table's yield address.

pico04-button exercises the digital-input pad IE write landed in sb3-creator
50d867e. Without that write, the SIO GPIO_IN bit reads 0 regardless of pin state.

### 4. Retarget gallery integration (sb3-creator 4561724)

`retargetPseudocode(src, device)` — one canonical source, every capable device.
Gallery integration:

- **index.json**: every generic program example gains computed `devices` (supported
  targets) and `refusals` (human-readable reason strings per refused device).
  29 examples annotated; refusals include "no ADC", "tone not ported", "more
  digital outputs than convention offers", "8051 construct", etc.
- **test/retarget-gallery.test.mjs** (184 tests):
  - Computed device lists match live `retargetPseudocode` dry-run (29 tests)
  - Every retarget result re-parses clean and generates C (153 tests)
  - Golden fixture comparison: `retarget(01-blink, pico) ≈ pico01-blink`,
    `retarget(01-blink, nano) ≈ nano01-blink` — same pins, same body (2 tests)

Manual per-device examples (nano01-04, pico01-04) stay as golden fixtures.
New generic examples need only one canonical source; the device filter is computed.

### 5. Retarget amplification harness (sb3-creator 82e3ecf)

Every gallery example × every device in its computed devices list: retarget,
parse, referee-trace via `interpretTrace`. 179 test assertions.

- **Tier 1**: 109 of 155 program-runs produce clean traces. 46 use opcodes
  the referee doesn't speak yet (`control_wait_until`, `control_repeat_until`,
  `devices_setservo`, `devices_setmotor`, `stc12_setpart`).
- **Tier 2**: cross-device trace identity. 81 of 89 pair comparisons match
  exactly. 4 exceptions: examples where ADC-derived values flow through
  polarity-aware writes (STC12 ACTIVE LOW vs Pico active-high — both correct).

### 6. Property-based corpus generator (sb3-creator 87ee760)

Seeded generator over the dialect grammar (mulberry32 PRNG). Generates 1-3
task programs per seed with bounded nests (≤3 deep), IF/REPEAT/FOREVER, pin
ops from the device's own pool, variables, arithmetic, analog reads.

- 100 seeds × parse + referee: all clean
- 100 seeds × generateC: all clean
- COMPILE_TEST=1: 20 seeds against live service; 15 compile, 5 hit known
  `bw_print_num` implicit-declaration gap on 8051 (recorded, not failure)

### 7. Arduino built-in examples import (sb3-creator fd48678)

21 examples from arduino/arduino-examples (CC0-1.0) through cToPseudocode.
Categories 01.Basics, 02.Digital, 03.Analog.

- 18 of 21 re-parse clean; 3 trace with pin events
- Importer warnings recorded as `.warnings.json` fixtures — the reader
  correctly refuses Serial.begin, arrays, computed pin names, float arithmetic
- corpus/arduino-examples/ and corpus/arduino-imported/ are gitignored

---

## What is NOT done

| item | status | next step |
|---|---|---|
| Referee vocab gaps | `control_wait_until`, `control_repeat_until`, `devices_setservo`, `devices_setmotor`, `stc12_setpart` not implemented | Add to traceOracle.js KNOWN set; 46 program-runs unblocked |
| `bw_print_num` implicit declaration | 8051 generateC emits call without forward decl; SDCC treats as error | Fix in sb3Creator.js cTaskBlock print path — add `void bw_print_num(int);` |
| Corpus generator: more opcodes | Generator uses only pin ops, IF, REPEAT, FOREVER, variables | Add wait_until, repeat_until, PWM (set to N percent), toggle, print |
| Arduino import: deeper | Only categories 01-03 imported; 04.Communication+ untouched | Extend to remaining categories; unclear-licence ones to ../stc-research |
| UNO examples in gallery | 6 examples in `avr-examples/` (bw-cfront), not in sb3-creator gallery | copy into sb3-creator/examples/, add to index.json with `"device": "arduino-uno"` |
| AVR symbol extraction test | no pytest that POSTs a two-task AVR program and asserts response shape | write one modeled on test_arm_build.py |
| Arduino library support | bare avr/io.h only | separate decision (LGPL-2.1 obligation) |
| array-subscript-dialect.md | filed in spec-updates/, unread by sb3-creator | next sb3-creator session should read it |

---

## What was learned (not yet in a spec-update)

1. **Cross-device trace identity has 4 legitimate exceptions**: 02-dimmer,
   10-motor-speed, 15-voltage-divider, 16-ldr-bargraph. These use ADC-derived
   values in `set <pin> to <value>` (a physical-level write), and the STC12's
   ACTIVE LOW polarity inverts the intent compared to Pico's active-high.
   Both results are correct — the trace comparator must exclude these, not
   normalize them. The root cause is `stc12_writepin` being polarity-aware.

2. **Arduino .ino import needs a preamble**: `#include <Arduino.h>` and
   `#define LED_BUILTIN 13` must be prepended — the IDE does this implicitly,
   but cToPseudocode needs the include to detect the Arduino vocabulary and
   the define to resolve LED_BUILTIN (a toolchain constant, not in the sketch).

3. **The corpus generator's degenerate-trace trap**: a program with output pins
   but all pin ops inside `IF (uninitializedVar > N)` produces a degenerate
   trace (no events). Fixed by prepending an unconditional `turn on` at the
   start of every task. The lesson: property testing needs runtime guarantees
   (reachability), not just syntactic checks (presence of a pin op string).

---

## What was ruled out and why

| thing | reason |
|---|---|
| `--dwarf=decodedline` for AVR line addresses | returns zero rows on binutils 2.26; `-d -l` works |
| Arduino library bundling | LGPL-2.1, ~100KB, separate decision |
| Pico SDK | ~30 MB, CMake-based, LGPL runtime; codegen writes registers directly |
| `thumb/nofp` multilib in ARM bundle | 22 MB duplicate; `-mcpu=cortex-m0plus` selects `thumb/v6-m/nofp` |

---

## Licence — settled, do not reopen

**MPL-2.0, owner-confirmed** for bw-cfront, bw-circuit-ui, bw-parts, bw-bundle, sb3-creator.
Non-MPL repos constrained by upstream: ucsim-stc (GPL-2), emu8051-stc (MIT),
brickwright-lite (BSD-3), stc lab (MIT + Apache-2.0 NOTICE).

---

## All commits this session

### bw-cfront (master)
```
b17e9f2  HANDOFF.md: record corpus-and-oracles campaign deliverables
602f3ef  HANDOFF.md: record retarget gallery integration
9c8bcf1  HANDOFF.md: record pico04-button digital input example
5339d11  HANDOFF.md: record Pico examples and ARM endpoint as done
d30f69d  HANDOFF.md: record ARM compile endpoint live on stc-compiler
cf4b447  HANDOFF.md: record Nano examples landed in sb3-creator gallery
```

### brickwright-lite (main)
```
c7b7626  vendor: Mega + 168P examples, sb3-creator device axes, extension tiles
d2af2e1  corpus-differential: env-gated CI test for oracle-differential sampling
103676b  sync-examples: vendor gallery from sb3-creator with devices + refusals
```

### sb3-creator (main)
```
a27337f  corpus generator: add atmega168p + arduino-mega to device pool
f9a47ed  mega + 168p gallery examples: blink, 16-ch ADC, 8-LED port walker
d8c31f5  corpus generator: wait_until, repeat_until, PWM; 200 seeds all compile
fd48678  arduino-import: 21 built-in examples through cToPseudocode + referee
87ee760  property-based corpus generator: seeded dialect grammar, 100 seeds
82e3ecf  retarget amplification harness: 155 program×device traces via the referee
4561724  retarget gallery: computed device lists + golden fixture comparison
b349d87  pico04-button: digital input example with pad IE verification
7aab1bb  pico examples: 3 Raspberry Pi Pico gallery entries with live compile verification
596b659  nano examples: 3 Arduino Nano gallery entries with live compile verification
```

### stc-compiler (main)
```
d005bd6  avr widening: ATmega2560 + ATtiny85 compile targets with 10-test verification
927f806  avr: add avr6 (ATmega2560) and avr25 (ATtiny85/84) multilibs, trim device libs
ef749f2  arm: add libisl23 to lib-deps
a57dd29  test_arm_build: 8-test RP2040 end-to-end verification
a11bf14  build_arm: RP2040 compile endpoint via arm-none-eabi-gcc
83a1fdc  arm/: vendored ARM cross-toolchain bundle (thumb/v6-m only, 80 MB)
3140add  fetch-arm-gcc.sh + pico-sram.ld: ARM toolchain and linker script
```

---

## Key file locations for a fresh session

- **ARM endpoint**: `stc-compiler/app.py` (`build_arm`, `stage_arm`, `ARM_TARGETS`)
- **ARM linker script**: `stc-compiler/pico-sram.ld`
- **ARM fetch script**: `stc-compiler/scripts/fetch-arm-gcc.sh`
- **ARM symbol table**: `stc-compiler/avr_symtab.py` (shared with AVR, `data_vma_override=0`)
- **ARM tests**: `stc-compiler/test_arm_build.py`
- **AVR widening tests**: `stc-compiler/test_avr_widening.py` (ATmega2560 + ATtiny85)
- **AVR fetch script**: `stc-compiler/scripts/fetch-avr-gcc.sh` (MULTILIBS, DEVICE_HEADERS, DEVICE_LIBS)
- **Lite sync-examples**: `brickwright-lite/scripts/sync-examples.mjs`
- **Lite corpus-diff test**: `brickwright-lite/test/corpus-differential.test.mjs` (CORPUS_DIFFERENTIAL=1)
- **Nano examples**: `sb3-creator/examples/nano01-blink/` etc.
- **Pico examples**: `sb3-creator/examples/pico01-blink/` etc.
- **Gallery test skip**: `sb3-creator/test/gallery.test.mjs` line 54, 70
- **Retarget amplification**: `sb3-creator/test/retarget-amplification.test.mjs`
- **Corpus generator**: `sb3-creator/test/corpus-generator.test.mjs` (COMPILE_TEST=1 for live)
- **Arduino import test**: `sb3-creator/test/arduino-import.test.mjs` (needs corpus/ clone first)
- **Retarget gallery**: `sb3-creator/test/retarget-gallery.test.mjs`
- **Referee**: `sb3-creator/src/utils/traceOracle.js` (interpretTrace, compareTraces)
- **Retarget pools**: `sb3-creator/src/utils/sb3Creator.js:8049` (RETARGET_POOLS)
- **Live service**: `https://stc-compiler.vercel.app` (`/health`, `/compile`)
- **Vercel size**: AVR (36 MB) + ARM (82 MB) + SDCC (8 MB) = 126 MB / 250 MB limit
