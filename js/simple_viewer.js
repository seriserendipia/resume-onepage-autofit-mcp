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
      window.addEventListener('message', this.handleMessage);
      
      // Notify parent
      if (window.parent) {
          window.parent.postMessage({ type: 'viewerReady' }, '*');
      }
  }

  handleMessage(event) {
      const data = event.data;
      const { type, payload, variable, value } = data;
      
      console.log('SimpleViewer received:', type, data);

      switch (type) {
          case 'SET_CONTENT':
              this.renderContent(payload);
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
      if (this.config.autoFit?.runOnFirstLoad && !this.hasUserInteracted) {
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
   * Simplified Auto-Fit Logic
   * Checks scrollHeight against A4 height (approx 1120px at 96dpi)
   */
  async fitToOnePage() {
      if (this.hasUserInteracted) {
          console.log('🔒 Auto-fit skipped: User has manually adjusted styles.');
          return;
      }

      this.isAutoFitting = true;
      console.log('📐 Starting Auto-Fit with LocalStorage Limits...');
      
      // Remove visual helpers to ensure accurate height measurement
      if (this.contentContainer) {
          this.contentContainer.querySelectorAll('.page-break-line').forEach(el => el.remove());
      }

      const page = document.querySelector('.page');
      const A4_HEIGHT_PX = 1120; // Slightly less than 1123px (297mm @ 96dpi)
      
      // Define the strategy: What to shrink and in what order?
      // We map strategies directly to slider IDs to easily lookup Min values.
      const strategies = [
          { name: 'pageMargin', cssVar: '--page-margin', id: 'marginSlider', step: 1.0, unit: 'mm' },
          { name: 'bodyMargin', cssVar: '--body-margin', id: 'bodyMarginSlider', step: 0.1, unit: 'em' },
          { name: 'ulMargin', cssVar: '--ul-margin', id: 'ulMarginSlider', step: 0.1, unit: 'em' },
          { name: 'headingScale', cssVar: '--heading-scale', id: 'headingSlider', step: 0.1, unit: '' },
          { name: 'lineHeight', cssVar: '--line-height', id: 'lineHeightSlider', step: 0.05, unit: '' },
          { name: 'fontSize', cssVar: '--body-font-size', id: 'fontSlider', step: 0.5, unit: 'pt' }
      ];

      const maxIterations = 20;
      let iteration = 0;

      while (page.scrollHeight > A4_HEIGHT_PX && iteration < maxIterations) {
          console.log(`[AutoFit] Iteration ${iteration}: ${page.scrollHeight}px > ${A4_HEIGHT_PX}px`);
          let reducedSomething = false;

          for (const strat of strategies) {
              if (reducedSomething) break; 

              // 1. Get current value
              const styleVal = getComputedStyle(document.documentElement).getPropertyValue(strat.cssVar).trim();
              let currentVal = parseFloat(styleVal);
              if (isNaN(currentVal)) continue;

              // 2. Determine the HARD LIMIT (Minimum)
              // Priority: User LocalStorage Limit > Config Default (Fallback)
              let limitMin = 0;
              
              // Fallback: Get static default min from config
              const sliderCfg = this.config.sliderConfig.find(s => s.id === strat.id);
              if (sliderCfg) {
                  limitMin = sliderCfg.min; 
              }
              
              // Override: If user has explicitly calibrated the Min limit, use that directly.
              // No "Math.max" check - trust the user's intent completely.
              const storedMin = localStorage.getItem(`${strat.id}_min`);
              if (storedMin !== null) {
                  const userMin = parseFloat(storedMin);
                  if (!isNaN(userMin)) {
                      limitMin = userMin; 
                  }
              }

              // 3. Attempt reduction
              if (currentVal > limitMin + 0.001) { // Float tolerance
                   let newVal = Math.max(limitMin, currentVal - strat.step);
                   
                   // Round to avoid float precision errors (e.g. 15.000000002)
                   newVal = Math.round(newVal * 100) / 100;

                   let valStr = newVal + strat.unit;
                   
                   // Apply
                   this.updateStyles({ [strat.cssVar]: valStr }, false);
                   this.syncSliderToParent(strat.cssVar, newVal);
                   
                   console.log(`🔻 Reduced ${strat.name} to ${valStr} (Limit: ${limitMin})`);
                   reducedSomething = true;
              } else {
                  console.log(`🛑 Cannot reduce ${strat.name} further. Current: ${currentVal}, Limit: ${limitMin}`);
              }
          }
          
          if (!reducedSomething) {
              console.log('⚠️ Algorithm hit all minimum limits. Cannot fit one page.');
              break;
          }
          
          await new Promise(r => setTimeout(r, 50));
          iteration++;
      }
      
      console.log('✅ Auto-Fit complete.');
      this.isAutoFitting = false;
      this.updatePageHelpers();
      
      // Signal auto-fit complete for MCP/automation
      document.body.classList.add('autofit-complete');
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
