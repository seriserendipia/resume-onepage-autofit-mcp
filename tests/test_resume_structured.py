import pytest
from resume_structured import strip_markdown, parse_date_range, parse_location

@pytest.mark.parametrize("src,out", [
    ("**Acme** Corp", "Acme Corp"),
    ("__Acme__ and _x_ and *y*", "Acme and x and y"),
    ("[LinkedIn](https://linkedin.com/in/j)", "LinkedIn"),
    (r"C\# and 5 \* 3", "C# and 5 * 3"),
    ("  a   b\u00a0c  ", "a b c"),
    ("cut churn by **12%**", "cut churn by 12%"),
])
def test_strip_markdown(src, out):
    assert strip_markdown(src) == out

D = lambda raw, y, m: {"raw": raw, "year": y, "month": m, "iso": f"{y}-{m:02d}"}

def test_date_canonical_range():
    r = parse_date_range("Sep 2022 – Feb 2023")
    assert r == {"start": D("Sep 2022", 2022, 9), "end": D("Feb 2023", 2023, 2),
                 "current": False, "canonical": "Sep 2022 – Feb 2023", "loose": False}

def test_date_present():
    r = parse_date_range("Aug 2026 – Present")
    assert r["end"] is None and r["current"] is True and r["loose"] is False

def test_date_single_month():
    r = parse_date_range("Oct 2025")
    assert r["start"] == r["end"] == D("Oct 2025", 2025, 10)
    assert r["current"] is False and r["canonical"] == "Oct 2025" and r["loose"] is False

@pytest.mark.parametrize("src,canonical", [
    ("September 2022 - February 2023", "Sep 2022 – Feb 2023"),
    ("Sep 2022-Feb 2023", "Sep 2022 – Feb 2023"),
    ("Sep. 2022 — Feb. 2023", "Sep 2022 – Feb 2023"),
    ("sep 2022 – current", "Sep 2022 – Present"),
    ("Jan 2024 – Now", "Jan 2024 – Present"),
    ("Sep – Dec 2025", "Sep 2025 – Dec 2025"),
    ("Oct 2025 - Oct 2025", "Oct 2025"),   # same-month range: canonical is the single month
    ("Oct 2025 – Oct 2025", "Oct 2025"),
    ("Sept 2022 – Present", "Sep 2022 – Present"),
])
def test_date_loose_forms_parse_and_are_flagged(src, canonical):
    r = parse_date_range(src)
    assert r["canonical"] == canonical and r["loose"] is True
    assert r["start"]["raw"] == canonical.split(" – ")[0]

def test_date_year_only():
    r = parse_date_range("2021 – 2023")
    assert r["start"] == {"raw": "2021", "year": 2021, "month": None, "iso": "2021"}
    assert r["end"]["year"] == 2023 and r["canonical"] is None and r["loose"] is True

@pytest.mark.parametrize("src", ["Los Angeles, CA", "Remote", "", "Spring semester", "2022 to now-ish"])
def test_date_not_a_date(src):
    assert parse_date_range(src) is None

@pytest.mark.parametrize("src,exp,ok", [
    ("Perris, CA", {"raw": "Perris, CA", "city": "Perris", "state": "CA", "country": "United States", "remote": False}, True),
    ("Shanghai, China", {"raw": "Shanghai, China", "city": "Shanghai", "state": None, "country": "China", "remote": False}, True),
    ("remote", {"raw": "remote", "city": None, "state": None, "country": None, "remote": True}, True),
    ("Washington, D.C., United States", {"raw": "Washington, D.C., United States", "city": "Washington, D.C.", "state": None, "country": "United States", "remote": False}, True),
    ("Bay Area", {"raw": "Bay Area", "city": None, "state": None, "country": None, "remote": False}, False),
    ("London, UK", {"raw": "London, UK", "city": "London", "state": None, "country": "UK", "remote": False}, True),
    ("Toronto, ON", {"raw": "Toronto, ON", "city": "Toronto", "state": None, "country": "ON", "remote": False}, True),
    ("San Juan, PR", {"raw": "San Juan, PR", "city": "San Juan", "state": "PR", "country": "United States", "remote": False}, True),
    ("Remote, US", {"raw": "Remote, US", "city": None, "state": None, "country": "US", "remote": True}, True),
    ("remote, CA", {"raw": "remote, CA", "city": None, "state": None, "country": "United States", "remote": True}, True),
])
def test_location(src, exp, ok):
    assert parse_location(src) == (exp, ok)


