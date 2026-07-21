import os
import time
from typing import Dict, Any

_start_time = time.time()


def get_uptime_seconds() -> float:
    return time.time() - _start_time


def format_uptime(seconds: float) -> str:
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def check_redis() -> Dict[str, Any]:
    """Ping Redis and return connectivity status."""
    try:
        import redis

        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(url, decode_responses=True)
        r.ping()
        return {"status": "connected", "url": _mask_url(url)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_celery() -> Dict[str, Any]:
    """Inspect Celery worker availability."""
    try:
        from mpips.worker import app as celery_app

        inspector = celery_app.control.inspect(timeout=2.0)
        active = inspector.active()
        if active is None:
            return {"status": "no_workers", "workers": 0}
        worker_count = len(active)
        return {"status": "available", "workers": worker_count}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def get_health_report() -> Dict[str, Any]:
    """Build a comprehensive health report."""
    uptime = get_uptime_seconds()
    return {
        "service": "mpips",
        "version": os.getenv("MPIPS_VERSION", "0.1.0"),
        "status": "healthy",
        "uptime_seconds": round(uptime, 2),
        "uptime_human": format_uptime(uptime),
        "redis": check_redis(),
        "celery": check_celery(),
        "environment": os.getenv("MPIPS_ENVIRONMENT", "development"),
    }


def _mask_url(url: str) -> str:
    """Mask sensitive parts of a connection URL."""
    if "@" in url:
        scheme_end = url.index("://") + 3
        at_pos = url.index("@")
        return url[:scheme_end] + "***@" + url[at_pos + 1 :]
    return url
