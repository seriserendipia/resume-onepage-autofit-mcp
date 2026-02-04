# Tests Directory

This directory contains tests for the Resume MCP Server project.

## Long-term Reusable Tests

### `test_release_safety.py`
Validates that sensitive files are properly excluded before publishing:
- Checks `.gitignore` contains personal config files
- Verifies example files exist
- Ensures example configs don't contain personal info

Run before each release:
```bash
python tests/test_release_safety.py
```

## Running Tests

```bash
cd resume-onepage-autofit-mcp
conda activate agent_env
python -m pytest tests/ -v
```

## Test Categories

| File | Purpose | When to Run |
|------|---------|-------------|
| `test_release_safety.py` | Release validation | Before publishing |
