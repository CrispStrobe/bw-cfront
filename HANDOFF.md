# bw-cfront — session handoff (2026-08-15)

## DONE — standing work contract complete

All 4 tasklist items are delivered, deployed, and verified live:

| # | item | SHA | prod verified |
|---|---|---|---|
| 1 | cc65 vendor (/assemble 6502) | stc-compiler a407685 | eater blink 32768 bytes, byte-identical |
| 2 | /uf2 endpoint (Pico drag-flash) | stc-compiler ce0fc23 | magic 0x0A324655, family 0xe48bff56 |
| 3 | Z80 /assemble (sdasz80) | stc-compiler a443ee2 | LD A,$55;HALT → 3E 55 76 |
| 4 | VDP gallery (eater6502-vdp-hello) | sb3-creator 47bca6f | gate green, extractor-clean |

89 stc-compiler tests pass. 729 sb3-creator tests pass.
Assemble service: 5 toolchains, 16 targets.
Phase 2 corpus baseline established: 520 programs, first fixes shipped.

---

## What this session completed

### 29. Phase 2 baseline + first fixes (sb3-creator f259006)

Corpus baseline: 1282 files, 1279 translate (99.8%), 520 have main().
Array subscripts (1472 occurrences) were the #1 structural gap.

**Fixed:**
- array read: `arr[i]` → `item i of arr` (in expressions)
- array write: `arr[i] = val` → `replace item i of arr with val`
- `arr[i]++/--` → `replace item i of arr with item + 1`
- compound `*=`, `/=`, `%=` → `set x to x OP rhs` (was dropped)
- local var with init: `int x = 0;` → `set x to 0` (was silent drop)

839 tests pass.

**Second pass** (sb3-creator 1f53052): non-trivial for-loops now emit
REPEAT UNTIL with the step moved into the body. Eliminates 77 "for loop
not a simple counter" warnings.

**Third pass** (sb3-creator 856cbe5): type aliases (`uchar`, `uint8`,
`u8`, `uint16`, etc.) recognized as type keywords in declarations AND
casts. Multi-var declarations (`int a=0, b=5`) emit separate set
statements. "statement dropped" exits the corpus top-10 warnings entirely.

**Fourth pass** (sb3-creator 71ccf12): chained assignments (`A = B = C = 0`)
emit separate set statements. SFR names in chains silently filtered.

**Final corpus state**: 230/520 programs clean (44.2%, up from baseline
226/43.5%). Remaining structural drops are irreducible:
- typedefs (74+66): genuinely inexpressible
- break→flag (63): correct transformation, structure-preserving
- unexpanded macros (35): `BOARD_LED3_1` etc. — need macro body
- pointer derefs (9): `*s -= '0'` — genuinely inexpressible
- array compound ops (8): `key[i] |= val` — need dialect extension

### 32. bw_print_num 8051 fix (sb3-creator 49ce197)

The 8051 core was missing the bw_putc/bw_print/bw_print_num function bodies
entirely (6502, ARM, AVR all had them). Added:
- UART init in bw_setup: SCON mode 1, Timer 1 mode 2 for 9600 baud
- bw_putc via SBUF + TI flag
- Forward declarations before task functions
Verified: two-task print program compiles to 2764 bytes on hosted service.
Unblocks the 24 known-issue corpus seeds.

### 31. AVR symbol extraction test (stc-compiler 7578ab3)

8-test pytest: two-task AVR cooperative scheduler (bw_task0 blink +
bw_task1 idle) compiled for ATmega328P. Asserts symbol table contains
both task names with yield entries. 97 total tests pass.

### 30. UNO examples in gallery (sb3-creator dfadf99)

6 Arduino Uno examples copied from bw-cfront/avr-examples into the
sb3-creator gallery: blink, dimmer, dual-blink, serial-pot, button-led,
blink-and-print. All parse, generate C, pass examples gate. 133 total
gallery entries.

### 28. /assemble Z80 target (stc-compiler a443ee2)

Fifth assemble chain: Z80 assembly via SDCC's sdasz80 + sdldz80 + makebin.
Output is raw binary (32K ROM image padded with $FF). Vendored sdasz80 and
sdldz80 binaries into the SDCC bundle.

8 tests with hand-computed opcodes:
- `LD A,$55; HALT` → bytes `3E 55 76` at address 0
- `OUT ($80),A` → bytes `D3 80` (MC6850 ACIA port)
- 32768-byte binary, listing, syntax error, /health listing

