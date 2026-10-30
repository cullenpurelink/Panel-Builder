#!/usr/bin/env python3
"""
Static file server for the PureLink module suite, plus three extra routes:
POST /api/git-push — commits any changes with an auto message and pushes.
POST /api/save-product-icon — writes a generated product icon file to
  system-diagrams/assets/products/ (used by the Product Icon Generator's
  "Save to library" button instead of a manual browser download).
POST /api/publish-to-library — writes a panel's layout JSON into
  data/library/ and registers it in data/library/manifest.json (used by
  Panel Builder's "Publish to System Diagrams library" export option).
POST /api/export-content-xlsx — builds a .xlsx from a Content Builder
  record, shaped to match the real PureTools product masterfile tabs
  (Silk&feature data / BURO+ info / PIM Upload row 5 / Label Text), and
  returns it as a file download (used by Content Builder's Export button).

Used by start.bat instead of plain `python -m http.server` so the Hub's
"Push to GitHub" button, the icon generator's save button, Panel
Builder's publish button, and Content Builder's Excel export have
something to call. Everything else behaves exactly like the plain
static server.
"""
import base64
import http.server
import io
import json
import re
import subprocess
import sys
import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 8743
PRODUCT_ICONS_DIR = REPO_ROOT / "system-diagrams" / "assets" / "products"
SAFE_ICON_NAME = re.compile(r"^Product_[A-Za-z0-9_-]+\.(svg|png)$")
LIBRARY_DIR = REPO_ROOT / "data" / "library"
MANIFEST_PATH = LIBRARY_DIR / "manifest.json"
SAFE_LIBRARY_NAME = re.compile(r"^[a-z0-9-]+-layout\.json$")


