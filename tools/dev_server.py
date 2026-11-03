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
POST /api/draft-content — drafts Feature Title, the 5 Features, Use Case
  and Label Text for a Content Builder record from its seed notes and
  linked Product Builder panels' real ports, via the Anthropic API (used
  by Content Builder's "Draft with AI" button). Needs an API key — see
  get_anthropic_key() below.
POST /api/export-content-prd-docx — builds a .docx PRD (the PureLink
  house PRD style issued to ODM factories) from a Content Builder
  record's `concept` fields, embedding PNG renders of the linked
  panel(s) that the client renders live from Panel Builder and posts
  alongside the record (used by Content Builder's "Export to Word"
  button).

Used by start.bat instead of plain `python -m http.server` so the Hub's
"Push to GitHub" button, the icon generator's save button, Panel
Builder's publish button, Content Builder's Excel export, and Content
Builder's AI drafting have something to call. Everything else behaves
exactly like the plain static server.
"""
import base64
import http.server
import io
import json
import os
import re
import subprocess
import sys
import datetime
import urllib.error
import urllib.request
from pathlib import Path

import openpyxl
from openpyxl.styles import Font
from docx import Document
from docx.shared import Mm

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 8743
PRODUCT_ICONS_DIR = REPO_ROOT / "system-diagrams" / "assets" / "products"
SAFE_ICON_NAME = re.compile(r"^Product_[A-Za-z0-9_-]+\.(svg|png)$")
LIBRARY_DIR = REPO_ROOT / "data" / "library"
MANIFEST_PATH = LIBRARY_DIR / "manifest.json"
SAFE_LIBRARY_NAME = re.compile(r"^[a-z0-9-]+-layout\.json$")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-5-5"
ANTHROPIC_KEY_FILE = REPO_ROOT / "tools" / "anthropic_key.txt"
ANTHROPIC_KEY_FILE_FALLBACK = REPO_ROOT / "tools" / "anthropic key.txt"

DRAFT_SYSTEM_PROMPT = (
    "You write PIM, label and sales copy for PureLink, an AV-over-IP hardware brand. "
    "Write only in British English (colour, optimise, licence as a noun, and so on). "
    "Base every claim strictly on the product facts and port list you are given — "
    "never invent a connector, spec or capability that isn't listed, and never "
    "guess a port count that wasn't given to you. "
    "Match the terse, feature-led style of real PureLink copy, "
    "for example a Feature Title like \"2x1 5K HDBaseT Presentation Switch\". "
    "Reply with ONLY a single JSON object — no markdown code fences, no commentary "
    "before or after it — shaped exactly as: "
    '{"featureTitle": "...", "features": ["...", "...", "...", "...", "..."], '
    '"useCase": "...", "labelFeatures": ["...", "...", "...", "...", "..."]}. '
    "featureTitle is one short product title line. "
    "features is exactly 5 concise feature/benefit sentences drawn from the seed "
    "notes and port list. "
    "useCase is a short paragraph describing one real-world scenario this product "
    "solves for the people who'd buy it. "
    "labelFeatures is the same 5 features abbreviated to 24 characters or fewer "
    "each (count every character, including spaces), for printing on a physical "
    "product label — abbreviate aggressively while staying clear."
)


def get_anthropic_key():
    """ANTHROPIC_API_KEY env var wins; otherwise a plain-text key in
    tools/anthropic_key.txt (gitignored) — easier to set for anyone who
    isn't comfortable with environment variables."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key and key.strip():
        return key.strip()
    for path in (ANTHROPIC_KEY_FILE, ANTHROPIC_KEY_FILE_FALLBACK):
        if path.exists():
            key = path.read_text(encoding="utf-8").strip()
            if key:
                return key
    return None


