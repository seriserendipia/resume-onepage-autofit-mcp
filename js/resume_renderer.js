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
        '--font-family': defaults.fontFamily || 'sans-serif',
        '--body-font-size': `${defaults.fontSize}pt`,
        '--heading-scale': `${defaults.headingScale}`,
        '--line-height': `${defaults.lineHeight}`,
        '--page-margin': `${defaults.margin}mm`,
        '--title-hr-margin': `${defaults.titleHrMargin}`,
        '--body-margin': `${defaults.bodyMargin}`,
        '--ul-margin': `${defaults.ulMargin}`,
        '--strong-paragraph-margin': `${defaults.strongParagraphMargin}`
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

// Tag entry-header paragraphs: a <p> whose LAST meaningful node is a trailing
// <em> (italic date/location), with real content before it. Decouples the
// "is this an entry header" structure from bolding — the company/school no longer
// needs to be **bold** for the date to right-align. Body prose that merely ends
// with "*italic*." is NOT tagged (text follows the <em>); nor is a fully-italic line.
function tagEntryHeaders(root) {
    root.querySelectorAll('p').forEach(p => {
        const last = p.lastElementChild;
        if (!last || last.tagName !== 'EM') return;
        let after = '';
        for (let n = last.nextSibling; n; n = n.nextSibling) after += n.textContent;
        if (after.trim() !== '') return;
        if (p.textContent.trim() === last.textContent.trim()) return;
        p.classList.add('entry-header');
    });
}

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

        // Tag entry-header paragraphs (decoupled from bolding) BEFORE the snapshot,
        // so the .entry-header class persists across paged.js re-renders.
        tagEntryHeaders(contentDiv);

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

// Paged.js measures text to place page breaks, so the bundled webfont must be
// loaded BEFORE layout — otherwise it paginates with fallback-font metrics.
async function ensureFontsLoaded() {
    if (!document.fonts || !document.fonts.load) return;
    const family = getComputedStyle(document.documentElement).getPropertyValue('--font-family').trim();
    if (!family) return;
    const variants = ['400', 'italic 400', '600', 'italic 600', '700', 'italic 700'];
    try {
        await Promise.all(variants.map(v => document.fonts.load(`${v} 12px ${family}`)));
    } catch (e) {
        console.log('[Renderer] Font preload failed, using fallback font', String(e));
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

        await ensureFontsLoaded();

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
     * 1. Treat the current styles as the "ideal" state.
     * 2. Build a ladder of states from roomiest to most compact:
     *      [ideal expanded step by step (expandOrder)] ← ideal → [ideal tightened
     *      step by step (shrinkOrder)]
     *    Each parameter moves between its slider min/max in slider steps, one
     *    parameter at a time, so every state is a coherent, in-bounds layout.
     *    Whitespace gives way first, leading only within its band, font size last.
     * 3. Page height is monotonic along the ladder → binary-search the roomiest
     *    state that fits on one page.
     * 4. If even the most compact state overflows, keep it and report failure
     *    (the caller must cut content; typography is not squeezed any further).
     */
    fitToOnePage: async function() {
        console.log('[Renderer] 📐 Starting Bidirectional Auto-Fit (Paged.js Mode)...');
        window.simpleViewer.isAutoFitting = true;

        const cfg = window.ResumeConfig || {};
        const autoFitCfg = cfg.autoFit || {};
        const params = {};
        (cfg.sliderConfig || []).forEach(s => { params[s.styleKey] = s; });
        const known = (names) => (names || []).filter(n => params[n]);
        const shrinkOrder = known(autoFitCfg.shrinkOrder);
        const expandOrder = known(autoFitCfg.expandOrder);
        const cssUnit = (p) => (p.unit === 'pt' || p.unit === 'mm') ? p.unit : '';
        const round = (v) => Math.round(v * 1000) / 1000;

        // Ideal = what is currently applied, clamped into bounds
        const ideal = {};
        [...new Set([...shrinkOrder, ...expandOrder])].forEach(name => {
            const p = params[name];
            const val = parseFloat(getComputedStyle(document.documentElement).getPropertyValue(p.cssVar));
            if (isNaN(val)) return;
            ideal[name] = Math.min(p.max, Math.max(p.min, val));
        });

        // Walk one parameter at a time to its limit, recording every step
        const walk = (order, dir) => {
            const states = [];
            const cur = { ...ideal };
            order.forEach(name => {
                if (!(name in cur)) return;
                const p = params[name];
                const limit = dir < 0 ? p.min : p.max;
                while ((limit - cur[name]) * dir > 1e-6) {
                    const next = cur[name] + dir * p.step;
                    cur[name] = round(dir < 0 ? Math.max(limit, next) : Math.min(limit, next));
                    states.push({ ...cur });
                }
            });
            return states;
        };
        const expanded = walk(expandOrder, +1);
        const ladder = [...expanded.reverse(), { ...ideal }, ...walk(shrinkOrder, -1)];
        const idealIdx = expanded.length;

        const getPageCount = () => document.querySelectorAll('.pagedjs_page').length;
        let renders = 0;
        let appliedIdx = -1;
        const renderAt = async (idx) => {
            const styles = {};
            Object.entries(ladder[idx]).forEach(([name, val]) => {
                styles[params[name].cssVar] = val + cssUnit(params[name]);
            });
            handleStyleUpdate(styles);
            await handlePagedRender(state.currentStyles);
            renders++;
            appliedIdx = idx;
            const pages = getPageCount();
            console.log(`[Renderer] Auto-Fit probe #${renders}: state ${idx}/${ladder.length - 1} → ${pages} page(s)`);
            return pages;
        };

        const initialPages = getPageCount();
        const initialFill = this.checkContentFill();
        let direction = 'none';
        if (initialPages > 1) direction = 'shrink';
        else if (initialPages === 1 && initialFill.isSparse) direction = 'expand';
        console.log(`[Renderer] Initial page count: ${initialPages}, fill: ${initialFill.ratio}, direction: ${direction}, ladder: ${ladder.length} states`);

        if (direction !== 'none') {
            // Invariant: `best` is the roomiest state known to fit (or the most
            // compact state when nothing is known to fit yet).
            let lo, hi, best;
            if (direction === 'shrink') {
                lo = idealIdx + 1; hi = ladder.length - 1; best = ladder.length - 1;
            } else {
                lo = 0; hi = idealIdx - 1; best = idealIdx;
            }
            while (lo <= hi) {
                const mid = (lo + hi) >> 1;
                if (await renderAt(mid) === 1) { best = mid; hi = mid - 1; }
                else { lo = mid + 1; }
            }
            if (appliedIdx !== best) await renderAt(best);
        }

        const finalPageCount = getPageCount();
        const finalFill = this.checkContentFill();
        const finalStyles = {};
        Object.values(params).forEach(p => {
            finalStyles[p.styleKey] = getComputedStyle(document.documentElement).getPropertyValue(p.cssVar).trim();
        });
        console.log(`[Renderer] Auto-Fit finished: ${direction}, ${renders} renders, final pages: ${finalPageCount}, final fill: ${finalFill.ratio}`);

        window.autoFitResult = {
            attempted: true,
            direction: direction,
            success: finalPageCount === 1,
            iterations: renders,
            pageCount: finalPageCount,
            fillRatio: finalFill.ratio,
            styles: finalStyles
        };

        window.simpleViewer.isAutoFitting = false;
        document.body.classList.add('autofit-complete');
    }
};