# --- more Markdown stripping and date branches -------------------------------

@pytest.mark.parametrize("src,out", [
    ("***Both***", "Both"),
    ("snake_case_name stays", "snake_case_name stays"),
    ("**[Site](https://x.example)**", "Site"),
    ("Built models in `dbt`", "Built models in dbt"),
    ("`*args*` stays", "*args* stays"),            # marks inside a code span are literal
])
def test_strip_markdown_more(src, out):
    assert strip_markdown(src) == out

def test_date_single_year_and_year_present():
    r = parse_date_range("2023")
    assert r["start"] == r["end"] == {"raw": "2023", "year": 2023, "month": None, "iso": "2023"}
    assert r["canonical"] is None and r["loose"] is True and r["current"] is False
    r = parse_date_range("2021 – Present")
    assert r["start"]["month"] is None and r["end"] is None and r["current"] is True
    assert r["canonical"] is None and r["loose"] is True


# --- block scanner ------------------------------------------------------------

from resume_structured import scan_blocks

SAMPLE = (
    "# Jane Doe\n"
    "SF, CA | jane@email.com\n"
    "\n"
    "## Experience\n"
    "\n"
    "**Acme** · Lead · Paris, France *Jan 2022 – Present*\n"
    "\n"
    "- Label: first line\n"
    "  continues here\n"
    "* Second bullet\n"
    "\n"
    "Plain paragraph that ends with *italic*.\n"
    "\n"
    "*fully italic line*\n"
    "\n"
    "School Name _Sep 2017 – Jun 2019_\n"
)

def test_scan_blocks_types_and_lines():
    b = scan_blocks(SAMPLE)
    assert [(x["type"], x["line"]) for x in b] == [
        ("h1", 1), ("para", 2), ("h2", 4), ("para", 6), ("bullet", 8), ("bullet", 10),
        ("para", 12), ("para", 14), ("para", 16)]

def test_scan_blocks_trailing_italic():
    b = scan_blocks(SAMPLE)
    assert b[3]["text"] == "**Acme** · Lead · Paris, France" and b[3]["trailing"] == "Jan 2022 – Present"
    assert b[6]["trailing"] is None      # text follows the italic
    assert b[7]["trailing"] is None      # the whole paragraph is italic
    assert b[8]["trailing"] == "Sep 2017 – Jun 2019"

def test_scan_blocks_bullet_continuation():
    assert scan_blocks(SAMPLE)[4]["text"] == "Label: first line continues here"

def test_scan_blocks_line_endings_and_nbsp():
    messy = SAMPLE.replace("\n", "\r\n").replace("Lead · Paris", "Lead\u00a0· Paris").replace("Present*", "Present*   ")
    strip = lambda bs: [{k: v for k, v in x.items()} for x in bs]
    assert strip(scan_blocks(messy)) == strip(scan_blocks(SAMPLE))


