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
            console.log('[DOM???] ??????', {
                actionType: action.type,
                payload: action.payload,
                newStylesKeys: newState.styles ? Object.keys(newState.styles) : [],
                oldStylesKeys: oldState.styles ? Object.keys(oldState.styles) : []
            });

            if (action.type === 'SET_STYLES') {
                console.log('[DOM???] ?? SET_STYLES ?????????');
                this.queueUpdate('styles', () => this.updateStylesDOM(newState.styles, oldState.styles));
                return;
            }

            if (action.type === 'UPDATE_STYLES') {
                console.log('[DOM???] ?? UPDATE_STYLES ?????????');
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
     * 向内容容器派发内容变化事件，供其他模块（如分页器）感知
     */
    dispatchContentChangeEvent(container) {
        try {
            const evt = new CustomEvent('contentChanged', {
                bubbles: true,
                detail: { timestamp: Date.now() }
            });
            container.dispatchEvent(evt);
            console.log('[DOM更新器] 已派发 contentChanged 事件');

            // 可选：通过统一队列请求一次更新
            if (window.pagedJsManager && typeof window.pagedJsManager.requestUpdate === 'function') {
                window.pagedJsManager.requestUpdate('domUpdater-content-changed');
            }
        } catch (e) {
            console.warn('[DOM更新器] 派发内容变化事件失败:', e);
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
        const styleDiff = {};
        if (styles) {
            Object.keys(styles).forEach((key) => {
                if (!oldStyles || styles[key] !== oldStyles[key]) {
                    styleDiff[key] = {
                        previous: oldStyles ? oldStyles[key] : undefined,
                        next: styles[key]
                    };
                }
            });
        }

        console.log('[DOM???] ??????', styleDiff);

        const root = document.documentElement;

        // ????? CSS ???--???
        if (styles) {
            Object.entries(styles).forEach(([key, value]) => {
                if (key.startsWith('--') && typeof value !== 'undefined') {
                    const previous = oldStyles ? oldStyles[key] : undefined;
                    if (previous !== value) {
                        root.style.setProperty(key, value);
                        console.log(`[DOM???] ??CSS??: ${key} = ${value}`);
                    }
                }
            });
        }

    }

                    /**
                     * 更新 UI DOM（占位实现：根据需要扩展）
                     * 保持为 async 以兼容队列中的 await 调用
                     */
                    async updateUIDOM(ui, oldUi = {}) {
                        try {
                            // 这里可以根据 ui.previewMode / ui.loading 等，更新页面提示或样式
                            console.log('[DOM更新器] UI 状态更新:', { ui, oldUi });
                        } catch (e) {
                            console.error('[DOM更新器] UI DOM 更新失败:', e);
                        }
                    }

                    /**
                     * 更新 Paged.js 相关 DOM（占位实现：根据需要扩展）
                     * 保持为 async 以兼容队列中的 await 调用
                     */
                    async updatePagedJsDOM(pagedjs, oldPagedjs = {}) {
                        try {
                            // 可在此根据 pagedjs.pageCount / isRendering，显示加载状态或统计信息
                            console.log('[DOM更新器] Paged.js 状态更新:', {
                                isRendering: pagedjs?.isRendering,
                                pageCount: pagedjs?.pageCount,
                                lastRenderTime: pagedjs?.lastRenderTime
                            });
                        } catch (e) {
                            console.error('[DOM更新器] Paged.js DOM 更新失败:', e);
                        }
                    }

}

let domUpdaterInstance = null;
let domUpdaterPromise = null;

function initDOMUpdater(options = {}) {
    const { forceReinitialize = false } = options;

    if (typeof window === 'undefined') {
        console.warn('[DOMUpdater] initDOMUpdater requires a browser environment');
        return Promise.resolve(null);
    }

    if (domUpdaterInstance && domUpdaterInstance.isInitialized && !forceReinitialize) {
        return Promise.resolve(domUpdaterInstance);
    }

    if (!domUpdaterInstance || forceReinitialize) {
        domUpdaterInstance = new DOMUpdater();
    }

    if (domUpdaterInstance.isInitialized && !forceReinitialize) {
        return Promise.resolve(domUpdaterInstance);
    }

    if (!domUpdaterPromise || forceReinitialize) {
        try {
            const initResult = domUpdaterInstance.init();
            if (initResult && typeof initResult.then === 'function') {
                domUpdaterPromise = initResult.then(() => domUpdaterInstance);
            } else {
                domUpdaterPromise = Promise.resolve(domUpdaterInstance);
            }
        } catch (error) {
            domUpdaterPromise = Promise.reject(error);
        }
    }

    return domUpdaterPromise.catch(error => {
        domUpdaterPromise = null;
        throw error;
    });
}

if (typeof window !== 'undefined') {
    window.DOMUpdater = DOMUpdater;
    window.initDOMUpdater = initDOMUpdater;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DOMUpdater;
    module.exports.initDOMUpdater = initDOMUpdater;
}
