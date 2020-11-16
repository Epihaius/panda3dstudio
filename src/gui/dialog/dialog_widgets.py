from ..base import *
from ..group import WidgetGroup
from ..text import Text, Label
from ..button import Button
from ..combobox import ComboBox
from ..checkbtn import CheckButton
from ..radiobtn import RadioButton, RadioButtonGroup
from ..field import InputField, SliderInputField, SpinnerInputField, SpinnerButton
from ..menu import Menu
from ..scroll import ScrollPane


class DialogWidgetGroup(WidgetGroup):

    def __init__(self, parent, title=""):

        title_bg_tex_id = Skin.atlas.gfx_ids["dialog"][""][1][1]

        WidgetGroup.__init__(self, parent, title_bg_tex_id, "dialog", title)

    @property
    def sort(self):

        return self.parent.sort


class DialogInset(Widget):

    def __init__(self, parent):

        gfx_ids = {"": Skin.atlas.gfx_ids["inset"]["dialog"]}

        Widget.__init__(self, "dialog_inset", parent, gfx_ids, "", has_mouse_region=False)

        sizer = Sizer("horizontal")
        self.sizer = sizer
        self._client_sizer = client_sizer = Sizer("vertical")
        sizer.add(client_sizer, (1., 1.), borders=self.gfx_inner_borders)

    @property
    def client_sizer(self):

        return self._client_sizer


class DialogText(Text):

    def __init__(self, parent, text, text_type="dialog"):

        skin_text = Skin.text[text_type]

        Text.__init__(self, parent, skin_text["font"], skin_text["color"], text)

        self.widget_type = "dialog_text"


class DialogLabel(Label):

    def __init__(self, parent, back_color, border_color, text, borders=None):

        skin_text = Skin.text["dialog"]

        Label.__init__(self, parent, skin_text["font"], skin_text["color"], back_color,
                       border_color, text, borders)

        self.widget_type = "dialog_label"


class DialogButton(Button):

    def __init__(self, parent, text="", icon_id="", tooltip_text=""):

        gfx_ids = Skin.atlas.gfx_ids["dialog_button"]

        Button.__init__(self, parent, gfx_ids, text, icon_id, tooltip_text,
                        button_type="dialog_button")

        self.widget_type = "dialog_button"

        self.mouse_region.sort = parent.sort + 1


class DialogDropdownButton(Button):

    _ref_node = NodePath("dropdown_btn_ref_node")
    _menu_offsets = {}

    @classmethod
    def set_ref_node_pos(cls, pos):

        cls._ref_node.set_pos(pos)

    def __init__(self, parent, text="", icon_id="", tooltip_text=""):

        gfx_ids = Skin.atlas.gfx_ids["dialog_dropdown_button"]

        Button.__init__(self, parent, gfx_ids, text, icon_id, tooltip_text,
                        button_type="dialog_button")

        self.widget_type = "dialog_dropdown_button"
        self.command = self.__show_menu

        self.mouse_region.sort = parent.sort + 1

        self._menu = Menu(on_hide=self.__on_hide)

        if not self._menu_offsets:
            x, y, w, h = Skin.atlas.regions[gfx_ids["normal"][0][0]]
            self._menu_offsets["top"] = (0, 0)
            self._menu_offsets["bottom"] = (0, h)

    def __on_hide(self):

        if self.active:
            self.active = False
            self.on_leave(force=True)

    def __show_menu(self):

        x, y = self.get_pos(ref_node=self._ref_node)
        offset_x, offset_y = self._menu_offsets["bottom"]
        pos = (x + offset_x, y + offset_y)
        offset_x, offset_y = self._menu_offsets["top"]
        w, h = self._menu.get_size()
        alt_pos = (x + offset_x, y + offset_y - h)

        if self._menu.show(pos, alt_pos):
            self.active = True

    def get_menu(self):

        return self._menu

    def destroy(self):

        Button.destroy(self)

        self._menu.destroy()
        self._menu = None


class DialogToolButton(Button):

    def __init__(self, parent, text="", icon_id="", tooltip_text=""):

        gfx_ids = Skin.atlas.gfx_ids["dialog_toolbutton"]

        Button.__init__(self, parent, gfx_ids, text, icon_id, tooltip_text,
                        button_type="dialog_button")

        self.widget_type = "dialog_toolbutton"

        self.mouse_region.sort = parent.sort + 1


