// 滑杆控制器 - 管理所有滑杆的行为和配置
class SliderController {
  constructor(config, styleController, messageHandler = null) {
    this.config = config;
    this.styleController = styleController;
    this.messageHandler = messageHandler; // 用于iframe通信
    
    this.sliders = new Map(); // 存储滑杆元素引用
    this.valueDisplays = new Map(); // 存储值显示元素引用
    this.isInitialized = false;
    
    // 事件回调
    this.onSliderChange = null;
    this.onDefaultsSet = null;
  }

  /**
   * 初始化滑杆控制器
   */
  init() {
    try {
      this.setupSliders();
      this.loadDefaultValues();
      this.isInitialized = true;
      console.log('滑杆控制器初始化完成');
    } catch (error) {
      console.error('滑杆控制器初始化失败:', error);
      throw error;
    }
  }

  /**
   * 仅更新滑杆UI（数值与显示），不触发应用与消息
   */
  setSliderUIOnly(sliderId, value) {
    const slider = this.sliders.get(sliderId);
    if (slider) {
      slider.value = value;
      const cfg = this.config.sliderConfig.find(c => c.id === sliderId);
      const valueSpan = cfg ? this.valueDisplays.get(cfg.id) : null;
      if (valueSpan) valueSpan.textContent = String(value);
    }
  }

  /**
   * 批量仅更新滑杆UI
   */
  setMultipleUIOnly(map) {
    Object.entries(map || {}).forEach(([id, val]) => this.setSliderUIOnly(id, val));
  }

  /**
   * 设置所有滑杆
   */
  setupSliders() {
    this.config.sliderConfig.forEach(cfg => {
      this.setupSingleSlider(cfg);
    });
  }

  /**
   * 设置单个滑杆
   * @param {Object} sliderConfig - 滑杆配置
   */
  setupSingleSlider(sliderConfig) {
    const slider = document.getElementById(sliderConfig.id);
    const valueSpan = document.getElementById(sliderConfig.valueId);
    
    if (!slider) {
      console.warn(`找不到滑杆元素: ${sliderConfig.id}`);
      return;
    }
    
    if (!valueSpan) {
      console.warn(`找不到值显示元素: ${sliderConfig.valueId}`);
      return;
    }

    // 存储元素引用
    this.sliders.set(sliderConfig.id, slider);
    this.valueDisplays.set(sliderConfig.id, valueSpan);

    // Wire up Min/Max buttons (Range Calibration Mode)
    const wrapper = slider.closest('.slider-wrapper');
    if (wrapper) {
        const minBtn = wrapper.querySelector('.min-btn');
        const maxBtn = wrapper.querySelector('.max-btn');
        
        // Load saved range limits from storage
        const savedMin = this.styleController.get(`${sliderConfig.id}_min`);
        const savedMax = this.styleController.get(`${sliderConfig.id}_max`);
        
        if (savedMin !== null) slider.min = savedMin;
        if (savedMax !== null) slider.max = savedMax;

        if (minBtn) {
            minBtn.onclick = () => {
                const currentVal = parseFloat(slider.value);
                const currentMax = parseFloat(slider.max);
                
                if (currentVal >= currentMax) {
                    console.warn("Min cannot be >= Max");
                    return;
                }
                
                // Set new Min
                slider.min = currentVal;
                // Persistent Save
                this.styleController.set(`${sliderConfig.id}_min`, currentVal);
                console.log(`🔒 Range Updated: ${sliderConfig.id} Min set to ${currentVal}`);
                
                // Visual feedback (optional)
                minBtn.style.backgroundColor = '#90ee90';
                setTimeout(() => minBtn.style.backgroundColor = '', 500);
            };
        }
        if (maxBtn) {
             maxBtn.onclick = () => {
                const currentVal = parseFloat(slider.value);
                const currentMin = parseFloat(slider.min);

                if (currentVal <= currentMin) {
                    console.warn("Max cannot be <= Min");
                    return;
                }

                // Set new Max
                slider.max = currentVal;
                // Persistent Save
                this.styleController.set(`${sliderConfig.id}_max`, currentVal);
                console.log(`🔒 Range Updated: ${sliderConfig.id} Max set to ${currentVal}`);

                // Visual feedback
                maxBtn.style.backgroundColor = '#90ee90';
                setTimeout(() => maxBtn.style.backgroundColor = '', 500);
            };
        }
    }

    // 添加事件监听器
    slider.addEventListener('input', (event) => {
      this.handleSliderChange(sliderConfig, event.target.value);
    });

    console.log(`滑杆设置完成: ${sliderConfig.id}`);
  }

