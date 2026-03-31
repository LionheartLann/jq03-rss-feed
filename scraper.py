import time
import logging
from base64 import b64encode

import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

logger = logging.getLogger(__name__)

BASE_URL = "https://www.plap.mil.cn"
API_PATH = "/freecms/rest/v1/notice/selectInfoMoreChannel.do"
DETAIL_BASE = BASE_URL + "/freecms-glht"

SITE_ID = "404bb030-5be9-4070-85bd-c94b1473e8de"
CHANNEL_ALL = "c5bff13f-21ca-4dac-b158-cb40accd3035"

RSA_PUBLIC_KEY_B64 = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCS2TZDs5+orLYCL5SsJ54+bPCV"
    "s1ZQQwP2RoPkFQF2jcT0HnNNT8ZoQgJTrGwNi5QNTBDoHC4oJesAVYe6DoxXS9Nl"
    "s8WbGE8ZNgOC5tVv1WVjyBw7k2x72C/qjPoyo/kO7TYl6Qnu4jqW/ImLoup/nsJp"
    "pUznF0YgbyU/dFFNBQIDAQAB"
)

PURCHASE_NATURE = {"1": "物资", "2": "工程", "3": "服务"}
PURCHASE_MANNER = {
    "1": "公开招标",
    "2": "邀请招标",
    "3": "竞争性谈判",
    "4": "询价",
    "5": "单一来源",
    "6": "竞争性磋商",
    "9": "其他",
}


def _build_rsa_key():
    pem = (
        "-----BEGIN PUBLIC KEY-----\n"
        + RSA_PUBLIC_KEY_B64
        + "\n-----END PUBLIC KEY-----"
    )
    return RSA.import_key(pem)


_rsa_key = _build_rsa_key()


def _encrypt_header(path: str) -> str:
    plaintext = f"{path}$${int(time.time() * 1000)}"
    cipher = PKCS1_v1_5.new(_rsa_key)
    encrypted = cipher.encrypt(plaintext.encode("utf-8"))
    return b64encode(encrypted).decode("ascii")


def build_detail_url(htmlpath: str) -> str:
    return DETAIL_BASE + htmlpath


def _build_query_string(
    title: str,
    start_time: str,
    end_time: str,
    page: int,
    page_size: int,
) -> str:
    """Build query string exactly matching the JS client format.

    start_time / end_time must be full datetime strings like
    ``2026-03-27 00:00:00`` or empty strings.
    """
    return (
        f"?&siteId={SITE_ID}"
        f"&channel={CHANNEL_ALL}"
        f"&currPage={page}"
        f"&pageSize={page_size}"
        f"&noticeType="
        f"&regionCode="
        f"&purchaseManner="
        f"&title={title}"
        f"&openTenderCode="
        f"&operationStartTime={start_time}"
        f"&operationEndTime={end_time}"
        f"&selectTimeName="
        f"&cityOrArea="
        f"&purchaseNature="
        f"&punishType="
    )


def fetch_notices(
    title: str = "",
    start_time: str = "",
    end_time: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Fetch procurement notices from the API.

    start_time / end_time accept ``YYYY-MM-DD HH:MM:SS`` or empty string.
    Returns the parsed JSON response with keys: code, total, data.
    """
    qs = _build_query_string(title, start_time, end_time, page, page_size)
    url = BASE_URL + API_PATH + qs

    headers = {
        "nsssjss": _encrypt_header(API_PATH),
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE_URL + "/freecms-glht/site/juncai/cggg/index.html",
    }

    logger.debug("GET %s", url)
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != "200":
        raise RuntimeError(f"API returned error: {data.get('msg', 'unknown')}")

    return data


def fetch_all_notices(title: str = "", start_time: str = "", end_time: str = "") -> list[dict]:
    """Fetch all pages of notices matching the query."""
    all_items = []
    page = 1
    page_size = 50

    while True:
        result = fetch_notices(
            title=title,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )
        items = result.get("data", [])
        if not items:
            break

        all_items.extend(items)
        total = result.get("total", 0)
        logger.info("Fetched page %d (%d items, total=%d)", page, len(items), total)

        if len(all_items) >= total:
            break
        page += 1

    return all_items


def enrich_notice(notice: dict) -> dict:
    """Add human-readable fields and detail URL to a notice dict."""
    return {
        "title": notice.get("title", ""),
        "noticeTime": notice.get("noticeTime", ""),
        "regionName": notice.get("regionName") or "",
        "purchaseManner": PURCHASE_MANNER.get(notice.get("purchaseManner", ""), "未知"),
        "purchaseNature": PURCHASE_NATURE.get(notice.get("purchaseNature", ""), "未知"),
        "openTenderCode": notice.get("openTenderCode") or "",
        "noticeId": notice.get("noticeId") or "",
        "detailUrl": build_detail_url(notice.get("htmlpath", "")),
    }
