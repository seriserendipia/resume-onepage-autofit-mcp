/**
 * 简历状态管理器
 * 负责管理所有应用状态，包括内容、样式、Paged.js状态等
 */
class ResumeStateManager {
    constructor() {
        // 初始状态
        this.state = {
            // 内容状态
            content: {
                markdown: '',
                html: '',
                lastModified: null,
                source: null // 内容来源（文件路径等）
            },
            
            // 样式状态
            styles: {
                fontSize: 16,
                lineHeight: 1.6,
                margins: { 
                    top: 20, 
                    bottom: 20, 
                    left: 20, 
                    right: 20 
                },
                fontFamily: 'Arial, sans-serif'
            },
            
            // Paged.js状态
            pagedjs: {
                isReady: false,
                isRendering: false,
                lastRenderTime: null,
                pageCount: 0,
                renderQueue: [],
                error: null
            },
            
            // UI状态
            ui: {
                debugMode: false,
                previewMode: 'web', // 'web' | 'print'
                showPageNumbers: true,
                loading: false,
                isLoading: false,
                operation: null,
                lastLoadedFile: null,
                error: null
            },
            
            // 文件状态
            files: {
                currentFileId: null,
                currentFileName: null,
                currentFilePath: null,
                availableFiles: []
            }
        };
        
        // 监听器存储
        this.listeners = new Map();
        
        // 中间件数组
        this.middleware = [];
        
        // 状态变化历史（用于调试）
        this.history = [];
        
        this.__instanceId = 'state_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
        console.log('[StateManager] 状态管理器已初始化: ' + this.__instanceId);
    }
    
    /**
     * 获取当前状态的深拷贝
     */
    getState() {
        return JSON.parse(JSON.stringify(this.state));
    }
    
    /**
     * 获取特定路径的状态
     */
    getStateByPath(path) {
        const keys = path.split('.');
        let current = this.state;
        
        for (const key of keys) {
            if (current && typeof current === 'object' && key in current) {
                current = current[key];
            } else {
                return undefined;
            }
        }
        
        return JSON.parse(JSON.stringify(current));
    }
    
    /**
     * 派发状态变更动作
     */
    dispatch(action) {
        const oldState = this.getState();
        
        console.log('[StateManager] 派发动作:', action.type, action.payload);
        
        // 执行中间件链
        let processedAction = action;
        for (const middleware of this.middleware) {
            const result = middleware(processedAction, oldState);
            if (result) {
                processedAction = result;
            }
        }
        
        // 更新状态
        const newState = this.reducer(oldState, processedAction);
        this.state = newState;
        
        // 记录历史
        this.history.push({
            action: processedAction,
            timestamp: new Date(),
            oldState: oldState,
            newState: newState
        });
        
        // 限制历史记录数量
        if (this.history.length > 50) {
            this.history.shift();
        }
        
        // 通知所有监听器
        this.notifyListeners(processedAction, oldState, newState);
        
        return newState;
    }
    
    /**
     * 状态减少器 - 根据动作类型更新状态
     */
    reducer(state, action) {
        const newState = JSON.parse(JSON.stringify(state));
        
        switch (action.type) {
            case 'SET_CONTENT':
                newState.content = { 
                    ...newState.content, 
                    ...action.payload,
                    lastModified: new Date()
                };
                break;
                
            case 'SET_STYLES':
                // 处理CSS变量样式更新
                const { source, ...styles } = action.payload;
                newState.styles = { 
                    ...newState.styles, 
                    ...styles 
                };
                console.log(`[StateManager] 样式已更新 (来源: ${source}):`, styles);
                break;
                
            case 'UPDATE_STYLES':
                newState.styles = { 
                    ...newState.styles, 
                    ...action.payload 
                };
                break;
                
            case 'SET_LOADING_STATE':
                // 处理加载状态更新
                newState.ui = {
                    ...newState.ui,
                    ...action.payload
                };
                console.log(`[StateManager] 加载状态已更新:`, action.payload);
                break;
                
            case 'SET_CURRENT_FILE':
                // 处理当前文件信息更新
                newState.files = {
                    ...newState.files,
                    currentFileId: action.payload.fileId,
                    currentFileName: action.payload.fileName,
                    currentFilePath: action.payload.filePath
                };
                console.log(`[StateManager] 当前文件已更新: ${action.payload.fileName}`);
                break;
                
            case 'PAGEDJS_STATE_CHANGE':
                newState.pagedjs = { 
                    ...newState.pagedjs, 
                    ...action.payload 
                };
                break;
                
            case 'UI_STATE_CHANGE':
                newState.ui = { 
                    ...newState.ui, 
                    ...action.payload 
                };
                break;
                
            case 'RESET_STATE':
                // 重置到初始状态，但保留某些设置
                const preservedSettings = {
                    styles: newState.styles,
                    ui: { ...newState.ui, loading: false }
                };
                Object.assign(newState, this.getInitialState(), preservedSettings);
                break;
                
            default:
                console.warn('[StateManager] 未知的动作类型:', action.type);
                break;
        }
        
        return newState;
    }
    
