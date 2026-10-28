"""Loopback-only static server for the Fabuloom Character Stage."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlsplit


FRONTEND_ROOT = Path(__file__).resolve().parent
EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports").resolve()


class StageHandler(BaseHTTPRequestHandler):
    server_version = "FabuloomStage/0.3"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = unquote(urlsplit(self.path).path)
        if path.startswith("/exports/"):
            root = EXPORT_ROOT
            relative = path.removeprefix("/exports/")
        else:
            root = FRONTEND_ROOT
            relative = path.removeprefix("/") or "index.html"
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            self.send_error(403, "path outside the local stage roots")
            return
        if not candidate.is_file():
            self.send_error(404, "resource not found")
            return
        content_type = "text/javascript" if candidate.suffix == ".ts" else mimetypes.guess_type(candidate.name)[0]
        content_type = content_type or "application/octet-stream"
        payload = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[stage] {self.address_string()} {format % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), StageHandler)
    print(f"Fabuloom Character Stage: http://127.0.0.1:{args.port}/")
    print("Only loopback requests are accepted; exports are limited to the Fabuloom workspace.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStage server stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
