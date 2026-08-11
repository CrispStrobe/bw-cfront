# Dialect request: array subscript expressions

**From:** bw-cfront (the C front end)
**To:** sb3-creator (the pseudocode dialect / block surface)
**Priority:** the last dialect gap blocking the corpus from 98.3% → 100%

## The construct

```c
for (i = 0; buzzc[i] != '\0'; i++) { /* ... */ }
```

A for-loop whose condition dereferences an array by index. This is the
standard C string-traversal idiom: walk until the null terminator.

## Why it does not translate today

The pseudocode dialect has `REPEAT N:` (counted) and `REPEAT UNTIL cond:`
(condition-based). Both work. But the **condition** `buzzc[i] != '\0'`
contains an array subscript (`buzzc[i]`), and the dialect has no way to
express indexing into an array or table by a variable.

The translator currently emits `REPEAT UNTIL 1 = 1:` (infinite loop) with
a warning: "a `for` loop that is not `for(;;)` or a simple counter."

## What would close it

A `TABLE` declaration already exists in the dialect (added for the LED cube
font tables). Extending it to support **indexed read** would close this gap:

```
TABLE buzzc = 104 101 108 108 111 0

REPEAT UNTIL buzzc[i] = 0:
  # process buzzc[i]
  change i by 1
```

The pieces needed:
1. A reporter block: `item (i) of table (buzzc)` — returns the value at index i
2. The pseudocode syntax: `buzzc[i]` or `item i of buzzc`
3. The C lowering: `buzzc[i]` (already natural in C)

This is the same tier-2 feature identified in `DIALECT-COVERAGE.md` as
"indexed lookup tables" — one of two features blocking 5 of 16 treideme
demos (the other being whole-port I/O).

## Corpus impact

1 of the 6 remaining non-translating corpus files would be fixed. The file
is `串口控制/main.c` from `C51_Study/13 1602液晶与串口应用实例/`.

## Minimal test case

```c
void main(void) {
    unsigned char buf[] = {1, 2, 3, 0};
    int i;
    for (i = 0; buf[i] != 0; i++) {
        delay_ms(buf[i] * 100);
    }
}
```

Today: warns and emits `REPEAT UNTIL 1 = 1:`.
With array dialect: `REPEAT UNTIL item i of buf = 0:` + `wait (item i of buf * 100 / 1000) seconds`.
