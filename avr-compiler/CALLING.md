# How to call the AVR compile endpoint

## Start locally

```bash
cd avr-compiler
pip install -r requirements.txt   # once
uvicorn app:app --host 127.0.0.1 --port 8321
```

## Call it

```bash
curl -X POST http://127.0.0.1:8321/compile \
    -H "Content-Type: application/json" \
    -d '{"code": "#include <avr/io.h>\n#include <util/delay.h>\nint main(void) { DDRB |= (1<<PB5); for(;;) { PORTB |= (1<<PB5); _delay_ms(500); PORTB &= ~(1<<PB5); _delay_ms(500); } }", "target": "atmega328p"}'
```

## Example response (recorded, not mocked)

Produced by the endpoint at commit `7b18dbe`, avr-gcc 7.3.0, blink.c for
ATmega328P. The hex, listing, size, version, target and **fcpu** are all real.

```json
{
    "hex": ":100000000C9434000C943E000C943E000C943E0082\n:100010000C943E000C943E000C943E000C943E0068\n...\n:00000001FF\n",
    "listing": "  16 0000 259A      \t\tsbi 0x4,5\n  18 0002 2D9A      \t\tsbi 0x5,5\n...",
    "errors": null,
    "size": { "text": 176, "data": 0 },
    "version": "avr-gcc (GCC) 7.3.0",
    "target": "atmega328p",
    "fcpu": 16000000
}
```

**`fcpu` is in the response.** The simulator reads it from here and configures
the avr8js clock to match. It is never hard-coded on the simulator side.

## For bw-board

To replace the local `avr-gcc` call in `avr-e2e.test.js` with this endpoint:

```javascript
const resp = await fetch('http://127.0.0.1:8321/compile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code: blinkSource, target: 'atmega328p' }),
});
const { hex, fcpu, source } = await resp.json();
// hex is Intel HEX text; fcpu is the clock the hex was compiled for
// source is always "endpoint" — see below
```

## Distinguishing endpoint from local compilation

The response includes `"source": "endpoint"`. A caller that falls back to
local `avr-gcc` should set `source` to `"local"` in its own result, so the
test can assert which path produced the hex.

The `version` field also distinguishes: the endpoint reports its pinned
`avr-gcc (GCC) 7.3.0`; a local install may be a different version.

## When the endpoint is absent

**The contract's position: report loudly, do not hide it.**

If the endpoint is unreachable (connection refused, timeout, DNS failure),
the caller has three options:

| option | when to use | what to say |
|---|---|---|
| **Fail the test** | CI that is meant to exercise the contract | `assert.fail('compile endpoint unreachable — the contract was not tested')` |
| **Fall back to local and report** | Development, where local avr-gcc is available | log `"compile endpoint absent, using local avr-gcc"` and set `source: "local"` in the result |
| **Skip the test** | CI without the service and without local avr-gcc | `{ skip: 'no compile endpoint and no local avr-gcc' }` |

**The one thing a caller must NOT do: fall back silently.** A green suite
that compiled locally while the contract went untested is the shape of every
gate-that-passes-by-not-checking failure this project has caught. The
fallback is reasonable; silence about it is not.

## What the endpoint does NOT do

- No Arduino libraries (bare `avr/io.h` + `util/delay.h` only)
- No upload / flashing
- No simulation — it returns hex, you run it
- Vercel deployment is NOT verified (avr-gcc may exceed free-tier function size)
