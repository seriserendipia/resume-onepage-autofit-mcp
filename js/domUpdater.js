/**
 * DOM 更新监听器
 * 负责监听状态变化并更新相应的 DOM 元素
 */

class DOMUpdater {
    constructor() {
        this.unsubscribeFunctions = [];
        this.isInitialized = false;
        this.updateQueue = [];
        this.isProcessingQueue = false;
        
        console.log('[DOM更新器] DOM 更新监听器已创建');
    }

    /**
     * 初始化DOM更新器
     */
    async init() {
        console.log('[DOM更新器] 初始化DOM更新监听器...');
        
        // 等待状态管理器就绪
        await this.waitForStateManager();
        
        // 设置所有监听器
        this.setupAllListeners();
        
        this.isInitialized = true;
        console.log('[DOM更新器] ✅ DOM更新监听器初始化完成');
    }

    /**
     * 等待状态管理器就绪
     */
    async waitForStateManager() {
        return new Promise((resolve) => {
            const check = () => {
                if (typeof window.ResumeState !== 'undefined') {
                    console.log('[DOM更新器] ✅ 状态管理器已就绪');
                    resolve();
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    }

    /**
     * 设置所有状态监听器
     */
    setupAllListeners() {
        // 监听内容变化
        this.setupContentListener();
        
        // 监听样式变化
        this.setupStyleListener();
        
        // 监听UI状态变化
        this.setupUIListener();
        
        // 监听Paged.js状态变化
        this.setupPagedJsListener();
        
        console.log('[DOM更新器] 所有状态监听器已设置');
    }

    /**
     * 监听内容状态变化
     */
    setupContentListener() {
        const unsubscribe = window.ResumeState.subscribe('content', (action, oldState, newState) => {
            if (action.type === 'SET_CONTENT') {
                console.log('[DOM更新器] 检测到内容变化');
                this.queueUpdate('content', () => this.updateContentDOM(newState.content));
            }
        });
        
        this.unsubscribeFunctions.push(unsubscribe);
    }

    /**
     * 监听样式状态变化
     */
    setupStyleListener() {
        const unsubscribe = window.ResumeState.subscribe('styles', (action, oldState, newState) => {
            if (action.type === 'UPDATE_STYLES') {
                console.log('[DOM更新器] 检测到样式变化');
                this.queueUpdate('styles', () => this.updateStylesDOM(newState.styles, oldState.styles));
            }
        });
        
        this.unsubscribeFunctions.push(unsubscribe);
    }

    /**
     * 监听UI状态变化
     */
    setupUIListener() {
        const unsubscribe = window.ResumeState.subscribe('ui', (action, oldState, newState) => {
            if (action.type === 'UI_STATE_CHANGE') {
                console.log('[DOM更新器] 检测到UI状态变化');
                this.queueUpdate('ui', () => this.updateUIDOM(newState.ui, oldState.ui));
            }
        });
        
        this.unsubscribeFunctions.push(unsubscribe);
    }

    /**
     * 监听Paged.js状态变化
     */
    setupPagedJsListener() {
        const unsubscribe = window.ResumeState.subscribe('pagedjs', (action, oldState, newState) => {
            if (action.type === 'PAGEDJS_STATE_CHANGE') {
                console.log('[DOM更新器] 检测到Paged.js状态变化');
                this.queueUpdate('pagedjs', () => this.updatePagedJsDOM(newState.pagedjs, oldState.pagedjs));
            }
        });
        
        this.unsubscribeFunctions.push(unsubscribe);
    }

    /**
     * 将更新任务加入队列
     */
    queueUpdate(type, updateFunction) {
        this.updateQueue.push({
            type,
            updateFunction,
            timestamp: Date.now()
        });
        
        this.processUpdateQueue();
    }

    /**
     * 处理更新队列
     */
    async processUpdateQueue() {
        if (this.isProcessingQueue || this.updateQueue.length === 0) {
            return;
        }
        
        this.isProcessingQueue = true;
        
        try {
            // 按时间戳排序，确保顺序执行
            this.updateQueue.sort((a, b) => a.timestamp - b.timestamp);
            
            // 执行所有更新
            while (this.updateQueue.length > 0) {
                const update = this.updateQueue.shift();
                try {
                    await update.updateFunction();
                    console.log(`[DOM更新器] ✅ ${update.type} 更新完成`);
                } catch (error) {
                    console.error(`[DOM更新器] ❌ ${update.type} 更新失败:`, error);
                }
            }
        } finally {
            this.isProcessingQueue = false;
        }
    }

    /**
     * 更新内容DOM
     */
    async updateContentDOM(content) {
        console.log('[DOM更新器] 更新内容DOM...');
        
        // 尝试多个可能的内容容器ID
        let container = document.getElementById('content') || 
                       document.getElementById('resume-content') ||
                       document.querySelector('.content') ||
                       document.querySelector('[data-content]');
                       
        if (!container) {
            console.warn('[DOM更新器] 未找到内容容器，尝试的选择器: #content, #resume-content, .content, [data-content]');
            return;
        }
        
        console.log(`[DOM更新器] 找到内容容器: ${container.id || container.className}`);
        
        if (content.html) {
            // 设置HTML内容
            container.innerHTML = content.html;
            console.log('[DOM更新器] HTML内容已更新');
            
            // 触发内容变化事件
            this.dispatchContentChangeEvent(container);
        } else if (content.markdown) {
            // 如果只有Markdown，需要先渲染
            console.log('[DOM更新器] 检测到Markdown内容，需要渲染为HTML');
            await this.renderMarkdownToHTML(content.markdown);
        }
    }

    /**
     * 渲染Markdown为HTML
     */
    async renderMarkdownToHTML(markdown) {
        // 调用现有的renderer模块
        if (window.resumeViewer && window.resumeViewer.renderer) {
            try {
                const html = await window.resumeViewer.renderer.renderMarkdown(markdown);
                
                // 更新状态中的HTML
                window.ResumeState.dispatch({
                    type: 'SET_CONTENT',
                    payload: { html: html }
                });
            } catch (error) {
                console.error('[DOM更新器] Markdown渲染失败:', error);
            }
        } else {
            console.warn('[DOM更新器] Renderer模块未找到');
        }
    }

    /**
     * 更新样式DOM
     */
    updateStylesDOM(styles, oldStyles = {}) {
        console.log('[DOM更新器] 更新样式DOM...');
        
        const root = document.documentElement;
        
        // 更新字体大小
        if (styles.fontSize !== oldStyles.fontSize) {
            root.style.setProperty('--font-size', `${styles.fontSize}px`);
            console.log(`[DOM更新器] 字体大小更新为: ${styles.fontSize}px`);
        }
        
        // 更新行高
        if (styles.lineHeight !== oldStyles.lineHeight) {
            root.style.setProperty('--line-height', styles.lineHeight);
            console.log(`[DOM更新器] 行高更新为: ${styles.lineHeight}`);
        }
        
        // 更新字体族
        if (styles.fontFamily !== oldStyles.fontFamily) {
            root.style.setProperty('--font-family', styles.fontFamily);
            console.log(`[DOM更新器] 字体族更新为: ${styles.fontFamily}`);
        }
        
        // 更新边距
        if (styles.margins && JSON.stringify(styles.margins) !== JSON.stringify(oldStyles.margins)) {
            const margins = styles.margins;
            root.style.setProperty('--margin-top', `${margins.top}px`);
            root.style.setProperty('--margin-bottom', `${margins.bottom}px`);
            root.style.setProperty('--margin-left', `${margins.left}px`);
            root.style.setProperty('--margin-right', `${margins.right}px`);
            console.log('[DOM更新器] 边距已更新:', margins);
        }
        
        // 触发样式变化事件
        this.dispatchStyleChangeEvent(styles);
    }

    /**
     * 更新UI DOM
     */
    updateUIDOM(ui, oldUI = {}) {
        console.log('[DOM更新器] 更新UI DOM...');
        
        // 更新调试模式
        if (ui.debugMode !== oldUI.debugMode) {
            document.body.classList.toggle('debug-mode', ui.debugMode);
            console.log(`[DOM更新器] 调试模式: ${ui.debugMode ? '开启' : '关闭'}`);
        }
        
        // 更新预览模式
        if (ui.previewMode !== oldUI.previewMode) {
            document.body.classList.remove('preview-web', 'preview-print');
            document.body.classList.add(`preview-${ui.previewMode}`);
            console.log(`[DOM更新器] 预览模式: ${ui.previewMode}`);
        }
        
        // 更新加载状态
        if (ui.loading !== oldUI.loading) {
            document.body.classList.toggle('loading', ui.loading);
            
            // 更新加载指示器
            this.updateLoadingIndicator(ui.loading);
        }
    }

    /**
     * 更新Paged.js相关DOM
     */
    updatePagedJsDOM(pagedjs, oldPagedjs = {}) {
        console.log('[DOM更新器] 更新Paged.js DOM...');
        
        // 更新页数显示
        if (pagedjs.pageCount !== oldPagedjs.pageCount) {
            this.updatePageCountDisplay(pagedjs.pageCount);
        }
        
        // 更新渲染状态指示器
        if (pagedjs.isRendering !== oldPagedjs.isRendering) {
            this.updateRenderingIndicator(pagedjs.isRendering);
        }
        
        // 显示错误信息
        if (pagedjs.error !== oldPagedjs.error) {
            this.updateErrorDisplay(pagedjs.error);
        }
    }

    /**
     * 更新页数显示
     */
    updatePageCountDisplay(pageCount) {
        const pageCountElements = document.querySelectorAll('.page-count');
        pageCountElements.forEach(element => {
            element.textContent = pageCount || '0';
        });
        
        console.log(`[DOM更新器] 页数显示已更新: ${pageCount}`);
    }

    /**
     * 更新渲染状态指示器
     */
    updateRenderingIndicator(isRendering) {
        const indicators = document.querySelectorAll('.rendering-indicator');
        indicators.forEach(indicator => {
            indicator.classList.toggle('active', isRendering);
        });
        
        console.log(`[DOM更新器] 渲染状态指示器: ${isRendering ? '显示' : '隐藏'}`);
    }

    /**
     * 更新错误显示
     */
    updateErrorDisplay(error) {
        const errorElements = document.querySelectorAll('.error-display');
        errorElements.forEach(element => {
            if (error) {
                element.textContent = error;
                element.style.display = 'block';
            } else {
                element.style.display = 'none';
            }
        });
        
        if (error) {
            console.error(`[DOM更新器] 显示错误: ${error}`);
        }
    }

    /**
     * 更新加载指示器
     */
    updateLoadingIndicator(loading) {
        const indicators = document.querySelectorAll('.loading-indicator');
        indicators.forEach(indicator => {
            indicator.style.display = loading ? 'block' : 'none';
        });
    }

    /**
     * 派发内容变化事件
     */
    dispatchContentChangeEvent(container) {
        const event = new CustomEvent('resumeContentChanged', {
            detail: {
                container: container,
                timestamp: new Date()
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * 派发样式变化事件
     */
    dispatchStyleChangeEvent(styles) {
        const event = new CustomEvent('resumeStyleChanged', {
            detail: {
                styles: styles,
                timestamp: new Date()
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * 获取当前状态
     */
    getStatus() {
        return {
            isInitialized: this.isInitialized,
            isProcessingQueue: this.isProcessingQueue,
            queueLength: this.updateQueue.length,
            listenerCount: this.unsubscribeFunctions.length
        };
    }

    /**
     * 清理资源
     */
    destroy() {
        console.log('[DOM更新器] 清理DOM更新监听器资源...');
        
        // 取消所有状态订阅
        this.unsubscribeFunctions.forEach(unsubscribe => {
            if (typeof unsubscribe === 'function') {
                unsubscribe();
            }
        });
        this.unsubscribeFunctions = [];
        
        // 清空更新队列
        this.updateQueue = [];
        
        this.isInitialized = false;
        this.isProcessingQueue = false;
        
        console.log('[DOM更新器] ✅ DOM更新监听器资源已清理');
    }
}

// 创建全局实例
let domUpdater = null;

/**
 * 初始化DOM更新器
 */
async function initDOMUpdater() {
    if (domUpdater) {
        console.warn('[DOM更新器] DOM更新器已存在，跳过初始化');
        return domUpdater;
    }
    
    domUpdater = new DOMUpdater();
    await domUpdater.init();
    
    // 设置全局引用
    window.domUpdater = domUpdater;
    
    return domUpdater;
}

// 自动初始化（如果在浏览器环境中）
if (typeof window !== 'undefined') {
    // 等待DOM和状态管理器准备就绪
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(initDOMUpdater, 200);
        });
    } else {
        setTimeout(initDOMUpdater, 200);
    }
}

// 导出供 Node.js 使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        DOMUpdater,
        initDOMUpdater
    };
}