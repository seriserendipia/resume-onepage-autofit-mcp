// ============================================================================
// Resume Config Defaults - 简历系统默认配置（权威来源）
// ============================================================================
// 
// 📋 This file is git-tracked and provides defaults for ALL users.
//    To override, create config.js (gitignored) with only the fields you want:
//
//    ResumeConfig.pdfOutput.directory = 'D:\\Downloads';
//    ResumeConfig.pdfOutput.filename = 'My Resume.pdf';
//    ResumeConfig.defaultStyles.fontSize = 12;
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
  // 垂直间距统一以「一行正文的高度」u = fontSize × lineHeight 为单位，
  // 并保持层级：章节间距 > 条目间距 > 列表项间距（亲密性原则）。
  // All vertical gaps are multiples of one body line (u = fontSize × lineHeight),
  // keeping the hierarchy: section gap > entry gap > bullet gap.
  //
  // 字号/行高是按 Source Sans 3 (x-height 0.478em) 调的。它的 x-height 比
  // Arial (0.528em) 小，所以 12pt 的视觉大小 ≈ Arial 10.9pt，行高比例也相应更低。
  // 换字体时请一并重调 fontSize / lineHeight 及其滑杆范围。
  // Sizes are tuned for Source Sans 3; if you change fontFamily, retune them.
  //
  defaultStyles: {
    fontFamily: "'Source Sans 3', 'Helvetica Neue', Arial, sans-serif",
    fontSize: 12,            // 正文字号 (pt)
    headingScale: 1.1,       // 章节标题相对正文的倍数
    lineHeight: 1.26,        // 正文行高（标题/姓名的行高在 CSS 中按角色单独设定）
    margin: 13,              // 页面边距 (mm) — 实际边距，≈0.5in

    // 以下单位均为 u (一行正文高度的倍数)
    titleHrMargin: 0.8,            // 章节间距（章节标题上方）
    bodyMargin: 0.45,              // 条目间距（段落 / 条目头上方）
    ulMargin: 0.1,                 // 列表项间距
    strongParagraphMargin: 0       // 条目头额外间距（叠加在条目间距之上，仅作用于带日期/地点的条目头）
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
  // 字段说明 (Field reference):
  //   styleKey     → 对应 defaultStyles 中的默认值字段（默认值的唯一来源）
  //                  Maps to a key in defaultStyles above — the single source for this slider's default.
  //   storage      → localStorage 持久化键名（用户拖动滑杆后保存的个人值）
  //   min/max/step → 滑杆范围与步长；运行时由 sliderController 写入 DOM，HTML 无需再写
  sliderConfig: [
    { id: 'fontSlider', styleKey: 'fontSize', cssVar: '--body-font-size', unit: 'pt', valueId: 'fontValue', storage: 'defaultFontSize', min: 11.5, max: 13, step: 0.25 },
    { id: 'headingSlider', styleKey: 'headingScale', cssVar: '--heading-scale', unit: '倍', valueId: 'headingValue', storage: 'defaultHeadingScale', min: 1.0, max: 1.2, step: 0.05 },
    { id: 'lineHeightSlider', styleKey: 'lineHeight', cssVar: '--line-height', unit: '倍', valueId: 'lineHeightValue', storage: 'defaultLineHeight', min: 1.18, max: 1.36, step: 0.02 },
    { id: 'marginSlider', styleKey: 'margin', cssVar: '--page-margin', unit: 'mm', valueId: 'marginValue', storage: 'defaultMargin', type: 'updatePageMargin', min: 10, max: 18, step: 1 },
    { id: 'titleHrMarginSlider', styleKey: 'titleHrMargin', cssVar: '--title-hr-margin', unit: 'u', valueId: 'titleHrMarginValue', storage: 'defaultTitleHrMargin', min: 0.5, max: 1.0, step: 0.1 },
    { id: 'bodyMarginSlider', styleKey: 'bodyMargin', cssVar: '--body-margin', unit: 'u', valueId: 'bodyMarginValue', storage: 'defaultBodyMargin', min: 0.25, max: 0.6, step: 0.05 },
    { id: 'ulMarginSlider', styleKey: 'ulMargin', cssVar: '--ul-margin', unit: 'u', valueId: 'ulMarginValue', storage: 'defaultUlMargin', min: 0, max: 0.2, step: 0.05 },
    { id: 'strongParagraphMarginSlider', styleKey: 'strongParagraphMargin', cssVar: '--strong-paragraph-margin', unit: 'u', valueId: 'strongParagraphMarginValue', storage: 'defaultStrongParagraphMargin', min: 0, max: 0.2, step: 0.1 }
  ],

  // ============================================================================
  // ⚙️ 高级配置 - 自动适配参数 (Advanced: Auto-Fit Parameters)
  // ============================================================================
  //
  // Auto-Fit 把 defaultStyles 当作「理想状态」，各参数的上下限取自上面 sliderConfig
  // 的 min/max/step。它按下面的顺序生成一条从「最宽松」到「最紧凑」的状态阶梯，
  // 然后二分查找能放进一页的最宽松状态。
  //
  // 收紧顺序 = 对可读性伤害从小到大：先收空白（章节→页边→条目头→条目→列表项），
  // 再收标题，再收行高（不低于下限），字号永远最后动、且有硬下限。
  // 触底仍放不下时不再压缩排版，而是返回 overflow 让调用方删减内容。
  //
  autoFit: {
    shrinkOrder: ['titleHrMargin', 'margin', 'strongParagraphMargin', 'bodyMargin', 'ulMargin', 'headingScale', 'lineHeight', 'fontSize'],
    // 内容过少时的放大顺序：先把字放大，再加行高与空白
    expandOrder: ['fontSize', 'lineHeight', 'headingScale', 'bodyMargin', 'ulMargin', 'titleHrMargin', 'strongParagraphMargin', 'margin']
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
