# -*- coding: utf-8 -*-
"""蒲江房产带看作战系统 - 安卓客户端（Kivy 原生 · 底部导航模块化架构 v2.0）

布局：顶部品牌栏 + 内容区（客户/房源/工具/我的）+ 底部导航栏。
新增功能只需：写一个页面 Widget + 在 BOTTOM_NAV 注册一项，主框架零改动。
数字与图片处理全本地，AI 只润色文字。
"""
import os
import datetime
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.image import AsyncImage
from kivy.uix.widget import Widget
from kivy.core.text import LabelBase
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.utils import get_color_from_hex

import api

# ============ ERP 深蓝主题（深海军蓝导航 · 亮蓝主色 · 价格橙） ============
C_BG = get_color_from_hex("#F0F2F5")
C_PANEL = get_color_from_hex("#FFFFFF")
C_PANEL2 = get_color_from_hex("#F5F7FA")
C_BORDER = get_color_from_hex("#E6EAF0")
C_ACCENT = get_color_from_hex("#0D6EFD")
C_ACCENT2 = get_color_from_hex("#0D6EFD")
C_NAVY = get_color_from_hex("#1B2A41")        # 顶部品牌栏
C_NAVY_DARK = get_color_from_hex("#1B2838")   # 底部导航
C_NAV_TEXT = get_color_from_hex("#AEBBD0")    # 深色区文字
C_NAV_ACTIVE = get_color_from_hex("#5B8DEF")  # 深色区选中
C_PRICE = get_color_from_hex("#F05A28")
C_TEXT = get_color_from_hex("#1F2A37")
C_TEXT2 = get_color_from_hex("#7A8798")
C_TEXT3 = get_color_from_hex("#AAB4C2")
C_SUCCESS = get_color_from_hex("#16A34A")
C_DANGER = get_color_from_hex("#E0483D")
C_CHIP_BG = get_color_from_hex("#EAF2FF")
C_CHIP_WARM = get_color_from_hex("#FFF3E8")
C_TEAL = get_color_from_hex("#0AA5A0")

_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinese_font.ttf")
if os.path.exists(_FONT):
    for n in ("Roboto", "RobotoItalic", "RobotoMedium", "RobotoMediumItalic",
              "RobotoBold", "RobotoBoldItalic", "DejaVuSans"):
        LabelBase.register(name=n, fn_regular=_FONT)


def card_bg(widget, color=C_PANEL, radius=8):
    with widget.canvas.before:
        Color(*color)
        widget._bg_rect = Rectangle(size=widget.size, pos=widget.pos, radius=[radius])
    widget.bind(size=lambda w, v: setattr(w._bg_rect, "size", v),
                pos=lambda w, v: setattr(w._bg_rect, "pos", v))


class Card(BoxLayout):
    def __init__(self, color=C_PANEL, **kw):
        super().__init__(**kw)
        card_bg(self, color)


class FlatButton(Button):
    """纯色扁平按钮：canvas 画圆角底，彻底去掉 Kivy 默认 nine-patch 的阴影块。"""
    def __init__(self, text="", on_press=None, bg=None, fg=None, radius=8,
                 size_hint_x=None, font_size="13sp", **kw):
        super().__init__(text=text, font_size=font_size,
                         color=fg or (1, 1, 1, 1), background_normal="",
                         background_down="", background_color=(0, 0, 0, 0),
                         **kw)
        # 只有显式指定宽度比例时才覆盖，否则保持默认 1（自适应父容器）
        if size_hint_x is not None:
            self.size_hint_x = size_hint_x
        self._bg = bg or C_ACCENT
        self._radius = radius
        with self.canvas.before:
            self._bgc = Color(*self._bg)
            self._rect = Rectangle(size=self.size, pos=self.pos, radius=[radius])
        self.bind(size=self._upd, pos=self._upd)
        if on_press:
            self.bind(on_press=on_press)

    def _upd(self, w, v):
        self._rect.size = self.size
        self._rect.pos = self.pos

    def set_bg(self, color):
        """切换底色（分段选择器用）。"""
        self._bg = color
        self._bgc.rgba = color


def accent_btn(text, on_press, size_hint_x=None, danger=False, **kw):
    return FlatButton(text, on_press, bg=C_DANGER if danger else C_ACCENT,
                      size_hint_x=size_hint_x, **kw)


def ghost_btn(text, on_press, size_hint_x=None, color=None, **kw):
    return FlatButton(text, on_press, bg=C_PANEL2, fg=color or C_TEXT,
                      size_hint_x=size_hint_x, font_size="12sp", **kw)


