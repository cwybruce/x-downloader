#!/usr/bin/env python3
"""
X (Twitter) 文章下载工具

将 X 平台的推文/文章链接下载为本地 Markdown 文件，
图片独立保存到文件夹中并在 Markdown 中引用。

Usage:
    python x_downloader.py <tweet_url> [--output-dir <dir>]
    python x_downloader.py "https://x.com/user/status/123456"
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("❌ 缺少依赖: requests")
    print("   请运行: pip install requests")
    sys.exit(1)


# ============================================================
# 1. URL 解析
# ============================================================

# 支持的 URL 域名
SUPPORTED_DOMAINS = [
    "x.com",
    "twitter.com",
    "mobile.twitter.com",
    "fxtwitter.com",
    "fixupx.com",
    "vxtwitter.com",
    "nitter.net",
]

# 匹配 /user/status/ID 或 /i/status/ID
STATUS_PATTERN = re.compile(r"/(?:[\w]+)/status(?:es)?/(\d+)")


def parse_tweet_url(url: str) -> tuple[str, str]:
    """
    从 X/Twitter URL 中解析出 screen_name 和 tweet_id.

    Returns:
        (screen_name, tweet_id)

    Raises:
        ValueError: 如果 URL 格式无效
    """
    url = url.strip()

    # 确保有 scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    domain = parsed.hostname

    if not domain:
        raise ValueError(f"无法解析 URL: {url}")

    # 去掉 www. 前缀
    domain = domain.lstrip("www.")

    if domain not in SUPPORTED_DOMAINS:
        raise ValueError(
            f"不支持的域名: {domain}\n"
            f"支持的域名: {', '.join(SUPPORTED_DOMAINS)}"
        )

    match = STATUS_PATTERN.search(parsed.path)
    if not match:
        raise ValueError(f"URL 中未找到推文 ID: {url}")

    tweet_id = match.group(1)

    # 提取 screen_name（路径第一段）
    path_parts = parsed.path.strip("/").split("/")
    screen_name = path_parts[0] if path_parts else "unknown"

    return screen_name, tweet_id


# ============================================================
# 2. FxTwitter API 数据获取
# ============================================================

FXTWITTER_API = "https://api.fxtwitter.com"

# 请求头，模拟正常浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def fetch_tweet(tweet_id: str, screen_name: str = "i") -> dict:
    """
    通过 FxTwitter API 获取推文数据。

    Args:
        tweet_id: 推文 ID
        screen_name: 用户名（用 'i' 也可以）

    Returns:
        推文数据字典
    """
    url = f"{FXTWITTER_API}/{screen_name}/status/{tweet_id}"
    print(f"📡 正在获取推文数据: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            "⚠️  无法连接到 FxTwitter API。请检查网络连接或使用代理。"
        )
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            raise ValueError(f"推文不存在或已被删除 (ID: {tweet_id})")
        raise ConnectionError(f"API 请求失败: {e}")

    data = resp.json()

    if data.get("code") != 200:
        raise ValueError(
            f"API 返回错误: {data.get('message', '未知错误')}"
        )

    return data.get("tweet", {})


# ============================================================
# 3. 图片下载
# ============================================================


def download_image(url: str, save_path: Path) -> bool:
    """
    下载单张图片到指定路径。

    Returns:
        True 如果下载成功
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        resp.raise_for_status()

        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        size_kb = save_path.stat().st_size / 1024
        print(f"   ✅ 已下载: {save_path.name} ({size_kb:.1f} KB)")
        return True

    except Exception as e:
        print(f"   ❌ 下载失败 {save_path.name}: {e}")
        return False


