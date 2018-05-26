from ..base import *
from ..text import Text, Label
from ..button import Button
from ..combobox import ComboBox
from ..field import InputField
from ..menu import Menu
from ..scroll import ScrollPane


class DialogInset(Widget):

    _gfx = {
        "": (
            ("dialog_inset2_border_topleft", "dialog_inset2_border_top", "dialog_inset2_border_topright"),
            ("dialog_inset2_border_left", "dialog_inset2_border_center", "dialog_inset2_border_right"),
            ("dialog_inset2_border_bottomleft", "dialog_inset2_border_bottom", "dialog_inset2_border_bottomright")
        )
    }

    def __init__(self, parent, stretch_dir="both"):

        Widget.__init__(self, "dialog_inset", parent, self._gfx, "", stretch_dir, has_mouse_region=False)

        sizer = Sizer("horizontal")
        self.set_sizer(sizer)
        self._client_sizer = client_sizer = Sizer("vertical")
        sizer.add(client_sizer, proportion=1., expand=True, borders=self.get_gfx_inner_borders())

    def get_client_sizer(self):

        return self._client_sizer


class DialogText(Text):

    def __init__(self, parent, text):

        skin_text = Skin["text"]["dialog"]
        Text.__init__(self, parent, skin_text["font"], skin_text["color"], text)

        self.set_widget_type("dialog_text")


class DialogLabel(Label):

    def __init__(self, parent, back_color, border_color, text, borders=None, stretch_dir=""):

        skin_text = Skin["text"]["dialog"]
        Label.__init__(self, parent, skin_text["font"], skin_text["color"], back_color,
                       border_color, text, borders, stretch_dir)

        self.set_widget_type("dialog_label")


class DialogMessageText(Text):

    def __init__(self, parent, text):

        skin_text = Skin["text"]["dialog_message"]
        Text.__init__(self, parent, skin_text["font"], skin_text["color"], text)

        self.set_widget_type("dialog_message_text")


class DialogStandardButton(Button):

    _gfx = {
        "normal": (("dialog_standard_button_normal_left", "dialog_standard_button_normal_center",
                    "dialog_standard_button_normal_right"),),
        "pressed": (("dialog_standard_button_pressed_left", "dialog_standard_button_pressed_center",
                     "dialog_standard_button_pressed_right"),),
        "hilited": (("dialog_standard_button_hilited_left", "dialog_standard_button_hilited_center",
                     "dialog_standard_button_hilited_right"),)
    }

    def __init__(self, parent, text="", tooltip_text="", command=None):

        Button.__init__(self, parent, self._gfx, text, "", tooltip_text, command,
                        button_type="dialog_standard_button")

        self.set_widget_type("dialog_standard_button")

        sort = parent.get_sort() + 4
        self.get_mouse_region().set_sort(sort)

    def on_left_up(self):

        if self.is_pressed():
            Mgr.do("accept_field_input")

        Button.on_left_up(self)


class DialogButton(Button):

    _gfx = {
        "normal": (("dialog_button_normal_left", "dialog_button_normal_center",
                    "dialog_button_normal_right"),),
        "pressed": (("dialog_button_pressed_left", "dialog_button_pressed_center",
                     "dialog_button_pressed_right"),),
        "hilited": (("dialog_button_hilited_left", "dialog_button_hilited_center",
                     "dialog_button_hilited_right"),),
        "active": (("dialog_button_active_left", "dialog_button_active_center",
                    "dialog_button_active_right"),),
        "disabled": (("dialog_button_disabled_left", "dialog_button_disabled_center",
                    "dialog_button_disabled_right"),)
    }

    def __init__(self, parent, text="", icon_id="", tooltip_text="", command=None):

        Button.__init__(self, parent, self._gfx, text, icon_id, tooltip_text, command,
                        button_type="dialog_button")

        self.set_widget_type("dialog_button")

        self.get_mouse_region().set_sort(parent.get_sort() + 1)


