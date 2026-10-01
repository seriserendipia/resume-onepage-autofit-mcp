"""
长期复用测试：控制面板前端冒烟测试 (real headless browser)

验证 control_panel.html 的 8 个滑杆的 min/max/step/value/显示文本完全由
js/config.defaults.js 驱动——HTML 里已不再硬编码这些数字（参见提交
"drive slider numbers from config.defaults.js alone"）。同时验证预览 iframe
能端到端渲染、不再停留在"正在加载"。

需要本地 HTTP 服务器：control_panel.html 通过 fetch() 加载简历 markdown，
file:// 协议下会被浏览器 CORS 拦截，所以必须经 http:// 提供。
"""
import functools
import http.server
import socketserver
import tempfile
import threading
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).parent.parent


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # 静默每条请求日志，保持测试输出干净
        pass


@pytest.fixture(scope="module")
def http_server():
    handler = functools.partial(_QuietHandler, directory=str(PROJECT_ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)  # 端口 0 = 自动分配
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


async def test_sliders_driven_by_config(http_server):
    """8 个滑杆的 min/max/step/value/显示文本都应来自 config，而非 HTML 硬编码。"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(f"{http_server}/control_panel.html", wait_until="networkidle")

            # 等待滑杆初始化完成：loadDefaultValues 会把显示文本填上
            await page.wait_for_function(
                "() => window.ResumeConfig && document.getElementById('fontValue')"
                " && document.getElementById('fontValue').textContent.trim() !== ''",
                timeout=15000,
            )

            # 读取 config（代码使用的同一来源）+ 每个滑杆的真实 DOM 状态
            data = await page.evaluate(
                """() => {
                    const cfg = window.ResumeConfig;
                    return cfg.sliderConfig.map(s => {
                        const el = document.getElementById(s.id);
                        const span = document.getElementById(s.valueId);
                        return {
                            id: s.id,
                            cfg: { min: s.min, max: s.max, step: s.step,
                                   def: cfg.defaultStyles[s.styleKey] },
                            dom: { min: parseFloat(el.min), max: parseFloat(el.max),
                                   step: parseFloat(el.step), value: parseFloat(el.value),
                                   span: span.textContent.trim() },
                        };
                    });
                }"""
            )

            assert len(data) == 8, f"应有 8 个滑杆，实际 {len(data)}"
            for d in data:
                c, dom, sid = d["cfg"], d["dom"], d["id"]
                assert dom["min"] == c["min"], f"{sid} min: DOM {dom['min']} != config {c['min']}"
                assert dom["max"] == c["max"], f"{sid} max: DOM {dom['max']} != config {c['max']}"
                assert dom["step"] == c["step"], f"{sid} step: DOM {dom['step']} != config {c['step']}"
                assert dom["value"] == c["def"], f"{sid} value: DOM {dom['value']} != config default {c['def']}"
                assert dom["span"] != "", f"{sid} 显示文本为空（应由 JS 填充）"
                assert dom["span"].startswith(str(c["def"])), \
                    f"{sid} 显示文本 '{dom['span']}' 未以默认值 {c['def']} 开头"

            # 回归锚点：ulMargin 滑杆必须读到 config 的 ulMargin（修复 storage/styleKey 错配前读到的是别的键）
            ul = next(d for d in data if d["id"] == "ulMarginSlider")
            assert ul["dom"]["value"] == ul["cfg"]["def"] == 0.1, \
                f"ulMargin 默认值应为 0.1，实际 {ul['dom']['value']}"

            # 截图供人工查看
            shot = str(Path(tempfile.gettempdir()) / "control_panel_smoke.png")
            await page.screenshot(path=shot, full_page=True)
            print(f"[smoke] 控制面板截图已保存: {shot}")
        finally:
            await browser.close()


async def test_preview_iframe_renders(http_server):
    """预览 iframe 应端到端渲染完成，且不再停留在'正在加载'。"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(f"{http_server}/control_panel.html", wait_until="networkidle")
            await page.wait_for_selector("#innerFrame")

            frame = next((f for f in page.frames if f.url and "resume_preview" in f.url), None)
            assert frame is not None, "未找到预览 iframe (resume_preview.html)"

            await frame.wait_for_selector("body.render-complete", timeout=20000)
            info = await frame.evaluate(
                """() => {
                    const c = document.getElementById('content');
                    return { len: c ? c.innerText.trim().length : 0,
                             head: c ? c.innerText.slice(0, 40) : '' };
                }"""
            )
            assert info["len"] > 0, "预览内容为空"
            assert "正在加载" not in info["head"], f"预览仍停留在加载态: {info['head']}"
        finally:
            await browser.close()


_SPACING_MD = """# Jane Doe
jane@example.com

## Summary

Plain paragraph one.

Plain paragraph two.

## Experience

**Acme** · Engineer *2022 – Present*

- First bullet
- Second bullet

**Globex** · Intern *2021*

- Only bullet
"""

# 每个间隙的 margin-top (px)。选择器只用相邻兄弟，分页前后都成立。
_MEASURE_GAPS = """() => {
    const mt = (sel) => {
        const el = document.querySelector(sel);
        return el ? parseFloat(getComputedStyle(el).marginTop) : null;
    };
    return {
        section: mt('ul + h2, p + h2'),
        entry: mt('ul + p.entry-header'),
        plain: mt('p:not(.entry-header) + p:not(.entry-header)'),
        list: mt('p + ul'),
        bullet: mt('li + li'),
    };
}"""


async def test_spacing_sliders_move_their_gaps(http_server):
    """面板里的间距滑杆必须真的改变对应间隙，且各管各的。

    回归锚点：单位 'u' 曾被当作 CSS 后缀拼进值里（"0.8u"），使 calc() 失效、
    面板预览里所有垂直间距都变成 0；strongParagraphMargin 曾无任何 CSS 消费。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            # 仓库不带 myexperience.md（gitignored），用固定内容顶替
            await page.route(
                "**/myexperience.md*",
                lambda r: r.fulfill(body=_SPACING_MD, content_type="text/markdown"),
            )
            await page.goto(f"{http_server}/control_panel.html", wait_until="networkidle")
            frame = next((f for f in page.frames if f.url and "resume_preview" in f.url), None)
            assert frame is not None, "未找到预览 iframe (resume_preview.html)"
            await frame.wait_for_selector("body.render-complete", timeout=20000)
            await frame.wait_for_selector("p.entry-header", state="attached", timeout=20000)

            async def set_slider(slider_id, value):
                await page.evaluate(
                    """([id, v]) => {
                        const s = document.getElementById(id);
                        s.value = v;
                        s.dispatchEvent(new Event('input', { bubbles: true }));
                    }""",
                    [slider_id, value],
                )
                await page.wait_for_timeout(300)
                return await frame.evaluate(_MEASURE_GAPS)

            base = await frame.evaluate(_MEASURE_GAPS)
            assert all(v is not None for v in base.values()), f"测量选择器未命中: {base}"
            assert base["section"] > base["entry"] > base["bullet"] > 0, \
                f"默认间距应满足 章节 > 条目 > 列表项 > 0，实际 {base}"
            # strongParagraphMargin 默认 0：条目头与普通段落间距相同
            assert base["entry"] == pytest.approx(base["plain"]), base

            # (滑杆, 目标值, 应变大的间隙, 必须不变的间隙)
            cases = [
                ("titleHrMarginSlider", 1.0, ["section"], ["entry", "plain", "list", "bullet"]),
                ("bodyMarginSlider", 0.6, ["entry", "plain"], ["section", "list", "bullet"]),
                ("ulMarginSlider", 0.2, ["list", "bullet"], ["section", "entry", "plain"]),
                ("strongParagraphMarginSlider", 0.2, ["entry"], ["section", "plain", "list", "bullet"]),
            ]
            prev = base
            for slider_id, value, grows, fixed in cases:
                cur = await set_slider(slider_id, value)
                for k in grows:
                    assert cur[k] > prev[k] + 0.1, f"{slider_id} 应增大 {k}: {prev[k]} → {cur[k]}"
                for k in fixed:
                    assert cur[k] == pytest.approx(prev[k]), f"{slider_id} 不应改变 {k}: {prev[k]} → {cur[k]}"
                prev = cur
        finally:
            await browser.close()


_LOOSE_LIST_MD = """# Jane Doe
jane@example.com

## Tight

**Acme** · Engineer *2022*

- one
- two
- three

## Loose

**Globex** · Engineer *2021*

- one

- two

- three
"""

# 每个 <ul>：是否松散列表、条目头→首条、相邻两条的行距 (px)
_MEASURE_LISTS = """() => [...document.querySelectorAll('ul')].map(ul => {
    const lis = [...ul.children];
    const box = (e) => {
        const r = document.createRange();
        r.selectNodeContents(e);
        return r.getBoundingClientRect();
    };
    return {
        loose: !!lis[0].querySelector(':scope > p'),
        headerToFirst: box(lis[0]).top - ul.previousElementSibling.getBoundingClientRect().bottom,
        pitch: box(lis[2]).top - box(lis[1]).top,
    };
})"""


async def test_loose_list_spacing_matches_tight_list(http_server):
    """松散列表（列表项之间有空行）的间距应与紧凑列表一致，并跟随列表间距滑杆。

    回归锚点：松散列表的 <li> 内含 <p>，其段落间距曾穿透 <li> 折叠出来，
    盖过列表间距，使 ulMargin 对松散列表完全失效。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(f"{http_server}/resume_preview.html", wait_until="networkidle")
            await page.evaluate(
                "md => window.postMessage({ type: 'SET_CONTENT', payload: { markdown: md } }, '*')",
                _LOOSE_LIST_MD,
            )
            await page.wait_for_selector("body.render-complete", timeout=20000)
            await page.wait_for_selector("li > p", state="attached", timeout=20000)

            async def measure():
                lists = await page.evaluate(_MEASURE_LISTS)
                assert [l["loose"] for l in lists] == [False, True], f"应为一紧一松两个列表: {lists}"
                return lists

            tight, loose = await measure()
            assert loose["pitch"] == pytest.approx(tight["pitch"], abs=0.1), (tight, loose)
            assert loose["headerToFirst"] == pytest.approx(tight["headerToFirst"], abs=0.1), (tight, loose)

            # 列表间距滑杆必须同样作用于松散列表
            await page.evaluate(
                "() => window.postMessage({ type: 'updateCSS', variable: '--ul-margin', value: '0.2' }, '*')"
            )
            await page.wait_for_timeout(300)
            tight2, loose2 = await measure()
            assert loose2["pitch"] > loose["pitch"] + 0.1, f"ulMargin 应增大松散列表行距: {loose} → {loose2}"
            assert loose2["pitch"] == pytest.approx(tight2["pitch"], abs=0.1), (tight2, loose2)
        finally:
            await browser.close()
