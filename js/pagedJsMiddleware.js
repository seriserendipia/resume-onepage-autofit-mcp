/**
 * Paged.js 中间件
 * 负责处理与 Paged.js 渲染相关的状态变化和任务队列管理
 */

/**
 * Paged.js 中间件函数
 * 在状态变化时自动管理 Paged.js 渲染队列
 */
function createPagedJsMiddleware() {
    return function pagedJsMiddleware(action, state) {
        // 需要触发重新渲染的动作类型
        const renderTriggerActions = [
            'SET_CONTENT',
            'UPDATE_STYLES'
        ];
        
        // 如果是触发渲染的动作
        if (renderTriggerActions.includes(action.type)) {
            console.log('[PagedJs中间件] 检测到需要重新渲染的动作:', action.type);
            
            // 创建渲染任务
            const renderTask = {
                id: `render_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                reason: action.type,
                timestamp: new Date(),
                priority: getRenderPriority(action.type),
                payload: action.payload
            };
            
            // 检查当前队列，避免重复任务
            const currentQueue = state.pagedjs.renderQueue || [];
            const hasSimilarTask = currentQueue.some(task => 
                task.reason === action.type && 
                (Date.now() - new Date(task.timestamp).getTime()) < 1000 // 1秒内的相似任务
            );
            
            if (!hasSimilarTask) {
                console.log('[PagedJs中间件] 添加渲染任务到队列:', renderTask.id);
                
                // 返回修改后的动作，同时添加渲染任务
                return {
                    ...action,
                    meta: {
                        ...action.meta,
                        triggersRender: true,
                        renderTask: renderTask
                    }
                };
            } else {
                console.log('[PagedJs中间件] 跳过重复的渲染任务');
            }
        }
        
        // 处理 Paged.js 特定状态变化
        if (action.type === 'PAGEDJS_STATE_CHANGE') {
            // 如果包含渲染任务，添加到队列
            if (action.payload && action.payload.addRenderTask) {
                const newTask = action.payload.addRenderTask;
                console.log('[PagedJs中间件] 收到直接渲染任务请求:', newTask.id);
                // 统一转为带 meta 的动作，交给 RenderTaskProcessor 监听后入队
                return {
                    ...action,
                    meta: {
                        ...action.meta,
                        triggersRender: true,
                        renderTask: newTask
                    }
                };
            }
            
            // 如果渲染完成，清理相关状态
            if (action.payload && action.payload.isRendering === false) {
                console.log('[PagedJs中间件] 渲染完成，清理状态');
            }
        }
        
        return action;
    };
}

/**
 * 获取渲染优先级
 */
function getRenderPriority(actionType) {
    const priorities = {
        'SET_CONTENT': 1,        // 最高优先级
        'UPDATE_STYLES': 2,      // 中等优先级
        'UI_STATE_CHANGE': 3     // 低优先级
    };
    
    return priorities[actionType] || 5;
}

/**
 * 渲染任务处理器
 * 处理渲染队列中的任务
 */
class RenderTaskProcessor {
    constructor(stateManager) {
        this.stateManager = stateManager;
        this.isProcessing = false;
        this.processingTimeout = null;
        
        // 监听状态变化
        this.setupListeners();
    }
    
    setupListeners() {
        // 监听渲染队列变化
        this.stateManager.subscribe('renderQueue', (action, oldState, newState) => {
            // 当有新的渲染任务时，处理队列
            if (action.meta && action.meta.triggersRender) {
                this.addTaskToQueue(action.meta.renderTask);
                this.scheduleProcessing();
            }
        });
    }
    
    /**
     * 添加任务到队列
     */
    addTaskToQueue(task) {
        this.stateManager.dispatch({
            type: 'PAGEDJS_STATE_CHANGE',
            payload: {
                renderQueue: [
                    ...this.stateManager.getStateByPath('pagedjs.renderQueue'),
                    task
                ]
            }
        });
    }
    
    /**
     * 安排处理队列（防抖）
     */
    scheduleProcessing() {
        // 清除之前的超时
        if (this.processingTimeout) {
            clearTimeout(this.processingTimeout);
        }
        
        // 设置新的超时（防抖 300ms）
        this.processingTimeout = setTimeout(() => {
            this.processQueue();
        }, 300);
    }
    
    /**
     * 处理渲染队列
     */
    async processQueue() {
        const state = this.stateManager.getState();
        
        // 如果正在渲染或队列为空，跳过
        if (this.isProcessing || state.pagedjs.isRendering || state.pagedjs.renderQueue.length === 0) {
            return;
        }
        
        this.isProcessing = true;
        
        try {
            // 标记开始渲染
            this.stateManager.dispatch({
                type: 'PAGEDJS_STATE_CHANGE',
                payload: {
                    isRendering: true,
                    error: null
                }
            });
            
            // 获取最高优先级的任务
            const queue = [...state.pagedjs.renderQueue];
            queue.sort((a, b) => a.priority - b.priority);
            const nextTask = queue[0];
            
            console.log('[渲染处理器] 开始处理任务:', nextTask.id, '原因:', nextTask.reason);
            
            // 执行渲染
            await this.executeRenderTask(nextTask);
            
            // 渲染成功，更新状态
            this.stateManager.dispatch({
                type: 'PAGEDJS_STATE_CHANGE',
                payload: {
                    isRendering: false,
                    lastRenderTime: new Date(),
                    renderQueue: [], // 清空队列
                    error: null
                }
            });
            
            console.log('[渲染处理器] 渲染完成');
            
        } catch (error) {
            console.error('[渲染处理器] 渲染失败:', error);
            
            // 渲染失败，更新错误状态
            this.stateManager.dispatch({
                type: 'PAGEDJS_STATE_CHANGE',
                payload: {
                    isRendering: false,
                    error: error.message || '渲染失败'
                }
            });
        } finally {
            this.isProcessing = false;
        }
    }
    
    /**
     * 执行渲染任务
     */
    async executeRenderTask(task) {
        // 这里将调用实际的 PagedJsManager
        if (window.pagedJsManager && typeof window.pagedJsManager.performUpdate === 'function') {
            await window.pagedJsManager.performUpdate(task.reason, {
                taskId: task.id,
                priority: task.priority
            });
        } else {
            console.warn('[渲染处理器] PagedJsManager 未准备就绪');
            // 模拟渲染延迟
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    }
}

/**
 * 初始化 Paged.js 中间件和任务处理器
 */
function initPagedJsMiddleware() {
    if (typeof window !== 'undefined' && window.ResumeState) {
        // 添加中间件
        const middleware = createPagedJsMiddleware();
        window.ResumeState.use(middleware);
        
        // 创建任务处理器
        window.renderTaskProcessor = new RenderTaskProcessor(window.ResumeState);
        
        console.log('[PagedJs中间件] 中间件和任务处理器已初始化');
        
        return {
            middleware,
            processor: window.renderTaskProcessor
        };
    } else {
        console.error('[PagedJs中间件] ResumeState 未找到，无法初始化中间件');
        return null;
    }
}

// 自动初始化（如果在浏览器环境中）
if (typeof window !== 'undefined') {
    // 等待 ResumeState 准备就绪
    if (window.ResumeState) {
        initPagedJsMiddleware();
    } else {
        // 如果 ResumeState 还没准备好，等待 DOM 加载完成
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                if (window.ResumeState) {
                    initPagedJsMiddleware();
                } else {
                    console.error('[PagedJs中间件] ResumeState 在 DOM 加载后仍未找到');
                }
            }, 100);
        });
    }
}

// 导出供 Node.js 使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        createPagedJsMiddleware,
        RenderTaskProcessor,
        initPagedJsMiddleware
    };
}