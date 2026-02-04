"""
Resume PDF Renderer using Playwright
Provides headless browser rendering with overflow detection
"""

import asyncio
import os
import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser


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
            - status: "success" 或 "overflow"
            - pdf_path: PDF 文件路径
            - reason: 失败原因
            - current_pages: 当前页数
            - overflow_amount: 溢出百分比
            - hint: 削减建议
            - content_stats: 内容统计
            - auto_fit_status: 自动适配状态详情
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

            # 注入 Markdown 内容
            self._log(f"[{self.__class__.__name__}] 7. Injecting SET_CONTENT message...")
            escaped_markdown = markdown_content.replace('`', '\\`').replace('${', '\\${')
            inject_script = f"""
                console.log("[InjectedScript] Dispatching SET_CONTENT...");
                window.postMessage({{
                    type: 'SET_CONTENT',
                    payload: {{ markdown: `{escaped_markdown}` }}
                }}, '*');
            """
            await page.evaluate(inject_script)
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

            # 等待一小段时间让 JS 有机会启动自动适配
            await page.wait_for_timeout(500)
            
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

            # 检测页面高度和溢出
            metrics = await self._check_overflow(page)
            
            # 获取内容统计信息
            content_stats = await self._get_content_stats(page)
            
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
                    "auto_fit_status": {
                        "run": auto_fit_run,
                        "result": auto_fit_result
                    }
                }
                with open(debug_json_path, 'w', encoding='utf-8') as f:
                    json.dump(debug_payload, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self._log(f"[{self.__class__.__name__}] Warning: Failed to write debug JSON: {e}")
            
            # 构造详细响应
            result = {
                "pdf_path": str(output_full_path),
                "current_pages": metrics['current_pages'],
                "fill_ratio": metrics.get('fill_ratio', 1.0),
                "total_height_px": metrics['total_height'],
                "overflow_amount": metrics['overflow_percentage'],
                "overflow_px": metrics['overflow_px'],
                "content_stats": content_stats,
                "hint": self._generate_hint(metrics, content_stats),
                "auto_fit_status": {
                    "run": auto_fit_run,
                    "result": auto_fit_result
                }
            }

            if metrics['current_pages'] <= 1:
                # 成功：适配单页
                # 检查是否内容过少，如果是，状态依然标记为 success 但提供调整建议
                if metrics.get('fill_ratio', 1.0) < 0.8:
                    result.update({
                        "status": "success",
                        "message": f"Resume fitted to single page, but content is sparse (fill ratio: {round(metrics['fill_ratio']*100)}%). Consider adding more content for better visual balance.",
                        "suggestion": "Add more achievements, skills, or project details to fill the page better.",
                        "next_action": "Review the hint field for specific expansion suggestions, or accept the current result."
                    })
                else:
                    result.update({
                        "status": "success",
                        "message": "Resume successfully fitted to single page PDF. / 简历已成功适配为单页 PDF。",
                        "suggestion": "The resume is ready. You can save it or make further adjustments if needed.",
                        "next_action": "Deliver the PDF to user or continue refining content."
                    })
            else:
                # 失败：内容溢出
                result.update({
                    "status": "overflow",
                    "reason": "content_exceeds_one_page",
                    "message": f"Content overflows by {metrics['overflow_percentage']}%, rendered {metrics['current_pages']} pages. / 内容溢出 {metrics['overflow_percentage']}%，已生成 {metrics['current_pages']} 页预览 PDF。",
                    "suggestion": f"Apply reduction strategy based on overflow amount. See hint field for specific recommendations.",
                    "next_action": f"Reduce content by approximately {metrics['overflow_percentage']}% following the Level strategy in hint, then call render_resume_pdf again."
                })
                
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
                    const totalHeight = pageCount * A4_HEIGHT_PX;
                    const overflowPx = Math.max(0, totalHeight - A4_HEIGHT_PX);
                    const overflowPercentage = (overflowPx / A4_HEIGHT_PX) * 100;
                    
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
    
    def _generate_hint(self, metrics: Dict[str, Any], content_stats: Dict[str, Any] = None) -> str:
        """根据溢出量、填充率和内容统计生成双向调整建议"""
        overflow_pct = metrics.get('overflow_percentage', 0)
        fill_ratio = metrics.get('fill_ratio', 1.0)
        page_count = metrics.get('current_pages', 1)
        
        hint_parts = []
        
        if page_count > 1:
            # 溢出提示 (Too Much Content)
            if overflow_pct < 5:
                hint_parts.append(f"内容轻微溢出（约 {overflow_pct}%）。建议：Level 1 压缩（合并简短列表、压缩技能项）。")
            elif overflow_pct < 15:
                hint_parts.append(f"内容中等溢出（约 {overflow_pct}%）。建议：Level 2 削减（精简项目描述、移除次要技能）。")
            else:
                hint_parts.append(f"内容严重溢出（超过 {overflow_pct}%）。建议：Level 3 大幅删减（建议削减约 {overflow_pct}% 的文本内容，或移除不相关的工作经历/项目）。")
        elif fill_ratio < 0.85:
            # 内容不足提示 (Too Little Content)
            fill_pct = round(fill_ratio * 100)
            missing_pct = round((0.9 - fill_ratio) * 100) # 目标填充 90%
            
            if fill_ratio > 0.75:
                hint_parts.append(f"页面略显空旷（填充率 {fill_pct}%）。建议：Level 1 扩充（为现有项目增加 1-2 条具体的量化成果描述）。")
            elif fill_ratio > 0.5:
                hint_parts.append(f"页面内容偏少（填充率 {fill_pct}%）。建议：Level 2 扩充（增加一个完整的工作经历或详细的项目介绍，约需增加 {missing_pct}% 的内容）。")
            else:
                hint_parts.append(f"页面过于空旷（填充率 {fill_pct}%）。建议：Level 3 大量补充（目前内容仅占约半页，请增加更多核心经历，建议内容量翻倍以获得更专业的视觉效果）。")
        else:
            hint_parts.append("内容完美适配单页。")
        
        # 基于具体内容统计的补充建议
        if content_stats:
            suggestions = []
            if page_count > 1:
                if content_stats.get('word_count', 0) > 600:
                    suggestions.append(f"总字数 {content_stats['word_count']} 过多，建议减至 500 字以内")
                if content_stats.get('li_count', 0) > 25:
                    suggestions.append(f"列表项 ({content_stats['li_count']}) 过多，建议合并相似项")
            elif fill_ratio < 0.7:
                if content_stats.get('word_count', 0) < 300:
                    suggestions.append(f"总字数 {content_stats['word_count']} 偏少，建议扩充至 400 字以上")
            
            if suggestions:
                hint_parts.append("具体数据建议：" + "；".join(suggestions))
        
        return " | ".join(hint_parts)


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
