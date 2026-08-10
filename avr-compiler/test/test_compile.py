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