  /**
   * 处理滑杆变化
   * @param {Object} sliderConfig - 滑杆配置
   * @param {string} value - 滑杆值
   */
  handleSliderChange(sliderConfig, value) {
    try {
      // 更新显示值
      const valueSpan = this.valueDisplays.get(sliderConfig.id);
      if (valueSpan) {
        valueSpan.textContent = value + (sliderConfig.unit ? ' ' + sliderConfig.unit : '');
      }

      // 计算CSS值
      const cssValue = this.styleController.calculateCSSValue(sliderConfig, value);
      
      // Persist the value immediately
      if (sliderConfig.storage) {
          this.styleController.set(sliderConfig.storage, value);
      }
      
      console.log(`滑杆 ${sliderConfig.id} 变化: ${value}, CSS值: ${cssValue}`);

      // 应用样式
      let result;
      if (sliderConfig.type === 'updatePageMargin') {
        // 特殊处理页面边距
        result = this.handlePageMarginUpdate(sliderConfig, value);
      } else {
        // 普通CSS变量
        result = this.styleController.applyCSSVariable(sliderConfig.cssVar, cssValue);
      }

      // 发送消息到iframe（如果需要）
      if (this.messageHandler) {
        const messageData = {
          type: sliderConfig.type || 'updateCSS',
          variable: sliderConfig.cssVar,
          value: cssValue
        };
        this.messageHandler(messageData);
      }

      // 触发变化回调
      if (this.onSliderChange) {
        this.onSliderChange(sliderConfig, value, cssValue, result);
      }

    } catch (error) {
      console.error(`滑杆处理失败: ${sliderConfig.id}`, error);
    }
  }

  /**
   * 处理页面边距更新
   * @param {Object} sliderConfig - 滑杆配置
   * @param {string} value - 滑杆值
   * @returns {Object} - 处理结果
   */
  handlePageMarginUpdate(sliderConfig, value) {
    try {
      const mmValue = value + 'mm';
      
      // 发送特殊的页面边距消息
      if (this.messageHandler) {
        this.messageHandler({
          type: 'updatePageMargin',
          value: mmValue
        });
      }

      return {
        success: true,
        variable: sliderConfig.cssVar,
        value: mmValue,
        type: 'pageMargin'
      };

    } catch (error) {
      return {
        success: false,
        variable: sliderConfig.cssVar,
        value: value + 'mm',
        error: error.message
      };
    }
  }

  /**
   * 加载默认值并设置滑杆
   */
  loadDefaultValues() {
    this.config.sliderConfig.forEach(cfg => {
      const slider = this.sliders.get(cfg.id);
      if (slider) {
        const defaultValue = this.styleController.get(cfg.storage, 
          slider.defaultValue || slider.value || this.config.defaultStyles[cfg.storage]);
        
        slider.value = defaultValue;
        
        // 触发一次change事件以应用样式
        this.handleSliderChange(cfg, defaultValue);
      }
    });

    console.log('滑杆默认值加载完成');
  }

  /**
   * 触发所有滑杆的input事件（用于初始化）
   */
  triggerAllSliders() {
    this.config.sliderConfig.forEach(cfg => {
      const slider = this.sliders.get(cfg.id);
      if (slider) {
        slider.dispatchEvent(new Event('input'));
      }
    });
  }

