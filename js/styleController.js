// StyleController - manages CSS variables through the shared state manager
class StyleController {
  constructor(config) {
    this.config = config;
    this.currentStyles = {};
    this.defaultStyles = config.defaultStyles;
    this.isStateManaged = false;
    this.pendingOperations = [];
    this.readyPromise = this.init();
  }

  /**
   * Initialise controller and wait for the state manager
   */
  async init() {
    await this.waitForStateManager();
    this.isStateManaged = true;
    console.log('[StyleController] connected to shared ResumeState');
    this.flushPendingOperations();
  }

  /**
   * Wait for ResumeState to be available (no timeout)
   */
  waitForStateManager() {
    if (typeof window === 'undefined') {
      return Promise.reject(new Error('StyleController requires a browser environment'));
    }

    if (typeof window.ResumeState !== 'undefined') {
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      let lastLogMark = -1;
      const check = () => {
        if (typeof window.ResumeState !== 'undefined') {
          resolve();
          return;
        }

        const mark = Math.floor(performance.now() / 500);
        if (mark !== lastLogMark) {
          console.log('[StyleController] waiting for ResumeState...');
          lastLogMark = mark;
        }

        setTimeout(check, 100);
      };

      check();
    });
  }

  /**
   * Queue an operation until ResumeState is ready
   */
  queueOperation(description, fn) {
    console.warn(`[StyleController] ResumeState not ready, queue operation: ${description}`);
    this.pendingOperations.push(fn);
  }

  /**
   * Run queued operations once ResumeState is ready
   */
  flushPendingOperations() {
    if (!this.isStateManaged) return;

    while (this.pendingOperations.length > 0) {
      const operation = this.pendingOperations.shift();
      try {
        operation();
      } catch (error) {
        console.error('[StyleController] queued operation failed:', error);
      }
    }
  }

  /**
   * Helpers for reading/writing persisted slider values
   */
  get(key, fallback) {
    return localStorage.getItem(key) || fallback;
  }

  set(key, value) {
    localStorage.setItem(key, value);
  }

  getAllDefaults() {
    const defaults = {};
    this.config.sliderConfig.forEach(cfg => {
      const element = document.getElementById(cfg.id);
      const defaultValue = element ? (element.defaultValue || element.value) : this.defaultStyles[cfg.id];
      defaults[cfg.id] = this.get(cfg.storage, defaultValue);
    });
    return defaults;
  }

  setAllDefaults() {
    this.config.sliderConfig.forEach(cfg => {
      const element = document.getElementById(cfg.id);
      if (element) {
        this.set(cfg.storage, element.value);
      }
    });
    console.log('[StyleController] current styles saved as defaults');
  }

  /**
   * Apply a single CSS variable through the state manager
   */
  applyCSSVariable(variable, value) {
    if (!this.isStateManaged) {
      this.queueOperation(`apply ${variable}`, () => this.applyCSSVariable(variable, value));
      return { success: false, pending: true, variable, value };
    }

    window.ResumeState.dispatch({
      type: 'SET_STYLES',
      payload: {
        [variable]: value,
        source: 'styleController'
      }
    });

    this.currentStyles[variable] = value;

    return {
      success: true,
      variable,
      value,
      method: 'state-managed'
    };
  }

  /**
   * Apply multiple CSS variables
   */
  applyMultipleStyles(styles) {
    if (!this.isStateManaged) {
      this.queueOperation('apply multiple styles', () => this.applyMultipleStyles(styles));
      return [];
    }

    const results = [];
    Object.entries(styles).forEach(([variable, value]) => {
      window.ResumeState.dispatch({
        type: 'SET_STYLES',
        payload: {
          [variable]: value,
          source: 'styleController'
        }
      });
      this.currentStyles[variable] = value;
      results.push({ success: true, variable, value, method: 'state-managed' });
    });

    return results;
  }

  /**
   * Utility: convert slider value to CSS value
   */
  calculateCSSValue(sliderConfig, rawValue) {
    let cssValue = rawValue;

    if (sliderConfig.scale) {
      cssValue = rawValue * sliderConfig.scale;
    }

    // Only append standard CSS units that are intended to be part of the value.
    // We explicitly exclude '倍' (UI only) and 'em' (used as scalar in calc()).
    // 'mm', 'pt', 'px', '%' are appeneded.
    const scalarUnits = ['倍', 'em'];
    if (sliderConfig.unit && !scalarUnits.includes(sliderConfig.unit)) {
      cssValue = `${cssValue}${sliderConfig.unit}`;
    }

    return cssValue;
  }

  applyStyleFromSlider(sliderConfig, value) {
    const cssValue = this.calculateCSSValue(sliderConfig, value);
    return this.applyCSSVariable(sliderConfig.cssVar, cssValue);
  }

  /**
   * Initialise default styles on first load
   */
  initializeDefaultStyles() {
    const defaults = this.getAllDefaults();
    const stylesToApply = {};

    this.config.sliderConfig.forEach(cfg => {
      const rawValue = defaults[cfg.id] || this.defaultStyles[cfg.storage];
      stylesToApply[cfg.cssVar] = this.calculateCSSValue(cfg, rawValue);
    });

    this.applyMultipleStyles(stylesToApply);
    console.log('[StyleController] default styles applied');
  }

  /**
   * Reset styles to defaults
   */
  resetToDefaults() {
    const stylesToApply = {};

    this.config.sliderConfig.forEach(cfg => {
      const defaultValue = this.defaultStyles[cfg.storage];
      stylesToApply[cfg.cssVar] = this.calculateCSSValue(cfg, defaultValue);

      const element = document.getElementById(cfg.id);
      if (element) {
        element.value = defaultValue;
      }
    });

    this.applyMultipleStyles(stylesToApply);
    console.log('[StyleController] styles reset to defaults');
  }

  /**
   * Expose helpers for exporting/importing styles
   */
  getCurrentStyles() {
    return { ...this.currentStyles };
  }

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
    console.log('[StyleController] style configuration imported');
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = StyleController;
} else {
  window.StyleController = StyleController;
}