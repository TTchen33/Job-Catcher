"""快手校园招聘抓取器
接口: POST https://campus.kuaishou.cn/recruit/campus/e/api/v1/open/positions/simple
"""
import requests
from .base import BaseScraper, JobItem, guess_category
import config


class KuaishouScraper(BaseScraper):
    name = "快手"

    def fetch(self):
        url = "https://campus.kuaishou.cn/recruit/campus/e/api/v1/open/positions/simple"
        # 先拿类别字典，把 code 翻译成中文名
        cat_map = self._fetch_category_map()
        headers = {
            "Content-Type": "application/json",
            "Referer": "https://campus.kuaishou.cn/recruit/campus/e/",
        }
        all_items = []
        page_num = 1
        while True:
            body = {
                "recruitSubProjectCodes": config.COMPANY_CONFIG["快手"]["recruit_sub_project_codes"],
                "pageSize": config.PAGE_SIZE,
                "pageNum": page_num,
            }
            r = self.session.post(url, json=body, headers=headers,
                                  timeout=config.REQUEST_TIMEOUT)
            data = r.json()
            if data.get("code") != 0:
                raise ValueError("快手岗位接口未返回成功状态")
            result = data.get("result", {})
            items = result.get("list", [])
            total = result.get("total", 0)
            all_items.extend(items)
            if len(all_items) >= total or not items:
                break
            page_num += 1
            if page_num > 20:
                break
        return [self._parse(it, cat_map) for it in all_items]

    def _fetch_category_map(self):
        """获取职位类别字典 code -> name"""
        url = ("https://campus.kuaishou.cn/recruit/campus/e/api/v1/dictionary/batch"
               "?types=workLocation,positionCategory,positionCategoryFlatten,positionNature")
        try:
            r = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            result = r.json().get("result", {})
            cat_map = {}
            for item in result.get("positionCategory", []) or []:
                cat_map[item.get("code")] = item.get("name")
            # positionCategoryFlatten 可能有更细的子类别
            for item in result.get("positionCategoryFlatten", []) or []:
                cat_map[item.get("code")] = item.get("name")
            return cat_map
        except Exception:
            return {}

    def _parse(self, it, cat_map):
        # 拼接城市：快手 simple 接口常不返回地点，尽力取
        cities = it.get("workLocationNameList") or it.get("workLocationNames") or []
        city_code = it.get("workLocationCode")
        if not cities and city_code:
            cities = [city_code]
        location = "、".join(cities) if isinstance(cities, list) else str(cities)
        # 类别：positionCategoryCode 映射不到时从标题推断
        cat_code = it.get("positionClassCode") or it.get("positionCategoryCode")
        category = cat_map.get(cat_code, "")
        if not category:
            category = guess_category(it.get("name", ""))
        # 标签
        tags = []
        if "快Star" in (it.get("name") or ""):
            tags.append("快Star")
        nature = it.get("positionNatureCode")
        if nature == "fulltime":
            tags.append("全职")
        elif nature in ("intern", "internship"):
            tags.append("实习")
        return JobItem(
            company=self.name,
            job_id=str(it.get("id") or it.get("code")),
            title=it.get("name", "").strip(),
            category=category,
            location=location,
            url="https://campus.kuaishou.cn/recruit/campus/e/#/campus/jobs?recruitSubProjectCodes=20271779425607",
            publish_time=self._fmt_date(it.get("publishTime")),
            tags="/".join(tags),
        )

    def _fmt_date(self, ts):
        if not ts:
            return ""
        try:
            from datetime import datetime
            return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
        except Exception:
            return str(ts)
