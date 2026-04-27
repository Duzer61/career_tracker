"""Shared test helpers."""


def cookies_from_response(response) -> dict:
    """Extract cookies from a response into a simple dict."""
    return dict(response.cookies)
