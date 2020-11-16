from ..base import *
from ..text import Text
from ..button import Button
from ..combobox import ComboBox
from ..field import InputField, SliderInputField, SpinnerInputField, SpinnerButton
from ..checkbtn import CheckButton
from ..colorbox import ColorBox
from ..radiobtn import RadioButton, RadioButtonGroup
from ..group import WidgetGroup


class PanelWidgetGroup(WidgetGroup):

    def __init__(self, parent, title=""):

        title_bg_tex_id = Skin.atlas.gfx_ids["control_panel"][""][0][0]

        WidgetGroup.__init__(self, parent, title_bg_tex_id, "panel", title)


class PanelText(Text):

    def __init__(self, parent, text):

        skin_text = Skin.text["panel"]

        Text.__init__(self, parent, skin_text["font"], skin_text["color"], text)

        self.widget_type = "panel_text"


class PanelButton(Button):

    def __init__(self, parent, text="", icon_id="", tooltip_text=""):

        gfx_ids = Skin.atlas.gfx_ids["panel_button"]

        Button.__init__(self, parent, gfx_ids, text, icon_id, tooltip_text,
                        button_type="panel_button")

        self.widget_type = "panel_button"
        self.delay_card_update()


class PanelCheckButton(CheckButton):

    _btn_borders = ()
    _img_offset = (0, 0)
    _box_img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, _, b, t = Skin.atlas.outer_borders["panel_checkbox"]
        cls._box_img_offset = (-l, -t)
        font = Skin.text["panel_checkbutton"]["font"]
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

    def __init__(self, parent, text="", text_offset=0):

        if not self._btn_borders:
            self.__set_borders()

        mark_color = Skin.colors["panel_checkmark"]
        back_color = Skin.colors["panel_checkbox_back"]

        CheckButton.__init__(self, parent, mark_color, back_color, text, text_offset)

        self.delay_card_update()

        if not self._border_image:
            self.__create_border_image()

        self.create_base_image()

    def __create_border_image(self):

        gfx_id = Skin.atlas.gfx_ids["checkbox"]["panel"][0][0]
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


