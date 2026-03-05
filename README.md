# X Downloader

将 X 平台（Twitter）的推文/文章链接下载为本地 **Markdown** 文件，图片独立保存到文件夹中并在 Markdown 中引用。

**无需 API Key，无需登录，开箱即用。**

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📄 推文下载 | 普通推文保存为 `.md` 文件 |
| 📰 长文章下载 | 自动识别 X Article，完整转换为 Markdown |
| 📷 图片下载 | 自动下载到独立文件夹，Markdown 中使用相对路径引用 |
| 🧵 Thread 支持 | 自动追溯同一作者的推文串 |
| 📊 统计数据 | 保留点赞、转发、评论、浏览等数据 |
| 💬 引用推文 | 支持嵌入引用推文内容 |
| 🖼️ 封面图 | X Article 的封面图自动下载 |
| 📝 代码块 | X Article 中的代码块正确转换 |

## 📦 安装

```bash
git clone https://github.com/cwybruce/x-downloader.git
cd x-downloader
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 🚀 使用方法

```bash
# 激活虚拟环境
source .venv/bin/activate

# 下载推文
python x_downloader.py "<推文链接>"
```

### 命令示例

```bash
# 下载普通推文
python x_downloader.py "https://x.com/jack/status/20"

# 下载 X Article（长文章） —— 自动识别
python x_downloader.py "https://x.com/stark_nico99/status/2026235176150581282"

# 指定输出目录
python x_downloader.py "https://x.com/用户/status/ID" -o 我的收藏

# 只下载单条推文（不获取 Thread）
python x_downloader.py "https://x.com/用户/status/ID" --no-thread
```

### 命令参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `url` | X/Twitter 推文链接（必填） | — |
| `-o`, `--output-dir` | 输出目录 | `output` |
| `--no-thread` | 不获取 Thread，只下载单条 | `False` |

## 📁 输出结构

### 普通推文

```
output/
├── username_123456.md
└── username_123456_images/
    ├── 1.jpg
    └── ...
```

### X Article（长文章）

```
output/
├── username_123456.md              # 完整文章 Markdown
└── username_123456_images/
    ├── cover.jpg                   # 封面图
    ├── article_1.png               # 文章内嵌图片
    └── ...
```

## 🔗 支持的 URL 格式

- `https://x.com/user/status/123456`
- `https://x.com/user/status/123456?s=20` （带参数也支持）
- `https://twitter.com/user/status/123456`
- `https://fxtwitter.com/user/status/123456`
- `https://fixupx.com/user/status/123456`
- `https://vxtwitter.com/user/status/123456`

## 📋 输出 Markdown 示例

### 普通推文

```markdown
# @username (Display Name) 的推文

> 📅 2026-02-26 12:00:00 | ❤️ 1.2K | 🔁 500 | 💬 50 | 👁️ 10K

---

推文正文内容...

![图片描述](username_123456_images/1.jpg)

---
*来源: https://x.com/username/status/123456*
```

### X Article

```markdown
# 文章标题

> ✍️ @username (Display Name)
> 📅 2026-02-26 12:00:00 | ❤️ 6.7K | 🔁 1.9K | 💬 141 | 👁️ 1.8M

![封面](username_123456_images/cover.jpg)

---

## 章节标题

文章正文，包含 **加粗**、*斜体*、[链接](url)、代码块等

---
*来源: https://x.com/username/status/123456*
```

## ⚙️ 技术说明

- 使用 [FxTwitter API](https://github.com/FixTweet/FxTwitter) 获取推文数据
- 无需 API Key 或登录
- 仅 `requests` 一个外部依赖
- X Article 使用 Draft.js 格式解析，支持标题、列表、引用、代码块、图片等
- 图片下载为原始质量

## 🤖 作为 AI Agent Skill 使用 (OpenClaw 等)

本项目自带了一个完整的 Agent Skill（目前已兼容 OpenClaw/ClawdBot 等工具）。使用该 Skill 后，你可以直接在 Telegram 或对话框中命令你的 AI 助理帮你下载推文。

**安装步骤：**

1. 将本仓库克隆到本地。
2. 将仓库内 `.agents/skills/x-downloader` 文件夹复制到你自己的 AI Agent 项目的 `.agents/skills/` 目录下。
3. 如果你的 Agent 不在同一台机器或同个目录，请确保修改 `SKILL.md` 中 Python 脚本的绝对路径，指向你实际的项目路径。
4. 现在你可以对你的 AI Agent 说：
   - *“帮我下载这篇 X 平台的长文章，保存下来：https://x.com/...”*
   - *“把这条推文和它的线程存到本地”*

## 📄 License

MIT
