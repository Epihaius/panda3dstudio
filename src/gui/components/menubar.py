from ..base import *
from ..button import Button
from ..menu import Menu


class MenuButton(Button):

    def __init__(self, parent, text):

        gfx_ids = Skin.atlas.gfx_ids["menu_button"]

        Button.__init__(self, parent, gfx_ids, text, button_type="menu_button")

        self.widget_type = "menu_button"

        def command():

            self.parent.set_mouse_region_sort(1001 if self._menu.is_hidden() else 0)
            self._menu.toggle()

        w, h = self.min_size
        border = Skin.options["menu_button_border"]
        self.set_size((w + border * 2, h), is_min=True)
        self._menu = Menu(self)
        self.command = command

    def destroy(self):

        Button.destroy(self)

        self._menu.destroy()
        self._menu = None

    def set_menu(self, menu):

        self._menu = menu
        menu.make_submenu(False)
        menu.set_parent(self)
        h = self.get_size()[1]
        menu.set_pos((0, h))
        menu.update_initial_pos()
        menu.update_mouse_region_frames()

    def get_menu(self):

        return self._menu

    def set_pos(self, pos):

        Button.set_pos(self, pos)

        h = self.get_size()[1]
        self._menu.set_pos((0, h))
        self._menu.update_mouse_region_frames()

    def confine_menu_to_window(self):

        menu = self._menu
        w, h = menu.get_size()
        w_w, h_w = Mgr.get("window_size")
        x_old, y_old = menu.get_pos(net=True)
        x = max(0, min(x_old, w_w - w))

        if x != x_old:
            menu.quad.set_x(x)
            dx = x - x_old
            x, y = menu.get_pos()
            x += dx
            menu.set_pos((x, y))
            menu.update_mouse_region_frames()

    def hide_menu(self):

        self.parent.set_mouse_region_sort(0)
        self._menu.hide()
        mouse_watcher = self.mouse_watcher
        region = self.mouse_region
        mouse_watcher.remove_region(region)
        mouse_watcher.add_region(region)
        self.parent.set_active_button(None)
        Button.on_leave(self, force=True)

    def on_enter(self):

        parent = self.parent
        active_button = parent.get_active_button()

        if active_button:
            if active_button is not self:
                parent.set_active_button(None)
                active_button.on_leave()
                active_button.press()
                self.on_left_down()
        else:
            Button.on_enter(self)

    def on_leave(self):

        if self.parent.get_active_button() is not self:
            Button.on_leave(self, force=True)

    def on_left_down(self):

        Button.on_left_down(self)
        self.press()
        self.set_pressed(False)

        parent = self.parent
        active_button = parent.get_active_button()

        if active_button:
            parent.set_active_button(None)
            Button.on_enter(self)
        else:
            parent.set_active_button(self)

    def on_left_up(self):

        if Mgr.get_state_id() == "suppressed" and self._menu.is_hidden():
            self._menu.exit_suppressed_state()


class MenuBar(Widget):

    def __init__(self, parent):

        gfx_ids = Skin.atlas.gfx_ids["menubar"]
        sizer_borders = Skin.atlas.inner_borders["menubar"]

        Widget.__init__(self, "menubar", parent, gfx_ids, sizer_borders=sizer_borders)

        sizer = Sizer("horizontal")
        sizer.default_size = (0, self.min_size[1])
        self.sizer = sizer
        self._menus = {}
        self._btns = {}
        self._active_button = None

    def finalize(self):

        for menu in self._menus.values():
            menu.update()

    def add_menu(self, menu_id, menu_name=""):

        btn = MenuButton(self, menu_name)
        self.sizer.add(btn)
        menu = btn.get_menu()
        self._menus[menu_id] = menu
        self._btns[menu_id] = btn

        return menu

    def get_menu(self, menu_id):

        return self._menus[menu_id]

    def get_menus(self):

        return self._menus

    def get_buttons(self):

        return self._btns

    def hide_menu(self, menu_id):

        btn = self._btns[menu_id]
        btn.hide()
        self.sizer.remove_cell(btn.sizer_cell)

    def show_menu(self, menu_id, index=None):

        btn = self._btns[menu_id]
        btn.show()
        self.sizer.add_cell(btn.sizer_cell, index=index)

    def set_active_button(self, button):

        self._active_button = button

    def get_active_button(self):

        return self._active_button

    def get_docking_data(self, point):

        if GD["shift_down"]:
            return

        l, r, b, t = self.mouse_region.frame
        x, y = point

        if l < x < r and b < -y < t:
            return self, "bottom", ((l + r) // 2, b)

    def set_mouse_region_sort(self, sort):

        for btn in self.sizer.get_widgets():
            btn.mouse_region.sort = sort