    /**
     * 订阅状态变化
     */
    subscribe(key, callback) {
        if (!this.listeners.has(key)) {
            this.listeners.set(key, []);
        }
        
        const callbacks = this.listeners.get(key);
        callbacks.push(callback);
        
        console.log(`[StateManager] 新增监听器: ${key}, 当前监听器数量: ${callbacks.length}`);
        
        // 返回取消订阅函数
        return () => {
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
                console.log(`[StateManager] 移除监听器: ${key}`);
            }
        };
    }
    
    /**
     * 通知所有监听器
     */
    notifyListeners(action, oldState, newState) {
        this.listeners.forEach((callbacks, key) => {
            callbacks.forEach(callback => {
                try {
                    callback(action, oldState, newState);
                } catch (error) {
                    console.error(`[StateManager] 监听器 ${key} 执行出错:`, error);
                }
            });
        });
    }
    
    /**
     * 添加中间件
     */
    use(middleware) {
        this.middleware.push(middleware);
        console.log('[StateManager] 添加中间件，当前中间件数量:', this.middleware.length);
        return this;
    }
    
    /**
     * 获取初始状态
     */
    getInitialState() {
        return {
            content: {
                markdown: '',
                html: '',
                lastModified: null,
                source: null
            },
            styles: {
                fontSize: 16,
                lineHeight: 1.6,
                margins: { top: 20, bottom: 20, left: 20, right: 20 },
                fontFamily: 'Arial, sans-serif'
            },
            pagedjs: {
                isReady: false,
                isRendering: false,
                lastRenderTime: null,
                pageCount: 0,
                renderQueue: [],
                error: null
            },
            ui: {
                debugMode: false,
                previewMode: 'web',
                showPageNumbers: true,
                loading: false
            }
        };
    }
    
    /**
     * 获取状态变化历史（调试用）
     */
    getHistory() {
        return [...this.history];
    }
    
    /**
     * 清空历史记录
     */
    clearHistory() {
        this.history = [];
        console.log('[StateManager] 历史记录已清空');
    }
}

const resumeStateBootStatus = {
    middlewareAttached: false,
    domUpdaterInitialized: false,
    domUpdaterPromise: null
};

function bootResumeState(options = {}) {
    const {
        attachMiddleware = false,
        initializeDomUpdater = false,
        context = 'unknown'
    } = options;

    if (typeof window === 'undefined') {
        console.warn('[StateManager] bootResumeState called outside of browser environment');
        return { state: null, created: false, instanceId: null };
    }

    let created = false;
    if (!(window.ResumeState instanceof ResumeStateManager)) {
        window.ResumeState = new ResumeStateManager();
        created = true;
        console.log('[StateManager] 创建新的全局状态管理器(' + window.ResumeState.__instanceId + ') - 来源: ' + context);
    } else {
        console.log('[StateManager] 复用全局状态管理器(' + window.ResumeState.__instanceId + ') - 来源: ' + context);
    }

    const state = window.ResumeState;

    if (attachMiddleware) {
        if (typeof createPagedJsMiddleware === 'function') {
            if (!resumeStateBootStatus.middlewareAttached) {
                const middleware = createPagedJsMiddleware();
                if (middleware) {
                    state.use(middleware);
                    resumeStateBootStatus.middlewareAttached = true;
                    console.log('[StateManager] 已挂载 PagedJs 中间件');
                }
            } else {
                console.log('[StateManager] PagedJs 中间件已挂载，跳过');
            }
        } else {
            console.warn('[StateManager] createPagedJsMiddleware 未加载，无法挂载');
        }
    }

    if (initializeDomUpdater) {
        if (typeof initDOMUpdater === 'function') {
            if (!resumeStateBootStatus.domUpdaterInitialized) {
                try {
                    const initResult = initDOMUpdater();
                    if (initResult && typeof initResult.then === 'function') {
                        resumeStateBootStatus.domUpdaterPromise = initResult.then((instance) => {
                            console.log('[StateManager] DOM 更新器初始化完成');
                            return instance;
                        }).catch((error) => {
                            console.error('[StateManager] DOM 更新器初始化失败:', error);
                            throw error;
                        });
                    } else {
                        resumeStateBootStatus.domUpdaterPromise = Promise.resolve(initResult);
                        console.log('[StateManager] DOM 更新器初始化已触发');
                    }
                    resumeStateBootStatus.domUpdaterInitialized = true;
                } catch (error) {
                    console.error('[StateManager] DOM 更新器初始化失败:', error);
                }
            } else {
                console.log('[StateManager] DOM 更新器已初始化，跳过');
            }
        } else {
            console.warn('[StateManager] initDOMUpdater 未加载，无法初始化 DOM 更新器');
        }
    }

    return {
        state,
        created,
        instanceId: state.__instanceId,
        middlewareAttached: resumeStateBootStatus.middlewareAttached,
        domUpdaterInitialized: resumeStateBootStatus.domUpdaterInitialized,
        domUpdaterPromise: resumeStateBootStatus.domUpdaterPromise
    };
}

if (typeof window !== 'undefined') {
    window.bootResumeState = bootResumeState;
}

// 如果在Node.js 环境，导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ResumeStateManager;
    module.exports.bootResumeState = bootResumeState;
}
