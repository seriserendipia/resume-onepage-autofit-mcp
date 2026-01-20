// Paged.js Resume Renderer with Race Condition Protection & Handshake Protocol

// Configuration
const CONFIG = {
    pollingInterval: 200, // ms for handshake
    pagedOptions: {
        auto: false, // Manual trigger
    }
};

// State
let state = {
    originalBody: "",
    originalHead: "",
    isRendering: false,
    pendingRenderRequest: null,
    handshakeInterval: null,
    isHandshakeComplete: false,
    currentStyles: {}, // Cache current styles
    contentLoaded: false
};

// Apply default styles from ResumeConfig (for MCP rendering)
function applyDefaultStyles() {
    if (!window.ResumeConfig || !window.ResumeConfig.defaultStyles) return;
    const defaults = window.ResumeConfig.defaultStyles;
    const styles = {
        '--body-font-size': `${defaults.fontSize}pt`,
        '--heading-scale': `${defaults.headingScale}`,
        '--line-height': `${defaults.lineHeight}`,
        '--page-margin': `${defaults.margin}mm`,
        '--title-hr-margin': `${defaults.titleHrMargin}em`,
        '--body-margin': `${defaults.bodyMargin}em`,
        '--ul-margin': `${defaults.ulMargin}em`,
        '--strong-paragraph-margin': `${defaults.strongParagraphMargin}em`
    };
    handleStyleUpdate(styles);
}

// Paged.js Instance
// Ensure Paged is available
const getPaged = () => {
    return window.Paged || window.PagedPolyfill;
};

function ensureA4PageRule() {
    const STYLE_ID = 'forced-page-a4';
    let styleEl = document.getElementById(STYLE_ID);
    if (!styleEl) {
        styleEl = document.createElement('style');
        styleEl.id = STYLE_ID;
        document.head.appendChild(styleEl);
    }
    // Paged.js ships with a default "@page { size: letter; margin: 0 }".
    // Injecting this rule last ensures A4 is used consistently.
    // Use computed --page-margin value (Paged.js doesn't re-evaluate CSS variables)
    const computedMargin = getComputedStyle(document.documentElement).getPropertyValue('--page-margin').trim() || '7mm';
    styleEl.textContent = `@page { size: A4; margin: ${computedMargin}; }`;
    console.log(`[ensureA4PageRule] Set @page margin to: ${computedMargin}`);
    
    // Debug: Verify the rule is in the stylesheet
    setTimeout(() => {
        try {
            for (const sheet of Array.from(document.styleSheets || [])) {
                if (sheet.ownerNode === styleEl) {
                    const rules = sheet.cssRules;
                    if (rules && rules.length > 0) {
                        console.log(`[ensureA4PageRule] Verified rule: ${rules[0].cssText}`);
                    }
                }
            }
        } catch (e) {
            console.log('[ensureA4PageRule] Could not verify rule:', e.message);
        }
    }, 0);
}

// Initialization
window.addEventListener('load', () => {
    console.log('🚀 Resume Renderer Loaded');
    
    // Capture initial "skeleton" state (before content)
    // We might update this after content load
    state.originalBody = document.body.innerHTML;
    state.originalHead = document.head.innerHTML;
    
    // Mark ready for external tools
    window.isRendererReady = true;

    // Apply defaults before any content render
    applyDefaultStyles();

    startHandshake();
});

// Handshake Protocol
function startHandshake() {
    state.handshakeInterval = setInterval(() => {
        if (window.parent) {
            window.parent.postMessage({ type: 'READY' }, '*');
            // Also send viewerReady for backward compatibility if needed, 
            // but the new controller logic should handle READY
        }
    }, CONFIG.pollingInterval);
}

