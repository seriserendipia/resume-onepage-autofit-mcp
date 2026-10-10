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

# 只属于私有仓的文件：local-main 上可以有，public staging / upstream 上不能有
PRIVATE_ONLY_PATHS = [
    'DEV_WORKFLOW.md',
    'docs/superpowers/',
    'docs/handoff_',
    'docs/ats-parse-eval.md',
]

# 所有被跟踪文件都不能含有的个人信息。更具体的敏感词（电话、邮箱等）写在被 .gitignore
# 排除的 tests/.private_patterns.txt 里，每行一个，免得敏感词本身被发布出去。
PERSONAL_PATTERNS = ['D:\\Downloads']
PRIVATE_PATTERNS_FILE = PROJECT_ROOT / 'tests' / '.private_patterns.txt'

# 必须存在的示例文件
REQUIRED_EXAMPLE_FILES = [
    'js/config.defaults.js',   # 配置默认值（单一权威源）
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


def git_tracked_files():
    result = subprocess.run(['git', 'ls-files', '-z'], cwd=PROJECT_ROOT, capture_output=True, check=True)
    return [f for f in result.stdout.decode('utf-8').split('\0') if f]


def current_branch() -> str:
    result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=PROJECT_ROOT, capture_output=True, text=True)
    return result.stdout.strip()


def is_private_only(path: str) -> bool:
    return any(path == p or (p.endswith(('/', '_')) and path.startswith(p)) for p in PRIVATE_ONLY_PATHS)


def personal_patterns():
    patterns = list(PERSONAL_PATTERNS)
    if PRIVATE_PATTERNS_FILE.exists():
        for line in PRIVATE_PATTERNS_FILE.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.startswith('#'):
                patterns.append(line.strip())
    return patterns


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
    defaults_config = PROJECT_ROOT / 'js/config.defaults.js'
    if defaults_config.exists():
        content = defaults_config.read_text(encoding='utf-8')
        sensitive_patterns = ['D:\\Downloads']
        found_sensitive = False
        for pattern in sensitive_patterns:
            if pattern in content:
                print(f"  ❌ config.defaults.js 包含敏感信息: {pattern}")
                found_sensitive = True
                all_passed = False
        if not found_sensitive:
            print(f"  ✅ config.defaults.js 不包含个人敏感信息")
    
    # 4. 被跟踪的文件里不能有个人信息（私有专属文件除外，它们由第 5 项把关）
    print("\n4. 扫描所有被跟踪文件中的个人信息:")
    patterns = personal_patterns()
    if not PRIVATE_PATTERNS_FILE.exists():
        print(f"  ⚠️ 没有 {PRIVATE_PATTERNS_FILE.relative_to(PROJECT_ROOT)}，只检查内置的 {len(patterns)} 个敏感词")
    hits = []
    for path in git_tracked_files():
        if is_private_only(path) or path == 'tests/test_release_safety.py':
            continue
        try:
            content = (PROJECT_ROOT / path).read_text(encoding='utf-8')
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if any(pattern.lower() in line.lower() for pattern in patterns):
                hits.append(f"{path}:{lineno}")
    if hits:
        all_passed = False
        for hit in hits:
            print(f"  ❌ {hit} 含有个人信息")
    else:
        print(f"  ✅ 未发现个人信息（{len(patterns)} 个敏感词）")

    # 5. 私有专属文件不能出现在 public staging / upstream 上
    branch = current_branch()
    print(f"\n5. 检查私有专属文件（当前分支: {branch}）:")
    private = [p for p in git_tracked_files() if is_private_only(p)]
    if branch == 'local-main':
        print(f"  ℹ️ local-main 是私有分支，跳过（{len(private)} 个私有文件）")
    elif private:
        all_passed = False
        for path in private:
            print(f"  ❌ {path} 只属于私有仓")
    else:
        print("  ✅ 没有私有专属文件")

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
