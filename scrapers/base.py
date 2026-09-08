"""抓取器基类与统一数据结构"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import config


@dataclass
class JobItem:
    """统一的岗位数据结构，所有抓取器都输出这个格式"""
    company: str            # 公司名称
    job_id: str             # 公司内唯一岗位ID（用于去重对比）
    title: str              # 岗位名称
    category: str = ""      # 职位类别（如 运营/产品/技术）
    location: str = ""      # 工作地点
    url: str = ""           # 详情/投递链接
    publish_time: str = ""  # 发布时间（ISO 格式，可为空）
    tags: str = ""          # 附加标签（如 TET/快Star）
    fetched_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @property
    def dedup_key(self) -> str:
        """去重键：公司+岗位ID"""
        return f"{self.company}::{self.job_id}"


class BaseScraper:
    """所有抓取器的基类"""
    name: str = ""

    def __init__(self, http_session):
        self.session = http_session

    def fetch(self) -> List[JobItem]:
        """抓取岗位列表，返回 JobItem 列表。子类必须实现"""
        raise NotImplementedError

    def safe(self, fn, *args, **kwargs):
        """安全执行，失败返回默认值"""
        try:
            return fn(*args, **kwargs)
        except Exception:
            return None


def guess_category(title: str) -> str:
    """从岗位标题推断职位类别（当 API 不返回类别时的兜底方案）"""
    title = title or ""
    cats = []
    # 产品/运营类（用户关注方向）
    for kw, kws in config.KEYWORDS.items():
        if kw in title or any(k in title for k in kws):
            cats.append(kw)
    # 技术类
    tech_kw = ["算法", "工程师", "开发", "架构", "前端", "后端", "客户端",
               "测试", "运维", "数据", "AI", "大模型", "安全", "Java", "C++",
               "Go", "Python", "研发", "机器学习", "深度学习"]
    if any(k in title for k in tech_kw):
        cats.append("技术")
    # 其他
    if "设计" in title:
        cats.append("设计")
    if "市场" in title or "商务" in title or "销售" in title:
        cats.append("市场")
    if "职能" in title or "财务" in title or "人事" in title or "行政" in title or "法务" in title:
        cats.append("职能")
    return "、".join(cats)
