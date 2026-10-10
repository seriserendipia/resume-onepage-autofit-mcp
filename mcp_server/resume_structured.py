"""Parse resume Markdown into a structured JSON document plus format warnings.

The document holds every `## ` section of the resume (summary, skills,
experience, projects and any other section), split into fields with the text
as printed; the warnings list the lines that do not follow the canonical forms
described in the render_resume_pdf tool. Pure standard-library Python; no browser.
"""
from __future__ import annotations  # README promises Python 3.8+

import re

# --- Markdown stripping ------------------------------------------------------

# A backslash before ASCII punctuation is an escape. Escaped characters are
# parked in the Private Use Area while emphasis is removed, then restored.
_ESCAPE = re.compile(r"\\([!-/:-@\[-`{-~])")
_PARKED = re.compile("[\ue000-\ue07f]")
_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_EMPHASIS = [
    re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*"),
    re.compile(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)"),
    re.compile(r"\*(?=\S)(.+?)(?<=\S)\*"),
    re.compile(r"(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w)"),
]


def _park(text):
    return re.sub(r"[!-/:-@\[-`{-~]", lambda m: chr(0xE000 + ord(m.group(0))), text)


def strip_markdown(text: str) -> str:
    """Remove code, emphasis and link syntax, undo escapes, collapse whitespace."""
    text = text.replace("\\`", _park("`"))  # an escaped backtick never opens a code span
    text = _CODE.sub(lambda m: _park(m.group(1)), text)  # code content is literal
    text = _ESCAPE.sub(lambda m: _park(m.group(1)), text)
    text = _LINK.sub(r"\1", text)
    previous = None
    while previous != text:  # repeat so nested marks (***x***) unwrap fully
        previous = text
        for pattern in _EMPHASIS:
            text = pattern.sub(r"\1", text)
    text = _PARKED.sub(lambda m: chr(ord(m.group(0)) - 0xE000), text)
    return " ".join(text.replace("\u00a0", " ").split())


# --- Block scanner ----------------------------------------------------------

_RULE = re.compile(r"-{3,}|\*{3,}|_{3,}")
_HEADING = re.compile(r"(#{1,2})(?:[ \t]+(.*))?$")
_MINOR_HEADING = re.compile(r"#{3,6}[ \t]+(.*)$")  # renders as <h3>-<h6>, never an entry header
# Ordered list items count as bullets. Inside a paragraph only `1.` / `1)` starts
# a list (as in CommonMark); any other number continues the paragraph.
_BULLET = re.compile(r"(?:[-*+]|(\d+)[.)])[ \t]+(.*)$")
# A paragraph ends in an <em> when its last characters close one of these.
# They mirror markdown-it: `*` may open inside a word, `_` may not; neither may
# sit next to whitespace on the inner side; an escaped `\*` is literal. The
# italic may hold a bold run (`*a **b***`, `***x***`).
_TRAILING_EM = [
    re.compile(r"(?<![*\\])\*(?!\s)((?:[^*]|\*\*[^*]+\*\*)+)(?<![\s\\])\*$"),
    re.compile(r"(?<![\w\\_])_(?!\s)((?:[^_]|__[^_]+__)+)(?<![\s\\])_$"),
]


def _split_trailing_italic(text):
    """Return (text before, italic inner text) or (text, None).

    Agrees with tagEntryHeaders in js/resume_renderer.js: the paragraph's last
    element is an <em>, only whitespace follows it, and text precedes it.
    """
    for pattern in _TRAILING_EM:
        m = pattern.search(text)
        if m:
            before = text[:m.start()].rstrip()
            return (before, m.group(1)) if before else (text, None)
    return text, None


def scan_blocks(markdown: str) -> list[dict]:
    """Split Markdown into h1 / h2 / bullet / para blocks with 1-based line numbers."""
    text = markdown.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    blocks, current = [], None
    for number, line in enumerate(text.split("\n"), 1):
        line = line.strip()
        if not line or _RULE.fullmatch(line):  # a horizontal rule is not text
            current = None
        elif m := _HEADING.match(line):
            kind = "h1" if len(m.group(1)) == 1 else "h2"
            blocks.append({"type": kind, "line": number, "text": m.group(2) or "", "trailing": None})
            current = None
        elif m := _MINOR_HEADING.match(line):
            # A plain paragraph of its own; "minor" keeps its trailing italic attached
            blocks.append({"type": "para", "line": number, "text": m.group(1), "trailing": None, "minor": True})
            current = None
        elif (m := _BULLET.match(line)) and (
                m.group(1) in (None, "1") or current is None or current["type"] != "para"):
            current = {"type": "bullet", "line": number, "text": m.group(2), "trailing": None}
            blocks.append(current)
        elif current is None:
            current = {"type": "para", "line": number, "text": line, "trailing": None}
            blocks.append(current)
        else:  # continuation line: same paragraph, or the bullet it follows
            current["text"] += " " + line
    for block in blocks:
        if block.pop("minor", False):
            continue
        if block["type"] == "para":
            block["text"], block["trailing"] = _split_trailing_italic(block["text"])
    return blocks


