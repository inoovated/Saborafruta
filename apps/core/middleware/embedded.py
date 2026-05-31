from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class EmbeddedModeRedirectMiddleware:
    """Mantem o modo embutido em redirecionamentos internos."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.GET.get("embedded") != "1":
            return response
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response
        location = response.get("Location")
        if not location or location.startswith(("http://", "https://", "//")):
            return response

        parts = urlsplit(location)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["embedded"] = "1"
        response["Location"] = urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )
        return response
