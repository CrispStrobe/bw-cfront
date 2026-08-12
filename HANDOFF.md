# bw-cfront — session handoff (2026-08-12)

## What this repo is

Two deliverables, both complete:

1. **cToPseudocode.js** — C → pseudocode front end. Lives in sb3-creator,
   developed here. Phase 1 (scheduler inversion) and Phase 2 (corpus-driven)
   done. **512/515 corpus files translate (98.3%).** Six non-translating cases
   fully classified (see below).

2. **avr-compiler/** — FastAPI endpoint wrapping avr-gcc. POST C source →
   {hex, listing, size, version, fcpu, symbols}. The symbols path produces
   the full 004-format debug table (same schema as stc_symtab.py).

3. **avr-examples/** — first wave of 6 Arduino UNO examples (see below).

---

## What was completed this session (2026-08-11 to 2026-08-12)

### Symbols endpoint — 004 format (bb917d3, eccd400)

`_extract_symbols` rewritten from a flat `{name: {addr, type}}` dict to the
full 004 schema matching stc_symtab.py:

```json
{
  "fcpu": 16000000, "device": "atmega328p",
  "scheduler": {
    "bw_ms": {"space": "sram", "addr": 260, "size": 4},
    "tasks": [{
      "name": "bw_task0", "func_addr": 218,
      "state": {"space": "sram", "addr": 258, "size": 2},
      "until": {"space": "sram", "addr": 256, "size": 2},
      "yields": [{"state": 0, "label": "loop_top", "addr": 240}, ...]
    }]
  }
}
```

Sources: `avr-nm` for SRAM + text addresses, `avr-objdump -d -l` for DWARF
line→code-address mapping, C source scanning for `case` labels + `@bw yield`
map + `@bw var` headers. Same drift check as stc_symtab: yield map must agree
with case labels or it refuses.

**Key implementation details:**
- SRAM addresses have `0x800000` AVR linker offset stripped (match avr8js data space)
- Yield `addr` values are **byte** code addresses; avr8js PC is **word** = addr/2
- `bw_ms` is 4 bytes (uint32_t on AVR), not 2 as on 8051
- `case N:` labels generate no DWARF record; forward-scans up to 10 lines for the
  first statement's address
- Uses `avr-objdump -d -l`, NOT `--dwarf=decodedline` — the latter returns zero
  rows on binutils 2.26 even with DWARF-2 (avr-gcc 7.3.0's default)
- `-g` flag added to compile only when `symbols=true` (no effect on release builds)

Verified end-to-end through the HTTP endpoint (two-task cooperative scheduler).

### Integration gap closed (documented in AVR-COMPILE-CONTRACT.md)

The coordinator proved the full chain (bw-board e715cf9):
generateC → avr-gcc → parseIntelHex → avr8js → D13 blinks at 500ms, ADC reads 512 @ 2.5V.
Contract updated from "NOT verified" to "verified" with the evidence.

### AVR examples — first wave (20592ad)

Six examples in `avr-examples/`, each with program.bw + circuit.json + EXPECTED.md:

| id | what it exercises |
|---|---|
| avr01-blink | D13 at 1 Hz, active-high push-pull (opposite to STC12's active-low) |
| avr02-dimmer | pot A0 → PWM brightness D9 |
| avr03-dual-blink | two cooperative scripts, D13+D12 at different rates |
| avr04-serial-pot | ADC print over USART0 (the onSerial path) |
| avr05-button-led | digital input D2 with pull-down, LED on D13 |
| avr06-blink-and-print | the exact pattern proven live: blink + serial ADC |

These live here, not in sb3-creator. Ready to merge into sb3-creator/examples/
when the index.json schema and gallery tests are extended for Arduino targets.

### Handoff, licence, naming rule (3e72024, bb9da67)

HANDOFF.md written with six-case classification and AVR endpoint state.
MPL-2.0 recorded as owner-confirmed (saved to memory too).
Naming rule saved to memory: no "competitor" in files/commits, keep attribution.

---

## The six non-translating cases (longest half-life)

| # | file | class | owner |
|---|---|---|---|
| 1 | `带闹钟…时钟.c` — `=` not `==` | source bug | nobody |
| 2,3 | `WaveForm_Rom.c` — `fopen` assignment-in-condition | out of scope | nobody |
| 4 | `串口控制/main.c` — `buzzc[i]` in for-loop condition | **dialect gap** | sb3-creator |
| 5,6 | ternary inside call arg (2 files) | architectural limit | ours, not worth cost |

**Case 4 is an open cross-repo request.** Filed as `spec-updates/array-subscript-dialect.md`.
Needs `item i of buzzc` in the pseudocode dialect. **sb3-creator has not read it.**

---

## What is NOT done

| item | status | next step |
|---|---|---|
| Automated symbol extraction test | no test compiles via HTTP with symbols:true and asserts the response shape | write a pytest that POSTs a two-task program, checks scheduler.tasks[0].yields has addr values |
| AVR examples in sb3-creator | examples are in bw-cfront/avr-examples, not in the gallery | merge into sb3-creator/examples/, extend index.json with `"device": "arduino-uno"`, update gallery tests |
| Vercel deployment | avr-gcc binary may exceed free-tier | test once, accept or switch to a VPS |
| Arduino library support | bare avr/io.h only | separate decision (LGPL-2.1 obligation) |
| array-subscript-dialect.md unread | sb3-creator session hit limit before seeing it | next sb3-creator session should read spec-updates/ |

---

## What was ruled out and why

| thing | reason |
|---|---|
| `--dwarf=decodedline` for line addresses | returns zero rows on binutils 2.26; `-d -l` works |
| Expression→statement hoisting (ternary in call arg) | costs more than the 2 files it serves |
| `goto` translation | genuinely impossible in structured blocks |
| Arduino library bundling | LGPL-2.1, ~100KB, separate decision |

---

## Licence — settled, do not reopen

**MPL-2.0, owner-confirmed** for bw-cfront, bw-circuit-ui, bw-parts, bw-bundle, sb3-creator.
Why: file-level copyleft, combinable under other terms, §3.3 one-way to GPL/AGPL,
AGPL-in-bundle blocks app-store distribution.

Non-MPL repos are constrained by upstream: ucsim-stc (GPL-2), emu8051-stc (MIT),
brickwright-lite (BSD-3), stc lab (MIT + Apache-2.0 NOTICE).

---

## All commits this session

```
eccd400  app.py: document why -d -l, not --dwarf=decodedline
20592ad  avr-examples: first wave — 6 Arduino UNO examples
cd87431  AVR-COMPILE-CONTRACT.md: document symbols response and close integration gap
2bbdedf  HANDOFF.md: update symbol extraction status after 004-format work
bb917d3  avr-compiler: emit 004-format symbol table matching the 8051 path
bb9da67  HANDOFF.md: record MPL-2.0 as owner-confirmed with reasoning
3e72024  HANDOFF.md: six-case classification, AVR endpoint state, open dialect request
14495a0  avr-compiler: add debug symbol extraction via avr-nm
```
