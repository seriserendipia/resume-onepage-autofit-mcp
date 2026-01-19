"""
Resume PDF Renderer using Playwright
Provides headless browser rendering with overflow detection
"""

import asyncio
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser


class ResumeRenderer:
    """使用 Playwright 渲染简历并检测页面溢出"""
    
    # 默认 PDF 输出目录（可修改）
    DEFAULT_OUTPUT_DIR = r"D:\Downloads"  # 使用原始字符串避免转义问题
    
    def __init__(self, html_path: str = "generated_resume.html"):
        self.html_path = Path(html_path).resolve()
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.A4_HEIGHT_PX = 1120  # 297mm @ 96dpi
        
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
            # 加载本地 HTML 文件
            html_url = f"file:///{self.html_path.as_posix()}"
            await page.goto(html_url, wait_until="networkidle")

            # 注入 Markdown 内容
            escaped_markdown = markdown_content.replace('`', '\\`').replace('${', '\\${')
            inject_script = f"""
                if (window.simpleViewer && window.simpleViewer.renderContent) {{
                    window.simpleViewer.renderContent(`{escaped_markdown}`);
                }} else {{
                    console.error('SimpleViewer not available');
                }}
            """
            await page.evaluate(inject_script)

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
            try:
                await page.wait_for_selector('body.render-complete', timeout=timeout_ms)
            except Exception as e:
                print(f"Warning: Render timeout: {e}")
            
            # 2. 智能等待自动适配 (Auto-Fit)
            # 简单浏览器逻辑: renderContent -> setTimeout(300ms) -> fitToOnePage -> isAutoFitting=true
            
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
                    print(f"Warning: Auto-fit wait timeout: {e}")
            
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
            
            # 构造详细响应
            result = {
                "pdf_path": str(output_full_path),
                "current_pages": metrics['current_pages'],
                "total_height_px": metrics['total_height'],
                "overflow_amount": metrics['overflow_percentage'],
                "overflow_px": metrics['overflow_px'],
                "content_stats": content_stats,
                "auto_fit_status": {
                    "run": auto_fit_run,
                    "result": auto_fit_result
                }
            }

            if metrics['current_pages'] <= 1:
                # 成功：适配单页
                result.update({
                    "status": "success",
                    "message": "✅ 简历已成功适配为单页 PDF"
                })
            else:
                # 失败：内容溢出
                result.update({
                    "status": "overflow",
                    "reason": "content_exceeds_one_page",
                    "hint": self._generate_hint(metrics, content_stats),
                    "message": f"⚠️ 内容溢出 {metrics['overflow_percentage']}%，已生成 {metrics['current_pages']} 页预览 PDF"
                })
                
            return result
                
        finally:
            await page.close()
            
    async def _check_overflow(self, page: Page) -> Dict[str, Any]:
        """检测页面溢出情况"""
        result = await page.evaluate("""
            () => {
                const contentEl = document.querySelector('#content') || document.querySelector('.page');
                if (!contentEl) {
                    return { error: 'Content element not found' };
                }
                
                const A4_HEIGHT_PX = 1120;
                const totalHeight = contentEl.scrollHeight;
                const pageCount = Math.ceil(totalHeight / A4_HEIGHT_PX);
                const overflowPx = Math.max(0, totalHeight - A4_HEIGHT_PX);
                const overflowPercentage = (overflowPx / A4_HEIGHT_PX) * 100;
                
                return {
                    total_height: totalHeight,
                    current_pages: pageCount,
                    overflow_px: overflowPx,
                    overflow_percentage: Math.round(overflowPercentage)
                };
            }
        """)
        
        return result
    
    async def _get_content_stats(self, page: Page) -> Dict[str, Any]:
        """获取内容统计信息，帮助 AI 判断削减策略"""
        stats = await page.evaluate("""
            () => {
                const contentEl = document.querySelector('#content') || document.querySelector('.page');
                if (!contentEl) {
                    return {};
                }
                
                const text = contentEl.innerText || '';
                const wordCount = text.split(/\\s+/).filter(w => w.length > 0).length;
                const charCount = text.length;
                
                // 统计各级标题数量
                const h1Count = contentEl.querySelectorAll('h1').length;
                const h2Count = contentEl.querySelectorAll('h2').length;
                const h3Count = contentEl.querySelectorAll('h3').length;
                
                // 统计列表项
                const liCount = contentEl.querySelectorAll('li').length;
                
                // 统计段落
                const pCount = contentEl.querySelectorAll('p').length;
                
                return {
                    word_count: wordCount,
                    char_count: charCount,
                    h1_count: h1Count,
                    h2_count: h2Count,
                    h3_count: h3Count,
                    list_items: liCount,
                    paragraphs: pCount
                };
            }
        """)
        
        return stats
    
    def _generate_hint(self, metrics: Dict[str, Any], content_stats: Dict[str, Any] = None) -> str:
        """根据溢出量和内容统计生成削减建议"""
        overflow_pct = metrics.get('overflow_percentage', 0)
        
        hint_parts = []
        
        # 基础建议
        if overflow_pct < 5:
            hint_parts.append("轻微溢出（<5%）。建议：应用 Level 1 削减（合并孤行、压缩技能列表）")
        elif overflow_pct < 15:
            hint_parts.append(f"中等溢出（{overflow_pct}%）。建议：应用 Level 2 削减（简化描述、移除软技能表述）")
        else:
            hint_parts.append(f"严重溢出（{overflow_pct}%）。建议：应用 Level 3 削减（移除不相关经历或项目）")
        
        # 基于内容统计的具体建议
        if content_stats:
            suggestions = []
            
            if content_stats.get('list_items', 0) > 20:
                suggestions.append(f"当前有 {content_stats['list_items']} 个列表项，可合并或删减")
            
            if content_stats.get('word_count', 0) > 500:
                suggestions.append(f"字数 {content_stats['word_count']} 偏多，建议删减至 300-400 字")
            
            if content_stats.get('h2_count', 0) > 5:
                suggestions.append(f"有 {content_stats['h2_count']} 个主要板块，考虑合并相似板块")
            
            if suggestions:
                hint_parts.append("具体建议：" + "；".join(suggestions))
        
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
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        await renderer.stop()
    
    asyncio.run(test())
