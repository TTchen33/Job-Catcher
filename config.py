"""
Campus Radar 配置文件
修改这里的配置来定制你的秋招监控。
"""

# ==================== 监控公司开关 ====================
# 把不想监控的公司设为 False 即可
ENABLED_COMPANIES = {
    "京东": True,
    "快手": True,
    "小红书": True,
    "拼多多": True,
    "淘宝": True,
    "offerstar": True,   # 聚合平台，补充行业动态
}

# ==================== 岗位关键词 ====================
# False = 不限制岗位方向；需要限定方向时设为 True 并修改下面的关键词。
FILTER_BY_KEYWORDS = False
# 简报会优先按"职位类别"过滤，再用关键词对岗位标题做兜底匹配
# 想加方向直接往里加关键词即可
KEYWORDS = {
    "电商": [
        "采销", "采销管培", "商家运营", "行业运营", "品类运营",
        "电商运营", "商品运营", "店铺运营", "平台运营", "招商",
        "供应链", "采购", "贸易", "跨境", "电商", "商家拓展",
        "行业BD", "商业化", "渠道运营", "分销",
    ],
    "产品": [
        "产品经理", "产品策划", "产品助理", "产品实习生",
        "数据产品", "商业化产品", "策略产品", "产品运营",
        "用户产品", "平台产品", "B端产品", "C端产品",
    ],
    "运营": [
        "用户运营", "内容运营", "活动运营", "社群运营",
        "新媒体运营", "社区运营", "增长运营",
        "海外运营", "国际化运营", "直播运营",
        "APP运营",
    ],
}

# 命中关键词的类别名（各公司 API 返回的类别字段里，含这些字就算命中）
CATEGORY_KEYWORDS = ["产品", "运营", "电商", "采销", "商家", "行业"]

# ==================== 目标城市 ====================
# 留空 [] 表示全国都看；填了就只看这些城市
# 注意：部分公司（如小红书）按城市过滤，填这里会精确过滤
TARGET_CITIES = ["香港", "深圳"]
CITY_ALIASES = {
    "香港": ["香港", "Hong Kong", "Hongkong", "HK"],
    "深圳": ["深圳", "Shenzhen"],
}
# 地点未披露、全国或多地岗位保留，避免遗漏，并在日报中提醒核实。
INCLUDE_UNSPECIFIED_LOCATIONS = True
# 公开仓库的日报默认不包含个人投递记录。
INCLUDE_APPLICATION_PROGRESS = False

# ==================== 各公司专属参数 ====================
COMPANY_CONFIG = {
    "京东": {
        # 应届生招聘类型，type=present 表示应届生
        "type": "present",
    },
    "快手": {
        # 27届校招项目代码（从官网 URL 里提取）
        "recruit_sub_project_codes": ["20271779425607"],
    },
    "小红书": {
        # term_regular = 应届生校招
        "campus_recruit_types": ["term_regular"],
        # workplace 城市编码（4401=上海）。留空则不限城市
        "workplaces": [],  # [] = 全国
    },
    "拼多多": {
        # t=null 表示全部类别，也可填具体类别 job code
        "t": None,
    },
    "淘宝": {
        # batchId 会自动获取，这里留默认即可
        "batch_channel": "campus_group_official_site",
    },
    "offerstar": {
        # 聚合平台查询参数
        "title": "2027",
        "positions": "",   # 空字符串 = 不限制岗位方向
        "channel": "校招",
    },
}

# ==================== 通用抓取源（零代码添加新公司）====================
# 后续添加新公司，只需在这里加一段配置即可，无需写代码！
# 配置格式见 scrapers/generic.py 文件顶部说明。
#
# 示例（取消注释并修改即可启用）：
#
# GENERIC_SOURCES = [
#     {
#         "name": "某公司",
#         "type": "api",                          # api 或 html
#         "url": "https://example.com/api/jobs",
#         "method": "POST",
#         "headers": {"Content-Type": "application/json"},
#         "body_template": {"page": "{page}", "size": 100},
#         "pagination": {"page_start": 1, "page_key": "page", "stop_when": "less_than_size"},
#         "response": {"list_path": "data.list", "total_path": "data.total"},
#         "fields": {
#             "job_id": "id", "title": "positionName", "category": "jobType",
#             "location": "workCity", "publish_time": "createTime",
#         },
#         "detail_url_template": "https://example.com/jobs/{job_id}",
#         "timestamp_field": "createTime",
#     },
# ]
GENERIC_SOURCES = []

# ==================== 运行参数 ====================
# 请求超时（秒）
REQUEST_TIMEOUT = 20
# 失败重试次数
MAX_RETRIES = 2
# 每页抓取条数（尽量大，减少翻页）
PAGE_SIZE = 100
# User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