# Each case states what markdown-it + tagEntryHeaders (js/resume_renderer.js) do.
@pytest.mark.parametrize("para,text,trailing", [
    ("Acme **bold end**", "Acme **bold end**", None),        # last element is <strong>
    ("Acme ***Jan 2022***", "Acme", "**Jan 2022**"),          # <em><strong>…</strong></em>
    ("x *a **b** c*", "x", "a **b** c"),                      # <strong> inside the <em>
    ("Acme ___Jan___", "Acme", "__Jan__"),
    ("**Acme *Jan 2022***", "**Acme *Jan 2022***", None),     # <em> inside a trailing <strong>
    ("Acme *a* then *Jan 2022*", "Acme *a* then", "Jan 2022"),  # only the last <em>
    ("Acme *Jan 2022* **x**", "Acme *Jan 2022* **x**", None),  # <strong> after the <em>
    ("snake_case_name_", "snake_case_name_", None),          # intraword _ is not emphasis
    ("Acme * Jan 2022 *", "Acme * Jan 2022 *", None),        # spaced * is not emphasis
    ("Line one\nAcme *Jan 2022*", "Line one Acme", "Jan 2022"),  # multi-line paragraph
])
def test_scan_blocks_trailing_italic_agrees_with_renderer(para, text, trailing):
    [b] = scan_blocks(para + "\n")
    assert (b["type"], b["text"], b["trailing"]) == ("para", text, trailing)

def test_scan_blocks_markers_interrupt_paragraphs():
    b = scan_blocks("Intro line\n## Skills\n- a\nlazy continuation\n## Next\n")
    assert [(x["type"], x["line"], x["text"]) for x in b] == [
        ("para", 1, "Intro line"), ("h2", 2, "Skills"), ("bullet", 3, "a lazy continuation"), ("h2", 5, "Next")]


# --- document builder and format warnings -------------------------------------

import json
from pathlib import Path
from resume_structured import parse_resume_structured

FIX = Path(__file__).parent / "fixtures"
read = lambda n: (FIX / n).read_text(encoding="utf-8")

def test_canonical_resume_matches_expected_document():
    doc, fw = parse_resume_structured(read("structured_canonical.md"))
    assert fw == []
    assert doc == json.loads(read("structured_canonical.json"))
    assert doc["warnings"] == []

def test_personal_header_is_never_emitted():
    md = "# Zed Qwerty\nNowhere, ZZ | (000) 111-2222 | zed@nowhere.example\n\n## Summary\nHello.\n"
    doc, _ = parse_resume_structured(md)
    blob = json.dumps(doc)
    for secret in ("Zed", "Qwerty", "Nowhere", "111-2222", "zed@nowhere.example"):
        assert secret not in blob

@pytest.mark.parametrize("md", ["", "just some text\n", "# Only A Name\n"])
def test_no_sections(md):
    doc, fw = parse_resume_structured(md)
    assert doc["sections"] == [] and fw == []

def _exp(md_body):
    doc, fw = parse_resume_structured("# N\n\n## Experience\n\n" + md_body)
    return doc["sections"][0], doc, fw

def test_parts_are_split_then_cleaned():
    sec, _, fw = _exp("**Acme** · [Lead](https://x.example) · Paris, France *Jan 2022 – Present*\n")
    e = sec["entries"][0]
    assert (e["company"], e["title"], e["location"]["country"]) == ("Acme", "Lead", "France")
    assert e["raw"] == "Acme · Lead · Paris, France" and e["id"] == "experience-1" and fw == []

def test_two_part_experience_has_null_location():
    sec, doc, fw = _exp("Acme · Lead *Jan 2022 – Mar 2022*\n")
    assert sec["entries"][0]["location"] is None and fw == [] and doc["warnings"] == []

def test_entry_line_without_date_is_kept_and_flagged():
    sec, doc, fw = _exp("Acme · Lead · Paris, France\n\n- Did: a thing\n- Did: another\n")
    assert sec["entries"] == []
    assert sec["paragraphs"] == ["Acme · Lead · Paris, France"]
    assert [b["raw"] for b in sec["bullets"]] == ["Did: a thing", "Did: another"]
    assert [(w["rule"], w["source_line"]) for w in fw] == [("entry-line", 5)]
    assert doc["warnings"][0]["entry_id"] is None

