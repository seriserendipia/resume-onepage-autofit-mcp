"""
Resume PDF Renderer using Playwright
Provides headless browser rendering with overflow detection
"""

import asyncio
import os
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser

from resume_structured import parse_resume_structured


def get_default_output_dir() -> str:
    """获取默认输出目录
    
    优先级：
    1. js/config.js 中的 pdfOutput.directory 配置（通过页面注入读取）
    2. 项目目录下的 generated_resume 文件夹（自动创建）
    3. 用户下载目录（跨平台兼容）
    4. 系统临时目录（最终回退）
    
    注意：config.js 中的配置在 render_to_pdf() 方法中动态读取，
    此函数仅提供 config.js 未配置时的默认值。
    """
    # 1. 项目目录下的 generated_resume 文件夹
    project_output = Path(__file__).parent.parent / "generated_resume"
    if project_output.exists() and project_output.is_dir():
        return str(project_output)
    # 如果目录不存在，尝试创建
    try:
        project_output.mkdir(parents=True, exist_ok=True)
        return str(project_output)
    except Exception:
        pass
    
    # 2. 尝试用户下载目录
    home = Path.home()
    downloads_candidates = [
        home / "Downloads",
        home / "downloads",
        home / "下载",  # 中文 Windows
    ]
    for downloads in downloads_candidates:
        if downloads.exists() and downloads.is_dir():
            return str(downloads)
    
    # 3. 回退到临时目录
    return tempfile.gettempdir()


def _explain(pages, metrics, page_info, direction, layout_warnings, format_warnings) -> str:
    """第一句说成功还是失败、为什么；第二句说下一步要做到什么。只给事实与目标，不指定删改哪段内容。"""
    if pages > 1:
        text = (f"Failed: the resume does not fit on one page. It overflows by {metrics['overflow_percentage']}% "
                f"(about {page_info.get('overflow_body_lines')} body lines); page 2 starts at source line "
                f"{page_info.get('first_source_line_on_page_2')}. ")
        if direction == "shrink":
            text += "Auto-fit has already shrunk font size, line spacing and margins as far as allowed, so the text itself must get shorter. "
        text += (f"Next step: shorten the Markdown file by at least {page_info.get('overflow_body_lines')} body lines, "
                 "then render again with the same markdown_path. The table below shows how many lines each section and entry takes.")
    elif layout_warnings:
        text = (f"Failed: the resume fits on one page, but {len(layout_warnings)} entry header line(s) wrap onto more "
                "than one line (see layout_warnings). Every entry header must fit on one line. "
                "Next step: shorten each listed source line, then render again with the same markdown_path.")
    else:
        text = (f"Success: the resume fits on one page with {page_info.get('empty_space_percent')}% of the page left empty. "
                "Next step: deliver the PDF, or add content and render again if the page should be fuller.")
    if format_warnings:
        text += (f" Also: {len(format_warnings)} source line(s) are not in the canonical form (see format_warnings); "
                 "rewrite each one to its expected form in the same edit.")
    return text