  /**
   * 设置滑杆值
   * @param {string} sliderId - 滑杆ID
   * @param {string|number} value - 新值
   */
  setSliderValue(sliderId, value) {
    const slider = this.sliders.get(sliderId);
    if (slider) {
      slider.value = value;
      
      // 找到对应配置并触发变化处理
      const config = this.config.sliderConfig.find(cfg => cfg.id === sliderId);
      if (config) {
        this.handleSliderChange(config, value);
      }
    } else {
      console.warn(`滑杆不存在: ${sliderId}`);
    }
  }

  /**
   * 获取滑杆值
   * @param {string} sliderId - 滑杆ID
   * @returns {string|null} - 滑杆值
   */
  getSliderValue(sliderId) {
    const slider = this.sliders.get(sliderId);
    return slider ? slider.value : null;
  }

  /**
   * 获取所有滑杆值
   * @returns {Object} - 所有滑杆值对象
   */
  getAllSliderValues() {
    const values = {};
    this.sliders.forEach((slider, sliderId) => {
      values[sliderId] = slider.value;
    });
    return values;
  }

  /**
   * 设置所有滑杆为默认值
   */
  setAllToDefaults() {
    try {
      // 保存当前值为默认值
      this.styleController.setAllDefaults();

      // 发送所有CSS变量到iframe
      if (this.messageHandler) {
        this.config.sliderConfig.forEach(cfg => {
          const slider = this.sliders.get(cfg.id);
          if (slider) {
            const cssValue = this.styleController.calculateCSSValue(cfg, slider.value);
            
            const messageData = {
              type: cfg.type || 'updateCSS',
              variable: cfg.cssVar,
              value: cssValue
            };
            
            this.messageHandler(messageData);
          }
        });
      }

      // 触发回调
      if (this.onDefaultsSet) {
        this.onDefaultsSet();
      }

      console.log('所有滑杆默认值已设置');
      
    } catch (error) {
      console.error('设置默认值失败:', error);
    }
  }

  /**
   * 重置所有滑杆为默认值
   */
  resetAllToDefaults() {
    this.config.sliderConfig.forEach(cfg => {
      const defaultValue = this.config.defaultStyles[cfg.storage];
      this.setSliderValue(cfg.id, defaultValue);
    });
    
    console.log('所有滑杆已重置为默认值');
  }

  /**
   * 设置消息处理器（用于iframe通信）
   * @param {Function} messageHandler - 消息处理函数
   */
  setMessageHandler(messageHandler) {
    this.messageHandler = messageHandler;
  }

  /**
   * 设置事件回调
   * @param {Object} callbacks - 回调函数对象
   */
  setCallbacks(callbacks) {
    this.onSliderChange = callbacks.onSliderChange || null;
    this.onDefaultsSet = callbacks.onDefaultsSet || null;
  }

  /**
   * 导出滑杆配置
   * @returns {Object} - 滑杆配置对象
   */
  exportSliderConfig() {
    const config = {};
    
    this.config.sliderConfig.forEach(cfg => {
      const slider = this.sliders.get(cfg.id);
      if (slider) {
        config[cfg.id] = {
          value: slider.value,
          cssVar: cfg.cssVar,
          cssValue: this.styleController.calculateCSSValue(cfg, slider.value)
        };
      }
    });
    
    return config;
  }

  /**
   * 导入滑杆配置
   * @param {Object} sliderConfig - 滑杆配置对象
   */
  importSliderConfig(sliderConfig) {
    Object.entries(sliderConfig).forEach(([sliderId, config]) => {
      if (config.value !== undefined) {
        this.setSliderValue(sliderId, config.value);
      }
    });
    
    console.log('滑杆配置导入完成');
  }

  /**
   * 获取初始化状态
   * @returns {boolean} - 是否已初始化
   */
  isReady() {
    return this.isInitialized;
  }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SliderController;
} else {
  window.SliderController = SliderController;
}