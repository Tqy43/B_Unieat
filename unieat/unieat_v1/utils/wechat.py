import logging
import requests
from django.conf import settings
from django.core.cache import cache

WX_API = "https://api.weixin.qq.com/sns/jscode2session"
ACCESS_TOKEN_API = "https://api.weixin.qq.com/cgi-bin/token"
MSG_SEC_CHECK_API = "https://api.weixin.qq.com/wxa/msg_sec_check"

logger = logging.getLogger(__name__)


class WechatAuthError(Exception):
    pass


class WechatServiceError(Exception):
    pass


def jscode2session(code: str) -> dict:
    """
    用wx.login返回的code换取 openid、session_key。
    失败抛出 WechatAuthError。
    """
    if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
        raise WechatAuthError("WECHAT_APPID/WECHAT_SECRET 未配置")

    params = {
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        resp = requests.get(WX_API, params=params, timeout=5)
        data = resp.json()
    except Exception as e:
        raise WechatAuthError(f"请求微信接口失败: {e}")

    # 微信的错误返回通常包含 errcode
    if "errcode" in data and data["errcode"] != 0:
        raise WechatAuthError(f"微信认证失败: {data}")

    if "openid" not in data or "session_key" not in data:
        raise WechatAuthError(f"返回缺少必要字段: {data}")

    return {"openid": data["openid"], "session_key": data["session_key"], "unionid": data.get("unionid")}


def _get_access_token_cache_key() -> str:
    return f"wechat:access_token:{settings.WECHAT_APPID}"


def get_wechat_access_token(force_refresh: bool = False) -> str:
    """获取微信 access_token，默认使用缓存。"""
    if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
        raise WechatServiceError("WECHAT_APPID/WECHAT_SECRET 未配置")

    cache_key = _get_access_token_cache_key()
    if not force_refresh:
        cached_token = cache.get(cache_key)
        if cached_token:
            return cached_token

    params = {
        "grant_type": "client_credential",
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_SECRET,
    }

    try:
        resp = requests.get(ACCESS_TOKEN_API, params=params, timeout=5)
        data = resp.json()
    except Exception as exc:
        raise WechatServiceError(f"请求微信 access_token 失败: {exc}")

    access_token = data.get("access_token")
    if not access_token:
        raise WechatServiceError(f"获取 access_token 失败: {data}")

    expires_in = max(int(data.get("expires_in", 7200)) - 120, 60)
    cache.set(cache_key, access_token, expires_in)
    return access_token


def msg_sec_check(openid: str, content: str, *, scene: int = 1, version: int = 2) -> dict:
    """调用微信文本内容安全接口。返回原始响应数据。"""
    if not content:
        return {"errcode": 0, "errmsg": "ok", "result": {"suggest": "pass"}}

    payload = {
        "openid": openid,
        "scene": scene,
        "version": version,
        "content": content,
    }

    for attempt in range(2):
        force_refresh = attempt == 1
        token = get_wechat_access_token(force_refresh=force_refresh)
        url = f"{MSG_SEC_CHECK_API}?access_token={token}"

        try:
            resp = requests.post(url, json=payload, timeout=5)
            data = resp.json()
        except Exception as exc:
            raise WechatServiceError(f"调用微信内容安全接口失败: {exc}")

        errcode = data.get("errcode", -1)
        if errcode == 0:
            return data

        # access_token 失效，刷新后再试一次
        if errcode in {40001, 42001, 40014} and not force_refresh:
            cache.delete(_get_access_token_cache_key())
            logger.warning("微信 access_token 失效，尝试刷新。响应: %s", data)
            continue

        raise WechatServiceError(f"微信内容安全接口返回错误: {data}")

    raise WechatServiceError("微信内容安全接口调用失败，重试后仍然错误")