# 逐块排版测量。块 = h1/h2/h3/p/li（列表项里的 p 归到 li），用 markdown-it 写入的
# data-line 对应回源文件行号。逐字符取 getClientRects，按行顶部分组得到每块的视觉行，
# 跨页拆开的块（Paged.js 克隆后 data-line 相同）合并计数。
MEASURE_LAYOUT_JS = """() => {
    const round1 = (x) => Math.round(x * 10) / 10;
    const pages = Array.from(document.querySelectorAll('.pagedjs_page'));
    if (!pages.length) return {};
    const contents = pages.map(pg => pg.querySelector('.pagedjs_page_content'));
    const sample = contents[0].querySelector('li, p') || contents[0];
    const linePx = parseFloat(getComputedStyle(sample).lineHeight) || 16;
    const tol = linePx / 2;

    function visualLines(el) {
        const ownList = el.closest('ul,ol');
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
            acceptNode(n) {
                const list = n.parentElement && n.parentElement.closest('ul,ol');
                return list === ownList ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
            }
        });
        const range = document.createRange();
        const rows = [];
        let top = null, cur = '';
        for (let n = walker.nextNode(); n; n = walker.nextNode()) {
            const t = n.data;
            for (let i = 0; i < t.length; i++) {
                range.setStart(n, i); range.setEnd(n, i + 1);
                const rects = range.getClientRects();
                if (!rects.length) continue;
                const r = rects[rects.length - 1];
                if (/\\s/.test(t[i]) && r.width === 0) continue;
                if (top === null || r.top > top + tol) {
                    if (top !== null) rows.push(cur);
                    cur = ''; top = r.top;
                }
                cur += t[i];
            }
        }
        if (top !== null) rows.push(cur);
        return rows.map(s => s.trim().length).filter(n => n > 0);
    }

    const blocks = [];          // 文档顺序
    const byLine = new Map();   // 跨页拆分的块合并
    const usedPx = [];
    contents.forEach((content, pi) => {
        const top = content.getBoundingClientRect().top;
        let bottom = top;
        content.querySelectorAll('h1,h2,h3,p,li').forEach(el => {
            if (el.tagName === 'P' && el.closest('li')) return;
            bottom = Math.max(bottom, el.getBoundingClientRect().bottom);
            const line = parseInt(el.dataset.line);
            if (!line) return;
            const rows = visualLines(el);
            const prev = byLine.get(line);
            if (prev) {
                prev.rows = prev.rows.concat(rows);
                return;
            }
            const kind = el.tagName === 'LI' ? 'bullet'
                : el.classList.contains('entry-header') ? 'entry_header'
                : /^H\\d$/.test(el.tagName) ? 'heading' : 'paragraph';
            const b = { line, tag: el.tagName.toLowerCase(), kind, rows, page: pi + 1,
                        text: el.tagName === 'H2' ? el.innerText.trim() : null };
            byLine.set(line, b);
            blocks.push(b);
        });
        usedPx.push(bottom - top);
    });

    const pageH = contents[0].getBoundingClientRect().height;
    const laterPx = usedPx.slice(1).reduce((a, b) => a + b, 0);
    const firstOff = blocks.find(b => b.page > 1);
    // 第 1 页上被拆开、延续到第 2 页的块，也算第 2 页的起点
    // 只认同一种标签：<ul> 与它的第一个 <li> 起始行号相同，列表的续页克隆不算拆分
    const split = blocks.find(b => b.page === 1 && contents.slice(1).some(c => c.querySelector(`${b.tag}[data-line="${b.line}"]`)));
    // bullet 一整行大约能放多少字符：取折行 bullet 里除最后一行外最长的一行（段落不缩进，会偏大）
    const fullRows = blocks.filter(b => b.tag === 'li').flatMap(b => b.rows.slice(0, -1));
    const page = {
        approx_characters_per_full_bullet_line: fullRows.length ? Math.max(...fullRows) : null,
        empty_space_percent: Math.round(Math.max(0, pageH - usedPx[0]) / pageH * 100),
        overflow_body_lines: round1(laterPx / linePx),
        first_source_line_on_page_2: pages.length > 1 ? ((split || firstOff || {}).line || null) : null,
    };

    const sections = [];
    let sec = { section_title: '(name and contact lines)', title_source_line: null, rendered_lines: 0, percent_of_all_rendered_lines: 0, items: [] };
    for (const b of blocks) {
        if (b.tag === 'h2') {
            if (sec.items.length || sec.title_source_line !== null) sections.push(sec);
            sec = { section_title: b.text, title_source_line: b.line, rendered_lines: 0, percent_of_all_rendered_lines: 0, items: [] };
            continue;
        }
        const n = b.rows.length;
        sec.rendered_lines += n;
        sec.items.push({ source_line: b.line, kind: b.kind, rendered_lines: n, characters_on_last_line: n ? b.rows[n - 1] : 0 });
    }
    sections.push(sec);
    const total = sections.reduce((a, x) => a + x.rendered_lines, 0) || 1;
    for (const x of sections) x.percent_of_all_rendered_lines = Math.round(x.rendered_lines / total * 100);
    return { page, sections };
}"""