class WhitePopup(Popup):
    """白底弹窗：Kivy 默认主题的弹窗底是深灰，深色文字会看不清。
    这里关掉默认背景图，自己画一块白色圆角底，保证和整体浅色主题一致。"""

    def __init__(self, **kw):
        kw.setdefault("background", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("title_color", C_TEXT)
        kw.setdefault("separator_color", C_BORDER)
        kw.setdefault("separator_height", dp(1))
        super().__init__(**kw)
        with self.canvas.before:
            Color(*C_PANEL)
            self._wbg = Rectangle(size=self.size, pos=self.pos, radius=[dp(12)])
        self.bind(size=lambda w, v: setattr(self._wbg, "size", v),
                  pos=lambda w, v: setattr(self._wbg, "pos", v))


class AiPopup(WhitePopup):
    """AI 结果弹窗：请求走后台线程，结果回主线程显示，可一键复制。
    推理模型一般 20～40 秒，所以先把「正在想」显示出来，不让人以为卡死。"""

    def __init__(self, title, subtitle, work_fn, **kw):
        self._text = ""
        self._work = work_fn

        content = BoxLayout(orientation="vertical", spacing=dp(8),
                            padding=[dp(4), dp(4)])
        content.add_widget(TLabel(subtitle, "10sp", C_TEXT3, height=dp(26)))

        scroll = ScrollView(size_hint=(1, 1))
        self.out = Label(text="AI 正在想，大约 20～40 秒…", font_size="13sp",
                         color=C_TEXT2, halign="left", valign="top",
                         size_hint_y=None, markup=False)
        self.out.bind(width=lambda w, v: setattr(w, "text_size", (max(int(v), 1), None)))
        self.out.bind(texture_size=lambda w, v: setattr(w, "height", v[1] + dp(12)))
        scroll.add_widget(self.out)
        content.add_widget(scroll)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.btn_copy = accent_btn("复制全文", self._copy)
        row.add_widget(self.btn_copy)
        row.add_widget(FlatButton("关闭", lambda _: self.dismiss(),
                                  bg=C_PANEL2, fg=C_TEXT2, radius=8))
        content.add_widget(row)

        super().__init__(title=title, content=content, size_hint=(0.94, 0.86),
                         auto_dismiss=False, **kw)
        self.open()
        Clock.schedule_once(self._start, 0.05)

    def _start(self, *_):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            d = self._work()
            txt = (d.get("text") if isinstance(d, dict) else str(d)) or ""
            Clock.schedule_once(lambda dt: self._show(txt, ""), 0)
        except Exception as e:
            msg = str(e) or type(e).__name__
            Clock.schedule_once(lambda dt: self._show("", msg), 0)

    def _show(self, txt, err):
        if err:
            self.out.text = "生成失败：\n" + err
            self.out.color = C_DANGER
            self.btn_copy.disabled = True
            return
        self._text = txt
        self.out.text = txt
        self.out.color = C_TEXT

    def _copy(self, *_):
        if not self._text:
            toast("还没有内容")
            return
        Clipboard.copy(self._text)
        toast("已复制，直接去微信粘贴")


def toast(msg):
    content = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
    content.add_widget(Label(text=str(msg), font_size="15sp", color=C_TEXT,
                             halign="center", valign="middle"))
    b = accent_btn("知道了", lambda _: p.dismiss())
    b.size_hint_y = None
    b.height = dp(42)
    content.add_widget(b)
    p = WhitePopup(title="提示", content=content, size_hint=(0.82, 0.32),
              background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
    p.open()


def confirm(title, msg, on_yes):
    content = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
    content.add_widget(Label(text=msg, font_size="14sp", color=C_TEXT,
                             halign="left", valign="middle"))
    bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    yes = accent_btn("确定", lambda _: (p.dismiss(), on_yes()))
    no = ghost_btn("取消", lambda _: p.dismiss())
    bar.add_widget(yes)
    bar.add_widget(no)
    content.add_widget(bar)
    p = WhitePopup(title=title, content=content, size_hint=(0.85, 0.36),
              background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
    p.open()


def _apk_price(r):
    if r.get("deal_type") == "sale":
        v = r.get("total_price")
        if v is None:
            return "", ""
        try:
            return "%.0f" % (float(v) / 10000), "万"
        except (ValueError, TypeError):
            return str(v), "万"
    v = r.get("annual_rent") or r.get("monthly_rent")
    if v is None:
        return "", ""
    try:
        if r.get("annual_rent"):
            return "%.1f" % (float(v) / 10000), "万/年"
        return "%.0f" % float(v), "元/月"
    except (ValueError, TypeError):
        return str(v), "元/月"


def _apk_budget(r):
    """客户预算显示：租房=万/年 或 元/年；买房=万 或 元。"""
    is_rent = r.get("customer_type") == "rent"
    b = r.get("rent_budget") if is_rent else r.get("budget_total")
    if b in (None, "", 0, "0"):
        return ""
    try:
        f = float(b)
    except (TypeError, ValueError):
        return str(b)
    if f >= 10000:
        return ("%.2f万/年" % (f / 10000)) if is_rent else ("%.1f万" % (f / 10000))
    return ("%.0f元/年" % f) if is_rent else ("%.0f元" % f)


def _apk_tags(r):
    tags = []
    if r.get("deal_type") == "sale":
        if r.get("full_five_unique"):
            tags.append(("满五唯一", True))
    elif r.get("can_short_rent"):
        tags.append(("可短租", False))
    if r.get("has_elevator"):
        tags.append(("有电梯", False))
    deco = str(r.get("decoration_level") or "")
    if "精装" in deco or "豪装" in deco:
        tags.append(("精装修", True))
    if not tags:
        tags.append(("随时看房" if r.get("deal_type") == "rent" else "真房源", False))
    return tags[:2]


def TLabel(text, size="12sp", color=None, bold=False, align="left", height=None, **kw):
    """文本标签：绑定 text_size 才能真正左/右对齐，避免 Kivy 默认居中。"""
    lb = Label(text=str(text), font_size=size, color=color or C_TEXT, bold=bold,
               halign=align, valign="middle", shorten=True, **kw)
    lb.bind(size=lambda w, v: setattr(w, "text_size", (max(v[0], 1), None)))
    if height:
        lb.size_hint_y = None
        lb.height = height
    return lb


class RecordRow(BoxLayout):
    """数据卡片：固定宽度的封面/头像 + 自适应信息区 + 固定宽度操作列。
    所有文字标签绑定 text_size，确保左对齐不被 Kivy 默认居中打乱。"""
    def __init__(self, text, sub, on_edit=None, on_delete=None, on_restore=None,
                 cover_url=None, price=None, tags=None, avatar=None, avatar_color=None,
                 on_ai=None, ai_label="AI", **kw):
        super().__init__(orientation="horizontal", size_hint_y=None,
                         height=dp(94), spacing=dp(10), padding=[dp(10), dp(10)], **kw)
        card_bg(self, C_PANEL, radius=11)

        # 左侧：封面图 / 头像圈（固定 60x60）
        if cover_url:
            cover = AsyncImage(source=cover_url, size_hint=(None, None),
                               width=dp(60), height=dp(60),
                               allow_stretch=True, keep_ratio=False)
            with cover.canvas.before:
                Color(*C_PANEL2)
                cover._rb = Rectangle(size=cover.size, pos=cover.pos, radius=[dp(8)])
            cover.bind(size=lambda w, v: setattr(w._rb, "size", v),
                       pos=lambda w, v: setattr(w._rb, "pos", v))
            self.add_widget(cover)
        elif avatar is not None:
            av = Label(text=avatar, font_size="19sp", color=(1, 1, 1, 1),
                       size_hint=(None, None), width=dp(52), height=dp(52),
                       halign="center", valign="middle")
            av.text_size = (dp(52), dp(52))
            with av.canvas.before:
                Color(*(avatar_color or C_ACCENT))
                av._ell = Ellipse(size=(dp(52), dp(52)), pos=av.pos)
            av.bind(pos=lambda w, v: setattr(av._ell, "pos", v),
                    size=lambda w, v: setattr(av._ell, "size", (dp(52), dp(52))))
            self.add_widget(av)

        # 中间信息区（占满剩余宽度）
        info = BoxLayout(orientation="vertical", spacing=dp(2), size_hint_x=1)
        info.add_widget(TLabel(text, "14sp", C_TEXT, bold=True, height=dp(21)))

        if tags:
            tagbar = BoxLayout(orientation="horizontal", size_hint_y=None,
                               height=dp(18), spacing=dp(5))
            for t, warm in tags[:2]:
                cl = Label(text=t, font_size="9sp",
                           color=(C_PRICE if warm else C_ACCENT),
                           size_hint=(None, None), width=dp(50), height=dp(18),
                           halign="center", valign="middle")
                cl.text_size = (dp(50), dp(18))
                with cl.canvas.before:
                    Color(*(C_CHIP_WARM if warm else C_CHIP_BG))
                    cl._rb = Rectangle(size=cl.size, pos=cl.pos, radius=[dp(5)])
                cl.bind(size=lambda w, v, c=cl: setattr(c._rb, "size", v),
                        pos=lambda w, v, c=cl: setattr(c._rb, "pos", v))
                tagbar.add_widget(cl)
            tagbar.add_widget(Widget())
            info.add_widget(tagbar)

        mid = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(22), spacing=dp(4))
        if price:
            mid.add_widget(TLabel(price, "16sp", C_PRICE, bold=True,
                                  height=dp(22), size_hint_x=None, width=dp(110)))
        mid.add_widget(TLabel(sub, "10sp", C_TEXT2, align="right", height=dp(22)))
        info.add_widget(mid)
        self.add_widget(info)

        # 右侧操作列（固定宽度）
        if on_ai:
            ops = BoxLayout(orientation="vertical", size_hint=(None, 1),
                            width=dp(62), spacing=dp(3))
        else:
            ops = BoxLayout(orientation="vertical", size_hint=(None, 1),
                            width=dp(54), spacing=dp(4))
        if on_restore:
            b = accent_btn("恢复", lambda _: on_restore())
            b.font_size = "12sp"
            ops.add_widget(b)
            ops.add_widget(Widget())
        else:
            if on_ai:
                ba = FlatButton(ai_label, lambda _: on_ai(), bg=C_ACCENT,
                                font_size="11sp", radius=6)
                ops.add_widget(ba)
            b1 = FlatButton("改", lambda _: on_edit(), bg=C_CHIP_BG,
                            fg=C_ACCENT2, font_size="12sp", radius=6)
            b2 = FlatButton("删", lambda _: on_delete(), bg=C_DANGER,
                            font_size="12sp", radius=6)
            ops.add_widget(b1)
            ops.add_widget(b2)
        self.add_widget(ops)


class FormField(BoxLayout):
    def __init__(self, label, value="", **kw):
        super().__init__(orientation="horizontal", size_hint_y=None,
                         height=dp(42), spacing=dp(6), **kw)
        self.add_widget(Label(text=label, font_size="13sp", color=C_TEXT2,
                              size_hint_x=0.32, halign="left"))
        self.input = TextInput(text=str(value or ""), font_size="14sp",
                               size_hint_x=0.68, background_color=C_PANEL2,
                               foreground_color=C_TEXT, cursor_color=C_ACCENT2,
                               padding=[dp(8), dp(8)])
        self.add_widget(self.input)

    @property
    def text(self):
        return self.input.text.strip()


class ListPanel(BoxLayout):
    """通用列表页：客户 / 房源。新增只写页面，不改主框架。"""
    def __init__(self, kind, **kw):
        super().__init__(orientation="vertical", **kw)
        self.kind = kind
        self.show_deleted = False

        # 顶部工具条
        bar = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6),
                        padding=[dp(10), dp(8)])
        card_bg(bar, C_PANEL, radius=0)
        self.title = Label(text=("客户" if kind == "customer" else "房源") + "列表",
                           font_size="16sp", color=C_TEXT, bold=True,
                           halign="left", valign="middle")
        self.title.bind(size=lambda w, v: setattr(w, "text_size", (max(v[0], 1), None)))
        btn_add = accent_btn("＋ 新增", self.on_add, size_hint_x=None)
        btn_add.width = dp(74)
        btn_refresh = ghost_btn("刷新", lambda _: self.load(), size_hint_x=None)
        btn_refresh.width = dp(56)
        self.btn_bin = FlatButton("回收站", lambda _: self.toggle_bin(), bg=C_CHIP_BG,
                                  fg=C_ACCENT2, size_hint_x=None, font_size="12sp")
        self.btn_bin.width = dp(66)
        btns = [btn_add, btn_refresh, self.btn_bin]
        self.peer_only = False
        if kind == "house":
            self.btn_peer = FlatButton("仅同行", lambda _: self.toggle_peer(), bg=C_PANEL2,
                                       fg=C_TEXT2, size_hint_x=None, font_size="11sp")
            self.btn_peer.width = dp(56)
            btns.append(self.btn_peer)
        for b in btns:
            b.size_hint_y = None
            b.height = dp(34)
        bar.add_widget(self.title)
        for b in btns:
            bar.add_widget(b)
        self.add_widget(bar)

        self.scroll = ScrollView()
        self.box = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=[dp(4), dp(4)])
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        self.add_widget(self.scroll)

        self.status = Label(text="加载中…", font_size="12sp", color=C_TEXT2,
                            size_hint_y=None, height=dp(24))
        self.add_widget(self.status)
        self.load()

    def toggle_bin(self):
        self.show_deleted = not self.show_deleted
        self.btn_bin.text = "返回列表" if self.show_deleted else "回收站"
        self.btn_bin.color = C_DANGER if self.show_deleted else C_ACCENT2
        self.title.text = ("客户" if self.kind == "customer" else "房源") + (
            "回收站" if self.show_deleted else "列表")
        self.load()

    def toggle_peer(self):
        """仅看同行房源（客户端本地过滤，不重新请求）。"""
        self.peer_only = not self.peer_only
        self.btn_peer.set_bg(C_ACCENT if self.peer_only else C_PANEL2)
        self.btn_peer.color = (1, 1, 1, 1) if self.peer_only else C_TEXT2
        self._render(self._last_rows, None, self._last_count)

    def load(self):
        self.status.text = "加载中…"

        def work():
            try:
                rows = (api.customer_list(self.show_deleted) if self.kind == "customer"
                        else api.house_list(only_deleted=self.show_deleted))
                err, count = None, len(rows)
            except Exception as e:
                rows, err, count = [], str(e), 0
            Clock.schedule_once(lambda _: self._render(rows, err, count), 0)

        threading.Thread(target=work, daemon=True).start()

    def _render(self, rows, err, count):
        self._last_rows = rows or []
        self._last_count = count or 0
        if self.peer_only and self.kind == "house" and not self.show_deleted:
            rows = [r for r in (rows or []) if r.get("is_peer")]
            count = len(rows)
        self.box.clear_widgets()
        if err:
            self.box.add_widget(Label(text="加载失败：" + err, font_size="13sp",
                                      color=C_DANGER, size_hint_y=None, height=dp(48)))
            self.status.text = "未连接"
            return
        self.status.text = "%s · 共 %d 条" % (
            "同行" if self.peer_only and self.kind == "house" else (
                "回收站" if self.show_deleted else "列表"), count)
        if not rows:
            self.box.add_widget(Label(text="暂无数据", font_size="14sp", color=C_TEXT2,
                                      size_hint_y=None, height=dp(56)))
            return
        for r in rows:
            cover = price = tags = avatar = avatar_color = None
            if self.kind == "customer":
                name = r.get("name") or "?"
                title = name
                b = _apk_budget(r)
                budget = ("预算 " + b) if b else "暂无预算"
                sub = "%s · %s" % (budget, r.get("region") or r.get("focus_landmark") or "")
                avatar = name[0]
                avatar_color = C_ACCENT if r.get("customer_type") == "buy" else C_TEAL
                tags = [(("买房" if r.get("customer_type") == "buy" else "租房"),
                         r.get("customer_type") == "buy")]
            else:
                title = r.get("community") or "未命名房源"
                num, unit = _apk_price(r)
                price = (num + unit) if num else ""
                photos = api.photos_of(r)
                cover = api.image_url(photos[0]) if photos else None
                sub = "%s · %s · %d图" % (
                    "买卖" if r.get("deal_type") == "sale" else "租赁",
                    r.get("region") or "", len(photos))
                tags = _apk_tags(r)
                if r.get("is_peer"):
                    tags = [("同行", True)] + tags
            if self.show_deleted:
                row = RecordRow(title, sub, on_restore=lambda rr=r: self.on_restore(rr),
                                cover_url=cover, price=price, tags=tags,
                                avatar=avatar, avatar_color=avatar_color)
            else:
                if self.kind == "customer":
                    row = RecordRow(title, sub,
                                    on_edit=lambda rr=r: self.on_edit(rr),
                                    on_delete=lambda rr=r: self.on_delete(rr),
                                    on_ai=lambda rr=r: self.on_ai(rr),
                                    ai_label="话术",
                                    cover_url=cover, price=price, tags=tags,
                                    avatar=avatar, avatar_color=avatar_color)
                else:
                    row = RecordRow(title, sub,
                                    on_edit=lambda rr=r: self.on_edit(rr),
                                    on_delete=lambda rr=r: self.on_delete(rr),
                                    on_ai=lambda rr=r: self.on_ai(rr),
                                    ai_label="AI",
                                    cover_url=cover, price=price, tags=tags,
                                    avatar=avatar, avatar_color=avatar_color)
            self.box.add_widget(row)

    def on_add(self, _=None):
        if self.show_deleted:
            toast("请先返回列表")
            return
        (self._customer_form if self.kind == "customer" else self._house_form)(None)

    def on_ai(self, r):
        """行内 AI：客户出跟进话术，房源出卖点。"""
        if self.kind == "customer":
            AiPopup("跟进话术",
                    "%s · 依据最近 10 条跟进记录生成" % (r.get("name") or ""),
                    lambda: api.ai_followup(r.get("id"), "wechat"))
        else:
            AiPopup("房源卖点",
                    "%s · 只使用这套房已填的字段" % (r.get("community") or ""),
                    lambda: api.ai_pitch(house_id=r.get("id")))

    def on_edit(self, r):
        (self._customer_form if self.kind == "customer" else self._house_form)(r)

    def on_delete(self, r):
        label = r.get("name") if self.kind == "customer" else r.get("community")
        confirm("确认删除", "将「%s」移入回收站？（可恢复）" % label,
                lambda: self._do_delete(r))

    def _do_delete(self, r):
        try:
            (api.customer_delete if self.kind == "customer" else api.house_delete)(r["id"])
            self.load()
        except Exception as e:
            toast(e)

    def on_restore(self, r):
        try:
            (api.customer_restore if self.kind == "customer" else api.house_restore)(r["id"])
            self.load()
        except Exception as e:
            toast(e)

    def _form_popup(self, title, content, height_hint=0.86):
        return WhitePopup(title=title, content=content, size_hint=(0.94, height_hint),
                     background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)

    def _customer_form(self, r):
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=[dp(6)])
        grid.bind(minimum_height=grid.setter("height"))
        vals = r or {}
        f_name = FormField("姓名 *", vals.get("name"))
        f_phone = FormField("电话", vals.get("phone"))
        f_type = FormField("类型 rent/buy", vals.get("customer_type") or "rent")
        f_budget = FormField("预算(元)", vals.get("rent_budget") or vals.get("budget_total"))
        f_region = FormField("区域", vals.get("region"))
        f_target = FormField("目标位置", vals.get("target_location"))
        f_landmark = FormField("关注地标", vals.get("focus_landmark"))
        f_note = FormField("备注", vals.get("note"))
        for w in (f_name, f_phone, f_type, f_budget, f_region, f_target, f_landmark, f_note):
            grid.add_widget(w)
        self._target_coord = (vals.get("target_lat"), vals.get("target_lng"))
        geo_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34),
                            spacing=dp(6))
        geo_label = TLabel("", "10sp", C_TEXT3, align="left")
        geo_btn = FlatButton("定位(转坐标)", lambda _: self._geocode_target(f_target, geo_label),
                             bg=C_CHIP_BG, fg=C_ACCENT2, font_size="11sp", radius=6)
        geo_btn.size_hint_x = None
        geo_btn.width = dp(96)
        geo_row.add_widget(geo_label)
        geo_row.add_widget(geo_btn)
        grid.add_widget(geo_row)
        scroll.add_widget(grid)
        content = BoxLayout(orientation="vertical", spacing=dp(8))
        content.add_widget(scroll)
        bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        pop = self._form_popup("编辑客户" if r else "新增客户", content, 0.82)
        save = accent_btn("保存", lambda _: self._save_customer(
            r, f_name, f_phone, f_type, f_budget, f_region, f_target, f_landmark, f_note, pop))
        cancel = ghost_btn("取消", lambda _: pop.dismiss())
        bar.add_widget(save)
        bar.add_widget(cancel)
        content.add_widget(bar)
        pop.open()

    def _save_customer(self, r, f_name, f_phone, f_type, f_budget, f_region, f_target,
                       f_landmark, f_note, pop):
        if not f_name.text:
            toast("姓名必填")
            return
        ctype = f_type.text or "rent"
        d = {"name": f_name.text, "phone": f_phone.text, "customer_type": ctype,
             "region": f_region.text, "target_location": f_target.text,
             "focus_landmark": f_landmark.text, "note": f_note.text}
        lat, lng = self._target_coord or (None, None)
        if lat is not None and lng is not None:
            d["target_lat"] = lat
            d["target_lng"] = lng
        if f_budget.text:
            try:
                d["rent_budget" if ctype == "rent" else "budget_total"] = float(f_budget.text)
            except ValueError:
                pass
        try:
            (api.customer_update(r["id"], d) if r else api.customer_create(d))
            pop.dismiss()
            self.load()
        except Exception as e:
            toast(e)

    def _geocode_target(self, f_target, label):
        addr = f_target.text.strip()
        if not addr:
            toast("先填目标位置")
            return
        label.text = "定位中…"
        self._target_coord = (None, None)

        def work():
            try:
                d = api.geo_geocode(addr)
                lat, lng = d.get("lat"), d.get("lng")
                self._target_coord = (lat, lng)
                txt = "已定位 %.4f,%.4f" % (lat, lng) if lat is not None else "定位失败"
            except Exception as e:
                txt = "定位失败：" + str(e)[:20]
            Clock.schedule_once(lambda _: setattr(label, "text", txt), 0)

        threading.Thread(target=work, daemon=True).start()

    def _house_form(self, r):
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=[dp(6)])
        grid.bind(minimum_height=grid.setter("height"))
        vals = r or {}
        f_deal = FormField("类型 rent/sale", vals.get("deal_type") or "rent")
        f_comm = FormField("小区 *", vals.get("community"))
        f_region = FormField("区域", vals.get("region"))
        f_type = FormField("户型", vals.get("house_type"))
        f_area = FormField("面积(㎡)", vals.get("area"))
        f_annual = FormField("年租金", vals.get("annual_rent"))
        f_total = FormField("总价", vals.get("total_price"))
        f_status = FormField("状态", vals.get("status") or "available")
        f_sp = FormField("卖点", vals.get("selling_point"))
        for w in (f_deal, f_comm, f_region, f_type, f_area, f_annual, f_total, f_status, f_sp):
            grid.add_widget(w)
        # 同行标记（P0）：四字段
        ck_peer = CheckRow("同行房源", bool(vals.get("is_peer")))
        f_pc = FormField("同行公司", vals.get("peer_company"))
        f_pct = FormField("同行联系人", vals.get("peer_contact"))
        f_pp = FormField("同行电话", vals.get("peer_phone"))
        grid.add_widget(ck_peer)
        for w in (f_pc, f_pct, f_pp):
            grid.add_widget(w)
        self._existing_urls = api.photos_of(r) if r else []
        self._new_urls = []
        img_info = Label(text="图片：%d 张（点下方选图）" % len(self._existing_urls),
                         font_size="12sp", color=C_TEXT2, size_hint_y=None, height=dp(26))
        grid.add_widget(img_info)
        scroll.add_widget(grid)
        content = BoxLayout(orientation="vertical", spacing=dp(8))
        content.add_widget(scroll)
        btn_pick = accent_btn("＋ 选择房源图片（自动压缩）", lambda _: self._pick_images(img_info))
        btn_pick.size_hint_y = None
        btn_pick.height = dp(42)
        content.add_widget(btn_pick)
        bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        pop = self._form_popup("编辑房源" if r else "新增房源", content, 0.94)
        save = accent_btn("保存", lambda _: self._save_house(
            r, f_deal, f_comm, f_region, f_type, f_area, f_annual, f_total, f_status, f_sp,
            ck_peer, f_pc, f_pct, f_pp, pop))
        cancel = ghost_btn("取消", lambda _: pop.dismiss())
        bar.add_widget(save)
        bar.add_widget(cancel)
        content.add_widget(bar)
        pop.open()

    def _pick_images(self, info_label):
        fc = FileChooserListView(path=os.path.expanduser("~"),
                                 filters=["*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp"],
                                 multiselect=True, background_color=C_PANEL2,
                                 foreground_color=C_TEXT, selection_color=C_ACCENT)
        content = BoxLayout(orientation="vertical", spacing=dp(6))
        content.add_widget(fc)
        bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        pop = WhitePopup(title="选择图片", content=content, size_hint=(0.96, 0.9),
                    background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
        ok = accent_btn("上传所选", lambda _: (pop.dismiss(), self._upload_images(fc.selection, info_label)))
        cancel = ghost_btn("取消", lambda _: pop.dismiss())
        bar.add_widget(ok)
        bar.add_widget(cancel)
        content.add_widget(bar)
        pop.open()

    def _upload_images(self, paths, info_label):
        if not paths:
            return
        info_label.text = "压缩上传中 0/%d…" % len(paths)

        def set_text(t):
            Clock.schedule_once(lambda _: setattr(info_label, "text", t), 0)

        def work():
            ok = 0
            for p in paths:
                try:
                    from PIL import Image, ImageOps
                    img = ImageOps.exif_transpose(Image.open(p))
                    if img.mode in ("RGBA", "LA", "P"):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                        img = bg
                    else:
                        img = img.convert("RGB")
                    w, h = img.size
                    if max(w, h) > 1280:
                        if w >= h:
                            img = img.resize((1280, int(h * 1280 / w)), Image.LANCZOS)
                        else:
                            img = img.resize((int(w * 1280 / h), 1280), Image.LANCZOS)
                    tmp = p + "_pj.jpg"
                    img.save(tmp, format="JPEG", quality=82, optimize=True)
                    try:
                        url = api.upload_image(tmp)
                        if url:
                            self._new_urls.append(url)
                            ok += 1
                    finally:
                        if os.path.exists(tmp):
                            os.remove(tmp)
                except Exception:
                    pass
            set_text("图片：%d 张（本次上传 %d）" % (
                len(self._existing_urls) + len(self._new_urls), ok))

        threading.Thread(target=work, daemon=True).start()

    def _save_house(self, r, f_deal, f_comm, f_region, f_type, f_area, f_annual,
                    f_total, f_status, f_sp, ck_peer, f_pc, f_pct, f_pp, pop):
        if not f_comm.text:
            toast("小区名必填")
            return
        d = {"deal_type": f_deal.text or "rent", "community": f_comm.text,
             "region": f_region.text, "house_type": f_type.text,
             "status": f_status.text or "available", "selling_point": f_sp.text,
             "is_peer": 1 if ck_peer.on else 0,
             "peer_company": f_pc.text, "peer_contact": f_pct.text,
             "peer_phone": f_pp.text}
        for key, fld in (("area", f_area), ("annual_rent", f_annual), ("total_price", f_total)):
            if fld.text:
                try:
                    d[key] = float(fld.text)
                except ValueError:
                    pass
        d["photos"] = list(self._existing_urls) + list(self._new_urls)
        try:
            (api.house_update(r["id"], d) if r else api.house_create(d))
            pop.dismiss()
            self.load()
        except Exception as e:
            toast(e)


class PlaceholderPage(BoxLayout):
    """后续功能占位页：框架就绪，功能替换即可。"""
    def __init__(self, title, desc, **kw):
        super().__init__(orientation="vertical", **kw)
        card_bg(self, C_BG, radius=0)
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(24), dp(40)])
        box.add_widget(Label(text=title, font_size="18sp", color=C_ACCENT, bold=True,
                             size_hint_y=None, height=dp(30)))
        box.add_widget(Label(text=desc, font_size="13sp", color=C_TEXT2,
                             halign="center", valign="middle"))
        self.add_widget(box)


