from .base import *
from .button import Button


class MenuSeparator(Widget):

    _gfx = {"": (("menu_separator_left", "menu_separator_center", "menu_separator_right"),)}

    def __init__(self, parent):

        Widget.__init__(self, "menu_separator", parent, self._gfx, stretch_dir="horizontal",
                        has_mouse_region=False)

    def enable(self, enable=True): pass

    def enable_hotkey(self, enable=True): pass


class MenuItem(Button):

    _gfx = {
        "normal": (("menu_item_normal_left", "menu_item_normal_center",
                   "menu_item_normal_right"),),
        "hilited": (("menu_item_hilited_left", "menu_item_hilited_center",
                   "menu_item_hilited_right"),)
    }
    _checkmark = None
    _radio_bullet = None

    def __init__(self, parent, item_id, text, command=None, item_type="normal", radio_group=""):

        if not self._checkmark:
            x, y, w, h = TextureAtlas["regions"]["checkmark"]
            MenuItem._checkmark = img = PNMImage(w, h, 4)
            img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
            img *= Skin["colors"]["menu_item_checkmark"]

        if not self._radio_bullet:
            x, y, w, h = TextureAtlas["regions"]["bullet"]
            MenuItem._radio_bullet = img = PNMImage(w, h, 4)
            img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
            img *= Skin["colors"]["menu_item_bullet"]

        gfx_data = self._gfx.copy()

        if item_type == "submenu":
            gfx_data["normal"] = (("menu_item_normal_left", "menu_item_normal_center",
                                  "menu_item_normal_right+arrow"),)
            gfx_data["hilited"] = (("menu_item_hilited_left", "menu_item_hilited_center",
                                   "menu_item_hilited_right+arrow"),)
        elif item_type == "check":
            gfx_data["normal"] = (("menu_item_normal_left+checkbox", "menu_item_normal_center",
                                  "menu_item_normal_right"),)
            gfx_data["hilited"] = (("menu_item_hilited_left+checkbox", "menu_item_hilited_center",
                                   "menu_item_hilited_right"),)
        elif item_type == "radio":
            gfx_data["normal"] = (("menu_item_normal_left+radiobutton", "menu_item_normal_center",
                                  "menu_item_normal_right"),)
            gfx_data["hilited"] = (("menu_item_hilited_left+radiobutton", "menu_item_hilited_center",
                                   "menu_item_hilited_right"),)

        if command:
            task = lambda t: command()
            item_command = lambda: Mgr.do_next_frame(task, "item_command")
        else:
            item_command = None

        Button.__init__(self, parent, gfx_data, text, command=item_command, text_alignment="left",
                        button_type="menu_item")

        self.set_widget_type("menu_item")
        w, h = self.get_min_size()
        self.set_size((w + 20, h), is_min=True)
        self.get_mouse_region().set_sort(parent.get_sort() + 1)
        self._id = item_id
        self._item_type = item_type
        self._hotkey_label = None
        self._hotkey_label_disabled = None
        self._is_checked = False
        self._radio_group = radio_group
        self._submenu = Menu(self, is_submenu=True) if item_type == "submenu" else None

        if self._submenu:
            self.get_mouse_region().set_suppress_flags(MouseWatcherRegion.SF_mouse_button)
            self.enable(False)

    def destroy(self):

        Button.destroy(self)

        if self._submenu:
            self._submenu.destroy()
            self._submenu = None

    def get_id(self):

        return self._id

    def get_item_type(self):

        return self._item_type

    def get_radio_group(self):

        return self._radio_group

    def get_submenu(self):

        return self._submenu

    def hide_menu(self):

        self._submenu.hide()
        mouse_watcher = self.get_mouse_watcher()
        region = self.get_mouse_region()
        mouse_watcher.remove_region(region)
        mouse_watcher.add_region(region)
        self.get_parent().set_active_item(None)
        Button.on_leave(self, force=True)

    def set_pos(self, pos):

        Button.set_pos(self, pos)

        if self._submenu:
            w = self.get_size()[0]
            self._submenu.set_pos((w, 0))

    def confine_menu_to_window(self):

        menu = self._submenu
        parent = self.get_parent()
        w, h = parent.get_size()
        w_m, h_m = menu.get_size()
        w_w, h_w = Mgr.get("window_size")
        x_old, y_old = menu.get_pos(from_root=True)
        x_new = x_old + w_m
        y_new = y_old + h_m
        quad = menu.get_quad()

        if x_new > w_w or y_new > h_w:

            x, y = parent.get_pos(from_root=True)
            x_m, y_m = menu.get_pos()

            if x_new > w_w:
                x -= w_m
                x_new = max(0, x)
                quad.set_x(x_new)
                x_m += x_new - x_old

            if y_new > h_w:
                y = y_old - h_m + self.get_size()[1]
                y_new = max(0, y)
                quad.set_z(-y_new)
                y_m += y_new - y_old

            menu.set_pos((x_m, y_m))
            menu.update_mouse_region_frames()

        x, y = menu.get_pos(from_root=True)
        quad_pos = Point3(x, 0, -y)

        if quad.get_pos() != quad_pos:
            quad.set_pos(quad_pos)
            menu.update_mouse_region_frames()

    def get_image(self, state=None, composed=True):

        width, height = self.get_size()
        image = Button.get_image(self, state, composed)

        if not image:
            image = PNMImage(width, height, 4)

        l, r, b, t = self.get_gfx_inner_borders()

        if self.get_hotkey_text():
            label = self._hotkey_label if self.is_enabled() else self._hotkey_label_disabled
            w = label.get_x_size()
            h = label.get_y_size()
            x = width - r - w
            y = (height - h) // 2 + 1
            image.blend_sub_image(label, x, y, 0, 0)

        if self._is_checked:
            if self._item_type == "check":
                l, r, b, t = TextureAtlas["outer_borders"]["menu_item_checkbox"]
                image.blend_sub_image(self._checkmark, l, t, 0, 0)
            elif self._item_type == "radio":
                l, r, b, t = TextureAtlas["outer_borders"]["menu_item_radiobutton"]
                image.blend_sub_image(self._radio_bullet, l, t, 0, 0)

        return image

    def set_text(self, text=""):

        if not Button.set_text(self, text):
            return False

        w, h = self.get_min_size()
        self.set_size((w + 20, h), is_min=True)

        return True

    def set_hotkey(self, hotkey=None, hotkey_text="", interface_id="main"):

        if self.get_hotkey_text() == hotkey_text:
            return False

        Button.set_hotkey(self, hotkey, hotkey_text, interface_id)

        if hotkey_text:
            skin_text = Skin["text"]["menu_item"]
            font = skin_text["font"]
            color = skin_text["color"]
            self._hotkey_label = font.create_image(hotkey_text, color)
            color = Skin["colors"]["disabled_menu_item_text"]
            self._hotkey_label_disabled = font.create_image(hotkey_text, color)
        else:
            self._hotkey_label = None

        return True

    def get_hotkey_label(self):

        return self._hotkey_label

    def on_enter(self):

        Button.on_enter(self)

        if not self.is_enabled():
            return

        parent = self.get_parent()
        active_item = parent.get_active_item()

        if active_item:
            if active_item is not self:
                parent.set_active_item(None)
                active_item.on_leave()
                active_item.get_submenu().hide()

        if self._submenu:
            if active_item is not self:
                self._submenu.show()
                parent.set_active_item(self)

    def on_leave(self):

        parent =  self.get_parent()

        if not parent or parent.get_active_item() is not self:
            Button.on_leave(self, force=True)

    def check(self, is_checked=True):

        if self._item_type in ("check", "radio"):
            self._is_checked = is_checked
            Button.on_leave(self, force=True)

    def is_checked(self):

        return self._is_checked

    def on_left_down(self):

        if self._item_type == "check":
            self._is_checked = not self._is_checked
        elif self._item_type == "radio" and not self._is_checked:
            self._is_checked = True
            self.get_parent().check_radio_item(self._id)
        elif self._item_type != "normal":
            return

        Button.on_left_down(self)
        self.press()
        self.set_pressed(False)

    def on_left_up(self): pass

    def is_hidden(self, check_ancestors=False):

        return Button.is_hidden(self, check_ancestors)

    def enable(self, enable=True):

        if not Button.enable(self, enable):
            return False

        self.get_mouse_region().set_active(True)

        if enable and not self._submenu:
            flags = 0
        else:
            flags = MouseWatcherRegion.SF_mouse_button

        self.get_mouse_region().set_suppress_flags(flags)

        return True