def test_bullet_label_and_continuation():
    sec, _, _ = _exp("Acme · Lead *Jan 2022*\n\n- **Churn Modeling:** Built a\n  pipeline\n- No label here\n")
    b = sec["entries"][0]["bullets"]
    assert b[0] == {"raw": "Churn Modeling: Built a pipeline", "label": "Churn Modeling", "text": "Built a pipeline"}
    assert b[1] == {"raw": "No label here", "label": None, "text": "No label here"}

def test_plain_paragraph_after_entry_goes_to_lines():
    sec, _, _ = _exp("Acme · Lead *Jan 2022*\n\nA one-line description.\n\n- X: y\n")
    assert sec["entries"][0]["lines"] == [{"raw": "A one-line description.", "trailing": None}]

def test_skills_groups():
    doc, fw = parse_resume_structured("# N\n\n## Skills\n- **Programming:** Python, SQL (PostgreSQL, BigQuery), Go\n- Docker, Git\n")
    g = doc["sections"][0]["groups"]
    assert g[0]["category"] == "Programming"
    assert g[0]["items"] == [
        {"raw": "Python", "name": "Python", "details": []},
        {"raw": "SQL (PostgreSQL, BigQuery)", "name": "SQL", "details": ["PostgreSQL", "BigQuery"]},
        {"raw": "Go", "name": "Go", "details": []}]
    assert g[1]["category"] is None and [i["name"] for i in g[1]["items"]] == ["Docker", "Git"]
    assert [w["rule"] for w in fw] == ["skills"]

def test_education_is_generic_with_degree_line():
    md = "# N\n\n## Education\n\nUniversity of Example *Aug 2023 – May 2025*\n\nMaster of Science in Statistics (GPA: 3.9/4.0) *San Francisco, CA*\n"
    doc, fw = parse_resume_structured(md)
    s = doc["sections"][0]
    assert s["kind"] == "other" and len(s["entries"]) == 1 and fw == []
    e = s["entries"][0]
    assert e["id"] == "education-1" and e["parts"] == ["University of Example"]
    assert e["lines"] == [{"raw": "Master of Science in Statistics (GPA: 3.9/4.0)", "trailing": "San Francisco, CA"}]

def test_variants_fixture_warnings():
    doc, fw = parse_resume_structured(read("structured_variants.md"))
    rules = [w["rule"] for w in fw]
    for rule in ("section-title", "date", "entry-parts", "location", "duplicate-section", "skills", "entry-line"):
        assert rule in rules, rule
    by_found = {w["found"]: w for w in fw}
    assert by_found["September 2022 - February 2023"]["expected"] == "Sep 2022 – Feb 2023"
    assert by_found["PROFESSIONAL EXPERIENCE"]["expected"] == "Experience"
    kinds = [s["kind"] for s in doc["sections"]]
    assert kinds.count("experience") == 1 and "other" in kinds
    # loose-but-parsed dates are a writing issue only; they are not downstream warnings
    assert not any("September" in json.dumps(w) for w in doc["warnings"])
    assert any(w["field"] == "start" and "month" in w["message"] for w in doc["warnings"])


# --- more builder, scanner, entry-line, date and warning branches -------------

