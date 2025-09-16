// 简历管理器 - 统一管理简历的CRUD操作
class ResumeManager {
  constructor(config, dataLoader, renderer, styleController) {
    this.config = config;
    this.dataLoader = dataLoader;
    this.renderer = renderer;
    this.styleController = styleController;
    
    this.currentResumeId = config.dataSources.currentSource;
    this.currentContent = null;
    this.isLoading = false;
    
    // 事件回调
    this.onLoadStart = null;
    this.onLoadSuccess = null;
    this.onLoadError = null;
    this.onRenderComplete = null;
  }

  /**
   * 初始化简历管理器
   * @param {HTMLElement} contentElement - 内容容器元素
   */
  async init(contentElement) {
    try {
      // 初始化渲染器
      this.renderer.init(contentElement);
      
      // 初始化默认样式
      this.styleController.initializeDefaultStyles();
      
      // 加载默认简历
      await this.loadCurrentResume();
      
      console.log('简历管理器初始化完成');
      
    } catch (error) {
      console.error('简历管理器初始化失败:', error);
      throw error;
    }
  }

  /**
   * 加载当前简历
   * @returns {Promise<string>} - 简历内容
   */
  async loadCurrentResume() {
    return await this.loadResume(this.currentResumeId);
  }

  /**
   * 加载指定简历
   * @param {string} resumeId - 简历ID
   * @returns {Promise<string>} - 简历内容
   */
  async loadResume(resumeId) {
    if (this.isLoading) {
      console.warn('正在加载中，请稍候...');
      return;
    }

    this.isLoading = true;
    
    try {
      // 触发加载开始回调
      if (this.onLoadStart) {
        this.onLoadStart(resumeId);
      }

      console.log(`开始加载简历: ${resumeId}`);
      
      // 加载Markdown内容
      const content = await this.dataLoader.loadResumeById(resumeId);
      
      // 渲染内容
      await this.renderer.renderMarkdown(content);
      
      // 更新状态
      this.currentResumeId = resumeId;
      this.currentContent = content;
      
      // 触发加载成功回调
      if (this.onLoadSuccess) {
        this.onLoadSuccess(resumeId, content);
      }

      // 触发渲染完成回调
      if (this.onRenderComplete) {
        this.onRenderComplete();
      }

      console.log(`简历加载完成: ${resumeId}`);
      return content;
      
    } catch (error) {
      console.error(`简历加载失败: ${resumeId}`, error);
      
      // 触发加载错误回调
      if (this.onLoadError) {
        this.onLoadError(resumeId, error);
      }
      
      throw error;
      
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * 切换简历
   * @param {string} resumeId - 新的简历ID
   * @returns {Promise<string>} - 简历内容
   */
  async switchResume(resumeId) {
    if (resumeId === this.currentResumeId) {
      console.log('已是当前简历，无需切换');
      return this.currentContent;
    }

    return await this.loadResume(resumeId);
  }

  /**
   * 重新加载当前简历
   * @returns {Promise<string>} - 简历内容
   */
  async reloadCurrentResume() {
    // 清除缓存
    const currentFile = this.getFileConfig(this.currentResumeId);
    if (currentFile) {
      this.dataLoader.clearCache(currentFile.path);
    }
    
    return await this.loadCurrentResume();
  }

  /**
   * 更新简历内容（仅内存中，不保存到文件）
   * @param {string} content - 新的内容
   * @returns {Promise<void>}
   */
  async updateContent(content) {
    try {
      console.log('更新简历内容');
      
      // 渲染新内容
      await this.renderer.renderMarkdown(content);
      
      // 更新当前内容
      this.currentContent = content;
      
      // 触发渲染完成回调
      if (this.onRenderComplete) {
        this.onRenderComplete();
      }
      
      console.log('简历内容更新完成');
      
    } catch (error) {
      console.error('简历内容更新失败:', error);
      throw error;
    }
  }

  /**
   * 应用样式
   * @param {string} variable - CSS变量名
   * @param {any} value - CSS变量值
   * @returns {Object} - 应用结果
   */
  applyStyle(variable, value) {
    const result = this.styleController.applyCSSVariable(variable, value);
    
    // 触发渲染器重新渲染
    this.renderer.previewDebounced();
    
    return result;
  }

  /**
   * 批量应用样式
   * @param {Object} styles - 样式对象
   * @returns {Array} - 应用结果数组
   */
  applyStyles(styles) {
    const results = this.styleController.applyMultipleStyles(styles);
    
    // 触发渲染器重新渲染
    this.renderer.previewDebounced();
    
    return results;
  }

  /**
   * 获取可用简历文件列表
   * @returns {Array} - 文件列表
   */
  getAvailableResumes() {
    return this.dataLoader.getAvailableFiles();
  }

  /**
   * 获取当前简历信息
   * @returns {Object} - 当前简历信息
   */
  getCurrentResumeInfo() {
    return {
      id: this.currentResumeId,
      content: this.currentContent,
      config: this.getFileConfig(this.currentResumeId),
      isLoading: this.isLoading
    };
  }

  /**
   * 获取文件配置
   * @param {string} resumeId - 简历ID
   * @returns {Object|null} - 文件配置
   */
  getFileConfig(resumeId) {
    return this.config.dataSources.availableFiles.find(f => f.id === resumeId) || null;
  }

  /**
   * 预加载所有简历
   * @returns {Promise<void>}
   */
  async preloadAll() {
    try {
      await this.dataLoader.preloadAll();
      console.log('所有简历预加载完成');
    } catch (error) {
      console.error('简历预加载失败:', error);
    }
  }

  /**
   * 设置事件回调
   * @param {Object} callbacks - 回调函数对象
   */
  setCallbacks(callbacks) {
    this.onLoadStart = callbacks.onLoadStart || null;
    this.onLoadSuccess = callbacks.onLoadSuccess || null;
    this.onLoadError = callbacks.onLoadError || null;
    this.onRenderComplete = callbacks.onRenderComplete || null;
  }

  /**
   * 导出当前状态
   * @returns {Object} - 当前状态对象
   */
  exportState() {
    return {
      currentResumeId: this.currentResumeId,
      currentContent: this.currentContent,
      styles: this.styleController.getCurrentStyles(),
      styleConfig: this.styleController.exportStyleConfig()
    };
  }

  /**
   * 导入状态
   * @param {Object} state - 状态对象
   * @returns {Promise<void>}
   */
  async importState(state) {
    try {
      // 导入样式配置
      if (state.styleConfig) {
        this.styleController.importStyleConfig(state.styleConfig);
      }
      
      // 切换简历
      if (state.currentResumeId) {
        await this.switchResume(state.currentResumeId);
      }
      
      // 如果有自定义内容，更新内容
      if (state.currentContent && state.currentContent !== this.currentContent) {
        await this.updateContent(state.currentContent);
      }
      
      console.log('状态导入完成');
      
    } catch (error) {
      console.error('状态导入失败:', error);
      throw error;
    }
  }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ResumeManager;
} else {
  window.ResumeManager = ResumeManager;
}
