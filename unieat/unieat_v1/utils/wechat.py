import requests
from django.conf import settings

WX_API = "https://api.weixin.qq.com/sns/jscode2session"

class WechatAuthError(Exception):
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
