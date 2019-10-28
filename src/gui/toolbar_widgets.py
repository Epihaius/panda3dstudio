from .base import *
from .text import Text
from .button import Button
from .tooltip import ToolTip
from .field import (InputField, SliderInputField, MultiValInputField,
                    SpinnerInputField, SpinnerButton)
from .checkbtn import CheckButton
from .combobox import ComboBox
from .colorbox import ColorBox


class ToolbarText(Text):

    def __init__(self, parent, text):

        skin_text = Skin["text"]["toolbar"]
        Text.__init__(self, parent, skin_text["font"], skin_text["color"], text)

        self.widget_type = "toolbar_text"


class ToolbarSeparator(Widget):

    _gfx = {"": (("toolbar_separator",),)}

    def __init__(self, parent):

        Widget.__init__(self, "toolbar_separator", parent, self._gfx, has_mouse_region=False)


class ToolbarButton(Button):

    _gfx = {
        "normal": (("toolbar_button_normal_left", "toolbar_button_normal_center",
                     "toolbar_button_normal_right"),),
        "pressed": (("toolbar_button_pressed_left", "toolbar_button_pressed_center",
                     "toolbar_button_pressed_right"),),
        "hilited": (("toolbar_button_hilited_left", "toolbar_button_hilited_center",
                     "toolbar_button_hilited_right"),),
        "active": (("toolbar_button_active_left", "toolbar_button_active_center",
                    "toolbar_button_active_right"),),
        "disabled": (("toolbar_button_disabled_left", "toolbar_button_disabled_center",
                    "toolbar_button_disabled_right"),)
    }

    def __init__(self, parent, text="", icon_id="", tooltip_text="", command=None):

        Button.__init__(self, parent, self._gfx, text, icon_id, tooltip_text, command,
                        button_type="toolbar_button")

        self.widget_type = "toolbar_button"

    def set_active(self, active):

        if not Button.set_active(self, active):
            return False

        if not active:
            state = self.state
            self.state = "normal"

        self.parent.update_composed_image(self)

        if not active:
            self.state = state

        return True

    def enable(self, enable=True, check_group_disablers=True):

        if not Button.enable(self, enable, check_group_disablers):
            return False

        self.parent.update_composed_image(self)

        return True


class ToolbarSpinButton(Button):

    width = 0
    _gfx = {
        "up": {"normal": (("toolbar_spinner_up_normal",),),
               "hilited": (("toolbar_spinner_up_hilited",),),
               "pressed": (("toolbar_spinner_up_pressed",),)},
        "down": {"normal": (("toolbar_spinner_down_normal",),),
                 "hilited": (("toolbar_spinner_down_hilited",),),
                 "pressed": (("toolbar_spinner_down_pressed",),)}
    }

    def __init__(self, parent, toolbar_bundle, direction):

        command = lambda: toolbar_bundle.spin_toolbar_rows(-1 if direction == "up" else 1)
        Button.__init__(self, parent, self._gfx[direction], command=command)

        self.widget_type = "toolbar_button"

        self._toolbar_bundle = toolbar_bundle
        self._direction = direction
        self._is_spinning = False
        self._mouse_start_y = 0
        self._spin_amount = 0
        self._listener = DirectObject()

        if not self.width:
            ToolbarSpinButton.width = self.min_size[0]

        self.always_enabled = True

    def destroy(self):

        Button.destroy(self)

        self._toolbar_bundle = None
        self._listener.ignore_all()
        self._listener = None

    def __spin_toolbar_rows(self, task):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        spin_amount = int(mouse_pointer.y - self._mouse_start_y) // 10

        if self._spin_amount != spin_amount:
            self._toolbar_bundle.spin_images(spin_amount)
            self._spin_amount = spin_amount

        return task.cont

    def on_enter(self):

        if not self._is_spinning:
            Button.on_enter(self)
            toolbar_row = self._toolbar_bundle[0 if self._direction == "up" else -2]
            ToolTip.show(toolbar_row.get_tooltip_label())

    def on_leave(self):

        ToolTip.hide()

        if self.is_pressed() and not self._is_spinning:
            mouse_pointer = Mgr.get("mouse_pointer", 0)
            self._mouse_start_y = mouse_pointer.y
            Mgr.add_task(self.__spin_toolbar_rows, "spin_toolbar_rows")
            self.set_pressed(False)
            self._listener.accept_once("gui_mouse1-up", self.on_left_up)
            self._is_spinning = True

        if not self._is_spinning:
            Button.on_leave(self, force=True)

    def on_left_up(self):

        if self._is_spinning:

            Mgr.remove_task("spin_toolbar_rows")
            self._toolbar_bundle.spin_toolbar_rows(self._spin_amount)
            self._mouse_start_y = 0
            self._spin_amount = 0
            self._is_spinning = False

            if self.mouse_watcher.get_over_region() == self.mouse_region:
                Button.on_enter(self)
                toolbar_row = self._toolbar_bundle[0 if self._direction == "up" else -2]
                ToolTip.show(toolbar_row.get_tooltip_label())
            else:
                Button.on_leave(self, force=True)

        else:

            Button.on_left_up(self)
            toolbar_row = self._toolbar_bundle[0 if self._direction == "up" else -2]
            ToolTip.set_label(toolbar_row.get_tooltip_label())

    def on_right_up(self):

        if not self._is_spinning:
            self._toolbar_bundle.show_menu()


