from ..base import *
from ..text import Text
from ..button import Button
from ..combobox import ComboBox
from ..field import InputField, SliderInputField, SpinnerInputField, SpinnerButton
from ..checkbtn import CheckButton
from ..colorbox import ColorBox
from ..radiobtn import RadioButton, RadioButtonGroup


class PanelText(Text):

    def __init__(self, parent, text):

        skin_text = Skin["text"]["panel"]
        Text.__init__(self, parent, skin_text["font"], skin_text["color"], text)

        self.widget_type = "panel_text"


class PanelButton(Button):

    _gfx = {
       "normal": (("panel_button_normal_left", "panel_button_normal_center",
                  "panel_button_normal_right"),),
       "pressed": (("panel_button_pressed_left", "panel_button_pressed_center",
                   "panel_button_pressed_right"),),
       "hilited": (("panel_button_hilited_left", "panel_button_hilited_center",
                   "panel_button_hilited_right"),),
       "active": (("panel_button_active_left", "panel_button_active_center",
                  "panel_button_active_right"),),
       "disabled": (("panel_button_disabled_left", "panel_button_disabled_center",
                  "panel_button_disabled_right"),)
    }

    def __init__(self, parent, text="", icon_id="", tooltip_text="", command=None):

        Button.__init__(self, parent, self._gfx, text, icon_id, tooltip_text, command,
                        button_type="panel_button")

        self.widget_type = "panel_button"
        self.delay_card_update()