def build_content_workbook(r):
    """Shapes a Content Builder record into the same tabs/columns as the
    real PureTools product masterfile (Silk&feature data, BURO+ info, PIM
    Upload row 5 only, Label Text) so it drops into existing downstream
    processes unchanged. Values are written as plain text/numbers, not
    formulas: the app is the live source of truth now, this file is a
    one-way export snapshot, not something meant to be hand-edited and
    recalculated in Excel.
    """
    wb = openpyxl.Workbook()
    bold = Font(bold=True)

    def sheet(name, headers, values, start_col=1):
        ws = wb.create_sheet(name)
        for i, h in enumerate(headers):
            c = ws.cell(row=1, column=start_col + i, value=h)
            c.font = bold
        for i, v in enumerate(values):
            ws.cell(row=2, column=start_col + i, value=v)
        return ws

    wb.remove(wb.active)

    features = (r.get("features") or []) + [""] * 5
    features = features[:10] if len(features) > 5 else (features + [""] * (5 - len(features)))[:5]
    label_features = (r.get("labelFeatures") or []) + [""] * 5
    label_features = label_features[:5]
    feature_images = (r.get("featureImages") or []) + [""] * 4
    feature_images = feature_images[:4]
    sku = r.get("sku") or ""
    name = r.get("name") or ""
    silk_desc = r.get("silkDescription") or ""
    long_desc = (name + " - " + ". ".join(f for f in features if f)).strip(" -")

    sheet(
        "Silk&feature data",
        ["#", "Supplier Model", "PureLink Article Number", 'Packaging sticker "Item Description"',
         "Silk Screen Heading", 'Silk screen - Bold Blue "Type"', 'Silk Screen - Small blue "Type"',
         "Silk Screen - Description Line 1 and 2", "Feature Title",
         "Feature 1", "Feature 2", "Feature 3", "Feature 4", "Feature 5", "EAN#"],
        [1, r.get("supplierModel", ""), sku, r.get("packagingDescription", ""),
         r.get("silkHeading", "PureTools"), r.get("silkTypeBold", ""), r.get("silkTypeSmall", ""),
         silk_desc, r.get("featureTitle", ""), *features, r.get("ean", "")],
    )

    sheet(
        "BURO+ info",
        ["#", "Supplier model name", "PureLink Article Number", "search key", "Short description",
         "Long description", "Price", "MOQ", "Feature Title",
         "Feature 1", "Feature 2", "Feature 3", "Feature 4", "Feature 5", "EAN#"],
        [1, r.get("supplierModel", ""), sku, r.get("searchKey", ""), (name + " - " + silk_desc).strip(" -"),
         long_desc, r.get("price"), r.get("moq"), r.get("featureTitle", ""), *features, r.get("ean", "")],
    )

    # PIM Upload: row 5 of the real file only — the batch-entry rows and the
    # legacy second attribute block are deliberately not reproduced here.
    ws = wb.create_sheet("PIM Upload")
    pim_codes = ["ID", "EXTERNALKEY", "NAME", "ATTRIBUTE478", "ATTRIBUTE480", "ATTRIBUTE491", "ATTRIBUTE492",
                 "ATTRIBUTE493", "ATTRIBUTE494", "ATTRIBUTE495", "ATTRIBUTE496", "ATTRIBUTE497", "ATTRIBUTE498",
                 "ATTRIBUTE499", "ATTRIBUTE500", "ATTRIBUTE322959", "ATTRIBUTE322960", "ATTRIBUTE531",
                 "ATTRIBUTE532", "ATTRIBUTE533", "ATTRIBUTE534", "NAVIGATIONPATH", "ATTRIBUTE548",
                 "ATTRIBUTE537", "ATTRIBUTE18643", "DATECREATED", "DATEMODIFIED"]
    pim_labels = ["ID", "EXTERNALKEY", "NAME", "Online Headline/Title", "Item Description Headline",
                  "Feature 1", "Feature 2", "Feature 3", "Feature 4", "Feature 5", "Feature 6", "Feature 7",
                  "Feature 8", "Feature 9", "Feature 10", "Feature 11 (Usecase)", "Feature 12 (Prompt Ergänzung)",
                  "Feature image 1", "Feature image 2", "Feature image 3", "Feature image 4", "NAVIGATIONPATH",
                  "Picture 1", "Cross-Selling", "Article properties (Filter)", "DATECREATED", "DATEMODIFIED"]
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    pim_values = ["", "", name, r.get("onlineHeadline", ""), r.get("itemDescriptionHeadline", ""),
                  *features, "", "", "", "", "", r.get("useCase", ""), r.get("additionalContext", ""),
                  *feature_images, r.get("navigationPath", ""), "", r.get("crossSelling", ""),
                  r.get("articleProperties", ""), now, now]
    for i, v in enumerate(pim_codes):
        ws.cell(row=3, column=2 + i, value=v).font = bold
    for i, v in enumerate(pim_labels):
        ws.cell(row=4, column=2 + i, value=v).font = bold
    for i, v in enumerate(pim_values):
        ws.cell(row=5, column=2 + i, value=v)

    sheet(
        "Label Text",
        ["#", "Supplier model name", 'Packaging sticker "Item Description"', "Abw. ArtNr.", "HEADLINE",
         "Feature 1", "Feature 2", "Feature 3", "Feature 4", "Feature 5", "EAN"],
        [1, r.get("supplierModel", ""), r.get("packagingDescription", ""), sku, r.get("featureTitle", ""),
         *label_features, r.get("ean", "")],
        start_col=2,
    )

    sheet(
        "Power point slide",
        ["Title", "Partnumber", "Feature 1", "Feature 2", "Feature 3", "Feature 4", "Feature 5",
         "Use Case", "UVP"],
        [name, sku, *features, r.get("useCase", ""), r.get("price")],
        start_col=23,  # matches the real tab's columns starting at W
    )

    return wb


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
        if self.path == "/api/git-push":
            ok, log = self.git_push()
            self._send_json({"ok": ok, "log": log})
        elif self.path == "/api/save-product-icon":
            ok, msg = self.save_product_icon()
            self._send_json({"ok": ok, "msg": msg}, status=200 if ok else 400)
        elif self.path == "/api/publish-to-library":
            ok, msg = self.publish_to_library()
            self._send_json({"ok": ok, "msg": msg}, status=200 if ok else 400)
        elif self.path == "/api/export-content-xlsx":
            self.export_content_xlsx()
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def save_product_icon(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
            filename = payload["filename"]
            if not SAFE_ICON_NAME.match(filename):
                return False, f"rejected filename: {filename}"
            data = payload["dataBase64"]
            if data.startswith("data:"):
                data = data.split(",", 1)[1]
            raw = base64.b64decode(data)
            PRODUCT_ICONS_DIR.mkdir(parents=True, exist_ok=True)
            (PRODUCT_ICONS_DIR / filename).write_bytes(raw)
            return True, f"saved {filename} ({len(raw)} bytes)"
        except Exception as e:
            return False, str(e)

    def publish_to_library(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
            filename = payload["filename"]
            if not SAFE_LIBRARY_NAME.match(filename):
                return False, f"rejected filename: {filename}"
            content = payload["content"]
            json.loads(content)  # validate it's real JSON before writing anything

            LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
            (LIBRARY_DIR / filename).write_text(content, encoding="utf-8", newline="\n")

            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else []
            added = filename not in manifest
            if added:
                manifest.insert(0, filename)
                MANIFEST_PATH.write_text(
                    json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
                )

            return True, (
                f"published {filename}" + (" and added to manifest.json" if added else " (already in manifest.json)")
            )
        except Exception as e:
            return False, str(e)

    def export_content_xlsx(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            record = json.loads(self.rfile.read(length))
            wb = build_content_workbook(record)
            buf = io.BytesIO()
            wb.save(buf)
            data = buf.getvalue()
        except Exception as e:
            self._send_json({"ok": False, "msg": str(e)}, status=400)
            return
        base = re.sub(r"[^A-Za-z0-9-]+", "-", (record.get("sku") or record.get("name") or "content").strip()).strip("-") or "content"
        filename = f"{base}-masterfile.xlsx"
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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
    print(f"Serving {REPO_ROOT} at http://127.0.0.1:{port} (with /api/git-push, /api/save-product-icon, /api/publish-to-library, /api/export-content-xlsx)")
    server.serve_forever()
