from aiohttp import web
import json
from sqlalchemy import func, select

from bot.config import EnvKeys
from bot.monitoring.metrics import get_metrics
from bot.database import Database
from bot.database.models.main import Order, ShoppingCart, Goods, BitcoinAddress
from bot.logger_mesh import logger


class MonitoringServer:
    """monitoring server with UI"""

    def __init__(self, host: str = None, port: int = None):
        self.host = host or EnvKeys.MONITORING_HOST
        self.port = port or EnvKeys.MONITORING_PORT
        self.app = web.Application()
        self.runner = None
        self._setup_routes()

    def _setup_routes(self):
        """Setup routes"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/metrics', self.metrics_json)
        self.app.router.add_get('/metrics/prometheus', self.prometheus_handler)

    async def metrics_json(self, request):
        """Return metrics as formatted JSON"""
        metrics = get_metrics()
        if not metrics:
            return web.json_response({"error": "Metrics not initialized"}, status=503)

        summary = metrics.get_metrics_summary()

        # Pretty print JSON with syntax highlighting
        json_str = json.dumps(summary, indent=2, default=str)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Metrics JSON</title>
            <style>
                body {{ 
                    background: #1e1e1e; 
                    color: #d4d4d4; 
                    font-family: 'Courier New', monospace;
                    padding: 20px;
                }}
                pre {{ 
                    background: #2d2d2d; 
                    padding: 20px; 
                    border-radius: 10px;
                    overflow: auto;
                }}
                .json-key {{ color: #9cdcfe; }}
                .json-value {{ color: #ce9178; }}
                .json-number {{ color: #b5cea8; }}
            </style>
        </head>
        <body>
            <h1>📊 Raw Metrics JSON</h1>
            <pre>{json_str}</pre>
            <p><a href="/" style="color: #569cd6;">← Back to Overview</a></p>
        </body>
        </html>
        """

        return web.Response(text=html, content_type='text/html')

    async def prometheus_handler(self, request):
        """Prometheus metrics"""
        metrics = get_metrics()
        if not metrics:
            return web.Response(text="# Metrics not initialized", status=503)

        prometheus_data = metrics.export_to_prometheus()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Prometheus Metrics</title>
            <style>
                body {{ 
                    background: #f5f5f5; 
                    font-family: 'Courier New', monospace;
                    padding: 20px;
                }}
                pre {{ 
                    background: white; 
                    padding: 20px; 
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    overflow: auto;
                }}
            </style>
        </head>
        <body>
            <h1>📈 Prometheus Metrics</h1>
            <pre>{prometheus_data}</pre>
            <p><a href="/">← Back to Overview</a></p>
        </body>
        </html>
        """

        return web.Response(text=html, content_type='text/html')

    async def health_check(self, request):
        """Enhanced health check endpoint"""
        health_status = {
            "status": "healthy",
            "checks": {}
        }

        # Database check with connection pool info
        try:
            db = Database()
            with db.session() as s:
                # Test database connection using SQLAlchemy select
                s.scalar(select(1))

            # Get pool stats with safe attribute access
            pool = db.engine.pool
            pool_stats = {
                "size": getattr(pool, 'size', lambda: 0)(),
                "checked_in": getattr(pool, 'checkedin', lambda: 0)(),
                "checked_out": getattr(pool, 'checkedout', lambda: 0)(),
                "overflow": getattr(pool, 'overflow', lambda: 0)() if hasattr(pool, 'overflow') else 0
            }
            health_status["checks"]["database"] = {
                "status": "ok",
                "pool": pool_stats
            }

            # Check if pool is near exhaustion
            if pool_stats["checked_out"] > pool_stats["size"] * 0.9:
                health_status["checks"]["database"]["warning"] = "connection pool nearly exhausted"
                health_status["status"] = "degraded"

        except Exception as e:
            health_status["checks"]["database"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"

        # Redis/Cache check (lazy import to avoid circular dependency)
        from bot.caching.cache import get_cache_manager
        cache = get_cache_manager()
        if cache:
            try:
                # Test redis connection
                await cache.get("health_check_test")
                health_status["checks"]["redis"] = "ok"
            except Exception as e:
                health_status["checks"]["redis"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
        else:
            health_status["checks"]["redis"] = "not configured"

        # Metrics system check
        metrics = get_metrics()
        if metrics:
            health_status["checks"]["metrics"] = "ok"
            health_status["uptime"] = metrics.get_metrics_summary()["uptime_seconds"]
        else:
            health_status["checks"]["metrics"] = "not initialized"
            health_status["status"] = "degraded"

        # Bitcoin address pool check - using SQLAlchemy ORM
        try:
            with Database().session() as s:
                result = s.query(func.count(BitcoinAddress.address)).filter(
                    BitcoinAddress.is_used == False
                ).scalar()

                health_status["checks"]["bitcoin_pool"] = {
                    "available": result,
                    "status": "ok" if result >= 10 else "warning" if result >= 5 else "critical"
                }

                if result < 5:
                    health_status["status"] = "degraded"

        except Exception as e:
            health_status["checks"]["bitcoin_pool"] = f"error: {str(e)}"

        # Background tasks check
        try:
            import bot.tasks.reservation_cleaner as cleaner_task
            import bot.tasks.file_watcher as watcher_task

            bg_tasks = {}

            # Check reservation cleaner
            if hasattr(cleaner_task, 'task') and cleaner_task.task:
                bg_tasks["reservation_cleaner"] = "running"
            else:
                bg_tasks["reservation_cleaner"] = "not started"

            # Check file watcher
            if hasattr(watcher_task, 'watcher') and watcher_task.watcher:
                bg_tasks["file_watcher"] = "running"
            else:
                bg_tasks["file_watcher"] = "not started"

            health_status["checks"]["background_tasks"] = bg_tasks

        except Exception as e:
            health_status["checks"]["background_tasks"] = f"error: {str(e)}"

        status_code = 200 if health_status["status"] == "healthy" else 503
        return web.json_response(health_status, status=status_code)

    async def start(self):
        """Start monitoring server without access logs"""
        try:
            # Disable access logs
            import logging
            logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

            self.runner = web.AppRunner(
                self.app,
                access_log=None  # Disable access logs
            )
            await self.runner.setup()
            site = web.TCPSite(self.runner, self.host, self.port)
            await site.start()
            logger.info(f"Monitoring server started on http://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start monitoring server: {e}")

    async def stop(self):
        """Stop server"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Monitoring server stopped")
