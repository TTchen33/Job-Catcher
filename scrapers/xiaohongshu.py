"""小红书校园招聘抓取器
接口: POST https://job.xiaohongshu.com/websiterecruit/position/pageQueryPosition
"""
import requests
from .base import BaseScraper, JobItem, guess_category
import config


class XiaohongshuScraper(BaseScraper):
    name = "小红书"

    def fetch(self):
        url = "https://job.xiaohongshu.com/websiterecruit/position/pageQueryPosition"
        headers = {
            "Content-Type": "application/json",
            "Referer": "https://job.xiaohongshu.com/campus/position",
        }
        # 先拿城市和类别字典
        city_map = self._fetch_dict()
        workplaces = config.COMPANY_CONFIG["小红书"]["workplaces"]
        all_items = []
        page_num = 1
        while True:
            body = {
                "recruitType": "campus",
                "positionName": "",
                "pageNum": page_num,
                "pageSize": config.PAGE_SIZE,
                "campusRecruitTypes": config.COMPANY_CONFIG["小红书"]["campus_recruit_types"],
                "workplaces": workplaces,
            }
            r = self.session.post(url, json=body, headers=headers,
                                  timeout=config.REQUEST_TIMEOUT)
            data = r.json()
            if not data.get("success"):
                raise ValueError("小红书岗位接口未返回成功状态")
            page_data = data.get("data", {})
            items = page_data.get("list", [])
            total = page_data.get("total", 0)
            all_items.extend(items)
            if len(all_items) >= total or not items:
                break
            page_num += 1
            if page_num > 20:
                break
        return [self._parse(it, city_map) for it in all_items]

    def _fetch_dict(self):
        """获取城市编码字典"""
        url = "https://job.xiaohongshu.com/websiterecruit/common/aggEnumList"
        try:
            r = self.session.post(
                url,
                json={"applyType": "campus",
                      "typeList": ["JobTypeEnum", "PositionWorkplaceEnum"]},
                headers={"Content-Type": "application/json"},
                timeout=config.REQUEST_TIMEOUT,
            )
            data = r.json().get("data", {})
            # city code -> name
            city_map = {}
            for item in data.get("PositionWorkplaceEnum", []) or []:
                city_map[item.get("code")] = item.get("name")
            return city_map
        except Exception:
            return {}

    def _parse(self, it, city_map):
        # 工作地点：API 直接返回中文字符串
        location = it.get("workplace") or ""
        # 类别：jobType 可能为 null，兜底从标题推断
        job_type = it.get("jobType") or ""
        type_map = {"tech": "技术类", "pro": "产品类", "om": "运营类",
                    "design": "设计类", "market": "销售类", "function": "职能类"}
        category = type_map.get(job_type, "")
        if not category:
            category = guess_category(it.get("positionName", ""))
        publish_time = it.get("publishTime") or ""
        if publish_time and len(publish_time) > 10:
            publish_time = publish_time[:10]
        return JobItem(
            company=self.name,
            job_id=str(it.get("positionId") or it.get("id") or it.get("code")),
            title=it.get("positionName", "").strip(),
            category=category,
            location=location,
            url="https://job.xiaohongshu.com/campus/position",
            publish_time=publish_time,
            tags=it.get("jobProjectName") or "",
        )