// Message Handler
window.addEventListener('message', async (event) => {
    const { type, payload, variable, value, content } = event.data;
    
    console.log(`[Renderer] Received message: ${type}`);

    // 1. Handshake ACK
    if (type === 'ACK') {
        if (state.handshakeInterval) {
            clearInterval(state.handshakeInterval);
            state.handshakeInterval = null;
        }
        state.isHandshakeComplete = true;
        console.log('✅ Handshake Complete');
        return;
    }

    // 2. Content Update
    if (type === 'updateContent' || type === 'SET_CONTENT') {
        const mdContent = content || (payload && payload.markdown) || payload;
        await handleContentUpdate(mdContent);
        return;
    }

    // 3. Style Updates (Live Preview - Lightweight)
    if (type === 'UPDATE_CSS_VAR' || type === 'updateCSS' || type === 'updateStyles') {
        // Normalizing payload
        let styles = {};
        if (type === 'UPDATE_CSS_VAR' || type === 'updateStyles') {
            styles = payload || {};
        } else if (variable) {
            styles[variable] = value;
        }
        
        handleStyleUpdate(styles);
        return;
    }

    // 3b. Legacy: Page Margin Update
    if (type === 'updatePageMargin') {
        const marginValue = payload?.margin || value;
        if (marginValue) {
             handleStyleUpdate({ '--page-margin': marginValue });
        }
        return;
    }

    // 4. Trigger Paged Render (Heavyweight)
    if (type === 'TRIGGER_PAGED' || type === 'renderPaged') {
        handlePagedRender(payload); // payload might contain latest styles
        return;
    }

    // 5. Print
    if (type === 'print') {
        window.print();
        return;
    }
});

// Logic: Content Update
async function handleContentUpdate(markdown) {
    console.log('[Renderer] 📝 Handle Content Update Triggered');
    
    // Check for Markdown library
    if (!window.markdownit) {
        console.error('[Renderer] ❌ Markdown-it not loaded!');
        document.body.innerHTML = "<h1>Error: Markdown library not found</h1>";
        return;
    }

    console.log('[Renderer] Rendering Markdown...');
    // Render Markdown
    const md = window.markdownit({ html: true });
    const html = md.render(markdown);

    // Apply to DOM (Clean Slate)
    const contentDiv = document.getElementById('content');
    if (contentDiv) {
        contentDiv.innerHTML = html;
        console.log('[Renderer] DOM updated with HTML');
        
        // Update snapshot
        state.originalBody = document.body.innerHTML;
        state.contentLoaded = true;
        
        // Initial Render
        console.log('[Renderer] Triggering Initial Paged Render...');
        await handlePagedRender();
    } else {
        console.error("[Renderer] No #content div found");
    }
}


// Logic: Style Update (Live)
function handleStyleUpdate(styles) {
    const root = document.documentElement;
    Object.entries(styles).forEach(([key, val]) => {
        // Store in cache
        state.currentStyles[key] = val;
        // Apply to DOM
        root.style.setProperty(key, val);
    });
}

function logLayoutMetrics(stage) {
    try {
        const getRect = (el) => {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
        };

        const root = document.documentElement;
        const content = document.getElementById('content');
        const pagedPage = document.querySelector('.pagedjs_page');
        const pagedBox = document.querySelector('.pagedjs_pagebox');

        // Try to extract @page rule text if present
        const pageRules = [];
        for (const sheet of Array.from(document.styleSheets || [])) {
            let rules;
            try {
                rules = sheet.cssRules;
            } catch {
                continue;
            }
            for (const rule of Array.from(rules || [])) {
                // 6 is CSSRule.PAGE_RULE in most browsers
                if (rule && rule.type === 6) {
                    pageRules.push(rule.cssText);
                }
            }
        }

        const payload = {
            stage,
            viewport: { w: window.innerWidth, h: window.innerHeight, dpr: window.devicePixelRatio },
            cssVars: {
                pageMargin: getComputedStyle(root).getPropertyValue('--page-margin').trim(),
                fontSize: getComputedStyle(root).getPropertyValue('--body-font-size').trim(),
                lineHeight: getComputedStyle(root).getPropertyValue('--line-height').trim(),
                headingScale: getComputedStyle(root).getPropertyValue('--heading-scale').trim()
            },
            body: {
                margin: getComputedStyle(document.body).margin,
                padding: getComputedStyle(document.body).padding
            },
            pagedBoxStyle: pagedBox ? {
                margin: getComputedStyle(pagedBox).margin,
                padding: getComputedStyle(pagedBox).padding
            } : null,
            contentRect: getRect(content),
            pagedPageRect: getRect(pagedPage),
            pagedBoxRect: getRect(pagedBox),
            pageRules
        };

        // Console logging (useful for Playwright runs)
        console.log('[Renderer][Layout]', payload);
    } catch (e) {
        console.log('[Renderer][Layout] logging failed', String(e));
    }
}