class DialogDropdownButton(Button):

    _gfx = {
        "normal": (("dialog_dropdown_button_normal_left", "dialog_dropdown_button_normal_center",
                    "dialog_dropdown_button_normal_right"),),
        "pressed": (("dialog_dropdown_button_pressed_left", "dialog_dropdown_button_pressed_center",
                     "dialog_dropdown_button_pressed_right"),),
        "hilited": (("dialog_dropdown_button_hilited_left", "dialog_dropdown_button_hilited_center",
                     "dialog_dropdown_button_hilited_right"),),
        "active": (("dialog_dropdown_button_active_left", "dialog_dropdown_button_active_center",
                    "dialog_dropdown_button_active_right"),),
        "disabled": (("dialog_dropdown_button_disabled_left", "dialog_dropdown_button_disabled_center",
                    "dialog_dropdown_button_disabled_right"),)
    }
    _ref_node = NodePath("dropdown_btn_ref_node")
    _menu_offsets = {}

    @classmethod
    def set_ref_node_pos(cls, pos):

        cls._ref_node.set_pos(pos)

    def __init__(self, parent, text="", icon_id="", tooltip_text=""):

        command = self.__show_menu
        Button.__init__(self, parent, self._gfx, text, icon_id, tooltip_text, command,
                        button_type="dialog_button")

        self.set_widget_type("dialog_dropdown_button")

        self.get_mouse_region().set_sort(parent.get_sort() + 1)

        self._menu = Menu(on_hide=self.__on_hide)

        if not self._menu_offsets:
            x, y, w, h = TextureAtlas["regions"]["dialog_dropdown_button_normal_left"]
            self._menu_offsets["top"] = (0, 0)
            self._menu_offsets["bottom"] = (0, h)

    def __on_hide(self):

        if self.is_active():
            self.set_active(False)
            self.on_leave(force=True)

    def __show_menu(self):

        x, y = self.get_pos(ref_node=self._ref_node)
        offset_x, offset_y = self._menu_offsets["bottom"]
        pos = (x + offset_x, y + offset_y)
        offset_x, offset_y = self._menu_offsets["top"]
        w, h = self._menu.get_size()
        alt_pos = (x + offset_x, y + offset_y - h)

        if self._menu.show(pos, alt_pos):
            self.set_active()

    def get_menu(self):

        return self._menu

    def destroy(self):

        Button.destroy(self)

        self._menu.destroy()
        self._menu = None


class DialogToolButton(Button):

    _gfx = {
        "normal": (("dialog_toolbutton_normal",),),
        "pressed": (("dialog_toolbutton_pressed",),),
        "hilited": (("dialog_toolbutton_hilited",),),
        "disabled": (("dialog_toolbutton_disabled",),)
    }

    def __init__(self, parent, text="", icon_id="", tooltip_text="", command=None):

        Button.__init__(self, parent, self._gfx, text, icon_id, tooltip_text, command,
                        button_type="dialog_button")

        self.set_widget_type("dialog_toolbutton")

        self.get_mouse_region().set_sort(parent.get_sort() + 1)


