#!/usr/bin/env python3
"""Military procurement website daily scraper.

Usage:
    python main.py              # Start the scheduler (runs daily)
    python main.py --now        # Run once immediately then exit
    python main.py --dry-run    # Run once, print results, skip email
"""

import argparse
import logging
import time
from datetime import date
from pathlib import Path

import yaml
import schedule

from scraper import fetch_all_notices, enrich_notice
from filter import filter_notices
from rss import update_rss

CONFIG_PATH = Path(__file__).parent / "config.yaml"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("jq03")


def load_config(path: str | Path | None = None) -> dict:
    p = Path(path or CONFIG_PATH)
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_job(config: dict, dry_run: bool = False) -> None:
    logger.info("=== Job started ===")
    today = date.today()
    start_time = today.strftime("%Y-%m-%d 00:00:00")
    end_time = today.strftime("%Y-%m-%d 23:59:59")

    # 1. Scrape
    logger.info("Fetching JQ03 notices for %s ...", today.isoformat())
    raw = fetch_all_notices(title="JQ03", start_time=start_time, end_time=end_time)
    logger.info("Fetched %d raw notices", len(raw))

    if not raw:
        logger.info("No notices found today, done.")
        return

    # 2. Enrich
    enriched = [enrich_notice(n) for n in raw]

    # 3. Filter by IT keywords
    keywords = config.get("keywords")
    filter_cfg = config.get("filter", {})
    matched = filter_notices(
        enriched,
        keywords,
        exclude_enabled=filter_cfg.get("exclude_enabled", True),
    )

    if not matched:
        logger.info("No IT-related JQ03 notices today, done.")
        return

    rss_cfg = config.get("rss", {})
    output = rss_cfg.get("output", "rss.xml")
    max_items = int(rss_cfg.get("max_items", 200))

    if dry_run:
        logger.info("DRY RUN — would merge %d notices into %s", len(matched), output)
        for n in matched[:20]:
            logger.info("  • %s  [%s]", n["title"], n["detailUrl"])
    else:
        added, total = update_rss(
            notices=matched,
            output_path=output,
            feed_cfg=rss_cfg,
            max_items=max_items,
        )
        logger.info("RSS updated: %s (added=%d, total=%d)", output, added, total)

    logger.info("=== Job finished ===")


def main():
    parser = argparse.ArgumentParser(description="JQ03 军采网采购公告监控")
    parser.add_argument("--now", action="store_true", help="立即执行一次然后退出")
    parser.add_argument("--dry-run", action="store_true", help="只打印结果，不发送邮件")
    parser.add_argument("--config", type=str, default=None, help="配置文件路径")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.now or args.dry_run:
        run_job(config, dry_run=args.dry_run)
        return

    sched_time = config.get("schedule", {}).get("time", "09:00")
    logger.info("Scheduling daily job at %s", sched_time)
    schedule.every().day.at(sched_time).do(run_job, config=config)

    # Also run immediately on first start
    run_job(config)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
