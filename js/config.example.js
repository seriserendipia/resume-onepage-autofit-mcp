// ============================================================================
// Resume Config File - 简历系统配置文件
// ============================================================================
// 
// 📋 使用方法 / How to use:
//    1. 复制此文件为 config.js（Copy this file to config.js）
//    2. 修改下方的配置项为你的个人设置
//    3. config.js 已在 .gitignore 中，不会被提交到 Git
//
// ============================================================================

const ResumeConfig = {

  // ============================================================================
  // 🎯 PDF 输出配置 (最常用 - 放在最前面方便查找)
  // PDF Output Settings (Most frequently used - placed at top for easy access)
  // ============================================================================
  // 
  // 这是 MCP Server 生成 PDF 时使用的保存路径配置。
  // 如果你希望 PDF 保存到特定文件夹，请修改下面的 directory 路径。
  // 
  // This is where MCP Server saves generated PDFs.
  // Modify the directory path below if you want PDFs saved to a specific folder.
  //
  pdfOutput: {
    // -------------------------------------------------------------------------
    // 📂 输出目录 (Output Directory)
    // -------------------------------------------------------------------------
    // 设置 PDF 文件的保存位置。留空则使用项目目录下的 generated_resume/ 文件夹。
    // 
    // Windows 路径示例:
    //   'C:\\Users\\YourName\\Documents\\Resumes'
    //   'D:\\MyResumes'
    // 
    // macOS/Linux 路径示例:
    //   '/Users/yourname/Documents/Resumes'
    //   '/home/yourname/resumes'
    //
    // 留空 '' = 使用默认路径 (项目目录/generated_resume/)
    // Empty '' = use default path (project_folder/generated_resume/)
    //
    directory: '',

    // -------------------------------------------------------------------------
    // 📄 默认文件名 (Default Filename)
    // -------------------------------------------------------------------------
    // PDF 文件的默认名称。AI 调用时也可以指定其他文件名覆盖此设置。
    // 
    // 示例: 'my_resume.pdf', 'John_Doe_Resume.pdf'
    //
    filename: 'output_resume.pdf'
  },

  // ============================================================================
  // 📝 简历数据源配置 (Resume Data Source)
  // ============================================================================
  // 
  // 配置简历 Markdown 文件的位置。默认读取项目根目录的 myexperience.md。
  // 如果你有多份简历，可以在 availableFiles 中添加。
  //
  dataSources: {
    // 默认加载的文件
    defaultFile: 'myexperience.md',

    // 可选的简历文件列表（用于控制面板切换）
    availableFiles: [
      { id: 'main', name: '我的简历', path: 'myexperience.md' },
      // { id: 'template', name: '简历模板', path: 'template.md' },
      { id: 'backup', name: '备份简历', path: 'backup.md' }
    ],

    // 当前选中的数据源 ID
    currentSource: 'main'
  },

  // ============================================================================
  // 🎨 默认样式值 (Default Style Values)
  // ============================================================================
  // 
  // 这些是简历渲染的初始样式参数。MCP Server 的 Auto-Fit 功能会自动调整这些值
  // 以确保内容正好适配一页。一般情况下不需要修改。
  //
  defaultStyles: {
    fontSize: 10.5,          // 正文字号 (pt)
    headingScale: 1.35,    // 标题相对正文的缩放倍数
    lineHeight: 1.25,     // 行高
    margin: 15,            // 页面边距 (mm)
    
    // 以下单位均为 em (相对于字号的倍数)
    titleHrMargin: 0.4,           // 标题下划线间距
    bodyMargin: 0.5,            // 正文段落间距
    ulMargin: 0.4,                // 列表项间距
    strongParagraphMargin: 0.1  // 加粗段落间距
  },

  // ============================================================================
  // 🔧 应用设置 (Application Settings)
  // ============================================================================
  app: {
    title: 'Resume Builder',
    version: '1.0.0',
    debug: true  // 设为 false 可减少控制台日志输出
  },

  // ============================================================================
  // ⚙️ 高级配置 - 滑杆控件映射 (Advanced: Slider Control Mapping)
  // ============================================================================
  // 
  // 以下配置用于控制面板的滑杆控件，一般用户无需修改。
  // 仅在需要自定义控制面板时参考。
  //
  sliderConfig: [
    { id: 'fontSlider', cssVar: '--body-font-size', unit: 'pt', valueId: 'fontValue', storage: 'defaultFontSize', min: 9.5, max: 12, step: 0.5 },
    { id: 'headingSlider', cssVar: '--heading-scale', unit: '倍', valueId: 'headingValue', storage: 'defaultHeadingScale', min: 1.1, max: 1.6, step: 0.05 },
    { id: 'lineHeightSlider', cssVar: '--line-height', unit: '倍', valueId: 'lineHeightValue', storage: 'defaultLineHeight', min: 1.15, max: 1.5, step: 0.05 },
    { id: 'marginSlider', cssVar: '--page-margin', unit: 'mm', valueId: 'marginValue', storage: 'defaultMargin', type: 'updatePageMargin', min: 10, max: 25, step: 1 },
    { id: 'titleHrMarginSlider', cssVar: '--title-hr-margin', unit: 'em', valueId: 'titleHrMarginValue', storage: 'defaultTitleHrMargin', min: 0, max: 0.6, step: 0.1 },
    { id: 'bodyMarginSlider', cssVar: '--body-margin', unit: 'em', valueId: 'bodyMarginValue', storage: 'defaultBodyMargin', min: 0, max: 0.5, step: 0.1 },
    { id: 'ulMarginSlider', cssVar: '--ul-margin', unit: 'em', valueId: 'ulMarginValue', storage: 'defaultUlMargin', min: 0, max: 0.5, step: 0.1 },
    { id: 'strongParagraphMarginSlider', cssVar: '--strong-paragraph-margin', unit: 'em', valueId: 'strongParagraphMarginValue', storage: 'defaultStrongParagraphMargin', min: 0, max: 0.3, step: 0.05 }
  ],

  // ============================================================================
  // ⚙️ 高级配置 - 自动适配参数 (Advanced: Auto-Fit Parameters)
  // ============================================================================
  // 
  // Auto-Fit 功能的参数范围设置。控制 MCP Server 自动调整样式时的边界值。
  // 一般用户无需修改，仅供高级定制使用。
  //
  autoFit: {
    runOnFirstLoad: true,     // 首次加载后自动尝试一页
    maxIterations: 10,        // 最大迭代次数
    
    // 调整策略顺序
    strategyOrder: ['pageMargin', 'spacing', 'headingScale', 'lineHeight', 'fontSize'],
    
    // 参数边界
    bounds: {
      pageMarginMm: { min: 5, max: 25, step: 1 },
      headingScale: { min: 1.1, max: 1.8, step: 0.05 },
      lineHeight: { min: 1.1, max: 1.6, step: 0.02 },
      spacingScales: {
        bodyMargin: { min: 0.02, max: 0.15, step: 0.01 },
        ulMargin: { min: 0.02, max: 0.15, step: 0.01 },
        strongParagraphMargin: { min: 0.02, max: 0.15, step: 0.01 }
      }
    }
  }
};

// ============================================================================
// 导出配置 (Export Configuration)
// ============================================================================
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ResumeConfig;
} else {
  window.ResumeConfig = ResumeConfig;
}