// Logic: Paged Render (Heavy)
async function handlePagedRender(extraStyles = {}) {
    console.log('[Renderer] handlePagedRender called');
    // Merge extra styles
    Object.assign(state.currentStyles, extraStyles);

    // Race Condition Protection
    if (state.isRendering) {
        console.log('[Renderer] Render locked, queuing request');
        state.pendingRenderRequest = { ...state.currentStyles };
        return;
    }

    state.isRendering = true;
    
    // Notify Parent (optional, for locking UI)
    window.parent.postMessage({ type: 'rendering' }, '*');

    try {
        console.log('[Renderer] 🎨 Starting Paged.js Render Execution...');
        
        // 1. Restore Clean DOM (Content + No Paged artifacts)
        // Check if we have original content
        if (state.originalBody) {
             document.body.innerHTML = state.originalBody;
        }
        if (state.originalHead) {
            document.head.innerHTML = state.originalHead;
        }

        // 2. Re-apply Styles
        handleStyleUpdate(state.currentStyles);

        // Ensure A4 page size overrides Paged.js default (letter)
        ensureA4PageRule();

        logLayoutMetrics('before_paged_preview');

        // 3. Initialize Paged
        const Paged = getPaged();
        if (Paged) {
            const previewer = new Paged.Previewer();
            console.log('[Renderer] Invoking previewer.preview()...');
            await previewer.preview();
            console.log('[Renderer] ✨ Paged.js preview() returned');
        } else {
            console.error("[Renderer] Paged.js not found");
        }

        logLayoutMetrics('after_paged_preview');

        // Add class for external detection (e.g. Playwright)
        document.body.classList.add('render-complete');
        console.log('[Renderer] Added .render-complete class');

        logLayoutMetrics('render_complete');

        window.parent.postMessage({ type: 'rendered' }, '*');
        window.parent.postMessage({ type: 'RENDER_COMPLETE' }, '*');

    } catch (e) {
        console.error("[Renderer] Rendering failed", e);
        // Fallback: Restore Clean DOM
        document.body.innerHTML = state.originalBody;
        document.head.innerHTML = state.originalHead;
    } finally {
        state.isRendering = false;
        
        // Process Pending
        if (state.pendingRenderRequest) {
            const nextStyles = state.pendingRenderRequest;
            state.pendingRenderRequest = null;
            handlePagedRender(nextStyles);
        }
    }
}

