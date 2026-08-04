import os


def get_health_report() -> dict[str, str]:
    """Return the current MPIPS service status without dependency claims."""
    return {
        "service": "mpips",
        "status": "healthy",
        "version": os.getenv("MPIPS_VERSION", "0.1.0"),
        "environment": os.getenv("MPIPS_ENVIRONMENT", "development"),
    }