def test_variants_fixture_full_warning_list():
    doc, fw = parse_resume_structured(read("structured_variants.md"))
    assert [(w["source_line"], w["rule"], w["found"], w["expected"]) for w in fw] == [
        (4, "section-title", "PROFESSIONAL EXPERIENCE", "Experience"),
        (6, "entry-line", "Initech · Analyst · Austin, TX", "Company · Job Title · Location *Mon YYYY – Mon YYYY*"),
        (11, "location", "Bay Area", "City, ST | City, Country | Remote"),
        (11, "date", "September 2022 - February 2023", "Sep 2022 – Feb 2023"),
        (15, "entry-parts", "Umbrella Works · Engineer · Platform Team · Boston, MA", "Company · Job Title · Location *Mon YYYY – Mon YYYY*"),
        (15, "location", "Platform Team", "City, ST | City, Country | Remote"),
        (15, "date", "2019 – 2021", "Mon YYYY – Mon YYYY"),
        (25, "section-title", "Technical Skills", "Skills"),
        (27, "skills", "Python, SQL, Docker", "- Category: item, item, item"),
        (30, "duplicate-section", "Experience", "one Experience section"),
    ]
    assert doc["warnings"] == [
        {"entry_id": None, "field": "entry", "message": "content before the first entry line; the entry line may be missing its date"},
        {"entry_id": "experience-1", "field": "location", "message": "location not recognized"},
        {"entry_id": "experience-2", "field": "parts", "message": "entry line has 4 parts, expected 2 or 3"},
        {"entry_id": "experience-2", "field": "location", "message": "location not recognized"},
        {"entry_id": "experience-2", "field": "start", "message": "date has no month"},
        {"entry_id": "experience-2", "field": "end", "message": "date has no month"},
        {"entry_id": None, "field": "kind", "message": "second experience section, treated as other"},
    ]
    umbrella = doc["sections"][0]["entries"][1]
    assert (umbrella["company"], umbrella["title"], umbrella["location"]["raw"]) == ("Umbrella Works", "Engineer", "Platform Team")
    sidequest = doc["sections"][1]["entries"][0]
    assert (sidequest["name"], sidequest["role"], sidequest["location"]) == ("Sidequest", None, None)
    # ids stay unique although the duplicate Experience section also uses the "experience" prefix
    assert doc["sections"][3]["entries"][0]["id"] == "experience-3"
    # the Notes section holds the tricky trailing-italic cases (pinned against the page in
    # test_structured_sidecar.py); an `other` section adds no warnings for them
    notes = doc["sections"][4]
    assert (notes["title"], notes["kind"], notes["paragraphs"], notes["bullets"]) == ("Notes", "other", [], [])
    assert [(e["raw"], e["date_raw"], [(l["raw"], l["trailing"]) for l in e["lines"]],
             [b["raw"] for b in e["bullets"]]) for e in notes["entries"]] == [
        ("Acme", "a b", [], []),
        ("Foo snake_case_name_", "Jan 2020", [("Price *not italic*", None)], []),
        ("Acme · Site", "Jan 2020", [("Two-line paragraph that ends in an", "italic")], []),
        ("Under", "Jan 2020", [], []),
        ("Code a*b", "Jan 2020", [("Tail x .", None), ("Heading with italic", None)],
         ["item ending in italic"]),
        ("Led a team of 2. engineers", "Jan 2020", [], []),
    ]

def test_unparseable_date_in_experience_warns():
    sec, doc, fw = _exp("Acme · Lead *Summer 2019*\n")
    e = sec["entries"][0]
    assert (e["date_raw"], e["start"], e["end"], e["current"]) == ("Summer 2019", None, None, False)
    assert [(w["rule"], w["expected"]) for w in fw] == [("date", "Mon YYYY – Mon YYYY")]
    assert doc["warnings"] == [{"entry_id": "experience-1", "field": "date", "message": "date not recognized"}]

def test_experience_with_one_part_warns():
    sec, doc, fw = _exp("Acme *Jan 2022*\n")
    e = sec["entries"][0]
    assert (e["company"], e["title"], e["location"]) == ("Acme", None, None)
    assert [w["rule"] for w in fw] == ["entry-parts"]

def test_projects_with_four_parts_warns():
    doc, fw = parse_resume_structured("# N\n\n## Projects\n\nA · B · Remote · D *Jan 2022*\n")
    e = doc["sections"][0]["entries"][0]
    assert (e["name"], e["role"], e["location"]["remote"]) == ("A", "B", True)
    assert [(w["rule"], w["expected"]) for w in fw] == [("entry-parts", "Project Name · Your Role *Mon YYYY – Mon YYYY*")]

