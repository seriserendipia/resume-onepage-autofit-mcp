"""
长期复用测试：验证发布前的配置安全性
确保敏感文件被 .gitignore 正确排除

此测试应在每次发布前运行
"""
import os
import subprocess
import sys
import io
from pathlib import Path

# 修复 Windows 控制台 Unicode 输出问题
# if sys.platform == 'win32':
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 应被 .gitignore 排除的敏感文件
SENSITIVE_FILES = [
    'js/config.js',       # 个人配置
    'myexperience.md',    # 个人简历
]

# 必须存在的示例文件
REQUIRED_EXAMPLE_FILES = [
    'js/config.example.js',   # 配置示例
    'example_resume.md',       # 简历示例
    '.gitignore',             # 忽略文件
]


def check_gitignore_contains(filepath: str) -> bool:
    """检查文件是否在 .gitignore 中"""
    gitignore_path = PROJECT_ROOT / '.gitignore'
    if not gitignore_path.exists():
        return False
    
    content = gitignore_path.read_text(encoding='utf-8')
    # 简单检查：文件路径是否在 .gitignore 中
    return filepath in content


def check_git_status(filepath: str) -> bool:
    """检查文件是否会被 git 跟踪（使用 git check-ignore）"""
    full_path = PROJECT_ROOT / filepath
    if not full_path.exists():
        return True  # 文件不存在，自然不会被跟踪
    
    try:
        result = subprocess.run(
            ['git', 'check-ignore', '-q', filepath],
            cwd=PROJECT_ROOT,
            capture_output=True
        )
        return result.returncode == 0  # 返回0表示被忽略
    except FileNotFoundError:
        # git 未安装
        print("⚠️ 警告: git 未安装，无法验证 .gitignore")
        return True


def main():
    print("=" * 60)
    print("发布前配置安全检查")
    print("=" * 60)
    
    all_passed = True
    
    # 1. 检查敏感文件是否在 .gitignore 中
    print("\n1. 检查敏感文件是否被 .gitignore 排除:")
    for filepath in SENSITIVE_FILES:
        in_gitignore = check_gitignore_contains(filepath)
        is_ignored = check_git_status(filepath)
        
        if in_gitignore:
            print(f"  ✅ {filepath} 在 .gitignore 中")
        else:
            print(f"  ❌ {filepath} 不在 .gitignore 中")
            all_passed = False
    
    # 2. 检查示例文件是否存在
    print("\n2. 检查示例文件是否存在:")
    for filepath in REQUIRED_EXAMPLE_FILES:
        full_path = PROJECT_ROOT / filepath
        if full_path.exists():
            print(f"  ✅ {filepath} 存在")
        else:
            print(f"  ❌ {filepath} 不存在")
            all_passed = False
    
    # 3. 检查示例配置不包含个人信息
    print("\n3. 检查示例配置不包含个人信息:")
    example_config = PROJECT_ROOT / 'js/config.example.js'
    if example_config.exists():
        content = example_config.read_text(encoding='utf-8')
        sensitive_patterns = ['Yihe', 'yihelu', 'D:\\\\Downloads']
        found_sensitive = False
        for pattern in sensitive_patterns:
            if pattern in content:
                print(f"  ❌ config.example.js 包含敏感信息: {pattern}")
                found_sensitive = True
                all_passed = False
        if not found_sensitive:
            print(f"  ✅ config.example.js 不包含个人敏感信息")
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有检查通过！可以安全发布")
    else:
        print("❌ 存在问题，请在发布前修复")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
