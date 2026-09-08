"""历史数据存储与新增对比（SQLite）"""
import sqlite3
import os
from datetime import datetime, date
from typing import List, Set
from scrapers.base import JobItem
import config

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jobs.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            company TEXT,
            job_id TEXT,
            title TEXT,
            category TEXT,
            location TEXT,
            url TEXT,
            publish_time TEXT,
            tags TEXT,
            first_seen TEXT,
            last_seen TEXT,
            PRIMARY KEY (company, job_id)
        )
    """)
    return conn


def save_jobs(jobs: List[JobItem]) -> Set[str]:
    """保存岗位，返回本次"新增"的 dedup_key 集合"""
    conn = _get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = date.today().isoformat()
    new_keys = set()
    for job in jobs:
        existing = conn.execute(
            "SELECT first_seen FROM jobs WHERE company=? AND job_id=?",
            (job.company, job.job_id),
        ).fetchone()
        if existing is None:
            # 新增岗位
            conn.execute(
                "INSERT INTO jobs (company,job_id,title,category,location,url,publish_time,tags,first_seen,last_seen) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (job.company, job.job_id, job.title, job.category, job.location,
                 job.url, job.publish_time, job.tags, now, now),
            )
            new_keys.add(job.dedup_key)
        else:
            # 已存在，更新 last_seen 和最新信息
            conn.execute(
                "UPDATE jobs SET title=?,category=?,location=?,url=?,publish_time=?,tags=?,last_seen=? "
                "WHERE company=? AND job_id=?",
                (job.title, job.category, job.location, job.url, job.publish_time,
                 job.tags, now, job.company, job.job_id),
            )
    conn.commit()
    conn.close()
    return new_keys


def get_today_new_jobs() -> List[dict]:
    """获取今天首次发现的岗位"""
    conn = _get_conn()
    today = date.today().isoformat()
    rows = conn.execute(
        "SELECT company,job_id,title,category,location,url,publish_time,tags,first_seen "
        "FROM jobs WHERE first_seen LIKE ? ORDER BY company, first_seen DESC",
        (f"{today}%",),
    ).fetchall()
    conn.close()
    return [dict(zip(
        ["company", "job_id", "title", "category", "location", "url",
         "publish_time", "tags", "first_seen"], row)) for row in rows]


def get_all_jobs_count():
    conn = _get_conn()
    n = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()
    return n


def clear_all():
    """清空所有历史数据（全量初始化用）"""
    conn = _get_conn()
    conn.execute("DELETE FROM jobs")
    conn.commit()
    conn.close()
