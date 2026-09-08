"""
Campus Radar —— 秋招岗位雷达
每日抓取各官网校招岗位，对比识别新增，生成 Markdown 简报。

用法:
    python main.py            # 跑一次，生成当日简报
    python main.py --full     # 全量抓取但不标记新增（首次初始化用）
"""
import sys
import os
import traceback
import argparse
import json
from datetime import date

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config
from scrapers import SCRAPERS
from scrapers.base import JobItem
import store
import report
import push


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT})
    retry = Retry(total=config.MAX_RETRIES, backoff_factor=1,
                  status_forcelist=[500, 502, 503, 504],
                  allowed_methods=["GET", "POST"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.hooks["response"].append(lambda response, *args, **kwargs: response.raise_for_status())
    return s


def main(argv=None):
    parser = argparse.ArgumentParser(description="香港 / 深圳岗位追踪")
    parser.add_argument("--full", action="store_true", help="仅为新数据库建立基线，不清除历史")
    parser.add_argument("--no-push", action="store_true", help="只保存简报，不推送通知")
    parser.add_argument("--strict", action="store_true", help="任一来源失败时以非零状态退出")
    args = parser.parse_args(argv)
    existing_count = store.get_all_jobs_count()
    if args.full and existing_count:
        parser.error("数据库已有历史记录，请直接运行日常抓取；--full 不会覆盖历史。")
    full_mode = args.full or existing_count == 0
    session = make_session()
    all_jobs = []
    raw_counts = {}
    source_errors = {}

    print("=" * 50)
    print(f"Campus Radar 启动 ｜ 模式: {'全量初始化' if full_mode else '日常抓取'}")
    print("=" * 50)

    for name, cls in SCRAPERS.items():
        if not config.ENABLED_COMPANIES.get(name, True):
            print(f"[{name}] 已跳过（配置关闭）")
            continue
        print(f"\n[{name}] 抓取中...")
        try:
            scraper = cls(session)
            jobs = scraper.fetch()
            all_jobs.extend(jobs)
            raw_counts[name] = len(jobs)
            print(f"  ✅ 获取 {len(jobs)} 个岗位")
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
            traceback.print_exc()
            raw_counts[name] = 0
            source_errors[name] = f"{type(e).__name__}: {e}"

    # 加载通用抓取源（零代码添加的新公司）
    from scrapers.generic import GenericScraper
    for src_cfg in getattr(config, "GENERIC_SOURCES", []):
        if not src_cfg.get("enabled", True):
            continue
        name = src_cfg.get("name", "未知")
        print(f"\n[{name}] 抓取中...(通用抓取器)")
        try:
            scraper = GenericScraper(session, src_cfg)
            jobs = scraper.fetch()
            all_jobs.extend(jobs)
            raw_counts[name] = len(jobs)
            print(f"  ✅ 获取 {len(jobs)} 个岗位")
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
            traceback.print_exc()
            raw_counts[name] = 0
            source_errors[name] = f"{type(e).__name__}: {e}"

    # 保存到数据库
    if full_mode:
        # 新数据库建立基线，不覆盖已有历史。
        store.save_jobs(all_jobs)
        new_keys = set()  # 初始化不报新增
    else:
        new_keys = store.save_jobs(all_jobs)

    total_new = len(new_keys)
    print(f"\n{'=' * 50}")
    print(f"抓取完成：共 {len(all_jobs)} 个岗位，本次新增 {total_new} 个")
    print(f"数据库累计：{store.get_all_jobs_count()} 个岗位")

    # 生成简报
    content = report.generate_brief(all_jobs, new_keys, raw_counts, source_errors)
    target_jobs = report.filter_jobs(all_jobs)
    target_new = sum(job.dedup_key in new_keys for job in target_jobs)
    summary = {
        "date": date.today().isoformat(),
        "initialized": full_mode,
        "target_cities": config.TARGET_CITIES,
        "filter_by_keywords": config.FILTER_BY_KEYWORDS,
        "sources": raw_counts,
        "errors": source_errors,
        "fetched": len(all_jobs),
        "matching": len(target_jobs),
        "new_matching": target_new,
    }
    with open(os.path.join(report.REPORT_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    today = date.today().isoformat()
    report_path = os.path.join("reports", f"{today}.md")
    print(f"\n📄 简报已生成：{report_path}")
    print("=" * 50)

    # 推送简报到微信等渠道（需配置环境变量）
    print("\n📤 推送简报...")
    today_str = date.today().isoformat()
    if full_mode:
        push_title = f"秋招雷达 {today_str} ｜ 初始化"
    elif target_new > 0:
        push_title = f"🆕 秋招雷达 {today_str} ｜ {target_new}个新岗位!"
    else:
        push_title = f"秋招雷达 {today_str} ｜ 无新增"
    if source_errors:
        push_title += f" ｜ {len(source_errors)}个来源异常"
    if not args.no_push and (target_new or source_errors):
        push.send_brief(content, title=push_title)
    else:
        print("本次不发送通知；简报已保存。")
    session.close()
    if args.strict and source_errors:
        raise SystemExit(1)
    return content


if __name__ == "__main__":
    main()
