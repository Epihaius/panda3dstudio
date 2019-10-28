from .widgets import *
from ..tooltip import ToolTip


class Dialog(WidgetCard):

    _dialogs = []
    _listener = None
    _mouse_region_mask = MouseWatcherRegion("dialog_mask", -100000., 100000., -100000., 100000.)
    _mouse_region_mask.sort = 200
    _entered_suppressed_state = False
    _ignoring_events = False
    _default_btn_width = 0
    _background_overlay = None

    @staticmethod
    def __enter_suppressed_state():

        cls = Dialog

        if not cls._entered_suppressed_state:
            Mgr.enter_state("suppressed")
            cls._entered_suppressed_state = True

    @staticmethod
    def __exit_suppressed_state():

        cls = Dialog

        if cls._entered_suppressed_state:
            Mgr.exit_state("suppressed")
            cls._entered_suppressed_state = False

    @classmethod
    def __on_left_down(cls):

        region = Mgr.get("mouse_watcher").get_over_region()

        if region and region.name == "dialog":
            cls._dialogs[-1].init_dragging()

    @classmethod
    def __on_commit(cls):

        if cls._dialogs:
            cls._dialogs[-1].close(answer="yes")

    @classmethod
    def __on_cancel(cls):

        if cls._dialogs and cls._dialogs[-1].allows_escape():
            cls._dialogs[-1].close()

    @classmethod
    def __add_dialog(cls, dialog):

        dialogs = cls._dialogs

        if dialogs:
            sort = dialogs[-1].sort + 10
            dialogs[-1].ignore_extra_dialog_events()
        else:
            sort = 200
            ToolTip.hide()

        region_mask = cls._mouse_region_mask
        region_mask.sort = sort
        dialog.sort = sort + 1
        cls._background_overlay.set_bin("dialog", sort)

        if not dialogs:

            if Skin["colors"]["dialog_background_overlay"][3]:
                cls._background_overlay.show()

            cls.__enter_suppressed_state()

            for watcher in GD["mouse_watchers"] + GD["viewport"]["mouse_watchers2"]:

                watcher.add_region(region_mask)

                if watcher.name == "panel_stack":

                    region = watcher.get_over_region()

                    if region:
                        Mgr.send("gui_region_leave", [region])

                    watcher.set_enter_pattern("")
                    watcher.set_leave_pattern("")

        cls._dialogs.append(dialog)

    @classmethod
    def __remove_dialog(cls):

        dialogs = cls._dialogs
        del dialogs[-1]

        if dialogs:
            dialog = dialogs[-1]
            sort = dialog.sort - 1
            dialog.accept_extra_dialog_events()
        else:
            sort = 200

        region_mask = cls._mouse_region_mask
        region_mask.sort = sort
        cls._background_overlay.set_bin("dialog", sort)

        if not dialogs:

            cls._background_overlay.hide()
            cls.__exit_suppressed_state()

            for watcher in GD["mouse_watchers"] + GD["viewport"]["mouse_watchers2"]:

                watcher.remove_region(region_mask)

                if watcher.name == "panel_stack":
                    watcher.set_enter_pattern("gui_region_enter")
                    watcher.set_leave_pattern("gui_region_leave")

    @classmethod
    def get_dialogs(cls):

        return cls._dialogs

    @classmethod
    def center_dialogs(cls):

        for dialog in cls._dialogs:
            dialog.center_in_window()

    @classmethod
    def hide_dialogs(cls):

        for dialog in cls._dialogs:
            dialog.quad.hide()

    @classmethod
    def show_dialogs(cls):

        for dialog in cls._dialogs:
            dialog.quad.show()

    @classmethod
    def enable_listener(cls):

        listener = cls._listener
        listener.accept("gui_mouse1", cls.__on_left_down)
        listener.accept("gui_enter", cls.__on_commit)
        listener.accept("gui_escape", cls.__on_cancel)

    @classmethod
    def disable_listener(cls):

        cls._listener.ignore_all()

    @classmethod
    def accept_extra_dialog_events(cls): pass

    @classmethod
    def ignore_extra_dialog_events(cls): pass

    @classmethod
    def accept_dialog_events(cls):

        if cls._dialogs and cls._ignoring_events:
            dialog = cls._dialogs[-1]
            dialog.enable_listener()
            dialog.accept_extra_dialog_events()
            cls._ignoring_events = False
            return True

        return False

    @classmethod
    def ignore_dialog_events(cls):

        if cls._dialogs and not cls._ignoring_events:
            dialog = cls._dialogs[-1]
            dialog.disable_listener()
            dialog.ignore_extra_dialog_events()
            cls._ignoring_events = True
            return True

        return False

    @classmethod
    def get_mouse_region_mask(cls):

        return cls._mouse_region_mask

    @classmethod
    def init(cls):

        cls._default_btn_width = Skin["options"]["dialog_standard_button_width"]
        cls._listener = DirectObject()
        cls.enable_listener()
        cm = CardMaker("dialog_background_overlay")
        cm.set_frame(-1., 1., -1., 1.)
        overlay = Mgr.get("gui_root").parent.attach_new_node(cm.generate())
        overlay.set_transparency(TransparencyAttrib.M_alpha)
        overlay.set_color(Skin["colors"]["dialog_background_overlay"])
        overlay.hide()
        cls._background_overlay = overlay

        Mgr.accept("accept_dialog_events", cls.accept_dialog_events)
        Mgr.accept("ignore_dialog_events", cls.ignore_dialog_events)

    def __init__(self, title="", choices="ok", ok_alias="OK", on_yes=None, on_no=None,
                 on_cancel=None, extra_button_data=(), allow_escape=True):

        WidgetCard.__init__(self, "dialog")

        self.mouse_region = region = MouseWatcherRegion("dialog", 0., 0., 0., 0.)
        self.mouse_watcher.add_region(region)
        self._sort = 0
        self._allows_escape = allow_escape

        self.__add_dialog(self)

        skin_text = Skin["text"]["dialog_title"]
        font = skin_text["font"]
        color = skin_text["color"]
        self._title_label = label = font.create_image(title, color) if title else None
        self._choices = choices
        sizer = Sizer("vertical")
        self.sizer = sizer
        self._client_sizer = client_sizer = Sizer("vertical")
        client_sizer.default_size = (max(100, label.size[0]) + 20, 50)
        sizer.add(client_sizer, expand=True)
        self._button_sizer = btn_sizer = Sizer("horizontal")
        h_b = Skin["options"]["dialog_bottom_height"]
        btn_sizer.add((0, h_b), proportion=1.)
        width = self._default_btn_width
        btn_sizer.add((width // 5, 0))

        for text, tooltip_text, command, btn_width, gap_multiplier in extra_button_data:
            btn = DialogStandardButton(self, text, tooltip_text, command)
            w, h = btn.min_size
            w = max(w, width if btn_width is None else btn_width)
            btn.set_size((w, h), is_min=True)
            btn_sizer.add(btn, alignment="center_v")
            btn_sizer.add((int(gap_multiplier * width / 5), 0))

        if "yes" in choices:
            command = lambda: self.close("yes")
            btn = DialogStandardButton(self, "Yes", command=command)
            w, h = btn.min_size
            btn.set_size((width, h), is_min=True)
            btn_sizer.add(btn, alignment="center_v")
            btn_sizer.add((width // 5, 0))

        if "no" in choices:
            command = lambda: self.close("no")
            btn = DialogStandardButton(self, "No", command=command)
            w, h = btn.min_size
            btn.set_size((width, h), is_min=True)
            btn_sizer.add(btn, alignment="center_v")
            btn_sizer.add((width // 5, 0))

        if "ok" in choices:
            command = lambda: self.close("yes")
            btn = DialogStandardButton(self, ok_alias, command=command)
            w, h = btn.min_size
            btn.set_size((width, h), is_min=True)
            btn_sizer.add(btn, alignment="center_v")
            btn_sizer.add((width // 5, 0))

        if "cancel" in choices:
            btn = DialogStandardButton(self, "Cancel", command=self.close)
            w, h = btn.min_size
            btn.set_size((width, h), is_min=True)
            btn_sizer.add(btn, alignment="center_v")
            btn_sizer.add((width // 5, 0))

        sizer.add(btn_sizer, expand=True)
        self._on_yes = on_yes if on_yes else lambda: None
        self._on_no = on_no if on_no else lambda: None
        self._on_cancel = on_cancel if on_cancel else lambda: None
        l, r, b, t = TextureAtlas["inner_borders"]["dialog"]
        self._item_offset = (l, t)
        self._background_image = None
        self._mouse_start_pos = None
        self._drag_offset = None

    @property
    def sort(self):

        return self._sort

    @sort.setter
    def sort(self, sort):

        self._sort = sort
        self.mouse_region.sort = sort

    def close(self, answer=""):

        if self._drag_offset is not None:
            self.finalize_dragging()

        self.__remove_dialog()
        self._client_sizer = None
        self._button_sizer = None

        WidgetCard.destroy(self)

        Mgr.set_cursor("main")

        if answer == "yes":
            self._on_yes()
        elif answer == "no":
            self._on_no()
        else:
            self._on_cancel()

        self._on_yes = lambda: None
        self._on_no = lambda: None
        self._on_cancel = lambda: None

    def is_top_dialog(self):

        return self._dialogs[-1] is self

    def get_client_sizer(self):

        return self._client_sizer

    def allows_escape(self):

        return self._allows_escape

    def update_widget_positions(self):
        """ Override in derived class """

        pass

    def center_in_window(self):

        w, h = self.get_size()
        w_w, h_w = Mgr.get("window_size")
        h_t = Skin["options"]["dialog_title_height"]
        x = (w_w - w) // 2
        y = (h_w - h + h_t) // 2
        pos = (x, y)
        self.set_pos(pos)
        self.sizer.update_mouse_region_frames()

        x, y = self.get_pos(from_root=True)
        l = x
        r = x + w
        b = -y - h
        t = -y + h_t
        self.mouse_region.frame = (l, r, b, t)

        self.update_widget_positions()

    def __drag(self, task):

        w_w, h_w = Mgr.get("window_size")
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = min(w_w, max(0, mouse_pointer.x))
        mouse_y = min(h_w, max(0, mouse_pointer.y))
        pos = (mouse_x, mouse_y)

        if pos != self._mouse_start_pos:
            offset_x, offset_y = self._drag_offset
            x = mouse_x - offset_x
            y = mouse_y - offset_y
            self.set_pos((x, y))
            self.quad.set_pos(x, 0, -y)
            self.update_widget_positions()

        return task.cont

    def init_dragging(self):

        Mgr.add_task(self.__drag, "drag_dialog")
        self._listener.accept("gui_mouse1-up", self.finalize_dragging)
        x, y = self.get_pos(from_root=True)
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.x
        mouse_y = mouse_pointer.y
        self._mouse_start_pos = (mouse_x, mouse_y)
        self._drag_offset = (mouse_x - x, mouse_y - y)

    def finalize_dragging(self):

        Mgr.remove_task("drag_dialog")
        self._listener.ignore("gui_mouse1-up")
        x, y = self.get_pos(from_root=True)
        self.quad.set_pos(x, 0, -y)
        w, h = self.get_size()
        l = x
        r = x + w
        b = -y - h
        t = -y + Skin["options"]["dialog_title_height"]
        self.mouse_region.frame = (l, r, b, t)
        self.sizer.update_mouse_region_frames()
        self._mouse_start_pos = None
        self._drag_offset = None

    def update_images(self):

        self.sizer.update_images()
        width, height = self.get_size()
        h_b = Skin["options"]["dialog_bottom_height"]
        height -= h_b
        center_img = PNMImage(width, height, 4)

        tex_atlas = TextureAtlas["image"]
        tex_atlas_regions = TextureAtlas["regions"]

        bl, br, bb, bt = TextureAtlas["inner_borders"]["dialog"]
        width += bl + br
        height += bb + bt

        img = PNMImage(width, height, 4)

        x_tl, y_tl, w_tl, h_tl = tex_atlas_regions["dialog_border_topleft"]
        img.copy_sub_image(tex_atlas, 0, 0, x_tl, y_tl, w_tl, h_tl)
        x_t, y_t, w_t, h_t = tex_atlas_regions["dialog_border_top"]
        x_tr, y_tr, w_tr, h_tr = tex_atlas_regions["dialog_border_topright"]
        part_img = PNMImage(w_t, h_t, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_t, y_t, w_t, h_t)
        scaled_w = width - w_tl - w_tr
        scaled_img = PNMImage(scaled_w, h_t, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, w_tl, 0, 0, 0)
        img.copy_sub_image(tex_atlas, w_tl + scaled_w, 0, x_tr, y_tr, w_tr, h_tr)
        x_l, y_l, w_l, h_l = tex_atlas_regions["dialog_border_left"]
        x_bl, y_bl, w_bl, h_bl = tex_atlas_regions["dialog_border_bottomleft"]
        part_img = PNMImage(w_l, h_l, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_l, y_l, w_l, h_l)
        scaled_h = height - h_tl - h_bl
        scaled_img = PNMImage(w_l, scaled_h, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, 0, h_tl, 0, 0)
        img.copy_sub_image(tex_atlas, 0, h_tl + scaled_h, x_bl, y_bl, w_bl, h_bl)
        x_r, y_r, w_r, h_r = tex_atlas_regions["dialog_border_right"]
        part_img = PNMImage(w_r, h_r, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_r, y_r, w_r, h_r)
        scaled_img = PNMImage(w_r, scaled_h, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, w_tl + scaled_w, h_tr, 0, 0)
        x_br, y_br, w_br, h_br = tex_atlas_regions["dialog_border_bottomright"]
        img.copy_sub_image(tex_atlas, w_tl + scaled_w, h_tr + scaled_h, x_br, y_br, w_br, h_br)
        x_b, y_b, w_b, h_b = tex_atlas_regions["dialog_border_bottom"]
        part_img = PNMImage(w_b, h_b, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x_b, y_b, w_b, h_b)
        scaled_img = PNMImage(scaled_w, h_b, 4)
        scaled_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(scaled_img, w_tl, h_tr + scaled_h, 0, 0)
        x, y, w, h = tex_atlas_regions["dialog_main"]
        part_img = PNMImage(w, h, 4)
        part_img.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
        center_img.unfiltered_stretch_from(part_img)
        img.copy_sub_image(center_img, bl, bt, 0, 0)

        label = self._title_label

        if label:
            w_l, h_l = label.size
            h_title = Skin["options"]["dialog_title_height"]
            x = (width - w_l) // 2
            y = (h_title - h_l) // 2 + Skin["options"]["dialog_title_top"]
            img.blend_sub_image(label, x, y, 0, 0)

        self._background_image = bg_image = PNMImage(width - bl, height - bt, 4)
        bg_image.copy_sub_image(img, 0, 0, bl, bt)
        ref_node = self.node

        for widget in self.sizer.get_widgets(include_children=False):

            widget_img = widget.get_image()

            if widget_img:
                x, y = widget.get_pos(ref_node=ref_node)
                img_offset_x, img_offset_y = widget.image_offset
                x += bl + img_offset_x
                y += bt + img_offset_y
                img.blend_sub_image(widget_img, x, y, 0, 0)

        tex = self.texture
        tex.load(img)

        l = -bl
        r = width - bl
        b = -height + bt
        t = bt
        quad = self.create_quad((l, r, b, t))
        quad.set_texture(tex)
        quad.set_transparency(TransparencyAttrib.M_alpha)
        quad.set_bin("dialog", self._sort)
        self._image = img

    def get_image(self, composed=False):

        return self._background_image

    def copy_sub_image(self, widget, sub_image, width, height, offset_x=0, offset_y=0):

        item_offset_x, item_offset_y = self._item_offset
        offset_x += item_offset_x
        offset_y += item_offset_y
        WidgetCard.copy_sub_image(self, widget, sub_image, width, height, offset_x, offset_y)

    def finalize(self):

        sizer = self.sizer
        size = sizer.update_min_size()
        sizer.set_size(size)
        sizer.calculate_positions()
        self.update_images()
        self.center_in_window()

    def update_layout(self):

        sizer = self.sizer
        size = sizer.update_min_size()
        sizer.set_size(size)
        sizer.calculate_positions()
        self.update_images()
        x, y = self.get_pos(from_root=True)
        self.quad.set_pos(x, 0, -y)
        w, h = self.get_size()
        l = x
        r = x + w
        b = -y - h
        t = -y + Skin["options"]["dialog_title_height"]
        self.mouse_region.frame = (l, r, b, t)
        sizer.update_mouse_region_frames()
        self.update_widget_positions()