def download_tweet_images(
    tweet_data: dict, images_dir: Path
) -> list[dict]:
    """
    下载推文中的所有图片。

    Returns:
        下载结果列表: [{"url": ..., "local_path": ..., "filename": ...}, ...]
    """
    media_list = tweet_data.get("media", {})
    if not media_list:
        # 尝试另一种格式
        media_list = tweet_data.get("medias", [])

    photos = []

    # media 可能是 dict 含 photos 列表，也可能是 list
    if isinstance(media_list, dict):
        photos = media_list.get("photos", [])
        # 如果 all 字段下有更多信息
        all_media = media_list.get("all", [])
        if not photos and all_media:
            photos = [m for m in all_media if m.get("type") == "photo"]
    elif isinstance(media_list, list):
        photos = [m for m in media_list if m.get("type") == "photo"]

    if not photos:
        print("📷 该推文没有图片")
        return []

    print(f"📷 发现 {len(photos)} 张图片，开始下载...")

    results = []
    for i, photo in enumerate(photos, 1):
        img_url = photo.get("url", "")
        if not img_url:
            continue

        # 从 URL 提取文件扩展名
        ext = _get_image_extension(img_url)
        filename = f"{i}{ext}"
        save_path = images_dir / filename

        if download_image(img_url, save_path):
            results.append({
                "url": img_url,
                "local_path": str(save_path),
                "filename": filename,
                "alt": photo.get("altText", f"图片{i}"),
            })

    return results


def _get_image_extension(url: str) -> str:
    """从 URL 中提取图片扩展名"""
    # Twitter 图片 URL 格式:
    # https://pbs.twimg.com/media/xxx.jpg
    # https://pbs.twimg.com/media/xxx?format=jpg&name=large
    parsed = urlparse(url)
    path = parsed.path

    # 直接从路径获取扩展名
    _, ext = os.path.splitext(path)
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        return ext

    # 从查询参数获取
    if "format=" in url:
        match = re.search(r"format=(\w+)", url)
        if match:
            return f".{match.group(1)}"

    return ".jpg"  # 默认


# ============================================================
# 4. X Article (长文章) 解析
# ============================================================


def convert_article_to_markdown(
    article: dict,
    entity_map: list,
    images_dir: Path,
    images_dir_name: str,
    media_url_map: dict | None = None,
) -> tuple[str, int]:
    """
    将 X Article 的 Draft.js blocks 转换为 Markdown。

    Returns:
        (markdown_text, downloaded_image_count)
    """
    content = article.get("content", {})
    blocks = content.get("blocks", [])

    # 构建 entity map 索引 (key -> value)
    entity_dict = {}
    if isinstance(entity_map, list):
        for item in entity_map:
            entity_dict[str(item.get("key", ""))] = item.get("value", {})
    elif isinstance(entity_map, dict):
        entity_dict = entity_map

    lines = []
    img_counter = 0
    list_counter = 0
    prev_type = ""

    for block in blocks:
        block_type = block.get("type", "unstyled")
        text = block.get("text", "")
        entity_ranges = block.get("entityRanges", [])
        inline_styles = block.get("inlineStyleRanges", [])

        # 应用内联样式 (Bold, Italic)
        styled_text = _apply_inline_styles(text, inline_styles)

        # 应用 entity（链接等）
        styled_text = _apply_entities(styled_text, text, entity_ranges, entity_dict)

        # 列表计数器管理
        if block_type != "ordered-list-item":
            list_counter = 0

        # 块类型分隔
        if prev_type in ("ordered-list-item", "unordered-list-item") and \
           block_type not in ("ordered-list-item", "unordered-list-item"):
            lines.append("")  # 列表结束后空行

        if block_type == "header-one":
            lines.append(f"# {styled_text}")
            lines.append("")
        elif block_type == "header-two":
            lines.append(f"## {styled_text}")
            lines.append("")
        elif block_type == "header-three":
            lines.append(f"### {styled_text}")
            lines.append("")
        elif block_type == "ordered-list-item":
            list_counter += 1
            lines.append(f"{list_counter}. {styled_text}")
        elif block_type == "unordered-list-item":
            lines.append(f"- {styled_text}")
        elif block_type == "blockquote":
            lines.append(f"> {styled_text}")
            lines.append("")
        elif block_type == "atomic":
            # 原子块：代码块、图片等
            result = _render_atomic_block(entity_ranges, entity_dict,
                                          images_dir, images_dir_name,
                                          img_counter, media_url_map)
            if result:
                md_text, new_imgs = result
                lines.append(md_text)
                lines.append("")
                img_counter += new_imgs
        elif block_type == "unstyled":
            if styled_text.strip():
                lines.append(styled_text)
                lines.append("")
            else:
                lines.append("")
        else:
            # 未知类型，当作普通文本
            if styled_text.strip():
                lines.append(styled_text)
                lines.append("")

        prev_type = block_type

    return "\n".join(lines), img_counter


