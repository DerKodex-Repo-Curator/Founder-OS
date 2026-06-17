"""Start the FastAPI dashboard API in a background thread."""
import asyncio
import logging
import threading

logger = logging.getLogger(__name__)


def start_in_thread(port: int = None):
    from config import config
    port = port or config.dashboard_api_port

    def _run():
        import uvicorn
        from api.app import app
        config_obj = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            loop="asyncio",
        )
        server = uvicorn.Server(config_obj)
        asyncio.run(server.serve())

    t = threading.Thread(target=_run, daemon=True, name="dashboard-api")
    t.start()
    logger.info(f"[Dashboard API] Serving at http://localhost:{port}")
    return t


if __name__ == "__main__":
    import uvicorn
    from config import config
    logging.basicConfig(level=logging.INFO)
    print(f"API at http://localhost:{config.dashboard_api_port}")
    uvicorn.run("api.app:app", host="127.0.0.1", port=config.dashboard_api_port, reload=False)
