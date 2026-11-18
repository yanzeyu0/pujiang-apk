# -*- coding: utf-8 -*-
"""蒲江房产带看作战系统 - 安卓客户端（Kivy 原生 · 科技简约风）
P1：客户/房源/回收站/图片上传。数字与图片处理全本地，AI 只润色文字。"""
import os
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex

import api

# ============ 科技简约主题 ============
C_BG = get_color_from_hex("#0D1117")
C_PANEL = get_color_from_hex("#161C24")
C_PANEL2 = get_color_from_hex("#1C2530")
C_BORDER = get_color_from_hex("#2A3542")
C_ACCENT = get_color_from_hex("#2F9BFF")
C_ACCENT2 = get_color_from_hex("#00D4C8")
C_TEXT = get_color_from_hex("#E6EDF3")
C_TEXT2 = get_color_from_hex("#93A1B1")
C_SUCCESS = get_color_from_hex("#2ECC8F")
C_DANGER = get_color_from_hex("#FF6B6B")

# 中文字体：随 APK 打包，注册到所有默认字体名
_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinese_font.ttf")
if os.path.exists(_FONT):
    for n in ("Roboto", "RobotoItalic", "RobotoMedium", "RobotoMediumItalic",
              "RobotoBold", "RobotoBoldItalic", "DejaVuSans"):
        LabelBase.register(name=n, fn_regular=_FONT)


def card_bg(widget, color=C_PANEL, radius=8):
    """给控件加圆角卡片底（用 canvas.before，兼容 Kivy 2.x）。"""
    with widget.canvas.before:
        Color(*color)
        widget._bg_rect = Rectangle(size=widget.size, pos=widget.pos, radius=[radius])
    widget.bind(size=lambda w, v: setattr(w._bg_rect, "size", v),
                pos=lambda w, v: setattr(w._bg_rect, "pos", v))


class Card(BoxLayout):
    """圆角面板容器"""
    def __init__(self, color=C_PANEL, **kw):
        super().__init__(**kw)
        card_bg(self, color)


def accent_btn(text, on_press, size_hint_x=None, danger=False):
    b = Button(text=text, font_size="14sp", size_hint_x=size_hint_x,
               background_color=C_DANGER if danger else C_ACCENT,
               color=(1, 1, 1, 1))
    b.bind(on_press=on_press)
    return b


