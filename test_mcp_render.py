"""
测试 MCP Server 渲染功能
演示如何检测溢出并应用削减策略
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp_server'))

from mcp_server.resume_renderer import ResumeRenderer

# 测试用简历内容（故意较长以触发溢出）
LONG_RESUME = """
# 张三

**邮箱**：zhangsan@example.com | **电话**：138-0013-8000 | **GitHub**：github.com/zhangsan

---

## 工作经历

### 高级 Python 开发工程师 | XYZ 科技有限公司 | 2021.06 - 至今

**项目：智能推荐系统**
- 负责设计并实现基于协同过滤的推荐算法，支持千万级用户的个性化推荐
- 使用 Python + FastAPI 构建高性能 RESTful API，QPS 达到 5000+
- 优化 Redis 缓存策略，将推荐结果响应时间从 200ms 降低到 50ms
- 引入 Docker + Kubernetes 实现服务容器化部署，提升系统可用性至 99.9%
- 与产品团队紧密协作，展现出色的沟通能力和需求分析能力

**项目：数据分析平台**
- 开发基于 Pandas 和 Matplotlib 的数据可视化模块，支持多维度数据分析
- 设计并实现 ETL 数据管道，每日处理 100GB+ 的业务数据
- 使用 Celery 实现异步任务调度，优化长时任务执行效率
- 编写详细的技术文档和操作手册，提升团队协作效率

### Python 开发工程师 | ABC 互联网公司 | 2019.07 - 2021.05

**项目：电商后台管理系统**
- 负责订单管理模块的开发与维护，处理日均 50万+ 订单
- 使用 Django ORM 优化数据库查询，将复杂查询响应时间降低 60%
- 实现基于 RabbitMQ 的消息队列，解决订单峰值处理问题
- 参与 Code Review，保证代码质量和团队规范

**项目：用户行为分析系统**
- 使用 Python + Spark 分析用户行为数据，为运营决策提供数据支持
- 开发实时数据看板，集成 ECharts 展示关键业务指标
- 优化数据采集流程，数据准确率提升至 98%

### 软件开发实习生 | DEF 软件公司 | 2018.06 - 2019.06

- 参与公司内部工具的开发，使用 Python 编写自动化脚本
- 协助测试团队进行自动化测试脚本编写
- 学习并掌握 Git 版本控制和敏捷开发流程

---

## 项目经历

### 开源项目：Resume-Builder（GitHub 500+ Stars）

- 使用 Python + Flask 开发的简历生成工具，支持 Markdown 转 PDF
- 实现自动排版算法，确保简历内容适配单页
- 获得社区积极反馈，持续维护和迭代

### 个人项目：智能股票分析系统

- 爬取金融数据并使用机器学习预测股票走势
- 采用 LSTM 神经网络模型，预测准确率达到 65%
- 使用 Streamlit 构建交互式 Web 界面

---

## 技能清单

- **编程语言**：Python, JavaScript, SQL, Bash
- **框架/库**：Django, FastAPI, Flask, Pandas, NumPy, Scikit-learn
- **数据库**：MySQL, PostgreSQL, Redis, MongoDB
- **工具/平台**：Docker, Kubernetes, Git, Jenkins, Linux
- **其他技能**：RESTful API 设计, 微服务架构, 数据分析, 机器学习基础

---

## 教育背景

**清华大学** | 计算机科学与技术 | 本科 | 2015.09 - 2019.06

- GPA: 3.8/4.0
- 核心课程：数据结构、算法设计、操作系统、数据库原理、机器学习
- 获得校级一等奖学金（连续三年）

---

## 证书与荣誉

- AWS Certified Solutions Architect (2022)
- 全国大学生数学建模竞赛 省级一等奖 (2017)
- 校级优秀毕业生 (2019)
"""

# 简化版本（应用 Level 2 削减策略）
REDUCED_RESUME = """
# 张三

**邮箱**：zhangsan@example.com | **电话**：138-0013-8000 | **GitHub**：github.com/zhangsan

---

## 工作经历

### 高级 Python 开发工程师 | XYZ 科技有限公司 | 2021.06 - 至今

