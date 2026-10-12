#!/usr/bin/env python3
"""
Static file server for the PureLink module suite, plus one extra route:
POST /api/git-push — commits any changes with an auto message and pushes.

Used by start.bat instead of plain `python -m http.server` so the Hub's
"Push to GitHub" button has something to call. Everything else behaves
exactly like the plain static server.
"""
import http.server
import json
import subprocess
import sys
import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 8743


def run_git(*args, timeout=30):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 1, (
            "git " + " ".join(args) + " timed out after " + str(timeout) + "s "
            "(a sign-in window may be waiting for you)"
        )
    return result.returncode, (result.stdout or "") + (result.stderr or "")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def do_POST(self):
        if self.path != "/api/git-push":
            self.send_response(404)
            self.end_headers()
            return
        ok, log = self.git_push()
        body = json.dumps({"ok": ok, "log": log}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def git_push(self):
        log_lines = []

        code, out = run_git("status", "--porcelain")
        log_lines.append(out)
        if code != 0:
            return False, "\n".join(log_lines)

        if out.strip():
            code, out = run_git("add", "-A")
            log_lines.append(out)
            if code != 0:
                return False, "\n".join(log_lines)

            message = "Update " + datetime.datetime.now().strftime("%d %b %Y %H:%M")
            code, out = run_git("commit", "-m", message)
            log_lines.append(out)
            if code != 0:
                return False, "\n".join(log_lines)
        else:
            log_lines.append("Nothing to commit, checking for unpushed commits...")

        code, out = run_git("push", "-u", "origin", "HEAD", timeout=120)
        log_lines.append(out)
        if code != 0:
            return False, "\n".join(log_lines)

        return True, "\n".join(log_lines)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Serving {REPO_ROOT} at http://127.0.0.1:{port} (with /api/git-push)")
    server.serve_forever()
