// 状态驱动的渲染引擎 - 处理Markdown到HTML转换，与状态管理系统集成
class ResumeRenderer {
  constructor() {
    this.contentElement = null;
    this.isStateManaged = false; // 是否使用状态管理
    this.renderQueue = []; // 渲染队列（仅用于回退模式）
    this.isRendering = false;
    this.debounceTimer = null;
    this.debounceDelay = 200;
    this.fontsReady = false;
    this.isPagedJsReady = false; // 回退模式使用
  }

  /**
   * 初始化渲染器
   * @param {HTMLElement} contentElement - 内容容器元素
   */
  async init(contentElement) {
    this.contentElement = contentElement;
    
    console.log('🎨 初始化状态驱动的渲染器...');
    
    // 尝试使用状态管理系统
    await this.setupStateIntegration();
    
    // 设置自动缩放（与状态管理无关的功能）
    this.setupAutoScale();
    
    console.log('✅ 状态驱动的渲染器初始化完成');
  }

  /**
   * 设置状态管理集成
   */
  async setupStateIntegration() {
    // 等待状态管理器就绪
    if (await this.waitForStateManager()) {
      this.isStateManaged = true;
      console.log('🔗 渲染器已与状态管理系统集成');
    } else {
      console.warn('⚠️ 状态管理器不可用，使用传统模式');
      this.isStateManaged = false;
      // 在传统模式下设置Paged.js
      this.setupPagedJs();
    }
  }

  /**
   * 等待状态管理器就绪
   */
  async waitForStateManager(timeout = 2000) {
    return new Promise((resolve) => {
      const startTime = Date.now();
      const check = () => {
        if (typeof window.ResumeState !== 'undefined') {
          resolve(true);
        } else if (Date.now() - startTime > timeout) {
          resolve(false);
        } else {
          setTimeout(check, 100);
        }
      };
      check();
    });
  }

  /**
   * 渲染Markdown内容
   * @param {string} markdownContent - Markdown内容
   * @returns {Promise<string>} 返回渲染后的HTML
   */
  async renderMarkdown(markdownContent) {
    if (!this.contentElement) {
      throw new Error('渲染器未初始化，请先调用 init() 方法');
    }

    try {
      // 检查marked.js是否可用
      if (typeof marked === 'undefined') {
        throw new Error('marked.js 未加载');
      }

      console.log('🎨 开始渲染Markdown内容');
      
      // 转换Markdown为HTML
      const htmlContent = marked.parse(markdownContent);
      
      console.log('📝 Markdown转换完成，HTML长度:', htmlContent.length);
      
      if (this.isStateManaged) {
        // 使用状态管理系统
        console.log('🔄 通过状态管理系统更新内容...');
        
        window.ResumeState.dispatch({
          type: 'SET_CONTENT',
          payload: {
            markdown: markdownContent,
            html: htmlContent,
            source: 'renderer'
          }
        });
        
        console.log('✅ 内容已通过状态系统更新');
      } else {
        // 回退到直接DOM操作
        console.log('⚠️ 直接更新DOM（回退模式）');
        this.contentElement.innerHTML = htmlContent;
        
        // 尝试手动触发Paged.js（如果可用）
        this.triggerLegacyRender();
      }
      
      return htmlContent;
      
    } catch (error) {
      console.error('❌ Markdown渲染失败:', error);
      
      const errorHtml = `<p style="color:red">渲染失败：${error.message}</p>`;
      
      if (this.isStateManaged) {
        window.ResumeState.dispatch({
          type: 'SET_CONTENT',
          payload: {
            html: errorHtml,
            error: error.message
          }
        });
      } else {
        this.contentElement.innerHTML = errorHtml;
      }
      
      throw error;
    }
  }

  /**
   * 触发传统渲染（回退模式）
   */
  triggerLegacyRender() {
    console.log('🔄 触发传统Paged.js渲染...');
    
    // 尝试调用viewer.js的管理器
    if (window.pagedJsManager && typeof window.pagedJsManager.requestUpdate === 'function') {
      window.pagedJsManager.requestUpdate('renderer-legacy');
    } else if (this.isPagedJsReady && window.PagedPolyfill) {
      // 直接调用Paged.js
      this.previewDebounced();
    }
  }

