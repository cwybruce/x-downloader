---
name: x-downloader
description: 下载 X (Twitter) 推文/文章到本地 Markdown 文件，含图片
---

# X (Twitter) 文章下载 Skill

将 X 平台的推文或长文章链接下载为本地 `.md` 文件，图片独立保存并引用。

## 使用前提

1. Python 3.10+ 已安装
2. `requests` 库已安装（或使用项目自带的 venv）

## 脚本位置

```
/Volumes/ex-ssd1/web3-learning2026/yd-35期/01-openclaw/x-文档下载工具/x_downloader.py
```

## 执行步骤

### 1. 激活虚拟环境

```bash
source /Volumes/ex-ssd1/web3-learning2026/yd-35期/01-openclaw/x-文档下载工具/.venv/bin/activate
```

### 2. 运行下载

```bash
python /Volumes/ex-ssd1/web3-learning2026/yd-35期/01-openclaw/x-文档下载工具/x_downloader.py "<X推文链接>" -o <输出目录>
```

**参数说明:**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `url` | X/Twitter 推文链接（必填） | — |
| `-o` | 输出目录 | `output` |
| `--no-thread` | 不获取 Thread | — |

### 3. 查看结果

下载完成后会在输出目录生成：
- `<用户名>_<ID>.md` — Markdown 文件
- `<用户名>_<ID>_images/` — 图片文件夹（如有图片）

## 支持的内容类型

| 类型 | 说明 |
|------|------|
| 普通推文 | 文本 + 图片 + 统计数据 |
| X Article | 长文章完整转换（标题/列表/代码块/封面图等） |
| Thread | 自动追溯同一作者的推文串 |
| 引用推文 | 嵌入引用的推文内容 |

## 使用示例

```bash
# 示例 1: 下载普通推文
python /Volumes/ex-ssd1/web3-learning2026/yd-35期/01-openclaw/x-文档下载工具/x_downloader.py "https://x.com/jack/status/20" -o ./downloads

# 示例 2: 下载 X Article（自动识别）
python /Volumes/ex-ssd1/web3-learning2026/yd-35期/01-openclaw/x-文档下载工具/x_downloader.py "https://x.com/stark_nico99/status/2026235176150581282"

# 示例 3: 只下载单条（不获取 Thread）
python /Volumes/ex-ssd1/web3-learning2026/yd-35期/01-openclaw/x-文档下载工具/x_downloader.py "https://x.com/user/status/ID" --no-thread
```

## 常见问题

- **推文不存在**: 确认链接是否有效，私人推文无法下载
- **网络超时**: 检查网络连接，FxTwitter API 需要能访问外网
- **没有图片**: 如果推文/文章不含图片，不会创建 images 文件夹

## 技术细节

- 数据源: FxTwitter API（免费、无需 API Key）
- 文章解析: Draft.js blocks → Markdown
- 图片质量: 原始分辨率