# --- Dates ------------------------------------------------------------------

_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MONTH_FULL = ["january", "february", "march", "april", "may", "june", "july",
               "august", "september", "october", "november", "december"]
_MONTHS = {name: i + 1 for i, name in enumerate(_MONTH_FULL)}
_MONTHS.update({abbr.lower(): i + 1 for i, abbr in enumerate(_MONTH_ABBR)})
_MONTHS["sept"] = 9

_SEP = r"\s*[-\u2013\u2014]\s*"
_POINT = r"(?:([A-Za-z]+)\.?\s+)?(\d{4})"
_RANGE = re.compile(rf"^{_POINT}{_SEP}(?:{_POINT}|(present|current|now))$", re.I)
_SHARED_YEAR = re.compile(rf"^([A-Za-z]+)\.?{_SEP}([A-Za-z]+)\.?\s+(\d{{4}})$")
_SINGLE = re.compile(rf"^{_POINT}$")

_NO_MONTH = object()  # month word that is not a month name


def _month(word):
    if word is None:
        return None
    return _MONTHS.get(word.lower(), _NO_MONTH)


def _date_point(month, year):
    year = int(year)
    if month is None:
        return {"raw": str(year), "year": year, "month": None, "iso": str(year)}
    return {"raw": f"{_MONTH_ABBR[month - 1]} {year}", "year": year,
            "month": month, "iso": f"{year}-{month:02d}"}


def parse_date_range(text: str) -> dict | None:
    """Parse an entry-line date. Returns None when the text is not a date.

    Result: {start, end, current, canonical, loose}. `canonical` is the
    canonical spelling (None when a month is missing); `loose` is true when the
    input is not already canonical.
    """
    text = text.strip()
    current = False
    if m := _SINGLE.match(text):
        months = [_month(m.group(1))]
        start_pair = end_pair = (months[0], m.group(2))
        single = True
    elif m := _RANGE.match(text):
        months = [_month(m.group(1)), _month(m.group(3))]
        start_pair = (months[0], m.group(2))
        current = m.group(5) is not None
        end_pair = None if current else (months[1], m.group(4))
        single = False
    elif m := _SHARED_YEAR.match(text):
        months = [_month(m.group(1)), _month(m.group(2))]
        start_pair, end_pair = (months[0], m.group(3)), (months[1], m.group(3))
        single = False
    else:
        return None
    if _NO_MONTH in months:
        return None

    start = _date_point(*start_pair)
    end = None if end_pair is None else _date_point(*end_pair)
    if start["month"] is None or (end is not None and end["month"] is None):
        canonical = None
    elif single or end == start:  # a same-month range is written as one month
        canonical = start["raw"]
    else:
        canonical = f"{start['raw']} \u2013 {'Present' if current else end['raw']}"
    return {"start": start, "end": end, "current": current,
            "canonical": canonical, "loose": canonical is None or text != canonical}


# --- Locations --------------------------------------------------------------

_US_STATE_CODES = frozenset("""
    AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO
    MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY
    DC PR GU VI AS MP
""".split())
# Full names written after the comma ("Austin, Texas"); keys are lower case.
_US_STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN",
    "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}


def _state_name_fix(text):
    """Canonical `City, ST` when `text` ends in a full US state name, else None."""
    head, sep, tail = text.rpartition(",")
    code = _US_STATE_NAMES.get(tail.strip().lower()) if sep else None
    return f"{head.strip()}, {code}" if code and head.strip() else None


def parse_location(text: str) -> tuple[dict, bool]:
    """Parse a location part. The bool is False when the form is not recognized."""
    loc = {"raw": text, "city": None, "state": None, "country": None, "remote": False}
    if text.strip().lower() == "remote":
        loc["remote"] = True
        return loc, True
    if "," in text:
        city, tail = (s.strip() for s in text.rsplit(",", 1))
        if city and tail:
            if city.lower() == "remote":  # "Remote, US": remote within a country
                loc["remote"] = True
            else:
                loc["city"] = city
            code = tail if tail in _US_STATE_CODES else _US_STATE_NAMES.get(tail.lower())
            if code:
                loc["country"] = "United States"
                if not loc["remote"]:
                    loc["state"] = code
            else:
                loc["country"] = tail
            return loc, True
    return loc, False


# --- Bullets and skills -----------------------------------------------------

def _split_label(raw):
    """(label, text) when `: ` starts within the first 40 characters, else (None, raw)."""
    i = raw.find(": ")
    if 0 < i < 40:
        return raw[:i].strip(), raw[i + 2:].strip()
    return None, raw


