# -*- coding: utf-8 -*-
"""蒲江房产带看作战系统 - 安卓客户端（Kivy 原生）P1 最小闭环"""
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
from kivy.core.text import LabelBase
from kivy.metrics import dp

import api

# 中文字体：随 APK 打包，注册到所有默认字体名
_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chinese_font.ttf")
if os.path.exists(_FONT):
    for n in ("Roboto", "RobotoItalic", "RobotoMedium", "RobotoMediumItalic",
              "RobotoBold", "RobotoBoldItalic", "DejaVuSans"):
        LabelBase.register(name=n, fn_regular=_FONT)


def toast(msg):
    p = Popup(title="提示", content=Label(text=str(msg), font_size="15sp"),
              size_hint=(0.8, 0.3))
    p.open()


class RecordRow(BoxLayout):
    """一条记录的展示行"""
    def __init__(self, text, on_edit, on_delete, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None,
                         height=dp(72), spacing=dp(6), padding=[dp(4), dp(4)], **kw)
        self.add_widget(Label(text=text, font_size="13sp", halign="left",
                              valign="middle", size_hint_x=0.7))
        b1 = Button(text="改", size_hint_x=0.15, font_size="14sp")
        b2 = Button(text="删", size_hint_x=0.15, font_size="14sp")
        b1.bind(on_press=lambda _: on_edit())
        b2.bind(on_press=lambda _: on_delete())
        self.add_widget(b1)
        self.add_widget(b2)


class ListPanel(BoxLayout):
    """通用列表面板：加载 + 新增"""
    def __init__(self, kind, **kw):
        super().__init__(orientation="vertical", **kw)
        self.kind = kind  # 'customer' or 'house'

        bar = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        title = Label(text=("客户列表" if kind == "customer" else "房源列表"),
                      font_size="16sp", size_hint_x=0.5)
        btn_add = Button(text="＋ 新增", size_hint_x=0.25, font_size="14sp")
        btn_refresh = Button(text="刷新", size_hint_x=0.25, font_size="14sp")
        btn_add.bind(on_press=self.on_add)
        btn_refresh.bind(on_press=lambda _: self.load())
        bar.add_widget(title)
        bar.add_widget(btn_add)
        bar.add_widget(btn_refresh)
        self.add_widget(bar)

        self.scroll = ScrollView()
        self.box = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        self.add_widget(self.scroll)

        self.rows = []
        self.load()

    def load(self):
        def work():
            try:
                rows = (api.customer_list() if self.kind == "customer"
                        else api.house_list())
                self.rows = rows
                self._render(rows, None)
            except Exception as e:
                self._render([], str(e))
        threading.Thread(target=work, daemon=True).start()

    def _render(self, rows, err):
        self.box.clear_widgets()
        if err:
            self.box.add_widget(Label(text="加载失败：" + err, font_size="14sp",
                                      size_hint_y=None, height=dp(48)))
            return
        if not rows:
            self.box.add_widget(Label(text="暂无数据，点上方新增", font_size="14sp",
                                      size_hint_y=None, height=dp(48)))
            return
        for r in rows:
            if self.kind == "customer":
                label = "%s  %s  %s" % (
                    r.get("name", ""), r.get("phone") or "",
                    ("买房" if r.get("customer_type") == "buy" else "租房"))
            else:
                price = ("总价%s" % r.get("total_price")) if r.get("deal_type") == "sale" \
                        else ("年租%s" % r.get("annual_rent"))
                label = "%s  %s  %s" % (
                    r.get("community", ""), price or "", r.get("region") or "")
            row = RecordRow(
                label,
                lambda rr=r: self.on_edit(rr),
                lambda rr=r: self.on_delete(rr))
            self.box.add_widget(row)

    def on_add(self, _=None):
        if self.kind == "customer":
            self._customer_form(None)
        else:
            self._house_form(None)

    def on_edit(self, r):
        if self.kind == "customer":
            self._customer_form(r)
        else:
            self._house_form(r)

    def on_delete(self, r):
        rid = r.get("id")
        try:
            if self.kind == "customer":
                api.customer_delete(rid)
            else:
                api.house_delete(rid)
            self.load()
        except Exception as e:
            toast(e)

    def _field(self, label, key, values, rows):
        rows.add_widget(Label(text=label, font_size="14sp", size_hint_x=0.3))
        ti = TextInput(text=str(values.get(key) or ""), font_size="15sp", size_hint_x=0.7)
        rows.add_widget(ti)
        return ti

    def _customer_form(self, r):
        content = BoxLayout(orientation="vertical", spacing=dp(4))
        grid = GridLayout(cols=2, spacing=dp(4), size_hint_y=None, height=dp(240))
        vals = r or {}
        f_name = self._field("姓名*", "name", vals, grid)
        f_phone = self._field("电话", "phone", vals, grid)
        f_type = self._field("类型(rent/buy)", "customer_type", vals, grid)
        if not r:
            f_type.text = "rent"
        f_budget = self._field("预算", "rent_budget",
                               {**vals, "rent_budget": vals.get("rent_budget")
                                or vals.get("budget_total") or ""}, grid)
        f_region = self._field("区域", "region", vals, grid)
        f_landmark = self._field("关注地标", "focus_landmark", vals, grid)
        f_note = self._field("备注", "note", vals, grid)
        content.add_widget(grid)
        pop = Popup(title=("编辑客户" if r else "新增客户"), content=content,
                    size_hint=(0.9, 0.7))

        def save(_):
            name = f_name.text.strip()
            if not name:
                toast("姓名必填")
                return
            ctype = f_type.text.strip() or "rent"
            d = {"name": name, "phone": f_phone.text.strip(),
                 "customer_type": ctype, "region": f_region.text.strip(),
                 "focus_landmark": f_landmark.text.strip(), "note": f_note.text.strip()}
            b = f_budget.text.strip()
            if b:
                try:
                    d["rent_budget" if ctype == "rent" else "budget_total"] = float(b)
                except ValueError:
                    pass
            try:
                if r:
                    api.customer_update(r["id"], d)
                else:
                    api.customer_create(d)
                pop.dismiss()
                self.load()
            except Exception as e:
                toast(e)

        btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        b_save = Button(text="保存")
        b_cancel = Button(text="取消")
        b_save.bind(on_press=save)
        b_cancel.bind(on_press=lambda _: pop.dismiss())
        btns.add_widget(b_save)
        btns.add_widget(b_cancel)
        content.add_widget(btns)
        pop.open()

    def _house_form(self, r):
        content = BoxLayout(orientation="vertical", spacing=dp(4))
        grid = GridLayout(cols=2, spacing=dp(4), size_hint_y=None, height=dp(300))
        vals = r or {}
        f_deal = self._field("类型(rent/sale)", "deal_type", vals, grid)
        if not r:
            f_deal.text = "rent"
        f_comm = self._field("小区*", "community", vals, grid)
        f_region = self._field("区域", "region", vals, grid)
        f_type = self._field("户型", "house_type", vals, grid)
        f_area = self._field("面积(㎡)", "area", vals, grid)
        f_annual = self._field("年租金", "annual_rent", vals, grid)
        f_total = self._field("总价", "total_price", vals, grid)
        f_status = self._field("状态(available)", "status", vals, grid)
        if not r:
            f_status.text = "available"
        f_sp = self._field("卖点", "selling_point", vals, grid)
        content.add_widget(grid)
        pop = Popup(title=("编辑房源" if r else "新增房源"), content=content,
                    size_hint=(0.9, 0.78))

        def save(_):
            comm = f_comm.text.strip()
            if not comm:
                toast("小区名必填")
                return
            deal = f_deal.text.strip() or "rent"
            d = {"deal_type": deal, "community": comm,
                 "region": f_region.text.strip(), "house_type": f_type.text.strip(),
                 "status": f_status.text.strip() or "available",
                 "selling_point": f_sp.text.strip()}
            for key, w in (("area", f_area), ("annual_rent", f_annual), ("total_price", f_total)):
                v = w.text.strip()
                if v:
                    try:
                        d[key] = float(v)
                    except ValueError:
                        pass
            try:
                if r:
                    api.house_update(r["id"], d)
                else:
                    api.house_create(d)
                pop.dismiss()
                self.load()
            except Exception as e:
                toast(e)

        btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        b_save = Button(text="保存")
        b_cancel = Button(text="取消")
        b_save.bind(on_press=save)
        b_cancel.bind(on_press=lambda _: pop.dismiss())
        btns.add_widget(b_save)
        btns.add_widget(b_cancel)
        content.add_widget(btns)
        pop.open()