class MinePage(BoxLayout):
    """我的/设置页：服务器地址 + 品牌 + 连接状态。"""
    def __init__(self, app_root, **kw):
        super().__init__(orientation="vertical", **kw)
        self.app_root = app_root
        card_bg(self, C_BG, radius=0)
        pad = BoxLayout(orientation="vertical", spacing=dp(10), padding=[dp(16), dp(20)])

        brand = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(72), spacing=dp(2))
        card_bg(brand, C_PANEL, radius=12)
        brand.add_widget(TLabel("贵江信息部", "18sp", C_TEXT, bold=True, height=dp(28)))
        brand.add_widget(TLabel("李经理  17328435631", "11sp", C_TEXT2, height=dp(20)))
        pad.add_widget(brand)

        btn = FlatButton("服务器设置 →", self.on_settings, bg=C_PANEL, fg=C_TEXT,
                         font_size="14sp", radius=10, size_hint_y=None, height=dp(48))
        pad.add_widget(btn)

        self.status = Label(text="连接检测中…", font_size="12sp", color=C_TEXT2,
                            size_hint_y=None, height=dp(30), halign="left")
        self.status.bind(size=lambda w, v: setattr(w, "text_size", (max(v[0], 1), None)))
        pad.add_widget(self.status)
        info = Label(text="数字由数据库本地计算 · AI 只润色文字\n图片本地压缩后上传",
                     font_size="11sp", color=C_TEXT3, halign="left", valign="top")
        info.bind(size=lambda w, v: setattr(w, "text_size", (max(v[0], 1), v[1])))
        pad.add_widget(info)
        self.add_widget(pad)
        self.refresh_status()

    def refresh_status(self):
        def work():
            try:
                h = api.health()
                txt = "● 已连接服务器 · v%s" % h.get("version", "?")
            except Exception as e:
                txt = "○ 未连接：" + str(e)[:24]
            Clock.schedule_once(lambda _: setattr(self.status, "text", txt), 0)
        threading.Thread(target=work, daemon=True).start()

    def on_settings(self, _):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(10)])
        content.add_widget(Label(text="服务器地址（http://IP 或域名）", font_size="14sp",
                                 color=C_TEXT, halign="left"))
        ti = TextInput(text=api.base_url(), font_size="15sp", size_hint_y=None,
                       height=dp(44), background_color=C_PANEL2,
                       foreground_color=C_TEXT, cursor_color=C_ACCENT2)
        content.add_widget(ti)
        pop = WhitePopup(title="设置", content=content, size_hint=(0.9, 0.46),
                    background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)

        def save(_):
            addr = ti.text.strip()
            if not addr:
                return
            conf = api.load_conf()
            conf["server_base"] = addr
            api.save_conf(conf)
            pop.dismiss()
            self.status.text = "地址已更新，重启应用生效"

        b = accent_btn("保存", save)
        b.size_hint_y = None
        b.height = dp(44)
        content.add_widget(Widget())
        content.add_widget(b)
        pop.open()


