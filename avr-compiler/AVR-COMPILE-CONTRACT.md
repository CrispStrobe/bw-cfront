# AVR compile contract — what the compiler promises and what it does not

This document is the agreement between the compile endpoint (`avr-compiler`)
and the execution engine (`avr8js` via bw-board's adapter, `23991e8`). Both
sides read this; neither negotiates at runtime.

## 1. F_CPU — one definition, two consumers

`F_CPU` is **defined per board variant**, not per compile request.

| board | F_CPU | crystal |
|---|---|---|
| Arduino Uno | 16000000 | 16 MHz ceramic resonator |
| Arduino Nano | 16000000 | 16 MHz crystal |
| Arduino Pro Mini 3.3V | 8000000 | 8 MHz crystal |

**The compile endpoint defines F_CPU.** It passes `-DF_CPU=<value>` to avr-gcc
based on the `target` or `board` field in the request. The default is 16 MHz
(Uno/Nano).

**The simulator must configure the same clock.** avr8js runs the CPU core at a
configurable frequency; the adapter must set it to match the F_CPU the hex was
compiled with. If they disagree, every `_delay_ms()` call runs at the wrong
speed — the program works but all timing is wrong, silently, which looks like
a bug in user code.

This is the same failure mode as the STC12 1T/12T trap (stc README §8.1):
a program compiled for one clock running at another. The fix is the same: one
source of truth, read by both sides.

**The compile response includes the F_CPU value** so the simulator does not
have to guess:

```json
{
  "hex": ":100000000C94...",
  "fcpu": 16000000,
  "target": "atmega328p",
  "version": "avr-gcc (GCC) 7.3.0"
}
```

## 2. The artifact

**Intel HEX**, text format, with `.eeprom` section removed.

Produced by: `avr-objcopy -O ihex -R .eeprom main.elf main.hex`

This is program memory only (flash). avr8js loads it into the CPU's program
memory space. EEPROM content, if any, is not included — avr8js starts with
EEPROM zeroed (0xFF), matching a freshly erased chip.

## 3. Compile flags

**Deterministic: same source + same flags + same compiler version = same hex.**
Tested: two calls with the same source produce byte-identical hex. No
`__DATE__`, `__TIME__`, build-id or temp-path leaks into the output.

The property is qualified by compiler version: the same source through a
different avr-gcc is a different hex. The `version` field in the response
pins which compiler produced it.

```
avr-gcc -mmcu=atmega328p -DF_CPU=16000000UL -Os -std=gnu99
        -Wall -Wextra -ffunction-sections -fdata-sections
        -Wl,--gc-sections
```

`-Os` is the default. `-O0` or `-O2` may be requested but are not guaranteed
to produce working timing (delay loops depend on optimisation level).

## 4. What is verified and what is not

| claim | status | evidence |
|---|---|---|
| blink.c compiles to 176 bytes | **verified** | avr-gcc 7.3.0 on this box (category 3 — one implementation) |
| The hex is valid Intel HEX | **verified** | starts with `:`, parses, correct checksums |
| Error reporting works | **verified** | undeclared function → error in response |
| The hex executes correctly under avr8js | **verified** | bw-board e715cf9: D13 blinks at 500ms edges, ADC reads 512 @ 2.5V |
| Timing matches F_CPU | **verified** | same test: 500ms edges are exact under avr8js at 16 MHz |
| Vercel deployment works | **NOT verified** | avr-gcc may exceed the free-tier function size |

**The integration gap is closed.** bw-board `e715cf9` proved the chain
end to end: `generateC` → this endpoint → `parseIntelHex` → avr8js → D13
blinks at exact 500ms edges, ADC reads 512 at 2.5V over the new `onSerial`
hook.

## 5. Error response shape

A compile error returns HTTP 200 with the error in the JSON body (not an
HTTP error status). This matches the stc-compiler pattern.

```json
{
    "hex": null,
    "listing": null,
    "errors": "main.c:1:14: error: implicit declaration of function 'undeclared'...",
    "size": null,
    "version": "avr-gcc (GCC) 7.3.0",
    "target": "atmega328p",
    "fcpu": 16000000
}
```

| field | on success | on error |
|---|---|---|
| `hex` | Intel HEX text | `null` |
| `listing` | assembly listing | `null` |
| `errors` | `null` | compiler stderr (string) |
| `size` | `{ text, data }` | `null` |
| `version` | always present | always present |
| `target` | always present | always present |
| `fcpu` | always present | always present |

**`errors` is the discriminator.** If `errors` is `null`, the compile
succeeded and `hex` is present. If `errors` is a string, the compile
failed and `hex` is `null`. There is no partial success — a warning
without a hard error still produces hex (with the warning in `errors`
being `null`; warnings appear in stderr but are not errors).

## 6. Debug symbols (`symbols: true`)

When the request includes `"symbols": true`, the response includes a `symbols`
object in the same 004 format as `stc_symtab.py`:

```json
{
  "symbols": {
    "fcpu": 16000000,
    "device": "atmega328p",
    "scheduler": {
      "bw_ms": {"space": "sram", "addr": 260, "size": 4},
      "tasks": [{
        "name": "bw_task0",
        "func_addr": 218,
        "state": {"space": "sram", "addr": 258, "size": 2},
        "until": {"space": "sram", "addr": 256, "size": 2},
        "yields": [
          {"state": 0, "label": "loop_top", "addr": 240},
          {"state": 1, "label": "loop_top", "addr": 248},
          {"state": 2, "label": "wait",     "addr": 316}
        ]
      }]
    }
  }
}
```

### Address conventions

| address kind | what it is | consumer note |
|---|---|---|
| `scheduler.bw_ms.addr` | SRAM data-space address | read 4 bytes LE for `uint32_t` |
| `tasks[].state.addr` | SRAM data-space address | read 2 bytes LE; `0xFFFF` = completed |
| `tasks[].until.addr` | SRAM data-space address | read 2 bytes LE; ms timestamp |
| `tasks[].func_addr` | flash **byte** address | text section entry point |
| `yields[].addr` | flash **byte** address | avr8js PC = `addr / 2` (word address) |

**SRAM addresses** are in the data address space (0x00–0x8FF for ATmega328P).
The `0x800000` linker offset from `avr-nm` is already stripped. These are the
same addresses avr8js uses for `readData()`.

**Code addresses** are byte addresses. avr8js uses **word** addresses for the
program counter (`cpu.pc`), so divide by 2 when setting yield breakpoints:
`adapter.setBreakpoint({kind: 'code', addr: yield.addr / 2})`.

### Differences from the 8051 path

| | 8051 (stc_symtab) | AVR (this endpoint) |
|---|---|---|
| `bw_ms` size | 2 (uint16_t) | 4 (uint32_t) |
| address space name | `"iram"` | `"sram"` |
| code address source | SDCC `.cdb` line records | avr-gcc DWARF via `avr-objdump -d -l` |
| code address unit | byte (8051 PC is byte) | byte (avr8js PC is **word** = byte/2) |
| `@bw yield` map | same format | same format |

### When symbols are absent

A program without `bw_taskN` functions (single-WHEN, no cooperative scheduler)
returns `symbols: null` with `symbols_error` explaining why. This is not an
error — the image is valid, it simply has no Level 1 position to describe.
The compile still succeeds; only the symbol table is absent.

## 7. What the compile endpoint does NOT do

- **No Arduino library support.** This compiles bare AVR C (`avr/io.h`,
  `util/delay.h`). Arduino's `setup()`/`loop()` pattern and its libraries
  (`Serial`, `Wire`, `SPI`) are not available. Adding them is a separate
  decision — it means bundling the Arduino core, which is ~100 KB of source
  and has its own licence (LGPL-2.1).
- **No upload.** The endpoint compiles; it does not flash. Flashing is
  the browser's job (Web Serial + STK500 protocol for Arduino boards).
- **No simulation.** The hex is returned to the caller, who passes it to
  avr8js. The compile endpoint has no knowledge of the board state.
