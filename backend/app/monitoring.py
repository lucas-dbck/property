from __future__ import annotations

import threading
import time

from sqlalchemy import select

from .config import get_settings
from .database import SessionLocal
from .models import MonitoredSearch
from .routes.opportunities import scan_monitored_search


_monitor_started = False


def start_immoweb_monitor() -> None:
    global _monitor_started
    settings = get_settings()
    if _monitor_started or not settings.immoweb_monitor_enabled:
        return
    _monitor_started = True
    thread = threading.Thread(target=run_immoweb_monitor_loop, daemon=True)
    thread.start()


def run_immoweb_monitor_loop() -> None:
    settings = get_settings()
    interval_seconds = max(settings.immoweb_monitor_interval_minutes, 5) * 60
    while True:
        scan_all_monitored_searches(settings.immoweb_monitor_max_listings)
        time.sleep(interval_seconds)


def scan_all_monitored_searches(max_listings: int) -> None:
    db = SessionLocal()
    try:
        searches = list(db.scalars(select(MonitoredSearch).where(MonitoredSearch.is_active.is_(True))))
        for search in searches:
            try:
                scan_monitored_search(db, search, max_listings=max_listings)
            except Exception:
                db.rollback()
    finally:
        db.close()
