# bw-cfront — session handoff (2026-08-12)

## What this session completed

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

---

## What is NOT done

| item | status | next step |
|---|---|---|
| UNO examples in gallery | 6 examples in `avr-examples/` (bw-cfront), not in sb3-creator gallery | copy into sb3-creator/examples/, add to index.json with `"device": "arduino-uno"` |
| AVR symbol extraction test | no pytest that POSTs a two-task AVR program and asserts response shape | write one modeled on test_arm_build.py |
| Arduino library support | bare avr/io.h only | separate decision (LGPL-2.1 obligation) |
| array-subscript-dialect.md | filed in spec-updates/, unread by sb3-creator | next sb3-creator session should read it |

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
5339d11  HANDOFF.md: record Pico examples and ARM endpoint as done
d30f69d  HANDOFF.md: record ARM compile endpoint live on stc-compiler
cf4b447  HANDOFF.md: record Nano examples landed in sb3-creator gallery
```

### sb3-creator (main)
```
b349d87  pico04-button: digital input example with pad IE verification
7aab1bb  pico examples: 3 Raspberry Pi Pico gallery entries with live compile verification
596b659  nano examples: 3 Arduino Nano gallery entries with live compile verification
```

### stc-compiler (main)
```
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
- **Nano examples**: `sb3-creator/examples/nano01-blink/` etc.
- **Pico examples**: `sb3-creator/examples/pico01-blink/` etc.
- **Gallery test skip**: `sb3-creator/test/gallery.test.mjs` line 54, 70
- **Live service**: `https://stc-compiler.vercel.app` (`/health`, `/compile`)
- **Vercel size**: AVR (36 MB) + ARM (82 MB) + SDCC (8 MB) = 126 MB / 250 MB limit