class DialogInputField(InputField):

    _mouse_region_mask = None
    _mouse_watchers = None

    @staticmethod
    def __create_mouse_region_mask():

        d = 100000
        # create a mouse region "mask" to disable interaction with all widgets of whatever
        # dialog is currently active, except input fields, whenever one of those fields is active;
        # the sort value of this region depends on that of the active dialog, so it needs to be
        # set whenever the region is used
        DialogInputField._mouse_region_mask = MouseWatcherRegion("inputfield_mask", -d, d, -d, d)
        # the mouse region mask needs to be added to only the main GUI mouse watcher, since
        # there should be at least one dialog shown, which has already masked the mouse regions
        # controlled by all other mouse watchers
        DialogInputField._mouse_watchers = (Mgr.get("mouse_watcher"),)

    @classmethod
    def _get_mouse_region_mask(cls, mouse_watcher_name):

        if cls._active_field:
            sort = cls._active_field.get_mouse_region().get_sort() - 4
            cls._mouse_region_mask.set_sort(sort)

        return cls._mouse_region_mask

    @staticmethod
    def get_mouse_region_mask():

        if not DialogInputField._mouse_region_mask:
            DialogInputField.__create_mouse_region_mask()

        return DialogInputField._mouse_region_mask

    def __init__(self, parent, border_gfx_data, width, dialog=None, text_color=None,
                 back_color=None, on_accept=None, on_reject=None, on_key_enter=None,
                 on_key_escape=None, allow_reject=True):

        if not self._mouse_region_mask:
            self.__create_mouse_region_mask()

        self._dialog = dialog if dialog else parent
        sort = self._dialog.get_sort() + 8
        cull_bin = ("dialog", sort)

        InputField.__init__(self, parent, border_gfx_data, width, text_color, back_color, sort,
                            cull_bin, on_accept, on_reject, on_key_enter, on_key_escape, allow_reject)

        self.set_widget_type("dialog_input_field")

    def destroy(self):

        InputField.destroy(self)

        self._dialog = None

    def get_dialog(self):

        return self._dialog

    def on_left_down(self):

        InputField.on_left_down(self)

        Mgr.do("ignore_dialog_events")

    def accept_input(self, text_handler=None):

        InputField.accept_input(self, text_handler)

        Mgr.do("accept_dialog_events")

    def reject_input(self):

        InputField.reject_input(self)

        Mgr.do("accept_dialog_events")


class ComboBoxInputField(DialogInputField):

    _border_gfx_data = (("dialog_combobox_normal_left", "dialog_combobox_normal_center",
                         "dialog_combobox_normal_right"),)
    _border_gfx_data2 = (("dialog_combobox2_normal_left", "dialog_combobox_normal_center",
                         "dialog_combobox_normal_right"),)
    _field_borders = ()
    _img_offset = (0, 0)
    _field_borders2 = ()
    _img_offset2 = (0, 0)
    _height = 0

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_combobox_field"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)
        l, r, b, t = TextureAtlas["outer_borders"]["dialog_combobox2_field"]
        cls._field_borders2 = (l, r, b, t)
        cls._img_offset2 = (-l, -t)
        cls._height = Skin["options"]["combobox_field_height"]

    def __init__(self, parent, dialog, width, text_color=None, back_color=None):

        if not self._field_borders:
            self.__set_field_borders()

        gfx_data = self._border_gfx_data if parent.has_icon() else self._border_gfx_data2
        DialogInputField.__init__(self, parent, gfx_data, width, dialog, text_color, back_color)

        self.set_widget_type("dialog_combo_field")

        img_offset = self._img_offset if parent.has_icon() else self._img_offset2
        self.set_image_offset(img_offset)

    def get_outer_borders(self):

        return self._field_borders if self.get_parent().has_icon() else self._field_borders2

    def get_image(self, state=None, composed=True, draw_border=False, crop=True):

        return DialogInputField.get_image(self, state, composed, draw_border=draw_border, crop=crop)

    def accept_input(self, text_handler=None):

        DialogInputField.accept_input(self, text_handler=self.get_parent().set_text)

    def set_value(self, value_id, value, text_handler=None, handle_value=True):

        DialogInputField.set_value(self, value_id, value, text_handler=self.get_parent().set_text,
                                   handle_value=handle_value)

    def set_text(self, value_id, text, text_handler=None):

        DialogInputField.set_text(self, value_id, text, text_handler=self.get_parent().set_text)