def _apply_inline_styles(text: str, styles: list) -> str:
    """应用内联样式（Bold, Italic）到文本"""
    if not styles or not text:
        return text

    # 按 offset 降序排列，从后向前替换避免偏移错误
    sorted_styles = sorted(styles, key=lambda s: s["offset"], reverse=True)

    chars = list(text)
    for style in sorted_styles:
        offset = style.get("offset", 0)
        length = style.get("length", 0)
        style_type = style.get("style", "")

        if offset + length > len(chars):
            continue

        segment = "".join(chars[offset:offset + length])

        if style_type == "Bold":
            replacement = f"**{segment}**"
        elif style_type == "Italic":
            replacement = f"*{segment}*"
        else:
            replacement = segment

        chars[offset:offset + length] = list(replacement)

    return "".join(chars)


def _apply_entities(styled_text: str, original_text: str,
                    entity_ranges: list, entity_dict: dict) -> str:
    """应用实体（链接等）到文本"""
    if not entity_ranges:
        return styled_text

    for er in sorted(entity_ranges, key=lambda e: e.get("offset", 0), reverse=True):
        key = str(er.get("key", ""))
        entity = entity_dict.get(key, {})
        entity_type = entity.get("type", "")
        entity_data = entity.get("data", {})

        if entity_type == "LINK":
            url = entity_data.get("url", "")
            offset = er.get("offset", 0)
            length = er.get("length", 0)
            link_text = original_text[offset:offset + length]
            if link_text and url:
                styled_text = styled_text.replace(
                    link_text, f"[{link_text}]({url})", 1
                )
        # TWEMOJI 不处理，保留原文 emoji

    return styled_text


def _render_atomic_block(entity_ranges: list, entity_dict: dict,
                         images_dir: Path, images_dir_name: str,
                         img_counter: int,
                         media_url_map: dict | None = None,
                         ) -> tuple[str, int] | None:
    """渲染原子块（代码块、图片等）"""
    if not entity_ranges:
        return None

    er = entity_ranges[0]
    key = str(er.get("key", ""))
    entity = entity_dict.get(key, {})
    entity_type = entity.get("type", "")
    entity_data = entity.get("data", {})

    if entity_type == "MARKDOWN":
        # 代码块
        md_content = entity_data.get("markdown", "")
        return md_content.strip(), 0

    elif entity_type == "IMAGE":
        # 文章内嵌图片（直接含 URL）
        img_url = entity_data.get("src", "") or entity_data.get("url", "")
        if img_url:
            img_counter += 1
            ext = _get_image_extension(img_url)
            filename = f"article_{img_counter}{ext}"
            save_path = images_dir / filename
            if download_image(img_url, save_path):
                alt = entity_data.get("alt", f"文章图片{img_counter}")
                return f"![{alt}]({images_dir_name}/{filename})", 1
        return None

    elif entity_type == "MEDIA":
        # 媒体内容：通过 mediaItems -> mediaId 查找 URL
        img_url = ""
        caption = entity_data.get("caption", "")

        # 方式1：通过 media_url_map 查找（mediaItems -> mediaId）
        media_items = entity_data.get("mediaItems", [])
        if media_items and media_url_map:
            media_id = media_items[0].get("mediaId", "")
            img_url = media_url_map.get(str(media_id), "")

        # 方式2：直接从 media_info 获取
        if not img_url:
            media_info = entity_data.get("media_info", {})
            img_url = media_info.get("original_img_url", "")

        if img_url:
            img_counter += 1
            ext = _get_image_extension(img_url)
            filename = f"article_{img_counter}{ext}"
            save_path = images_dir / filename
            if download_image(img_url, save_path):
                alt = caption.strip() if caption else f"文章图片{img_counter}"
                return f"![{alt}]({images_dir_name}/{filename})", 1
        return None

    return None