class ToolbarCheckButton(CheckButton):

    _border_gfx_data = (("toolbar_checkbox",),)
    _btn_borders = ()
    _img_offset = (0, 0)
    _box_img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, _, b, t = TextureAtlas["outer_borders"]["toolbar_checkbox"]
        cls._box_img_offset = (-l, -t)
        font = Skin["text"]["toolbar_checkbutton"]["font"]
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

        mark_color = Skin["colors"]["toolbar_checkmark"]
        back_color = Skin["colors"]["toolbar_checkbox_back"]

        CheckButton.__init__(self, parent, "toolbar", command, mark_color,
                             back_color, text, text_offset)

        if not self._border_image:
            self.__create_border_image()

        self.create_base_image()

    def __create_border_image(self):

        x, y, w, h = TextureAtlas["regions"]["toolbar_checkbox"]
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

    def set_checkmark_color(self, color=None):

        CheckButton.set_checkmark_color(self, color)

        offset_x, offset_y = self.image_offset
        self.parent.update_composed_image(self, None, offset_x, offset_y)

    def check(self, check=True):

        CheckButton.check(self, check)

        offset_x, offset_y = self.image_offset
        self.parent.update_composed_image(self, None, offset_x, offset_y)

    def enable(self, enable=True):

        if not CheckButton.enable(self, enable):
            return False

        offset_x, offset_y = self.image_offset
        self.parent.update_composed_image(self, None, offset_x, offset_y)

        return True


class ToolbarColorBox(ColorBox):

    _border_gfx_data = (("small_toolbar_inset_border_left", "small_toolbar_inset_border_center",
                         "small_toolbar_inset_border_right"),)
    _box_borders = ()
    _img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["small_toolbar_inset"]
        cls._box_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent, command=None, color=None, dialog_title=""):

        if not self._box_borders:
            self.__set_borders()

        ColorBox.__init__(self, parent, command, color, dialog_title)

        self.widget_type = "toolbar_colorbox"

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

    def set_color_type(self, color_type="single"):

        ColorBox.set_color_type(self, color_type)

        offset_x, offset_y = self.image_offset
        self.parent.update_composed_image(self, None, offset_x, offset_y)

    def set_color(self, color):

        ColorBox.set_color(self, color)

        offset_x, offset_y = self.image_offset
        self.parent.update_composed_image(self, None, offset_x, offset_y)


class GfxMixin:

    _border_gfx_data = (("small_toolbar_inset_border_left", "small_toolbar_inset_border_center",
                         "small_toolbar_inset_border_right"),)
    _field_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["small_toolbar_inset"]
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


class ToolbarInputField(GfxMixin, InputField):

    def __init__(self, parent, value_id, value_type, handler, width,
                 font=None, text_color=None, back_color=None,
                 alt_field_borders=None, alt_border_gfx_data=None):

        GfxMixin.__init__(self, alt_field_borders)
        gfx_data = alt_border_gfx_data if alt_border_gfx_data else self._border_gfx_data
        InputField.__init__(self, parent, value_id, value_type, handler, width,
                            gfx_data, self._img_offset, font, text_color, back_color)

        self.widget_type = "toolbar_input_field"

    def accept_input(self, text_handler=None):

        if InputField.accept_input(self, text_handler):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False

    def set_value(self, value, text_handler=None, handle_value=False, state="done"):

        if InputField.set_value(self, value, text_handler, handle_value, state):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False

    def set_text(self, text, text_handler=None):

        if InputField.set_text(self, text, text_handler):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False

    def show_text(self, show=True):

        if InputField.show_text(self, show):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False

    def set_text_color(self, color=None):

        if InputField.set_text_color(self, color):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False

    def clear(self, forget=True):

        InputField.clear(self, forget)

        if self.parent.widget_type == "toolbar":
            image = self.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image)

    def enable(self, enable=True):

        if InputField.enable(self, enable):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False