def toast(msg):
    content = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
    content.add_widget(Label(text=str(msg), font_size="15sp", color=C_TEXT,
                             halign="center", valign="middle"))
    b = accent_btn("知道了", lambda _: p.dismiss())
    b.size_hint_y = None
    b.height = dp(42)
    content.add_widget(b)
    p = Popup(title="提示", content=content, size_hint=(0.82, 0.32),
              background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
    p.open()


def confirm(title, msg, on_yes):
    content = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
    content.add_widget(Label(text=msg, font_size="14sp", color=C_TEXT,
                             halign="left", valign="middle"))
    bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    yes = accent_btn("确定", lambda _: (p.dismiss(), on_yes()))
    no = Button(text="取消", font_size="14sp", background_color=C_PANEL2, color=C_TEXT)
    no.bind(on_press=lambda _: p.dismiss())
    bar.add_widget(yes)
    bar.add_widget(no)
    content.add_widget(bar)
    p = Popup(title=title, content=content, size_hint=(0.85, 0.36),
              background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
    p.open()


class Header(BoxLayout):
    def __init__(self, title, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None,
                         height=dp(50), padding=[dp(12), dp(4)], spacing=dp(8), **kw)
        card_bg(self, C_PANEL, radius=0)
        lbl = Label(text=title, font_size="16sp", color=C_ACCENT2, halign="left")
        self.add_widget(lbl)


class RecordRow(BoxLayout):
    """一条记录行：文字 + 改/删 或 恢复"""
    def __init__(self, text, sub, on_edit=None, on_delete=None, on_restore=None, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None,
                         height=dp(66), spacing=dp(6), padding=[dp(8), dp(6)], **kw)
        card_bg(self, C_PANEL2, radius=6)
        info = BoxLayout(orientation="vertical", size_hint_x=0.62)
        info.add_widget(Label(text=text, font_size="14sp", color=C_TEXT,
                              halign="left", valign="bottom"))
        info.add_widget(Label(text=sub, font_size="11sp", color=C_TEXT2,
                              halign="left", valign="top"))
        self.add_widget(info)
        if on_restore:
            b = accent_btn("恢复", lambda _: on_restore(), size_hint_x=0.18)
            self.add_widget(b)
        else:
            b1 = Button(text="改", font_size="13sp", size_hint_x=0.17,
                        background_color=C_ACCENT, color=(1, 1, 1, 1))
            b2 = Button(text="删", font_size="13sp", size_hint_x=0.17,
                        background_color=C_DANGER, color=(1, 1, 1, 1))
            b1.bind(on_press=lambda _: on_edit())
            b2.bind(on_press=lambda _: on_delete())
            self.add_widget(b1)
            self.add_widget(b2)


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
    """通用列表：加载 / 新增 / 回收站切换"""
    def __init__(self, kind, **kw):
        super().__init__(orientation="vertical", **kw)
        self.kind = kind  # customer / house
        self.show_deleted = False
        self.rows = []

        # 顶栏
        bar = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6),
                        padding=[dp(4), dp(2)])
        self.title = Label(text=("客户" if kind == "customer" else "房源") + "列表",
                           font_size="16sp", color=C_ACCENT2, size_hint_x=0.34)
        btn_add = accent_btn("＋ 新增", self.on_add, size_hint_x=0.22)
        btn_refresh = Button(text="刷新", font_size="13sp", size_hint_x=0.18,
                             background_color=C_PANEL2, color=C_TEXT)
        btn_refresh.bind(on_press=lambda _: self.load())
        self.btn_bin = Button(text="回收站", font_size="13sp", size_hint_x=0.22,
                              background_color=C_PANEL2, color=C_TEXT2)
        self.btn_bin.bind(on_press=lambda _: self.toggle_bin())
        bar.add_widget(self.title)
        bar.add_widget(btn_add)
        bar.add_widget(btn_refresh)
        bar.add_widget(self.btn_bin)
        self.add_widget(bar)

        self.scroll = ScrollView()
        self.box = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=[dp(4), dp(4)])
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        self.add_widget(self.scroll)

        # 状态条
        self.status = Label(text="加载中…", font_size="12sp", color=C_TEXT2,
                            size_hint_y=None, height=dp(24))
        self.add_widget(self.status)
        self.load()

    def toggle_bin(self):
        self.show_deleted = not self.show_deleted
        self.btn_bin.text = "返回列表" if self.show_deleted else "回收站"
        self.btn_bin.color = C_ACCENT2 if self.show_deleted else C_TEXT2
        self.title.text = ("客户" if self.kind == "customer" else "房源") + ("回收站" if self.show_deleted else "列表")
        self.load()

    def load(self):
        self.status.text = "加载中…"
        def work():
            try:
                # only_deleted=True 后端只返回已删除项
                rows = (api.customer_list(self.show_deleted) if self.kind == "customer"
                        else api.house_list(only_deleted=self.show_deleted))
                self._render(rows, None, len(rows))
            except Exception as e:
                self._render([], str(e), 0)
        threading.Thread(target=work, daemon=True).start()

    def _render(self, rows, err, count):
        self.box.clear_widgets()
        if err:
            self.box.add_widget(Label(text="加载失败：" + err, font_size="13sp",
                                      color=C_DANGER, size_hint_y=None, height=dp(48)))
            self.status.text = "未连接"
            return
        self.status.text = "%s · 共 %d 条" % ("回收站" if self.show_deleted else "列表", count)
        if not rows:
            self.box.add_widget(Label(text="暂无数据", font_size="14sp", color=C_TEXT2,
                                      size_hint_y=None, height=dp(56)))
            return
        for r in rows:
            if self.kind == "customer":
                title = "%s  %s" % (r.get("name", ""), r.get("phone") or "")
                sub = "%s · %s" % ("买房" if r.get("customer_type") == "buy" else "租房",
                                  r.get("region") or "")
            else:
                price = ("总价%s" % r.get("total_price")) if r.get("deal_type") == "sale" \
                        else ("年租%s" % r.get("annual_rent"))
                nimg = len(api.photos_of(r))
                title = "%s  %s" % (r.get("community", ""), price or "")
                sub = "%s · %s · %d图" % ("买卖" if r.get("deal_type") == "sale" else "租赁",
                                         r.get("region") or "", nimg)
            if self.show_deleted:
                row = RecordRow(title, sub, on_restore=lambda rr=r: self.on_restore(rr))
            else:
                row = RecordRow(title, sub,
                                on_edit=lambda rr=r: self.on_edit(rr),
                                on_delete=lambda rr=r: self.on_delete(rr))
            self.box.add_widget(row)

    def on_add(self, _=None):
        if self.show_deleted:
            toast("请先返回列表")
            return
        (self._customer_form if self.kind == "customer" else self._house_form)(None)

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
        p = Popup(title=title, content=content, size_hint=(0.94, height_hint),
                  background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
        return p

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
        f_landmark = FormField("关注地标", vals.get("focus_landmark"))
        f_note = FormField("备注", vals.get("note"))
        for w in (f_name, f_phone, f_type, f_budget, f_region, f_landmark, f_note):
            grid.add_widget(w)
        scroll.add_widget(grid)
        content = BoxLayout(orientation="vertical", spacing=dp(8))
        content.add_widget(scroll)
        bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        pop = self._form_popup("编辑客户" if r else "新增客户", content, 0.82)
        save = accent_btn("保存", lambda _: self._save_customer(r, f_name, f_phone, f_type,
                                                                f_budget, f_region, f_landmark,
                                                                f_note, pop))
        cancel = Button(text="取消", font_size="14sp", background_color=C_PANEL2, color=C_TEXT)
        cancel.bind(on_press=lambda _: pop.dismiss())
        bar.add_widget(save)
        bar.add_widget(cancel)
        content.add_widget(bar)
        pop.open()

    def _save_customer(self, r, f_name, f_phone, f_type, f_budget, f_region, f_landmark, f_note, pop):
        if not f_name.text:
            toast("姓名必填")
            return
        ctype = f_type.text or "rent"
        d = {"name": f_name.text, "phone": f_phone.text, "customer_type": ctype,
             "region": f_region.text, "focus_landmark": f_landmark.text, "note": f_note.text}
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
        # 图片区
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
            r, f_deal, f_comm, f_region, f_type, f_area, f_annual, f_total, f_status, f_sp, pop))
        cancel = Button(text="取消", font_size="14sp", background_color=C_PANEL2, color=C_TEXT)
        cancel.bind(on_press=lambda _: pop.dismiss())
        bar.add_widget(save)
        bar.add_widget(cancel)
        content.add_widget(bar)
        pop.open()

    def _pick_images(self, info_label):
        fc = FileChooserListView(path=os.path.expanduser("~"), filters=["*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp"],
                                 multiselect=True, background_color=C_PANEL2,
                                 foreground_color=C_TEXT, selection_color=C_ACCENT)
        content = BoxLayout(orientation="vertical", spacing=dp(6))
        content.add_widget(fc)
        bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        pop = Popup(title="选择图片", content=content, size_hint=(0.96, 0.9),
                    background_color=C_PANEL, title_color=C_ACCENT2, separator_color=C_ACCENT)
        ok = accent_btn("上传所选", lambda _: (pop.dismiss(), self._upload_images(fc.selection, info_label)))
        cancel = Button(text="取消", font_size="14sp", background_color=C_PANEL2, color=C_TEXT)
        cancel.bind(on_press=lambda _: pop.dismiss())
        bar.add_widget(ok)
        bar.add_widget(cancel)
        content.add_widget(bar)
        pop.open()

    def _upload_images(self, paths, info_label):
        if not paths:
            return
        info_label.text = "压缩上传中 0/%d…" % len(paths)
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
            info_label.text = "图片：%d 张（本次上传 %d）" % (
                len(self._existing_urls) + len(self._new_urls), ok)
        threading.Thread(target=work, daemon=True).start()

    def _save_house(self, r, f_deal, f_comm, f_region, f_type, f_area, f_annual,
                    f_total, f_status, f_sp, pop):
        if not f_comm.text:
            toast("小区名必填")
            return
        d = {"deal_type": f_deal.text or "rent", "community": f_comm.text,
             "region": f_region.text, "house_type": f_type.text,
             "status": f_status.text or "available", "selling_point": f_sp.text}
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


