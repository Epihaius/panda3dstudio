from .base import *
from .button import Button


class MenuSeparator(Widget):

    def __init__(self, parent):

        gfx_ids = {"": Skin.atlas.gfx_ids["separator"]["menu"]}

        Widget.__init__(self, "menu_separator", parent, gfx_ids, has_mouse_region=False)

    def get_submenu(self):

        return None

    def enable(self, enable=True): pass

    def enable_hotkey(self, enable=True): pass

    def update_sort(self): pass


class MenuItem(Button):

    _checkmark = None
    _radio_bullet = None

    def __init__(self, parent, item_id, text, command=None, item_type="normal", radio_group_id=""):

        if not self._checkmark:
            gfx_id = Skin.atlas.gfx_ids["checkmark"][""][0][0]
            x, y, w, h = Skin.atlas.regions[gfx_id]
            MenuItem._checkmark = img = PNMImage(w, h, 4)
            img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
            img *= Skin.colors["menu_item_checkmark"]

        if not self._radio_bullet:
            gfx_id = Skin.atlas.gfx_ids["bullet"][""][0][0]
            x, y, w, h = Skin.atlas.regions[gfx_id]
            MenuItem._radio_bullet = img = PNMImage(w, h, 4)
            img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
            img *= Skin.colors["menu_item_bullet"]

        gfx_ids = Skin.atlas.gfx_ids[f"menu_item_{item_type}"]

        Button.__init__(self, parent, gfx_ids, text, text_alignment="left",
                        button_type="menu_item")

        if command:
            item_command = lambda: Mgr.do_next_frame(lambda t: command(), "item_command")
        else:
            item_command = None

        self.widget_type = "menu_item"
        self.command = item_command
        w, h = self.min_size
        offset = Skin.options["menu_item_hotkey_offset"]
        self.set_size((w + offset, h), is_min=True)
        self.mouse_region.sort = parent.sort + 1
        self.id = item_id
        self.item_type = item_type
        self._hotkey_label = None
        self._hotkey_label_disabled = None
        self._is_checked = False
        self.radio_group_id = radio_group_id
        self._submenu = Menu(self, is_submenu=True) if item_type == "submenu" else None

        if self._submenu:
            self.mouse_region.suppress_flags = MouseWatcherRegion.SF_mouse_button
            self.enable(False)

    def destroy(self):

        Button.destroy(self)

        if self._submenu:
            self._submenu.destroy()
            self._submenu = None

    def update_sort(self):

        if self.parent:
            self.mouse_region.sort = self.parent.sort + 1

        if self._submenu:
            self._submenu.update_sort()

    def set_parent(self, parent):

        Button.set_parent(self, parent)

        if parent:

            self.mouse_region.sort = parent.sort + 1

            if self._submenu:
                self._submenu.update_sort()

    def set_submenu(self, menu):

        self._submenu = menu

        if menu:
            menu.make_submenu()
            menu.set_parent(self)
            w = self.get_size()[0]
            menu.set_pos((w, 0))
            menu.update_initial_pos()

    def get_submenu(self):

        return self._submenu

    def hide_menu(self):

        self._submenu.hide()
        mouse_watcher = self.mouse_watcher
        region = self.mouse_region
        mouse_watcher.remove_region(region)
        mouse_watcher.add_region(region)
        self.parent.set_active_item(None)
        Button.on_leave(self, force=True)

    def set_pos(self, pos):

        Button.set_pos(self, pos)

        if self._submenu:
            w = self.get_size()[0]
            self._submenu.set_pos((w, 0))

    def confine_menu_to_window(self):

        menu = self._submenu
        parent = self.parent
        w, h = parent.get_size()
        w_m, h_m = menu.get_size()
        w_w, h_w = Mgr.get("window_size")
        x_old, y_old = menu.get_pos(from_root=True)
        x_new = x_old + w_m
        y_new = y_old + h_m
        quad = menu.quad

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

        l, r, b, t = self.gfx_inner_borders

        if self.get_hotkey_text():
            label = self._hotkey_label if self.is_enabled() else self._hotkey_label_disabled
            w, h = label.size
            x = width - r - w
            y = (height - h) // 2 + 1
            image.blend_sub_image(label, x, y, 0, 0)

        if self._is_checked:
            if self.item_type == "check":
                l, r, b, t = Skin.atlas.outer_borders["menu_item_checkbox"]
                image.blend_sub_image(self._checkmark, l, t, 0, 0)
            elif self.item_type == "radio":
                l, r, b, t = Skin.atlas.outer_borders["menu_item_radiobox"]
                image.blend_sub_image(self._radio_bullet, l, t, 0, 0)

        return image

    def set_text(self, text=""):

        if not Button.set_text(self, text):
            return False

        w, h = self.min_size
        offset = Skin.options["menu_item_hotkey_offset"]
        self.set_size((w + offset, h), is_min=True)

        return True

    def set_hotkey(self, hotkey=None, hotkey_text="", interface_id="main"):

        if self.get_hotkey_text() == hotkey_text:
            return False

        Button.set_hotkey(self, hotkey, hotkey_text, interface_id)

        if hotkey_text:
            skin_text = Skin.text["menu_item"]
            font = skin_text["font"]
            color = skin_text["color"]
            self._hotkey_label = font.create_image(hotkey_text, color)
            color = Skin.colors["disabled_menu_item_text"]
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

        parent = self.parent
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

        parent =  self.parent

        if not parent or parent.get_active_item() is not self:
            Button.on_leave(self, force=True)

    def check(self, is_checked=True):

        if self.item_type in ("check", "radio"):
            self._is_checked = is_checked
            Button.on_leave(self, force=True)

    def is_checked(self):

        return self._is_checked

    def on_left_down(self):

        if self.item_type == "check":
            self._is_checked = not self._is_checked
        elif self.item_type == "radio" and not self._is_checked:
            self._is_checked = True
            self.parent.check_radio_item(self.id)
        elif self.item_type != "normal":
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

        self.mouse_region.active = True

        if enable and not self._submenu:
            flags = 0
        else:
            flags = MouseWatcherRegion.SF_mouse_button

        self.mouse_region.suppress_flags = flags

        return True


