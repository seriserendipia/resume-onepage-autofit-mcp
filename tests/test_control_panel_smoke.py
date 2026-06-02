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

            # 回归锚点：ulMargin 默认值应为 0.4（修复 storage/styleKey 错配前，面板实际是 0.2）
            ul = next(d for d in data if d["id"] == "ulMarginSlider")
            assert ul["dom"]["value"] == 0.4, f"ulMargin 默认值应为 0.4，实际 {ul['dom']['value']}"

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
