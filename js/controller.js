// 简历控制器 - 专门用于外层控制页面
class ResumeController {
  constructor() {
    // 模块实例
    this.config = null;
    this.styleController = null;
    this.sliderController = null;
    
    // UI元素
    this.iframe = null;
    this.setDefaultButton = null;
    this.printButton = null;
    
    // 状态
    this.isInitialized = false;
    this.isIframeReady = false;
  }

  /**
   * 初始化控制器
   */
  async init() {
    try {
      console.log('开始初始化简历控制器...');
      
      // 获取DOM元素
      this.iframe = document.getElementById('innerFrame');
      this.setDefaultButton = document.getElementById('setDefaultButton');
      this.printButton = document.getElementById('printButton');
      
      if (!this.iframe) {
        throw new Error('找不到iframe元素');
      }

      // 初始化模块
      this.initializeModules();
      
      // 初始化滑杆控制器
      this.sliderController.init();
      
      // 设置事件监听
      this.setupEventListeners();
      
      // 等待iframe加载
      await this.waitForIframeLoad();
      
      this.isInitialized = true;
      console.log('简历控制器初始化完成');
      
    } catch (error) {
      console.error('控制器初始化失败:', error);
      throw error;
    }
  }

  /**
   * 初始化模块
   */
  initializeModules() {
    // 获取配置
    this.config = window.ResumeConfig;
    if (!this.config) {
      throw new Error('配置文件未加载');
    }

    // 初始化样式控制器
    this.styleController = new StyleController(this.config);
    
    // 初始化滑杆控制器
    this.sliderController = new SliderController(
      this.config,
      this.styleController,
      (data) => this.sendMessageToIframe(data)
    );

    // 设置滑杆回调
    this.sliderController.setCallbacks({
      onSliderChange: (config, value, cssValue, result) => {
        console.log(`滑杆变化: ${config.id} = ${value} (CSS: ${cssValue})`);
      },
      onDefaultsSet: () => {
        console.log('默认值已设置');
        alert('默认值已设置！');
      }
    });

    console.log('控制器模块初始化完成');
  }

  /**
   * 设置事件监听
   */
  setupEventListeners() {
    // 设置默认值按钮
    if (this.setDefaultButton) {
      this.setDefaultButton.addEventListener('click', () => {
        this.sliderController.setAllToDefaults();
      });
    }

    // 打印按钮
    if (this.printButton) {
      this.printButton.addEventListener('click', () => {
        this.sendMessageToIframe({ type: 'print' });
      });
    }

    // 监听来自iframe的消息
    window.addEventListener('message', (event) => {
      this.handleMessage(event);
    });

    // 错误处理
    window.addEventListener('error', (event) => {
      console.error('全局错误:', event.error);
    });

    console.log('事件监听器设置完成');
  }

  /**
   * 等待iframe加载完成
   */
  waitForIframeLoad() {
    return new Promise((resolve) => {
      const onLoad = () => {
        setTimeout(() => {
          this.onIframeLoaded();
          resolve();
        }, 200);
      };

      if (this.iframe.contentDocument && this.iframe.contentDocument.readyState === 'complete') {
        onLoad();
      } else {
        this.iframe.addEventListener('load', onLoad);
      }
    });
  }

  /**
   * iframe加载完成处理
   */
  onIframeLoaded() {
    this.isIframeReady = true;
    
    // 发送初始样式到iframe
    this.sendInitialStyles();
    
    console.log('iframe加载完成');
  }

  /**
   * 发送初始样式到iframe
   */
  sendInitialStyles() {
    // 延迟发送，确保iframe内部初始化完成
    setTimeout(() => {
      this.sliderController.triggerAllSliders();
    }, 300);
  }

  /**
   * 向iframe发送消息
   */
  sendMessageToIframe(data) {
    if (this.iframe && this.iframe.contentWindow && this.isIframeReady) {
      this.iframe.contentWindow.postMessage(data, '*');
    }
  }

  /**
   * 处理来自iframe的消息
   */
  handleMessage(event) {
    // 基础安全检查
    if (event.origin !== window.location.origin && event.origin !== 'null') {
      console.warn('收到来自未知源的消息:', event.origin);
      return;
    }

    const data = event.data;
    if (!data || !data.type) return;

    try {
      switch (data.type) {
        case 'cssUpdateConfirmed':
          this.handleCSSUpdateConfirmed(data);
          break;
        case 'viewerReady':
          this.handleViewerReady();
          break;
        case 'error':
          this.handleIframeError(data);
          break;
        case 'rendering':
          this.setControlsEnabled(false);
          break;
        case 'rendered':
          this.setControlsEnabled(true);
          break;
        default:
          console.log('未知消息类型:', data.type);
      }
    } catch (error) {
      console.error(`消息处理失败 [${data.type}]:`, error);
    }
  }