def generate_article_markdown(
    tweet_data: dict,
    article: dict,
    images_dir: Path,
    images_dir_name: str,
    original_url: str,
) -> tuple[str, int]:
    """
    将 X Article 转为完整 Markdown。

    Returns:
        (markdown_text, total_image_count)
    """
    author = tweet_data.get("author", {})
    author_name = author.get("name", "Unknown")
    author_screen = author.get("screen_name", "unknown")

    title = article.get("title", "")
    created_at = article.get("created_at", "")
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            created_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            pass

    likes = format_number(tweet_data.get("likes", 0))
    retweets = format_number(tweet_data.get("retweets", 0))
    replies = format_number(tweet_data.get("replies", 0))
    views = format_number(tweet_data.get("views", 0))

    lines = []

    # 标题
    if title:
        lines.append(f"# {title}")
    else:
        lines.append(f"# @{author_screen} 的文章")
    lines.append("")

    # 作者和元信息
    lines.append(f"> ✍️ @{author_screen} ({author_name})")
    lines.append(f"> 📅 {created_at} | "
                 f"❤️ {likes} | "
                 f"🔁 {retweets} | "
                 f"💬 {replies} | "
                 f"👁️ {views}")
    lines.append("")

    # 封面图
    cover = article.get("cover_media", {})
    cover_img_count = 0
    if cover:
        media_info = cover.get("media_info", {})
        cover_url = media_info.get("original_img_url", "")
        if cover_url:
            ext = _get_image_extension(cover_url)
            filename = f"cover{ext}"
            save_path = images_dir / filename
            print(f"📷 下载封面图片...")
            if download_image(cover_url, save_path):
                lines.append(f"![封面]({images_dir_name}/{filename})")
                lines.append("")
                cover_img_count = 1

    lines.append("---")
    lines.append("")

    # 构建 media_id -> URL 查找表
    media_url_map = {}
    for me in article.get("media_entities", []):
        mid = str(me.get("media_id", ""))
        info = me.get("media_info", {})
        url = info.get("original_img_url", "")
        if mid and url:
            media_url_map[mid] = url

    if media_url_map:
        print(f"📷 发现 {len(media_url_map)} 张文章内嵌图片，开始下载...")

    # 文章正文
    content = article.get("content", {})
    entity_map = content.get("entityMap", [])

    article_md, article_img_count = convert_article_to_markdown(
        article, entity_map, images_dir, images_dir_name, media_url_map
    )
    lines.append(article_md)

    # 来源
    lines.append("")
    lines.append("---")
    lines.append("")
    tweet_url = tweet_data.get("url", original_url)
    lines.append(f"*来源: [{tweet_url}]({tweet_url})*")
    lines.append("")

    total_images = cover_img_count + article_img_count
    return "\n".join(lines), total_images


# ============================================================
# 5. Markdown 生成 (普通推文)
# ============================================================


def format_number(num) -> str:
    """格式化数字: 1200 -> 1.2K"""
    if num is None:
        return "0"
    if isinstance(num, str):
        try:
            num = int(num)
        except ValueError:
            return num
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def format_tweet_date(date_str: str) -> str:
    """格式化推文日期"""
    if not date_str:
        return "未知日期"
    try:
        # FxTwitter 返回的日期格式: "Wed Oct 10 20:19:24 +0000 2018"
        dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return date_str