class Menu(WidgetCard):

    _shown_menu = None
    _listener = None
    _mouse_region_mask = MouseWatcherRegion("menu_mask", -100000., 100000., -100000., 100000.)
    _mouse_region_mask.sort = 1000
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

            parent = menu.parent

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

        WidgetCard.__init__(self, "menu", parent, is_root_container=True)

        if not self._listener:
            Menu._listener = listener = DirectObject()
            listener.accept("gui_mouse1", self.__hide)
            listener.accept("gui_mouse3", self.__hide)
            listener.accept("focus_loss", self.__hide)
            listener.accept("gui_escape", lambda: self.__hide(last_shown=True))

        self._is_submenu = is_submenu
        self.sort = parent.parent.sort + 1 if is_submenu else 1001
        self._items = {}
        self._radio_items = {}
        self._active_item = None
        self._item_offset = (0, 0)
        sizer = Sizer("vertical")
        self._item_sizer = subsizer = Sizer("vertical")
        subsizer.set_column_proportion(0, 1.)
        sizer.add(subsizer)
        subsizer = Sizer("horizontal")
        sizer.add(subsizer)
        self._label_sizer = label_sizer = Sizer("vertical")
        self._hotkey_label_sizer = hotkey_label_sizer = Sizer("vertical")
        subsizer.add(label_sizer)
        subsizer.add(hotkey_label_sizer)
        self.sizer = sizer
        self.mouse_region = mouse_region = MouseWatcherRegion("menu", 0., 0., 0., 0.)
        self.mouse_watcher.add_region(mouse_region)
        mouse_region.suppress_flags = MouseWatcherRegion.SF_mouse_button
        mouse_region.sort = self.sort
        self._mouse_regions = [mouse_region]
        self._initial_pos = (0, 0)
        self._on_hide = on_hide if on_hide else lambda: None

    def destroy(self):

        WidgetCard.destroy(self)

        self._items = {}
        self._radio_items = {}
        self._active_item = None
        self._item_sizer = None
        self._label_sizer = None
        self._hotkey_label_sizer = None
        self._mouse_regions = []

    def clear(self):

        self._items = {}
        self._radio_items = {}
        self._active_item = None
        self._item_sizer.clear()
        self._label_sizer.clear()
        self._hotkey_label_sizer.clear()
        self._mouse_regions = [self.mouse_region]

        parent = self.parent

        if parent is not Mgr.get("window"):
            parent.enable(False)

    def update(self, update_initial_pos=True):

        sizer = self.sizer
        size = sizer.update_min_size()
        sizer.set_size(size)
        sizer.update_positions()
        self.update_mouse_region_frames()
        self.update_images()

        if update_initial_pos:
            self._initial_pos = self.get_pos()

        self._mouse_regions = mouse_regions = [self.mouse_region]

        for item in self._items.values():
            mouse_region = item.mouse_region
            if mouse_region:
                mouse_regions.append(mouse_region)

        self.hide(call_custom_handler=False)

        for item in self._items.values():
            submenu = item.get_submenu()
            if submenu:
                submenu.update(update_initial_pos)

    def update_initial_pos(self):

        self._initial_pos = self.get_pos()

        for item in self._items.values():
            submenu = item.get_submenu()
            if submenu:
                submenu.update_initial_pos()

    def update_sort(self):

        self.sort = self.parent.parent.sort + 1 if self._is_submenu else 1001
        self.mouse_region.sort = self.sort

        quad = self.quad

        if quad:
            quad.set_bin("menu", self.sort)

        for item in self._items.values():
            item.update_sort()

    def set_parent(self, parent):

        WidgetCard.set_parent(self, parent)

        self.update_sort()

    def make_submenu(self, is_submenu=True):

        self._is_submenu = is_submenu

    def set_active_item(self, item):

        self._active_item = item

    def get_active_item(self):

        return self._active_item

    def set_item_text(self, item_id, text, update=False):

        if item_id not in self._items:
            return

        item = self._items[item_id]

        if item.set_text(text):

            sizer_cell = item.sizer_cell
            index = self._item_sizer.cells.index(sizer_cell)
            sizer_cell = self._label_sizer.cells[index]
            self._label_sizer.remove_cell(sizer_cell)
            self._label_sizer.add((item.min_size[0], 0), index=index)

            if update:
                self._item_sizer.set_min_size_stale()
                self.update()

    def set_item_hotkey(self, item_id, hotkey=None, hotkey_text="", interface_id="main", update=False):

        item = self._items[item_id]

        if item.set_hotkey(hotkey, hotkey_text, interface_id):

            sizer_cell = item.sizer_cell
            index = self._item_sizer.cells.index(sizer_cell)
            sizer_cell = self._hotkey_label_sizer.cells[index]
            self._hotkey_label_sizer.remove_cell(sizer_cell)
            hotkey_label = item.get_hotkey_label()
            w = hotkey_label.size[0] if hotkey_label else 0
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
        other_radio_items = self._radio_items[item.radio_group_id][:]
        other_radio_items.remove(item)

        for other_item in other_radio_items:
            other_item.check(False)

    def get_checked_radio_item_id(self, radio_group_id=""):

        radio_items = self._radio_items.get(radio_group_id, [])

        for item in radio_items:
            if item.is_checked():
                return item.id

    def clear_radio_check(self, radio_group_id=""):

        radio_items = self._radio_items.get(radio_group_id, [])

        for item in radio_items:
            if item.is_checked():
                item.check(False)
                return

    def get_last_shown_submenu(self):

        if not self._active_item:
            return self

        return self._active_item.get_submenu().get_last_shown_submenu()

    def add(self, item_id, item_text="", item_command=None, item_type="normal", radio_group_id="",
            index=None, update=False):

        if item_id in self._items:
            return

        if item_type == "separator":
            item = MenuSeparator(self)
        else:
            item = MenuItem(self, item_id, item_text, item_command, item_type, radio_group_id)

        self._items[item_id] = item
        self._item_sizer.add(item, index=index)
        self._label_sizer.add((item.min_size[0], 0), index=index)
        self._hotkey_label_sizer.add((0, 0), index=index)

        if item_type == "radio":
            self._radio_items.setdefault(radio_group_id, []).append(item)

        if update:
            self.update()

        parent = self.parent

        if parent is not Mgr.get("window"):
            parent.enable()

        return item

    def add_item(self, item, index=None, update=False):

        item_id = item.id

        if item_id in self._items:
            return False

        item.set_parent(self)
        self._items[item_id] = item
        self._item_sizer.add_cell(item.sizer_cell, index)
        self._label_sizer.add((item.min_size[0], 0), index=index)
        hotkey_label = item.get_hotkey_label()
        w = hotkey_label.size[0] if hotkey_label else 0
        self._hotkey_label_sizer.add((w, 0), index=index)
        mouse_region = item.mouse_region

        if mouse_region:
            self._mouse_regions.append(mouse_region)

        if update:
            self.update()

        parent = self.parent

        if parent is not Mgr.get("window"):
            parent.enable()

        return True

    def remove(self, item_id, update=False, destroy=False):

        if item_id not in self._items:
            return False

        menu_item = self._items[item_id]
        mouse_region = menu_item.mouse_region

        if mouse_region:

            mouse_watcher = self.mouse_watcher
            mouse_watcher.remove_region(mouse_region)

            if mouse_region in self._mouse_regions:
                self._mouse_regions.remove(mouse_region)

        del self._items[item_id]

        if menu_item.item_type == "radio":
            radio_group_id = menu_item.radio_group_id
            self._radio_items[radio_group_id].remove(menu_item)

        sizer_cell = menu_item.sizer_cell
        index = self._item_sizer.cells.index(sizer_cell)
        self._item_sizer.remove_cell(sizer_cell)
        sizer_cell = self._label_sizer.cells[index]
        self._label_sizer.remove_cell(sizer_cell)
        sizer_cell = self._hotkey_label_sizer.cells[index]
        self._hotkey_label_sizer.remove_cell(sizer_cell)

        if destroy:
            menu_item.destroy()
        else:
            menu_item.set_parent(None)

        if self._items:

            if update:
                self.update()

        else:

            parent = self.parent

            if parent is not Mgr.get("window"):
                parent.enable(False)

        return True

    @property
    def items(self):

        return self._items

    def get_item_index(self, item_id):

        item = self._items[item_id]
        sizer_cell = item.sizer_cell

        return self._item_sizer.cells.index(sizer_cell)

    def is_empty(self):

        return len(self._items) == 0

    def get_submenu(self, menu_id):

        return self._items[menu_id].get_submenu()

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
        self.quad.set_pos(x, 0, -y)
        self.update_mouse_region_frames()

        return "xy" if x != x_old and y != y_old else ("x" if x != x_old else "y")

    def show_at_mouse_pos(self):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        pos = (mouse_pointer.x, mouse_pointer.y)

        return self.show(pos)

    def show(self, pos=None, alt_pos=None):

        if not self._items:
            return False

        quad = self.quad

        if not quad.is_hidden():
            return False

        parent = self.parent
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
        mouse_watcher = self.mouse_watcher

        if not self._is_submenu:
            for watcher in GD["mouse_watchers"] + GD["viewport"]["mouse_watchers2"]:
                watcher.add_region(region_mask)

        for mouse_region in self._mouse_regions:
            mouse_watcher.add_region(mouse_region)

        return True

    def hide(self, call_custom_handler=True):

        quad = self.quad

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
        mouse_watcher = self.mouse_watcher
        region_mask = self._mouse_region_mask
        parent_is_window = self.parent is Mgr.get("window")

        if not parent_is_window and self._initial_pos != self.get_pos():
            self.set_pos(self._initial_pos)
            self._item_sizer.update_mouse_region_frames()

        if not self._is_submenu:
            for watcher in GD["mouse_watchers"] + GD["viewport"]["mouse_watchers2"]:
                watcher.remove_region(region_mask)

        for mouse_region in self._mouse_regions:
            mouse_watcher.remove_region(mouse_region)

        if call_custom_handler:
            self._on_hide()

        return True

    def toggle(self):

        self.show() if self.quad.is_hidden() else self.hide()

    def is_hidden(self, check_ancestors=False):

        return self.quad.is_hidden() if self.quad else False

    def update_images(self):

        self._item_sizer.update_images()
        width, height = self.get_size()

        tex_atlas = Skin.atlas.image
        tex_atlas_regions = Skin.atlas.regions
        gfx_ids = Skin.atlas.gfx_ids["menu"][""]
        border_topleft_id, border_top_id, border_topright_id = gfx_ids[0]
        border_left_id, _, border_right_id = gfx_ids[1]
        border_bottomleft_id, border_bottom_id, border_bottomright_id = gfx_ids[2]

        x_tl, y_tl, w_tl, h_tl = tex_atlas_regions[border_topleft_id]
        self._item_offset = (w_tl, h_tl)
        width += w_tl
        height += h_tl
        x, y, w, h = tex_atlas_regions[border_bottomright_id]
        width += w
        height += h

        img = PNMImage(width, height, 4)

        img.copy_sub_image(tex_atlas, 0, 0, x_tl, y_tl, w_tl, h_tl)
        x_t, y_t, w_t, h_t = tex_atlas_regions[border_top_id]
        x_tr, y_tr, w_tr, h_tr = tex_atlas_regions[border_topright_id]
        part_img = PNMImage(w_t, h_t, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_t, y_t, w_t, h_t)
        scaled_w = width - w_tl - w_tr
        scaled_img = PNMImage(scaled_w, h_t, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, w_tl, 0, 0, 0)
        img.copy_sub_image(tex_atlas, w_tl + scaled_w, 0, x_tr, y_tr, w_tr, h_tr)
        x_l, y_l, w_l, h_l = tex_atlas_regions[border_left_id]
        x_bl, y_bl, w_bl, h_bl = tex_atlas_regions[border_bottomleft_id]
        part_img = PNMImage(w_l, h_l, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_l, y_l, w_l, h_l)
        scaled_h = height - h_tl - h_bl
        scaled_img = PNMImage(w_l, scaled_h, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, 0, h_tl, 0, 0)
        img.copy_sub_image(tex_atlas, 0, h_tl + scaled_h, x_bl, y_bl, w_bl, h_bl)
        x_r, y_r, w_r, h_r = tex_atlas_regions[border_right_id]
        x_br, y_br, w_br, h_br = tex_atlas_regions[border_bottomright_id]
        part_img = PNMImage(w_r, h_r, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_r, y_r, w_r, h_r)
        scaled_img = PNMImage(w_r, scaled_h, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, w_tl + scaled_w, h_tr, 0, 0)
        img.copy_sub_image(tex_atlas, w_tl + scaled_w, h_tr + scaled_h, x_br, y_br, w_br, h_br)
        x_b, y_b, w_b, h_b = tex_atlas_regions[border_bottom_id]
        part_img = PNMImage(w_b, h_b, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_b, y_b, w_b, h_b)
        scaled_img = PNMImage(scaled_w, h_b, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, w_tl, h_tr + scaled_h, 0, 0)

        for item in self._items.values():
            x, y = item.get_pos()
            img.copy_sub_image(item.get_image(), x + w_tl, y + h_tl, 0, 0)

        tex = self.texture
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
        quad.set_bin("menu", self.sort)
        self._image = img

    def copy_sub_image(self, widget, sub_image, width, height, offset_x=0, offset_y=0):

        item_offset_x, item_offset_y = self._item_offset
        offset_x += item_offset_x
        offset_y += item_offset_y
        WidgetCard.copy_sub_image(self, widget, sub_image, width, height, offset_x, offset_y)

    def update_mouse_region_frames(self):

        w, h = self.get_size()
        x, y = self.get_pos(from_root=True)
        l = x
        r = x + w
        b = -y - h
        t = -y
        self.mouse_region.frame = (l, r, b, t)

        self._item_sizer.update_mouse_region_frames()

    def enable(self, enable=True):

        for item in self._items.values():
            item.enable(enable)

    def enable_hotkeys(self, enable=True):

        for item in self._items.values():
            item.enable_hotkey(enable)