class ResumeRenderer:
    """使用 Playwright 渲染简历并检测页面溢出"""
    
    # 默认 PDF 输出目录（跨平台）
    DEFAULT_OUTPUT_DIR = get_default_output_dir()
    
    def __init__(self, html_path: str = None):
        if html_path is None:
            # Default to resume_preview.html in the parent directory of this script
            self.html_path = Path(__file__).parent.parent / "resume_preview.html"
        else:
            self.html_path = Path(html_path)
            
        self.html_path = self.html_path.resolve()
        
        if not self.html_path.exists():
            # Fallback for some dev environments where it might be in current dir
            alt_path = Path("resume_preview.html").resolve()
            if alt_path.exists():
                self.html_path = alt_path
                
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.A4_HEIGHT_PX = 1120  # 297mm @ 96dpi

    def _log(self, message: str) -> None:
        """Log to stderr without breaking MCP stdio (stdout is reserved for protocol).

        VS Code MCP LocalProcess expects ONLY JSON messages on stdout. Any debug logs must go to stderr.
        Also, Windows consoles may use GBK; ensure we never crash on Unicode output.
        """
        text = f"{message}\n"
        try:
            sys.stderr.write(text)
        except UnicodeEncodeError:
            encoding = sys.stderr.encoding or "utf-8"
            sys.stderr.buffer.write(text.encode(encoding, errors="backslashreplace"))
        
    async def start(self):
        """启动浏览器实例"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        
    async def stop(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def render_resume_pdf(
        self, 
        markdown_content: str, 
        output_path: str = None,
        timeout_ms: int = 15000  # Increased timeout to accommodate auto-fit
    ) -> Dict[str, Any]:
        """
        渲染简历为 PDF 并检测溢出
        
        Args:
            markdown_content: Markdown 格式的简历内容
            output_path: PDF 输出路径
            timeout_ms: 渲染超时时间（毫秒）
            
        Returns:
            字典包含:
            - status: "success" | "overflow" | "layout_error"
            - message: 一句事实描述（不含删改建议）
            - pdf_path / structured_path（写失败时为 None）
            - current_pages / fill_ratio
            - page: 页面行数预算、空余行数、溢出行数、溢出起始行
            - auto_fit: 自动适配的方向、是否成功、最终字号/行高/页边距
            - sections: 每个板块、每个块（源文件行号、渲染行数、最后一行字符数）
            - layout_warnings / format_warnings: 只在非空时出现
        """
        if not self.browser:
            await self.start()
            
        page = await self.browser.new_page()
        
        try:
            html_url = f"file:///{self.html_path.as_posix()}"
            self._log(f"[{self.__class__.__name__}] 1. Opening Page: {html_url}")
            # Enable console logging for debugging
            def safe_console_log(msg):
                try:
                    self._log(f"[{self.__class__.__name__}] Browser Console: {msg.text}")
                except Exception:
                    # Never let console logging crash the renderer.
                    return
            
            page.on("console", safe_console_log)

            # 加载本地 HTML 文件
            await page.goto(html_url, wait_until="networkidle")
            self._log(f"[{self.__class__.__name__}] 2. Page Loaded (NetworkIdle)")

            # Wait for Renderer to be ready
            self._log(f"[{self.__class__.__name__}] 3. Waiting for window.isRendererReady...")
            try:
                await page.wait_for_function("() => window.isRendererReady", timeout=5000)
                self._log(f"[{self.__class__.__name__}] 4. Renderer is READY")
            except Exception:
                self._log(f"[{self.__class__.__name__}] Warning: window.isRendererReady check timed out. Proceeding anyway.")

            # Check for Markdown-it availability
            self._log(f"[{self.__class__.__name__}] 5. Checking markdown-it...")
            is_markdown_loaded = await page.evaluate("() => !!window.markdownit")
            if not is_markdown_loaded:
                self._log(f"[{self.__class__.__name__}] Error: markdown-it library not loaded. Please check js/markdown-it.min.js integrity.")
            else:
                self._log(f"[{self.__class__.__name__}] 6. markdown-it is loaded")

            # Stop the Handshake Polling
            await page.evaluate("window.postMessage({ type: 'ACK' }, '*')")

            # 注入 Markdown 内容（通过 Playwright 参数传递，避免模板字面量转义问题）
            self._log(f"[{self.__class__.__name__}] 7. Injecting SET_CONTENT message...")
            await page.evaluate("""(md) => {
                console.log("[InjectedScript] Dispatching SET_CONTENT...");
                window.postMessage({
                    type: 'SET_CONTENT',
                    payload: { markdown: md }
                }, '*');
            }""", markdown_content)
            self._log(f"[{self.__class__.__name__}] 8. Message Dispatched")
            
            # 动态获取 PDF 输出路径配置
            if output_path is None:
                pdf_config = await page.evaluate("() => window.ResumeConfig?.pdfOutput || {}")
                dir_path = pdf_config.get('directory', self.DEFAULT_OUTPUT_DIR)
                filename = pdf_config.get('filename', "output_resume.pdf")
                output_path = os.path.join(dir_path, filename)
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 1. 等待基础渲染完成 (render-complete)
            self._log(f"[{self.__class__.__name__}] 9. Waiting for 'body.render-complete'...")
            try:
                await page.wait_for_selector('body.render-complete', timeout=timeout_ms)
                self._log(f"[{self.__class__.__name__}] 10. Render Complete Signal Received")
                
                # Debug: Verify what is actually on the page
                debug_info = await page.evaluate("""() => {
                    const bodyText = document.body.innerText || "";
                    const pages = document.querySelectorAll('.pagedjs_page');
                    const contentDiv = document.getElementById('content');
                    return {
                        totalLength: bodyText.length,
                        previewText: bodyText.substring(0, 200).replace(/\\n/g, ' '),
                        pageCount: pages.length,
                        contentHtmlLength: contentDiv ? contentDiv.innerHTML.length : -1
                    };
                }""")
                self._log(f"[{self.__class__.__name__}] [VERIFICATION] Rendered Content Stats:")
                self._log(f"    - Total Text Length: {debug_info['totalLength']}")
                self._log(f"    - Page Count: {debug_info['pageCount']}")
                self._log(f"    - Content HTML Length: {debug_info['contentHtmlLength']}")
                self._log(f"    - Preview (First 200 chars): \"{debug_info['previewText']}...\"")
                
                if "正在加载" in debug_info['previewText'] or "Loading" in debug_info['previewText']:
                    self._log(f"[{self.__class__.__name__}] WARNING: Page seems to still show Loading state!")

                # Capture layout metrics to diagnose margin mismatches between preview and printed PDF
                layout_debug = await page.evaluate("""() => {
                    const rect = (el) => {
                        if (!el) return null;
                        const r = el.getBoundingClientRect();
                        return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
                    };

                    const root = document.documentElement;
                    const content = document.getElementById('content');
                    const pagedPage = document.querySelector('.pagedjs_page');
                    const pagedBox = document.querySelector('.pagedjs_pagebox');

                    const pageRules = [];
                    for (const sheet of Array.from(document.styleSheets || [])) {
                        let rules;
                        try { rules = sheet.cssRules; } catch { continue; }
                        for (const rule of Array.from(rules || [])) {
                            if (rule && rule.type === 6) {
                                pageRules.push(rule.cssText);
                            }
                        }
                    }

                    const csRoot = getComputedStyle(root);
                    const csBody = getComputedStyle(document.body);
                    const csPagedBox = pagedBox ? getComputedStyle(pagedBox) : null;

                    return {
                        viewport: { w: window.innerWidth, h: window.innerHeight, dpr: window.devicePixelRatio },
                        cssVars: {
                            pageMargin: csRoot.getPropertyValue('--page-margin').trim(),
                            fontSize: csRoot.getPropertyValue('--body-font-size').trim(),
                            lineHeight: csRoot.getPropertyValue('--line-height').trim(),
                            headingScale: csRoot.getPropertyValue('--heading-scale').trim()
                        },
                        body: { margin: csBody.margin, padding: csBody.padding },
                        pagedBox: csPagedBox ? { padding: csPagedBox.padding, margin: csPagedBox.margin } : null,
                        contentRect: rect(content),
                        pagedPageRect: rect(pagedPage),
                        pagedBoxRect: rect(pagedBox),
                        pageRules
                    };
                }""")
                self._log(f"[{self.__class__.__name__}] [LAYOUT_DEBUG] {layout_debug}")

            except Exception as e:
                self._log(f"[{self.__class__.__name__}] Warning: Render wait failed (body.render-complete): {e}")
                # We can dump the current HTML to debug
                content = await page.content()
                self._log(f"[{self.__class__.__name__}] Debug: Current Body HTML len: {len(content)}")

            
            # 2. 智能等待自动适配 (Auto-Fit)
            
            # 主动触发自动适配逻辑：如果页面超过 1 页或内容过于稀疏，且尚未运行过 autofit
            should_trigger_autofit = await page.evaluate("""() => {
               console.log("[AutoFitCheck] Checking if should trigger...");
               // 检查是否已经自动运行过
               if (window.autoFitResult || document.body.classList.contains('autofit-complete')) {
                   console.log("[AutoFitCheck] Already run, skipping.");
                   return false;
               }
               // 检查当前页面数
               const pages = document.querySelectorAll('.pagedjs_page');
               console.log("[AutoFitCheck] Current page count:", pages.length);
               
               if (pages.length > 1) return true;
               
               // 如果只有一页，检查填充率是否过低 (低于 85%)
               if (pages.length === 1 && window.simpleViewer && window.simpleViewer.checkContentFill) {
                   const fill = window.simpleViewer.checkContentFill();
                   console.log("[AutoFitCheck] One page fill ratio:", fill.ratio, "isSparse:", fill.isSparse);
                   return fill.isSparse;
               }
               console.log("[AutoFitCheck] Conditions not met.");
               return false;
            }""")

            if should_trigger_autofit:
                self._log(f"[{self.__class__.__name__}] [AutoFit] Triggering Auto-Fit (Optimization Required)...")
                # 调用前端暴露的 fitToOnePage 方法
                await page.evaluate("() => window.simpleViewer && window.simpleViewer.fitToOnePage && window.simpleViewer.fitToOnePage()")

            # 检查是否正在进行自动适配
            is_autofitting = await page.evaluate("() => window.simpleViewer && window.simpleViewer.isAutoFitting")
            
            if is_autofitting:
                # 如果正在适配，等待直到完成 (isAutoFitting 变为 false)
                try:
                    await page.wait_for_function(
                        "() => !window.simpleViewer.isAutoFitting", 
                        timeout=15000  # 给予充足时间进行多次迭代
                    )
                except Exception as e:
                    self._log(f"[{self.__class__.__name__}] Warning: Auto-fit wait timeout: {e}")
            
            # 3. 获取自动适配结果和状态
            auto_fit_result = await page.evaluate("() => window.autoFitResult || null")
            auto_fit_run = await page.evaluate("() => document.body.classList.contains('autofit-complete')")

            # 最终生效的排版参数（字体、字号、行高、间距），便于调用方确认实际输出
            final_styles = await page.evaluate("""() => {
                const cs = getComputedStyle(document.documentElement);
                const get = (v) => cs.getPropertyValue(v).trim();
                return {
                    fontFamily: get('--font-family'),
                    fontSize: get('--body-font-size'),
                    lineHeight: get('--line-height'),
                    headingScale: get('--heading-scale'),
                    pageMargin: get('--page-margin'),
                    sectionGap: get('--title-hr-margin'),
                    entryGap: get('--body-margin'),
                    bulletGap: get('--ul-margin')
                };
            }""")

            # 4. 布局后置检查：条目头（行尾斜体 *日期/地点*）必须单行
            #    结构信号是"行尾斜体"，与是否加粗无关（公司/学校名可不加粗）。
            #    高度法：折行后段落高度 ≈ N×行高，覆盖"日期掉行"与"中间文字折行"两种成因。
            layout_warnings = await page.evaluate("""() => {
                const warnings = [];
                const paras = document.querySelectorAll('.pagedjs_page p');

                paras.forEach(p => {
                    // 条目头 = 最后一个元素子节点是 <em>（行尾斜体日期/地点），且其后无有意义文字
                    const emItem = p.lastElementChild;
                    if (!emItem || emItem.tagName !== 'EM') return;
                    // 行尾斜体后不能再有有意义文字（否则是正文，如 "...*x*."）
                    let after = '';
                    for (let n = emItem.nextSibling; n; n = n.nextSibling) after += n.textContent;
                    if (after.trim() !== '') return;
                    // 护栏：斜体不能是整段
                    if (p.textContent.trim() === emItem.textContent.trim()) return;

                    const lineH = parseFloat(getComputedStyle(p).lineHeight)
                                  || emItem.getBoundingClientRect().height;
                    const pH = p.getBoundingClientRect().height;
                    if (!lineH || pH <= lineH * 1.5) return;  // 单行 → 正常

                    // 区分成因：行尾斜体掉到下一行 vs 整行折行（不依赖行首加粗）
                    const dropped =
                        (emItem.getBoundingClientRect().top
                         - p.getBoundingClientRect().top) > lineH * 0.5;
                    warnings.push({
                        source_line: parseInt(p.dataset.line) || null,
                        rendered_lines: Math.round(pH / lineH),
                        cause: dropped ? 'date_dropped_to_next_line' : 'header_wrapped',
                        text: p.innerText.replace(/\\n/g, ' ').substring(0, 60),
                    });
                });
                return warnings;
            }""")

            if layout_warnings:
                self._log(f"[{self.__class__.__name__}] [WARNING] Layout Warnings detected: {len(layout_warnings)}")
                for w in layout_warnings:
                    self._log(f"  - {w}")

            # 检测页面高度和溢出
            metrics = await self._check_overflow(page)
            
            # 获取内容统计信息（只写进 debug JSON）
            content_stats = await self._get_content_stats(page)

            # 逐块排版反馈：每个块占几行、最后一行几个字符、溢出多少行
            layout = await page.evaluate(MEASURE_LAYOUT_JS)
            
            # 无论成功或失败，都生成 PDF 供 AI 查看效果
            output_full_path = Path(output_path).resolve()
            await page.pdf(
                path=str(output_full_path),
                format='A4',
                print_background=True,
                margin={
                    'top': '0mm',
                    'bottom': '0mm',
                    'left': '0mm',
                    'right': '0mm'
                }
            )

            # Write debug sidecar JSON (helps diagnose print margin/layout issues)
            debug_json_path = output_full_path.with_suffix('.debug.json')
            try:
                debug_payload = {
                    "pdf_path": str(output_full_path),
                    "debug_info": locals().get('debug_info'),
                    "layout_debug": locals().get('layout_debug'),
                    "metrics": metrics,
                    "content_stats": content_stats,
                    "layout": layout,
                    "final_styles": final_styles,
                    "auto_fit_status": {
                        "run": auto_fit_run,
                        "result": auto_fit_result
                    }
                }
                with open(debug_json_path, 'w', encoding='utf-8') as f:
                    json.dump(debug_payload, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self._log(f"[{self.__class__.__name__}] Warning: Failed to write debug JSON: {e}")

            # 写结构化 JSON 侧车文件：内容只取决于输入的 Markdown，每次写 PDF 都写（包括溢出时）
            structured_path = None
            format_warnings = []
            structured_json_path = output_full_path.with_suffix('.structured.json')
            try:
                doc, fw = parse_resume_structured(markdown_content)
                structured_doc = {
                    "schema_version": doc["schema_version"],
                    "generator": doc["generator"],
                    "generated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    "pdf_file": output_full_path.name,
                    "warnings": doc["warnings"],
                    "sections": doc["sections"],
                }
                with open(structured_json_path, 'w', encoding='utf-8') as f:
                    json.dump(structured_doc, f, ensure_ascii=False, indent=2)
                structured_path = str(structured_json_path)
                format_warnings = fw
            except Exception as e:
                self._log(f"[{self.__class__.__name__}] Warning: Failed to write structured JSON: {e}")
                # 删掉上一次渲染留下的同名 JSON，免得它看起来对应这次的 PDF
                try:
                    structured_json_path.unlink(missing_ok=True)
                except Exception as e2:
                    self._log(f"[{self.__class__.__name__}] Warning: Failed to remove stale structured JSON: {e2}")

            pages = metrics['current_pages']
            page_info = layout.get('page', {})
            direction = (auto_fit_result or {}).get('direction') if (auto_fit_result or {}).get('attempted') else None
            explanation = _explain(pages, metrics, page_info, direction, layout_warnings, format_warnings)

            if pages > 1:
                status = "overflow"
                page_fit = {
                    "page_count": pages,
                    "overflow_percent": metrics['overflow_percentage'],
                    "overflow_body_lines": page_info.get('overflow_body_lines'),
                    "first_source_line_on_page_2": page_info.get('first_source_line_on_page_2'),
                    "approx_characters_per_full_bullet_line": page_info.get('approx_characters_per_full_bullet_line'),
                }
            else:
                status = "layout_error" if layout_warnings else "success"
                page_fit = {
                    "page_count": pages,
                    "empty_space_percent": page_info.get('empty_space_percent'),
                    "approx_characters_per_full_bullet_line": page_info.get('approx_characters_per_full_bullet_line'),
                }
            page_fit["auto_fit_direction"] = direction or "none"

            # 顺序即阅读顺序：结果 → PDF → 原因与下一步 → 页数与溢出 → 各板块占用
            result = {
                "status": status,
                "pdf_path": str(output_full_path),
                "explanation": explanation,
                "page_fit": page_fit,
                "space_by_section": layout.get('sections', []),
            }
            # 空列表不返回，省 token
            if layout_warnings:
                result["layout_warnings"] = layout_warnings
            if format_warnings:
                result["format_warnings"] = format_warnings
            # structured_path 只用于测试与直接调用方；MCP 层不输出（文件名固定为 <pdf>.structured.json）
            result["structured_path"] = structured_path

            return result
                
        finally:
            await page.close()
            
    async def _check_overflow(self, page: Page) -> Dict[str, Any]:
        """检测页面溢出情况"""
        result = await page.evaluate("""
            () => {
                const A4_HEIGHT_PX = 1120;

                // Priority 1: Check Paged.js pages
                const pagedPages = document.querySelectorAll('.pagedjs_page');
                if (pagedPages.length > 0) {
                    const pageCount = pagedPages.length;
                    // 最后一页只算实际占用的高度，这样溢出量才是"需要删掉多少内容"，
                    // 而不是恒为 100% × (页数-1)。
                    const lastPage = pagedPages[pageCount - 1];
                    const lastContent = lastPage.querySelector('.pagedjs_page_content');
                    const lastBox = lastPage.querySelector('.pagedjs_pagebox');
                    let lastFill = 1.0;
                    if (lastContent && lastBox && lastBox.clientHeight) {
                        const top = lastContent.getBoundingClientRect().top;
                        const bottoms = Array.from(lastContent.querySelectorAll('h1,h2,h3,p,li,td'))
                            .map(el => el.getBoundingClientRect().bottom);
                        if (bottoms.length) {
                            lastFill = Math.min(1, (Math.max(...bottoms) - top) / lastBox.clientHeight);
                        }
                    }
                    const usedPages = (pageCount - 1) + lastFill;
                    const totalHeight = Math.round(usedPages * A4_HEIGHT_PX);
                    const overflowPx = Math.max(0, totalHeight - A4_HEIGHT_PX);
                    // 占全部内容的比例 = 大约需要删减的内容量
                    const overflowPercentage = pageCount > 1 ? Math.max(1, ((usedPages - 1) / usedPages) * 100) : 0;
                    
                    // 获取第一页的填充率
                    let fillRatio = 1.0;
                    const firstPageContent = document.querySelector('.pagedjs_page_content');
                    const firstPageBox = document.querySelector('.pagedjs_pagebox');
                    if (firstPageContent && firstPageBox) {
                        // 寻找内容中最后一个可见元素，以更好地估算实际内容高度
                        const children = Array.from(firstPageContent.querySelectorAll('*'));
                        if (children.length > 0) {
                            const lastChild = children[children.length - 1];
                            const contentTop = firstPageContent.getBoundingClientRect().top;
                            const lastBottom = lastChild.getBoundingClientRect().bottom;
                            const actualContentHeight = lastBottom - contentTop;
                            fillRatio = actualContentHeight / firstPageBox.clientHeight;
                        } else {
                            fillRatio = firstPageContent.scrollHeight / firstPageBox.clientHeight;
                        }
                    }
                    
                    return {
                        total_height: totalHeight,
                        current_pages: pageCount,
                        overflow_px: overflowPx,
                        overflow_percentage: Math.round(overflowPercentage),
                        fill_ratio: parseFloat(fillRatio.toFixed(2))
                    };
                }

                // Priority 2: Check Standard Content Element
                const contentEl = document.querySelector('#content') || document.querySelector('.page');
                if (!contentEl) {
                    return { error: 'Content element not found' };
                }
                
                const totalHeight = contentEl.scrollHeight;
                const pageCount = Math.ceil(totalHeight / A4_HEIGHT_PX);
                const overflowPx = Math.max(0, totalHeight - A4_HEIGHT_PX);
                const overflowPercentage = (overflowPx / A4_HEIGHT_PX) * 100;
                const fillRatio = (totalHeight % A4_HEIGHT_PX) / A4_HEIGHT_PX;
                
                return {
                    total_height: totalHeight,
                    current_pages: pageCount,
                    overflow_px: overflowPx,
                    overflow_percentage: Math.round(overflowPercentage),
                    fill_ratio: parseFloat((pageCount > 1 ? 1.0 : fillRatio).toFixed(2))
                };
            }
        """)
        
        return result
    
    async def _get_content_stats(self, page: Page) -> Dict[str, Any]:
        """获取内容统计信息，帮助 AI 判断削减策略"""
        stats = await page.evaluate("""
            () => {
                // Priority: Check raw markdown inputs if stored, otherwise check content text
                // Attempt to get raw markdown from a global variable if available (hypothetical)
                // Otherwise fallback to innerText counting
                
                const contentEl = document.querySelector('#content');
                if (!contentEl) return {};
                
                // Get text excluding Paged.js artifacts if possible, 
                // but #content is usually hidden/modified by Paged.js.
                // Better to look at the 'originalBody' if preserved or just the raw text content.
                
                const text = contentEl.innerText || '';
                
                // 更精确的字数统计 (Simple approximation for CJK + English)
                // Remove whitespace
                const cleanText = text.replace(/\\s+/g, '');
                const charCount = cleanText.length;
                
                // English word count approximation
                const wordCount = text.trim().split(/\\s+/).length;

                return {
                    word_count: wordCount,
                    char_count: charCount,
                    h1_count: document.querySelectorAll('h1').length,
                    h2_count: document.querySelectorAll('h2').length,
                    li_count: document.querySelectorAll('li').length,
                    p_count: document.querySelectorAll('p').length
                };
            }
        """)
        
        return stats
    
# 单独的工具函数用于 MCP 集成
async def render_resume_tool(markdown: str, output: str = "resume.pdf") -> Dict[str, Any]:
    """MCP 工具：渲染简历 PDF"""
    renderer = ResumeRenderer()
    try:
        result = await renderer.render_resume_pdf(markdown, output)
        return result
    finally:
        await renderer.stop()


if __name__ == "__main__":
    # 测试示例
    async def test():
        renderer = ResumeRenderer()
        await renderer.start()
        
        # 读取示例 Markdown
        try:
            with open("myexperience.md", "r", encoding="utf-8") as f:
                markdown = f.read()
        except FileNotFoundError:
             # 如果找不到文件，使用一个简单的测试字符串
             markdown = "# Test Resume\n\n## Experience\n\n- Job 1\n- Job 2"

        
        result = await renderer.render_resume_pdf(markdown, "test_output.pdf")
        try:
            print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
        except UnicodeEncodeError:
            sys.stderr.buffer.write(json.dumps(result, indent=2, ensure_ascii=False).encode(sys.stderr.encoding or "utf-8", errors="backslashreplace"))
        
        await renderer.stop()
    
    asyncio.run(test())