def test_other_section_non_date_trailing():
    md = ("# N\n\n## Certifications\n\n"
          "Cloud Practitioner *Online*\n\n"        # no entry yet: starts an entry, no date, no warning
          "Issued by Example Org *Verified*\n\n"   # entry has no bullets: becomes a line
          "- ID: 123\n\n"
          "Data Analyst Cert *Remote*\n")           # entry has bullets: starts a new entry
    doc, fw = parse_resume_structured(md)
    s = doc["sections"][0]
    assert fw == [] and doc["warnings"] == []
    assert [(e["id"], e["raw"], e["start"]) for e in s["entries"]] == [
        ("certifications-1", "Cloud Practitioner", None), ("certifications-2", "Data Analyst Cert", None)]
    assert s["entries"][0]["lines"] == [{"raw": "Issued by Example Org", "trailing": "Verified"}]

def test_loose_date_in_other_section_is_flagged_but_not_a_downstream_warning():
    doc, fw = parse_resume_structured("# N\n\n## Education\n\nSchool *Sep 2017 - Jun 2019*\n")
    assert [(w["rule"], w["expected"]) for w in fw] == [("date", "Sep 2017 – Jun 2019")]
    assert doc["warnings"] == []

def test_summary_joins_paragraphs_and_bullets():
    doc, _ = parse_resume_structured("# N\n\n## Profile\n\nFirst **para**.\n\nSecond para.\n\n- A bullet\n")
    assert doc["sections"][0] == {"title": "Profile", "kind": "summary", "text": "First para.\nSecond para.\nA bullet"}

def test_content_after_a_later_h1_is_skipped():
    doc, _ = parse_resume_structured("# N\n\n## Summary\n\nHello.\n\n# Other Name\n\nsecret line\n\n## Awards\n\n- Prize\n")
    assert "secret" not in json.dumps(doc)
    assert [s["title"] for s in doc["sections"]] == ["Summary", "Awards"]

def test_document_envelope():
    doc, _ = parse_resume_structured("# N\n\n## Summary\n\nHello.\n")
    assert list(doc) == ["schema_version", "generator", "warnings", "sections"]
    assert (doc["schema_version"], doc["generator"]) == ("1.0", "resume-onepage-autofit-mcp")


# --- stray dot, same-month range, horizontal rules -----------------------------

def test_date_same_month_range_has_single_month_canonical():
    r = parse_date_range("Oct 2025 – Oct 2025")
    assert r["start"] == r["end"] == D("Oct 2025", 2025, 10)
    assert r["canonical"] == "Oct 2025" and r["loose"] is True

def test_scan_blocks_skips_horizontal_rules():
    md = "## Summary\n\nHello.\n\n---\n\n## Experience\n\nAcme · Lead *Jan 2022*\n***\n- X: y\n___\n"
    assert [(b["type"], b["line"]) for b in scan_blocks(md)] == [
        ("h2", 1), ("para", 3), ("h2", 7), ("para", 9), ("bullet", 11)]

@pytest.mark.parametrize("section,line,fields", [
    ("Experience", "Acme · Lead · Paris, France · *Jan 2022 – Present*",
     {"company": "Acme", "title": "Lead", "raw": "Acme · Lead · Paris, France"}),
    ("Projects", "tinyqueue · Maintainer · *Nov 2022*",
     {"name": "tinyqueue", "role": "Maintainer", "raw": "tinyqueue · Maintainer"}),
])
def test_dot_before_date_is_dropped_and_flagged(section, line, fields):
    doc, fw = parse_resume_structured(f"# N\n\n## {section}\n\n{line}\n")
    e = doc["sections"][0]["entries"][0]
    assert {k: e[k] for k in fields} == fields
    if section == "Experience":
        assert e["location"]["country"] == "France"
    expected = {"Experience": "Company · Job Title · Location *Mon YYYY – Mon YYYY*",
                "Projects": "Project Name · Your Role *Mon YYYY – Mon YYYY*"}[section]
    assert [(w["source_line"], w["rule"], w["expected"]) for w in fw] == [(5, "entry-parts", expected)]
    assert doc["warnings"] == []


