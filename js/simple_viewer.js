/**
 * Simple Resume Viewer
 * Replaces Paged.js with native CSS printing and simple DOM logic.
 */
class SimpleResumeViewer {
  constructor() {
      this.config = window.ResumeConfig || {};
      this.contentContainer = null;
      this.hasUserInteracted = false;
      this.isAutoFitting = false;
      
      // Current state of style values (mirrors the sliders)
      this.currentStyleState = {}; 

      this.handleMessage = this.handleMessage.bind(this);
  }

  init() {
      console.log('🚀 Initializing Native CSS Viewer...');
      this.contentContainer = document.querySelector('#content'); // Should match HTML
      
      // 1. Apply Defaults immediately
      this.applyDefaults();

      window.addEventListener('message', this.handleMessage);
      
      // Notify parent
      if (window.parent) {
          window.parent.postMessage({ type: 'viewerReady' }, '*');
      }
  }

  applyDefaults() {
      if (!this.config.sliderConfig || !this.config.defaultStyles) return;
      
      console.log('Applying default styles from config...');
      const root = document.documentElement;
      const defaults = this.config.defaultStyles;

      this.config.sliderConfig.forEach(slider => {
          let val = null;
          
          // Try to find value in defaultStyles
          // 1. Check exact storage key match (e.g. 'defaultFontSize')
          if (defaults[slider.storage] !== undefined) {
              val = defaults[slider.storage];
          } 
          // 2. Check derived key (e.g. 'defaultFontSize' -> 'fontSize')
          else if (slider.storage && slider.storage.startsWith('default')) {
              const derivedKey = slider.storage.replace('default', '');
              const key = derivedKey.charAt(0).toLowerCase() + derivedKey.slice(1);
              if (defaults[key] !== undefined) {
                  val = defaults[key];
              }
          }

          // If found, apply it
          if (val !== null) {
              let cssValue = val;
              // Add unit if needed (and not '倍' which is unitless in CSS usually, or handled as number)
              if (slider.unit && slider.unit !== '倍' && typeof val === 'number') {
                  cssValue = val + slider.unit;
              }
              
              root.style.setProperty(slider.cssVar, cssValue);
              this.currentStyleState[slider.cssVar] = val;
          }
      });
  }

  handleMessage(event) {
      const data = event.data;
      const { type, payload, variable, value } = data;
      
      // console.log('SimpleViewer received:', type, data);

      switch (type) {
          case 'SET_CONTENT':
          case 'updateContent': // Support legacy message type from controller
              // Handle both direct string payload and object with markdown property
              const content = (typeof payload === 'object' && payload.markdown) ? payload.markdown : (payload || data.content);
              this.renderContent(content);
              break;

          case 'UPDATE_STYLES':
          case 'updateStyles':
              this.updateStyles(payload, true);
              break;
              
          // Legacy format from SliderController
          case 'updateCSS':
              if (variable && value !== undefined) {
                  this.updateStyles({ [variable]: value }, true);
              }
              break;
              
          // Legacy format for margins
          case 'updatePageMargin':
              const marginValue = data.margin || data.value;
              if (marginValue !== undefined) {
                  this.updateStyles({ '--page-margin': marginValue }, true);
              }
              break;
              
          case 'print':
              window.print();
              break;
      }
  }

  async renderContent(markdown) {
      if (!this.contentContainer) this.contentContainer = document.querySelector('#content');

      if (!window.markdownit) {
          console.error('Markdown-it not loaded!');
          if (window.marked) {
              console.warn('Falling back to marked.js');
              this.contentContainer.innerHTML = window.marked.parse(markdown);
          }
          return;
      }
      const md = window.markdownit({ html: true });
      this.contentContainer.innerHTML = md.render(markdown);
      console.log('📝 Content rendered');

      // Update Visual Helpers (Page Count & Red Lines)
      this.updatePageHelpers();

      // Signal render complete for MCP/automation
      document.body.classList.add('render-complete');
      
      // Trigger Auto-Fit if allowed
      // Ensure we haven't interacted yet
      // CHANGED: We now trigger on logic unless strictly forbidden to ensure MCP works
      if (!this.hasUserInteracted) {
          console.log('⚡ Triggering Auto-Fit on Content Load...');
          // Small delay to allow DOM to settle
          setTimeout(() => this.fitToOnePage(), 300);
      }
  }