class DialogComboBox(ComboBox):

    _gfx = {
        "normal": (("dialog_combobox_normal_left", "dialog_combobox_normal_center",
                    "dialog_combobox_normal_right"),),
        "pressed": (("dialog_combobox_pressed_left", "dialog_combobox_pressed_center",
                     "dialog_combobox_pressed_right"),),
        "hilited": (("dialog_combobox_hilited_left", "dialog_combobox_hilited_center",
                     "dialog_combobox_hilited_right"),),
        "active": (("dialog_combobox_pressed_left", "dialog_combobox_pressed_center",
                    "dialog_combobox_pressed_right"),),
        "disabled": (("dialog_combobox_disabled_left", "dialog_combobox_disabled_center",
                    "dialog_combobox_disabled_right"),)
    }
    _gfx2 = {
        "normal": (("dialog_combobox2_normal_left", "dialog_combobox_normal_center",
                    "dialog_combobox_normal_right"),),
        "pressed": (("dialog_combobox2_pressed_left", "dialog_combobox_pressed_center",
                     "dialog_combobox_pressed_right"),),
        "hilited": (("dialog_combobox2_hilited_left", "dialog_combobox_hilited_center",
                     "dialog_combobox_hilited_right"),),
        "active": (("dialog_combobox2_pressed_left", "dialog_combobox_pressed_center",
                    "dialog_combobox_pressed_right"),),
        "disabled": (("dialog_combobox2_disabled_left", "dialog_combobox_disabled_center",
                    "dialog_combobox_disabled_right"),)
    }
    _box_borders = ()
    _box_borders2 = ()
    _field_offset = (0, 0)
    _field_offset2 = (0, 0)
    _field_label_offset = (0, 0)
    _icon_offset = (0, 0)
    _menu_offsets = {"top": (0, 0), "bottom": (0, 0)}
    _menu_offsets2 = {"top": (0, 0), "bottom": (0, 0)}

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["inner_borders"]["dialog_combobox"]
        cls._box_borders = (l, r, b, t)
        cls._field_offset = (l, t)
        x, y, w, h = TextureAtlas["regions"]["dialog_combobox_normal_left"]
        cls._menu_offsets["top"] = (l, t)
        cls._menu_offsets["bottom"] = (l, h - b)
        l, r, b, t = TextureAtlas["inner_borders"]["dialog_combobox2"]
        cls._box_borders2 = (l, r, b, t)
        cls._field_offset2 = (l, t)
        x, y, w, h = TextureAtlas["regions"]["dialog_combobox2_normal_left"]
        cls._menu_offsets2["top"] = (l, t)
        cls._menu_offsets2["bottom"] = (l, h - b)
        l, r, b, t = TextureAtlas["inner_borders"]["dialog_combobox_field"]
        cls._field_label_offset = (l, t)
        l, r, b, t = TextureAtlas["inner_borders"]["dialog_combobox_icon_area"]
        cls._icon_offset = (l, t)

    def __init__(self, parent, field_width, text="", icon_id="", tooltip_text="", editable=False):

        if not self._box_borders:
            self.__set_borders()

        if icon_id:
            gfx_data = self._gfx
        else:
            gfx_data = self._gfx2

        ComboBox.__init__(self, parent, field_width, gfx_data, text, icon_id, tooltip_text, editable)

        self.set_widget_type("dialog_combobox")

        self.get_mouse_region().set_sort(parent.get_sort() + 1)

        x, y, w, h = TextureAtlas["regions"]["dialog_combobox_field_back"]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        img = PNMImage(field_width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)

        if editable:
            input_field = ComboBoxInputField(self, parent, field_width)
            self.set_input_field(input_field)

    def set_size(self, size, includes_borders=True, is_min=False):

        width, height = ComboBox.set_size(self, size, includes_borders, is_min)

        l, r, b, t = self.get_inner_borders()
        field_width = width - l + r
        x, y, w, h = TextureAtlas["regions"]["dialog_combobox_field_back"]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        img = PNMImage(field_width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)

        return width, height

    def get_inner_borders(self):

        if self.has_icon():
            return self._box_borders
        else:
            return self._box_borders2

    def get_field_offset(self):

        if self.has_icon():
            return self._field_offset
        else:
            return self._field_offset2

    def get_field_label_offset(self):

        return self._field_label_offset

    def get_icon_offset(self):

        return self._icon_offset

    def get_menu_offset(self, edge="bottom"):

        if self.has_icon():
            return self._menu_offsets[edge]
        else:
            return self._menu_offsets2[edge]


