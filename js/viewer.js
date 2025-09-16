// ✨ 状态驱动的 Paged.js 管理器 - 与状态管理系统集成
class PagedJsManager {
  constructor() {
    this.isReady = false;
    this.pendingOperations = [];
    this.debounceTimer = null;
    this.debounceDelay = 300;
    this.isProcessing = false;
    this.stateUnsubscribe = null; // 状态订阅取消函数
  }

  /**
   * 初始化管理器
   */
  async init() {
    console.log('🎨 初始化状态驱动的Paged.js管理器...');
    
    // 等待状态管理器和Paged.js加载
    await this.waitForDependencies();
    
    // 设置事件监听
    this.setupEventListeners();
    
    // 设置状态管理集成
    this.setupStateIntegration();
    
    // 更新Paged.js就绪状态
    this.updatePagedJsReadyState(true);
    
    this.isReady = true;
    console.log('✅ 状态驱动的Paged.js管理器就绪');
    
    // 处理积压的操作
    this.processPendingOperations();
  }

  /**
   * 等待依赖项加载
   */
  async waitForDependencies() {
    // 等待状态管理器
    await this.waitForStateManager();
    
    // 等待Paged.js加载
    await this.waitForPagedJs();
  }

  /**
   * 等待状态管理器
   */
  async waitForStateManager() {
    return new Promise((resolve) => {
      const check = () => {
        if (typeof window.ResumeState !== 'undefined') {
          console.log('✅ 状态管理器已就绪');
          resolve();
        } else {
          setTimeout(check, 100);
        }
      };
      check();
    });
  }

  /**
   * 等待Paged.js加载
   */
  async waitForPagedJs() {
    return new Promise((resolve) => {
      const check = () => {
        if (typeof window.PagedPolyfill !== 'undefined') {
          console.log('✅ Paged.js已加载');
          resolve();
        } else {
          setTimeout(check, 100);
        }
      };
      check();
    });
  }

  /**
   * 设置事件监听
   */
  setupEventListeners() {
    // 监听Paged.js渲染完成
    document.addEventListener('pagedjs:rendered', () => {
      console.log('🎨 Paged.js渲染完成事件');
      this.isProcessing = false;
      this.ensureContentVisible();
      
      // 更新状态：渲染完成
      this.updateRenderCompleteState();
    });

    // 监听窗口大小变化
    window.addEventListener('resize', () => {
      this.requestUpdate('resize');
    });
  }

  /**
   * 设置状态管理集成
   */
  setupStateIntegration() {
    if (!window.ResumeState) {
        console.error('❌ 依赖加载超时，未就绪依赖: ' + missing.join(', '));
      return;
    }

    // 注册为全局PagedJsManager实例，供中间件调用
    window.pagedJsManager = this;

    console.log('🔗 Paged.js管理器已与状态管理系统集成');
  }

  /**
   * 更新Paged.js就绪状态
   */
  updatePagedJsReadyState(isReady) {
    if (window.ResumeState) {
      window.ResumeState.dispatch({
        type: 'PAGEDJS_STATE_CHANGE',
        payload: { 
          isReady: isReady,
          lastReadyTime: new Date()
        }
      });
    }
  }

  /**
   * 更新渲染完成状态
   */
  updateRenderCompleteState() {
    if (window.ResumeState) {
      // 计算页数
      const pageCount = document.querySelectorAll('.pagedjs_page').length;
      
      window.ResumeState.dispatch({
        type: 'PAGEDJS_STATE_CHANGE',
        payload: { 
          isRendering: false,
          lastRenderTime: new Date(),
          pageCount: pageCount,
          renderQueue: [], // 清空队列
          error: null
        }
      });
      
      console.log(`📊 渲染完成，页数: ${pageCount}`);
    }
  }

