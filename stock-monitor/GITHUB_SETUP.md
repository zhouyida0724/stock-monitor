# GitHub 集成配置指南

> 项目: stock-monitor  
> 路径: /Users/yidazhou/.openclaw/workspace/stock-monitor

## 📋 当前状态

| 检查项 | 状态 |
|--------|------|
| GitHub Skill | ✅ 已安装 |
| Git 初始化 | ✅ 已完成 |
| Git 用户名 | ✅ zhouyida |
| Git 邮箱 | ✅ zyd0724@hotmail.com |
| GitHub CLI (gh) | ❌ 未安装 |
| 远程仓库 | ❌ 未配置 |

## 🔧 配置步骤

### 第一步：安装 GitHub CLI

```bash
# 使用 Homebrew 安装
brew install gh
```

### 第二步：登录 GitHub

```bash
# 浏览器登录方式
gh auth login

# 按提示选择:
# - GitHub.com
# - HTTPS
# - 浏览器登录 (推荐)
```

### 第三步：创建 GitHub 仓库

**方式 A: 使用 gh CLI (推荐)**

```bash
cd /Users/yidazhou/.openclaw/workspace/stock-monitor

# 创建私有仓库
gh repo create stock-monitor --private --source=. --push

# 或创建公开仓库
gh repo create stock-monitor --public --source=. --push
```

**方式 B: 手动创建**

1. 访问 https://github.com/new
2. 填写仓库名: `stock-monitor`
3. 选择公开或私有
4. 不勾选 "Initialize this repository with a README"
5. 点击 "Create repository"
6. 按页面提示推送现有仓库

### 第四步：推送代码

如果第三步未自动推送，手动执行：

```bash
cd /Users/yidazhou/.openclaw/workspace/stock-monitor

# 添加远程仓库
git remote add origin https://github.com/USERNAME/stock-monitor.git

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit"

# 推送
git push -u origin master
```

## ❓ 需要用户提供的信息

在继续配置前，请提供以下信息：

1. **GitHub 用户名**: _____________
2. **仓库名称**: stock-monitor (建议) 或 _____________
3. **仓库可见性**: 
   - [ ] 公开 (Public)
   - [ ] 私有 (Private)
4. **是否已有远程仓库**: 
   - [ ] 没有，需要创建新的
   - [ ] 已有仓库: _____________

## 🚀 快速开始脚本

```bash
# 1. 安装 gh
brew install gh

# 2. 登录
gh auth login

# 3. 进入项目目录
cd /Users/yidazhou/.openclaw/workspace/stock-monitor

# 4. 创建并推送仓库 (请将 USERNAME 替换为你的 GitHub 用户名)
gh repo create stock-monitor --private --source=. --remote=origin --push

# 完成！
```

## 📚 常用命令

```bash
# 查看仓库状态
gh repo view

# 查看 Issue 列表
gh issue list

# 创建 Pull Request
gh pr create

# 查看工作流运行状态
gh run list
```

---

*生成时间: 2026-02-17*