def build_draft_prompt(payload):
    product = payload.get("product") or {}
    existing = payload.get("existing") or {}
    ports = payload.get("ports") or []

    lines = [
        f"Product name: {product.get('name') or '(not set)'}",
        f"SKU: {product.get('sku') or '(not set)'}",
    ]
    if product.get("supplierModel"):
        lines.append(f"Supplier model: {product['supplierModel']}")
    lines.append("")
    lines.append("Seed notes from the product owner:")
    lines.append(payload.get("seed") or "(none given)")

    if payload.get("additionalContext"):
        lines.append("")
        lines.append("Additional context (extra raw material for a complex product):")
        lines.append(payload["additionalContext"])

    if ports:
        lines.append("")
        lines.append(
            "Real ports/connectors from the linked Product Builder panel(s) — "
            "ground features in these, do not invent others:"
        )
        for p in ports:
            bits = [p.get("panel") or "", p.get("side") or "", p.get("type") or "", p.get("func") or "", p.get("label") or ""]
            lines.append("- " + " / ".join(b for b in bits if b))
    else:
        lines.append("")
        lines.append(
            "No panels linked yet — do not invent specific port counts or "
            "connector types; keep features general to the seed notes."
        )

    if existing.get("featureTitle") or any(existing.get("features") or []) or existing.get("useCase"):
        lines.append("")
        lines.append("Existing draft text to improve on rather than discard outright:")
        if existing.get("featureTitle"):
            lines.append(f"Feature Title: {existing['featureTitle']}")
        for i, f in enumerate(existing.get("features") or []):
            if f:
                lines.append(f"Feature {i + 1}: {f}")
        if existing.get("useCase"):
            lines.append(f"Use Case: {existing['useCase']}")

    return "\n".join(lines)


def call_anthropic_draft(key, payload):
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1500,
        "system": DRAFT_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": build_draft_prompt(payload)}],
    }).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"Anthropic API error {e.code}: {detail[:300]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Couldn't reach the Anthropic API: {e.reason}")

    text = "".join(
        block.get("text", "") for block in result.get("content", []) if block.get("type") == "text"
    )
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        draft = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError("The draft wasn't valid JSON — try again. Raw reply: " + text[:200])

    features = (draft.get("features") or [])[:5]
    features += [""] * (5 - len(features))
    label_features = (draft.get("labelFeatures") or [])[:5]
    label_features += [""] * (5 - len(label_features))
    return {
        "featureTitle": str(draft.get("featureTitle") or ""),
        "features": [str(f) for f in features],
        "useCase": str(draft.get("useCase") or ""),
        "labelFeatures": [str(f) for f in label_features],
    }


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


