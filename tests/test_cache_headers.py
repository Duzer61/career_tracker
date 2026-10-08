"""Tests for cache-control headers on HTML pages and static assets.

Frontend JS/CSS must always be revalidated by the browser, otherwise users can
get a stale asset after a deploy. This caused an "Invalid Date" bug: a browser
served the pre-fix ``utils.js`` while a newly added ``backups.js`` was fresh.
"""

STATIC_JS_URL = "/static/js/utils.js"
STATIC_CSS_URL = "/static/css/base.css"


class TestStaticAssetCacheHeaders:
    """Static assets must force revalidation, never rely on stale copies."""

    async def test_static_js_has_no_cache(self, client):
        response = await client.get(STATIC_JS_URL)

        assert response.status_code == 200
        cache_control = response.headers.get("cache-control", "")
        assert "no-cache" in cache_control

    async def test_static_css_has_no_cache(self, client):
        response = await client.get(STATIC_CSS_URL)

        assert response.status_code == 200
        cache_control = response.headers.get("cache-control", "")
        assert "no-cache" in cache_control


class TestHtmlCacheHeaders:
    """HTML pages keep the strict no-store policy."""

    async def test_html_is_not_cached(self, client):
        response = await client.get("/")

        assert response.status_code == 200
        cache_control = response.headers.get("cache-control", "")
        assert "no-store" in cache_control
