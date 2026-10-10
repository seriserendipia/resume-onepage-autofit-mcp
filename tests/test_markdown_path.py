"""
render_resume_pdf takes the resume as a file path (markdown_path), not as inline text.
These tests cover reading that file on Linux and Windows; none of them start a browser.
"""
import sys

import pytest

# `mcp_server` is the package when run alone, but the module once test_mcp_server.py
# has put mcp_server/ first on sys.path during collection.
try:
    from mcp_server.mcp_server import read_markdown_file, handle_call_tool, handle_list_tools
except ImportError:
    from mcp_server import read_markdown_file, handle_call_tool, handle_list_tools

RESUME = "# Jane Doe\n\n## Skills\n\n- Languages: Python\n"
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows path forms")
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX path forms")


def _write(path, data: bytes):
    path.write_bytes(data)
    return str(path)


# --- reading ------------------------------------------------------------------

def test_reads_absolute_path(tmp_path):
    p = _write(tmp_path / "resume.md", RESUME.encode("utf-8"))
    text, err = read_markdown_file(p)
    assert err is None and text == RESUME


def test_crlf_and_bom_are_normalized(tmp_path):
    # Notepad on Windows saves UTF-8 with a BOM and CRLF line endings.
    p = _write(tmp_path / "resume.md", b"\xef\xbb\xbf" + RESUME.replace("\n", "\r\n").encode("utf-8"))
    text, err = read_markdown_file(p)
    assert err is None and text == RESUME


def test_non_ascii_path_and_content(tmp_path):
    d = tmp_path / "简历 folder"
    d.mkdir()
    p = _write(d / "张三 resume.md", "# 张三\n".encode("utf-8"))
    text, err = read_markdown_file(p)
    assert err is None and text == "# 张三\n"


@pytest.mark.parametrize("quote", ['"', "'"])
def test_surrounding_quotes_and_whitespace_are_stripped(tmp_path, quote):
    # Windows Explorer "Copy as path" wraps the path in double quotes.
    p = _write(tmp_path / "my resume.md", RESUME.encode("utf-8"))
    text, err = read_markdown_file(f"  {quote}{p}{quote}\n")
    assert err is None and text == RESUME


def test_home_directory_is_expanded(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))          # POSIX
    monkeypatch.setenv("USERPROFILE", str(tmp_path))   # Windows
    _write(tmp_path / "resume.md", RESUME.encode("utf-8"))
    text, err = read_markdown_file("~/resume.md")
    assert err is None and text == RESUME


# --- errors -------------------------------------------------------------------

@pytest.mark.parametrize("raw", [None, "", "   ", 42])
def test_missing_path(raw):
    text, err = read_markdown_file(raw)
    assert text is None and err["error_code"] == "INVALID_PATH"


@pytest.mark.parametrize("raw", ["resume.md", "./resume.md", "generated_resume/resume.md"])
def test_relative_path_is_rejected(raw):
    # Relative paths would resolve against the server's working directory,
    # which is not the agent's workspace.
    text, err = read_markdown_file(raw)
    assert text is None and err["error_code"] == "INVALID_PATH"
    assert "absolute" in err["message"]


def test_file_not_found(tmp_path):
    text, err = read_markdown_file(str(tmp_path / "nope.md"))
    assert text is None and err["error_code"] == "FILE_NOT_FOUND"


def test_directory_is_rejected(tmp_path):
    text, err = read_markdown_file(str(tmp_path))
    assert text is None and err["error_code"] == "INVALID_PATH"


def test_non_utf8_file(tmp_path):
    p = _write(tmp_path / "resume.md", "# 张三\n".encode("gbk"))
    text, err = read_markdown_file(p)
    assert text is None and err["error_code"] == "FILE_READ_FAILED"
    assert "UTF-8" in err["message"]


def test_empty_file(tmp_path):
    p = _write(tmp_path / "resume.md", b"\xef\xbb\xbf \r\n")
    text, err = read_markdown_file(p)
    assert text is None and err["error_code"] == "EMPTY_CONTENT"


# --- platform-specific path forms ----------------------------------------------

@windows_only
def test_windows_forward_slashes(tmp_path):
    p = _write(tmp_path / "resume.md", RESUME.encode("utf-8"))
    text, err = read_markdown_file(p.replace("\\", "/"))   # C:/Users/.../resume.md
    assert err is None and text == RESUME


@windows_only
@pytest.mark.parametrize("raw", ["C:resume.md", "\\resume.md", "/resume.md"])
def test_windows_drive_or_root_relative_is_rejected(raw):
    text, err = read_markdown_file(raw)
    assert text is None and err["error_code"] == "INVALID_PATH"


@posix_only
def test_windows_path_on_posix_is_rejected():
    text, err = read_markdown_file("C:\\Users\\jane\\resume.md")
    assert text is None and err["error_code"] == "INVALID_PATH"


# --- tool interface -------------------------------------------------------------

async def test_schema_takes_a_path_not_content():
    tool = (await handle_list_tools())[0]
    props = tool.inputSchema["properties"]
    assert "markdown" not in props
    assert tool.inputSchema["required"] == ["markdown_path"]
    assert props["markdown_path"]["type"] == "string"
    assert "absolute" in props["markdown_path"]["description"].lower()


async def test_call_reports_path_errors_without_rendering(tmp_path):
    out = await handle_call_tool("render_resume_pdf", {"markdown_path": str(tmp_path / "nope.md")})
    text = out[0].text
    assert text.startswith("status: error\nerror_code: FILE_NOT_FOUND\n")


async def test_inline_markdown_argument_is_not_accepted():
    out = await handle_call_tool("render_resume_pdf", {"markdown": RESUME})
    text = out[0].text
    assert text.startswith("status: error\nerror_code: INVALID_PATH\n")