class Menu(WidgetCard):

    _shown_menu = None
    _listener = None
    _mouse_region_mask = MouseWatcherRegion("menu_mask", -100000., 100000., -100000., 100000.)
    _mouse_region_mask.set_sort(1000)
    _entered_suppressed_state = False
    _ignoring_dialog_events = False

    @staticmethod
    def enter_suppressed_state():

        cls = Menu

        if not cls._entered_suppressed_state:
            Mgr.enter_state("suppressed")
            cls._entered_suppressed_state = True

    @staticmethod
    def exit_suppressed_state():

        cls = Menu

        if cls._entered_suppressed_state:
            Mgr.exit_state("suppressed")
            cls._entered_suppressed_state = False

    @classmethod
    def __ignore_dialog_events(cls):

        cls._ignoring_dialog_events = Mgr.do("ignore_dialog_events")

    @classmethod
    def __accept_dialog_events(cls):

        if cls._ignoring_dialog_events:
            Mgr.do("accept_dialog_events")
            cls._ignoring_dialog_events = False

    @classmethod
    def __hide(cls, last_shown=False):

        menu = cls._shown_menu

        if not menu:
            return

        if last_shown:
            menu = menu.get_last_shown_submenu()

        if menu is cls._shown_menu:
            cls._shown_menu = None
            cls.exit_suppressed_state()
            Mgr.do("accept_field_events")
            cls.__accept_dialog_events()

        def task():

            parent = menu.get_parent()

            if parent is Mgr.get("window"):
                menu.hide()
            else:
                parent.hide_menu()

            if Mgr.get("active_input_field"):
                Mgr.set_cursor("input_commit")

        task_id = "hide_menu"
        PendingTasks.add(task, task_id)

    @classmethod
    def is_menu_shown(cls):

        return True if cls._shown_menu else False

    def __init__(self, parent=None, is_submenu=False, on_hide=None):

        WidgetCard.__init__(self, "menu", parent)

        if not self._listener:
            Menu._listener = listener = DirectObject()
            listener.accept("gui_mouse1", self.__hide)
            listener.accept("gui_mouse3", self.__hide)
            listener.accept("focus_loss", self.__hide)
            listener.accept("gui_escape", lambda: self.__hide(last_shown=True))

        self._is_submenu = is_submenu
        self._sort = parent.get_parent().get_sort() + 1 if is_submenu else 1001
        self._menus = {}
        self._items = {}
        self._radio_items = {}
        self._active_item = None
        self._item_offset = (0, 0)
        sizer = Sizer("vertical")
        self._item_sizer = subsizer = Sizer("vertical")
        sizer.add(subsizer, expand=True)
        subsizer = Sizer("horizontal")
        sizer.add(subsizer, expand=True)
        self._label_sizer = label_sizer = Sizer("vertical")
        self._hotkey_label_sizer = hotkey_label_sizer = Sizer("vertical")
        subsizer.add(label_sizer)
        subsizer.add(hotkey_label_sizer)
        self.set_sizer(sizer)
        self._mouse_region = mouse_region = MouseWatcherRegion("menu", 0., 0., 0., 0.)
        self.get_mouse_watcher().add_region(mouse_region)
        mouse_region.set_suppress_flags(MouseWatcherRegion.SF_mouse_button)
        mouse_region.set_sort(self._sort)
        self._mouse_regions = [mouse_region]
        self._initial_pos = (0, 0)
        self._initial_quad_pos = Point3()
        self._on_hide = on_hide if on_hide else lambda: None

    def destroy(self):

        WidgetCard.destroy(self)

        for menu in self._menus.values():
            menu.destroy()

        self._menus = {}
        self._items = {}
        self._radio_items = {}
        self._active_item = None
        self._item_sizer = None
        self._label_sizer = None
        self._hotkey_label_sizer = None
        self._mouse_regions = []

    def update(self):

        sizer = self.get_sizer()
        size = sizer.update_min_size()
        sizer.set_size(size)
        sizer.calculate_positions()
        self.update_mouse_region_frames()
        self.update_images()
        self._initial_pos = self.get_pos()
        self._initial_quad_pos = self.get_quad().get_pos()

        self._mouse_regions = mouse_regions = [self._mouse_region]

        for item in self._items.values():

            mouse_region = item.get_mouse_region()

            if mouse_region:
                mouse_regions.append(mouse_region)

        self.hide()

        for menu in self._menus.values():
            menu.update()

    def set_active_item(self, item):

        self._active_item = item

    def get_active_item(self):

        return self._active_item

    def set_item_text(self, item_id, text, update=False):

        if item_id not in self._items:
            return

        item = self._items[item_id]

        if item.set_text(text):

            sizer_item = item.get_sizer_item()
            index = self._item_sizer.get_item_index(sizer_item)
            sizer_item = self._label_sizer.get_item(index)
            self._label_sizer.remove_item(sizer_item)
            self._label_sizer.add((item.get_min_size()[0], 0), index=index)

            if update:
                self.update()

    def set_item_hotkey(self, item_id, hotkey=None, hotkey_text="", interface_id="main", update=False):

        item = self._items[item_id]

        if item.set_hotkey(hotkey, hotkey_text, interface_id):

            sizer_item = item.get_sizer_item()
            index = self._item_sizer.get_item_index(sizer_item)
            sizer_item = self._hotkey_label_sizer.get_item(index)
            self._hotkey_label_sizer.remove_item(sizer_item)
            hotkey_label = item.get_hotkey_label()
            w = hotkey_label.get_x_size() if hotkey_label else 0
            self._hotkey_label_sizer.add((w, 0), index=index)

            if update:
                self.update()

    def enable_item(self, item_id, enable=True):

        self._items[item_id].enable(enable)

    def check_item(self, item_id, is_checked=True):

        self._items[item_id].check(is_checked)

    def check_radio_item(self, item_id):

        item = self._items[item_id]
        item.check()
        other_radio_items = self._radio_items[item.get_radio_group()][:]
        other_radio_items.remove(item)

        for other_item in other_radio_items:
            other_item.check(False)

    def get_checked_radio_item_id(self, radio_group=""):

        radio_items = self._radio_items.get(radio_group, [])

        for item in radio_items:
            if item.is_checked():
                return item.get_id()

    def clear_radio_check(self, radio_group=""):

        radio_items = self._radio_items.get(radio_group, [])

        for item in radio_items:
            if item.is_checked():
                item.check(False)
                return

    def get_last_shown_submenu(self):

        if not self._active_item:
            return self

        return self._active_item.get_submenu().get_last_shown_submenu()

    def get_sort(self):

        return self._sort

    def add(self, item_id, item_text="", item_command=None, item_type="normal", radio_group="",
            index=None, update=False):

        if item_id in self._items:
            return

        if item_type == "separator":
            item = MenuSeparator(self)
            menu = None
        else:
            item = MenuItem(self, item_id, item_text, item_command, item_type, radio_group)
            menu = item.get_submenu()

        self._items[item_id] = item
        self._item_sizer.add(item, expand=True, index=index)
        self._label_sizer.add((item.get_min_size()[0], 0), index=index)
        self._hotkey_label_sizer.add((0, 0), index=index)

        if item_type == "radio":
            self._radio_items.setdefault(radio_group, []).append(item)

        if update:
            self.update()

        parent = self.get_parent()

        if parent is not Mgr.get("window"):
            parent.enable()

        if menu:
            self._menus[item_id] = menu

        return item

    def add_item(self, item, index=None, update=False):

        item_id = item.get_id()

        if item_id in self._items:
            return False

        item.set_parent(self)
        self._items[item_id] = item
        self._item_sizer.add_item(item.get_sizer_item(), index)
        self._label_sizer.add((item.get_min_size()[0], 0), index=index)
        hotkey_label = item.get_hotkey_label()
        w = hotkey_label.get_x_size() if hotkey_label else 0
        self._hotkey_label_sizer.add((w, 0), index=index)
        mouse_region = item.get_mouse_region()

        if mouse_region:
            self._mouse_regions.append(mouse_region)

        if update:
            self.update()

        parent = self.get_parent()

        if parent is not Mgr.get("window"):
            parent.enable()

        return True

    def remove(self, item_id, update=False, destroy=False):

        if item_id not in self._items:
            return False

        menu_item = self._items[item_id]
        mouse_region = menu_item.get_mouse_region()

        if mouse_region:

            mouse_watcher = self.get_mouse_watcher()
            mouse_watcher.remove_region(mouse_region)

            if mouse_region in self._mouse_regions:
                self._mouse_regions.remove(mouse_region)

        del self._items[item_id]

        if menu_item.get_item_type() == "radio":
            radio_group = menu_item.get_radio_group()
            self._radio_items[radio_group].remove(menu_item)

        sizer_item = menu_item.get_sizer_item()
        index = self._item_sizer.get_item_index(sizer_item)
        self._item_sizer.remove_item(sizer_item)
        sizer_item = self._label_sizer.get_item(index)
        self._label_sizer.remove_item(sizer_item)
        sizer_item = self._hotkey_label_sizer.get_item(index)
        self._hotkey_label_sizer.remove_item(sizer_item)

        if destroy:
            menu_item.destroy()
        else:
            menu_item.set_parent(None)

        if self._items:

            if update:
                self.update()

        else:

            parent = self.get_parent()

            if parent is not Mgr.get("window"):
                parent.enable(False)

        return True

    def get_item(self, item_id):

        return self._items[item_id]

    def get_items(self):

        return self._items

    def get_item_index(self, item_id):

        item = self._items[item_id]
        sizer_item = item.get_sizer_item()

        return self._item_sizer.get_item_index(sizer_item)

    def get_item_count(self):

        return len(self._items)

    def is_empty(self):

        return len(self._items) == 0

    def get_submenu(self, menu_id):

        return self._menus[menu_id]

    def confine_to_window(self):

        w, h = self.get_size()
        w_w, h_w = Mgr.get("window_size")
        x_old, y_old = self.get_pos(from_root=True)
        x = max(0, min(x_old, w_w - w))
        y = max(0, min(y_old, h_w - h))

        if (x, y) == (x_old, y_old):
            return ""

        self.set_pos((x, y))
        x, y = self.get_pos(from_root=True)
        self.get_quad().set_pos(x, 0, -y)
        self.update_mouse_region_frames()

        return "xy" if x != x_old and y != y_old else ("x" if x != x_old else "y")

    def show_at_mouse_pos(self):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        pos = (mouse_pointer.get_x(), mouse_pointer.get_y())

        return self.show(pos)

    def show(self, pos=None, alt_pos=None):

        if not self._items:
            return False

        quad = self.get_quad()

        if not quad.is_hidden():
            return False

        parent = self.get_parent()
        parent_is_window = parent is Mgr.get("window")
        region_mask = self._mouse_region_mask
 
        if not self._is_submenu:

            Menu._shown_menu = self

            if Mgr.get_state_id() != "suppressed":
                self.enter_suppressed_state()

            Mgr.do("ignore_field_events")
            self.__ignore_dialog_events()

        if pos:
            x, y = pos
            self.set_pos(pos)
            quad.set_pos(x, 0, -y)
            self.update_mouse_region_frames()

        if parent_is_window:
            confined = self.confine_to_window()
        else:
            confined = parent.confine_menu_to_window()

        set_alt_pos = confined and alt_pos

        if set_alt_pos:

            x_alt, y_alt = alt_pos

            if confined == "xy" or (confined == "x" and x_alt != x) or (confined == "y" and y_alt != y):

                self.set_pos(alt_pos)
                quad.set_pos(x_alt, 0, -y_alt)
                self.update_mouse_region_frames()

                if parent_is_window:
                    self.confine_to_window()
                else:
                    parent.confine_menu_to_window()

        quad.show()
        self._listener.ignore("gui_mouse1")
        self._listener.ignore("gui_mouse3")

        def task(t):

            self._listener.accept("gui_mouse1", self.__hide)
            self._listener.accept("gui_mouse3", self.__hide)
            Mgr.set_cursor("main")

        task_id = "enable_menu_dismiss_by_mouse"
        Mgr.do_next_frame(task, task_id)
        mouse_watcher = self.get_mouse_watcher()

        if not self._is_submenu:
            for watcher in GlobalData["mouse_watchers"] + GlobalData["viewport"]["mouse_watchers2"]:
                watcher.add_region(region_mask)

        for mouse_region in self._mouse_regions:
            mouse_watcher.add_region(mouse_region)

        return True

    def hide(self):

        quad = self.get_quad()

        if not quad or quad.is_hidden():
            return False

        if self._active_item:
            active_item = self._active_item
            self._active_item = None
            active_item.on_leave()
            active_item.get_submenu().hide()

        if not self._is_submenu:
            Menu._shown_menu = None

        quad.hide()
        mouse_watcher = self.get_mouse_watcher()
        region_mask = self._mouse_region_mask
        parent_is_window = self.get_parent() is Mgr.get("window")

        if not parent_is_window and self._initial_pos != self.get_pos():
            self.set_pos(self._initial_pos)
            quad.set_pos(self._initial_quad_pos)
            self._item_sizer.update_mouse_region_frames()

        if not self._is_submenu:
            for watcher in GlobalData["mouse_watchers"] + GlobalData["viewport"]["mouse_watchers2"]:
                watcher.remove_region(region_mask)

        for mouse_region in self._mouse_regions:
            mouse_watcher.remove_region(mouse_region)

        self._on_hide()

        return True

    def toggle(self):

        self.show() if self.get_quad().is_hidden() else self.hide()

    def is_hidden(self, check_ancestors=False):

        return self.get_quad().is_hidden() if self.get_quad() else False

    def update_images(self):

        self._item_sizer.update_images()
        width, height = self.get_size()

        tex_atlas = TextureAtlas["image"]
        tex_atlas_regions = TextureAtlas["regions"]

        x_tl, y_tl, w_tl, h_tl = tex_atlas_regions["menu_border_topleft"]
        self._item_offset = (w_tl, h_tl)
        width += w_tl
        height += h_tl
        x, y, w, h = tex_atlas_regions["menu_border_bottomright"]
        width += w
        height += h

        img = PNMImage(width, height, 4)

        img.copy_sub_image(tex_atlas, 0, 0, x_tl, y_tl, w_tl, h_tl)
        x_t, y_t, w_t, h_t = tex_atlas_regions["menu_border_top"]
        x_tr, y_tr, w_tr, h_tr = tex_atlas_regions["menu_border_topright"]
        part_img = PNMImage(w_t, h_t, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_t, y_t, w_t, h_t)
        scaled_w = width - w_tl - w_tr
        scaled_img = PNMImage(scaled_w, h_t, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, w_tl, 0, 0, 0)
        img.copy_sub_image(tex_atlas, w_tl + scaled_w, 0, x_tr, y_tr, w_tr, h_tr)
        x_l, y_l, w_l, h_l = tex_atlas_regions["menu_border_left"]
        x_bl, y_bl, w_bl, h_bl = tex_atlas_regions["menu_border_bottomleft"]
        part_img = PNMImage(w_l, h_l, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_l, y_l, w_l, h_l)
        scaled_h = height - h_tl - h_bl
        scaled_img = PNMImage(w_l, scaled_h, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, 0, h_tl, 0, 0)
        img.copy_sub_image(tex_atlas, 0, h_tl + scaled_h, x_bl, y_bl, w_bl, h_bl)
        x_r, y_r, w_r, h_r = tex_atlas_regions["menu_border_right"]
        x_br, y_br, w_br, h_br = tex_atlas_regions["menu_border_bottomright"]
        part_img = PNMImage(w_r, h_r, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_r, y_r, w_r, h_r)
        scaled_img = PNMImage(w_r, scaled_h, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, w_tl + scaled_w, h_tr, 0, 0)
        img.copy_sub_image(tex_atlas, w_tl + scaled_w, h_tr + scaled_h, x_br, y_br, w_br, h_br)
        x_b, y_b, w_b, h_b = tex_atlas_regions["menu_border_bottom"]
        part_img = PNMImage(w_b, h_b, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_b, y_b, w_b, h_b)
        scaled_img = PNMImage(scaled_w, h_b, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, w_tl, h_tr + scaled_h, 0, 0)

        for item in self._items.values():
            x, y = item.get_pos()
            img.copy_sub_image(item.get_image(), x + w_tl, y + h_tl, 0, 0)

        tex = self._tex
        tex.load(img)

        l = -w_tl
        r = width - w_tl
        b = -height + h_tl
        t = h_tl
        quad = self.create_quad((l, r, b, t))
        quad.set_texture(tex)
        x, y = self.get_pos(from_root=True)
        quad.set_transparency(TransparencyAttrib.M_alpha)
        quad.set_pos(x, 0., -y)
        quad.set_bin("menu", self._sort)
        self._image = img

    def copy_sub_image(self, widget, sub_image, width, height, offset_x=0, offset_y=0):

        item_offset_x, item_offset_y = self._item_offset
        offset_x += item_offset_x
        offset_y += item_offset_y
        WidgetCard.copy_sub_image(self, widget, sub_image, width, height, offset_x, offset_y)

    def get_mouse_region(self):

        return self._mouse_region

    def update_mouse_region_frames(self):

        w, h = self.get_size()
        x, y = self.get_pos(from_root=True)
        l = x
        r = x + w
        b = -y - h
        t = -y
        self._mouse_region.set_frame(l, r, b, t)

        self._item_sizer.update_mouse_region_frames()

    def enable(self, enable=True):

        for item in self._items.values():
            item.enable(enable)

    def enable_hotkeys(self, enable=True):

        for item in self._items.values():
            item.enable_hotkey(enable)