def generate_markdown(
    tweet_data: dict,
    images: list[dict],
    images_dir_name: str,
    original_url: str,
) -> str:
    """
    将推文数据转为 Markdown 格式字符串。
    """
    author = tweet_data.get("author", {})
    author_name = author.get("name", "Unknown")
    author_screen = author.get("screen_name", "unknown")
    author_avatar = author.get("avatar_url", "")

    tweet_text = tweet_data.get("text", "")
    created_at = format_tweet_date(tweet_data.get("created_at", ""))
    tweet_url = tweet_data.get("url", original_url)

    likes = format_number(tweet_data.get("likes", 0))
    retweets = format_number(tweet_data.get("retweets", 0))
    replies = format_number(tweet_data.get("replies", 0))
    views = format_number(tweet_data.get("views", 0))

    lines = []

    # 标题
    lines.append(f"# @{author_screen} ({author_name}) 的推文\n")

    # 元信息
    lines.append(f"> 📅 {created_at} | "
                 f"❤️ {likes} | "
                 f"🔁 {retweets} | "
                 f"💬 {replies} | "
                 f"👁️ {views}\n")

    lines.append("---\n")

    # 正文
    if tweet_text:
        lines.append(f"{tweet_text}\n")

    # 图片
    if images:
        lines.append("")
        for img in images:
            alt = img.get("alt", "图片")
            rel_path = f"{images_dir_name}/{img['filename']}"
            lines.append(f"![{alt}]({rel_path})\n")

    # 视频提示
    media = tweet_data.get("media", {})
    videos = []
    if isinstance(media, dict):
        videos = media.get("videos", [])
    if videos:
        lines.append("\n> 🎬 该推文包含视频，请访问原文查看\n")

    # 引用推文
    quote = tweet_data.get("quote")
    if quote:
        lines.append("\n---\n")
        lines.append("### 引用推文\n")
        quote_author = quote.get("author", {})
        quote_screen = quote_author.get("screen_name", "unknown")
        quote_text = quote.get("text", "")
        lines.append(f"> **@{quote_screen}**: {quote_text}\n")

    # 来源
    lines.append("\n---\n")
    lines.append(f"*来源: [{tweet_url}]({tweet_url})*\n")

    return "\n".join(lines)


# ============================================================
# 6. Thread（推文串）支持
# ============================================================


def fetch_thread(tweet_data: dict, screen_name: str) -> list[dict]:
    """
    尝试获取推文所在的 Thread.

    简单策略: 如果推文有 replying_to 且回复自己的推文，
    则向上追溯获取整个 thread。

    Returns:
        Thread 中所有推文的列表（按时间升序）
    """
    thread = [tweet_data]

    # 检查是否有对话 / thread 信息
    # FxTwitter API 中 conversation 相关字段
    replying_to = tweet_data.get("replying_to")
    tweet_author = tweet_data.get("author", {}).get("screen_name", "")

    if not replying_to:
        return thread

    # 如果是回复自己的推文，尝试向上追溯 (最多20条)
    current = tweet_data
    visited = {tweet_data.get("id")}
    max_depth = 20

    for _ in range(max_depth):
        reply_id = current.get("replying_to_status")
        if not reply_id or reply_id in visited:
            break

        try:
            parent = fetch_tweet(reply_id, screen_name)
            parent_author = parent.get("author", {}).get("screen_name", "")

            # 只追溯同一作者的 thread
            if parent_author.lower() != tweet_author.lower():
                break

            visited.add(reply_id)
            thread.insert(0, parent)  # 插入到最前面
            current = parent
            time.sleep(0.5)  # 避免请求过快

        except Exception:
            break

    if len(thread) > 1:
        print(f"🧵 发现 Thread，共 {len(thread)} 条推文")

    return thread


# ============================================================
# 7. 主流程
# ============================================================


