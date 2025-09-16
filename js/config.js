// 简历系统配置文件
const ResumeConfig = {
  // 数据源配置
  dataSources: {
    defaultFile: 'myexperience.md',
    availableFiles: [
      { id: 'main', name: '我的简历', path: 'myexperience.md' },
      { id: 'template', name: '简历模板', path: 'template.md' },
      { id: 'backup', name: '备份简历', path: 'backup.md' }
    ],
    currentSource: 'backup'  // 暂时使用backup.md，因为我们创建了这个文件
  },

  // 滑杆与CSS变量映射配置（复用现有配置）
  sliderConfig: [
    { id: 'fontSlider', cssVar: '--body-font-size', unit: 'pt', valueId: 'fontValue', storage: 'defaultFontSize' },
    { id: 'headingSlider', cssVar: '--heading-scale', unit: '', valueId: 'headingValue', storage: 'defaultHeadingScale' },
    { id: 'lineHeightSlider', cssVar: '--line-height', unit: '', valueId: 'lineHeightValue', storage: 'defaultLineHeight' },
    { id: 'marginSlider', cssVar: '--page-margin', unit: 'mm', valueId: 'marginValue', storage: 'defaultMargin', type: 'updatePageMargin' },
    { id: 'globalMarginSlider', cssVar: '--global-margin', unit: '', valueId: 'globalMarginValue', storage: 'defaultGlobalMargin', scale: 0.01 },
    { id: 'globalPaddingSlider', cssVar: '--global-padding', unit: '', valueId: 'globalPaddingValue', storage: 'defaultGlobalPadding', scale: 0.01 },
    { id: 'titleHrMarginSlider', cssVar: '--title-hr-margin', unit: '', valueId: 'titleHrMarginValue', storage: 'defaultTitleHrMargin', scale: 0.01 },
    { id: 'bodyMarginSlider', cssVar: '--body-margin', unit: '', valueId: 'bodyMarginValue', storage: 'defaultBodyMargin', scale: 0.01 },
    { id: 'ulMarginSlider', cssVar: '--ul-margin', unit: '', valueId: 'ulMarginValue', storage: 'defaultUlMargin', scale: 0.01 },
    { id: 'strongParagraphMarginSlider', cssVar: '--strong-paragraph-margin', unit: '', valueId: 'strongParagraphMarginValue', storage: 'defaultStrongParagraphMargin', scale: 0.01 }
  ],

  // 默认样式值
  defaultStyles: {
    fontSize: 16,
    headingScale: 1.5,
    lineHeight: 1.4,
    margin: 20,
    globalMargin: 5,
    globalPadding: 5,
    titleHrMargin: 5,
    bodyMargin: 5,
    ulMargin: 5,
    strongParagraphMargin: 5
  },

  // 应用设置
  app: {
    title: 'Resume Builder',
    version: '1.0.0',
    debug: true
  }
};

// 导出配置对象
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ResumeConfig;
} else {
  window.ResumeConfig = ResumeConfig;
}