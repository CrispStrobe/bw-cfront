# bw-cfront — results

## Phase 1: cooperative-scheduler inversion — DONE

The Duff's-device state machines that `generateC` emits for multi-script
projects are now structurally recognised and recovered. The inverter walks
the `switch (task_state) { case 0: … }` body, matching each shape:

| construct        | C pattern |
|------------------|-----------|
| FOREVER          | `state = S; case S: <body> state = S; return;` |
| REPEAT n         | `bw_iK = (expr); state = S; case S: if (bw_iK) { … bw_iK--; state = S; return; }` |
| REPEAT UNTIL c   | `state = S; case S: if (!(c)) { … state = S; return; }` |
| wait N seconds   | `until = bw_now() + (MS); state = S; case S: if ((int)(…) < 0) return;` |
| wait until c     | `state = S; case S: if (!(c)) return;` |
| stop             | `state = 0xFFFF; return;` |
| if / if-else     | parsed with task-aware handler for nested case labels |

Case labels inside `if`/`else` branches (the Duff's-device property) are
handled. Proc parameter names recovered from the C function signature.
Round-trip tests for 2- and 3-script fixtures, all fixed points after one hop.

**Test suite**: 394 pass, 0 fail (was 391; added 3 round-trip tests, changed
1 from "scheduler refused" to "scheduler inverted").

---

## Phase 2: corpus-driven broadening — DONE

**Corpus**: 76 / 85 repos cloned (9 link rot), 1282 `.c` files.

### Numbers (library files excluded from percentages)

### Without keil2sdcc

| | count | of 515 files with main() |
|---|---|---|
| Translate with at most function-call warnings | **468** | **90.9%** |
| Real failures | 47 | 9.1% |
| **Exceptions** | **0** | **(was 46)** |

### With keil2sdcc preprocessing

| | count | of 515 files with main() |
|---|---|---|
| Translate | **484** | **94.0%** |
| Real failures | 31 | |

The two effects are separate: bitwise adds **+42** files (dialect expressibility),
keil2sdcc adds **+16** on top (input widening — Keil-style bitwise SFR setup that
is now expressible after the dialect extended).

### Expressibility breakdown of the 47 remaining failures (without keil2sdcc)

**Genuinely inexpressible (3 files):**
- `goto` — structured blocks cannot represent arbitrary jumps. Correct to refuse.

**Expressible at a cost (12 files, 9 break-only):**
- **`break`/`continue`**: the standard transformation is a flag variable plus
  `repeat until`. Not impossible, just structural — it changes the shape of the
  loop. **This is now the largest remaining category.**

**Translator limitations (32 files):**
- Pin assigned computed value: 16 files — a pin can only be on/off/toggled in
  pseudocode, not assigned a computed expression.
- Parser crash on buggy C source: 5 files (e.g. `if(flag=1)` instead of `==`)
- Other (overlap of multiple issues): ~11 files

### Effect of keil2sdcc preprocessing (measured separately)

keil2sdcc changes 494 corpus files. Before the bitwise dialect it gained only +1
file (dialect couldn't express the results anyway). After the dialect: **+16 files**
(468→484). The two interact: keil2sdcc translates Keil-style SFR bitwise setup
into SDCC form, and the bitwise dialect now makes that translatable.

### What was done (12 improvements, each per-file forensics)

1. Array subscripts — was 46 parser exceptions, now 0
2. `do/while` → REPEAT UNTIL
3. `switch/case` → series of IF blocks
4. Pointer casts `(char *)` — fixed isCast + skip logic
5. Ternary `?:` parsed
6. Unary `&` / `*` / pre-post `++`/`--` in expressions
7. Struct member access `.` and `->` parsed
8. `while(1)` → FOREVER
9. User function calls → custom-block call syntax
10. Keil type specifiers (`sbit`, `sfr`, `code`, `data`, `xdata`, etc.) skip cleanly
11. `_nop_()` recognised and skipped
12. More `for`-loop patterns: count-down, `<=`, empty-init

### Commits

```
91016a8  invert the cooperative-scheduler form in cToPseudocode
6c1a4e7  broaden the hand-written-C subset: arrays, do/while, switch, casts, ternary
0550332  handle more for-loop variants and count-down patterns
2eca31c  add corpus measurement scripts: baseline and keil2sdcc effect
16a8bb7  suppress spurious break warnings inside switch case bodies
ab85b22  map C bitwise operators onto the new pseudocode dialect
7a38ff2  transform break/continue into flag variables and loop conditions
```

### What's next

Bitwise operators landed in the pseudocode dialect (sb3Creator.js, separate work).
cToPseudocode.js now maps C's `& | ^ ~ << >>` and `&= |= ^= <<= >>=` onto
`bitand bitor bitxor bitnot shiftleft shiftright`. SFR register setup stays
silently filtered.

**break/continue is now handled** — `if (cond) break;` at loop end folds into
`REPEAT UNTIL cond` (exact, no warning); break-in-middle uses a flag variable
with a guard on subsequent statements (warned as structural change).

### Final numbers (four categories)

| | count | of 515 |
|---|---|---|
| 1. Translates directly | **494** | **95.9%** |
| 2. Translates after restructuring (warned) | 9 | 1.7% |
| **── total that translate ──** | **503** | **97.7%** |
| 3. Blocked by fixable defect | 9 | |
| ····for-loop variant | 1 | |
| ····parser crash (bug) | 4 | |
| ····ternary (else branch dropped) | 3 | |
| ····pin computed value | **0** | was 16 — dialect closed it |
| 4. Genuinely impossible (`goto`) | **3** | **0.6%** |