class DialogCheckButton(CheckButton):

    _btn_borders = ()
    _img_offset = (0, 0)
    _box_img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, _, b, t = Skin.atlas.outer_borders["dialog_checkbox"]
        cls._box_img_offset = (-l, -t)
        font = Skin.text["dialog_checkbutton"]["font"]
        h_f = font.get_height()
        h = Skin.options["checkbox_height"]
        dh = max(0, h_f - h) // 2
        b = max(0, b - dh)
        t = max(0, t - dh)
        cls._btn_borders = (l, 0, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent, text="", text_offset=5):

        if not self._btn_borders:
            self.__set_borders()

        mark_color = Skin.colors["dialog_checkmark"]
        back_color = Skin.colors["dialog_checkbox_back"]

        CheckButton.__init__(self, parent, mark_color, back_color, text, text_offset)

        if not self._border_image:
            self.__create_border_image()

        self.create_base_image()

        self.mouse_region.sort = parent.sort + 1

    def __create_border_image(self):

        gfx_id = Skin.atlas.gfx_ids["checkbox"]["dialog"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        tmp_widget = Widget("tmp", self.parent, {"": ((gfx_id,),)}, has_mouse_region=False)
        tmp_widget.set_size((w, h), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def get_border_image(self):

        return self._border_image

    def get_box_image_offset(self):

        return self._box_img_offset


class DialogRadioButton(RadioButton):

    _btn_borders = ()
    _img_offset = (0, 0)
    _box_img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, _, b, t = Skin.atlas.outer_borders["dialog_radiobox"]
        cls._box_img_offset = (-l, -t)
        font = Skin.text["dialog_radiobutton"]["font"]
        h_f = font.get_height()
        h = Skin.options["radiobox_height"]
        dh = max(0, h_f - h) // 2
        b = max(0, b - dh)
        t = max(0, t - dh)
        cls._btn_borders = (l, 0, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent, btn_id, text, group):

        if not self._btn_borders:
            self.__set_borders()

        RadioButton.__init__(self, parent, btn_id, text, group)

        if not self._border_image:
            self.__create_border_image()

        self.create_base_image()

        self.mouse_region.sort = parent.sort + 1

    def __create_border_image(self):

        gfx_ids = Skin.atlas.gfx_ids["radiobox"]["dialog"]
        x, y, w, h = Skin.atlas.regions[gfx_ids[0][0]]
        tmp_widget = Widget("tmp", self.parent, {"": gfx_ids}, has_mouse_region=False)
        tmp_widget.set_size((w, h), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def get_border_image(self):

        return self._border_image

    def get_box_image_offset(self):

        return self._box_img_offset


class DialogRadioButtonGroup(RadioButtonGroup):

    def __init__(self, parent, prim_dir, prim_limit=0, gaps=(0, 0), expand=False,
                 text_offset=5):

        bullet_color = Skin.colors["dialog_bullet"]
        back_color = Skin.colors["dialog_radiobox_back"]

        RadioButtonGroup.__init__(self, bullet_color, back_color, prim_dir, prim_limit,
                                  gaps, expand, text_offset)

        self._parent = parent
        self.delay_card_update()

    def add_button(self, btn_id, text, index=None):

        btn = DialogRadioButton(self._parent, btn_id, text, self)
        RadioButtonGroup.add_button(self, btn_id, btn, index)

        return btn


class MouseWatcherMixin:

    _mouse_region_mask = None
    _mouse_watchers = None

    @staticmethod
    def __create_mouse_region_mask():

        d = 100000
        # create a mouse region "mask" to disable interaction with all widgets of whatever
        # dialog is currently active, except input fields, whenever one of those fields is active;
        # the sort value of this region depends on that of the active dialog, so it needs to be
        # set whenever the region is used
        MouseWatcherMixin._mouse_region_mask = MouseWatcherRegion("inputfield_mask", -d, d, -d, d)
        # the mouse region mask needs to be added to only the main GUI mouse watcher, since
        # there should be at least one dialog shown, which has already masked the mouse regions
        # controlled by all other mouse watchers
        MouseWatcherMixin._mouse_watchers = (Mgr.get("mouse_watcher"),)

    @classmethod
    def _get_mouse_region_mask(cls, mouse_watcher_name):

        if cls._active_field:
            sort = cls._active_field.mouse_region.sort - 4
            cls._mouse_region_mask.sort = sort

        return cls._mouse_region_mask

    @staticmethod
    def get_mouse_region_mask():

        if not MouseWatcherMixin._mouse_region_mask:
            MouseWatcherMixin.__create_mouse_region_mask()

        return MouseWatcherMixin._mouse_region_mask

    def __init__(self):

        if not self._mouse_region_mask:
            self.__create_mouse_region_mask()


class GfxMixin:

    _field_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["dialog_inset1"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    def __init__(self, alt_field_borders=None):

        self._alt_field_borders = alt_field_borders

        if not GfxMixin._field_borders:
            GfxMixin.__set_field_borders()

    @property
    def outer_borders(self):

        if self._alt_field_borders:
            return self._alt_field_borders

        return self._field_borders


class DialogInputField(MouseWatcherMixin, GfxMixin, InputField):

    def __init__(self, parent, width, font=None, text_color=None, back_color=None,
                 alt_field_borders=None, alt_border_gfx_ids=None, alt_image_offset=None):

        self._dialog = parent.root_container
        sort = self._dialog.sort + 8
        cull_bin = ("dialog", sort)

        MouseWatcherMixin.__init__(self)
        GfxMixin.__init__(self, alt_field_borders)
        field_gfx_ids = Skin.atlas.gfx_ids["field"]["dialog"]
        gfx_ids = alt_border_gfx_ids if alt_border_gfx_ids else field_gfx_ids
        img_offset = alt_image_offset if alt_image_offset else self._img_offset
        InputField.__init__(self, parent, width, gfx_ids, img_offset, font,
                            text_color, back_color, sort, cull_bin)

        self.widget_type = "dialog_input_field"

    def destroy(self):

        InputField.destroy(self)

        self._dialog = None

    def get_dialog(self):

        return self._dialog

    def _on_left_up(self):

        if InputField._on_left_up(self):
            Mgr.do("ignore_dialog_events")

    def accept_input(self, text_handler=None):

        InputField.accept_input(self, text_handler)

        Mgr.do("accept_dialog_events")

    def reject_input(self):

        InputField.reject_input(self)

        Mgr.do("accept_dialog_events")


class DialogSliderField(MouseWatcherMixin, GfxMixin, SliderInputField):

    def __init__(self, parent, width, font=None, text_color=None, back_color=None,
                 alt_field_borders=None, alt_border_gfx_ids=None, alt_image_offset=None):

        self._dialog = parent.root_container
        sort = self._dialog.sort + 8
        cull_bin = ("dialog", sort)

        MouseWatcherMixin.__init__(self)
        GfxMixin.__init__(self, alt_field_borders)
        field_gfx_ids = Skin.atlas.gfx_ids["field"]["dialog"]
        gfx_ids = alt_border_gfx_ids if alt_border_gfx_ids else field_gfx_ids
        img_offset = alt_image_offset if alt_image_offset else self._img_offset
        SliderInputField.__init__(self, parent, width, gfx_ids, img_offset, font,
                                  text_color, back_color, sort, cull_bin)

        self.widget_type = "dialog_input_field"

    def destroy(self):

        SliderInputField.destroy(self)

        self._dialog = None

    def get_dialog(self):

        return self._dialog

    def _on_slide_start(self):

        Mgr.do("ignore_dialog_events")

    def _on_slide_end(self, cancelled=False):

        SliderInputField._on_slide_end(self, cancelled)

        Mgr.do("accept_dialog_events")

    def _on_left_up(self):

        if SliderInputField._on_left_up(self):
            Mgr.do("ignore_dialog_events")

    def accept_input(self, text_handler=None):

        SliderInputField.accept_input(self, text_handler)

        Mgr.do("accept_dialog_events")

    def reject_input(self):

        SliderInputField.reject_input(self)

        Mgr.do("accept_dialog_events")


class DialogSpinnerButton(SpinnerButton):

    def __init__(self, parent, gfx_ids):

        SpinnerButton.__init__(self, parent, gfx_ids)

        self.widget_type = "dialog_spinner_button"

        self.mouse_region.sort = parent.sort + 1

    def _on_spin_start(self):

        Mgr.do("ignore_dialog_events")

    def _on_spin_end(self, cancelled=False):

        Mgr.do("accept_dialog_events")


class DialogSpinnerField(SpinnerInputField):

    _border_image = None

    @classmethod
    def __create_border_image(cls):

        gfx_id = Skin.atlas.gfx_ids["dialog_spin_up_button"]["normal"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        l, r, b, t = Skin.atlas.outer_borders["dialog_inset1"]
        gfx_ids = {"": Skin.atlas.gfx_ids["spinner"]["dialog"]}
        tmp_widget = Widget("tmp", None, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((w + r, h * 2 + b + t), is_min=True)
        tmp_widget.update_images()
        cls._border_image = tmp_widget.get_image()
        tmp_widget.destroy()

    def __init__(self, parent, width, font=None, text_color=None, back_color=None,
                 has_slider=False):

        if not self._border_image:
            self.__create_border_image()

        gfx_ids = Skin.atlas.gfx_ids["spinner_field"]["dialog"]
        l, r, b, t = Skin.atlas.outer_borders["dialog_inset1"]
        borders = (l, 0, b, t)  # right field border offset must be zero

        if has_slider:
            field = DialogSliderField(parent, width, font, text_color, back_color, borders, gfx_ids)
        else:
            field = DialogInputField(parent, width, font, text_color, back_color, borders, gfx_ids)

        incr_btn_gfx_ids = Skin.atlas.gfx_ids["dialog_spin_up_button"]
        decr_btn_gfx_ids = Skin.atlas.gfx_ids["dialog_spin_down_button"]
        incr_btn = DialogSpinnerButton(parent, incr_btn_gfx_ids)
        decr_btn = DialogSpinnerButton(parent, decr_btn_gfx_ids)
        borders = (0, r, b, t)  # left spinner border offset must be zero
        SpinnerInputField.__init__(self, parent, field, incr_btn, decr_btn, borders)

    def get_border_image(self):

        return self._border_image


class ComboBoxInputField(DialogInputField):

    _alt_borders = ()
    _alt_offset = (0, 0)
    _alt_borders_icon = ()
    _alt_offset_icon = (0, 0)
    _height = 0

    @classmethod
    def __set_alt_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["dialog_combobox_field"]
        cls._alt_borders = (l, r, b, t)
        cls._alt_offset = (-l, -t)
        l, r, b, t = Skin.atlas.outer_borders["dialog_combobox_field+icon"]
        cls._alt_borders_icon = (l, r, b, t)
        cls._alt_offset_icon = (-l, -t)
        cls._height = Skin.options["combobox_field_height"]

    def __init__(self, parent, value_id, value_type, handler, width,
                 font=None, text_color=None, back_color=None):

        if not self._alt_borders:
            self.__set_alt_borders()

        borders = self._alt_borders_icon if parent.has_icon() else self._alt_borders
        gfx_ids_no_icon = Skin.atlas.gfx_ids["combo_field"]["dialog"]
        gfx_ids_icon = Skin.atlas.gfx_ids["combo_field"]["dialog+icon"]
        gfx_ids = gfx_ids_icon if parent.has_icon() else gfx_ids_no_icon
        img_offset = self._alt_offset_icon if parent.has_icon() else self._alt_offset
        DialogInputField.__init__(self, parent, width, font, text_color, back_color,
                                  alt_field_borders=borders, alt_border_gfx_ids=gfx_ids,
                                  alt_image_offset=img_offset)

        self.widget_type = "dialog_combo_field"
        self.value_id = value_id
        self.value_type = value_type
        self.set_value_handler(handler)

    def get_image(self, state=None, composed=True, draw_border=False, crop=True):

        return DialogInputField.get_image(self, state, composed, draw_border=draw_border, crop=crop)

    def accept_input(self, text_handler=None):

        DialogInputField.accept_input(self, text_handler=self.parent.set_text)

    def set_value(self, value, text_handler=None, handle_value=False):

        DialogInputField.set_value(self, value, text_handler=self.parent.set_text,
                                   handle_value=handle_value)

    def set_text(self, text, text_handler=None):

        DialogInputField.set_text(self, text, text_handler=self.parent.set_text)


class DialogComboBox(ComboBox):

    _box_borders = ()
    _box_borders_icon = ()
    _field_offset = (0, 0)
    _field_offset_icon = (0, 0)
    _field_label_offset = (0, 0)
    _icon_offset = (0, 0)
    _menu_offsets = {"top": (0, 0), "bottom": (0, 0)}
    _menu_offsets_icon = {"top": (0, 0), "bottom": (0, 0)}

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.inner_borders["dialog_combobox"]
        cls._box_borders = (l, r, b, t)
        cls._field_offset = (l, t)
        gfx_id = Skin.atlas.gfx_ids["dialog_combobox"]["normal"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        cls._menu_offsets["top"] = (l, t)
        cls._menu_offsets["bottom"] = (l, h - b)
        l, r, b, t = Skin.atlas.inner_borders["dialog_combobox+icon"]
        cls._box_borders_icon = (l, r, b, t)
        cls._field_offset_icon = (l, t)
        gfx_id = Skin.atlas.gfx_ids["dialog_combobox+icon"]["normal"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        cls._menu_offsets_icon["top"] = (l, t)
        cls._menu_offsets_icon["bottom"] = (l, h - b)
        l, r, b, t = Skin.atlas.inner_borders["dialog_combobox_field"]
        cls._field_label_offset = (l, t)
        l, r, b, t = Skin.atlas.inner_borders["dialog_combobox_icon_area"]
        cls._icon_offset = (l, t)

    def __init__(self, parent, field_width, text="", icon_id="", tooltip_text=""):

        if not self._box_borders:
            self.__set_borders()

        gfx_ids = Skin.atlas.gfx_ids["dialog_combobox" + ("+icon" if icon_id else "")]

        ComboBox.__init__(self, parent, field_width, gfx_ids, text, icon_id, tooltip_text)

        self.widget_type = "dialog_combobox"

        self.mouse_region.sort = parent.sort + 1

        gfx_id = Skin.atlas.gfx_ids["combo_field_back"]["dialog"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        img = PNMImage(field_width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)

    def set_size(self, size, includes_borders=True, is_min=False):

        width, height = ComboBox.set_size(self, size, includes_borders, is_min)

        l, r, b, t = self.inner_borders
        field_width = width - l + r
        gfx_id = Skin.atlas.gfx_ids["combo_field_back"]["dialog"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        img = PNMImage(field_width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)

        return width, height

    @property
    def inner_borders(self):

        if self.has_icon():
            return self._box_borders_icon
        else:
            return self._box_borders

    def get_field_offset(self):

        if self.has_icon():
            return self._field_offset_icon
        else:
            return self._field_offset

    def get_field_label_offset(self):

        return self._field_label_offset

    def get_icon_offset(self):

        return self._icon_offset

    def get_menu_offset(self, edge="bottom"):

        if self.has_icon():
            return self._menu_offsets_icon[edge]
        else:
            return self._menu_offsets[edge]

    def set_input_field(self, value_id, value_type, handler):

        input_field = ComboBoxInputField(self, value_id, value_type, handler, self._field_width)
        self.input_field = input_field

        return input_field


class DialogScrollPane(ScrollPane):

    def __init__(self, parent, pane_id, scroll_dir, frame_client_size):

        frame_gfx_ids = {"": Skin.atlas.gfx_ids["scrollframe"]["dialog"]}
        bar_gfx_ids = {"": Skin.atlas.gfx_ids["scrollbar"][f"dialog_{scroll_dir}"]}
        thumb_gfx_ids = Skin.atlas.gfx_ids["dialog_scrollthumb"]
        bar_inner_border_id = f'dialog_scrollbar_{"h" if scroll_dir == "horizontal" else "v"}'
        bg_tex_id = Skin.atlas.gfx_ids["dialog"][""][1][1]

        ScrollPane.__init__(self, parent, pane_id, scroll_dir, "dialog", frame_gfx_ids,
                            bar_gfx_ids, thumb_gfx_ids, bar_inner_border_id, bg_tex_id,
                            frame_client_size, frame_has_mouse_region=False)

        self.setup()
        dialog = parent.get_ancestor("dialog")
        mouse_watcher = self.mouse_watcher
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
