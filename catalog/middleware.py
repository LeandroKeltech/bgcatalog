"""
Custom middleware for development
"""
from django.utils.deprecation import MiddlewareMixin


class DisableCSRFMiddleware(MiddlewareMixin):
    """
    Disable CSRF validation for all requests.
    WARNING: Only use this in development! Never in production!
    """
    def process_request(self, request):
        setattr(request, '_dont_enforce_csrf_checks', True)