def _doc_table(doc, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for cell, h in zip(table.rows[0].cells, headers):
        cell.text = h
        cell.paragraphs[0].runs[0].bold = True
    for row in rows:
        cells = table.add_row().cells
        for cell, v in zip(cells, row):
            cell.text = "" if v is None else str(v)
    return table


def build_prd_document(r):
    """Shapes a Content Builder record's `concept` fields into the same
    PRD structure PureLink itself issues to ODM factories (see
    PT-MA-HD88/PT-PSW-21HC-KVM's own PRDs) — only the sections the user
    chose to include when this was built. Blank where nothing could be
    inferred from Content Builder/Panel Builder/System Diagrams, for the
    team to fill in by hand; not every field is auto-fillable by design.
    """
    c = r.get("concept") or {}
    tech = c.get("techSpec") or {}
    name = r.get("name") or "(unnamed product)"
    sku = r.get("sku") or ""

    doc = Document()
    doc.add_heading("Product Requirement Document (PRD)", level=0)
    doc.add_paragraph(name)

    _doc_table(doc, ["Product Model", "Product Description", "Product Type"],
               [[sku, name, c.get("productType") or ""]])

    if c.get("shortDesc") or c.get("targetMarket"):
        doc.add_heading("Positioning", level=1)
        if c.get("shortDesc"):
            doc.add_paragraph(c["shortDesc"])
        if c.get("targetMarket"):
            p = doc.add_paragraph()
            p.add_run("Target market: ").bold = True
            p.add_run(c["targetMarket"])

    doc.add_heading("Revision History", level=1)
    rev = c.get("revisionHistory") or []
    _doc_table(doc, ["Version", "Prepared", "Verify", "Date", "Notes"],
               [[x.get("version", ""), x.get("prepared", ""), x.get("verify", ""), x.get("date", ""), x.get("notes", "")] for x in rev]
               or [["", "", "", "", ""]])
    if c.get("approvalSignoff"):
        doc.add_paragraph("Approval: " + c["approvalSignoff"])

    doc.add_heading("1. Product Description", level=1)
    doc.add_paragraph(c.get("description") or "(TBD)")

    doc.add_heading("2. Features", level=1)
    feats = [f for f in (r.get("features") or []) if f]
    if feats:
        for f in feats:
            doc.add_paragraph(f, style="List Bullet")
    else:
        doc.add_paragraph("(TBD)")

    doc.add_heading("3. Technical Specifications", level=1)
    _doc_table(doc, ["Item", "Detail"], [
        ("Input Connectors", tech.get("inputConnectors")),
        ("Output Connectors", tech.get("outputConnectors")),
        ("Buttons and LEDs", tech.get("buttonsLeds")),
        ("Supported I/O Formats", tech.get("ioFormats")),
        ("Audio Format", tech.get("audioFormat")),
        ("Data Rate", tech.get("dataRate")),
        ("USB Hub Tiers", tech.get("usbTiers")),
        ("Control Method", tech.get("controlMethod")),
        ("EDID Setting", tech.get("edidSetting")),
    ])

    doc.add_heading("4. Function Details", level=1)
    led = c.get("ledBehaviour") or []
    if led:
        doc.add_paragraph("LED behaviour:")
        _doc_table(doc, ["LED", "On / off / blink meaning"], [[x.get("led", ""), x.get("meaning", "")] for x in led])
    for label, key in [("Power behaviour", "powerBehaviour"), ("Firmware update", "firmwareUpdate"), ("Other functions", "otherFunctions")]:
        if c.get(key):
            p = doc.add_paragraph()
            p.add_run(label + ": ").bold = True
            p.add_run(c[key])

    doc.add_heading("5. Visuals", level=1)
    # Rendered live by the client from the linked panel's real Panel Builder
    # layout (the same source as Content Builder's on-screen reference
    # strip) and posted as PNG bytes — never a pre-generated icon file,
    # so the PRD can never show a stale or missing drawing just because
    # nobody ran the separate "save icon to library" step for this SKU.
    panel_images = [img for img in (r.get("panelImages") or []) if img.get("frontBase64") or img.get("rearBase64")]
    if panel_images:
        doc.add_paragraph("Silkscreen:")
        for img in panel_images:
            if img.get("frontBase64"):
                doc.add_picture(io.BytesIO(base64.b64decode(img["frontBase64"])), width=Mm(80))
        doc.add_paragraph("Interface layout:")
        for img in panel_images:
            if len(panel_images) > 1 and img.get("label"):
                doc.add_paragraph().add_run(img["label"]).bold = True
            if img.get("frontBase64"):
                doc.add_picture(io.BytesIO(base64.b64decode(img["frontBase64"])), width=Mm(80))
            if img.get("rearBase64"):
                doc.add_picture(io.BytesIO(base64.b64decode(img["rearBase64"])), width=Mm(80))
    else:
        doc.add_paragraph("Silkscreen: (size TBD — no panel linked, or the browser couldn't render it)")
        doc.add_paragraph("Interface layout: (TBD)")
    doc.add_paragraph("Application scenario: (no scenario rendered yet)")
    doc.add_paragraph("Block diagram: (TBD)")

    doc.add_heading("6. GUI Design List", level=1)
    doc.add_paragraph(c.get("guiDesignList") or "(TBD)")

    doc.add_heading("7. Installation & Structural", level=1)
    _doc_table(doc, ["Item", "Detail"], [
        ("Installation method", c.get("installationMethod") or ""),
        ("Dimensions", c.get("dimensions") or ""),
        ("Raw materials", c.get("rawMaterials") or ""),
    ])

    doc.add_heading("8. Certification", level=1)
    doc.add_paragraph(c.get("certificationDetails") or "(TBD)")

    doc.add_heading("9. Accessories & Packaging", level=1)
    acc = c.get("accessories") or []
    _doc_table(doc, ["No.", "Name", "Remark"],
               [[str(i + 1), x.get("name", ""), x.get("remark", "")] for i, x in enumerate(acc)] or [["1", "", ""]])
    _doc_table(doc, ["Item", "Detail"], [
        ("Power adapter", c.get("powerAdapterSpec") or ""),
        ("Label / sticker", c.get("labelType") or ""),
        ("User manual", c.get("userManual") or ""),
        ("Package type", c.get("packageType") or ""),
    ])

    doc.add_heading("10. Quotation", level=1)
    price, moq = r.get("price"), r.get("moq")
    bits = [b for b in [f"${price}" if price is not None else "", f"MOQ {moq}pcs" if moq is not None else ""] if b]
    doc.add_paragraph("Quotation: " + sku + (", " + ", ".join(bits) if bits else " (TBD)"))
    if c.get("sampleQuantity"):
        doc.add_paragraph("Sample quantity: " + c["sampleQuantity"])

    doc.add_heading("11. Open Questions", level=1)
    oq = (c.get("openQuestions") or "").strip()
    if oq:
        for line in oq.splitlines():
            if line.strip():
                doc.add_paragraph(line.strip(), style="List Bullet")
    else:
        doc.add_paragraph("(none)")

    doc.add_heading("12. Authorized Signature", level=1)
    _doc_table(doc, ["PureLink GmbH", "Supplier"], [["", c.get("signatureSupplierName") or ""]])

    return doc


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

    def end_headers(self):
        # This server exists so every edit shows up on the next reload —
        # SimpleHTTPRequestHandler sends Last-Modified but no Cache-Control,
        # which lets browsers heuristically cache a page for a while and
        # silently keep serving it after a real edit. Restarting this
        # process doesn't fix that either: the stale copy lives in the
        # browser, not here. A page load should always hit the disk.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

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
        elif self.path == "/api/export-content-prd-docx":
            self.export_content_prd_docx()
        elif self.path == "/api/draft-content":
            self.draft_content()
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

    def export_content_prd_docx(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            record = json.loads(self.rfile.read(length))
            doc = build_prd_document(record)
            buf = io.BytesIO()
            doc.save(buf)
            data = buf.getvalue()
        except Exception as e:
            self._send_json({"ok": False, "msg": str(e)}, status=400)
            return
        base = re.sub(r"[^A-Za-z0-9-]+", "-", (record.get("sku") or record.get("name") or "content").strip()).strip("-") or "content"
        filename = f"{base}-concept-prd.docx"
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def draft_content(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
        except Exception as e:
            self._send_json({"ok": False, "msg": f"bad request: {e}"}, status=400)
            return
        key = get_anthropic_key()
        if not key:
            self._send_json({
                "ok": False,
                "msg": "No Anthropic API key configured. Set the ANTHROPIC_API_KEY "
                       "environment variable, or put the key alone in "
                       "tools/anthropic_key.txt, then restart the server.",
            }, status=400)
            return
        try:
            draft = call_anthropic_draft(key, payload)
        except Exception as e:
            self._send_json({"ok": False, "msg": str(e)}, status=502)
            return
        self._send_json({"ok": True, "draft": draft})

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
    print(f"Serving {REPO_ROOT} at http://127.0.0.1:{port} (with /api/git-push, /api/save-product-icon, /api/publish-to-library, /api/export-content-xlsx, /api/export-content-prd-docx, /api/draft-content)")
    server.serve_forever()
