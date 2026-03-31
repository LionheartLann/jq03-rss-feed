import logging
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def _parse_notice_time(value: str) -> datetime:
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except Exception:
        dt = datetime.now()
    return dt.replace(tzinfo=timezone.utc)


def _load_existing_items(path: Path) -> list[dict]:
    if not path.exists():
        return []

    try:
        root = ET.parse(path).getroot()
        channel = root.find("channel")
        if channel is None:
            return []

        items = []
        for item in channel.findall("item"):
            items.append(
                {
                    "guid": (item.findtext("guid") or "").strip(),
                    "title": item.findtext("title") or "",
                    "link": item.findtext("link") or "",
                    "description": item.findtext("description") or "",
                    "pubDate": item.findtext("pubDate") or "",
                }
            )
        return items
    except Exception as exc:
        logger.warning("Failed to parse existing RSS, rebuilding file: %s", exc)
        return []


def _notice_to_item(notice: dict) -> dict:
    pub_dt = _parse_notice_time(notice.get("noticeTime", ""))
    desc = (
        f"项目编号: {notice.get('openTenderCode', '')}\n"
        f"地区: {notice.get('regionName', '')}\n"
        f"采购方式: {notice.get('purchaseManner', '')}\n"
        f"项目类别: {notice.get('purchaseNature', '')}\n"
        f"发布时间: {notice.get('noticeTime', '')}"
    )
    return {
        "guid": notice.get("noticeId") or notice.get("detailUrl", ""),
        "title": notice.get("title", ""),
        "link": notice.get("detailUrl", ""),
        "description": desc,
        "pubDate": format_datetime(pub_dt),
    }


def _build_xml(items: list[dict], feed_cfg: dict) -> ET.Element:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    title = feed_cfg.get("title", "JQ03 Procurement Feed")
    link = feed_cfg.get(
        "site_link",
        "https://www.plap.mil.cn/freecms-glht/site/juncai/cggg/index.html",
    )
    description = feed_cfg.get(
        "description",
        "JQ03 related procurement notices for software/hardware/electronics/AI.",
    )
    language = feed_cfg.get("language", "zh-cn")

    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "link").text = link
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "language").text = language
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc)
    )

    for item in items:
        node = ET.SubElement(channel, "item")
        ET.SubElement(node, "title").text = item["title"]
        ET.SubElement(node, "link").text = item["link"]
        ET.SubElement(node, "guid").text = item["guid"]
        ET.SubElement(node, "pubDate").text = item["pubDate"]
        ET.SubElement(node, "description").text = item["description"]

    return rss


def update_rss(
    notices: list[dict],
    output_path: str = "rss.xml",
    feed_cfg: dict | None = None,
    max_items: int = 200,
) -> tuple[int, int]:
    """Merge matched notices into RSS file and keep most recent entries.

    Returns:
        (newly_added_count, total_items_after_merge)
    """
    cfg = feed_cfg or {}
    path = Path(output_path)

    new_items = [_notice_to_item(n) for n in notices]
    existing_items = _load_existing_items(path)

    seen = set()
    merged = []
    added = 0

    for item in new_items + existing_items:
        guid = item.get("guid", "")
        if not guid or guid in seen:
            continue
        seen.add(guid)
        merged.append(item)
        if item in new_items:
            added += 1

    merged = merged[: max_items if max_items > 0 else 200]

    rss = _build_xml(merged, cfg)
    tree = ET.ElementTree(rss)
    tree.write(path, encoding="utf-8", xml_declaration=True)

    return added, len(merged)