# ============ 日期小工具（后端日期可能是 RFC822 或 ISO） ============
def _parse_dt(v):
    if not v:
        return None
    s = str(v).strip()
    if "," in s and "GMT" in s.upper():
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(s).replace(tzinfo=None)
        except Exception:
            return None
    s = s.replace("T", " ")
    for ln, fmt in ((19, "%Y-%m-%d %H:%M:%S"), (16, "%Y-%m-%d %H:%M"), (10, "%Y-%m-%d")):
        try:
            return datetime.datetime.strptime(s[:ln], fmt)
        except ValueError:
            continue
    return None


def _human_day(d):
    if not d:
        return "—"
    today = datetime.date.today()
    day = d.date() if isinstance(d, datetime.datetime) else d
    delta = (day - today).days
    if delta < 0:
        return "逾期%d天" % (-delta)
    if delta == 0:
        return "今天"
    if delta == 1:
        return "明天"
    if delta == 2:
        return "后天"
    return "%02d-%02d" % (day.month, day.day)


def _day_color(d):
    if not d:
        return C_TEXT3
    today = datetime.date.today()
    day = d.date() if isinstance(d, datetime.datetime) else d
    delta = (day - today).days
    if delta < 0:
        return C_DANGER
    if delta == 0:
        return C_PRICE
    if delta <= 2:
        return C_ACCENT
    return C_TEXT2