# --- escaped backticks, one entry-parts warning per line ---------------------

def test_strip_markdown_keeps_escaped_backticks():
    assert strip_markdown(r"Use \`x\` and \`y\`") == "Use `x` and `y`"

def test_stray_dot_and_too_many_parts_give_one_entry_parts_warning():
    _, fw = parse_resume_structured("# N\n\n## Experience\n\nA · B · C · D · *Jan 2022*\n")
    assert [w for w in fw if w["rule"] == "entry-parts"] == [
        {"source_line": 5, "rule": "entry-parts", "found": "A · B · C · D",
         "expected": "Company · Job Title · Location *Mon YYYY – Mon YYYY*"}]


# --- deeper headings and ordered lists -----------------------------------------

def test_deeper_heading_is_a_plain_paragraph_not_an_entry():
    doc, fw = parse_resume_structured(
        "# N\n\n## Experience\n\n### Google · Engineer · Mountain View, CA *Jan 2022 – Present*\n")
    s = doc["sections"][0]
    assert s["entries"] == []
    assert s["paragraphs"] == ["Google · Engineer · Mountain View, CA Jan 2022 – Present"]
    assert [(w["source_line"], w["rule"]) for w in fw] == [(5, "entry-line")]

def test_scan_blocks_deeper_heading_keeps_no_trailing():
    assert scan_blocks("###### Deep *x*") == [{"type": "para", "line": 1, "text": "Deep *x*", "trailing": None}]

def test_ordered_list_item_is_a_bullet():
    doc, fw = parse_resume_structured(
        "# N\n\n## Experience\n\nAcme · Lead · Austin, TX *Jan 2022 – Present*\n\n1. Migrated services to *Kubernetes*\n")
    entries = doc["sections"][0]["entries"]
    assert len(entries) == 1 and fw == [] and doc["warnings"] == []
    assert entries[0]["bullets"] == [{"raw": "Migrated services to Kubernetes", "label": None,
                                      "text": "Migrated services to Kubernetes"}]
    assert [b["type"] for b in scan_blocks("2) second")] == ["bullet"]


# --- full state names, numbered lines inside paragraphs -------------------------

@pytest.mark.parametrize("src,city,state", [
    ("San Francisco, California", "San Francisco", "CA"),
    ("Austin, texas", "Austin", "TX"),
    ("Washington, District of Columbia", "Washington", "DC"),
    ("Tbilisi, Georgia", "Tbilisi", "GA"),   # ambiguous by nature: read as the US state
])
def test_location_full_state_name(src, city, state):
    loc, ok = parse_location(src)
    assert ok and loc == {"raw": src, "city": city, "state": state,
                          "country": "United States", "remote": False}

def test_full_state_name_is_flagged_with_canonical_form():
    doc, fw = parse_resume_structured(
        "# N\n\n## Experience\n\nAcme · Lead · San Francisco, California *Jan 2022 – Present*\n")
    assert fw == [{"source_line": 5, "rule": "location", "found": "San Francisco, California",
                   "expected": "San Francisco, CA"}]
    assert doc["warnings"] == []
    assert doc["sections"][0]["entries"][0]["location"]["state"] == "CA"

def test_numbered_line_other_than_1_continues_a_paragraph():
    assert scan_blocks("Led a team of\n2. engineers *Jan 2020*") == [
        {"type": "para", "line": 1, "text": "Led a team of 2. engineers", "trailing": "Jan 2020"}]

def test_numbered_line_1_interrupts_a_paragraph():
    assert [b["type"] for b in scan_blocks("Intro line\n1. first")] == ["para", "bullet"]

def test_any_number_starts_a_bullet_after_a_blank_line():
    assert [(b["type"], b["text"]) for b in scan_blocks("Intro line\n\n2. second")] == [
        ("para", "Intro line"), ("bullet", "second")]