  /**
   * 启用/禁用外层控制（滑杆、按钮）
   */
  setControlsEnabled(enabled) {
    try {
      if (this.config && this.config.sliderConfig) {
        this.config.sliderConfig.forEach(cfg => {
          const el = document.getElementById(cfg.id);
          if (el) el.disabled = !enabled;
        });
      }
      if (this.setDefaultButton) this.setDefaultButton.disabled = !enabled;
      if (this.printButton) this.printButton.disabled = !enabled;
    } catch (e) {
      console.warn('切换控件可用状态失败:', e);
    }
  }

  /**
   * 处理CSS更新确认
   */
  handleCSSUpdateConfirmed(data) {
    if (data.success) {
      console.log(`CSS变量 ${data.variable} 更新成功`);
    } else {
      console.error(`CSS变量 ${data.variable} 更新失败:`, data.error);
    }
  }

  /**
   * 处理查看器就绪
   */
  handleViewerReady() {
    console.log('查看器已就绪');
    this.sendInitialStyles();
  }

  /**
   * 处理iframe错误
   */
  handleIframeError(data) {
    console.error('iframe错误:', data.message);
  }

  /**
   * 加载指定简历
   */
  loadResume(resumeId) {
    this.sendMessageToIframe({
      type: 'loadResume',
      resumeId: resumeId
    });
  }

  /**
   * 更新简历内容
   */
  updateContent(content) {
    this.sendMessageToIframe({
      type: 'updateContent',
      content: content
    });
  }

  /**
   * 重置所有滑杆为默认值
   */
  resetToDefaults() {
    this.sliderController.resetAllToDefaults();
  }

  /**
   * 获取当前滑杆值
   */
  getCurrentSliderValues() {
    return this.sliderController.getAllSliderValues();
  }

  /**
   * 设置滑杆值
   */
  setSliderValue(sliderId, value) {
    this.sliderController.setSliderValue(sliderId, value);
  }

  /**
   * 导出配置
   */
  exportConfig() {
    return {
      sliders: this.sliderController.exportSliderConfig(),
      styles: this.styleController.getCurrentStyles()
    };
  }

  /**
   * 导入配置
   */
  importConfig(config) {
    if (config.sliders) {
      this.sliderController.importSliderConfig(config.sliders);
    }
  }

  /**
   * 获取状态
   */
  getState() {
    return {
      isInitialized: this.isInitialized,
      isIframeReady: this.isIframeReady,
      sliderValues: this.getCurrentSliderValues()
    };
  }
}

// 全局控制器实例
let resumeController = null;

// 初始化函数
async function initializeResumeController() {
  try {
    console.log('🚀 开始初始化简历控制器...');
    
    // 1. 首先初始化状态管理器
    if (typeof bootResumeState === 'function') {
      const bootInfo = bootResumeState({
        attachMiddleware: true,
        initializeDomUpdater: true,
        context: 'outer-controller'
      });
      console.log('✅ 状态管理系统已准备 (instance: ' + bootInfo.instanceId + ', created: ' + bootInfo.created + ')');
    } else if (typeof ResumeStateManager !== 'undefined') {
      console.warn('⚠️ bootResumeState 未定义，回退到直接实例化');
      if (!window.ResumeState) {
        window.ResumeState = new ResumeStateManager();
      }
    } else {
      console.warn('⚠️ 无法初始化状态管理器，继续以传统模式运行');
    }

    // 2. 初始化主控制器
    resumeController = new ResumeController();
    await resumeController.init();
    
    // 暴露到全局
    window.resumeController = resumeController;
    
    console.log('🎉 简历控制器初始化完成');
    
  } catch (error) {
    console.error('❌ 控制器启动失败:', error);
  }
}

// 注意：此文件的自动初始化已被移除，以避免与iframe内容页的viewer.js竞争
// 外层页面(outer_resume_display.html)会手动调用 initializeResumeController() 来初始化

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ResumeController, initializeResumeController };
} else {
  window.ResumeController = ResumeController;
  window.initializeResumeController = initializeResumeController;
}
