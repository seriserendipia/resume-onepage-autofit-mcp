"""
真实迭代削减测试：模拟 AI Agent 的完整工作流程
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp_server'))
from resume_renderer import ResumeRenderer

# V1: 长简历
LONG_RESUME = """
# 张三

**邮箱**：zhangsan@example.com | **电话**：138-0013-8000 | **GitHub**：github.com/zhangsan

---

## 工作经历

### 高级 Python 开发工程师 | XYZ 科技有限公司 | 2021.06 - 至今

- 负责设计并实现基于协同过滤的推荐算法，支持千万级用户的个性化推荐
- 使用 Python + FastAPI 构建高性能 RESTful API，QPS 达到 5000+
- 优化 Redis 缓存策略，将推荐结果响应时间从 200ms 降低到 50ms
- 引入 Docker + Kubernetes 实现服务容器化部署，提升系统可用性至 99.9%

### Python 开发工程师 | ABC 互联网公司 | 2019.07 - 2021.05

- 负责订单管理模块的开发与维护，处理日均 50万+ 订单
- 使用 Django ORM 优化数据库查询，将复杂查询响应时间降低 60%
- 实现基于 RabbitMQ 的消息队列，解决订单峰值处理问题

---

## 项目经历

**开源项目：Resume-Builder（GitHub 500+ Stars）**
- 使用 Python + Flask 开发的简历生成工具，支持 Markdown 转 PDF

---

## 技能清单

- **编程语言**：Python, JavaScript, SQL
- **框架/库**：Django, FastAPI, Flask, Pandas
- **数据库**：MySQL, PostgreSQL, Redis
- **工具/平台**：Docker, Kubernetes, Git

---

## 教育背景

**清华大学** | 计算机科学与技术 | 本科 | 2015-2019 | GPA: 3.8/4.0
"""

# V2: Level 3 削减后
REDUCED_V2 = """
# 张三

**邮箱**：zhangsan@example.com | **电话**：138-0013-8000

---

## 工作经历

### 高级 Python 开发工程师 | XYZ 科技 | 2021.06 - 至今

- 实现协同过滤推荐算法，支持千万级用户，QPS 5000+
- 优化 Redis 缓存，响应时间从 200ms 降至 50ms
- Docker + K8s 容器化部署，系统可用性 99.9%

### Python 开发工程师 | ABC 公司 | 2019.07 - 2021.05

- 开发订单管理模块，日均处理 50万+ 订单
- 优化 Django ORM 查询，响应时间降低 60%

---

## 技能

**语言**: Python | JavaScript | SQL | **框架**: Django | FastAPI | **数据库**: MySQL | Redis | **工具**: Docker | K8s | Git

---

## 教育

**清华大学** 计算机科学 本科 (2015-2019) | GPA: 3.8
"""

# V3: Level 2 再削减
REDUCED_V3 = """
# 张三

**邮箱**：zhangsan@example.com | **电话**：138-0013-8000

---

## 工作经历

### 高级 Python 开发工程师 | XYZ 科技 | 2021-至今

- 实现推荐算法，QPS 5000+，响应 50ms
- K8s 部署，可用性 99.9%

### Python 开发工程师 | ABC 公司 | 2019-2021

- 订单模块，日均 50万+ 订单
- 优化查询性能 60%

---

## 技能

Python | Django | FastAPI | MySQL | Redis | Docker | K8s

---

## 教育

清华大学 计算机科学 (2015-2019)
"""


async def test_iteration():
    """模拟完整的迭代削减流程"""
    print("🔄 开始迭代削减测试\n")
    
    renderer = ResumeRenderer()
    await renderer.start()
    
    versions = [
        ("V1 - 原始版本", LONG_RESUME),
        ("V2 - Level 3 削减", REDUCED_V2),
        ("V3 - Level 2 削减", REDUCED_V3),
    ]
    
    for i, (version_name, markdown) in enumerate(versions, 1):
        print("=" * 70)
        print(f"📝 第 {i} 轮迭代：{version_name}")
        print("=" * 70)
        
        result = await renderer.render_resume_pdf(
            markdown, 
            output_path=f"iteration_round_{i}.pdf"
        )
        
        print(f"\n状态: {result['status']}")
        print(f"当前页数: {result['current_pages']}")
        print(f"PDF 路径: {result['pdf_path']}")
        
        if result.get('content_stats'):
            stats = result['content_stats']
            print(f"\n📊 内容统计:")
            print(f"  - 字数: {stats.get('word_count', 0)}")
            print(f"  - 列表项: {stats.get('list_items', 0)}")
            print(f"  - 主要板块 (H2): {stats.get('h2_count', 0)}")
        
        if result['status'] == 'overflow':
            print(f"\n⚠️  溢出 {result['overflow_amount']}%")
            print(f"💡 建议: {result['hint']}")
            print(f"📄 消息: {result['message']}")
        else:
            print(f"\n✅ {result['message']}")
            print("\n🎉 削减成功！迭代结束")
            break
        
        print()
    
    await renderer.stop()
    
    print("=" * 70)
    print("✅ 测试完成！")
    print("\n生成的文件：")
    for i in range(1, len(versions) + 1):
        print(f"  - iteration_round_{i}.pdf")


if __name__ == "__main__":
    asyncio.run(test_iteration())