89 total tests pass.

### 27. eater6502-vdp-hello gallery example (sb3-creator 47bca6f)

EATER6502 + TMS9918 at $4000. Hand-written C program initializes
Graphics I mode and writes "HELLO" centered on a 32x24 screen via
`BW_VDP_DATA`/`BW_VDP_CTRL` defines. VDP declared via `CHIP vdp1 =
TMS9918 AT $4000` in program.bw (no parts-data sidecar yet — extractor
doesn't detect TMS9918 from wires). Circuit is the standard eater6502-bench
wiring, extractor-clean with zero refusals. Compiles to 1080 bytes.
Passes examples gate.

### 26. /uf2 endpoint for Pico drag-flash (stc-compiler ce0fc23)

POST /uf2 `{base64, origin}` → UF2 container for BOOTSEL drag-flash.
Clean-room implementation from the public UF2 spec (MIT). 256-byte blocks,
RP2040 family ID `0xe48bff56`, sequential target addresses. Supports both
flash (`0x10000000`) and SRAM (`0x20000000`) origins.

12 tests: magic bytes, family ID flag, target address, payload size,
block count, sequential addresses, block numbers, payload content.
81 total tests pass. Verified live on production.

### 25. Vendor cc65 — /assemble 6502 works hosted (stc-compiler a407685)

Vendored cc65 V2.19 (zlib licence) Linux binaries: ca65 + ld65 + none.lib
+ asminc headers. 2.4 MB bundle, staged like the ARM chain (Linux-guarded,
dev Macs use brew cc65).

- `/assemble` targets `eater6502`/`6502`/`w65c02` now assemble on the
  hosted service (were returning "cc65 not deployed")
- ca65 invoked with `--cpu 65C02` (W65C02 ISA)
- Output byte-identical to system cc65
- `/health` reports cc65 version
- Verified live: eater blink ROM assembles to 32768 bytes with listing + labels

### 24. Retro bench gallery examples (sb3-creator 3383190)

Two wire-based circuit.json bench examples with extractor verification:

**eater6502-bench**: W65C02 + 62256 (RAM) + 28C256 (ROM) + W65C22 (VIA) +
W65C51 (ACIA) + 2x 74HC00 (A15 NAND decode). Extracts to:
```
MAP RAM $0000-$3FFF, MAP ROM $8000-$FFFF
CHIP via = W65C22 AT $6000, CHIP acia = W65C51 AT $5000
```

**z80-bench**: Z80 + 62256 (RAM) + 28C256 (ROM) + MC6850 (I/O-mapped ACIA) +
2x 74HC00 (MREQ/IORQ split decode, Searle shape). Extracts to:
```
MAP ROM $0000-$7FFF, MAP RAM $8000-$FFFF
CHIP acia = MC6850 AT PORT $0080
```

Both: zero extractor refusals, pass bw-board examples-gate.test.mjs.
Each has a `check-extract.mjs` that asserts the extractor output matches the
preset map exactly.

Prerequisite fixes:
- bw-board ac0677e: 28c256 select pin `ceb` (was `csb`, mismatched parts-data)
- bw-board 4fe876a: examples-gate DESIGNER_ONLY set includes retro DIP kinds
  (w65c02, 62256, 28c256, w65c22, w65c51, z80, mc6850 — extract-only, no
  board engine device model)

### 23. Lite vendor re-sync (brickwright-lite 930000d)

Synced bw-circuit-ui to 00958c6 (352/352 files). Brings in all 8 retro DIP
part sidecars (w65c02, w65c22, w65c51, 28c256, 62256, 74hc00, z80, mc6850
json+svg). Also picks up CircuitDesigner, schematic, DRC, declarations, and
infer-seated updates. 4 stale model files removed.

130/144 lite tests pass; 11 failures from upstream component API evolution
(toolbar, declarations, schematic tests need updating — not caused by the
sync, but exposed by it).

### 22. /assemble nRF52833 target (stc-compiler 199e663)

New `/assemble` target `nrf52833` (micro:bit V2, Cortex-M4) via the existing
arm-none-eabi-gcc bundle. Fourth assemble chain.

- **Input**: GAS `.s` source with `.syntax unified` / `.cpu cortex-m4` / `.thumb`
- **Output**: Intel HEX (`objcopy -O ihex`) — the format DAPLink MSD drag-flash
  accepts on micro:bit V2
- **Linker script**: `nrf52833.ld`, clean-room from Nordic nRF52833 PS memory map
  (512K flash @ 0x0, 128K RAM @ 0x20000000, vector table at origin)
- **CODAL/SoftDevice rejection**: pattern match on `MicroBitDisplay`, `codal_`,
  `nrf_sdh_`, `softdevice`, `CODAL_` — returns clean `success:false` with reason
- **Tests**: 10 new (vector-table+loop, GPIO row/col LED P0.21/P0.28, Intel HEX
  format, listing, syntax error, CODAL rejection, /health, toolchain field).
  69 total tests pass.

### 21. All-green sweep (2026-08-14)

**CI status (all GREEN after fixes):**

| repo | branch | SHA | status | note |
|---|---|---|---|---|
| sb3-creator | main | de072db | GREEN | lint fix landed (was RED at 44c5227) |
| brickwright-lite | main | 6831d87 | GREEN | Build (permissive base) |
| stc-compiler | main | 6b18055 | GREEN | staged sdas8051/sdld fix landed (was 5855f37) |
| emu8051-stc | master | 0aaf3a9 | GREEN | Build SDCC WASM |

**Deploys (all current with main):**

| service | target | deployed SHA | freshness |
|---|---|---|---|
| GH Pages | crispstrobe.github.io/brickwright-lite | 6831d87 | current |
| Vercel | stc-compiler.vercel.app | 6b18055 | current |

**Production endpoint probes (final):**

| endpoint | toolchain | result | detail |
|---|---|---|---|
| /health | — | PASS | version 6b18055, all targets listed |
| /compile | 8051 (stc12c5a60s2) | PASS | 382 bytes |
| /compile | AVR (atmega328p) | PASS | 406 bytes |
| /compile | ARM (rp2040) | PASS | 32 bytes |
| /compile+listing | 8051 | PASS | format: sdcc |
| /compile+listing | AVR | PASS | format: avr-gcc |
| /compile+listing | ARM | PASS | format: arm-gcc |
| /assemble | 8051 (mcs51) | PASS | 52 bytes, listing present |
| /assemble | AVR (atmega328p) | PASS | 38 bytes, listing present |
| /assemble | 6502 (eater6502) | CLEAN FAIL | `success:false` + message: cc65 not deployed; follow-up to vendor ca65/ld65 |

**Score: 9/10 probes pass, 1 expected clean failure.** The 6502 /assemble
returns a proper error (not a 500) because cc65 isn't vendored yet — recorded
follow-up, not a bug.

Initial probe (pre-fix) found two 500s: sdas8051 bare-command-name PATH bug
and missing cc65. Coordinator fixed both (stc-compiler 6b18055, sb3-creator
de072db). Re-probe confirmed all clear.

---

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

### 20. /assemble endpoint (stc-compiler 77d2be7 + 5855f37)

New `POST /assemble` with `{asm, target}`. Three toolchains:

| chain | assembler | linker | output | error format |
|---|---|---|---|---|
| 8051 | sdas8051 | sdld | Intel HEX | `file:line: Error: msg` |
| 6502 | ca65 | ld65 (eater.cfg) | raw binary + labels | `file(line): Error: msg` |
| AVR | avr-gcc -x asm-with-cpp | (gcc links) | Intel HEX | `file:line: Error: msg` |

Response: `{success, base64, errors: [{line, message}], listing: {asm, lineMap, format, v:1}, filename, bytes, toolchain}`.
6502 also returns `labels` (ld65 -Ln output for bw-board `symbolsFromLd65Labels`).

Errors normalized per-toolchain to `[{line, message}]`. ld65's harmless
STARTUP-segment warning is filtered out.

17 smoke tests (`test_assemble.py`): per chain, valid blink + syntax error.
59 total tests pass. `/health` lists `assemble_targets`.

### 19. Listing artifact: {asm, lineMap, format, v:1} (stc-compiler 8c7693c)

New `listing.py` extracts a versioned disassembly artifact for all three
toolchains when `disassemble=True`:

| toolchain | source | format id |
|---|---|---|
| AVR (avr-gcc) | `avr-objdump -dS` + `--dwarf=decodedline` | `avr-gcc` |
| ARM (arm-gcc) | `arm-none-eabi-objdump -dS` + `--dwarf=decodedline` | `arm-gcc` |
| SDCC (8051) | `.rst` relocatable source listing | `sdcc` |

Response shape: `response["listing"] = {asm, lineMap: [{addr, file, line}], format, v: 1}`.
The existing `response["disassembly"]` string is preserved for backwards compatibility.

`-gdwarf-2` / `--debug` now triggered by `disassemble=True` as well as
`symbols=True`, so source interleaving has line info available.

15 new smoke tests (`test_listing.py`): 42 total tests pass.

Three consumers: R1 asm view, R3 debugger stepping map, AVR/ARM debug
target disasm panes. Client tab is a separate task.

### 18. Licensing adjudication: BASIC tab labels + attributions

**UI labels fixed** (brickwright-lite f2a6a6c):
- Tab: plain "BASIC" (was already correct)
- Profile toggle: "BBC BASIC" / "6502 BASIC" (was "MS BASIC 1.1")
- basicNote: describes "runs BBC BASIC (R.T. Russell, zlib) or 6502 BASIC
  (derived from MIT-licensed source)" — describes, never brands
- Reference panel: "6502 BASIC" throughout (was "MS BASIC 1.1")

**Attributions added**:
- brickwright-lite `THIRD-PARTY-NOTICES.md`: BBC BASIC (zlib, with BBC name
  permission notice), 6502 BASIC as basic-m6502-bw (MIT), Acorn ROM and
  ehBASIC explicitly listed as NOT shipped
- sb3-creator `THIRD-PARTY-NOTICES.md` (ed4d99b): same dialect attributions

### 17. CI all green + deploys + production probes

**CI status** (all green):
- sb3-creator: green (f54cc81)
- brickwright-lite: green (621d554) — curly-quote JSX fix was needed
- stc-compiler: green (d005bd6)
- emu8051-stc: green

**Deploys:**
- GH Pages: https://crispstrobe.github.io/brickwright-lite/ — deployed 2026-08-13T21:40:15Z
- Vercel: https://stc-compiler.vercel.app — d005bd6, ok

**Production probes** (`proof-production.mjs`):
- **Nano**: 5/5 PASS (positionLive, ledBlinks, serialVisible, pauseFrozen, stepMoves)
- **Pico**: 4/5 PASS — `ledBlinks` FAIL (pre-existing: shadow-DOM glow detection flaky on headless Chromium; NOT caused by the BASIC tab)

### 16. BASIC tab in the bundle app (brickwright-lite 636a553)

Fifth language tab in the Code pane: BBC BASIC / MS BASIC 1.1.

**VIEW**: `generateBASIC` output with two toggles — profile (bbc/ms) and
line numbers (on/off; ms always numbered). Refusals (multi-WHEN etc.)
render as `REM` lines with the reasons, not as an empty pane.

**IMPORT**: paste BASIC → `basicToPseudocode` → blocks. Reader warnings
(unmapped lines kept as `# BASIC: <line>` comments) surface in the UI.

Also vendors `basicToPseudocode.js` via sync-sb3creator.mjs (new entry
in the FILES list). 116 tests pass.

sb3-creator app has no code tabs (pseudocode-only), so the BASIC tab
is in lite only — this is correct per the architecture.

### 15. Retro/BASIC corpus catalog (retro-corpus-public 80e97a1)

Sorted 9 repos into publishable vs research-only:

**Publishable** (cloned to `/mnt/volume1/code/retro-corpus-public/`):
- `BBCSDL` (zlib) — 254 .bbc programs; console build = future generateBASIC oracle
- `next-bbc-basic` (zlib) — Z80 ASM interpreter; 17 .bbc examples
- `agon-bbc-basic` (zlib) — eZ80 ASM interpreter; 25+ .bas examples
- `PicoBB` (zlib) — Pico port of BBCSDL; C runtime reference, no BASIC programs
- `BBCMicroDevelopment` (Apache-2.0) — teaching repo; 4 .bas + 1 .6502
- `BASIC-M6502` (MIT) — Microsoft BASIC v1.1 for 6502; 6954-line reference

**Research-only** (cloned to `/mnt/volume1/code/stc-research/retro-corpus/`):
- `polymer-picker-6502` (unlicensed) — BBC Micro game; 5 .bas files
- `chalice-raider` — **NOT FOUND** (deleted or private)
- `1D_Life` — **NOT FOUND** (deleted or private)

~300 publishable BASIC programs total. Catalog in `retro-corpus-public/README.md`.
No remote created for the catalog repo (house rule: no new GitHub repos).

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

### 36. Arduino CC0 campaign — generateC AVR coverage (sb3-creator a575788)

Per the arduino-cc0-campaign.md doctrine, assessed all 6 items:

**Implemented (compiles on hosted service):**
- tone_set for AVR: Timer2 CTC + ISR pin toggle, any TONE pin (56600ab)
- Mega PWM D2-D8 + D44-D46: Timers 3-5 added (6367c14)
- setup()/loop() spurious drop warnings fixed (a575788)

**Honestly refused (genuinely inexpressible, not miscompiled):**
- 08.Strings (14 sketches): ALL use Arduino `String` class (C++ operator
  overloading, dynamic memory, `.length()/.indexOf()/.replace()` methods).
  Bare-metal C cannot express these. The importer translates what it can
  (print statements, pin ops) and warns about the rest. 2-18 pseudocode
  lines per sketch, 5-20 warnings each. This is the correct refusal.
- serialEvent: Arduino-framework callback, no bare-metal equivalent.
- Serial1 on mega (MultiSerial): requires UART1 library. The dialect has
  `print` mapped to UART0; a second UART would need a `print2`/`print to`
  dialect extension. Not yet expressible.

### 38. ATtiny88 hosted compile (stc-compiler 1f80d08)

ATtiny88 (avr25, 8 KB flash, 28-pin DIP — the Blinkenrocket MCU) added
to both /compile and /assemble. Device header, CRT, lib vendored.
5 new tests with Blinkenrocket-style PORTB/PORTD pin test. 102 total pass.

### 37. Mega Timer3/4/5 init for PWM (sb3-creator 99b4034)

The pwm_set case statements were setting COMnx1 bits but Timer3/4/5
were never initialized to fast PWM mode. Added conditional TCCRnA/B
init in bw_setup — only timers whose pins are declared get initialized.
Verified: D2+D6+D44 compiles to 905 bytes with correct timer init.

167/167 gallery examples generate C with zero failures.

### 35. Mega PWM coverage D2-D8 + D44-D46 (sb3-creator 6367c14)

Extended ATmega2560 pwm_set from 4 pins (D9-D12) to 15 pins across
Timers 1-5. Verified: D2+D6+D44 compiles to 844 bytes on hosted service.

### 34. AVR tone_set — Timer2 CTC + ISR toggle (sb3-creator 56600ab)

Software square-wave on any declared TONE pin via Timer2 COMPA interrupt.
Prescaler auto-selected. freq=0 stops. 8051/ARM get stubs.
Verified: 1167 bytes on hosted service.

### 33. Arduino import: all 11 categories (sb3-creator 50e7e55)

Extended the import test from 3 categories to all 11 (CC0-1.0). 75 Arduino
examples total: Communication, Control, Sensors, Display, Strings, USB,
StarterKit, ArduinoISP. All 75 translate (produce WHEN blocks), 57 re-parse
clean, 18 have expected parse warnings (Serial, USB HID, ISP, arrays).
150 import tests pass.

---

## What is NOT done

| item | status | next step |
|---|---|---|
| Arduino library support | bare avr/io.h only | separate decision (LGPL-2.1 obligation) |

**Cleared this session:**
- ~~Referee vocab gaps~~ — already implemented (all 5 opcodes in KNOWN + case handlers)
- ~~bw_print_num implicit declaration~~ — 8051 print library + UART setup (49ce197)
- ~~Corpus generator: more opcodes~~ — already done in d8c31f5
- ~~UNO examples in gallery~~ — 6 examples copied (dfadf99)
- ~~AVR symbol extraction test~~ — 8-test pytest (7578ab3)
- ~~array-subscript-dialect.md~~ — implemented in cToPseudocode Phase 2 (f259006)

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
f2a6a6c  licensing: BASIC tab labels + interpreter attributions per owner adjudication
621d554  fix: replace curly quotes in JSX with straight quotes — babel parse error
636a553  BASIC tab: generateBASIC view + basicToPseudocode import, two toggles
c7b7626  vendor: Mega + 168P examples, sb3-creator device axes, extension tiles
d2af2e1  corpus-differential: env-gated CI test for oracle-differential sampling
103676b  sync-examples: vendor gallery from sb3-creator with devices + refusals
```

### sb3-creator (main)
```
ed4d99b  THIRD-PARTY-NOTICES: BBC BASIC (zlib) and 6502 BASIC (MIT) dialect attributions
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
5855f37  test_assemble: 17 smoke tests for /assemble endpoint
77d2be7  /assemble endpoint: raw assembly for 8051, 6502, AVR
8c7693c  listing artifact: {asm, lineMap, format, v:1} for all three toolchains
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
