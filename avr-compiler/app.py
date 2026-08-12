"""
avr-compiler — hosted AVR-GCC compile endpoint.

POST /compile { code, target?, flags? } → { hex, listing, errors, version }

Mirrors the stc-compiler service pattern: GPL toolchain invoked as a service
(not linked), repo stays MIT. Deterministic flags, version pinned and reported.

Target: ATmega328P (-mmcu=atmega328p) by default.
"""

from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="avr-compiler", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ---- toolchain discovery ----

AVR_GCC = os.environ.get("AVR_GCC", shutil.which("avr-gcc") or "avr-gcc")
AVR_OBJCOPY = os.environ.get("AVR_OBJCOPY", shutil.which("avr-objcopy") or "avr-objcopy")
AVR_SIZE = os.environ.get("AVR_SIZE", shutil.which("avr-size") or "avr-size")

# Version, pinned at startup
try:
    _ver = subprocess.run([AVR_GCC, "--version"], capture_output=True, text=True, timeout=5)
    AVR_GCC_VERSION = _ver.stdout.split("\n")[0].strip()
except Exception:
    AVR_GCC_VERSION = "unknown"

# ---- supported targets ----

TARGETS = {
    "atmega328p": {"mcu": "atmega328p", "flash": 32768, "ram": 2048, "fcpu": 16000000},
    "atmega168p": {"mcu": "atmega168p", "flash": 16384, "ram": 1024, "fcpu": 16000000},
    "atmega2560": {"mcu": "atmega2560", "flash": 262144, "ram": 8192, "fcpu": 16000000},
}
DEFAULT_TARGET = "atmega328p"

# ---- compile flags ----
# Deterministic: same source + same flags = same hex, always.
BASE_FLAGS = [
    "-Os",                      # optimise for size
    "-std=gnu99",               # C99 + GNU extensions (AVR headers need them)
    "-Wall", "-Wextra",         # warnings
    "-Wno-implicit-fallthrough", # Duff's-device cooperative scheduler uses deliberate fallthrough
    "-ffunction-sections",      # dead-code elimination
    "-fdata-sections",
    "-fno-exceptions",
    "-fno-threadsafe-statics",
]
LINK_FLAGS = [
    "-Wl,--gc-sections",        # strip unused sections
]

# ---- size limit ----
MAX_SOURCE_BYTES = 64 * 1024    # 64 KiB of source text


class CompileReq(BaseModel):
    code: str
    target: Optional[str] = None
    language: Optional[str] = "c"
    symbols: Optional[bool] = False


class CompileResp(BaseModel):
    hex: Optional[str] = None       # Intel HEX as text
    listing: Optional[str] = None   # assembly listing
    errors: Optional[str] = None    # compiler stderr
    size: Optional[dict] = None     # { text, data, bss }
    version: str = AVR_GCC_VERSION
    target: str = DEFAULT_TARGET
    fcpu: int = 16000000            # the F_CPU the hex was compiled with
    source: str = "endpoint"        # always "endpoint" — a caller that compiled locally should set "local"
    symbols: Optional[dict] = None  # symbol table: { name → { addr, type } } when requested
    symbols_error: Optional[str] = None