class ToolbarSliderField(GfxMixin, SliderInputField):

    def __init__(self, parent, value_id, value_type, value_range, handler,
                 width, font=None, text_color=None, back_color=None,
                 alt_field_borders=None, alt_border_gfx_data=None):

        GfxMixin.__init__(self, alt_field_borders)
        gfx_data = alt_border_gfx_data if alt_border_gfx_data else self._border_gfx_data
        SliderInputField.__init__(self, parent, value_id, value_type, value_range,
                                  handler, width, gfx_data, self._img_offset,
                                  font, text_color, back_color)

        self.widget_type = "toolbar_input_field"

    def accept_input(self, text_handler=None):

        if SliderInputField.accept_input(self, text_handler):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False

    def set_value(self, value, text_handler=None, handle_value=False, state="done"):

        if SliderInputField.set_value(self, value, text_handler, handle_value, state):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False

    def set_text(self, text, text_handler=None):

        if SliderInputField.set_text(self, text, text_handler):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False

    def show_text(self, show=True):

        if SliderInputField.show_text(self, show):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False

    def set_text_color(self, color=None):

        if SliderInputField.set_text_color(self, color):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False

    def clear(self, forget=True):

        SliderInputField.clear(self, forget)

        if self.parent.widget_type == "toolbar":
            image = self.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image)

    def enable(self, enable=True):

        if SliderInputField.enable(self, enable):
            if self.parent.widget_type == "toolbar":
                image = self.get_image(composed=False, draw_border=True, crop=True)
                self.parent.update_composed_image(self, image)
            return True

        return False


class ToolbarMultiValField(GfxMixin, MultiValInputField):

    def __init__(self, parent, width, text_color=None, back_color=None):

        GfxMixin.__init__(self)
        MultiValInputField.__init__(self, parent, width, self._border_gfx_data,
                                    self._img_offset, text_color, back_color)

        self.widget_type = "toolbar_input_field"

    def accept_input(self, text_handler=None):

        if MultiValInputField.accept_input(self, text_handler):
            image = self.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image)

    def set_value(self, value_id, value, text_handler=None, handle_value=False, state="done"):

        if MultiValInputField.set_value(self, value_id, value, text_handler, handle_value, state):
            image = self.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image)

    def set_text(self, value_id, text, text_handler=None):

        if MultiValInputField.set_text(self, value_id, text, text_handler):
            image = self.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image)

    def show_text(self, show=True):

        if MultiValInputField.show_text(self, show):
            image = self.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image)

    def set_text_color(self, color=None):

        if MultiValInputField.set_text_color(self, color):
            image = self.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image)

    def clear(self, forget=True):

        MultiValInputField.clear(self, forget)

        image = self.get_image(composed=False, draw_border=True, crop=True)
        self.parent.update_composed_image(self, image)

    def show_value(self, value_id):

        MultiValInputField.show_value(self, value_id)

        image = self.get_image(composed=False, draw_border=True, crop=True)
        self.parent.update_composed_image(self, image)

    def enable(self, enable=True):

        if not MultiValInputField.enable(self, enable):
            return False

        image = self.get_image(composed=False, draw_border=True, crop=True)
        self.parent.update_composed_image(self, image)

        return True


class ToolbarSpinnerButton(SpinnerButton):

    def __init__(self, parent, gfx_data):

        SpinnerButton.__init__(self, parent, gfx_data)

        self.widget_type = "toolbar_spinner_button"


