#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ALPH = "0123456789abcdefghijklmnopqrstuvwxyz$"
MOD = 37


def to_digits(text: str) -> list[int]:
    out: list[int] = []
    for ch in text:
        if "0" <= ch <= "9":
            out.append(ord(ch) - 48)
        elif "a" <= ch <= "z":
            out.append(ord(ch) - 87)
        elif "A" <= ch <= "Z":
            out.append(ord(ch) - 55)
        elif ch == "$":
            out.append(36)
        else:
            raise ValueError(f"unsupported character: {ch!r}")
    return out


def from_digits(values: list[int]) -> str:
    return "".join(ALPH[v] for v in values)


def encode_payload(payload: str) -> str:
    prefix = to_digits(payload)
    y = prefix + [
        sum(prefix) % MOD,
        sum(prefix[i] for i in range(len(prefix)) if i & 1) % MOD,
        sum(prefix[i] for i in range(len(prefix)) if not (i & 1)) % MOD,
    ]

    partials: list[int] = []
    acc = 0
    for value in y:
        acc = (acc + value) % MOD
        partials.append(acc)

    encoded = [0] * len(y)
    encoded[-1] = partials[-1]
    for i in range(len(y) - 2, -1, -1):
        encoded[i] = (partials[i] + encoded[i + 1]) % MOD
    return from_digits(encoded)


def split_encoded(encoded: str, split_prefix: int = 4) -> tuple[str, str]:
    if split_prefix <= 0 or split_prefix >= len(encoded):
        raise ValueError(f"invalid split_prefix={split_prefix} for encoded length {len(encoded)}")
    return encoded[:split_prefix], encoded[split_prefix:]


def runtime_decode(code: str, authorization: str) -> str | None:
    data = (authorization + code).replace("L", "l").replace(" ", "")
    values = to_digits(data)
    if len(values) > 99:
        return None

    if len(values) > 1:
        for i in range(len(values) - 1):
            values[i] = (values[i] - values[i + 1]) % MOD
        for i in range(len(values) - 1, 0, -1):
            values[i] = (values[i] - values[i - 1]) % MOD

    if len(values) < 3:
        return None

    prefix = values[:-3]
    checks = values[-3:]
    expect = [
        sum(prefix) % MOD,
        sum(prefix[i] for i in range(len(prefix)) if i & 1) % MOD,
        sum(prefix[i] for i in range(len(prefix)) if not (i & 1)) % MOD,
    ]
    if checks != expect:
        return None
    return from_digits(prefix)


def serial_blacklisted(serial: str) -> bool:
    if len(serial) == 8:
        return serial in {"10699393", "18461036"}
    if len(serial) == 11:
        return serial == "66610930394"
    if len(serial) == 12:
        return serial in {
            "301709301764",
            "401506209949",
            "501609127264",
            "501609129301",
            "501709301094",
        }
    return False


def emulate_runtime(payload: str, serial: str) -> str:
    encoded = encode_payload(payload)
    authorization = encoded[:5]
    code = encoded[5:]
    decoded = runtime_decode(code, authorization)
    if decoded is None:
        return "decode_failed"

    parts = decoded.split("$")
    if not parts or parts[0] != serial:
        return "serial_mismatch"
    if serial_blacklisted(serial):
        return "serial_blacklisted"
    if len(parts) < 7:
        return "missing_fields"

    try:
        f1 = int(parts[1])
        f2 = int(parts[2])
        f3 = int(parts[3])
        int(parts[4])
    except ValueError:
        return "int_parse_failed"

    if not parts[5] or parts[5][0] not in "abcdefgh":
        return "field5_invalid"
    if parts[6] and len(parts[6]) != 8:
        return "field6_invalid"
    if f2 != 24:
        return "network_disallowed"
    if f3 not in (2, 5):
        return "not_applicable"
    if f1 <= 179:
        return "status7"
    return "theoretical_success"


def write_license(
    runtime_dir: Path,
    serial: str,
    payload: str,
    line1: str = "LocalLab",
    line2: str = "LocalLab",
    split_prefix: int = 4,
) -> tuple[str, str, Path]:
    encoded = encode_payload(payload)
    authorization, code = split_encoded(encoded, split_prefix)
    checksum = sum(line1.encode()) + sum(line2.encode())
    lic_text = f"{serial}!{code}!{authorization}!{line1}!{line2}!{checksum}!"
    lic_path = runtime_dir / "stata.lic"
    lic_path.write_text(lic_text)
    return code, authorization, lic_path


def run_stata(runtime_dir: Path, libdir: Path, binary: str) -> str:
    try:
        proc = subprocess.run(
            [binary],
            cwd=runtime_dir,
            env={"LD_LIBRARY_PATH": str(libdir)},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + (exc.stderr or "")
    out = re.sub(r"\x1b\[[0-9;?=]*[A-Za-z]", "", out)
    out = out.replace("\x1b=", "").replace("\x1b>", "")
    return out.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime-dir",
        default="/home/epictus/ctf/stata18-toolkit/runtime/stata-local",
    )
    parser.add_argument(
        "--libdir",
        default="/home/epictus/ctf/stata18-toolkit/runtime/localdeps/ncurses5/usr/lib",
    )
    parser.add_argument("--serial", default="12345678")
    parser.add_argument("--payload", required=True)
    parser.add_argument("--line1", default="LocalLab")
    parser.add_argument("--line2", default="LocalLab")
    parser.add_argument("--split-prefix", type=int, default=4)
    parser.add_argument("--binary", default="./stata")
    parser.add_argument("--write-license", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    runtime_dir = Path(args.runtime_dir)
    libdir = Path(args.libdir)

    encoded = encode_payload(args.payload)
    authorization, code = split_encoded(encoded, args.split_prefix)
    decoded = runtime_decode(code, authorization)
    status = emulate_runtime(args.payload, args.serial)

    print(f"payload={args.payload}")
    print(f"encoded={encoded}")
    print(f"split_prefix={args.split_prefix}")
    print(f"authorization={authorization}")
    print(f"code={code}")
    print(f"decoded={decoded}")
    print(f"emulated_status={status}")

    if args.write_license:
        _, _, lic_path = write_license(
            runtime_dir,
            args.serial,
            args.payload,
            args.line1,
            args.line2,
            args.split_prefix,
        )
        print(f"license_path={lic_path}")

    if args.run:
        print("--- stata ---")
        print(run_stata(runtime_dir, libdir, args.binary))


if __name__ == "__main__":
    main()