@app.get("/")
def root():
    return {
        "service": "avr-compiler",
        "version": AVR_GCC_VERSION,
        "targets": list(TARGETS.keys()),
        "endpoint": "POST /compile {code, target?, language?}",
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": AVR_GCC_VERSION}


@app.post("/compile")
def compile_source(req: CompileReq) -> CompileResp:
    """Compile C source to Intel HEX for an AVR target."""

    target_name = (req.target or DEFAULT_TARGET).lower()
    if target_name not in TARGETS:
        return CompileResp(
            errors=f"Unknown target '{target_name}'. Supported: {', '.join(TARGETS)}",
            target=target_name,
        )

    target = TARGETS[target_name]

    if len(req.code.encode("utf-8")) > MAX_SOURCE_BYTES:
        return CompileResp(
            errors=f"Source too large ({len(req.code)} bytes, max {MAX_SOURCE_BYTES})",
            target=target_name,
        )

    work = tempfile.mkdtemp(prefix="avr-")
    try:
        src_path = os.path.join(work, "main.c")
        elf_path = os.path.join(work, "main.elf")
        hex_path = os.path.join(work, "main.hex")
        lst_path = os.path.join(work, "main.lst")

        with open(src_path, "w") as f:
            f.write(req.code)

        # Copy the AVR runtime header so #include "avr_runtime.h" works
        runtime_dir = os.path.join(os.path.dirname(__file__), "runtime")
        if os.path.isdir(runtime_dir):
            for rf in os.listdir(runtime_dir):
                shutil.copy2(os.path.join(runtime_dir, rf), work)

        # ---- compile ----
        fcpu = target["fcpu"]
        debug_flags = ["-g"] if req.symbols else []
        cmd = [
            AVR_GCC,
            f"-mmcu={target['mcu']}",
            f"-DF_CPU={fcpu}UL",
            *BASE_FLAGS,
            *debug_flags,
            "-Wa,-adhlns=" + lst_path,      # generate listing
            "-o", elf_path,
            src_path,
            *LINK_FLAGS,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=work,
        )

        if result.returncode != 0:
            return CompileResp(
                errors=result.stderr.strip(),
                target=target_name,
            )

        # ---- extract hex ----
        objcopy = subprocess.run(
            [AVR_OBJCOPY, "-O", "ihex", "-R", ".eeprom", elf_path, hex_path],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=work,
        )
        if objcopy.returncode != 0:
            return CompileResp(
                errors=f"objcopy failed: {objcopy.stderr.strip()}",
                target=target_name,
            )

        # ---- size ----
        size_result = subprocess.run(
            [AVR_SIZE, "--mcu=" + target["mcu"], "--format=avr", elf_path],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=work,
        )
        size_info = _parse_size(size_result.stdout) if size_result.returncode == 0 else None

        hex_text = open(hex_path).read()
        lst_text = open(lst_path).read() if os.path.exists(lst_path) else None

        # ---- flash size check ----
        hex_bytes = sum(
            len(bytes.fromhex(line[9:-2])) for line in hex_text.splitlines()
            if line.startswith(":") and line[7:9] == "00" and len(line) > 10
        )
        if hex_bytes > target["flash"]:
            return CompileResp(
                hex=hex_text,
                listing=lst_text,
                errors=f"Image size {hex_bytes} bytes exceeds {target['mcu']} flash ({target['flash']} bytes)",
                size=size_info,
                target=target_name,
            )

        # ---- symbols (debug info) ----
        sym_table = None
        sym_error = None
        if req.symbols:
            try:
                sym_table = _extract_symbols(
                    elf_path, req.code,
                    fcpu=fcpu, device=target_name,
                )
            except SymbolTableError as e:
                sym_error = str(e)
            except Exception as e:
                sym_error = str(e)

        return CompileResp(
            hex=hex_text,
            listing=lst_text,
            size=size_info,
            target=target_name,
            fcpu=fcpu,
            symbols=sym_table,
            symbols_error=sym_error,
        )

    except subprocess.TimeoutExpired:
        return CompileResp(
            errors="Compilation timed out (30s limit)",
            target=target_name,
        )
    except Exception as e:
        return CompileResp(
            errors=f"Internal error: {str(e)}",
            target=target_name,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _parse_size(output: str) -> dict | None:
    """Parse avr-size --format=avr output."""
    info = {}
    for line in output.splitlines():
        if "Program:" in line:
            # "Program:     234 bytes (0.7% Full)"
            parts = line.split()
            try:
                info["text"] = int(parts[1])
            except (IndexError, ValueError):
                pass
        elif "Data:" in line:
            parts = line.split()
            try:
                info["data"] = int(parts[1])
            except (IndexError, ValueError):
                pass
    return info if info else None


AVR_NM = os.environ.get("AVR_NM", shutil.which("avr-nm") or "avr-nm")
AVR_OBJDUMP = os.environ.get("AVR_OBJDUMP", shutil.which("avr-objdump") or "avr-objdump")


class SymbolTableError(Exception):
    pass


# ---- C source scanning (mirrors stc_symtab.py) ----

TASK_RE = re.compile(r"^void\s+(bw_task\d+)\s*\(")
CASE_RE = re.compile(r"^\s*case\s+(\d+)\s*:")
YIELD_RE = re.compile(r"@bw\s+yield\s+(bw_task\d+)\s+(\d+)\s+(\S+)\s+(\S+)")
VAR_RE = re.compile(r'@bw\s+var\s+(\S+)\s+"([^"]+)"(?:\s+"([^"]+)")?')


def _scan_tasks(source: str) -> dict[str, list[tuple[int, int, str]]]:
    """Find bw_taskN functions and their case labels.

    Returns {task_name: [(state, line_number, label), ...]}.
    """
    lines = source.splitlines()
    tasks: dict[str, list[tuple[int, int, str]]] = {}
    current: str | None = None
    depth = 0
    started = False

    for i, raw in enumerate(lines, start=1):
        m = TASK_RE.match(raw)
        if m and current is None:
            current, depth, started = m.group(1), 0, False
            tasks[current] = []
            continue

        if current is None:
            continue

        depth += raw.count("{") - raw.count("}")
        if raw.count("{"):
            started = True

        c = CASE_RE.match(raw)
        if c:
            state = int(c.group(1))
            label = _label_for(lines, i)
            tasks[current].append((state, i, label))

        if started and depth <= 0:
            current = None

    return tasks


def _label_for(lines: list[str], lineno: int) -> str:
    """Advisory label for a yield point, from the guarding statement."""
    if lineno < len(lines):
        nxt = lines[lineno].strip()  # line after the case label
        if "bw_now()" in nxt:
            return "wait"
        if nxt.startswith("if (bw_i"):
            return "repeat_top"
        if nxt.startswith("if (!(") or nxt.startswith("if ("):
            return "wait_until"
    return "loop_top"


def _scan_yield_map(source: str) -> dict[str, dict[int, str]]:
    """Parse `@bw yield` lines from the header → {task: {state: block_id}}."""
    header = re.search(r"@bw-begin(.*?)@bw-end", source, re.S)
    if not header:
        return {}
    out: dict[str, dict[int, str]] = {}
    for line in header.group(1).splitlines():
        m = YIELD_RE.search(line)
        if m:
            out.setdefault(m.group(1), {})[int(m.group(2))] = unquote(m.group(3))
    return out


def _scan_variables(source: str) -> list[dict]:
    """Parse `@bw var` lines from the header."""
    header = re.search(r"@bw-begin(.*?)@bw-end", source, re.S)
    if not header:
        return []
    out = []
    for line in header.group(1).splitlines():
        m = VAR_RE.search(line)
        if m:
            entry = {"c": m.group(1), "name": m.group(2)}
            if m.group(3):
                entry["sprite"] = m.group(3)
            out.append(entry)
    return out


def _line_addresses(elf_path: str) -> dict[int, int]:
    """Source line → code address from DWARF debug info.

    Uses `avr-objdump -d -l` (disassembly with source lines interleaved),
    NOT `--dwarf=decodedline`. The decodedline path returns zero rows on
    binutils 2.26 even with DWARF-2 (avr-gcc 7.3.0's default), because
    2.26's decoder does not handle the AVR line program. The -d -l path
    works because the disassembler reads the DWARF through a different
    code path (inline source annotation).

    Parses lines like "/path/to/main.c:42" followed by "  1a4: ..." to
    build {lineno: first_addr}. Keeps only the first address per line
    (matches stc_symtab convention).
    """
    result = subprocess.run(
        [AVR_OBJDUMP, "-d", "-l", elf_path],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise SymbolTableError(f"avr-objdump failed: {result.stderr.strip()}")

    lines: dict[int, int] = {}
    # Pattern: /path/to/main.c:42
    line_ref_re = re.compile(r"^(/.*?/main\.c):(\d+)$")
    # Pattern:   1a4:   xx xx   instruction
    insn_re = re.compile(r"^\s+([0-9a-f]+):\s")
    pending_lineno: int | None = None

    for raw in result.stdout.splitlines():
        m = line_ref_re.match(raw)
        if m:
            pending_lineno = int(m.group(2))
            continue
        if pending_lineno is not None:
            m2 = insn_re.match(raw)
            if m2:
                addr = int(m2.group(1), 16)
                lines.setdefault(pending_lineno, addr)
                pending_lineno = None
    return lines


# AVR-GCC linker places data symbols at 0x800000 + SRAM offset.
# avr8js uses the raw data-space address (0x100+ for ATmega328P SRAM).
AVR_RAM_BASE = 0x800000


def _nm_symbols(elf_path: str) -> dict[str, tuple[int, str]]:
    """All bw_* symbols from avr-nm. Returns {name: (addr, section)}.

    Data/BSS addresses have the 0x800000 linker offset stripped so they
    match the data-space addresses avr8js uses.
    """
    result = subprocess.run(
        [AVR_NM, "--defined-only", elf_path],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise SymbolTableError(f"avr-nm failed: {result.stderr.strip()}")

    nm_sections = {
        "b": "bss", "B": "bss",
        "d": "data", "D": "data",
        "t": "text", "T": "text",
        "r": "rodata", "R": "rodata",
    }
    symbols = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        addr_hex, typ, name = parts
        if not name.startswith("bw_"):
            continue
        section = nm_sections.get(typ, typ)
        addr = int(addr_hex, 16)
        # Strip the linker's RAM offset for data/bss symbols
        if section in ("bss", "data") and addr >= AVR_RAM_BASE:
            addr -= AVR_RAM_BASE
        symbols[name] = (addr, section)
    return symbols


def _extract_symbols(elf_path: str, source: str, *,
                     fcpu: int, device: str) -> dict:
    """Build the debug symbol table in the same schema as stc_symtab.

    Output shape (004 format):
    {
      "fcpu": 16000000,
      "device": "atmega328p",
      "scheduler": {
        "bw_ms": {"space": "sram", "addr": 0x10c, "size": 4},
        "tasks": [{
          "name": "bw_task0",
          "func_addr": 0x1a0,
          "state": {"space": "sram", "addr": 0x10a, "size": 2},
          "until": {"space": "sram", "addr": 0x108, "size": 2},
          "yields": [
            {"state": 0, "label": "entry", "addr": 0x1a4, "block": "..."},
            ...
          ]
        }]
      },
      "variables": [...]
    }
    """
    nm = _nm_symbols(elf_path)
    tasks = _scan_tasks(source)
    yield_map = _scan_yield_map(source)
    variables = _scan_variables(source)

    if not tasks:
        raise SymbolTableError(
            "no bw_taskN functions in this source. A single-WHEN program "
            "compiles to a plain loop with no scheduler and no per-task state, "
            "so there is no Level 1 position to describe."
        )

    # Get line→address mapping from DWARF for yield code addresses
    line_addrs = _line_addresses(elf_path)

    # Drift check: yield map must agree with case labels
    if yield_map:
        from_header = {(t, s) for t, states in yield_map.items() for s in states}
        from_source = {(t, s) for t, cases in tasks.items() for s, _, _ in cases}
        if from_header != from_source:
            only_header = sorted(from_header - from_source)
            only_source = sorted(from_source - from_header)
            raise SymbolTableError(
                "the @bw yield map disagrees with the case labels in the same "
                "file. It was written by a different build than this C.\n"
                f"  in the header but not the source: {only_header}\n"
                f"  in the source but not the header: {only_source}"
            )

    # bw_ms is uint32_t on AVR (4 bytes), vs uint16_t on 8051
    bw_ms_entry = nm.get("bw_ms")
    if not bw_ms_entry:
        raise SymbolTableError("bw_ms not found in the ELF symbols")
    bw_ms = {"space": "sram", "addr": bw_ms_entry[0], "size": 4}

    # Build a sorted list of (lineno, addr) for nearest-line lookup.
    # avr-gcc's DWARF often has no address for the `case N:` line itself
    # (it is a label, not code); the address is on the first statement after.
    sorted_line_addrs = sorted(line_addrs.items())

    def _addr_at_or_after(lineno: int, max_ahead: int = 10) -> int | None:
        """Find the code address for the first DWARF line in [lineno, lineno+max_ahead].

        The `case N:` label itself generates no code; the address we want is
        the first statement after it, which is typically 1-2 lines later.
        """
        for ln, addr in sorted_line_addrs:
            if ln >= lineno and ln <= lineno + max_ahead:
                return addr
            if ln > lineno + max_ahead:
                break
        return None

    out_tasks = []
    for name in sorted(tasks, key=lambda n: int(n[len("bw_task"):])):
        yields = []
        for state, lineno, label in sorted(tasks[name]):
            entry: dict = {"state": state, "label": label}
            addr = _addr_at_or_after(lineno)
            if addr is not None:
                entry["addr"] = addr
            block = yield_map.get(name, {}).get(state)
            if block is not None:
                entry["block"] = block
            yields.append(entry)

        missing = [y["state"] for y in yields if "addr" not in y]
        if missing:
            raise SymbolTableError(
                f"{name}: no code address for case labels at states {missing}. "
                f"Was the image compiled with -g? (lines checked: "
                f"{[(s, ln) for s, ln, _ in sorted(tasks[name])]})"
            )

        # State and until are uint16_t (2 bytes, 16-bit LE)
        state_sym = nm.get(f"{name}_state")
        until_sym = nm.get(f"{name}_until")
        func_sym = nm.get(name)

        out_tasks.append({
            "name": name,
            "func_addr": func_sym[0] if func_sym else None,
            "state": {"space": "sram", "addr": state_sym[0], "size": 2} if state_sym else None,
            "until": {"space": "sram", "addr": until_sym[0], "size": 2} if until_sym else None,
            "yields": yields,
        })

    table: dict = {
        "fcpu": fcpu,
        "device": device,
        "scheduler": {
            "bw_ms": bw_ms,
            "tasks": out_tasks,
        },
    }

    # Variables from the @bw header, with SRAM addresses from nm
    if variables:
        out_vars = []
        for v in variables:
            sym = nm.get(v["c"])
            if sym:
                out_vars.append({**v, "space": "sram", "addr": sym[0], "size": 2})
            else:
                out_vars.append({**v, "unlocated": f"{v['c']} not found in ELF symbols"})
        table["variables"] = out_vars

    return table