// --- Extended Functionality: Bidirectional Auto-Fit for MCP ---
window.simpleViewer = {
    isAutoFitting: false,

    checkContentFill: function() {
        const pageContent = document.querySelector('.pagedjs_page_content');
        if (!pageContent) return { isSparse: false, ratio: 1.0 };
        const pageBox = document.querySelector('.pagedjs_pagebox');
        if (!pageBox) return { isSparse: false, ratio: 1.0 };
        
        // 寻找内容中最后一个可见元素，以更好地估算实际内容高度
        const children = Array.from(pageContent.querySelectorAll('*'));
        let actualContentHeight = pageContent.scrollHeight;
        if (children.length > 0) {
            const lastChild = children[children.length - 1];
            const contentTop = pageContent.getBoundingClientRect().top;
            const lastBottom = lastChild.getBoundingClientRect().bottom;
            actualContentHeight = lastBottom - contentTop;
        }

        const availableHeight = pageBox.clientHeight;
        const fillRatio = actualContentHeight / availableHeight;
        console.log(`[Renderer] Actual content height: ${actualContentHeight}, Available: ${availableHeight}, Fill ratio: ${(fillRatio * 100).toFixed(1)}%`);
        return {
            isSparse: fillRatio < 0.85, // 为保证美观，低于 85% 认为内容过少
            ratio: parseFloat(fillRatio.toFixed(2))
        };
    },
    
    /**
     * Bidirectional Auto-Fit for MCP/Paged.js mode
     * Uses Paged.js page count as the source of truth for overflow detection.
     * 
     * Algorithm:
     * 1. Let Paged.js render first
     * 2. Count .pagedjs_page elements
     * 3. If pages > 1: shrink styles and re-render
     * 4. If pages = 1 and content is sparse: expand styles and re-render
     * 5. Iterate until optimal fit is achieved
     */
    fitToOnePage: async function() {
        console.log('[Renderer] 📐 Starting Bidirectional Auto-Fit (Paged.js Mode)...');
        window.simpleViewer.isAutoFitting = true;
        
        // Config helpers
        const cfg = window.ResumeConfig || {};
        const sliderCfg = cfg.sliderConfig || [];
        const getSlider = (id) => sliderCfg.find(s => s.id === id) || {};
        const getStep = (id, fallback) => {
            const s = getSlider(id);
            return typeof s.step === 'number' ? s.step : fallback;
        };
        const getLimit = (id, isMax, fallback) => {
            const s = getSlider(id);
            return typeof s[isMax ? 'max' : 'min'] === 'number' ? s[isMax ? 'max' : 'min'] : fallback;
        };

        // Shrink strategies (low-impact first: margin → spacing → font)
        const shrinkStrategies = [
            { name: 'pageMargin', cssVar: '--page-margin', id: 'marginSlider', step: getStep('marginSlider', 1.0), unit: 'mm', min: getLimit('marginSlider', false, 7) },
            { name: 'bodyMargin', cssVar: '--body-margin', id: 'bodyMarginSlider', step: getStep('bodyMarginSlider', 0.1), unit: 'em', min: getLimit('bodyMarginSlider', false, 0) },
            { name: 'ulMargin', cssVar: '--ul-margin', id: 'ulMarginSlider', step: getStep('ulMarginSlider', 0.1), unit: 'em', min: getLimit('ulMarginSlider', false, 0) },
            { name: 'headingScale', cssVar: '--heading-scale', id: 'headingSlider', step: getStep('headingSlider', 0.1), unit: '', min: getLimit('headingSlider', false, 1.0) },
            { name: 'lineHeight', cssVar: '--line-height', id: 'lineHeightSlider', step: getStep('lineHeightSlider', 0.05), unit: '', min: getLimit('lineHeightSlider', false, 1.0) },
            { name: 'fontSize', cssVar: '--body-font-size', id: 'fontSlider', step: getStep('fontSlider', 0.5), unit: 'pt', min: getLimit('fontSlider', false, 9) }
        ];
        
        // Expand strategies (readability first: font → spacing → margin)
        const expandStrategies = [
            { name: 'fontSize', cssVar: '--body-font-size', id: 'fontSlider', step: getStep('fontSlider', 0.5), unit: 'pt', max: getLimit('fontSlider', true, 12) },
            { name: 'lineHeight', cssVar: '--line-height', id: 'lineHeightSlider', step: getStep('lineHeightSlider', 0.05), unit: '', max: getLimit('lineHeightSlider', true, 1.6) },
            { name: 'headingScale', cssVar: '--heading-scale', id: 'headingSlider', step: getStep('headingSlider', 0.1), unit: '', max: getLimit('headingSlider', true, 1.7) },
            { name: 'bodyMargin', cssVar: '--body-margin', id: 'bodyMarginSlider', step: getStep('bodyMarginSlider', 0.1), unit: 'em', max: getLimit('bodyMarginSlider', true, 0.5) },
            { name: 'ulMargin', cssVar: '--ul-margin', id: 'ulMarginSlider', step: getStep('ulMarginSlider', 0.1), unit: 'em', max: getLimit('ulMarginSlider', true, 0.5) },
            { name: 'pageMargin', cssVar: '--page-margin', id: 'marginSlider', step: getStep('marginSlider', 1.0), unit: 'mm', max: getLimit('marginSlider', true, 15) }
        ];

        const maxIterations = 25;
        
        // Helper: Get current page count from Paged.js output
        const getPageCount = () => document.querySelectorAll('.pagedjs_page').length;
        
        // Helper: Apply one shrink step
        const applyShrinkStep = () => {
            for (const strat of shrinkStrategies) {
                const cssVal = getComputedStyle(document.documentElement).getPropertyValue(strat.cssVar).trim();
                let val = parseFloat(cssVal);
                if (isNaN(val)) continue;
                
                if (val > strat.min + 0.001) {
                    let newVal = Math.max(strat.min, val - strat.step);
                    newVal = Math.round(newVal * 100) / 100;
                    handleStyleUpdate({ [strat.cssVar]: newVal + strat.unit });
                    console.log(`[Renderer] Shrink: ${strat.name} ${val} → ${newVal}${strat.unit}`);
                    return true;
                }
            }
            console.log("[Renderer] Shrink hit all limits.");
            return false;
        };
        
        // Helper: Apply one expand step
        const applyExpandStep = () => {
            for (const strat of expandStrategies) {
                const cssVal = getComputedStyle(document.documentElement).getPropertyValue(strat.cssVar).trim();
                let val = parseFloat(cssVal);
                if (isNaN(val)) continue;
                
                if (val < strat.max - 0.001) {
                    let newVal = Math.min(strat.max, val + strat.step);
                    newVal = Math.round(newVal * 100) / 100;
                    handleStyleUpdate({ [strat.cssVar]: newVal + strat.unit });
                    console.log(`[Renderer] Expand: ${strat.name} ${val} → ${newVal}${strat.unit}`);
                    return { strat, prevVal: val };
                }
            }
            console.log("[Renderer] Expand hit all limits.");
            return null;
        };
        
        // Helper: Render with Paged.js and return page count
        const renderAndCount = async () => {
            await handlePagedRender(state.currentStyles);
            return getPageCount();
        };

        let iteration = 0;
        let pageCount = getPageCount();
        let fillInfo = this.checkContentFill();
        let direction = 'none';
        
        console.log(`[Renderer] Initial page count: ${pageCount}, Initial fill: ${fillInfo.ratio}`);
        
        // Determine initial direction based on current page count
        if (pageCount > 1) {
            direction = 'shrink';
        } else if (pageCount === 1 && fillInfo.isSparse) {
            direction = 'expand';
        }
        
        console.log(`[Renderer] Direction: ${direction}`);

        // SHRINK LOOP: Reduce content until it fits on 1 page
        if (direction === 'shrink') {
            while (pageCount > 1 && iteration < maxIterations) {
                const adjusted = applyShrinkStep();
                if (!adjusted) break;
                
                pageCount = await renderAndCount();
                console.log(`[Renderer] After shrink iter ${iteration + 1}: ${pageCount} pages`);
                iteration++;
            }
        }
        
        // EXPAND LOOP: Increase readability while staying on 1 page
        if (direction === 'expand') {
            let lastAdjusted = null;
            while (pageCount === 1 && iteration < maxIterations) {
                fillInfo = this.checkContentFill();
                if (!fillInfo.isSparse) break;

                lastAdjusted = applyExpandStep();
                if (!lastAdjusted) break;
                
                pageCount = await renderAndCount();
                console.log(`[Renderer] After expand iter ${iteration + 1}: ${pageCount} pages`);
                
                // Rollback if expansion caused overflow
                if (pageCount > 1) {
                    console.log("[Renderer] Expand caused overflow, rolling back...");
                    const { strat, prevVal } = lastAdjusted;
                    handleStyleUpdate({ [strat.cssVar]: prevVal + strat.unit });
                    pageCount = await renderAndCount();
                    break;
                }
                iteration++;
            }
        }
        
        const finalPageCount = getPageCount();
        const finalFill = this.checkContentFill();
        console.log(`[Renderer] Auto-Fit finished: ${direction}, ${iteration} iters, final pages: ${finalPageCount}, final fill: ${finalFill.ratio}`);
        
        window.autoFitResult = { 
            attempted: true, 
            direction: direction,
            success: finalPageCount === 1,
            iterations: iteration,
            pageCount: finalPageCount,
            fillRatio: finalFill.ratio
        };
        
        window.simpleViewer.isAutoFitting = false;
        document.body.classList.add('autofit-complete');
    }
};
