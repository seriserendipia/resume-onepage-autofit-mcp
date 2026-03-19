# Tests Directory

This directory contains tests for the Resume MCP Server project.

## Test Files

### `test_inline_formatting.py`
Tests for inline formatting rendering (bold, italic, date alignment).
Uses Playwright to render actual HTML and verify:
- `<strong>` inside `<p>` is NOT `display:block` (prevents unwanted line breaks)
- Bold text stays on same line as surrounding text
- Dates in `*italic*` at line end are right-aligned via `float:right`
- Inline italic in body text is NOT floated
- h1 is centered and larger than h2
- h2 has bottom border (underline)

Run:
```bash
python -m pytest tests/test_inline_formatting.py -v
```

### `test_release_safety.py`
Validates that sensitive files are properly excluded before publishing:
- Checks `.gitignore` contains personal config files
- Verifies example files exist
- Ensures example configs don't contain personal info

Run before each release:
```bash
python tests/test_release_safety.py
```

## Running All Tests

```bash
cd resume-onepage-autofit-mcp
conda activate agent_env
python -m pytest tests/ -v
```

## Test Categories

| File | Purpose | When to Run |
|------|---------|-------------|
| `test_inline_formatting.py` | Layout & CSS validation | After CSS/rendering changes |
| `test_release_safety.py` | Release validation | Before publishing |
