"""京东校园招聘抓取器
接口: POST https://campus.jd.com/api/wx/position/page?type=present
"""
import requests
from datetime import datetime
from .base import BaseScraper, JobItem
import config


class JdScraper(BaseScraper):
    name = "京东"

    def fetch(self):
        url = "https://campus.jd.com/api/wx/position/page"
        params = {"type": config.COMPANY_CONFIG["京东"]["type"]}
        headers = {
            "Content-Type": "application/json",
            "Referer": "https://campus.jd.com/",
            "Origin": "https://campus.jd.com",
        }
        all_items = []
        page_idx = 0
        while True:
            body = {
                "pageSize": config.PAGE_SIZE,
                "pageIndex": page_idx,
                "parameter": {
                    "positionName": "",
                    "planIdList": [],
                    "jobDirectionCodeList": [],
                    "workCityCodeList": [],
                    "positionDeptList": [],
                },
            }
            r = self.session.post(url, params=params, json=body, headers=headers,
                                  timeout=config.REQUEST_TIMEOUT)
            data = r.json()
            if not data.get("success"):
                raise ValueError("京东岗位接口未返回成功状态")
            items = data["body"]["items"]
            total = data["body"]["totalNumber"]
            all_items.extend(items)
            if len(all_items) >= total or not items:
                break
            page_idx += 1
            if page_idx > 20:
                break
        return [self._parse(it) for it in all_items]

    def _parse(self, it):
        publish_ts = it.get("publishTime")
        publish_time = ""
        if publish_ts:
            publish_time = datetime.fromtimestamp(publish_ts / 1000).strftime("%Y-%m-%d")
        req_id = str(it.get("reqId", ""))
        job_dir = it.get("jobDirection", "")
        return JobItem(
            company=self.name,
            job_id=req_id,
            title=it.get("positionName", "").strip(),
            category=self._category(it, job_dir),
            location=it.get("workCity") or "",
            url=f"https://campus.jd.com/#/jobs?reqId={req_id}",
            publish_time=publish_time,
            tags=job_dir,
        )

    def _category(self, it, job_dir):
        # 京东的 jobDirection 较粗，用 positionDept/workContent 兜底判断
        dept = (it.get("positionDept") or "").strip()
        for kw in config.CATEGORY_KEYWORDS:
            if kw in dept or kw in (it.get("positionName") or ""):
                return kw
        return job_dir or ""