# ============ 日程页 ============
class ScheduleRow(BoxLayout):
    """一条日程：左侧日期块 + 中间信息 + 右侧操作。"""

    def __init__(self, kind, row, on_action, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(78),
                         spacing=dp(8), padding=[dp(10), dp(8)], **kw)
        card_bg(self, C_PANEL, radius=10)

        when = _parse_dt(row.get("next_follow_date") if kind == "todo" else row.get("plan_at"))
        datebox = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(60), spacing=0)
        datebox.add_widget(TLabel(_human_day(when), "11sp", _day_color(when), bold=True,
                                  align="center", height=dp(22)))
        datebox.add_widget(TLabel("跟进" if kind == "todo" else "带看", "9sp", C_TEXT3,
                                  align="center", height=dp(16)))
        self.add_widget(datebox)

        info = BoxLayout(orientation="vertical", spacing=dp(2), size_hint_x=1)
        if kind == "todo":
            name = str(row.get("name") or "未命名")
            sub = str(row.get("content") or "").strip() or "未填跟进内容"
            sub2 = "%s · %s" % (row.get("phone") or "", row.get("region") or "")
        else:
            name = str(row.get("customer_name") or "客户")
            houses = "、".join(row.get("house_labels") or []) or "未选房源"
            sub = houses
            sub2 = str(row.get("note") or "").strip() or (row.get("customer_phone") or "")
        info.add_widget(TLabel(name, "14sp", C_TEXT, bold=True, height=dp(21)))
        info.add_widget(TLabel(sub, "10sp", C_TEXT2, height=dp(18)))
        info.add_widget(TLabel(sub2, "9sp", C_TEXT3, height=dp(16)))
        self.add_widget(info)

        btnbox = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(52))
        btnbox.add_widget(Widget())
        b = FlatButton("记录" if kind == "todo" else "完成",
                       lambda _: on_action(kind, row),
                       bg=C_CHIP_BG if kind == "todo" else C_SUCCESS,
                       fg=C_ACCENT2 if kind == "todo" else (1, 1, 1, 1),
                       font_size="11sp", radius=6)
        b.size_hint_y = None
        b.height = dp(32)
        btnbox.add_widget(b)
        btnbox.add_widget(Widget())
        self.add_widget(btnbox)


class SchedulePane(BoxLayout):
    """带看日程：待跟进 + 带看预约，按日期排序。"""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        bar = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6),
                        padding=[dp(10), dp(8)])
        card_bg(bar, C_PANEL, radius=0)
        bar.add_widget(TLabel("带看日程", "16sp", C_TEXT, bold=True))
        visit = accent_btn("发起带看", self.on_visit_plan, size_hint_x=None)
        visit.width = dp(78)
        add = accent_btn("＋跟进", self.on_add, size_hint_x=None)
        add.width = dp(70)
        ref = ghost_btn("刷新", lambda _: self.load(), size_hint_x=None)
        ref.width = dp(54)
        for b in (visit, add, ref):
            b.size_hint_y = None
            b.height = dp(34)
        bar.add_widget(visit)
        bar.add_widget(add)
        bar.add_widget(ref)
        self.add_widget(bar)

        strip = BoxLayout(size_hint_y=None, height=dp(30), padding=[dp(12), 0])
        card_bg(strip, C_BG, radius=0)
        self.sum = TLabel("加载中…", "11sp", C_TEXT2)
        strip.add_widget(self.sum)
        self.add_widget(strip)

        self.scroll = ScrollView()
        self.box = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=[dp(4), dp(2)])
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        self.add_widget(self.scroll)

        self.status = TLabel("", "10sp", C_TEXT3, height=dp(22))
        self.add_widget(self.status)
        self.load()

    # ---------- 数据 ----------
    def load(self):
        self.sum.text = "加载中…"
        self.status.text = ""

        def work():
            try:
                data = api.schedule(14)
                err = None
            except Exception as e:
                data, err = None, str(e)
            Clock.schedule_once(lambda _: self._render(data, err), 0)

        threading.Thread(target=work, daemon=True).start()

    def _render(self, data, err):
        self.box.clear_widgets()
        if err:
            msg = ("服务器后端还是旧版本，没有日程接口" if "404" in err
                   else "加载失败：" + err[:40])
            self.sum.text = msg
            self.box.add_widget(TLabel("更新服务器后端后即可看到待跟进与带看", "12sp",
                                       C_TEXT2, align="center", height=dp(56)))
            return
        todos = data.get("todos") or []
        visits = data.get("visits") or []
        s = data.get("summary") or {}
        self.sum.text = "逾期 %d · 今天 %d · 本周 %d · 今日带看 %d" % (
            s.get("overdue", 0), s.get("today", 0), s.get("week", 0),
            s.get("visit_today", 0))
        rows = []
        for t in todos:
            rows.append((_parse_dt(t.get("next_follow_date")) or datetime.datetime(2099, 1, 1),
                         "todo", t))
        for v in visits:
            rows.append((_parse_dt(v.get("plan_at")) or datetime.datetime(2099, 1, 1),
                         "visit", v))
        rows.sort(key=lambda x: x[0])
        if not rows:
            self.box.add_widget(TLabel("近两周没有待跟进和带看", "13sp", C_TEXT2,
                                       align="center", height=dp(60)))
            self.status.text = "点「＋跟进」记录一次联系，设的下次日期会出现在这里"
            return
        for _d, kind, r in rows:
            self.box.add_widget(ScheduleRow(kind, r, self.on_action))
        self.status.text = "共 %d 条 · 下拉刷新" % len(rows)

    # ---------- 动作 ----------
    def on_action(self, kind, row):
        if kind == "todo":
            self._follow_form(row, row.get("customer_id"), str(row.get("name") or "客户"))
        else:
            self._finish_form(row)

    def on_add(self, _=None):
        def work():
            try:
                rows = api.customer_list(False)
            except Exception as e:
                Clock.schedule_once(lambda _: toast("读取客户失败：" + str(e)[:30]), 0)
                return
            Clock.schedule_once(lambda _: self._pick_customer(rows), 0)

        threading.Thread(target=work, daemon=True).start()

    def on_visit_plan(self, _=None):
        """发起带看：选客户 → 勾多套房 → 定时间 → 生成看房计划 → 写带看预约。"""
        def work():
            try:
                rows = api.customer_list(False)
            except Exception as e:
                Clock.schedule_once(lambda _: toast("读取客户失败：" + str(e)[:30]), 0)
                return
            Clock.schedule_once(lambda _: self._pick_visit_customer(rows), 0)

        threading.Thread(target=work, daemon=True).start()

    def _pick_visit_customer(self, rows):
        if not rows:
            toast("还没有客户，先去「客户」里新增")
            return
        content = BoxLayout(orientation="vertical", spacing=dp(4), padding=[dp(8), dp(8)])
        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter("height"))
        pop = WhitePopup(title="发起带看 · 选客户", content=content, size_hint=(0.92, 0.8),
                         background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
        for r in rows:
            b = FlatButton("%s  %s" % (r.get("name") or "未命名", r.get("phone") or ""),
                           lambda _, rr=r: (pop.dismiss(), self._pick_visit_houses(rr)),
                           bg=C_PANEL2, fg=C_TEXT, font_size="13sp", radius=8)
            b.size_hint_y = None
            b.height = dp(42)
            grid.add_widget(b)
        scroll.add_widget(grid)
        content.add_widget(scroll)
        pop.open()

    def _pick_visit_houses(self, customer):
        deal = "sale" if (customer.get("customer_type") == "buy") else "rent"

        def work():
            try:
                rows = api.house_list(deal_type=deal)
            except Exception as e:
                Clock.schedule_once(lambda _: toast("读取房源失败：" + str(e)[:30]), 0)
                return
            Clock.schedule_once(lambda _: self._multi_pick_houses(customer, rows), 0)

        threading.Thread(target=work, daemon=True).start()

    def _multi_pick_houses(self, customer, rows):
        if not rows:
            toast("还没有%s房源，先去「房源」里新增" %
                  ("买卖" if customer.get("customer_type") == "buy" else "租赁"))
            return
        self._visit_customer = customer
        self._visit_picked = []
        self._visit_rows = {r.get("id"): r for r in rows}
        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=[dp(8), dp(8)])
        info = TLabel("客户：%s · 点选要看哪几套" % (customer.get("name") or ""),
                      "11sp", C_TEXT2, height=dp(22))
        content.add_widget(info)
        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter("height"))
        pop = WhitePopup(title="勾选房源（按点选顺序）", content=content, size_hint=(0.94, 0.86),
                         background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
        for r in rows:
            num, unit = _apk_price(r)
            label = "%s · %s %s%s" % (r.get("community") or "未命名",
                                      r.get("house_type") or "", num, unit)
            b = FlatButton(label, lambda _, rr=r: self._toggle_house(rr, b, info),
                           bg=C_PANEL2, fg=C_TEXT, font_size="12sp", radius=8)
            b.size_hint_y = None
            b.height = dp(40)
            grid.add_widget(b)
        scroll.add_widget(grid)
        content.add_widget(scroll)
        bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        bar.add_widget(accent_btn("下一步：定时间",
                                  lambda _: (pop.dismiss(), self._visit_datetime())))
        bar.add_widget(ghost_btn("取消", lambda _: pop.dismiss()))
        content.add_widget(bar)
        pop.open()

    def _toggle_house(self, r, btn, info):
        if r.get("id") in self._visit_picked:
            self._visit_picked.remove(r.get("id"))
            btn.set_bg(C_PANEL2)
            btn.color = C_TEXT
        else:
            self._visit_picked.append(r.get("id"))
            btn.set_bg(C_CHIP_BG)
            btn.color = C_ACCENT2
        info.text = "客户：%s · 已选 %d 套" % (
            self._visit_customer.get("name") or "", len(self._visit_picked))

    def _visit_datetime(self):
        if not self._visit_picked:
            toast("至少选一套房")
            return
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(10), dp(10)])
        content.add_widget(TLabel("带看时间（格式 2026-11-19 10:00）", "11sp", C_TEXT3, height=dp(20)))
        ti = TextInput(text=(datetime.date.today() + datetime.timedelta(days=1)).isoformat() + " 10:00",
                       font_size="14sp", background_color=C_PANEL2, foreground_color=C_TEXT,
                       cursor_color=C_ACCENT, padding=[dp(8), dp(10)])
        ti.size_hint_y = None
        ti.height = dp(40)
        content.add_widget(ti)
        content.add_widget(TLabel("备注（接送/钥匙等）", "11sp", C_TEXT3, height=dp(20)))
        note = TextInput(font_size="14sp", background_color=C_PANEL2, foreground_color=C_TEXT,
                         cursor_color=C_ACCENT, padding=[dp(8), dp(8)])
        note.size_hint_y = None
        note.height = dp(70)
        content.add_widget(note)
        pop = WhitePopup(title="定时间", content=content, size_hint=(0.9, 0.54),
                         background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
        bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        bar.add_widget(accent_btn("生成看房计划",
                                  lambda _: self._save_visit(ti.text, note.text, pop)))
        bar.add_widget(ghost_btn("取消", lambda _: pop.dismiss()))
        content.add_widget(bar)
        pop.open()

    def _save_visit(self, plan_at, note, pop):
        try:
            api.visit_create(self._visit_customer.get("id"), self._visit_picked,
                             plan_at=plan_at.strip() or None, note=note.strip())
        except Exception as e:
            toast(str(e)[:60])
            return
        pop.dismiss()
        self._show_plan(plan_at, note)
        self.load()

    def _show_plan(self, plan_at, note):
        c = self._visit_customer
        lines = ["【看房计划】", "",
                 "客户：%s%s" % (c.get("name") or "",
                                 (" " + c.get("phone")) if c.get("phone") else "")]
        if c.get("target_location"):
            lines.append("出发地：%s" % c.get("target_location"))
        lines.append("时间：%s" % (plan_at or "待定"))
        lines.append("")
        for i, hid in enumerate(self._visit_picked, 1):
            h = self._visit_rows.get(hid) or {}
            num, unit = _apk_price(h)
            lines.append("%d. %s %s %s %s%s" % (
                i, h.get("community") or "未命名", h.get("house_type") or "",
                h.get("region") or "", num, unit))
        if note.strip():
            lines.append("")
            lines.append("备注：%s" % note.strip())
        txt = "\n".join(lines)
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(10), dp(10)])
        scroll = ScrollView()
        out = Label(text=txt, font_size="12sp", color=C_TEXT, halign="left", valign="top",
                    size_hint_y=None)
        out.bind(width=lambda w, v: setattr(w, "text_size", (max(int(v), 1), None)))
        out.bind(texture_size=lambda w, v: setattr(w, "height", v[1] + dp(12)))
        scroll.add_widget(out)
        content.add_widget(scroll)
        bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        bar.add_widget(accent_btn("复制发微信",
                                  lambda _: (Clipboard.copy(txt), toast("已复制，去微信粘贴"))))
        bar.add_widget(ghost_btn("关闭", lambda _: pop.dismiss()))
        content.add_widget(bar)
        pop = WhitePopup(title="看房计划", content=content, size_hint=(0.94, 0.8),
                         background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
        pop.open()

    def _pick_customer(self, rows):
        if not rows:
            toast("还没有客户，先去「客户」里新增")
            return
        content = BoxLayout(orientation="vertical", spacing=dp(4), padding=[dp(8), dp(8)])
        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter("height"))
        pop = WhitePopup(title="选择客户", content=content, size_hint=(0.92, 0.8),
                    background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)

        def choose(r):
            pop.dismiss()
            self._follow_form(r, r.get("id"), str(r.get("name") or "客户"))

        for r in rows:
            label = "%s  %s" % (r.get("name") or "未命名", r.get("phone") or "")
            b = FlatButton(label, lambda _, rr=r: choose(rr), bg=C_PANEL2, fg=C_TEXT,
                           font_size="13sp", radius=8)
            b.size_hint_y = None
            b.height = dp(42)
            grid.add_widget(b)
        scroll.add_widget(grid)
        content.add_widget(scroll)
        pop.open()

    def _follow_form(self, customer, cid, name):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(10), dp(10)])
        content.add_widget(TLabel("客户：%s" % name, "13sp", C_TEXT, bold=True, height=dp(22)))
        ti = TextInput(hint_text="这次聊了什么 / 约了什么", font_size="14sp",
                       background_color=C_PANEL2, foreground_color=C_TEXT,
                       cursor_color=C_ACCENT, padding=[dp(8), dp(8)])
        ti.size_hint_y = None
        ti.height = dp(84)
        content.add_widget(ti)
        nxt = TextInput(text=(datetime.date.today() + datetime.timedelta(days=3)).isoformat(),
                        font_size="14sp", background_color=C_PANEL2, foreground_color=C_TEXT,
                        cursor_color=C_ACCENT, padding=[dp(8), dp(10)])
        nxt.size_hint_y = None
        nxt.height = dp(40)
        content.add_widget(TLabel("下次跟进日期（留空=不再提醒）", "10sp", C_TEXT3, height=dp(18)))
        content.add_widget(nxt)
        content.add_widget(Widget())
        pop = WhitePopup(title="记录跟进", content=content, size_hint=(0.92, 0.62),
                    background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
        bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        save = accent_btn("保存", lambda _: self._save_follow(cid, ti.text, nxt.text, pop))
        bar.add_widget(save)
        bar.add_widget(ghost_btn("取消", lambda _: pop.dismiss()))
        content.add_widget(bar)
        pop.open()

    def _save_follow(self, cid, text, nxt, pop):
        if not text.strip():
            toast("跟进内容不能为空")
            return
        nfd = nxt.strip()[:10] or None
        try:
            api.followup_create(cid, "phone", text.strip(), nfd)
            pop.dismiss()
            self.load()
        except Exception as e:
            toast(e)

    def _finish_form(self, row):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(10), dp(10)])
        content.add_widget(TLabel("带看结果（客户反馈、意向、下一步）", "11sp", C_TEXT3, height=dp(20)))
        ti = TextInput(font_size="14sp", background_color=C_PANEL2, foreground_color=C_TEXT,
                       cursor_color=C_ACCENT, padding=[dp(8), dp(8)])
        content.add_widget(ti)
        pop = WhitePopup(title="完成带看", content=content, size_hint=(0.9, 0.5),
                    background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
        bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))

        def save(_):
            try:
                api.visit_done(row.get("id"), ti.text.strip())
                pop.dismiss()
                self.load()
            except Exception as e:
                toast(e)

        bar.add_widget(accent_btn("保存", save))
        bar.add_widget(ghost_btn("取消", lambda _: pop.dismiss()))
        content.add_widget(bar)
        pop.open()