  updateStyles(styles, isUserAction = false) {
      // If user manually adjusts, we lock auto-fit
      if (isUserAction && !this.isAutoFitting) {
        if (!this.hasUserInteracted) {
            console.log('🔒 Auto-fit locked due to user interaction.');
        }
        this.hasUserInteracted = true;
      }

      const root = document.documentElement;
      Object.entries(styles).forEach(([key, value]) => {
          // Update CSS variable
          // Handle potential raw numbers that need units, though controller usually sends units
          root.style.setProperty(key, value);
          // Cache it
          this.currentStyleState[key] = value;
      });
      
      // Update visual helpers unless we are in the middle of auto-fitting (to avoid layout thrashing/false size readings)
      if (!this.isAutoFitting) {
          this.updatePageHelpers();
      }
  }

  updatePageHelpers() {
      const page = this.contentContainer;
      if (!page) return;

      // Clean up old lines
      page.querySelectorAll('.page-break-line').forEach(el => el.remove());

      const A4_MM = 297;
      // 1mm ~ 3.7795px
      const MM_TO_PX = 3.779527559; 
      const A4_HEIGHT_PX = A4_MM * MM_TO_PX;

      const totalHeightPx = page.scrollHeight;
      const pageCount = Math.ceil(totalHeightPx / Math.floor(A4_HEIGHT_PX - 2)); // slight tolerance

      // Update Indicator
      const indicator = document.getElementById('page-count-indicator');
      if (indicator) {
          indicator.textContent = `共 ${pageCount} 页`;
          // Optional: Change color if > 1 page?
          indicator.style.background = pageCount > 1 ? 'rgba(233, 30, 99, 0.9)' : 'rgba(33, 150, 243, 0.9)';
      }

      // Inject Break Lines
      // We start at 1 * A4, 2 * A4, etc.
      for (let i = 1; i < pageCount; i++) {
          const topMm = i * A4_MM;
          const line = document.createElement('div');
          line.className = 'page-break-line';
          line.style.top = `${topMm}mm`;
          line.innerHTML = `<span class="page-break-label">第 ${i} 页结束 / 第 ${i+1} 页开始</span>`;
          page.appendChild(line);
      }
      
      // Also inject a line at the very end of the LAST page if it's visually helpful?
      // No, usually we only want to see where the breaks are.
      // But user asked for "where the red line is".
      // Let's add one at exactly 297mm always if height > 297mm, or even if close?
      // The loop above handles i=1 (297mm) if pageCount > 1.
      // If pageCount is 1, maybe they still want to see the boundary?
      if (pageCount === 1) {
           // Check if we are close to the edge? 
           // Or just always show the 297mm boundary so they know how much space fits?
           // The user said "One Page Red Line".
           // I will draw the first page boundary always, even if content is short.
           const line = document.createElement('div');
           line.className = 'page-break-line';
           line.style.top = '297mm';
           line.innerHTML = `<span class="page-break-label">A4 底部边界</span>`;
           page.appendChild(line);
      }
  }