- 设计并实现协同过滤推荐算法，支持千万级用户，QPS 5000+
- 优化 Redis 缓存策略，推荐响应时间从 200ms 降至 50ms
- 引入 Docker + K8s 容器化部署，系统可用性达 99.9%

### Python 开发工程师 | ABC 互联网公司 | 2019.07 - 2021.05

- 开发订单管理模块，处理日均 50万+ 订单
- 优化 Django ORM 查询，复杂查询响应时间降低 60%
- 实现 RabbitMQ 消息队列，解决订单峰值处理

---

## 项目经历

**Resume-Builder（GitHub 500+ Stars）**：使用 Python + Flask 开发简历生成工具，实现自动排版算法

**智能股票分析**：采用 LSTM 预测股票走势，准确率 65%，Streamlit 构建交互界面

---

## 技能

**语言**：Python | JavaScript | SQL | **框架**：Django | FastAPI | Pandas | **数据库**：MySQL | Redis | **工具**：Docker | K8s | Git

---

## 教育

**清华大学** 计算机科学与技术 本科 (2015-2019) | GPA: 3.8/4.0
"""


async def test_overflow_detection():
    """测试溢出检测功能"""
    print("=" * 60)
    print("测试 1: 溢出检测")
    print("=" * 60)
    
    renderer = ResumeRenderer()
    await renderer.start()
    
    result = await renderer.render_resume_pdf(
        LONG_RESUME, 
        "test_long_resume.pdf"
    )
    
    print("\n📊 渲染结果：")
    print(f"状态: {result['status']}")
    print(f"当前页数: {result['current_pages']}")
    
    if result['status'] == 'failed':
        print(f"溢出量: {result['overflow_amount']}%")
        print(f"溢出像素: {result['overflow_px']}px")
        print(f"建议: {result['hint']}")
    else:
        print(f"PDF 路径: {result['pdf_path']}")
    
    await renderer.stop()
    print("\n" + "=" * 60)


async def test_successful_render():
    """测试成功渲染（简化版）"""
    print("=" * 60)
    print("测试 2: 成功渲染（简化版）")
    print("=" * 60)
    
    renderer = ResumeRenderer()
    await renderer.start()
    
    result = await renderer.render_resume_pdf(
        REDUCED_RESUME, 
        "test_reduced_resume.pdf"
    )
    
    print("\n📊 渲染结果：")
    print(f"状态: {result['status']}")
    print(f"当前页数: {result['current_pages']}")
    
    if result['status'] == 'success':
        print(f"✅ PDF 已生成: {result['pdf_path']}")
        print(f"消息: {result['message']}")
    else:
        print(f"⚠️ 仍需削减: {result['hint']}")
    
    await renderer.stop()
    print("\n" + "=" * 60)


async def test_iteration_flow():
    """模拟完整的迭代流程"""
    print("=" * 60)
    print("测试 3: 完整迭代流程模拟")
    print("=" * 60)
    
    renderer = ResumeRenderer()
    await renderer.start()
    
    versions = [
        ("V1 - 原始版本", LONG_RESUME),
        ("V2 - 削减后版本", REDUCED_RESUME)
    ]
    
    for version_name, markdown in versions:
        print(f"\n📝 正在渲染 {version_name}...")
        result = await renderer.render_resume_pdf(
            markdown, 
            f"iteration_{version_name.split()[0]}.pdf"
        )
        
        if result['status'] == 'success':
            print(f"✅ {version_name} 成功！")
            break
        else:
            print(f"⚠️ {version_name} 溢出 {result['overflow_amount']}%")
            print(f"   建议：{result['hint']}")
    
    await renderer.stop()
    print("\n" + "=" * 60)


async def main():
    """运行所有测试"""
    print("\n🚀 开始测试 MCP Server 渲染功能\n")
    
    try:
        await test_overflow_detection()
        await asyncio.sleep(1)
        
        await test_successful_render()
        await asyncio.sleep(1)
        
        await test_iteration_flow()
        
        print("\n✅ 所有测试完成！")
        print("\n生成的文件：")
        print("- test_long_resume.pdf (如果未溢出)")
        print("- test_reduced_resume.pdf")
        print("- iteration_V1.pdf (如果未溢出)")
        print("- iteration_V2.pdf")
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
