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


def customer_list(include_deleted=False):
    return _req("GET", "/api/customer",
                params={"include_deleted": 1} if include_deleted else None).get("data", [])


def customer_create(data):
    return _req("POST", "/api/customer", data)


def customer_update(cid, data):
    return _req("PUT", "/api/customer/%s" % cid, data)


def customer_delete(cid):
    return _req("DELETE", "/api/customer/%s" % cid)


def customer_restore(cid):
    return _req("POST", "/api/customer/%s/restore" % cid)


def house_list(deal_type=None, keyword=None, include_deleted=False):
    params = {}
    if include_deleted:
        params["include_deleted"] = 1
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
