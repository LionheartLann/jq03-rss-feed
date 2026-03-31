import logging
from typing import Sequence

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    "计算机", "软件", "硬件", "服务器", "网络设备", "网络安全",
    "信息化", "信息系统", "信息安全", "电子信息",
    "通信设备", "通信系统", "通讯设备", "通讯系统",
    "AI", "人工智能", "大数据", "云计算", "云平台",
    "数据库", "数据中心", "系统集成", "数字化",
    "光纤", "交换机", "路由器", "防火墙",
    "显示屏", "显示器", "打印机", "打印设备",
    "存储设备", "存储系统", "磁盘阵列",
    "操作系统", "中间件", "办公软件",
    "终端设备", "智能终端",
    "监控系统", "视频会议", "指挥系统",
    "无线电", "雷达", "卫星通信",
]

EXCLUDE_KEYWORDS = [
    "食品", "副食", "被装", "物业", "保洁", "保安",
    "医疗", "医用", "药品", "手术", "诊断", "临床", "断层扫描",
    "车辆", "运输", "搬迁", "拖车", "燃油", "燃气",
    "绿化", "供暖", "供水", "供电", "炊事", "餐饮",
    "印刷", "装修", "土建", "房屋", "营房",
]


def matches_jq03(title: str) -> bool:
    return "JQ03" in title.upper()


def matches_it_keywords(title: str, keywords: Sequence[str] | None = None) -> bool:
    kw_list = keywords or DEFAULT_KEYWORDS
    return any(kw in title for kw in kw_list)


def matches_exclude(title: str) -> bool:
    return any(kw in title for kw in EXCLUDE_KEYWORDS)


def filter_notices(
    notices: list[dict],
    keywords: Sequence[str] | None = None,
) -> list[dict]:
    """Return notices that contain JQ03 AND match IT-related keywords.

    Uses a two-pass approach: first include by IT keywords, then exclude
    notices whose titles clearly belong to non-IT domains (food, medical,
    logistics, etc.).
    """
    matched = []
    for n in notices:
        title = n.get("title", "")
        if not matches_jq03(title):
            continue
        if not matches_it_keywords(title, keywords):
            logger.debug("Skipped (no IT keyword): %s", title)
            continue
        if matches_exclude(title):
            logger.debug("Excluded (non-IT domain): %s", title)
            continue
        matched.append(n)

    logger.info(
        "Filter result: %d/%d notices matched", len(matched), len(notices)
    )
    return matched