class DialogScrollPane(ScrollPane):

    def __init__(self, dialog, pane_id, scroll_dir, frame_client_size, stretch_dir=""):

        frame_gfx_data = {
            "": (
                ("dialog_inset2_border_topleft", "dialog_inset2_border_top", "dialog_inset2_border_topright"),
                ("dialog_inset2_border_left", "dialog_inset2_border_center", "dialog_inset2_border_right"),
                ("dialog_inset2_border_bottomleft", "dialog_inset2_border_bottom", "dialog_inset2_border_bottomright")
            )
        }

        if scroll_dir == "horizontal":
            bar_gfx_data = {
                "": (
                    ("dialog_scrollbar_h_topleft", "dialog_scrollbar_h_top", "dialog_scrollbar_h_topright"),
                    ("dialog_scrollbar_h_left", "dialog_scrollbar_h_center", "dialog_scrollbar_h_right"),
                    ("dialog_scrollbar_h_bottomleft", "dialog_scrollbar_h_bottom", "dialog_scrollbar_h_bottomright")
                )
            }
        else:
            bar_gfx_data = {
                "": (
                    ("dialog_scrollbar_v_topleft", "dialog_scrollbar_v_top", "dialog_scrollbar_v_topright"),
                    ("dialog_scrollbar_v_left", "dialog_scrollbar_v_center", "dialog_scrollbar_v_right"),
                    ("dialog_scrollbar_v_bottomleft", "dialog_scrollbar_v_bottom", "dialog_scrollbar_v_bottomright")
                )
            }

        thumb_gfx_data = {
            "normal": (
                ("dialog_scrollthumb_normal_topleft", "dialog_scrollthumb_normal_top",
                 "dialog_scrollthumb_normal_topright"),
                ("dialog_scrollthumb_normal_left", "dialog_scrollthumb_normal_center",
                 "dialog_scrollthumb_normal_right"),
                ("dialog_scrollthumb_normal_bottomleft", "dialog_scrollthumb_normal_bottom",
                 "dialog_scrollthumb_normal_bottomright")
            ),
            "hilited": (
                ("dialog_scrollthumb_hilited_topleft", "dialog_scrollthumb_hilited_top",
                 "dialog_scrollthumb_hilited_topright"),
                ("dialog_scrollthumb_hilited_left", "dialog_scrollthumb_hilited_center",
                 "dialog_scrollthumb_hilited_right"),
                ("dialog_scrollthumb_hilited_bottomleft", "dialog_scrollthumb_hilited_bottom",
                 "dialog_scrollthumb_hilited_bottomright")
            )
        }
        bar_inner_border_id = "dialog_scrollbar_{}".format("h" if scroll_dir == "horizontal" else "v")
        ScrollPane.__init__(self, dialog, pane_id, scroll_dir, "dialog", frame_gfx_data,
                            bar_gfx_data, thumb_gfx_data, bar_inner_border_id, "dialog_main",
                            frame_client_size, stretch_dir, frame_has_mouse_region=False)

        self.setup()
        mouse_watcher = self.get_mouse_watcher()
        mouse_watcher.add_region(dialog.get_mouse_region_mask())
        mouse_watcher.add_region(DialogInputField.get_mouse_region_mask())

        self._dialog = dialog

    def _can_scroll(self):

        if not self._dialog.is_top_dialog() or Mgr.get("active_input_field") or Menu.is_menu_shown():
            return False

        return True

    def get_dialog(self):

        return self._dialog

    def destroy(self):

        ScrollPane.destroy(self)

        self._dialog = None