# ============ 计算工具 ============
def _m_equal(principal, rate, years):
    """等额本息：返回 (月供, 总利息, 还款总额)。"""
    n = max(1, int(round(years * 12)))
    r = rate / 100.0 / 12.0
    if r <= 0:
        return principal / n, 0.0, principal
    f = (1 + r) ** n
    m = principal * r * f / (f - 1)
    return m, m * n - principal, m * n


def _m_principal(principal, rate, years):
    """等额本金：返回 (首月, 末月, 总利息, 总额)。"""
    n = max(1, int(round(years * 12)))
    r = rate / 100.0 / 12.0
    per = principal / n
    interest = principal * r * (n + 1) / 2.0
    return per + principal * r, per + per * r, interest, principal + interest


def _tax(price, area, first, full2, full5, agent_rate):
    if first == "3":
        deed = 0.03
    elif first == "2":
        deed = 0.01 if area <= 140 else 0.02
    else:
        deed = 0.01 if area <= 140 else 0.015
    d = price * deed
    v = 0.0 if full2 else price * 0.053
    i = 0.0 if full5 else price * 0.01
    a = price * agent_rate / 100.0
    return d, v, i, a, d + v + i + a


def _money(v, digits=0):
    try:
        return ("{:,.%df}" % digits).format(float(v))
    except (TypeError, ValueError):
        return "—"


