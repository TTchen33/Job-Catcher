"""简报生成模块（Markdown）"""
import os
import re
from datetime import datetime, date
from typing import List
from scrapers.base import JobItem
import config


REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")


def _match_keywords(job: JobItem) -> bool:
    """判断岗位是否命中产品运营关键词"""
    if not config.FILTER_BY_KEYWORDS:
        return True
    text = f"{job.title} {job.category} {job.tags}"
    # 优先按类别命中
    for cat_kw in config.CATEGORY_KEYWORDS:
        if cat_kw in job.category:
            return True
    # 再按标题关键词兜底
    all_kw = []
    for kws in config.KEYWORDS.values():
        all_kw.extend(kws)
    return any(kw in text for kw in all_kw)


def _enrich_category(job: JobItem) -> JobItem:
    """如果 category 不含关注方向关键词，用 guess_category 补充"""
    from scrapers.base import guess_category
    # 检查现有 category 是否已包含关注方向
    has_focus = any(kw in job.category for kw in config.CATEGORY_KEYWORDS)
    if not has_focus:
        guessed = guess_category(job.title)
        # 只保留关注方向的类别（产品/运营/电商），不追加技术等
        focus_cats = [c for c in guessed.split("、") if c in config.KEYWORDS.keys()]
        if focus_cats:
            existing = [c for c in job.category.split("、") if c] if job.category else []
            # 合并去重
            merged = list(dict.fromkeys(focus_cats + existing))
            job.category = "、".join(merged)
    return job


def _match_city(job: JobItem) -> bool:
    """判断岗位是否在目标城市（空配置=不限）"""
    if not config.TARGET_CITIES:
        return True
    loc = (job.location or "").strip()
    if config.INCLUDE_UNSPECIFIED_LOCATIONS and (
        not loc or any(word in loc for word in ["全国", "全國", "多地"])
    ):
        return True
    for city in config.TARGET_CITIES:
        for alias in config.CITY_ALIASES.get(city, [city]):
            if alias.isascii():
                # 避免 HK 匹配到另一个地名内部；忽略英文大小写与多余空格。
                pattern = r"(?<![a-zA-Z])" + r"\s*".join(
                    re.escape(part) for part in alias.split()
                ) + r"(?![a-zA-Z])"
                if re.search(pattern, loc, re.IGNORECASE):
                    return True
            elif alias in loc:
                return True
    return False


def filter_jobs(jobs: List[JobItem]) -> List[JobItem]:
    """按关键词+城市过滤岗位"""
    result = []
    for j in jobs:
        _enrich_category(j)
        if _match_keywords(j) and _match_city(j):
            result.append(j)
    return result