class ToolbarSpinnerField(SpinnerInputField):

    _border_image = None
    _img_offset = (0, 0)

    @classmethod
    def __create_border_image(cls):

        x, y, w, h = TextureAtlas["regions"]["toolbar_spin_up_button_normal"]
        l, r, b, t = TextureAtlas["outer_borders"]["small_toolbar_inset"]
        cls._img_offset = (l, t)
        # spinner border image should not contain left border parts, so these are replaced with
        # central parts
        border_gfx_data = (("small_toolbar_inset_border_center", "small_toolbar_inset_border_center",
                            "small_toolbar_inset_border_right"),)
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
            "normal": (("toolbar_spin_up_button_normal",),),
            "hilited": (("toolbar_spin_up_button_hilited",),),
            "pressed": (("toolbar_spin_up_button_pressed",),)
        }
        decr_btn_gfx_data = {
            "normal": (("toolbar_spin_down_button_normal",),),
            "hilited": (("toolbar_spin_down_button_hilited",),),
            "pressed": (("toolbar_spin_down_button_pressed",),)
        }
        # field border image should not contain right border parts, so these are replaced with
        # central parts
        border_gfx_data = (("small_toolbar_inset_border_left", "small_toolbar_inset_border_center",
                            "small_toolbar_inset_border_center"),)
        l, r, b, t = TextureAtlas["outer_borders"]["small_toolbar_inset"]
        borders = (l, 0, b, t)  # right field border offset must be zero

        if has_slider:
            field = ToolbarSliderField(parent, value_id, value_type, value_range, handler, width,
                                       font, text_color, back_color, borders, border_gfx_data)
        else:
            field = ToolbarInputField(parent, value_id, value_type, handler, width, font,
                                      text_color, back_color, borders, border_gfx_data)

        incr_btn = ToolbarSpinnerButton(parent, incr_btn_gfx_data)
        decr_btn = ToolbarSpinnerButton(parent, decr_btn_gfx_data)
        borders = (0, r, b, t)  # left spinner border offset must be zero
        SpinnerInputField.__init__(self, parent, value_range, step, field, incr_btn, decr_btn, borders)

    def get_border_image(self):

        return self._border_image

    def accept_input(self, text_handler=None):

        if self.field.accept_input(text_handler):
            image = self.field.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image, *self._img_offset)

    def set_value(self, value, text_handler=None, handle_value=False, state="done"):

        if self.field.set_value(value, text_handler, handle_value, state):
            image = self.field.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image, *self._img_offset)

    def set_text(self, text, text_handler=None):

        if self.field.set_text(text, text_handler):
            image = self.field.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image, *self._img_offset)

    def show_text(self, show=True):

        if self.field.show_text(show):
            image = self.field.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image, *self._img_offset)

    def set_text_color(self, color=None):

        if self.field.set_text_color(color):
            image = self.field.get_image(composed=False, draw_border=True, crop=True)
            self.parent.update_composed_image(self, image, *self._img_offset)

    def clear(self, forget=True):

        self.field.clear(forget)
        image = self.field.get_image(composed=False, draw_border=True, crop=True)
        self.parent.update_composed_image(self, image, *self._img_offset)

    def enable(self, enable=True):

        if not self.field.enable(enable):
            return False

        image = self.field.get_image(composed=False, draw_border=True, crop=True)
        self.parent.update_composed_image(self, image, *self._img_offset)

        return True


class ComboBoxInputField(InputField):

    _border_gfx_data = (("toolbar_combobox_normal_left", "toolbar_combobox_normal_center",
                         "toolbar_combobox_normal_right"),)
    _border_gfx_data2 = (("toolbar_combobox2_normal_left", "toolbar_combobox_normal_center",
                         "toolbar_combobox_normal_right"),)
    _field_borders = ()
    _img_offset = (0, 0)
    _field_borders2 = ()
    _img_offset2 = (0, 0)
    _height = 0

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["toolbar_combobox_field"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)
        l, r, b, t = TextureAtlas["outer_borders"]["toolbar_combobox2_field"]
        cls._field_borders2 = (l, r, b, t)
        cls._img_offset2 = (-l, -t)
        cls._height = Skin["options"]["combobox_field_height"]

    def __init__(self, parent, value_id, value_type, handler, width,
                 font=None, text_color=None, back_color=None):

        if not self._field_borders:
            self.__set_field_borders()

        gfx_data = self._border_gfx_data if parent.has_icon() else self._border_gfx_data2
        img_offset = self._img_offset if parent.has_icon() else self._img_offset2
        InputField.__init__(self, parent, value_id, value_type, handler, width, gfx_data,
                            img_offset, font, text_color, back_color)

        self.widget_type = "toolbar_combo_field"

    @property
    def outer_borders(self):

        return self._field_borders if self.parent.has_icon() else self._field_borders2

    def get_image(self, state=None, composed=True, draw_border=False, crop=True):

        return InputField.get_image(self, state, composed, draw_border=draw_border, crop=crop)

    def accept_input(self, text_handler=None):

        if InputField.accept_input(self, text_handler=self.parent.set_text):
            combobox = self.parent
            combobox.parent.update_composed_image(combobox)

    def set_value(self, value, text_handler=None, handle_value=False, state="done"):

        if InputField.set_value(self, value, text_handler=self.parent.set_text,
                handle_value=handle_value, state=state):
            combobox = self.parent
            combobox.parent.update_composed_image(combobox)

    def set_text(self, text, text_handler=None):

        if InputField.set_text(self, text, text_handler=self.parent.set_text):
            combobox = self.parent
            combobox.parent.update_composed_image(combobox)

    def show_text(self, show=True):

        if InputField.show_text(self, show):
            combobox = self.parent
            combobox.parent.update_composed_image(combobox)

    def set_text_color(self, color=None):

        if InputField.set_text_color(self, color):
            combobox = self.parent
            combobox.parent.update_composed_image(combobox)

    def clear(self, forget=True):

        InputField.clear(self, forget)

        combobox = self.parent
        combobox.parent.update_composed_image(combobox)

    def enable(self, enable=True):

        if not InputField.enable(self, enable):
            return False

        combobox = self.parent
        combobox.parent.update_composed_image(combobox)

        return True