class PanelColorBox(ColorBox):

    _box_borders = ()
    _img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["panel_inset"]
        cls._box_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent):

        if not self._box_borders:
            self.__set_borders()

        ColorBox.__init__(self, parent)

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
        gfx_ids = Skin.atlas.gfx_ids["colorbox"]["panel"]
        tmp_widget = Widget("tmp", self.parent, {"": gfx_ids}, has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def get_border_image(self):

        return self._border_image


class PanelRadioButton(RadioButton):

    _btn_borders = ()
    _img_offset = (0, 0)
    _box_img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["panel_radiobox"]
        cls._box_img_offset = (-l, -t)
        font = Skin.text["panel_radiobutton"]["font"]
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

    def __create_border_image(self):

        gfx_ids = Skin.atlas.gfx_ids["radiobox"]["panel"]
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


class PanelRadioButtonGroup(RadioButtonGroup):

    def __init__(self, parent, prim_dir, prim_limit=0, gaps=(0, 0), expand=False,
                 text_offset=0):

        bullet_color = Skin.colors["panel_bullet"]
        back_color = Skin.colors["panel_radiobox_back"]

        RadioButtonGroup.__init__(self, bullet_color, back_color, prim_dir, prim_limit,
                                  gaps, expand, text_offset)

        self._parent = parent
        self.delay_card_update()

    def add_button(self, btn_id, text, index=None):

        btn = PanelRadioButton(self._parent, btn_id, text, self)
        RadioButtonGroup.add_button(self, btn_id, btn, index)

        return btn


class GfxMixin:

    _field_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["panel_inset"]
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

    def __init__(self, parent, width, font=None, text_color=None, back_color=None,
                 alt_field_borders=None, alt_border_gfx_ids=None):

        GfxMixin.__init__(self, alt_field_borders)
        field_gfx_ids = Skin.atlas.gfx_ids["field"]["panel"]
        gfx_ids = alt_border_gfx_ids if alt_border_gfx_ids else field_gfx_ids
        InputField.__init__(self, parent, width, gfx_ids, self._img_offset,
                            font, text_color, back_color)

        self.widget_type = "panel_input_field"
        self.delay_card_update()

        control_pane = self.get_ancestor("control_pane")

        if control_pane:
            scissor_effect = control_pane.scissor_effect
            self.set_scissor_effect(scissor_effect)


class PanelSliderField(GfxMixin, SliderInputField):

    def __init__(self, parent, width, font=None, text_color=None, back_color=None,
                 alt_field_borders=None, alt_border_gfx_ids=None):

        GfxMixin.__init__(self, alt_field_borders)
        field_gfx_ids = Skin.atlas.gfx_ids["field"]["panel"]
        gfx_ids = alt_border_gfx_ids if alt_border_gfx_ids else field_gfx_ids
        SliderInputField.__init__(self, parent, width, gfx_ids, self._img_offset,
                                  font, text_color, back_color)

        self.widget_type = "panel_input_field"
        self.delay_card_update()

        control_pane = self.get_ancestor("control_pane")

        if control_pane:
            scissor_effect = control_pane.scissor_effect
            self.set_scissor_effect(scissor_effect)


class PanelSpinnerButton(SpinnerButton):

    def __init__(self, parent, gfx_ids):

        SpinnerButton.__init__(self, parent, gfx_ids)

        self.widget_type = "panel_spinner_button"
        self.delay_card_update()


class PanelSpinnerField(SpinnerInputField):

    _border_image = None

    @classmethod
    def __create_border_image(cls):

        gfx_id = Skin.atlas.gfx_ids["panel_spin_up_button"]["normal"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        l, r, b, t = Skin.atlas.outer_borders["panel_inset"]
        gfx_ids = {"": Skin.atlas.gfx_ids["spinner"]["panel"]}
        tmp_widget = Widget("tmp", None, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((w + r, h * 2 + b + t), is_min=True)
        tmp_widget.update_images()
        cls._border_image = tmp_widget.get_image()
        tmp_widget.destroy()

    def __init__(self, parent, width, font=None, text_color=None, back_color=None,
                 has_slider=False):

        if not self._border_image:
            self.__create_border_image()

        gfx_ids = Skin.atlas.gfx_ids["spinner_field"]["panel"]
        l, r, b, t = Skin.atlas.outer_borders["panel_inset"]
        borders = (l, 0, b, t)  # right field border offset must be zero

        if has_slider:
            field = PanelSliderField(parent, width, font, text_color, back_color, borders, gfx_ids)
        else:
            field = PanelInputField(parent, width, font, text_color, back_color, borders, gfx_ids)

        incr_btn_gfx_ids = Skin.atlas.gfx_ids["panel_spin_up_button"]
        decr_btn_gfx_ids = Skin.atlas.gfx_ids["panel_spin_down_button"]
        incr_btn = PanelSpinnerButton(parent, incr_btn_gfx_ids)
        decr_btn = PanelSpinnerButton(parent, decr_btn_gfx_ids)
        borders = (0, r, b, t)  # left spinner border offset must be zero
        SpinnerInputField.__init__(self, parent, field, incr_btn, decr_btn, borders)

        self.widget_type = "panel_input_field"
        self.delay_card_update()

    def get_border_image(self):

        return self._border_image


class ComboBoxInputField(InputField):

    _field_borders = ()
    _img_offset = (0, 0)
    _height = 0

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["panel_combobox_field"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)
        cls._height = Skin.options["combobox_field_height"]

    def __init__(self, parent, value_id, value_type, handler, width,
                 font=None, text_color=None, back_color=None):

        if not self._field_borders:
            self.__set_field_borders()

        gfx_ids = Skin.atlas.gfx_ids["combo_field"]["panel"]

        InputField.__init__(self, parent, width, gfx_ids, self._img_offset, font,
                            text_color, back_color)

        self.widget_type = "panel_combo_field"
        self.delay_card_update()
        self.value_id = value_id
        self.value_type = value_type
        self.set_value_handler(handler)

        control_pane = self.get_ancestor("control_pane")

        if control_pane:
            scissor_effect = control_pane.scissor_effect
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

    _box_borders = ()
    _field_offset = (0, 0)
    _field_label_offset = (0, 0)
    _menu_offsets = {"top": (0, 0), "bottom": (0, 0)}

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.inner_borders["panel_combobox"]
        cls._box_borders = (l, r, b, t)
        cls._field_offset = (l, t)
        gfx_id = Skin.atlas.gfx_ids["panel_combobox"]["normal"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        cls._menu_offsets["top"] = (l, t)
        cls._menu_offsets["bottom"] = (l, h - b)
        l, r, b, t = Skin.atlas.inner_borders["panel_combobox_field"]
        cls._field_label_offset = (l, t)

    def __init__(self, parent, field_width, text="", icon_id="", tooltip_text=""):

        if not self._box_borders:
            self.__set_borders()

        gfx_ids = Skin.atlas.gfx_ids["panel_combobox"]

        ComboBox.__init__(self, parent, field_width, gfx_ids, text, icon_id, tooltip_text)

        self.widget_type = "panel_combobox"
        self.delay_card_update()

        gfx_id = Skin.atlas.gfx_ids["combo_field_back"]["panel"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        img = PNMImage(field_width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)

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
        gfx_id = Skin.atlas.gfx_ids["combo_field_back"]["panel"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        img = PNMImage(width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)

    def set_input_field(self, value_id, value_type, handler):

        input_field = ComboBoxInputField(self, value_id, value_type, handler, self._field_width)
        self.input_field = input_field

        return input_field


__all__ = ("PanelWidgetGroup", "PanelText", "PanelButton", "PanelCheckButton",
           "PanelRadioButtonGroup", "PanelColorBox", "PanelInputField",
           "PanelSliderField", "PanelSpinnerField", "PanelComboBox")
