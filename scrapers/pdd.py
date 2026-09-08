"""拼多多校园招聘抓取器
接口: POST https://careers.pddglobalhr.com/api/careers/api/recruit/position/list
"""
import requests
from datetime import datetime
from .base import BaseScraper, JobItem
import config


class PddScraper(BaseScraper):
    name = "拼多多"

    def fetch(self):
        url = "https://careers.pddglobalhr.com/api/careers/api/recruit/position/list"
        headers = {
            "Content-Type": "application/json",
            "Referer": "https://careers.pddglobalhr.com/campus/grad",
        }
        t = config.COMPANY_CONFIG["拼多多"]["t"]
        all_items = []
        page = 1
        while True:
            body = {"page": page, "pageSize": config.PAGE_SIZE, "t": t}
            r = self.session.post(url, json=body, headers=headers,
                                  timeout=config.REQUEST_TIMEOUT)
            data = r.json()
            if not data.get("success"):
                raise ValueError("拼多多岗位接口未返回成功状态")
            result = data.get("result", {})
            items = result.get("list", [])
            all_items.extend(items)
            if len(items) < config.PAGE_SIZE or not items:
                break
            page += 1
            if page > 20:
                break
        return [self._parse(it) for it in all_items]

    def _parse(self, it):
        release_ts = it.get("releaseTime")
        publish_time = ""
        if release_ts:
            try:
                publish_time = datetime.fromtimestamp(release_ts / 1000).strftime("%Y-%m-%d")
            except Exception:
                publish_time = str(release_ts)[:10]
        job_id = it.get("id") or it.get("code")
        return JobItem(
            company=self.name,
            job_id=str(job_id),
            title=it.get("name", "").strip(),
            category=it.get("jobName", ""),       # 直接有中文类别名
            location=it.get("workLocationName") or it.get("workLocation") or "",
            url=f"https://careers.pddglobalhr.com/campus/grad/position/detail?id={job_id}",
            publish_time=publish_time,
            tags="云弧计划" if "云弧" in (it.get("name") or "") else "",
        )
