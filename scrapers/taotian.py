"""淘宝(淘天集团)校园招聘抓取器
接口: POST https://talent.taotian.com/position/search
需要先获取 CSRF token 和 batchId
"""
import requests
from datetime import datetime
from .base import BaseScraper, JobItem, guess_category
import config


class TaotianScraper(BaseScraper):
    name = "淘宝"

    BASE = "https://talent.taotian.com"

    def fetch(self):
        headers = {
            "Content-Type": "application/json",
            "Referer": f"{self.BASE}/campus/position",
            "Origin": self.BASE,
            "User-Agent": config.USER_AGENT,
        }
        # 1. 访问页面拿 CSRF token (cookie 里的 XSRF-TOKEN)
        self.session.get(f"{self.BASE}/campus/position",
                         headers={"User-Agent": config.USER_AGENT},
                         timeout=config.REQUEST_TIMEOUT)
        csrf = self.session.cookies.get("XSRF-TOKEN") or ""
        if not csrf:
            # 兜底：从页面 meta 里找
            csrf = self._extract_csrf_from_html()

        # 2. 获取 batchId（应届生招聘批次）
        batch_id = self._get_batch_id(csrf, headers)
        if not batch_id:
            return []

        # 3. 抓岗位列表
        all_items = []
        page_idx = 1
        while True:
            body = {
                "batchId": batch_id,
                "pageIndex": page_idx,
                "pageSize": config.PAGE_SIZE,
                "regions": "",
                "channel": config.COMPANY_CONFIG["淘宝"]["batch_channel"],
                "language": "zh",
            }
            r = self.session.post(
                f"{self.BASE}/position/search",
                params={"_csrf": csrf}, json=body, headers=headers,
                timeout=config.REQUEST_TIMEOUT,
            )
            data = r.json()
            if not data.get("success"):
                raise ValueError("淘宝岗位接口未返回成功状态")
            content = data.get("content", {})
            items = content.get("datas", [])
            all_items.extend(items)
            total = content.get("totalSize") or content.get("totalCount") or len(items)
            if len(items) < config.PAGE_SIZE or not items:
                break
            page_idx += 1
            if page_idx > 20:
                break
        return [self._parse(it) for it in all_items]

    def _get_batch_id(self, csrf, headers):
        url = f"{self.BASE}/searchCondition/listBatch"
        r = self.session.post(url, params={"_csrf": csrf}, json={},
                              headers=headers, timeout=config.REQUEST_TIMEOUT)
        data = r.json()
        content = data.get("content", {})
        # 优先取应届生批次
        graduate = content.get("graduate", [])
        if graduate:
            return graduate[0].get("id")
        # 兜底取第一个
        for key in ["graduate", "internship", "topTalentPlan"]:
            lst = content.get(key, [])
            if lst:
                return lst[0].get("id")
        return None

    def _extract_csrf_from_html(self):
        try:
            r = self.session.get(f"{self.BASE}/campus/position",
                                 timeout=config.REQUEST_TIMEOUT)
            text = r.text
            # 常见模式：meta name="_csrf" content="xxx" 或 window.__csrf__
            import re
            m = re.search(r'name=["\']_csrf["\']\s+content=["\']([a-f0-9-]+)', text)
            if m:
                return m.group(1)
            m = re.search(r'["\']_csrf["\']:\s*["\']([a-f0-9-]+)', text)
            if m:
                return m.group(1)
        except Exception:
            pass
        return ""

    def _parse(self, it):
        modify_ts = it.get("modifyTime") or it.get("publishTime")
        publish_time = ""
        if modify_ts:
            try:
                publish_time = datetime.fromtimestamp(modify_ts / 1000).strftime("%Y-%m-%d")
            except Exception:
                publish_time = str(modify_ts)[:10]
        locations = it.get("workLocations", [])
        location = "、".join(locations) if isinstance(locations, list) else str(locations)
        # 类别：categories 为 null 时从标题推断
        cats = it.get("categories")
        if isinstance(cats, list) and cats:
            category = "、".join(str(c) for c in cats)
        else:
            category = guess_category(it.get("name", ""))
        job_id = it.get("id")
        tags = "T-Star" if "T-Star" in (it.get("name") or "") else ""
        return JobItem(
            company=self.name,
            job_id=str(job_id),
            title=it.get("name", "").strip(),
            category=category,
            location=location,
            url=f"{self.BASE}/campus/position/detail?id={job_id}",
            publish_time=publish_time,
            tags=tags,
        )
