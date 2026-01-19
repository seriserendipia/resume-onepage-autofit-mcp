// Resume Config File
// 简历系统配置文件
const ResumeConfig = {
  // 数据源配置
  dataSources: {
    defaultFile: 'myexperience.md',
    availableFiles: [
      { id: 'main', name: '我的简历', path: 'myexperience.md' },
      // { id: 'template', name: '简历模板', path: 'template.md' },
      { id: 'backup', name: '备份简历', path: 'backup.md' }
    ],
    currentSource: 'main'  // 
  },

  // 滑杆与CSS变量映射配置 (Hardcoded Satisfied Values)
  sliderConfig: [
    { id: 'fontSlider', cssVar: '--body-font-size', unit: 'pt', valueId: 'fontValue', storage: 'defaultFontSize', min: 9, max: 13, step: 0.5 },
    { id: 'headingSlider', cssVar: '--heading-scale', unit: '倍', valueId: 'headingValue', storage: 'defaultHeadingScale', min: 1.0, max: 1.7, step: 0.1 },
    { id: 'lineHeightSlider', cssVar: '--line-height', unit: '倍', valueId: 'lineHeightValue', storage: 'defaultLineHeight', min: 1.0, max: 1.7, step: 0.05 },
    
    // A4 页面边距 (物理尺寸)
    { id: 'marginSlider', cssVar: '--page-margin', unit: 'mm', valueId: 'marginValue', storage: 'defaultMargin', type: 'updatePageMargin', min: 7, max: 21, step: 1 },
    
    // 内容间距 (相对于字号的倍数 em)
    { id: 'titleHrMarginSlider', cssVar: '--title-hr-margin', unit: 'em', valueId: 'titleHrMarginValue', storage: 'defaultTitleHrMargin', min: 0, max: 0.7, step: 0.1 },
    { id: 'bodyMarginSlider', cssVar: '--body-margin', unit: 'em', valueId: 'bodyMarginValue', storage: 'defaultBodyMargin', min: 0, max: 0.5, step: 0.1 },
    { id: 'ulMarginSlider', cssVar: '--ul-margin', unit: 'em', valueId: 'ulMarginValue', storage: 'defaultUlMargin', min: 0, max: 0.5, step: 0.1 },
    { id: 'strongParagraphMarginSlider', cssVar: '--strong-paragraph-margin', unit: 'em', valueId: 'strongParagraphMarginValue', storage: 'defaultStrongParagraphMargin', min: 0, max: 0.2, step: 0.1 }
  ],

  // 默认样式值
  defaultStyles: {
    fontSize: 9,
    headingScale: 1.7,
    lineHeight: 1.45,
    margin: 7, // mm
    
    // 以下单位均为 em (倍数)
    titleHrMargin: 0,
    bodyMargin: 0.5,
    ulMargin: 0,
    strongParagraphMargin: 0.2
  },

  // 应用设置
  app: {
    title: 'Resume Builder',
    version: '1.0.0',
    debug: true
  },

  // PDF 输出配置 (用于 MCP Server)
  pdfOutput: {
    // 默认输出目录
    directory: 'D:\\Downloads', 
    // 默认文件名
    filename: 'Yihe Lu resume.pdf'
  },

  // 自动一页配置（Auto One-Page Fit）
  autoFit: {
    // 首次加载后自动尝试一页
    runOnFirstLoad: true,
    // 最大迭代次数（全局上限）
    maxIterations: 10,
    // 调整顺序：页边距 → 间距 → 标题比例 → 行高 → 字体大小
    strategyOrder: ['pageMargin', 'spacing', 'headingScale', 'lineHeight', 'fontSize'],
    // 参数范围与步长
    bounds: {
      // @page 页面边距（mm）
      pageMarginMm: { min: 5, max: 25, step: 1 },
      // 正文字号（pt）
      // 标题比例（相对正文字号倍数）
      headingScale: { min: 1.1, max: 1.8, step: 0.05 },
      // 行高
      lineHeight: { min: 1.1, max: 1.6, step: 0.02 },
      // 内容垂直间距（滑杆原始值，和字体大小相乘后转为 px/pt）
      spacingScales: {
        bodyMargin: { min: 0.02, max: 0.15, step: 0.01 },
        ulMargin: { min: 0.02, max: 0.15, step: 0.01 },
        strongParagraphMargin: { min: 0.02, max: 0.15, step: 0.01 }
      }
    }
  }
};

// 导出配置对象
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ResumeConfig;
} else {
  window.ResumeConfig = ResumeConfig;
}