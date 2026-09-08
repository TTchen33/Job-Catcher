"""
通用 API 抓取器 —— 零代码添加新公司

后续想加新公司，只需在 config.py 的 GENERIC_SOURCES 里加一段配置即可，
无需写任何代码。配置说明见下方示例。

支持两种数据源类型：
  - "api"    : JSON 接口（POST/GET），返回岗位列表
  - "html"   : 服务端渲染页面，解析 HTML 表格/卡片

示例配置（加到 config.py 的 GENERIC_SOURCES 列表里）：

    {
        "name": "某公司",
        "type": "api",                          # api 或 html
        "url": "https://example.com/api/jobs",
        "method": "POST",                       # POST 或 GET
        "headers": {"Content-Type": "application/json"},
        # 请求体模板，{page} 会被替换为页码
        "body_template": {"page": "{page}", "size": 100},
        "pagination": {
            "page_start": 1,
            "page_key": "page",                 # body_template 里的占位符
            "stop_when": "less_than_size",      # 停止条件: less_than_size / empty_list / no_more
        },
        # 响应字段路径：用点号分隔，如 "data.list"
        "response": {
            "list_path": "data.list",           # 岗位列表在响应里的路径
            "total_path": "data.total",         # 总数字段（可选）
        },
        # 字段映射：API 字段名 -> 统一字段
        "fields": {
            "job_id":     "id",
            "title":      "positionName",
            "category":   "jobType",
            "location":   "workCity",
            "url":        "detailUrl",          # 没有就留空，会自动生成
            "publish_time": "createTime",
            "tags":       "projectName",
        },
        # 详情页 URL 模板（可选，{job_id} 会被替换）
        "detail_url_template": "https://example.com/jobs/{job_id}",
        # 时间戳转换（可选）：如果发布时间是毫秒时间戳
        "timestamp_field": "createTime",        # 会自动转成 YYYY-MM-DD
    }
"""
import requests
import json
from datetime import datetime
from .base import BaseScraper, JobItem, guess_category
import config