def _bullet(markdown):
    raw = strip_markdown(markdown)
    label, text = _split_label(raw)
    return {"raw": raw, "label": label, "text": text}


def _split_outside_parens(text):
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


_SKILL_DETAILS = re.compile(r"(.+?)\s*\((.*)\)")


def _skill_item(raw):
    m = _SKILL_DETAILS.fullmatch(raw)
    if not m:
        return {"raw": raw, "name": raw, "details": []}
    details = [d.strip() for d in m.group(2).split(",") if d.strip()]
    return {"raw": raw, "name": m.group(1).strip(), "details": details}


# --- Section kinds, and the canonical templates given as `expected` ---------

_SECTION_TITLES = {
    "summary": ["summary", "professional summary", "profile", "objective"],
    "skills": ["skills", "technical skills", "core skills"],
    "experience": ["experience", "work experience", "professional experience", "employment"],
    "projects": ["projects", "project experience", "selected projects"],
}
_ENTRY_TEMPLATE = {
    "experience": "Company · Job Title · Location *Mon YYYY – Mon YYYY*",
    "projects": "Project Name · Your Role *Mon YYYY – Mon YYYY*",
}
_ENTRY_FIELDS = {"experience": ("company", "title"), "projects": ("name", "role")}
_PARTS_EXPECTED = {"experience": "2 or 3", "projects": "1 to 3"}
_DATE_TEMPLATE = "Mon YYYY – Mon YYYY"
_LOCATION_TEMPLATE = "City, ST | City, Country | Remote"
_SKILLS_TEMPLATE = "- Category: item, item, item"
_PART_SEPARATOR = re.compile(r"\s+·\s+")
_DOT_BEFORE_DATE = re.compile(r"\s+·$")


# --- Document builder -------------------------------------------------------

