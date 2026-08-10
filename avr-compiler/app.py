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
import shutil
import subprocess
import tempfile
from typing import Optional

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


class CompileResp(BaseModel):
    hex: Optional[str] = None       # Intel HEX as text
    listing: Optional[str] = None   # assembly listing
    errors: Optional[str] = None    # compiler stderr
    size: Optional[dict] = None     # { text, data, bss }
    version: str = AVR_GCC_VERSION
    target: str = DEFAULT_TARGET
    fcpu: int = 16000000            # the F_CPU the hex was compiled with


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

        # ---- compile ----
        fcpu = target["fcpu"]
        cmd = [
            AVR_GCC,
            f"-mmcu={target['mcu']}",
            f"-DF_CPU={fcpu}UL",
            *BASE_FLAGS,
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

        return CompileResp(
            hex=hex_text,
            listing=lst_text,
            size=size_info,
            target=target_name,
            fcpu=fcpu,
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
