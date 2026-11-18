# -*- coding: utf-8 -*-
"""安卓端网络模块：封装后端 API。服务器地址从本地配置读取，不写死。"""
import json
from pathlib import Path
import requests

# 安卓端配置文件放应用可写目录，App 启动后由 init_conf() 设置
CONF_PATH = None

DEFAULT_CONF = {
    "server_base": "http://159.75.108.130",
    "timeout": 15,
}
_conf = dict(DEFAULT_CONF)


def init_conf():
    """在 App 启动后调用，加载配置文件"""
    global CONF_PATH, _conf
    from kivy.app import App
    CONF_PATH = Path(App.get_running_app().user_data_dir) / "client_config.json"
    if CONF_PATH.exists():
        try:
            with open(CONF_PATH, encoding="utf-8") as f:
                saved = json.load(f)
            _conf = dict(DEFAULT_CONF)
            _conf.update(saved)
        except Exception:
            _conf = dict(DEFAULT_CONF)


def load_conf():
    return dict(_conf)


def save_conf(conf):
    global _conf
    _conf = dict(conf)
    if CONF_PATH:
        CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONF_PATH, "w", encoding="utf-8") as f:
            json.dump(conf, f, ensure_ascii=False, indent=2)


def base_url():
    return _conf["server_base"].rstrip("/")


def _req(method, path, data=None, params=None):
    url = base_url() + path
    try:
        if method == "GET":
            r = requests.get(url, params=params, timeout=_conf["timeout"])
        else:
            r = requests.request(method, url, json=data, timeout=_conf["timeout"])
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("连接不上服务器，检查网络或服务器地址")
    except requests.exceptions.Timeout:
        raise RuntimeError("请求超时")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError("服务器错误 %s" % e.response.status_code)
    except ValueError:
        raise RuntimeError("服务器返回格式异常")


def health():
    return _req("GET", "/api/health")


def customer_list(only_deleted=False):
    """only_deleted=True 只看回收站（status=0），默认只看正常客户。"""
    return _req("GET", "/api/customer",
                params={"only_deleted": 1} if only_deleted else None).get("data", [])


def customer_create(data):
    return _req("POST", "/api/customer", data)


def customer_update(cid, data):
    return _req("PUT", "/api/customer/%s" % cid, data)


def customer_delete(cid):
    return _req("DELETE", "/api/customer/%s" % cid)


def customer_restore(cid):
    return _req("POST", "/api/customer/%s/restore" % cid)


def house_list(deal_type=None, keyword=None, only_deleted=False):
    """only_deleted=True 只看回收站（deleted=1），默认只看正常房源。"""
    params = {}
    if only_deleted:
        params["only_deleted"] = 1
    if deal_type:
        params["deal_type"] = deal_type
    if keyword:
        params["keyword"] = keyword
    return _req("GET", "/api/house", params=params).get("data", [])


def house_create(data):
    return _req("POST", "/api/house", data)


def house_update(hid, data):
    return _req("PUT", "/api/house/%s" % hid, data)


def house_delete(hid):
    return _req("DELETE", "/api/house/%s" % hid)


def house_restore(hid):
    return _req("POST", "/api/house/%s/restore" % hid)


# ---------- 图片 ----------
def upload_image(file_path):
    """上传单张已本地压缩的图片，返回 /uploads/... URL。"""
    import os
    url = base_url() + "/api/upload"
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        r = requests.post(url, files=files, timeout=max(_conf["timeout"], 30))
    r.raise_for_status()
    return r.json().get("url")


def upload_delete(url):
    return _req("POST", "/api/upload/delete", {"url": url})


def image_url(path):
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return base_url() + path


def photos_of(house_row):
    import json
    v = house_row.get("photos") if house_row else None
    if not v:
        return []
    if isinstance(v, list):
        return [x for x in v if x]
    if isinstance(v, str):
        try:
            arr = json.loads(v)
            return arr if isinstance(arr, list) else [v]
        except (ValueError, TypeError):
            return [v]
    return []


# ---------- AI（混元，只产出文字） ----------
AI_TIMEOUT = 120  # 推理模型慢，且上游限流时服务端会重试一轮