class PanelCheckButton(CheckButton):

    _border_gfx_data = (("panel_checkbox",),)
    _btn_borders = ()
    _img_offset = (0, 0)
    _box_img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, _, b, t = TextureAtlas["outer_borders"]["panel_checkbox"]
        cls._box_img_offset = (-l, -t)
        font = Skin["text"]["panel_checkbutton"]["font"]
        h_f = font.get_height()
        h = Skin["options"]["checkbox_height"]
        dh = max(0, h_f - h) // 2
        b = max(0, b - dh)
        t = max(0, t - dh)
        cls._btn_borders = (l, 0, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent, command, text="", text_offset=5):

        if not self._btn_borders:
            self.__set_borders()

        mark_color = Skin["colors"]["panel_checkmark"]
        back_color = Skin["colors"]["panel_checkbox_back"]

        CheckButton.__init__(self, parent, "panel", command, mark_color,
                             back_color, text, text_offset)

        self.delay_card_update()

        if not self._border_image:
            self.__create_border_image()

        self.create_base_image()

    def __create_border_image(self):

        x, y, w, h = TextureAtlas["regions"]["panel_checkbox"]
        gfx_data = {"": self._border_gfx_data}
        tmp_widget = Widget("tmp", self.parent, gfx_data, has_mouse_region=False)
        tmp_widget.set_size((w, h), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def get_border_image(self):

        return self._border_image

    def get_box_image_offset(self):

        return self._box_img_offset


class PanelColorBox(ColorBox):

    _border_gfx_data = (
        ("panel_inset_border_topleft", "panel_inset_border_top", "panel_inset_border_topright"),
        ("panel_inset_border_left", "panel_inset_border_center", "panel_inset_border_right"),
        ("panel_inset_border_bottomleft", "panel_inset_border_bottom", "panel_inset_border_bottomright")
    )
    _box_borders = ()
    _img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["panel_inset"]
        cls._box_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent, command=None, color=None, dialog_title=""):

        if not self._box_borders:
            self.__set_borders()

        ColorBox.__init__(self, parent, command, color, dialog_title)

        self.widget_type = "panel_colorbox"
        self.delay_card_update()

        if not self._border_image:
            self.__create_border_image()

        self.image_offset = self._img_offset
        self.outer_borders = self._box_borders

    def __create_border_image(self):

        w, h = self.get_size()
        l, r, b, t = self._box_borders
        width = w + l + r
        height = h + b + t
        gfx_data = {"": self._border_gfx_data}
        tmp_widget = Widget("tmp", self.parent, gfx_data, has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def get_border_image(self):

        return self._border_image


class PanelRadioButton(RadioButton):

    _border_gfx_data = (("panel_radiobox",),)
    _btn_borders = ()
    _img_offset = (0, 0)
    _box_img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["panel_radiobox"]
        cls._box_img_offset = (-l, -t)
        font = Skin["text"]["panel_radiobutton"]["font"]
        h_f = font.get_height()
        h = Skin["options"]["radiobox_height"]
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

        RadioButton.__init__(self, parent, "panel", btn_id, text, group)

        if not self._border_image:
            self.__create_border_image()

        self.create_base_image()

    def __create_border_image(self):

        x, y, w, h = TextureAtlas["regions"]["panel_radiobox"]
        gfx_data = {"": self._border_gfx_data}
        tmp_widget = Widget("tmp", self.parent, gfx_data, has_mouse_region=False)
        tmp_widget.set_size((w, h), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def get_border_image(self):

        return self._border_image

    def get_box_image_offset(self):

        return self._box_img_offset


class PanelRadioButtonGroup(RadioButtonGroup):

    def __init__(self, parent, rows=0, columns=0, gap_h=0, gap_v=0, stretch=False,
                 text_offset=5):

        bullet_color = Skin["colors"]["panel_bullet"]
        back_color = Skin["colors"]["panel_radiobox_back"]

        RadioButtonGroup.__init__(self, bullet_color, back_color, rows, columns,
                                  gap_h, gap_v, stretch, text_offset)

        self._parent = parent
        self.delay_card_update()

    def add_button(self, btn_id, text):

        btn = PanelRadioButton(self._parent, btn_id, text, self)
        RadioButtonGroup.add_button(self, btn_id, btn)


class GfxMixin:

    _border_gfx_data = (
        ("panel_inset_border_topleft", "panel_inset_border_top", "panel_inset_border_topright"),
        ("panel_inset_border_left", "panel_inset_border_center", "panel_inset_border_right"),
        ("panel_inset_border_bottomleft", "panel_inset_border_bottom", "panel_inset_border_bottomright")
    )
    _field_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["panel_inset"]
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


class PanelInputField(GfxMixin, InputField):

    def __init__(self, parent, value_id, value_type, handler, width,
                 font=None, text_color=None, back_color=None,
                 alt_field_borders=None, alt_border_gfx_data=None):

        GfxMixin.__init__(self, alt_field_borders)
        gfx_data = alt_border_gfx_data if alt_border_gfx_data else self._border_gfx_data
        InputField.__init__(self, parent, value_id, value_type, handler, width,
                            gfx_data, self._img_offset, font, text_color, back_color)

        self.widget_type = "panel_input_field"
        self.delay_card_update()

        panel_stack = self.get_ancestor("panel_stack")

        if panel_stack:
            scissor_effect = panel_stack.get_scissor_effect()
            self.set_scissor_effect(scissor_effect)


class PanelSliderField(GfxMixin, SliderInputField):

    def __init__(self, parent, value_id, value_type, value_range, handler,
                 width, font=None, text_color=None, back_color=None,
                 alt_field_borders=None, alt_border_gfx_data=None):

        GfxMixin.__init__(self, alt_field_borders)
        gfx_data = alt_border_gfx_data if alt_border_gfx_data else self._border_gfx_data
        SliderInputField.__init__(self, parent, value_id, value_type, value_range,
                                  handler, width, gfx_data, self._img_offset,
                                  font, text_color, back_color)

        self.widget_type = "panel_input_field"
        self.delay_card_update()

        panel_stack = self.get_ancestor("panel_stack")

        if panel_stack:
            scissor_effect = panel_stack.get_scissor_effect()
            self.set_scissor_effect(scissor_effect)


class PanelSpinnerButton(SpinnerButton):

    def __init__(self, parent, gfx_data):

        SpinnerButton.__init__(self, parent, gfx_data)

        self.widget_type = "panel_spinner_button"
        self.delay_card_update()


class PanelSpinnerField(SpinnerInputField):

    _border_image = None

    @classmethod
    def __create_border_image(cls):

        x, y, w, h = TextureAtlas["regions"]["panel_spin_up_button_normal"]
        l, r, b, t = TextureAtlas["outer_borders"]["panel_inset"]
        # spinner border image should not contain left border parts, so these are replaced with
        # central parts
        border_gfx_data = (
            ("panel_inset_border_top", "panel_inset_border_top", "panel_inset_border_topright"),
            ("panel_inset_border_center", "panel_inset_border_center", "panel_inset_border_right"),
            ("panel_inset_border_bottom", "panel_inset_border_bottom", "panel_inset_border_bottomright")
        )
        gfx_data = {"": border_gfx_data}
        tmp_widget = Widget("tmp", None, gfx_data, has_mouse_region=False)
        tmp_widget.set_size((w + r, h * 2 + b + t), is_min=True)
        tmp_widget.update_images()
        cls._border_image = tmp_widget.get_image()
        tmp_widget.destroy()

    def __init__(self, parent, value_id, value_type, value_range, step, handler, width,
                 font=None, text_color=None, back_color=None, has_slider=False):

        if not self._border_image:
            self.__create_border_image()

        incr_btn_gfx_data = {
            "normal": (("panel_spin_up_button_normal",),),
            "hilited": (("panel_spin_up_button_hilited",),),
            "pressed": (("panel_spin_up_button_pressed",),)
        }
        decr_btn_gfx_data = {
            "normal": (("panel_spin_down_button_normal",),),
            "hilited": (("panel_spin_down_button_hilited",),),
            "pressed": (("panel_spin_down_button_pressed",),)
        }
        # field border image should not contain right border parts, so these are replaced with
        # central parts
        border_gfx_data = (
            ("panel_inset_border_topleft", "panel_inset_border_top", "panel_inset_border_top"),
            ("panel_inset_border_left", "panel_inset_border_center", "panel_inset_border_center"),
            ("panel_inset_border_bottomleft", "panel_inset_border_bottom", "panel_inset_border_bottom")
        )
        l, r, b, t = TextureAtlas["outer_borders"]["panel_inset"]
        borders = (l, 0, b, t)  # right field border offset must be zero

        if has_slider:
            field = PanelSliderField(parent, value_id, value_type, value_range, handler, width,
                                     font, text_color, back_color, borders, border_gfx_data)
        else:
            field = PanelInputField(parent, value_id, value_type, handler, width, font,
                                    text_color, back_color, borders, border_gfx_data)

        incr_btn = PanelSpinnerButton(parent, incr_btn_gfx_data)
        decr_btn = PanelSpinnerButton(parent, decr_btn_gfx_data)
        borders = (0, r, b, t)  # left spinner border offset must be zero
        SpinnerInputField.__init__(self, parent, value_range, step, field, incr_btn, decr_btn, borders)

    def get_border_image(self):

        return self._border_image


class ComboBoxInputField(InputField):

    _border_gfx_data = (("panel_combobox_normal_left", "panel_combobox_normal_center",
                         "panel_combobox_normal_right"),)
    _field_borders = ()
    _img_offset = (0, 0)
    _height = 0

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["panel_combobox_field"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)
        cls._height = Skin["options"]["combobox_field_height"]

    def __init__(self, parent, value_id, value_type, handler, width,
                 font=None, text_color=None, back_color=None):

        if not self._field_borders:
            self.__set_field_borders()

        InputField.__init__(self, parent, value_id, value_type, handler, width,
                            self._border_gfx_data, self._img_offset, font,
                            text_color, back_color)

        self.widget_type = "panel_combo_field"
        self.delay_card_update()

        panel_stack = self.get_ancestor("panel_stack")

        if panel_stack:
            scissor_effect = panel_stack.get_scissor_effect()
            self.set_scissor_effect(scissor_effect)

    @property
    def outer_borders(self):

        return self._field_borders

    def get_image(self, state=None, composed=True, draw_border=False, crop=True):

        return InputField.get_image(self, state, composed, draw_border=draw_border, crop=crop)

    def accept_input(self, text_handler=None):

        InputField.accept_input(self, text_handler=self.parent.set_text)

    def set_value(self, value, text_handler=None, handle_value=False):

        InputField.set_value(self, value, text_handler=self.parent.set_text,
                             handle_value=handle_value)

    def set_text(self, text, text_handler=None):

        InputField.set_text(self, text, text_handler=self.parent.set_text)


class PanelComboBox(ComboBox):

    _gfx = {
        "normal": (("panel_combobox_normal_left", "panel_combobox_normal_center",
                    "panel_combobox_normal_right"),),
        "pressed": (("panel_combobox_pressed_left", "panel_combobox_pressed_center",
                     "panel_combobox_pressed_right"),),
        "hilited": (("panel_combobox_hilited_left", "panel_combobox_hilited_center",
                     "panel_combobox_hilited_right"),),
        "active": (("panel_combobox_pressed_left", "panel_combobox_pressed_center",
                    "panel_combobox_pressed_right"),),
        "disabled": (("panel_combobox_disabled_left", "panel_combobox_disabled_center",
                    "panel_combobox_disabled_right"),)
    }
    _box_borders = ()
    _field_offset = (0, 0)
    _field_label_offset = (0, 0)
    _menu_offsets = {"top": (0, 0), "bottom": (0, 0)}

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["inner_borders"]["panel_combobox"]
        cls._box_borders = (l, r, b, t)
        cls._field_offset = (l, t)
        x, y, w, h = TextureAtlas["regions"]["panel_combobox_normal_left"]
        cls._menu_offsets["top"] = (l, t)
        cls._menu_offsets["bottom"] = (l, h - b)
        l, r, b, t = TextureAtlas["inner_borders"]["panel_combobox_field"]
        cls._field_label_offset = (l, t)

    def __init__(self, parent, field_width, text="", icon_id="", tooltip_text="",
                 editable=False, value_id="", value_type="string", handler=None):

        if not self._box_borders:
            self.__set_borders()

        ComboBox.__init__(self, parent, field_width, self._gfx, text, icon_id,
                          tooltip_text, editable)

        self.widget_type = "panel_combobox"
        self.delay_card_update()

        x, y, w, h = TextureAtlas["regions"]["panel_combobox_field_back"]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        img = PNMImage(field_width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)

        if editable:
            input_field = ComboBoxInputField(self, value_id, value_type,
                                             handler, field_width)
            self.set_input_field(input_field)

    @property
    def inner_borders(self):

        return self._box_borders

    def get_field_offset(self):

        return self._field_offset

    def get_field_label_offset(self):

        return self._field_label_offset

    def get_icon_offset(self):

        return (0, 0)

    def get_menu_offset(self, edge="bottom"):

        return self._menu_offsets[edge]

    def set_size(self, size, includes_borders=True, is_min=False):

        width, height = ComboBox.set_size(self, size, includes_borders, is_min)

        l, r, b, t = self.inner_borders
        width -= l + r
        x, y, w, h = TextureAtlas["regions"]["panel_combobox_field_back"]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        img = PNMImage(width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)


__all__ = ("PanelText", "PanelButton", "PanelCheckButton", "PanelRadioButtonGroup",
           "PanelColorBox", "PanelInputField", "PanelSliderField", "PanelSpinnerField",
           "PanelComboBox")