def _wan(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return "{:,.1f} 万".format(f / 10000.0) if abs(f) >= 10000 else "{:,.0f} 元".format(f)


class NumRow(BoxLayout):
    """一行数字输入：标签 + 输入框 + 单位。"""

    def __init__(self, label, value, suffix="", on_change=None, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(38),
                         spacing=dp(6), **kw)
        self.add_widget(TLabel(label, "12sp", C_TEXT2, size_hint_x=None, width=dp(92),
                               height=dp(38)))
        self.ti = TextInput(text=str(value), font_size="14sp", multiline=False,
                            input_type="number", background_color=C_PANEL2,
                            foreground_color=C_TEXT, cursor_color=C_ACCENT,
                            padding=[dp(8), dp(9)], size_hint_x=1)
        self.add_widget(self.ti)
        self.add_widget(TLabel(suffix, "10sp", C_TEXT3, size_hint_x=None, width=dp(52),
                               height=dp(38)))
        if on_change:
            self.ti.bind(text=lambda *a: on_change())

    @property
    def value(self):
        try:
            return float((self.ti.text or "").strip() or 0)
        except ValueError:
            return 0.0


class SegRow(BoxLayout):
    """分段选择：几个互斥选项，选中高亮。"""

    def __init__(self, options, on_change=None, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(34),
                         spacing=dp(6), **kw)
        self.on_change = on_change
        self.sel = 0
        self.buttons = []
        for i, text in enumerate(options):
            b = FlatButton(text, lambda _, i=i: self.select(i), bg=C_PANEL2, fg=C_TEXT2,
                           font_size="11sp", radius=6)
            self.buttons.append(b)
            self.add_widget(b)
        self.select(0, notify=False)

    def select(self, i, notify=True):
        self.sel = i
        for n, b in enumerate(self.buttons):
            b.set_bg(C_ACCENT if n == i else C_PANEL2)
            b.color = (1, 1, 1, 1) if n == i else C_TEXT2
        if notify and self.on_change:
            self.on_change()


class CheckRow(FlatButton):
    """开关型按钮：点一下切换 是/否。"""

    def __init__(self, label, default=False, on_change=None, **kw):
        super().__init__("", lambda _: self.flip(), bg=C_PANEL2, fg=C_TEXT2,
                         font_size="11sp", radius=6, size_hint_y=None, height=dp(34), **kw)
        self.label = label
        self.on = bool(default)
        self.on_change = on_change
        self._sync()

    def _sync(self):
        self.text = "%s：%s" % (self.label, "是" if self.on else "否")
        self.set_bg(C_CHIP_BG if self.on else C_PANEL2)
        self.color = C_ACCENT2 if self.on else C_TEXT2

    def flip(self, *a):
        self.on = not self.on
        self._sync()
        if self.on_change:
            self.on_change()


class ResultBox(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(92),
                         spacing=dp(2), padding=[dp(10), dp(8)], **kw)
        card_bg(self, C_PANEL2, radius=8)
        self.cap = TLabel("", "10sp", C_TEXT3, height=dp(16))
        self.big = TLabel("—", "21sp", C_PRICE, bold=True, height=dp(30))
        self.detail = TLabel("", "10sp", C_TEXT2, height=dp(34))
        self.add_widget(self.cap)
        self.add_widget(self.big)
        self.add_widget(self.detail)


def _card_title(text):
    return TLabel(text, "14sp", C_TEXT, bold=True, height=dp(24))


class MortgageCard(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(346),
                         spacing=dp(6), padding=[dp(10), dp(10)], **kw)
        card_bg(self, C_PANEL, radius=12)
        self.add_widget(_card_title("月供计算"))
        self.price = NumRow("总价(万)", 100, "万", self.calc)
        self.down = NumRow("首付比例", 30, "%", self.calc)
        self.years = NumRow("贷款年限", 30, "年", self.calc)
        self.rate = NumRow("年利率", 3.1, "%", self.calc)
        self.seg = SegRow(["等额本息", "等额本金"], self.calc)
        for w in (self.price, self.down, self.years, self.rate, self.seg):
            self.add_widget(w)
        self.res = ResultBox()
        self.add_widget(self.res)
        self.calc()

    def calc(self):
        price = self.price.value * 10000.0
        principal = price * (1 - self.down.value / 100.0)
        if self.seg.sel == 0:
            m, interest, total = _m_equal(principal, self.rate.value, self.years.value)
            self.res.cap.text = "每月月供（等额本息）"
            self.res.big.text = _money(m) + " 元"
            self.res.detail.text = "贷款 %s · 总利息 %s · 还款 %s" % (
                _wan(principal), _wan(interest), _wan(total))
        else:
            first, last, interest, total = _m_principal(
                principal, self.rate.value, self.years.value)
            self.res.cap.text = "首月月供（等额本金）"
            self.res.big.text = _money(first) + " 元"
            self.res.detail.text = "末月 %s · 总利息 %s" % (
                _money(last), _wan(interest))


class TaxCard(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(392),
                         spacing=dp(6), padding=[dp(10), dp(10)], **kw)
        card_bg(self, C_PANEL, radius=12)
        self.add_widget(_card_title("购房税费（二手房）"))
        self.price = NumRow("成交价(万)", 100, "万", self.calc)
        self.area = NumRow("建筑面积", 90, "㎡", self.calc)
        self.first = SegRow(["首套", "二套", "三套+"], self.calc)
        self.full2 = CheckRow("满 2 年（免增值税）", True, self.calc)
        self.full5 = CheckRow("满五唯一（免个税）", False, self.calc)
        self.agent = NumRow("中介费率", 1.5, "%", self.calc)
        for w in (self.price, self.area, self.first, self.full2, self.full5, self.agent):
            self.add_widget(w)
        self.res = ResultBox()
        self.add_widget(self.res)
        self.calc()

    def calc(self):
        price = self.price.value * 10000.0
        first = ["1", "2", "3"][self.first.sel]
        d, v, i, a, total = _tax(price, self.area.value, first, self.full2.on,
                                 self.full5.on, self.agent.value)
        self.res.cap.text = "一次性支出合计（税费+中介）"
        self.res.big.text = _wan(total)
        self.res.detail.text = "契税 %s · 增值 %s · 个税 %s · 中介 %s" % (
            _money(d), _money(v), _money(i), _money(a))


class YieldCard(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(292),
                         spacing=dp(6), padding=[dp(10), dp(10)], **kw)
        card_bg(self, C_PANEL, radius=12)
        self.add_widget(_card_title("租金回报"))
        self.price = NumRow("总价(万)", 60, "万", self.calc)
        self.rent = NumRow("月租金", 1800, "元", self.calc)
        self.vacant = NumRow("年空置", 1, "月", self.calc)
        for w in (self.price, self.rent, self.vacant):
            self.add_widget(w)
        self.res = ResultBox()
        self.add_widget(self.res)
        self.calc()

    def calc(self):
        price = self.price.value * 10000.0
        annual = self.rent.value * 12
        if price <= 0:
            self.res.big.text = "—"
            self.res.detail.text = "填总价后自动算"
            return
        gross = annual / price * 100.0
        net_rent = annual * (1 - min(self.vacant.value, 12) / 12.0)
        net = net_rent / price * 100.0
        self.res.cap.text = "净租金回报率"
        self.res.big.text = "%.2f %%" % net
        self.res.detail.text = "毛回报 %.2f%% · 年租金 %s · 回本 %s" % (
            gross, _money(annual), ("%.0f 年" % (price / net_rent)) if net_rent > 0 else "—")


class BuyTotalCard(BoxLayout):
    """买房总账：首付 + 税费中介 + 首月月供 一次性算清。"""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(432),
                         spacing=dp(6), padding=[dp(10), dp(10)], **kw)
        card_bg(self, C_PANEL, radius=12)
        self.add_widget(_card_title("买房总账（首付+税费+月供）"))
        self.price = NumRow("总价(万)", 100, "万", self.calc)
        self.down = NumRow("首付比例", 30, "%", self.calc)
        self.years = NumRow("贷款年限", 30, "年", self.calc)
        self.rate = NumRow("年利率", 3.1, "%", self.calc)
        self.area = NumRow("建筑面积", 90, "㎡", self.calc)
        self.first = SegRow(["首套", "二套", "三套+"], self.calc)
        self.full2 = CheckRow("满 2 年（免增值税）", True, self.calc)
        self.full5 = CheckRow("满五唯一（免个税）", False, self.calc)
        self.agent = NumRow("中介费率", 1.5, "%", self.calc)
        for w in (self.price, self.down, self.years, self.rate, self.area,
                  self.first, self.full2, self.full5, self.agent):
            self.add_widget(w)
        self.res = ResultBox()
        self.add_widget(self.res)
        self.calc()

    def calc(self):
        price = self.price.value * 10000.0
        down = price * self.down.value / 100.0
        principal = price - down
        first = ["1", "2", "3"][self.first.sel]
        d, v, i, a, tax_total = _tax(price, self.area.value, first,
                                     self.full2.on, self.full5.on, self.agent.value)
        m, _, _ = _m_equal(principal, self.rate.value, self.years.value)
        total = down + tax_total + m
        self.res.cap.text = "首期总支出（首付+税费中介+首月月供）"
        self.res.big.text = _wan(total)
        self.res.detail.text = "首付 %s · 税费中介 %s · 月供 %s" % (
            _wan(down), _wan(tax_total), _money(m))


class ToolsPane(BoxLayout):
    """计算工具：月供 / 税费 / 租金回报，全本地公式。"""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        bar = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(12), dp(8)])
        card_bg(bar, C_PANEL, radius=0)
        bar.add_widget(TLabel("计算工具", "16sp", C_TEXT, bold=True))
        self.add_widget(bar)

        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=[dp(6), dp(6)])
        grid.bind(minimum_height=grid.setter("height"))
        grid.add_widget(BuyTotalCard())
        grid.add_widget(MortgageCard())
        grid.add_widget(TaxCard())
        grid.add_widget(YieldCard())
        grid.add_widget(TLabel("结果为公式估算值，签合同前以银行批贷、税务核定为准",
                               "9sp", C_TEXT3, align="center", height=dp(30)))
        scroll.add_widget(grid)
        self.add_widget(scroll)


