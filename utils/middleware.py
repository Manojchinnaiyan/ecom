import logging
import time
import json
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("django")


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware to log request details and timing."""

    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, "start_time"):
            duration = time.time() - request.start_time

            log_data = {
                "user": request.user.id if request.user.is_authenticated else None,
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration": round(duration * 1000, 2),  # in ms
                "content_length": (
                    len(response.content) if hasattr(response, "content") else 0
                ),
            }

            if response.status_code >= 400:
                logger.warning(f"Request failed: {json.dumps(log_data)}")
            else:
                logger.info(f"Request processed: {json.dumps(log_data)}")

        return response