  /**
   * 🎯 兼容性入口：请求更新Paged.js显示
   * 现在通过状态管理系统工作
   * @param {string} reason - 更新原因
   * @param {Object} options - 更新选项
   */
  requestUpdate(reason = 'unknown', options = {}) {
    console.log(`📝 请求Paged.js更新(兼容模式): ${reason}`);

    if (!this.isReady) {
      console.log('⏳ Paged.js未就绪，加入待处理队列');
      this.pendingOperations.push({ reason, options, timestamp: Date.now() });
      return;
    }

    // 通过状态管理系统触发更新
    if (window.ResumeState) {
      window.ResumeState.dispatch({
        type: 'PAGEDJS_STATE_CHANGE',
        payload: {
          addRenderTask: {
            id: `compat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            reason: `compat_${reason}`,
            timestamp: new Date(),
            priority: 3, // 兼容性调用的优先级稍低
            payload: options
          }
        }
      });
    } else {
      // 如果状态管理器不可用，回退到直接调用
      console.warn('⚠️ 状态管理器不可用，回退到直接渲染');
      this.performUpdateLegacy(reason, options);
    }
  }

  /**
   * 传统的直接更新方法（回退用）
   */
  performUpdateLegacy(reason, options) {
    // 防抖处理，避免频繁更新
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      this.performUpdate(reason, options);
    }, this.debounceDelay);
  }

  /**
   * 执行Paged.js更新（被状态管理系统调用）
   */
  async performUpdate(reason = 'unknown', options = {}) {
    if (this.isProcessing) {
      console.log('⚠️ Paged.js正在处理中，跳过本次更新');
      return;
    }

    console.log(`🎨 执行Paged.js更新: ${reason}`);
    this.isProcessing = true;

    // 更新状态：开始渲染
    this.updateRenderStartState(reason, options);

    try {
      // 严格检查 Paged.js 可用性
      if (!window.PagedPolyfill) {
        throw new Error('PagedPolyfill 未定义');
      }
      
      if (!window.PagedPolyfill.preview) {
        throw new Error('PagedPolyfill.preview 方法不可用');
      }

      console.log('📄 调用 Paged.js 进行分页渲染');
      await window.PagedPolyfill.preview();
      
      // 等待渲染完成
      await this.waitForRenderComplete();

      console.log(`✅ Paged.js更新完成: ${reason}`);
    } catch (error) {
        console.error('❌ 依赖加载超时，未就绪依赖: ' + missing.join(', '));
      this.isProcessing = false;
      
      // 更新状态：渲染失败
      this.updateRenderErrorState(error);
      
      // 重新抛出错误，让调用者知道失败了
      throw error;
    }
  }

  /**
   * 更新渲染开始状态
   */
  updateRenderStartState(reason, options) {
    if (window.ResumeState) {
      window.ResumeState.dispatch({
        type: 'PAGEDJS_STATE_CHANGE',
        payload: { 
          isRendering: true,
          lastRenderReason: reason,
          lastRenderOptions: options,
          error: null
        }
      });
    }
  }

  /**
   * 更新渲染错误状态
   */
  updateRenderErrorState(error) {
    if (window.ResumeState) {
      window.ResumeState.dispatch({
        type: 'PAGEDJS_STATE_CHANGE',
        payload: { 
          isRendering: false,
          error: error.message || '渲染失败'
        }
      });
    }
  }

  /**
   * 等待渲染完成
   */
  async waitForRenderComplete() {
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        console.log('⚠️ Paged.js渲染超时，继续执行');
        this.isProcessing = false;
        resolve();
      }, 2000);

      const checkComplete = () => {
        const pagedArea = document.querySelector('.pagedjs_area');
        if (pagedArea && pagedArea.innerHTML.length > 100) {
          clearTimeout(timeout);
          this.ensureContentVisible();
          resolve();
        } else {
          setTimeout(checkComplete, 100);
        }
      };

      setTimeout(checkComplete, 200);
    });
  }

  /**
   * 确保内容可见
   */
  ensureContentVisible() {
    const pagedContainer = document.querySelector('.pagedjs_pages');
    const pagedArea = document.querySelector('.pagedjs_area');
    const pagedPage = document.querySelector('.pagedjs_page');

    if (pagedContainer && pagedArea && pagedPage) {
      // 确保整个Paged.js容器链条可见
      pagedContainer.style.visibility = 'visible';
      pagedContainer.style.display = 'flex';
      pagedContainer.style.opacity = '1';

      pagedPage.style.visibility = 'visible';
      pagedPage.style.display = 'block';
      pagedPage.style.opacity = '1';

      pagedArea.style.visibility = 'visible';
      pagedArea.style.display = 'block';
      pagedArea.style.opacity = '1';

      console.log('✅ Paged.js内容已确保可见');
    } else {
      console.log('⚠️ Paged.js容器未找到');
    }
  }

  /**
   * 处理积压的操作
   */
  processPendingOperations() {
    if (this.pendingOperations.length > 0) {
      console.log(`📋 处理${this.pendingOperations.length}个积压操作`);
      
      // 只执行最新的操作，忽略过期的
      const latestOp = this.pendingOperations[this.pendingOperations.length - 1];
      this.pendingOperations = [];
      
      this.requestUpdate(`pending-${latestOp.reason}`, latestOp.options);
    }
  }

  /**
   * 获取状态信息
   */
  getStatus() {
    return {
      isReady: this.isReady,
      isProcessing: this.isProcessing,
      pendingCount: this.pendingOperations.length,
      hasPagedContent: !!document.querySelector('.pagedjs_area')
    };
  }

  /**
   * 清理资源
   */
  destroy() {
    console.log('🧹 清理Paged.js管理器资源...');
    
    // 清理定时器
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
    
    // 清理状态订阅
    if (this.stateUnsubscribe) {
      this.stateUnsubscribe();
      this.stateUnsubscribe = null;
    }
    
    // 清理全局引用
    if (window.pagedJsManager === this) {
      window.pagedJsManager = null;
    }
    
    // 更新状态
    this.updatePagedJsReadyState(false);
    
    this.isReady = false;
    this.pendingOperations = [];
    
    console.log('✅ Paged.js管理器资源已清理');
  }
}

// 简历查看器 - 专门用于内层 iframe 页面
class ResumeViewer {
  constructor() {
    // 模块实例
    this.config = null;
    this.dataLoader = null;
    this.renderer = null;
    this.styleController = null;
    this.resumeManager = null;

    // UI 元素
    this.contentElement = null;

    // 状态
    this.isInitialized = false;
    
    // ✨ 统一的 Paged.js 管理器
    this.pagedJsManager = new PagedJsManager();
  }

  /**
   * 初始化查看器
   */
  async init() {
    try {
      console.log('=== 开始初始化简历查看器 ===');
      console.log('当前DOM状态:', document.readyState);

      // 获取 DOM 元素
      this.contentElement = document.getElementById('content');
      if (!this.contentElement) {
        throw new Error('找不到 content 元素');
      }
      console.log('✅ content 元素已找到, 当前内容:', this.contentElement.innerHTML.substring(0, 100));

      // 初始化模块
      console.log('开始初始化模块...');
      await this.initializeModules();
      console.log('✅ 模块初始化完成');

      // 设置消息监听
      this.setupMessageHandlers();
      console.log('✅ 消息监听器设置完成');

      // 🎯 初始化统一的Paged.js管理器
      await this.pagedJsManager.init();

      // 初始化简历管理器
      console.log('开始初始化简历管理器...');
      console.log('初始化前content内容:', this.contentElement.innerHTML.substring(0, 100));
      
      await this.resumeManager.init(this.contentElement);
      
      console.log('初始化后content内容:', this.contentElement.innerHTML.substring(0, 100));
      console.log('✅ 简历管理器初始化完成');

      // 🎯 请求首次Paged.js渲染
      this.pagedJsManager.requestUpdate('initial-load');

      this.isInitialized = true;
      console.log('=== 简历查看器初始化完成 ===');

    } catch (error) {
      console.error('查看器初始化失败:', error);
      this.handleError(error);
      throw error;
    }
  }

  /**
   * 初始化模块
   */
  async initializeModules() {
    // 检查必要的依赖
    console.log('检查依赖加载状态');
    console.log('- marked:', typeof marked !== 'undefined' ? '✅' : '❌');
    console.log('- PagedPolyfill:', typeof window.PagedPolyfill !== 'undefined' ? '✅' : '❌');
    console.log('- ResumeConfig:', typeof window.ResumeConfig !== 'undefined' ? '✅' : '❌');
    console.log('- DataLoader:', typeof window.DataLoader !== 'undefined' ? '✅' : '❌');
    console.log('- ResumeRenderer:', typeof window.ResumeRenderer !== 'undefined' ? '✅' : '❌');
    console.log('- StyleController:', typeof window.StyleController !== 'undefined' ? '✅' : '❌');
    console.log('- ResumeManager:', typeof window.ResumeManager !== 'undefined' ? '✅' : '❌');

    // 获取配置
    this.config = window.ResumeConfig;
    if (!this.config) {
      throw new Error('配置文件未加载');
    }
    console.log('✅ 配置加载成功，当前数据源:', this.config.dataSources.currentSource);

    // 检查 marked.js
    if (typeof marked === 'undefined') {
      throw new Error('marked.js 未加载');
    }

    // 初始化数据加载器
    console.log('初始化数据加载器...');
    this.dataLoader = new DataLoader(this.config);

    // 初始化渲染器
    console.log('初始化渲染器...');
    this.renderer = new ResumeRenderer();

    // 初始化样式控制器
    console.log('初始化样式控制器...');
    this.styleController = new StyleController(this.config);

    // 初始化简历管理器
    console.log('初始化简历管理器...');
    this.resumeManager = new ResumeManager(
      this.config,
      this.dataLoader,
      this.renderer,
      this.styleController
    );

    // 设置回调
    this.resumeManager.setCallbacks({
      onLoadStart: (resumeId) => {
        console.log(`📂 开始加载简历: ${resumeId}`);
        console.log('加载前content内容:', this.contentElement ? this.contentElement.innerHTML.substring(0, 100) : 'content元素不存在');
      },
      onLoadSuccess: (resumeId, content) => {
        console.log(`✅ 简历加载成功: ${resumeId}, 内容长度: ${content.length}`);
        console.log('加载成功后content内容:', this.contentElement ? this.contentElement.innerHTML.substring(0, 100) : 'content元素不存在');
      },
      onLoadError: (resumeId, error) => {
        console.error(`❌ 简历加载失败: ${resumeId}`, error);
      },
      onRenderComplete: () => {
        console.log('🎨 渲染完成');
        console.log('渲染完成后content内容:', this.contentElement ? this.contentElement.innerHTML.substring(0, 100) : 'content元素不存在');
        
        // 🎯 使用统一入口请求更新
        this.pagedJsManager.requestUpdate('render-complete');
      }
    });

    console.log('✅ 查看器模块初始化完成');
  }

  /**
   * 设置消息处理
   */
  setupMessageHandlers() {
    window.addEventListener('message', (event) => {
      // 基础安全检查
      if (event.origin !== window.location.origin && event.origin !== 'null') {
        console.warn('收到来自未知源的消息:', event.origin);
        return;
      }

      const data = event.data;
      if (!data || !data.type) return;

      try {
        switch (data.type) {
          case 'updateCSS':
            this.handleUpdateCSS(data, event);
            break;
          case 'updatePageMargin':
            this.handleUpdatePageMargin(data);
            break;
          case 'print':
            this.handlePrint();
            break;
          case 'loadResume':
            this.handleLoadResume(data);
            break;
          case 'updateContent':
            this.handleUpdateContent(data);
            break;
          default:
            console.log('未知消息类型:', data.type);
        }
      } catch (error) {
        console.error(`消息处理失败 [${data.type}]:`, error);
      }
    });

    console.log('消息处理器设置完成');
  }

  /**
   * 处理 CSS 更新
   */
  handleUpdateCSS(data, event) {
    const result = this.styleController.applyCSSVariable(data.variable, data.value);

    // 🎯 使用统一入口请求更新
    this.pagedJsManager.requestUpdate(`css-${data.variable}`, { variable: data.variable, value: data.value });

    // 发送确认消息
    event.source.postMessage({
      type: 'cssUpdateConfirmed',
      variable: data.variable,
      value: data.value,
      success: result.success,
      error: result.error || null
    }, event.origin);

    console.log(`CSS 更新: ${data.variable} = ${data.value}`);
  }

  /**
   * 处理页面边距更新
   */
  handleUpdatePageMargin(data) {
    try {
      const styleEl = this.ensurePageMarginStyle();
      styleEl.textContent = `@page { size: A4; margin: ${data.value}; }`;
      
      // 🎯 使用统一入口请求更新
      this.pagedJsManager.requestUpdate(`page-margin`, { margin: data.value });
      
      console.log(`页面边距更新: ${data.value}`);
    } catch (error) {
      console.error('页面边距更新失败:', error);
    }
  }

  /**
   * 确保存在用于控制 @page 边距的样式标签
   */
  ensurePageMarginStyle() {
    let el = document.getElementById('page-margins');
    if (!el) {
      el = document.createElement('style');
      el.id = 'page-margins';
      document.head.appendChild(el);
    }
    return el;
  }

  /**
   * 处理打印
   */
  handlePrint() {
    try {
      window.print();

      window.onafterprint = function () {
        alert('打印完成！请检查保存的 PDF 文件。');
      };
    } catch (error) {
      console.error('打印失败:', error);
      alert('打印失败：' + error.message);
    }
  }

  /**
   * 处理简历加载
   */
  async handleLoadResume(data) {
    try {
      if (data.resumeId) {
        await this.resumeManager.switchResume(data.resumeId);
        // 🎯 使用统一入口请求更新
        this.pagedJsManager.requestUpdate(`load-resume-${data.resumeId}`);
      }
    } catch (error) {
      console.error('简历加载失败:', error);
    }
  }

  /**
   * 处理内容更新
   */
  async handleUpdateContent(data) {
    try {
      if (data.content) {
        await this.resumeManager.updateContent(data.content);
        // 🎯 使用统一入口请求更新
        this.pagedJsManager.requestUpdate('update-content');
      }
    } catch (error) {
      console.error('内容更新失败:', error);
    }
  }

  /**
   * 错误处理
   */
  handleError(error) {
    const errorMessage = `查看器错误: ${error.message}`;
    console.error(errorMessage);

    if (this.contentElement) {
      this.contentElement.innerHTML = `<p style="color:red">${errorMessage}</p>`;
    }
  }

  /**
   * 等待内容稳定，然后统一处理 Paged.js
   */
  async waitForContentStable() {
    console.log('⏳ 等待内容稳定...');
    
    // 等待一小段时间确保所有同步操作完成
    await new Promise(resolve => setTimeout(resolve, 300));
    
    console.log('📊 检查当前内容状态:');
    console.log('- 原始content长度:', this.contentElement.innerHTML.length);
    console.log('- 原始content预览:', this.contentElement.innerHTML.substring(0, 200));
    
    // 现在统一触发 Paged.js 处理
    console.log('🎨 开始统一的Paged.js处理流程...');
    
    // 确保 renderer 知道 Paged.js 的状态
    if (this.renderer && this.renderer.setPagedJsReady) {
      this.renderer.setPagedJsReady();
    }
    
    if (this.renderer && this.renderer.isPagedJsReady) {
      console.log('✅ Paged.js已就绪，触发渲染');
      this.renderer.previewDebounced();
      
      // 等待 Paged.js 处理完成
      await this.waitForPagedJsComplete();
    } else {
      console.log('⚠️ Paged.js未就绪，直接显示内容');
      this.forceContentDisplay();
    }
  }

  /**
   * 等待 Paged.js 完全处理完成
   */
  async waitForPagedJsComplete() {
    console.log('⏳ 等待Paged.js处理完成...');
    
    return new Promise((resolve) => {
      let attempts = 0;
      const maxAttempts = 20;
      
      const checkComplete = () => {
        attempts++;
        const pagedArea = document.querySelector('.pagedjs_area');
        
        if (pagedArea && pagedArea.innerHTML.length > 100) {
          console.log(`✅ Paged.js处理完成 (尝试 ${attempts}/${maxAttempts})`);
          console.log('📊 Paged.js区域内容长度:', pagedArea.innerHTML.length);
          
          // 确保显示
          this.forceContentDisplay();
          resolve();
        } else if (attempts >= maxAttempts) {
          console.warn('⚠️ Paged.js处理超时，强制显示');
          this.forceContentDisplay();
          resolve();
        } else {
          console.log(`⏳ 等待Paged.js处理... (${attempts}/${maxAttempts})`);
          setTimeout(checkComplete, 100);
        }
      };
      
      // 开始检查
      setTimeout(checkComplete, 200);
    });
  }

  /**
   * 强制显示内容 - 立即执行，不等待
   */
  forceContentDisplay() {
    console.log('🔧 强制显示内容...');
    
    // 首先检查原始content元素
    const contentEl = document.getElementById('content');
    if (!contentEl) {
        console.error('❌ 依赖加载超时，未就绪依赖: ' + missing.join(', '));
      return;
    }

    console.log('📋 原始content内容长度:', contentEl.innerHTML.length);
    console.log('📋 原始content内容预览:', contentEl.innerHTML.substring(0, 200));

    // 检查 Paged.js 是否已处理 - 查看实际内容位置
    const pagedContainer = document.querySelector('.pagedjs_pages');
    const pagedArea = document.querySelector('.pagedjs_area');
    const pagedPage = document.querySelector('.pagedjs_page');
    
    console.log('🎨 Paged.js状态:', {
      pagedContainer: !!pagedContainer,
      pagedPage: !!pagedPage,
      pagedArea: !!pagedArea,
      pagedContainerStyle: pagedContainer ? pagedContainer.style.display : 'N/A',
      pagedPageStyle: pagedPage ? pagedPage.style.display : 'N/A'
    });

    if (pagedArea) {
      // Paged.js已处理，内容在.pagedjs_area内
      console.log('✅ 发现Paged.js处理后的内容区域');
      console.log('📋 Paged.js区域内容长度:', pagedArea.innerHTML.length);
      console.log('📋 Paged.js区域内容预览:', pagedArea.innerHTML.substring(0, 200));
      
      // 确保Paged.js容器可见
      if (pagedContainer) {
        pagedContainer.style.visibility = 'visible !important';
        pagedContainer.style.display = 'flex !important';
        pagedContainer.style.opacity = '1 !important';
      }
      
      // 确保页面可见
      if (pagedPage) {
        pagedPage.style.visibility = 'visible !important';
        pagedPage.style.display = 'block !important';
        pagedPage.style.opacity = '1 !important';
      }
      
      // 确保内容区域可见
      pagedArea.style.visibility = 'visible !important';
      pagedArea.style.display = 'block !important';
      pagedArea.style.opacity = '1 !important';
      
      console.log('✅ Paged.js容器已强制显示');
    } else {
      // Paged.js未处理，直接显示原始内容
      console.log('⚠️ Paged.js容器不存在，显示原始content');
      
      // 强制设置原始content显示样式
      contentEl.style.visibility = 'visible !important';
      contentEl.style.display = 'block !important';
      contentEl.style.opacity = '1 !important';
      contentEl.style.position = 'relative';
      contentEl.style.zIndex = '9999';
      
      // 移除可能影响显示的class
      contentEl.classList.remove('pagedjs_area');
      
      // 确保内容在最前面
      contentEl.style.background = 'white';
      contentEl.style.padding = '20px';
      contentEl.style.margin = '20px';
    }

    // 更新调试信息
    if (window.debugInfo) {
      window.debugInfo.updateStatus('内容已强制显示');
      window.debugInfo.updateContentLength();
    }

    console.log('✅ 强制显示完成');
  }

  /**
   * 处理渲染完成后的显示问题
   */
  async handleRenderComplete() {
    // 立即尝试显示一次
    this.forceContentDisplay();
    
    // 等待一小段时间让Paged.js完成处理，然后再次强制显示
    setTimeout(() => {
      console.log('🔄 延迟强制显示...');
      this.forceContentDisplay();
      
      // 额外检查：如果还是看不到内容，尝试更激进的方法
      const contentEl = document.getElementById('content');
      if (contentEl && contentEl.innerHTML.length > 50) {
        // 检查元素是否真的可见
        const rect = contentEl.getBoundingClientRect();
        console.log('📐 content元素位置和大小:', {
          width: rect.width,
          height: rect.height,
          top: rect.top,
          left: rect.left,
          visible: rect.width > 0 && rect.height > 0
        });
        
        if (rect.width === 0 || rect.height === 0) {
          console.warn('⚠️ content元素尺寸为0，可能被隐藏');
          // 重置所有可能影响显示的CSS
          contentEl.style.cssText = `
            visibility: visible !important;
            display: block !important;
            opacity: 1 !important;
            position: relative !important;
            z-index: 9999 !important;
            width: auto !important;
            height: auto !important;
            background: white !important;
            padding: 20px !important;
            margin: 20px !important;
          `;
        }
        
        window.updateDebugPanel && window.updateDebugPanel('内容已强制显示');
      }
    }, 1000);
    
    // 再等待一段时间进行最终检查
    setTimeout(() => {
      console.log('🔍 最终显示检查...');
      this.forceContentDisplay();
    }, 2000);
  }

  /**
   * 获取当前状态
   */
  getState() {
    return {
      isInitialized: this.isInitialized,
      resumeInfo: this.resumeManager ? this.resumeManager.getCurrentResumeInfo() : null,
      styles: this.styleController ? this.styleController.getCurrentStyles() : null
    };
  }
}

// 全局查看器实例
let resumeViewer = null;
let isInitializing = false; // 防重复初始化标志

// 初始化函数
async function initializeResumeViewer() {
  try {
    // 防止重复初始化
    if (isInitializing || resumeViewer) {
      console.log('⚠️ 查看器已在初始化中或已初始化，跳过重复初始化');
      return;
    }
    
    isInitializing = true;
    console.log('🚀 准备启动简历查看器...');
    
    // 严格检查 Paged.js 是否可用
    if (typeof window.PagedPolyfill === 'undefined') {
      throw new Error('Paged.js 未加载 - PagedPolyfill 未定义');
    }
    
    const hasPagedHandler = (window.PagedPolyfill && window.PagedPolyfill.Handler) ||
      (window.Paged && window.Paged.Handler);

    if (!hasPagedHandler) {
      console.warn('?? Paged.js Handler ???????????????', {
        pagedPolyfillType: typeof window.PagedPolyfill,
        hasPagedNamespace: typeof window.Paged !== 'undefined'
      });
      if (window.debugInfo) {
        window.debugInfo.updatePagedJS('?? Handler ??(????)');
      }
    }

    if (typeof window.PagedPolyfill.preview !== 'function') {
      throw new Error('Paged.js preview 方法不可用');
    }
    
    console.log('✅ Paged.js 验证通过，启用分页功能');
    if (window.debugInfo && hasPagedHandler) {
      window.debugInfo.updatePagedJS('✅ 验证通过');
    }

    // 1. 初始化状态管理器（如果在iframe中且未初始化）
    if (typeof bootResumeState === 'function') {
      const bootInfo = bootResumeState({
        attachMiddleware: true,
        initializeDomUpdater: true,
        context: 'inner-viewer'
      });
      console.log('✅ iframe状态管理系统就绪 (instance: ' + bootInfo.instanceId + ', created: ' + bootInfo.created + ')');
      if (bootInfo.domUpdaterPromise && typeof bootInfo.domUpdaterPromise.then === 'function') {
        try {
          await bootInfo.domUpdaterPromise;
        } catch (error) {
          console.error('⚠️ DOM 更新器初始化失败', error);
        }
      }
    } else if (typeof ResumeStateManager !== 'undefined' && !window.ResumeState) {
      console.warn('⚠️ bootResumeState 未定义，回退到直接实例化');
      window.ResumeState = new ResumeStateManager();
      if (typeof createPagedJsMiddleware !== 'undefined') {
        const pagedJsMiddleware = createPagedJsMiddleware();
        window.ResumeState.use(pagedJsMiddleware);
      }
      if (typeof DomUpdater !== 'undefined') {
        window.domUpdater = new DomUpdater();
        await window.domUpdater.init();
      }
    }

    // 2. 等待必要的依赖加载
    // 2. 等待必要的依赖加载
    await waitForDependencies();

    // 3. 设置DOM监听器来追踪content变化
    setupContentMonitor();

    // 4. 初始化查看器
    resumeViewer = new ResumeViewer();
    await resumeViewer.init();

    // 暴露到全局
    window.resumeViewer = resumeViewer;

    console.log('🎉 简历查看器启动成功');
    
    isInitializing = false; // 重置初始化标志

  } catch (error) {
    console.error('💥 查看器启动失败', error);
    
    isInitializing = false; // 重置初始化标志
    
    // 显示错误信息给用户
    const contentElement = document.getElementById('content');
    if (contentElement) {
      contentElement.innerHTML = `
        <div style="padding: 20px; color: red; border: 1px solid red; border-radius: 5px; margin: 20px;">
          <h3>加载失败</h3>
          <p><strong>错误信息:</strong> ${error.message}</p>
          <p><strong>建议:</strong> 请检查网络连接或刷新页面重试</p>
        </div>
      `;
    }
  }
}

// 设置content元素监听器
function setupContentMonitor() {
  const contentElement = document.getElementById('content');
  if (!contentElement) return;

  console.log('🔍 设置content元素监听器');

  // 更新调试面板
  function updateDebugPanel(action) {
    const statusEl = document.getElementById('debug-status');
    const lengthEl = document.getElementById('debug-content-length');
    const updateEl = document.getElementById('debug-last-update');
    
    if (statusEl) statusEl.textContent = action;
    if (lengthEl) lengthEl.textContent = contentElement.innerHTML.length;
    if (updateEl) updateEl.textContent = new Date().toLocaleTimeString();
  }

  // 初始状态
  updateDebugPanel('监听器已设置');

  // 使用MutationObserver监听content变化
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList') {
        console.log('🔄 content子元素发生变化:', {
          addedNodes: mutation.addedNodes.length,
          removedNodes: mutation.removedNodes.length,
          currentContent: contentElement.innerHTML.substring(0, 100)
        });
        updateDebugPanel(`子元素变化: +${mutation.addedNodes.length} -${mutation.removedNodes.length}`);
      } else if (mutation.type === 'characterData') {
        console.log('📝 content文本内容发生变化:', contentElement.innerHTML.substring(0, 100));
        updateDebugPanel('文本内容变化');
      }
    });
  });

  observer.observe(contentElement, {
    childList: true,
    subtree: true,
    characterData: true
  });

  // 暴露到全局以便调试
  window.contentObserver = observer;
  window.updateDebugPanel = updateDebugPanel;
}

// 等待依赖加载和 DOM 准备
function waitForDependencies() {
  return new Promise((resolve) => {
    let attempts = 0;
    const maxAttempts = 120;
    const logInterval = 5;

    const checkDependencies = () => {
      attempts += 1;

      const contentElement = document.getElementById('content') || document.querySelector('[data-content]');
      const statusMap = {
        domReady: document.readyState === 'complete',
        contentElement: !!contentElement,
        ResumeConfig: typeof window.ResumeConfig !== 'undefined',
        DataLoader: typeof window.DataLoader !== 'undefined',
        ResumeRenderer: typeof window.ResumeRenderer !== 'undefined',
        StyleController: typeof window.StyleController !== 'undefined',
        ResumeManager: typeof window.ResumeManager !== 'undefined',
        marked: typeof marked !== 'undefined',
        PagedPolyfill: typeof window.PagedPolyfill !== 'undefined'
      };

      const missing = Object.keys(statusMap).filter((key) => !statusMap[key]);

      if (missing.length === 0) {
        console.log('✅ DOM 和所有依赖都已就绪');
        setTimeout(resolve, 100);
        return;
      }

      if (attempts % logInterval === 0) {
        console.log('⏳ 等待依赖 (' + attempts + '/' + maxAttempts + ')，未就绪: ' + missing.join(', '));
      }

      if (attempts >= maxAttempts) {
        console.error('❌ 依赖加载超时，未就绪依赖: ' + missing.join(', '));
        console.log('当前状态快照:', statusMap);
        resolve();
        return;
      }

      setTimeout(checkDependencies, 100);
    };

    checkDependencies();
  });
}

// DOM 加载完成后初始化
// 统一的初始化入口点
function startInitialization() {
  console.log('🚀 启动查看器初始化...');
  
  // 防止重复初始化
  if (window.resumeViewerInitializing || window.resumeViewer) {
    console.log('⚠️ 查看器已在初始化或已初始化，跳过');
    return;
  }
  
  window.resumeViewerInitializing = true;
  
  // 直接初始化查看器，不再等待 Paged.js
  console.log('� 直接初始化查看器...');
  initializeResumeViewer()
    .then(() => {
      console.log('✅ 查看器初始化完成');
      window.resumeViewerInitializing = false;
    })
    .catch(error => {
        console.error('❌ 依赖加载超时，未就绪依赖: ' + missing.join(', '));
      window.resumeViewerInitializing = false;
    });
}

// Paged.js 文件加载完成的回调
window.pagedJsFileLoaded = function() {
  console.log('📦 Paged.js 文件加载完成，启动初始化');
  startInitialization();
};

// DOM加载完成后启动初始化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(startInitialization, 500); // 给 Paged.js 一些加载时间
  });
} else {
  // 如果DOM已经加载完成，立即启动
  setTimeout(startInitialization, 500);
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ResumeViewer, initializeResumeViewer };
} else {
  window.ResumeViewer = ResumeViewer;
  window.initializeResumeViewer = initializeResumeViewer;
}