class GenericScraper(BaseScraper):
    """通用抓取器，由配置驱动"""

    def __init__(self, http_session, source_config):
        self.name = source_config["name"]
        self.cfg = source_config
        super().__init__(http_session)

    def fetch(self):
        dtype = self.cfg.get("type", "api")
        if dtype == "html":
            return self._fetch_html()
        return self._fetch_api()

    def _fetch_api(self):
        url = self.cfg["url"]
        method = self.cfg.get("method", "GET")
        headers = self.cfg.get("headers", {})
        headers.setdefault("User-Agent", config.USER_AGENT)
        body_tpl = self.cfg.get("body_template")
        pagination = self.cfg.get("pagination", {})
        page_start = pagination.get("page_start", 1)
        page_key = pagination.get("page_key", "page")
        stop_when = pagination.get("stop_when", "less_than_size")
        page_size = self.cfg.get("page_size", config.PAGE_SIZE)

        resp_cfg = self.cfg.get("response", {})
        list_path = resp_cfg.get("list_path", "list")
        total_path = resp_cfg.get("total_path")

        all_raw = []
        page = page_start
        max_pages = 30
        while page < page_start + max_pages:
            # 构造请求体
            body = None
            if body_tpl:
                body = json.loads(json.dumps(body_tpl))  # 深拷贝
                self._replace_placeholder(body, page_key, page)
                # 同时替换 {page} 字符串形式
                body_str = json.dumps(body)
                body_str = body_str.replace("{page}", str(page))
                body = json.loads(body_str)

            # 发请求
            try:
                if method.upper() == "POST":
                    r = self.session.post(url, json=body, headers=headers,
                                          timeout=config.REQUEST_TIMEOUT)
                else:
                    params = body or {}
                    r = self.session.get(url, params=params, headers=headers,
                                         timeout=config.REQUEST_TIMEOUT)
                data = r.json()
            except Exception as e:
                raise RuntimeError(f"第 {page} 页请求失败") from e

            # 提取列表
            items = self._extract_path(data, list_path)
            if not isinstance(items, list):
                raise ValueError(f"响应中 {list_path} 不是岗位列表，请检查字段配置")
            all_raw.extend(items)

            # 判断是否停止
            if stop_when == "empty_list" and not items:
                break
            elif stop_when == "less_than_size" and len(items) < page_size:
                break
            # 检查总数
            if total_path:
                total = self._extract_path(data, total_path)
                if isinstance(total, (int, float)) and len(all_raw) >= total:
                    break
            if not items:
                break
            page += 1

        return [self._parse_api_item(it) for it in all_raw]

    def _fetch_html(self):
        url = self.cfg["url"]
        headers = {"User-Agent": config.USER_AGENT}
        try:
            r = self.session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        except Exception as e:
            raise RuntimeError("页面请求失败") from e
        return self._parse_html(r.text)

    def _parse_html(self, html):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        fields = self.cfg.get("fields", {})
        table = soup.find("table")
        if table is None:
            raise ValueError("未找到表格；动态页面或卡片布局需要专用适配")
        items = []
        if table:
            rows = table.find_all("tr")[1:]  # 跳过表头
            for row in rows:
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) < 2:
                    continue
                job_id = cells[0]
                items.append(JobItem(
                    company=self.name,
                    job_id=job_id,
                    title=cells[1],
                    category=guess_category(cells[1]),
                    location=cells[2] if len(cells) > 2 else "",
                    url="",
                    tags="聚合",
                ))
        return items

    def _parse_api_item(self, it):
        fields = self.cfg.get("fields", {})
        job_id = str(self._extract_path(it, fields.get("job_id", "id")) or "")
        title = str(self._extract_path(it, fields.get("title", "name")) or "").strip()
        category = str(self._extract_path(it, fields.get("category", "")) or "")
        location = str(self._extract_path(it, fields.get("location", "")) or "")
        url = str(self._extract_path(it, fields.get("url", "")) or "")
        publish_time = str(self._extract_path(it, fields.get("publish_time", "")) or "")
        tags = str(self._extract_path(it, fields.get("tags", "")) or "")

        # 时间戳转换
        ts_field = self.cfg.get("timestamp_field")
        if ts_field and publish_time:
            ts = self._extract_path(it, ts_field)
            if isinstance(ts, (int, float)):
                try:
                    publish_time = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
                except Exception:
                    pass

        # 类别为空时从标题推断
        if not category:
            category = guess_category(title)

        # URL 兜底
        if not url:
            tpl = self.cfg.get("detail_url_template", "")
            if tpl and job_id:
                url = tpl.replace("{job_id}", job_id)

        return JobItem(
            company=self.name,
            job_id=job_id,
            title=title,
            category=category,
            location=location,
            url=url,
            publish_time=publish_time,
            tags=tags,
        )

    def _extract_path(self, obj, path):
        """按点号路径提取嵌套字段，如 "data.list" """
        if not path:
            return None
        current = obj
        for key in path.split("."):
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                current = current[idx] if idx < len(current) else None
            else:
                return None
            if current is None:
                return None
        return current

    def _replace_placeholder(self, obj, key, value):
        """递归替换字典/列表里的占位符"""
        if isinstance(obj, dict):
            for k in obj:
                if isinstance(obj[k], str) and "{page}" in obj[k]:
                    obj[k] = obj[k].replace("{page}", str(value))
                elif isinstance(obj[k], (dict, list)):
                    self._replace_placeholder(obj[k], key, value)
                elif k == key:
                    obj[k] = value
        elif isinstance(obj, list):
            for i in range(len(obj)):
                if isinstance(obj[i], str) and "{page}" in obj[i]:
                    obj[i] = obj[i].replace("{page}", str(value))
                elif isinstance(obj[i], (dict, list)):
                    self._replace_placeholder(obj[i], key, value)