def _req_ex(method, path, data=None, timeout=AI_TIMEOUT):
    """带业务错误的请求：把后端 {"error": ...} 的原话抛出来。"""
    url = base_url() + path
    try:
        if method == "GET":
            r = requests.get(url, timeout=timeout)
        else:
            r = requests.request(method, url, json=data, timeout=timeout)
    except requests.exceptions.ConnectionError:
        raise RuntimeError("连不上服务器，检查网络")
    except requests.exceptions.Timeout:
        raise RuntimeError("AI 思考超时（%d 秒），再试一次" % timeout)

    if not r.ok:
        msg = ""
        try:
            body = r.json()
            if isinstance(body, dict):
                msg = body.get("error") or ""
        except Exception:
            pass
        if not msg:
            if r.status_code == 404:
                msg = "后端还没更新 AI 接口，请先更新服务器"
            elif r.status_code == 503:
                msg = "服务器还没配置 AI Key"
            else:
                msg = "服务器返回 %s" % r.status_code
        raise RuntimeError(msg)
    try:
        return r.json()
    except ValueError:
        raise RuntimeError("服务器返回格式异常")


def ai_status():
    return _req_ex("GET", "/api/ai/status", timeout=20).get("data", {})


def ai_pitch(house_id=None, house=None, tone=""):
    payload = {"tone": tone}
    if house_id:
        payload["house_id"] = house_id
    if house is not None:
        payload["house"] = house
    return _req_ex("POST", "/api/ai/pitch", payload).get("data", {})


def ai_followup(customer_id, scene="wechat"):
    return _req_ex("POST", "/api/ai/followup",
                   {"customer_id": customer_id, "scene": scene}).get("data", {})


def ai_profile(customer_id):
    return _req_ex("GET", "/api/ai/profile/%s" % customer_id).get("data", {})


def ai_match(customer_id, house_ids=None, limit=5):
    """客户一键匹配房源：本地粗排 + AI 出适配度与理由。"""
    payload = {"customer_id": customer_id, "limit": limit}
    if house_ids:
        payload["house_ids"] = house_ids
    return _req_ex("POST", "/api/ai/match", payload).get("data", {})


def ai_copy(house_id, platform="xiaohongshu"):
    """图文作品文案：标题 + 正文 + #话题。"""
    return _req_ex("POST", "/api/ai/copy",
                   {"house_id": house_id, "platform": platform}).get("data", {})


def ai_image(house_id, platform="xiaohongshu", n=1, size="1024x1024"):
    """AI 去重图（平台变体）。返回 {images:[url], prompt, platform}。"""
    return _req_ex("POST", "/api/ai/image",
                   {"house_id": house_id, "platform": platform,
                    "n": n, "size": size}).get("data", {})


# ---------- 高德地理（真实坐标/里程，接口不可用显示「—」） ----------
def geo_geocode(address, city="成都"):
    """地址解析 → 经纬度。失败抛异常，调用方兜底显示「—」。"""
    from urllib.parse import quote
    path = "/api/geo/geocode?address=%s&city=%s" % (quote(str(address)), quote(str(city)))
    return _req_ex("GET", path, timeout=20).get("data", {})


def geo_route(from_lng, from_lat, to_lng, to_lat, modes=None):
    """客户目标位置 → 房源 的步行/骑行/驾车真实距离与用时。"""
    payload = {"from_lng": from_lng, "from_lat": from_lat,
               "to_lng": to_lng, "to_lat": to_lat}
    if modes:
        payload["modes"] = modes
    return _req_ex("POST", "/api/geo/route", payload, timeout=30).get("data", {})


# ---------- 日程 / 跟进 / 带看 ----------
def schedule(days=14):
    return _req("GET", "/api/schedule", params={"days": days})


def followup_create(customer_id, method, content, next_follow_date=None):
    return _req("POST", "/api/followup",
                {"customer_id": customer_id, "method": method,
                 "content": content, "next_follow_date": next_follow_date})


def visit_create(customer_id, house_ids, plan_at=None, note=""):
    """发起带看：plan_at 给日期/时间视为预约(planned)，不给视为已完成(done)。"""
    return _req("POST", "/api/visit",
                {"customer_id": customer_id, "house_ids": house_ids,
                 "plan_at": plan_at, "note": note})


def visit_done(vid, result=""):
    return _req("POST", "/api/visit/%s/done" % vid, {"result": result})


def visit_cancel(vid):
    return _req("POST", "/api/visit/%s/cancel" % vid)