class _Builder:
    def __init__(self):
        self.format_warnings = []
        self.warnings = []
        self.sections = []
        self._kinds_seen = set()
        self._id_counts = {}

    def flag(self, line, rule, found, expected):
        self.format_warnings.append({"line": line, "rule": rule, "found": found, "expected": expected})

    def warn(self, entry_id, field, message):
        self.warnings.append({"entry_id": entry_id, "field": field, "message": message})

    def next_id(self, prefix):
        # Counted per prefix across the file so ids stay unique even when two
        # sections share a prefix (e.g. a duplicate Experience section).
        self._id_counts[prefix] = self._id_counts.get(prefix, 0) + 1
        return f"{prefix}-{self._id_counts[prefix]}"

    def section_kind(self, heading, title):
        key = title.lower()
        kind = next((k for k, names in _SECTION_TITLES.items() if key in names), "other")
        if kind == "other":
            return kind
        canonical = _SECTION_TITLES[kind][0].capitalize()
        if key != _SECTION_TITLES[kind][0]:
            self.flag(heading["line"], "section-title", title, canonical)
        if kind in self._kinds_seen:
            self.flag(heading["line"], "duplicate-section", title, f"one {canonical} section")
            self.warn(None, "kind", f"second {kind} section, treated as other")
            return "other"
        self._kinds_seen.add(kind)
        return kind

    def add_section(self, heading, body):
        title = strip_markdown(heading["text"])
        kind = self.section_kind(heading, title)
        if kind == "summary":
            section = {"title": title, "kind": kind, "text": _summary_text(body)}
        elif kind == "skills":
            section = {"title": title, "kind": kind, "groups": self.skill_groups(body)}
        else:
            section = self.entry_section(title, kind, body)
        self.sections.append(section)

    def skill_groups(self, body):
        groups = []
        for block in body:
            if block["type"] != "bullet":
                continue  # paragraphs in a skills section are not groups
            raw = strip_markdown(block["text"])
            category, rest = _split_label(raw)
            if category is None:
                self.flag(block["line"], "skills", raw, _SKILLS_TEMPLATE)
            groups.append({"raw": raw, "category": category,
                           "items": [_skill_item(s) for s in _split_outside_parens(rest)]})
        return groups

    def entry_section(self, title, kind, body):
        section = {"title": title, "kind": kind, "paragraphs": [], "bullets": [], "entries": []}
        prefix = kind if kind != "other" else (re.sub(r"[\W_]+", "-", title.lower()).strip("-") or "section")
        entry, stray_seen = None, False
        for block in body:
            is_para = block["type"] == "para"
            if is_para and block["trailing"] is not None:
                date = parse_date_range(strip_markdown(block["trailing"]))
                if kind == "other" and date is None and entry is not None and not entry["bullets"]:
                    entry["lines"].append({"raw": strip_markdown(block["text"]),
                                           "trailing": strip_markdown(block["trailing"])})
                else:
                    entry = self.entry(kind, prefix, block, date)
                    section["entries"].append(entry)
            elif entry is not None:
                if is_para:
                    entry["lines"].append({"raw": strip_markdown(block["text"]), "trailing": None})
                else:
                    entry["bullets"].append(_bullet(block["text"]))
            else:
                if is_para:
                    section["paragraphs"].append(strip_markdown(block["text"]))
                else:
                    section["bullets"].append(_bullet(block["text"]))
                # One warning per stray paragraph (likely a dateless entry line);
                # bullets under it add none, a stray bullet run gets one.
                if kind in _ENTRY_TEMPLATE and (is_para or not stray_seen):
                    self.flag(block["line"], "entry-line", strip_markdown(block["text"]), _ENTRY_TEMPLATE[kind])
                    self.warn(None, "entry",
                              "content before the first entry line; the entry line may be missing its date")
                stray_seen = True
        return section

    def entry(self, kind, prefix, block, date):
        text = block["text"]
        stray_dot = _DOT_BEFORE_DATE.search(text)
        if stray_dot:  # "A · B · *date*": the date follows the last part directly
            text = text[:stray_dot.start()]
        parts = [strip_markdown(p) for p in _PART_SEPARATOR.split(text)]
        entry = {"id": self.next_id(prefix), "raw": " · ".join(parts)}
        if kind == "other":
            entry["parts"] = parts
        else:
            parts_flagged = self.named_parts(kind, block, entry, parts)
            if stray_dot and not parts_flagged:  # one entry-parts warning per line
                self.flag(block["line"], "entry-parts", strip_markdown(block["text"]), _ENTRY_TEMPLATE[kind])
        self.date_fields(kind, block, entry, date)
        entry["lines"], entry["bullets"] = [], []
        return entry

    def named_parts(self, kind, block, entry, parts):
        """Fill the named fields; return True when the part count was flagged."""
        first, second = _ENTRY_FIELDS[kind]
        padded = parts[:3] + [None] * (3 - len(parts))
        entry[first], entry[second] = padded[0], padded[1]
        bad_count = len(parts) > 3 or (kind == "experience" and len(parts) < 2)
        if bad_count:
            self.flag(block["line"], "entry-parts", entry["raw"], _ENTRY_TEMPLATE[kind])
            self.warn(entry["id"], "parts",
                      f"entry line has {len(parts)} parts, expected {_PARTS_EXPECTED[kind]}")
        entry["location"] = None
        if padded[2] is not None:
            entry["location"], ok = parse_location(padded[2])
            if not ok:
                self.flag(block["line"], "location", padded[2], _LOCATION_TEMPLATE)
                self.warn(entry["id"], "location", "location not recognized")
            elif fixed := _state_name_fix(padded[2]):  # fields are right; only the spelling is off
                self.flag(block["line"], "location", padded[2], fixed)
        return bad_count

    def date_fields(self, kind, block, entry, date):
        entry["date_raw"] = strip_markdown(block["trailing"])
        if date is None:
            entry["start"], entry["end"], entry["current"] = None, None, False
            if kind != "other":
                self.flag(block["line"], "date", entry["date_raw"], _DATE_TEMPLATE)
                self.warn(entry["id"], "date", "date not recognized")
            return
        entry["start"], entry["end"], entry["current"] = date["start"], date["end"], date["current"]
        if date["loose"]:
            self.flag(block["line"], "date", entry["date_raw"], date["canonical"] or _DATE_TEMPLATE)
        if date["start"]["month"] is None:
            self.warn(entry["id"], "start", "date has no month")
        end = date["end"]
        if end is not None and end["month"] is None and end != date["start"]:
            self.warn(entry["id"], "end", "date has no month")


def _summary_text(body):
    lines = []
    for block in body:
        text = strip_markdown(block["text"])
        if block["trailing"] is not None:
            text = f"{text} {strip_markdown(block['trailing'])}"
        lines.append(text)
    return "\n".join(lines)


def parse_resume_structured(markdown: str) -> tuple[dict, list[dict]]:
    """Return (JSON document, format_warnings).

    The caller adds `pdf_file` and `generated_at`. Nothing outside a `## `
    section is emitted: the `# Name` line, the contact line under it, and
    anything else before the first `## ` (or after a later `# `) is skipped.
    """
    builder = _Builder()
    heading, body = None, []
    for block in scan_blocks(markdown) + [{"type": "end"}]:
        if block["type"] in ("h1", "h2", "end"):
            if heading is not None:
                builder.add_section(heading, body)
            heading = block if block["type"] == "h2" else None
            body = []
        elif heading is not None:
            body.append(block)
    doc = {"schema_version": "1.0", "generator": "resume-onepage-autofit-mcp",
           "warnings": builder.warnings, "sections": builder.sections}
    return doc, builder.format_warnings
