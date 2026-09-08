"""scrapers 包"""
from .jd import JdScraper
from .kuaishou import KuaishouScraper
from .xiaohongshu import XiaohongshuScraper
from .pdd import PddScraper
from .taotian import TaotianScraper
from .offerstar import OfferstarScraper
from .generic import GenericScraper

# 内置抓取器（每个公司一个专用类）
SCRAPERS = {
    "京东": JdScraper,
    "快手": KuaishouScraper,
    "小红书": XiaohongshuScraper,
    "拼多多": PddScraper,
    "淘宝": TaotianScraper,
    "offerstar": OfferstarScraper,
}