class MainScreen(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        header = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(10), dp(6)])
        header.add_widget(Label(text="蒲江房产带看作战系统", font_size="18sp"))
        btn_set = Button(text="设置", size_hint_x=0.2, font_size="14sp")
        btn_set.bind(on_press=self.on_settings)
        header.add_widget(btn_set)
        self.add_widget(header)

        self.status = Label(text="连接中…", font_size="12sp", size_hint_y=None, height=dp(28))
        self.add_widget(self.status)

        tabs = TabbedPanel(do_default_tab=False)
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
            self.status.text = "已连接服务器 · v%s" % h.get("version", "?")
        except Exception as e:
            self.status.text = "未连接：" + str(e)

    def on_settings(self, _):
        content = BoxLayout(orientation="vertical", spacing=dp(6))
        content.add_widget(Label(text="服务器地址（http://IP 或域名）", font_size="14sp"))
        ti = TextInput(text=api.base_url(), font_size="15sp",
                       size_hint_y=None, height=dp(44))
        content.add_widget(ti)
        pop = Popup(title="设置", content=content, size_hint=(0.9, 0.45))

        def save(_):
            addr = ti.text.strip()
            if not addr:
                return
            conf = api.load_conf()
            conf["server_base"] = addr
            api.save_conf(conf)
            pop.dismiss()
            self.status.text = "地址已更新，重新启动生效"

        b = Button(text="保存", size_hint_y=None, height=dp(44))
        b.bind(on_press=save)
        content.add_widget(b)
        pop.open()


class PujiangApp(App):
    title = "蒲江房产带看"

    def build(self):
        api.init_conf()
        return MainScreen()


if __name__ == "__main__":
    PujiangApp().run()
