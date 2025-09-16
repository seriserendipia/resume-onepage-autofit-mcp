// 样式控制器 - 管理CSS变量和样式状态，与状态管理系统集成
class StyleController {
  constructor(config) {
    this.config = config;
    this.currentStyles = {};
    this.defaultStyles = config.defaultStyles;
    this.isStateManaged = false; // 是否使用状态管理
    this.init();
  }

  /**
   * 初始化样式控制器
   */
  async init() {
    // 检查状态管理器是否可用
    if (await this.waitForStateManager()) {
      this.isStateManaged = true;
      console.log('🎨 样式控制器已与状态管理系统集成');
    } else {
      console.warn('⚠️ 状态管理器不可用，样式控制器使用传统模式');
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
   * 从localStorage获取配置值
   * @param {string} key - 键名
   * @param {any} fallback - 默认值
   * @returns {string} - 配置值
   */
  get(key, fallback) {
    return localStorage.getItem(key) || fallback;
  }

  /**
   * 向localStorage设置配置值
   * @param {string} key - 键名
   * @param {any} value - 值
   */
  set(key, value) {
    localStorage.setItem(key, value);
  }

  /**
   * 获取所有默认样式值
   * @returns {Object} - 默认样式对象
   */
  getAllDefaults() {
    const defaults = {};
    this.config.sliderConfig.forEach(cfg => {
      const element = document.getElementById(cfg.id);
      const defaultValue = element ? (element.defaultValue || element.value) : this.defaultStyles[cfg.id];
      defaults[cfg.id] = this.get(cfg.storage, defaultValue);
    });
    return defaults;
  }

  /**
   * 保存所有当前样式值为默认值
   */
  setAllDefaults() {
    this.config.sliderConfig.forEach(cfg => {
      const element = document.getElementById(cfg.id);
      if (element) {
        this.set(cfg.storage, element.value);
      }
    });
    console.log('所有样式默认值已保存');
  }

  /**
   * 应用单个CSS变量
   * @param {string} variable - CSS变量名
   * @param {any} value - CSS变量值
   * @returns {Object} - 包含成功状态和实际值的对象
   */
  applyCSSVariable(variable, value) {
    try {
      // 如果使用状态管理，通过状态系统更新
      if (this.isStateManaged) {
        console.log(`🎨 通过状态管理更新CSS变量: ${variable} = ${value}`);
        
        window.ResumeState.dispatch({
          type: 'SET_STYLES',
          payload: {
            [variable]: value,
            source: 'styleController'
          }
        });
        
        // 更新本地记录
        this.currentStyles[variable] = value;
        
        return {
          success: true,
          variable: variable,
          value: value,
          method: 'state-managed'
        };
      } else {
        // 传统模式：直接操作DOM
        document.documentElement.style.setProperty(variable, value);
        
        // 验证CSS变量是否成功设置
        const actualValue = getComputedStyle(document.documentElement).getPropertyValue(variable);
        
        // 更新当前样式记录
        this.currentStyles[variable] = value;
        
        console.log(`CSS变量应用成功（传统模式）: ${variable} = ${value}`);
        
        return {
          success: true,
          variable: variable,
          value: value,
          actualValue: actualValue.trim(),
          method: 'direct-dom'
        };
      }
      
    } catch (error) {
      console.error(`CSS变量应用失败: ${variable}`, error);
      return {
        success: false,
        variable: variable,
        value: value,
        error: error.message
      };
    }
  }

  /**
   * 批量应用CSS变量
   * @param {Object} styles - 样式对象 {variable: value, ...}
   * @returns {Array} - 应用结果数组
   */
  applyMultipleStyles(styles) {
    if (this.isStateManaged) {
      // 状态管理模式：批量更新
      console.log(`🎨 通过状态管理批量更新CSS变量:`, styles);
      
      window.ResumeState.dispatch({
        type: 'SET_STYLES',
        payload: {
          ...styles,
          source: 'styleController-batch'
        }
      });
      
      // 更新本地记录
      Object.assign(this.currentStyles, styles);
      
      return Object.entries(styles).map(([variable, value]) => ({
        success: true,
        variable,
        value,
        method: 'state-managed-batch'
      }));
      
    } else {
      // 传统模式：逐个应用
      const results = [];
      
      Object.entries(styles).forEach(([variable, value]) => {
        const result = this.applyCSSVariable(variable, value);
        results.push(result);
      });
      
      console.log('批量样式应用完成（传统模式）:', results);
      return results;
    }
  }

  /**
   * 根据滑杆配置计算CSS值
   * @param {Object} sliderConfig - 滑杆配置
   * @param {string|number} rawValue - 原始值
   * @returns {string|number} - 计算后的CSS值
   */
  calculateCSSValue(sliderConfig, rawValue) {
    let cssValue = rawValue;
    
    // 应用单位
    if (sliderConfig.unit) {
      cssValue = rawValue + sliderConfig.unit;
    }
    
    // 应用缩放
    if (sliderConfig.scale) {
      cssValue = rawValue * sliderConfig.scale;
    }
    
    return cssValue;
  }

  /**
   * 从滑杆配置应用样式
   * @param {Object} sliderConfig - 滑杆配置
   * @param {string|number} value - 滑杆值
   * @returns {Object} - 应用结果
   */
  applyStyleFromSlider(sliderConfig, value) {
    const cssValue = this.calculateCSSValue(sliderConfig, value);
    return this.applyCSSVariable(sliderConfig.cssVar, cssValue);
  }

  /**
   * 初始化所有默认样式
   */
  initializeDefaultStyles() {
    const defaults = this.getAllDefaults();
    const stylesToApply = {};
    
    this.config.sliderConfig.forEach(cfg => {
      const rawValue = defaults[cfg.id] || this.defaultStyles[cfg.storage];
      const cssValue = this.calculateCSSValue(cfg, rawValue);
      stylesToApply[cfg.cssVar] = cssValue;
    });
    
    this.applyMultipleStyles(stylesToApply);
    console.log('默认样式初始化完成');
  }

  /**
   * 重置所有样式为默认值
   */
  resetToDefaults() {
    const stylesToApply = {};
    
    this.config.sliderConfig.forEach(cfg => {
      const defaultValue = this.defaultStyles[cfg.storage];
      const cssValue = this.calculateCSSValue(cfg, defaultValue);
      stylesToApply[cfg.cssVar] = cssValue;
      
      // 同时重置滑杆值
      const element = document.getElementById(cfg.id);
      if (element) {
        element.value = defaultValue;
      }
    });
    
    this.applyMultipleStyles(stylesToApply);
    console.log('样式已重置为默认值');
  }

  /**
   * 获取当前所有样式值
   * @returns {Object} - 当前样式对象
   */
  getCurrentStyles() {
    return { ...this.currentStyles };
  }

  /**
   * 导出样式配置
   * @returns {Object} - 样式配置对象
   */
  exportStyleConfig() {
    const config = {};
    
    this.config.sliderConfig.forEach(cfg => {
      const element = document.getElementById(cfg.id);
      if (element) {
        config[cfg.id] = {
          value: element.value,
          cssVar: cfg.cssVar,
          cssValue: this.currentStyles[cfg.cssVar]
        };
      }
    });
    
    return config;
  }

  /**
   * 导入样式配置
   * @param {Object} styleConfig - 样式配置对象
   */
  importStyleConfig(styleConfig) {
    const stylesToApply = {};
    
    Object.entries(styleConfig).forEach(([sliderId, config]) => {
      const element = document.getElementById(sliderId);
      if (element && config.cssValue) {
        element.value = config.value;
        stylesToApply[config.cssVar] = config.cssValue;
      }
    });
    
    this.applyMultipleStyles(stylesToApply);
    console.log('样式配置导入完成');
  }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
  module.exports = StyleController;
} else {
  window.StyleController = StyleController;
}