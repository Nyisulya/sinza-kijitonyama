from django.conf import settings
from urllib.parse import urlparse

class DynamicCsrfMiddleware:
    """
    Middleware inayoongeza kiotomatiki Host, IP, au Domain ya sasa kwenye
    settings.CSRF_TRUSTED_ORIGINS ili kuzuia kosa la '403 CSRF verification failed'
    bila kujali ni IP ipi au Domain ipi inayotumika kwenye VPS au Local.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            full_host = request.get_host()
            host_only = full_host.split(':')[0]
            origin = request.META.get('HTTP_ORIGIN', '')
            referer = request.META.get('HTTP_REFERER', '')

            candidates = [
                f"http://{full_host}",
                f"https://{full_host}",
                f"http://{host_only}",
                f"https://{host_only}",
            ]

            if origin:
                candidates.append(origin)

            if referer:
                parsed = urlparse(referer)
                if parsed.scheme and parsed.netloc:
                    candidates.append(f"{parsed.scheme}://{parsed.netloc}")

            for c in candidates:
                if c and c not in settings.CSRF_TRUSTED_ORIGINS:
                    settings.CSRF_TRUSTED_ORIGINS.append(c)
        except Exception:
            pass

        return self.get_response(request)
