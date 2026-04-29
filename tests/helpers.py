"""Shared test helpers."""


def cookies_from_response(response) -> dict:
    """Extract cookies from a response into a simple dict."""
    return dict(response.cookies)


def set_client_cookies(client, response):
    """Clear existing cookies and set new ones from a response."""
    client.cookies.clear()
    client.cookies.update(dict(response.cookies))