class MainScreen(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        with self.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=lambda w, v: setattr(self._bg, "size", v),
                  pos=lambda w, v: setattr(self._bg, "pos", v))

        # 品牌头
        header = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(12), dp(6)], spacing=dp(8))
        card_bg(header, C_PANEL, radius=0)
        brand = BoxLayout(orientation="vertical", size_hint_x=0.72)
        brand.add_widget(Label(text="蒲江房产带看作战系统", font_size="16sp",
                               color=C_ACCENT2, halign="left"))
        brand.add_widget(Label(text="贵江信息部 · 李经理 17328435631", font_size="10sp",
                               color=C_TEXT2, halign="left"))
        header.add_widget(brand)
        btn_set = accent_btn("设置", self.on_settings, size_hint_x=0.16)
        header.add_widget(btn_set)
        self.add_widget(header)

        self.status = Label(text="● 连接中…", font_size="11sp", color=C_TEXT2,
                            size_hint_y=None, height=dp(22))
        self.add_widget(self.status)

        tabs = TabbedPanel(do_default_tab=False, background_color=C_PANEL,
                           tab_height=dp(44))
        t1 = TabbedPanelItem(text="客户")
        t1.add_widget(ListPanel("customer"))
        t2 = TabbedPanelItem(text="房源")
        t2.add_widget(ListPanel("house"))
        tabs.add_widget(t1)
        tabs.add_widget(t2)
        self.add_widget(tabs)

        threading.Thread(target=self.check, daemon=True).start()

    def check(self):
        try:
            h = api.health()
            self.status.text = "● 已连接服务器 · v%s" % h.get("version", "?")
            self.status.color = C_SUCCESS
        except Exception as e:
            self.status.text = "○ 未连接：" + str(e)[:24]
            self.status.color = C_DANGER

    def on_settings(self, _):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(10)])
        content.add_widget(Label(text="服务器地址（http://IP 或域名）", font_size="14sp",
                                 color=C_TEXT, halign="left"))
        ti = TextInput(text=api.base_url(), font_size="15sp", size_hint_y=None,
                       height=dp(44), background_color=C_PANEL2,
                       foreground_color=C_TEXT, cursor_color=C_ACCENT2)
        content.add_widget(ti)
        info = Label(text="贵江信息部 · 李经理 17328435631", font_size="11sp", color=C_TEXT2)
        content.add_widget(info)
        pop = Popup(title="设置", content=content, size_hint=(0.9, 0.46),
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
        content.add_widget(b)
        pop.open()


class PujiangApp(App):
    title = "蒲江房产带看 · 贵江信息部"

    def build(self):
        api.init_conf()
        return MainScreen()


if __name__ == "__main__":
    PujiangApp().run()
