// MultiPreviewManager: manage one or more Paged.Previewer instances with a simple API.
// It works with Paged.js polyfill bundled in js/paged.polyfill.js via window.Paged.Previewer.
// Default usage registers a single instance rendering into the default paged.js container,
// but the API is extensible to multiple side-by-side previews.

(function () {
  const fontsReady = () => (document.fonts && document.fonts.ready) ? document.fonts.ready.catch(() => {}) : Promise.resolve();

  class MultiPreviewManager {
    constructor() {
      this.instances = new Map(); // id -> { previewer, container, stylesheets, getSource, lastError }
      this.enabled = true; // feature flag; can be turned off to fall back to legacy path
    }

    // Register or update a preview instance
    register(id, options) {
      const {
        container,           // HTMLElement | CSS selector string | null (if null, use paged default container)
        stylesheets = [],    // array of stylesheet URLs (strings)
        getSource,           // () => HTMLElement (source content node)
        onRendered           // optional callback(flow) per instance
      } = options || {};

      if (!window.Paged || !window.Paged.Previewer) {
        throw new Error('window.Paged.Previewer is not available. Ensure paged.polyfill.js is loaded and PagedConfig.auto=false.');
      }

      let containerEl = null;
      if (typeof container === 'string') {
        containerEl = document.querySelector(container);
      } else if (container instanceof HTMLElement) {
        containerEl = container;
      }

      const existing = this.instances.get(id);
      const previewer = existing?.previewer || new window.Paged.Previewer();

      this.instances.set(id, {
        previewer,
        container: containerEl || null,
        stylesheets: Array.isArray(stylesheets) ? stylesheets : [],
        getSource: typeof getSource === 'function' ? getSource : null,
        onRendered: typeof onRendered === 'function' ? onRendered : null,
        lastError: null,
      });

      return this;
    }

    setStyles(id, stylesheets) {
      const inst = this.instances.get(id);
      if (!inst) throw new Error(`Instance '${id}' not found`);
      inst.stylesheets = Array.isArray(stylesheets) ? stylesheets : [];
    }

    async render(id) {
      if (!this.enabled) return; // feature-flag off

      const inst = this.instances.get(id);
      if (!inst) throw new Error(`Instance '${id}' not found`);
      const { previewer, container, stylesheets, getSource, onRendered } = inst;

      const source = getSource ? getSource() : document.getElementById('content');
      if (!source) throw new Error('render(): source element not found');

      if (container) container.innerHTML = '';

      await fontsReady();

      try {
        const flow = await previewer.preview(source, stylesheets, container || undefined);
        inst.lastError = null;
        if (typeof onRendered === 'function') onRendered(flow);
        return flow;
      } catch (err) {
        inst.lastError = err;
        throw err;
      }
    }

    async renderAll() {
      if (!this.enabled) return;
      const ids = Array.from(this.instances.keys());
      for (const id of ids) {
        await this.render(id);
      }
    }

    // Convenience for single-instance default registration
    ensureDefaultInstance() {
      if (this.instances.size === 0) {
        this.register('default', {
          container: null, // let paged.js use its default render root
          stylesheets: [],
          getSource: () => document.getElementById('content')
        });
      }
      return this;
    }
  }

  // expose globally
  window.MultiPreviewManager = MultiPreviewManager;
})();
