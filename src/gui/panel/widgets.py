from ..base import *
from ..text import Text
from ..button import Button
from ..combobox import ComboBox
from ..field import InputField
from ..checkbox import CheckBox
from ..colorbox import ColorBox
from ..radiobtn import RadioButton, RadioButtonGroup


class PanelText(Text):

    def __init__(self, parent, text):

        skin_text = Skin["text"]["panel"]
        Text.__init__(self, parent, skin_text["font"], skin_text["color"], text)

        self.set_widget_type("panel_text")


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

        self.set_widget_type("panel_button")
        self.delay_card_update()


class PanelCheckBox(CheckBox):

    _border_gfx_data = (("panel_checkbox",),)
    _box_borders = ()
    _img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["panel_checkbox"]
        cls._box_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent, command):

        if not self._box_borders:
            self.__set_borders()

        mark_color = Skin["colors"]["panel_checkmark"]
        back_color = Skin["colors"]["panel_checkbox"]

        CheckBox.__init__(self, parent, command, mark_color, back_color)

        self.set_widget_type("panel_checkbox")
        self.delay_card_update()

        if not self._border_image:
            self.__create_border_image()

        self.set_image_offset(self._img_offset)
        self.set_outer_borders(self._box_borders)

    def __create_border_image(self):

        w, h = self.get_size()
        l, r, b, t = self._box_borders
        width = w + l + r
        height = h + b + t
        gfx_data = {"": self._border_gfx_data}
        tmp_widget = Widget("tmp", self.get_parent(), gfx_data, stretch_dir="both", has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def get_border_image(self):

        return self._border_image


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

        self.set_widget_type("panel_colorbox")
        self.delay_card_update()

        if not self._border_image:
            self.__create_border_image()

        self.set_image_offset(self._img_offset)
        self.set_outer_borders(self._box_borders)

    def __create_border_image(self):

        w, h = self.get_size()
        l, r, b, t = self._box_borders
        width = w + l + r
        height = h + b + t
        gfx_data = {"": self._border_gfx_data}
        tmp_widget = Widget("tmp", self.get_parent(), gfx_data, stretch_dir="both", has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def get_border_image(self):

        return self._border_image


class PanelRadioButton(RadioButton):

    _border_gfx_data = (("panel_radiobutton",),)
    _btn_borders = ()
    _img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["panel_radiobutton"]
        cls._btn_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent, btn_id, group):

        if not self._btn_borders:
            self.__set_borders()

        RadioButton.__init__(self, parent, btn_id, group)

        self.set_widget_type("panel_radiobutton")

        if not self._border_image:
            self.__create_border_image()

        self.set_image_offset(self._img_offset)
        self.set_outer_borders(self._btn_borders)

    def __create_border_image(self):

        w, h = self.get_size()
        l, r, b, t = self._btn_borders
        width = w + l + r
        height = h + b + t
        gfx_data = {"": self._border_gfx_data}
        tmp_widget = Widget("tmp", self.get_parent(), gfx_data, stretch_dir="both", has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def get_border_image(self):

        return self._border_image


class PanelRadioButtonGroup(RadioButtonGroup):

    def __init__(self, parent, rows=0, columns=0, gap_h=0, gap_v=0):

        bullet_color = Skin["colors"]["panel_bullet"]
        back_color = Skin["colors"]["panel_radiobutton"]

        RadioButtonGroup.__init__(self, bullet_color, back_color, rows, columns, gap_h, gap_v)

        self._parent = parent
        self.delay_card_update()

    def add_button(self, btn_id, text):

        btn = PanelRadioButton(self._parent, btn_id, self)
        RadioButtonGroup.add_button(self, btn_id, btn, PanelText(self._parent, text))


class PanelInputField(InputField):

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

    def __init__(self, parent, width, text_color=None, back_color=None):

        if not self._field_borders:
            self.__set_field_borders()

        InputField.__init__(self, parent, self._border_gfx_data, width, text_color, back_color)

        self.set_widget_type("panel_input_field")
        self.delay_card_update()

        self.set_image_offset(self._img_offset)

        panel_stack = self.get_ancestor("panel_stack")

        if panel_stack:
            scissor_effect = panel_stack.get_scissor_effect()
            self.set_scissor_effect(scissor_effect)

        self._image_data = {}

    def get_outer_borders(self):

        return self._field_borders


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

    def __init__(self, parent, width, text_color=None, back_color=None):

        if not self._field_borders:
            self.__set_field_borders()

        InputField.__init__(self, parent, self._border_gfx_data, width, text_color, back_color)

        self.set_widget_type("panel_combo_field")
        self.delay_card_update()

        self.set_image_offset(self._img_offset)

        panel_stack = self.get_ancestor("panel_stack")

        if panel_stack:
            scissor_effect = panel_stack.get_scissor_effect()
            self.set_scissor_effect(scissor_effect)

    def get_outer_borders(self):

        return self._field_borders

    def get_image(self, state=None, composed=True, draw_border=False, crop=True):

        return InputField.get_image(self, state, composed, draw_border=draw_border, crop=crop)

    def accept_input(self, text_handler=None):

        InputField.accept_input(self, text_handler=self.get_parent().set_text)

    def set_value(self, value_id, value, text_handler=None, handle_value=True):

        InputField.set_value(self, value_id, value, text_handler=self.get_parent().set_text,
                             handle_value=handle_value)

    def set_text(self, value_id, text, text_handler=None):

        InputField.set_text(self, value_id, text, text_handler=self.get_parent().set_text)


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

    def __init__(self, parent, field_width, text="", icon_id="", tooltip_text="", editable=False):

        if not self._box_borders:
            self.__set_borders()

        ComboBox.__init__(self, parent, field_width, self._gfx, text, icon_id, tooltip_text,
                          editable)

        self.set_widget_type("panel_combobox")
        self.delay_card_update()

        x, y, w, h = TextureAtlas["regions"]["panel_combobox_field_back"]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        img = PNMImage(field_width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)

        if editable:
            input_field = ComboBoxInputField(self, field_width)
            self.set_input_field(input_field)

    def get_inner_borders(self):

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

        l, r, b, t = self.get_inner_borders()
        width -= l + r
        x, y, w, h = TextureAtlas["regions"]["panel_combobox_field_back"]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        img = PNMImage(width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)


__all__ = ("PanelText", "PanelButton", "PanelCheckBox", "PanelColorBox",
           "PanelRadioButtonGroup", "PanelInputField", "PanelComboBox")