def download_tweet(
    url: str,
    output_dir: str = "output",
    include_thread: bool = True,
) -> str:
    """
    主函数：下载推文并保存为 Markdown。

    Args:
        url: X/Twitter 推文链接
        output_dir: 输出目录
        include_thread: 是否尝试获取整个 Thread

    Returns:
        生成的 Markdown 文件路径
    """
    print(f"\n{'='*50}")
    print(f"🔗 X 文章下载工具")
    print(f"{'='*50}\n")

    # 1. 解析 URL
    screen_name, tweet_id = parse_tweet_url(url)
    print(f"👤 用户: @{screen_name}")
    print(f"🆔 推文 ID: {tweet_id}\n")

    # 2. 获取推文数据
    tweet_data = fetch_tweet(tweet_id, screen_name)

    # 实际作者可能与 URL 中的不同
    actual_author = tweet_data.get("author", {}).get("screen_name", screen_name)

    # 3. 构建输出路径
    output_path = Path(output_dir)
    base_name = f"{actual_author}_{tweet_id}"
    md_path = output_path / f"{base_name}.md"
    images_dir = output_path / f"{base_name}_images"
    images_dir_name = f"{base_name}_images"

    output_path.mkdir(parents=True, exist_ok=True)

    # 4. 检查是否为 X Article (长文章)
    article = tweet_data.get("article")
    if article and article.get("content"):
        print(f"📰 检测到 X Article: {article.get('title', '无标题')}")
        final_md, total_images = generate_article_markdown(
            tweet_data, article, images_dir, images_dir_name, url
        )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(final_md)

        print(f"\n{'='*50}")
        print(f"✅ 下载完成!")
        print(f"📄 Markdown: {md_path}")
        if total_images > 0:
            print(f"📷 图片目录: {images_dir} ({total_images} 张)")
        print(f"{'='*50}\n")
        return str(md_path)

    # 5. 普通推文：获取 Thread（可选）
    if include_thread:
        tweets = fetch_thread(tweet_data, actual_author)
    else:
        tweets = [tweet_data]

    # 6. 处理每条推文
    all_md_parts = []
    total_images = 0

    for idx, tweet in enumerate(tweets):
        if len(tweets) > 1:
            print(f"\n--- 推文 {idx + 1}/{len(tweets)} ---")

        # 下载图片
        images = download_tweet_images(tweet, images_dir)
        total_images += len(images)

        # 生成 Markdown
        md_content = generate_markdown(
            tweet, images, images_dir_name, url
        )

        if len(tweets) > 1 and idx > 0:
            # Thread 中的后续推文用分隔线连接
            all_md_parts.append("\n---\n---\n")

        all_md_parts.append(md_content)

    # 7. 合并并写入文件
    final_md = "\n".join(all_md_parts)

    # 如果是 Thread，更新标题
    if len(tweets) > 1:
        first_line = final_md.split("\n")[0]
        final_md = final_md.replace(
            first_line,
            f"# @{actual_author} 的推文串 (Thread, 共 {len(tweets)} 条)",
            1,
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(final_md)

    # 8. 完成报告
    print(f"\n{'='*50}")
    print(f"✅ 下载完成!")
    print(f"📄 Markdown: {md_path}")
    if total_images > 0:
        print(f"📷 图片目录: {images_dir} ({total_images} 张)")
    print(f"{'='*50}\n")

    return str(md_path)


# ============================================================
# 8. CLI 入口
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="X (Twitter) 文章下载工具 - 将推文保存为 Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python x_downloader.py "https://x.com/elonmusk/status/123456"
  python x_downloader.py "https://twitter.com/user/status/789" -o my_tweets
  python x_downloader.py "https://x.com/user/status/123" --no-thread
        """,
    )

    parser.add_argument(
        "url",
        help="X/Twitter 推文链接",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="output",
        help="输出目录 (默认: output)",
    )
    parser.add_argument(
        "--no-thread",
        action="store_true",
        help="不获取 Thread，只下载单条推文",
    )

    args = parser.parse_args()

    try:
        download_tweet(
            url=args.url,
            output_dir=args.output_dir,
            include_thread=not args.no_thread,
        )
    except ValueError as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)
    except ConnectionError as e:
        print(f"\n❌ 网络错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹ 已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 意外错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
