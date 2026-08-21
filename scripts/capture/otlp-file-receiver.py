#!/usr/bin/env python3
"""Minimal OTLP/HTTP receiver that writes every export request body to its own file.

Used by docs/runbooks/claude-code-capture.md to capture a real Claude Code emission for
the F1 fixture corpus. It deliberately does nothing but persist bytes: the artefact under
capture is the `ExportTraceServiceRequest` exactly as the emitter sent it, so decoding,
re-encoding or pretty-printing here would destroy the thing being collected.

Standard library only, no dependencies, Python 3.9+.

    python3 scripts/capture/otlp-file-receiver.py --out ~/plumbline-captures/2026-08-21

Handles the two transports the Claude Code exporter uses in practice: chunked transfer
encoding, and gzip content encoding. Writes the *decompressed* body, because gzip is a
transport detail the collector re-applies itself.
"""

import argparse
import datetime
import gzip
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Receiver(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    out_dir: pathlib.Path
    count = 0

    def do_POST(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        body = self._read_body()

        if self.headers.get("Content-Encoding", "").lower() == "gzip":
            try:
                body = gzip.decompress(body)
            except OSError as exc:
                print(f"  ! gzip decode failed ({exc}); writing the raw bytes", file=sys.stderr)

        Receiver.count += 1
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S")
        suffix = "json" if "json" in self.headers.get("Content-Type", "") else "pb"
        name = f"{Receiver.count:04d}-{stamp}-{self.path.strip('/').replace('/', '_')}.{suffix}"
        path = self.out_dir / name
        path.write_bytes(body)

        print(f"  {path.name}: {len(body)} bytes  ({self.headers.get('Content-Type', 'unknown type')})")

        self.send_response(200)
        self.send_header("Content-Type", "application/x-protobuf")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _read_body(self) -> bytes:
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            chunks = []
            while True:
                size_line = self.rfile.readline().strip()
                size = int(size_line.split(b";")[0], 16)
                if size == 0:
                    self.rfile.readline()  # trailing CRLF
                    break
                chunks.append(self.rfile.read(size))
                self.rfile.readline()  # CRLF after each chunk
            return b"".join(chunks)

        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def log_message(self, *_args) -> None:
        """Silence the default access log; the write line above is the useful one."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="directory for captured bodies (keep it OUTSIDE the repository)")
    parser.add_argument("--port", type=int, default=4318)
    args = parser.parse_args()

    out = pathlib.Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    if pathlib.Path.cwd() in out.parents or out.is_relative_to(pathlib.Path.cwd()):
        print(
            f"refusing to write captures into {out}: a raw capture carries user.id, user.email "
            "and organization.id, and this repository is public. Choose a directory outside it.",
            file=sys.stderr,
        )
        return 2

    Receiver.out_dir = out
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Receiver)
    print(f"listening on http://127.0.0.1:{args.port}, writing to {out}")
    print("stop with Ctrl-C when the Claude Code session has finished")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\ncaptured {Receiver.count} export request(s) into {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