  /**
   * Bidirectional Auto-Fit Logic
   * - If content > 1 page: shrink parameters to fit
   * - If content << 1 page: expand parameters to fill (better readability)
   * Checks scrollHeight against A4 height (approx 1120px at 96dpi)
   */
  async fitToOnePage() {
      if (this.hasUserInteracted) {
          console.log('🔒 Auto-fit skipped: User has manually adjusted styles.');
          return;
      }

      this.isAutoFitting = true;
      console.log('📐 Starting Bidirectional Auto-Fit...');
      
      // Initialize result object attached to window for external checking
      window.autoFitResult = { 
        attempted: true, 
        success: false, 
        direction: 'none',
        limitsHit: false,
        iterations: 0
      };

      // Remove visual helpers to ensure accurate height measurement
      if (this.contentContainer) {
          this.contentContainer.querySelectorAll('.page-break-line').forEach(el => el.remove());
      }

      const page = document.querySelector('.page');
      if (!page) {
          console.error('❌ No .page element found');
          this.isAutoFitting = false;
          return;
      }

      const A4_HEIGHT_PX = 1120; // Slightly less than 1123px (297mm @ 96dpi)
      const TOLERANCE = 5; // px tolerance to avoid infinite loops
      const EXPAND_THRESHOLD = 50; // Only expand if > 50px spare room
      
      // Strategy definitions with min/max bounds
      // Order: For shrink - low-impact first; For expand - readability first
      const shrinkStrategies = [
          { name: 'pageMargin', cssVar: '--page-margin', id: 'marginSlider', step: 1.0, unit: 'mm' },
          { name: 'bodyMargin', cssVar: '--body-margin', id: 'bodyMarginSlider', step: 0.1, unit: 'em' },
          { name: 'ulMargin', cssVar: '--ul-margin', id: 'ulMarginSlider', step: 0.1, unit: 'em' },
          { name: 'headingScale', cssVar: '--heading-scale', id: 'headingSlider', step: 0.1, unit: '' },
          { name: 'lineHeight', cssVar: '--line-height', id: 'lineHeightSlider', step: 0.05, unit: '' },
          { name: 'fontSize', cssVar: '--body-font-size', id: 'fontSlider', step: 0.5, unit: 'pt' }
      ];
      
      // For expand: prioritize readability (fontSize, lineHeight first)
      const expandStrategies = [
          { name: 'fontSize', cssVar: '--body-font-size', id: 'fontSlider', step: 0.5, unit: 'pt' },
          { name: 'lineHeight', cssVar: '--line-height', id: 'lineHeightSlider', step: 0.05, unit: '' },
          { name: 'headingScale', cssVar: '--heading-scale', id: 'headingSlider', step: 0.1, unit: '' },
          { name: 'bodyMargin', cssVar: '--body-margin', id: 'bodyMarginSlider', step: 0.1, unit: 'em' },
          { name: 'ulMargin', cssVar: '--ul-margin', id: 'ulMarginSlider', step: 0.1, unit: 'em' },
          { name: 'pageMargin', cssVar: '--page-margin', id: 'marginSlider', step: 1.0, unit: 'mm' }
      ];

      const maxIterations = 25;
      let iteration = 0;
      
      // Determine direction
      let currentHeight = page.scrollHeight;
      let direction = 'none';
      
      if (currentHeight > A4_HEIGHT_PX + TOLERANCE) {
          direction = 'shrink';
      } else if (currentHeight < A4_HEIGHT_PX - EXPAND_THRESHOLD) {
          direction = 'expand';
      }
      
      window.autoFitResult.direction = direction;
      console.log(`📐 Direction: ${direction} (height=${currentHeight}px, target=${A4_HEIGHT_PX}px)`);

      // Helper: Get limit (min or max) for a parameter
      const getLimit = (strat, isMax) => {
          const sliderCfg = this.config.sliderConfig?.find(s => s.id === strat.id);
          let limit = isMax ? (sliderCfg?.max || 999) : (sliderCfg?.min || 0);
          
          // Check localStorage override
          const storageKey = `${strat.id}_${isMax ? 'max' : 'min'}`;
          const stored = localStorage.getItem(storageKey);
          if (stored !== null) {
              const parsed = parseFloat(stored);
              if (!isNaN(parsed)) limit = parsed;
          }
          return limit;
      };

      // Helper: Get current value
      const getCurrentValue = (cssVar) => {
          const val = getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
          return parseFloat(val);
      };

      // SHRINK LOOP
      if (direction === 'shrink') {
          while (page.scrollHeight > A4_HEIGHT_PX && iteration < maxIterations) {
              let adjusted = false;

              for (const strat of shrinkStrategies) {
                  if (adjusted) break;
                  
                  const currentVal = getCurrentValue(strat.cssVar);
                  if (isNaN(currentVal)) continue;
                  
                  const limitMin = getLimit(strat, false);
                  
                  if (currentVal > limitMin + 0.001) {
                      let newVal = Math.max(limitMin, currentVal - strat.step);
                      newVal = Math.round(newVal * 100) / 100;
                      
                      this.updateStyles({ [strat.cssVar]: newVal + strat.unit }, false);
                      this.syncSliderToParent(strat.cssVar, newVal);
                      adjusted = true;
                  }
              }
              
              if (!adjusted) {
                  console.log('⚠️ Shrink hit all minimum limits.');
                  window.autoFitResult.limitsHit = true;
                  break;
              }
              
              await new Promise(r => setTimeout(r, 30));
              iteration++;
          }
      }
      
      // EXPAND LOOP
      if (direction === 'expand') {
          // Store initial values for potential rollback
          const initialValues = {};
          for (const strat of expandStrategies) {
              initialValues[strat.cssVar] = getCurrentValue(strat.cssVar);
          }
          
          while (page.scrollHeight < A4_HEIGHT_PX - 10 && iteration < maxIterations) {
              let adjusted = false;
              let lastAdjusted = null;

              for (const strat of expandStrategies) {
                  if (adjusted) break;
                  
                  const currentVal = getCurrentValue(strat.cssVar);
                  if (isNaN(currentVal)) continue;
                  
                  const limitMax = getLimit(strat, true);
                  
                  if (currentVal < limitMax - 0.001) {
                      let newVal = Math.min(limitMax, currentVal + strat.step);
                      newVal = Math.round(newVal * 100) / 100;
                      
                      this.updateStyles({ [strat.cssVar]: newVal + strat.unit }, false);
                      this.syncSliderToParent(strat.cssVar, newVal);
                      lastAdjusted = { strat, prevVal: currentVal };
                      adjusted = true;
                  }
              }
              
              if (!adjusted) {
                  console.log('⚠️ Expand hit all maximum limits.');
                  window.autoFitResult.limitsHit = true;
                  break;
              }
              
              await new Promise(r => setTimeout(r, 30));
              iteration++;
              
              // Safety check: If we overflowed, rollback last change and stop
              if (page.scrollHeight > A4_HEIGHT_PX && lastAdjusted) {
                  console.log('⚠️ Expand caused overflow, rolling back...');
                  const { strat, prevVal } = lastAdjusted;
                  this.updateStyles({ [strat.cssVar]: prevVal + strat.unit }, false);
                  this.syncSliderToParent(strat.cssVar, prevVal);
                  break;
              }
          }
      }
      
      window.autoFitResult.iterations = iteration;
      window.autoFitResult.finalHeight = page.scrollHeight;
      
      if (page.scrollHeight <= A4_HEIGHT_PX + TOLERANCE && page.scrollHeight > 0) {
           window.autoFitResult.success = true;
           console.log(`✅ Auto-Fit success (${direction}, ${iteration} iterations, final=${page.scrollHeight}px)`);
      } else {
           console.log(`❌ Auto-Fit incomplete (${direction}, final=${page.scrollHeight}px)`);
      }

      this.isAutoFitting = false;
      this.updatePageHelpers();
      
      // Signal auto-fit complete for MCP/automation
      document.body.classList.add('autofit-complete');
  }

  // --- External Control for MCP ---
  // Allow forceful triggering even if user has interacted, 
  // or trigger from init if needed (though init usually reserves for defaults)
  forceAutoFit() {
      this.hasUserInteracted = false; // Reset lock
      return this.fitToOnePage();
  }

  syncSliderToParent(cssVar, value) {
      if (window.parent && this.config.sliderConfig) {
          const slider = this.config.sliderConfig.find(s => s.cssVar === cssVar);
          if (!slider) return;
          
          // Reverse calculation for scale if needed
          let rawValue = value;
          if (slider.scale) {
              rawValue = rawValue / slider.scale;
          }

          window.parent.postMessage({
              type: 'autoOnePageSync',
              sliders: {
                  [slider.id]: rawValue
              }
          }, '*');
      }
  }
}

// Initialize
window.simpleViewer = new SimpleResumeViewer();
window.onload = () => window.simpleViewer.init();
