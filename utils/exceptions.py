# utils/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger("django")


def custom_exception_handler(exc, context):
    """Custom exception handler for DRF."""
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    # If response is None, there was an unhandled exception
    if response is None:
        if isinstance(exc, Exception):
            logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return None

    # Add more context to the response
    if isinstance(response.data, dict):
        # If it's already a dict, add a proper error message
        if "detail" in response.data:
            response.data = {
                "error": response.data["detail"],
                "status_code": response.status_code,
            }
        else:
            # Format validation errors in a consistent way
            error_details = {}
            for key, value in response.data.items():
                if isinstance(value, list):
                    error_details[key] = value[0]
                else:
                    error_details[key] = value

            response.data = {
                "error": "Validation error",
                "details": error_details,
                "status_code": response.status_code,
            }

    return response
