import httpx

from app.config import config as cf


async def verify_smartcaptcha(token: str, ip: str | None = None) -> bool:
    """
    Validates Yandex SmartCaptcha token via server-side API.
    Returns True if captcha is valid (user is human).

    If SMARTCAPTCHA keys are not configured, validation is skipped (returns True).
    This allows the application to work without captcha during development/testing.

    Behaviour on errors depends on environment:
    - dev: fail open (return True) — to avoid blocking during development
    - prod: fail closed (return False) — to block bots on errors
    """
    # Skip validation if captcha is not configured
    if not cf.SMARTCAPTCHA_SECRET_KEY or not cf.SMARTCAPTCHA_SITE_KEY:
        return True

    data = {
        "secret": cf.SMARTCAPTCHA_SECRET_KEY,
        "token": token,
    }
    if ip:
        data["ip"] = ip

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://smartcaptcha.cloud.yandex.ru/validate",
                data=data,
                timeout=5,
            )
            if resp.status_code != 200:
                return not cf.IS_PROD  # fail open in dev, fail closed in prod

            result = resp.json()
            return result.get("status") == "ok"
        except Exception:
            return not cf.IS_PROD  # fail open in dev, fail closed in prod