def generate_brief(jobs: List[JobItem], new_keys: set, all_raw_count: dict,
                   source_errors: dict = None) -> str:
    """生成当日 Markdown 简报"""
    today = date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 过滤出目标岗位
    target_jobs = filter_jobs(jobs)
    # 标记新增
    for j in target_jobs:
        j._is_new = j.dedup_key in new_keys

    new_jobs = [j for j in target_jobs if getattr(j, "_is_new", False)]
    existing_jobs = [j for j in target_jobs if not getattr(j, "_is_new", False)]

    lines = []
    lines.append(f"# 📋 秋招雷达日报 · {today}")
    lines.append("")
    focus = " / ".join(config.KEYWORDS) if config.FILTER_BY_KEYWORDS else "不限岗位方向"
    lines.append(f"> 自动抓取于 {now} ｜ 关注方向：{focus} ｜ 目标城市：{('、'.join(config.TARGET_CITIES)) or '不限'}")
    lines.append("")
    if config.INCLUDE_UNSPECIFIED_LOCATIONS:
        lines.append("> 地点为空、全国或多地的岗位也会保留，需在官网确认是否开放香港或深圳。")
        lines.append("")
    if source_errors:
        lines.append("## ⚠️ 抓取异常")
        lines.append("")
        for name, error in source_errors.items():
            lines.append(f"- {name}：{error}")
        lines.append("")
        lines.append("这些来源本次未完成检查，不能据此判断没有新增岗位。")
        lines.append("")

    # 公司排序：官网优先，offerstar 最后
    company_order = ["京东", "快手", "小红书", "拼多多", "淘宝", "offerstar"]
    def _sort_key(name):
        if name in company_order:
            return (0, company_order.index(name))
        return (1, name)  # 未知公司排在最后

    sorted_companies = sorted(all_raw_count.keys(), key=_sort_key)

    # 总览
    lines.append("## 📊 今日总览")
    lines.append("")
    lines.append("| 公司 | 抓取岗位总数 | 命中方向 | 今日新增 |")
    lines.append("|------|------------|---------|---------|")
    for company in sorted_companies:
        cnt = all_raw_count[company]
        def belongs(job):
            return job.company == company or (
                company == "offerstar" and job.company.startswith("offerstar·")
            )
        hit = sum(belongs(j) for j in target_jobs)
        new = sum(belongs(j) for j in new_jobs)
        count_label = "失败" if company in (source_errors or {}) else cnt
        lines.append(f"| {company} | {count_label} | {hit} | {new if new else '-'} |")
    lines.append("")

    # 投递进度概览
    app_section = _build_application_section() if config.INCLUDE_APPLICATION_PROGRESS else None
    if app_section:
        lines.extend(app_section)

    # 新增岗位
    if new_jobs:
        lines.append("## 🆕 今日新增岗位")
        lines.append("")
        by_company = {}
        for j in new_jobs:
            by_company.setdefault(j.company, []).append(j)
        for company in sorted(by_company.keys(), key=_sort_key):
            lines.append(f"### {company}")
            lines.append("")
            lines.append("| 岗位名称 | 类别 | 地点 | 发布时间 | 标签 | 链接 |")
            lines.append("|---------|------|------|---------|------|------|")
            for j in by_company[company]:
                link = f"[查看]({j.url})" if j.url else "-"
                lines.append(
                    f"| {j.title} | {j.category or '-'} | {j.location or '-'} | "
                    f"{j.publish_time or '-'} | {j.tags or '-'} | {link} |"
                )
            lines.append("")
    else:
        lines.append("## 🆕 今日新增岗位")
        lines.append("")
        lines.append("本次成功抓取的来源中暂无新增目标岗位。首次运行仅建立基线；之后的检查会列出新发现的岗位。")
        lines.append("")

    # 在招岗位存量（命中的，便于随时查阅）
    if existing_jobs:
        lines.append(f"## 📌 本次抓取到的存量岗位（{focus}）")
        lines.append("")
        lines.append("<details><summary>点击展开全部在招岗位</summary>")
        lines.append("")
        by_company = {}
        for j in existing_jobs:
            by_company.setdefault(j.company, []).append(j)
        for company in sorted(by_company.keys(), key=_sort_key):
            lines.append(f"**{company}**")
            lines.append("")
            for j in by_company[company]:
                link = f"[查看]({j.url})" if j.url else ""
                tag_str = f"`{j.tags}`" if j.tags else ""
                lines.append(f"- {j.title} ｜ {j.category or ''} ｜ {j.location or ''} ｜ {j.publish_time or ''} {tag_str} {link}")
            lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("---")
    lines.append("*由 Job-Catcher（基于 Campus Radar）生成。0 岗位也可能由接口变化引起；投递前请以官网详情和截止日期为准。*")

    content = "\n".join(lines)

    # 写文件
    os.makedirs(REPORT_DIR, exist_ok=True)
    filepath = os.path.join(REPORT_DIR, f"{today}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    with open(os.path.join(REPORT_DIR, "latest.md"), "w", encoding="utf-8") as f:
        f.write(content)
    return content


def _build_application_section():
    """构建投递进度概览（插入每日简报里）"""
    try:
        import sqlite3
        conn = sqlite3.connect(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "applications.db"))
        rows = conn.execute("""
            SELECT company, position, status, apply_date, feedback, next_step
            FROM applications ORDER BY update_time DESC
        """).fetchall()
        conn.close()
    except Exception:
        return None
    if not rows:
        return None

    total = len(rows)
    # 按状态分组
    by_status = {}
    for r in rows:
        by_status.setdefault(r[2] or "未知", []).append(r)
    # 进展中的（非终态）
    in_progress = [r for r in rows if r[2] in ("笔试", "一面", "二面", "三面", "HR面")]
    offers = [r for r in rows if r[2] == "Offer"]
    rejected = [r for r in rows if r[2] in ("已拒", "已放弃")]

    lines = []
    lines.append("## 📬 我的投递进度")
    lines.append("")
    lines.append(f"> 共投递 **{total}** 个岗位 ｜ 进行中 **{len(in_progress)}** ｜ Offer **{len(offers)}** ｜ 已结束 **{len(rejected)}**")
    lines.append("")

    # 状态分布条
    status_order = ["待投递", "已投递", "笔试", "一面", "二面", "三面", "HR面", "Offer", "已拒", "已放弃"]
    parts = []
    for s in status_order:
        if s in by_status:
            parts.append(f"`{s}: {len(by_status[s])}`")
    if parts:
        lines.append("  ".join(parts))
        lines.append("")

    # 近期需要关注的（有下一步动作 或 进行中）
    focus = [r for r in rows if r[2] in ("笔试", "一面", "二面", "三面", "HR面") or r[5]]
    if focus:
        lines.append("<details><summary>📍 需关注（进行中 / 有待办）</summary>")
        lines.append("")
        lines.append("| 公司 | 岗位 | 状态 | 投递日期 | 反馈 | 下一步 |")
        lines.append("|------|------|------|---------|------|--------|")
        for r in focus[:15]:
            lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3] or '-'} | {r[4] or '-'} | {r[5] or '-'} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # Offer 列表（如果有）
    if offers:
        lines.append("### 🎉 已获 Offer")
        lines.append("")
        for r in offers:
            lines.append(f"- **{r[0]}** - {r[1]} （{r[3]}）")
        lines.append("")

    return lines