class AIPostPane(BoxLayout):
    """AI 图文作品：选房源 → 勾平台 → 生成文案 + 去重图（只生成不发布）。"""
    PLATFORMS = [("xiaohongshu", "小红书"), ("douyin", "抖音"), ("wechat", "朋友圈")]

    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        bar = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(12), dp(8)])
        card_bg(bar, C_PANEL, radius=0)
        bar.add_widget(TLabel("AI 图文作品", "16sp", C_TEXT, bold=True))
        self.add_widget(bar)

        self.house = None
        self.picked_plats = set()
        self._last = ""

        self.house_btn = FlatButton("1. 选择房源", self.pick_house, bg=C_PANEL, fg=C_TEXT,
                                    font_size="14sp", radius=10, size_hint_y=None, height=dp(46))
        plat = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6), padding=[dp(0), 0])
        plat.add_widget(TLabel("2. 平台：", "12sp", C_TEXT2, size_hint_x=None, width=dp(64)))
        self.plat_sel = {}
        for key, name in self.PLATFORMS:
            b = FlatButton(name, lambda _, k=key: self._toggle_plat(k), bg=C_PANEL2, fg=C_TEXT2,
                           font_size="11sp", radius=6)
            self.plat_sel[key] = b
            plat.add_widget(b)
        self.gen_btn = accent_btn("3. 生成文案 + 去重图", self.generate)
        self.gen_btn.size_hint_y = None
        self.gen_btn.height = dp(46)
        self.copy_btn = ghost_btn("复制全文", self.copy_all)
        self.copy_btn.size_hint_y = None
        self.copy_btn.height = dp(40)

        self.out = Label(text="选择房源和平台后点生成。AI 只润色文字，不编数字。",
                         font_size="12sp", color=C_TEXT3, halign="left", valign="top",
                         size_hint_y=None)
        self.out.bind(width=lambda w, v: setattr(w, "text_size", (max(int(v), 1), None)))
        self.out.bind(texture_size=lambda w, v: setattr(w, "height", v[1] + dp(12)))
        self.scroll = ScrollView()
        self.scroll.add_widget(self.out)

        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(12), dp(10)])
        box.add_widget(self.house_btn)
        box.add_widget(plat)
        box.add_widget(self.gen_btn)
        box.add_widget(self.copy_btn)
        box.add_widget(self.scroll)
        self.add_widget(box)
        self._toggle_plat("xiaohongshu")

    def _toggle_plat(self, key):
        if key in self.picked_plats:
            self.picked_plats.discard(key)
            self.plat_sel[key].set_bg(C_PANEL2)
            self.plat_sel[key].color = C_TEXT2
        else:
            self.picked_plats.add(key)
            self.plat_sel[key].set_bg(C_ACCENT)
            self.plat_sel[key].color = (1, 1, 1, 1)

    def copy_all(self, *_):
        if not self._last:
            toast("还没有内容")
            return
        Clipboard.copy(self._last)
        toast("已复制")

    def pick_house(self, _=None):
        def work():
            try:
                rows = api.house_list()
            except Exception as e:
                Clock.schedule_once(lambda _: toast("读取房源失败：" + str(e)[:30]), 0)
                return
            Clock.schedule_once(lambda _: self._show_houses(rows), 0)

        threading.Thread(target=work, daemon=True).start()

    def _show_houses(self, rows):
        if not rows:
            toast("还没有房源")
            return
        content = BoxLayout(orientation="vertical", spacing=dp(4), padding=[dp(8), dp(8)])
        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter("height"))
        pop = WhitePopup(title="选择房源", content=content, size_hint=(0.92, 0.8),
                         background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)

        def choose(r):
            self.house = r
            self.house_btn.text = "1. 房源：" + (r.get("community") or "未命名")
            pop.dismiss()

        for r in rows:
            num, unit = _apk_price(r)
            b = FlatButton("%s · %s%s" % (r.get("community") or "未命名", num, unit),
                           lambda _, rr=r: choose(rr),
                           bg=C_PANEL2, fg=C_TEXT, font_size="12sp", radius=8)
            b.size_hint_y = None
            b.height = dp(42)
            grid.add_widget(b)
        scroll.add_widget(grid)
        content.add_widget(scroll)
        pop.open()

    def generate(self, _=None):
        if not self.house:
            toast("先选房源")
            return
        if not self.picked_plats:
            toast("先选平台")
            return
        self.out.text = "生成中…（文案几秒，生图约 15～30 秒）"
        self.out.color = C_TEXT2
        hid = self.house.get("id")
        plats = list(self.picked_plats)

        def work():
            lines = []
            for p in plats:
                pname = dict(self.PLATFORMS).get(p, p)
                try:
                    cp = api.ai_copy(hid, p)
                    title = cp.get("title") or ""
                    body = cp.get("body") or ""
                    tags = " ".join(cp.get("tags") or [])
                    lines.append("【%s】" % pname)
                    if title:
                        lines.append("标题：" + title)
                    if body:
                        lines.append(body)
                    if tags:
                        lines.append(tags)
                except Exception as e:
                    lines.append("【%s】文案失败：%s" % (pname, str(e)[:40]))
                try:
                    img = api.ai_image(hid, p, n=1)
                    urls = img.get("images") or []
                    if urls:
                        lines.append("配图（12小时有效，请及时保存）：\n" + urls[0])
                    else:
                        lines.append("配图：无")
                except Exception as e:
                    lines.append("配图失败：%s" % str(e)[:40])
                lines.append("")
            Clock.schedule_once(lambda _: self._show("\n".join(lines)), 0)

        threading.Thread(target=work, daemon=True).start()

    def _show(self, txt):
        self.out.text = txt
        self.out.color = C_TEXT
        self._last = txt


# 底部导航注册表：key, 显示文字, 页面工厂。加功能=加一行。
BOTTOM_NAV = [
    ("customer", "客户", lambda root: ListPanel("customer")),
    ("house", "房源", lambda root: ListPanel("house")),
    ("schedule", "日程", lambda root: SchedulePane()),
    ("tools", "工具", lambda root: ToolsPane()),
    ("post", "图文", lambda root: AIPostPane()),
    ("mine", "我的", lambda root: MinePage(root)),
]





class NavItem(BoxLayout):
    """底部导航单项：canvas 圆点图标 + 中文文字，选中变贝壳蓝。"""
    def __init__(self, key, text, on_tap, **kw):
        super().__init__(orientation="vertical", spacing=dp(2), padding=[0, dp(5)], **kw)
        self.key = key
        with self.canvas.before:
            self._dotc = Color(*C_NAV_TEXT)
            self._dot = Ellipse(size=(dp(12), dp(12)), pos=self.pos)
        self.bind(size=self._upd, pos=self._upd)
        self.dot_space = Widget(size_hint_y=None, height=dp(18))
        self.add_widget(self.dot_space)
        self.tx = Label(text=text, font_size="11sp", color=C_NAV_TEXT,
                        size_hint_y=None, height=dp(20))
        self.add_widget(self.tx)
        self.bind(on_touch_down=lambda w, touch: (
            on_tap(key) if w.collide_point(*touch.pos) else None))

    def _upd(self, w, v):
        self._dot.size = (dp(12), dp(12))
        self._dot.pos = (self.x + (self.width - dp(12)) / 2,
                         self.y + self.height - dp(20))

    def set_active(self, active):
        col = C_NAV_ACTIVE if active else C_NAV_TEXT
        self._dotc.rgba = col
        self.tx.color = col
        self.tx.bold = active


class BottomBar(BoxLayout):
    """底部导航栏：四个入口，选中态贝壳蓝圆点。"""
    def __init__(self, root, **kw):
        super().__init__(size_hint_y=None, height=dp(62), spacing=0,
                         padding=[0, dp(3), 0, dp(3)], **kw)
        card_bg(self, C_NAVY_DARK, radius=0)
        self.buttons = {}
        for key, text, _ in BOTTOM_NAV:
            item = NavItem(key, text, root.navigate)
            self.buttons[key] = item
            self.add_widget(item)

    def select(self, key):
        for k, b in self.buttons.items():
            b.set_active(k == key)


class MainScreen(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        card_bg(self, C_BG, radius=0)

        # 顶部品牌栏
        header = BoxLayout(size_hint_y=None, height=dp(58),
                           padding=[dp(14), dp(7)], spacing=dp(8))
        card_bg(header, C_NAVY, radius=0)
        brand = BoxLayout(orientation="vertical", spacing=dp(1))
        brand.add_widget(TLabel("贵江信息部", "16sp", (1, 1, 1, 1), bold=True, height=dp(25)))
        brand.add_widget(TLabel("房产带看作战系统 · 李经理 17328435631", "10sp",
                                C_NAV_TEXT, height=dp(17)))
        header.add_widget(brand)
        self.add_widget(header)

        # 内容区
        self.content = BoxLayout(orientation="vertical")
        self.add_widget(self.content)

        # 底部导航
        self.bottom = BottomBar(self)
        self.add_widget(self.bottom)

        # 页面缓存：切换不重建，保留列表状态
        self.pages = {}
        for key, _, factory in BOTTOM_NAV:
            self.pages[key] = factory(self)
        self.navigate("customer")

    def navigate(self, key):
        page = self.pages.get(key)
        if page is None:
            return
        self.content.clear_widgets()
        self.content.add_widget(page)
        self.bottom.select(key)
        if key == "mine" and hasattr(page, "refresh_status"):
            page.refresh_status()


class PujiangApp(App):
    title = "蒲江房产带看 · 贵江信息部"

    def build(self):
        api.init_conf()
        return MainScreen()


if __name__ == "__main__":
    PujiangApp().run()
