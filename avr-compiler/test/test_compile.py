"""Test the avr-compiler service locally."""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import compile_source, CompileReq

BLINK = open(os.path.join(os.path.dirname(__file__), "blink.c")).read()


def test_blink_compiles():
    req = CompileReq(code=BLINK)
    resp = compile_source(req)
    assert resp.errors is None, f"Compile failed: {resp.errors}"
    assert resp.hex is not None, "No hex output"
    assert resp.hex.startswith(":"), "Hex does not start with :"
    assert resp.target == "atmega328p"
    assert resp.version and "avr-gcc" in resp.version.lower() or "GCC" in resp.version
    assert resp.size and resp.size.get("text", 0) > 0, f"Size: {resp.size}"
    print(f"  blink: {resp.size['text']} bytes, {resp.hex.count(chr(10))} hex lines")


def test_bad_code_reports_errors():
    req = CompileReq(code="int main() { undeclared_function(); }")
    resp = compile_source(req)
    assert resp.errors is not None, "Bad code should produce errors"
    assert "undeclared" in resp.errors.lower() or "implicit" in resp.errors.lower()
    assert resp.hex is None, "Bad code should not produce hex"


def test_unknown_target_refused():
    req = CompileReq(code=BLINK, target="pic16f84")
    resp = compile_source(req)
    assert resp.errors is not None
    assert "Unknown target" in resp.errors


def test_version_reported():
    req = CompileReq(code=BLINK)
    resp = compile_source(req)
    assert resp.version != "unknown"


COOP = open(os.path.join(os.path.dirname(__file__), "coop_blink.c")).read()


def test_cooperative_scheduler_compiles():
    """The Duff's-device cooperative scheduler pattern compiles for AVR."""
    req = CompileReq(code=COOP)
    resp = compile_source(req)
    assert resp.errors is None, f"Coop scheduler failed: {resp.errors}"
    assert resp.hex is not None
    assert resp.size and resp.size.get("text", 0) > 0
    assert resp.fcpu == 16000000, f"F_CPU must be in the response: {resp.fcpu}"
    print(f"  coop_blink: {resp.size['text']} bytes, fcpu={resp.fcpu}")


def test_fcpu_in_response():
    req = CompileReq(code=BLINK)
    resp = compile_source(req)
    assert resp.fcpu == 16000000, f"Expected 16 MHz, got {resp.fcpu}"


def test_source_field_is_endpoint():
    """The source field must say 'endpoint' so callers can distinguish from local."""
    req = CompileReq(code=BLINK)
    resp = compile_source(req)
    assert resp.source == "endpoint", f"source should be 'endpoint', got '{resp.source}'"


def test_source_field_on_error():
    """Even on error, source is 'endpoint'."""
    req = CompileReq(code="int main() { undeclared(); }")
    resp = compile_source(req)
    assert resp.source == "endpoint"


def test_determinism_same_source_same_hex():
    """Same source + same flags + same compiler = byte-identical hex."""
    req = CompileReq(code=BLINK)
    r1 = compile_source(req)
    r2 = compile_source(req)
    assert r1.hex == r2.hex, "Two compiles of the same source must produce identical hex"
    assert r1.size == r2.size, "Size must match"
    assert r1.version == r2.version, "Version must match"


def test_determinism_no_date_time_leak():
    """The hex and listing must not contain __DATE__ or __TIME__."""
    import re
    req = CompileReq(code=BLINK)
    resp = compile_source(req)
    # Check listing for date/time stamps that would break determinism
    listing = resp.listing or ""
    months = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2} \d{4}"
    assert not re.search(months, listing), "Listing contains __DATE__"
    times = r"\d{2}:\d{2}:\d{2}"
    # avr-gcc version string has no time; check for stray timestamps
    non_version = re.sub(r"GCC.*$", "", listing, flags=re.MULTILINE)
    assert not re.search(times, non_version), "Listing contains __TIME__"


def test_determinism_coop_scheduler():
    """The cooperative scheduler also produces deterministic output."""
    req = CompileReq(code=COOP)
    r1 = compile_source(req)
    r2 = compile_source(req)
    assert r1.hex == r2.hex, "Coop scheduler: two compiles must be identical"


def test_error_response_shape():
    """A compile error returns errors string, null hex, and the target/version."""
    req = CompileReq(code="int main() { undeclared_function(); }")
    resp = compile_source(req)
    # errors is a non-empty string
    assert isinstance(resp.errors, str), f"errors should be str, got {type(resp.errors)}"
    assert len(resp.errors) > 0, "errors should be non-empty"
    # hex is None
    assert resp.hex is None, "Failed compile should not return hex"
    # listing is None (compilation didn't get that far)
    assert resp.listing is None, "Failed compile should not return listing"
    # target and version are still present
    assert resp.target == "atmega328p"
    assert resp.version != "unknown"
    assert resp.fcpu == 16000000
    print(f"  error shape: errors={resp.errors[:60]}...")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS: {name}")
            except AssertionError as e:
                print(f"  FAIL: {name}: {e}")
                sys.exit(1)
    print("All tests passed.")