class ToolbarComboBox(ComboBox):

    _gfx = {
        "normal": (("toolbar_combobox_normal_left", "toolbar_combobox_normal_center",
                    "toolbar_combobox_normal_right"),),
        "pressed": (("toolbar_combobox_pressed_left", "toolbar_combobox_pressed_center",
                     "toolbar_combobox_pressed_right"),),
        "hilited": (("toolbar_combobox_hilited_left", "toolbar_combobox_hilited_center",
                     "toolbar_combobox_hilited_right"),),
        "active": (("toolbar_combobox_pressed_left", "toolbar_combobox_pressed_center",
                    "toolbar_combobox_pressed_right"),),
        "disabled": (("toolbar_combobox_disabled_left", "toolbar_combobox_disabled_center",
                    "toolbar_combobox_disabled_right"),)
    }
    _gfx2 = {
        "normal": (("toolbar_combobox2_normal_left", "toolbar_combobox_normal_center",
                    "toolbar_combobox_normal_right"),),
        "pressed": (("toolbar_combobox2_pressed_left", "toolbar_combobox_pressed_center",
                     "toolbar_combobox_pressed_right"),),
        "hilited": (("toolbar_combobox2_hilited_left", "toolbar_combobox_hilited_center",
                     "toolbar_combobox_hilited_right"),),
        "active": (("toolbar_combobox2_pressed_left", "toolbar_combobox_pressed_center",
                    "toolbar_combobox_pressed_right"),),
        "disabled": (("toolbar_combobox2_disabled_left", "toolbar_combobox_disabled_center",
                    "toolbar_combobox_disabled_right"),)
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

        l, r, b, t = TextureAtlas["inner_borders"]["toolbar_combobox"]
        cls._box_borders = (l, r, b, t)
        cls._field_offset = (l, t)
        x, y, w, h = TextureAtlas["regions"]["toolbar_combobox_normal_left"]
        cls._menu_offsets["top"] = (l, t)
        cls._menu_offsets["bottom"] = (l, h - b)
        l, r, b, t = TextureAtlas["inner_borders"]["toolbar_combobox2"]
        cls._box_borders2 = (l, r, b, t)
        cls._field_offset2 = (l, t)
        x, y, w, h = TextureAtlas["regions"]["toolbar_combobox2_normal_left"]
        cls._menu_offsets2["top"] = (l, t)
        cls._menu_offsets2["bottom"] = (l, h - b)
        l, r, b, t = TextureAtlas["inner_borders"]["toolbar_combobox_field"]
        cls._field_label_offset = (l, t)
        l, r, b, t = TextureAtlas["inner_borders"]["toolbar_combobox_icon_area"]
        cls._icon_offset = (l, t)

    def __init__(self, parent, field_width, text="", icon_id="", tooltip_text="",
                 editable=False, value_id="", value_type="string", handler=None):

        if not self._box_borders:
            self.__set_borders()

        if icon_id:
            gfx_data = self._gfx
        else:
            gfx_data = self._gfx2

        ComboBox.__init__(self, parent, field_width, gfx_data, text, icon_id,
                          tooltip_text, editable)

        self.widget_type = "toolbar_combobox"

        x, y, w, h = TextureAtlas["regions"]["toolbar_combobox_field_back"]
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

    def set_field_tint(self, tint=None):

        if not ComboBox.set_field_tint(self, tint):
            return False

        self.parent.update_composed_image(self)

        return True

    def set_text(self, text):

        if not ComboBox.set_text(self, text):
            return False

        task = lambda: self.parent.update_composed_image(self)
        PendingTasks.add(task, "update_composed_toolbar_image", sort=1, id_prefix=id(self))

        return True

    def show_input_field(self, show=True):

        if not ComboBox.show_input_field(self, show):
            return False

        self.parent.update_composed_image(self)

        return True

    def set_size(self, size, includes_borders=True, is_min=False):

        width, height = ComboBox.set_size(self, size, includes_borders, is_min)

        l, r, b, t = self.inner_borders
        width -= l + r
        x, y, w, h = TextureAtlas["regions"]["toolbar_combobox_field_back"]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        img = PNMImage(width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)