  /**
   * 设置Paged.js（传统模式）
   */
  setupPagedJs() {
    console.log('🔄 设置传统Paged.js模式...');
    
    // 等待Paged.js加载完成
    const checkPagedJs = () => {
      if (typeof window.PagedPolyfill !== 'undefined') {
        this.isPagedJsReady = true;
        console.log('✅ Paged.js 已准备就绪（传统模式）');
        this.setupRenderHooks();
      } else {
        setTimeout(checkPagedJs, 100);
      }
    };

    checkPagedJs();
  }

  /**
   * 应用单个CSS变量（传统模式）
   * @param {string} variable - CSS变量名
   * @param {string} value - 值
   */
  applyCSSVariable(variable, value) {
    if (this.isStateManaged) {
      console.warn('⚠️ 状态管理模式下不应直接调用applyCSSVariable');
      return;
    }

    try {
      document.documentElement.style.setProperty(variable, value);
      console.log(`应用样式: ${variable} = ${value}`);
      
      // 触发重新渲染（节流）
      this.previewDebounced();
      
    } catch (error) {
      console.error('应用样式失败:', error);
    }
  }

  /**
   * 批量应用CSS变量（传统模式）
   * @param {Object} styles - 样式对象
   */
  applyStyles(styles) {
    if (this.isStateManaged) {
      console.warn('⚠️ 状态管理模式下不应直接调用applyStyles');
      return;
    }

    Object.entries(styles).forEach(([variable, value]) => {
      document.documentElement.style.setProperty(variable, value);
    });
    
    console.log('批量应用样式:', styles);
    this.previewDebounced();
  }

  /**
   * 统一的预览节流，避免频繁调用 preview()（传统模式）
   */
  previewDebounced() {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    this.debounceTimer = setTimeout(async () => {
      this.debounceTimer = null;
      if (!this.isPagedJsReady) return;
      try {
        console.log('🎨 [previewDebounced] 即将调用 PagedPolyfill.preview()');
        
        await this.waitForFonts();
        window.PagedPolyfill.preview();
        
      } catch (error) {
        console.error('Paged.js 渲染失败:', error);
      }
    }, this.debounceDelay);
  }

  /**
   * 监听渲染事件钩子，维护渲染状态（传统模式）
   */
  setupRenderHooks() {
    document.addEventListener('pagedjs:rendering', () => {
      this.isRendering = true;
      try { 
        if (window.parent && window.parent !== window) { 
          window.parent.postMessage({ type: 'rendering' }, '*'); 
        } 
      } catch (e) {}
    });
    
    document.addEventListener('pagedjs:rendered', () => {
      this.isRendering = false;
      try { 
        if (window.parent && window.parent !== window) { 
          window.parent.postMessage({ type: 'rendered' }, '*'); 
        } 
      } catch (e) {}
    });
  }

  /**
   * 在渲染前等待字体加载
   */
  async waitForFonts() {
    if (this.fontsReady) return;
    try {
      if (document.fonts && document.fonts.ready) {
        await document.fonts.ready;
      }
    } catch (e) {
      // 忽略字体API不可用
    } finally {
      this.fontsReady = true;
    }
  }

  /**
   * 设置自动缩放
   */
  setupAutoScale() {
    // 这部分功能与状态管理无关，保持原有逻辑
    console.log('🔧 设置自动缩放功能');
  }

  /**
   * 获取状态
   */
  getStatus() {
    return {
      isStateManaged: this.isStateManaged,
      isPagedJsReady: this.isPagedJsReady,
      isRendering: this.isRendering,
      fontsReady: this.fontsReady
    };
  }

  /**
   * 设置Paged.js就绪状态（供外部调用）
   */
  setPagedJsReady(ready = true) {
    this.isPagedJsReady = ready;
    console.log(`🎨 Paged.js就绪状态: ${ready}`);
  }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ResumeRenderer;
} else {
  window.ResumeRenderer = ResumeRenderer;
}