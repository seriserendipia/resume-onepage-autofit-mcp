// 数据加载器 - 专门处理本地Markdown文件的读取，与状态管理系统集成
class DataLoader {
  constructor(config) {
    this.config = config;
    this.cache = new Map(); // 简单的缓存机制
    this.isStateManaged = false; // 是否使用状态管理
    this.init();
  }

  /**
   * 初始化数据加载器
   */
  async init() {
    // 检查状态管理器是否可用
    if (await this.waitForStateManager()) {
      this.isStateManaged = true;
      console.log('📊 数据加载器已与状态管理系统集成');
    } else {
      console.warn('⚠️ 状态管理器不可用，数据加载器使用传统模式');
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
   * 加载Markdown文件
   * @param {string} filePath - 文件路径
   * @returns {Promise<string>} - 文件内容
   */
  async loadMarkdown(filePath) {
    try {
      // 检查缓存
      if (this.cache.has(filePath)) {
        console.log(`📦 从缓存加载: ${filePath}`);
        return this.cache.get(filePath);
      }

      console.log(`📂 正在加载文件: ${filePath}`);
      
      // 如果使用状态管理，通知开始加载
      if (this.isStateManaged) {
        window.ResumeState.dispatch({
          type: 'SET_LOADING_STATE',
          payload: {
            isLoading: true,
            operation: 'loadMarkdown',
            filePath: filePath
          }
        });
      }

      const response = await fetch(filePath);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: 无法加载 ${filePath}`);
      }

      const content = await response.text();
      
      // 存入缓存
      this.cache.set(filePath, content);
      
      console.log(`✅ 文件加载成功: ${filePath}, 内容长度: ${content.length}`);
      
      // 如果使用状态管理，通知加载完成
      if (this.isStateManaged) {
        window.ResumeState.dispatch({
          type: 'SET_LOADING_STATE',
          payload: {
            isLoading: false,
            operation: null,
            lastLoadedFile: filePath
          }
        });
      }
      
      return content;
      
    } catch (error) {
      console.error(`❌ 文件加载失败: ${filePath}`, error);
      
      // 如果使用状态管理，通知错误状态
      if (this.isStateManaged) {
        window.ResumeState.dispatch({
          type: 'SET_LOADING_STATE',
          payload: {
            isLoading: false,
            operation: null,
            error: error.message
          }
        });
      }
      
      throw new Error(`加载简历失败：${error.message}`);
    }
  }

  /**
   * 根据文件ID加载简历
   * @param {string} fileId - 文件ID
   * @returns {Promise<string>} - 文件内容
   */
  async loadResumeById(fileId) {
    const fileConfig = this.config.dataSources.availableFiles.find(f => f.id === fileId);
    if (!fileConfig) {
      throw new Error(`找不到文件ID: ${fileId}`);
    }

    console.log(`📂 通过ID加载简历: ${fileId}`);
    
    const content = await this.loadMarkdown(fileConfig.path);
    
    // 如果使用状态管理，更新当前文件ID
    if (this.isStateManaged) {
      window.ResumeState.dispatch({
        type: 'SET_CURRENT_FILE',
        payload: {
          fileId: fileId,
          fileName: fileConfig.name,
          filePath: fileConfig.path
        }
      });
    }
    
    return content;
  }

  /**
   * 获取可用文件列表
   * @returns {Array} - 文件列表
   */
  getAvailableFiles() {
    return this.config.dataSources.availableFiles;
  }

  /**
   * 清除缓存
   * @param {string} filePath - 可选，指定文件路径
   */
  clearCache(filePath = null) {
    if (filePath) {
      this.cache.delete(filePath);
      console.log(`已清除缓存: ${filePath}`);
    } else {
      this.cache.clear();
      console.log('已清除所有缓存');
    }
  }

  /**
   * 预加载所有可用文件
   * @returns {Promise<void>}
   */
  async preloadAll() {
    const files = this.getAvailableFiles();
    const promises = files.map(file => 
      this.loadMarkdown(file.path).catch(err => 
        console.warn(`预加载失败: ${file.path}`, err)
      )
    );
    
    await Promise.allSettled(promises);
    console.log('预加载完成');
  }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
  module.exports = DataLoader;
} else {
  window.DataLoader = DataLoader;
}