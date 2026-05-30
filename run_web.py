import os

import uvicorn

from tam.config import get_settings, validate_web_settings

if __name__ == "__main__":
    settings = get_settings()
    validate_web_settings(settings)
    reload_enabled = os.getenv("WEB_RELOAD", "false").lower() in {"1", "true", "yes"}
    uvicorn.run(
        "web.main:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=reload_enabled,
    )
