"""
Custom middleware for Visuospatial Assessment.
Zero em-dashes.
"""

class FixNullOriginMiddleware:
    """
    Sanitizes 'Origin: null' headers sent by sandboxes, local containers,
    or strict browser policies so Django CSRF verification succeeds smoothly.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.META.get('HTTP_ORIGIN') == 'null':
            try:
                host = request.get_host()
                scheme = 'https' if request.is_secure() else 'http'
                request.META['HTTP_ORIGIN'] = f"{scheme}://{host}"
            except Exception:
                request.META.pop('HTTP_ORIGIN', None)
        return self.get_response(request)
