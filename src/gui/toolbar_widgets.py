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

        skin_text = Skin.text["toolbar"]
        Text.__init__(self, parent, skin_text["font"], skin_text["color"], text)

        self.widget_type = "toolbar_text"


class ToolbarSeparator(Widget):

    def __init__(self, parent):

        gfx_ids = {"": Skin.atlas.gfx_ids["separator"]["toolbar"]}

        Widget.__init__(self, "toolbar_separator", parent, gfx_ids, has_mouse_region=False)


class GridSpacingBox(Widget):

    _box_borders = ()
    _border_image = None
    _background_image = None
    _img_offset = (0, 0)
    _box_size = (0, 0)

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["large_toolbar_inset"]
        cls._box_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    @classmethod
    def __set_background_image(cls):

        tex_atlas = Skin.atlas.image
        tex_atlas_regions = Skin.atlas.regions
        gfx_id = Skin.atlas.gfx_ids["gridspacing_box"]["background"][0][0]
        x, y, w, h = tex_atlas_regions[gfx_id]
        cls._background_image = image = PNMImage(w, h, 4)
        image.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
        cls._box_size = (w, h)

    def __init__(self, parent):

        if not self._box_borders:
            self.__set_borders()

        Widget.__init__(self, "gridspacing_box", parent, gfx_ids={})

        if not self._border_image:
            self.__set_background_image()
            self.set_size(self._box_size, is_min=True)
            self.__create_border_image()
        else:
            self.set_size(self._box_size, is_min=True)

        skin_text = Skin.text["grid_spacing"]
        self._font = skin_text["font"]
        self._text_color = skin_text["color"]

        self.image_offset = self._img_offset
        self.outer_borders = self._box_borders
        self._grid_spacing = str(0.)
        self._grid_spacing_label = None

        Mgr.add_app_updater("gridspacing", self.__update_grid_spacing)

    def __create_border_image(self):

        w, h = self.get_size()
        l, r, b, t = self._box_borders
        width = w + l + r
        height = h + b + t
        gfx_ids = Skin.atlas.gfx_ids["gridspacing_box"]
        tmp_widget = Widget("tmp", self.parent, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def __update_card_image(self):

        if self.is_hidden():
            return

        image = self.get_image(composed=False)

        if image:
            w, h = image.size
            img_offset_x, img_offset_y = self.image_offset
            self.card.copy_sub_image(self, image, w, h, img_offset_x, img_offset_y)

    def update_images(self, recurse=True, size=None): pass

    def get_image(self, state=None, composed=True):

        image = PNMImage(self._background_image)
        bg_img = self._background_image
        label = self._grid_spacing_label

        if label:
            w, h = self._box_size
            w_l, h_l = label.size
            x = (w - w_l) // 2
            y = h - h_l
            image.blend_sub_image(label, x, y, 0, 0)

        border_img = self._border_image
        w, h = border_img.size
        img = PNMImage(w, h, 4)
        img_offset_x, img_offset_y = self.image_offset
        img.copy_sub_image(image, -img_offset_x, -img_offset_y, 0, 0)
        img.blend_sub_image(border_img, 0, 0, 0, 0)

        return img

    def __update_grid_spacing(self, grid_spacing):

        if self._grid_spacing != grid_spacing:
            self._grid_spacing = grid_spacing
            self._grid_spacing_label = self._font.create_image(grid_spacing, self._text_color)
            self.__update_card_image()
            offset_x, offset_y = self.image_offset
            self.parent.update_composed_image(self, None, offset_x, offset_y)


class ToolbarButton(Button):

    def __init__(self, parent, text="", icon_id="", tooltip_text=""):

        gfx_ids = Skin.atlas.gfx_ids["toolbar_button"]

        Button.__init__(self, parent, gfx_ids, text, icon_id, tooltip_text,
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

    def __init__(self, parent, toolbar_bundle, direction):

        gfx_ids = Skin.atlas.gfx_ids[f"toolbar_bundle_spin_{direction}_button"]

        Button.__init__(self, parent, gfx_ids)

        self.widget_type = "toolbar_button"
        self.command = lambda: toolbar_bundle.spin_toolbar_rows(-1 if direction == "up" else 1)

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

    _btn_borders = ()
    _img_offset = (0, 0)
    _box_img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, _, b, t = Skin.atlas.outer_borders["toolbar_checkbox"]
        cls._box_img_offset = (-l, -t)
        font = Skin.text["toolbar_checkbutton"]["font"]
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

        mark_color = Skin.colors["toolbar_checkmark"]
        back_color = Skin.colors["toolbar_checkbox_back"]

        CheckButton.__init__(self, parent, mark_color, back_color, text, text_offset)

        if not self._border_image:
            self.__create_border_image()

        self.create_base_image()

    def __create_border_image(self):

        gfx_id = Skin.atlas.gfx_ids["checkbox"]["toolbar"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        gfx_ids = {"": ((gfx_id,),)}
        tmp_widget = Widget("tmp", self.parent, gfx_ids, has_mouse_region=False)
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

    _box_borders = ()
    _img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["small_toolbar_inset"]
        cls._box_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent):

        if not self._box_borders:
            self.__set_borders()

        ColorBox.__init__(self, parent)

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
        gfx_ids = {"": Skin.atlas.gfx_ids["colorbox"]["toolbar"]}
        tmp_widget = Widget("tmp", self.parent, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def get_border_image(self):

        return self._border_image

    @property
    def color_type(self):

        return ColorBox.color_type.fget(self)

    @color_type.setter
    def color_type(self, color_type):

        ColorBox.color_type.fset(self, color_type)

        offset_x, offset_y = self.image_offset
        self.parent.update_composed_image(self, None, offset_x, offset_y)

    @property
    def color(self):

        return ColorBox.color.fget(self)

    @color.setter
    def color(self, color):

        ColorBox.color.fset(self, color)

        offset_x, offset_y = self.image_offset
        self.parent.update_composed_image(self, None, offset_x, offset_y)


class GfxMixin:

    _field_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["small_toolbar_inset"]
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

    def __init__(self, parent, width, font=None, text_color=None, back_color=None,
                 alt_field_borders=None, alt_border_gfx_ids=None):

        GfxMixin.__init__(self, alt_field_borders)
        field_gfx_ids = Skin.atlas.gfx_ids["field"]["toolbar"]
        gfx_ids = alt_border_gfx_ids if alt_border_gfx_ids else field_gfx_ids
        InputField.__init__(self, parent, width, gfx_ids, self._img_offset,
                            font, text_color, back_color)

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

    def __init__(self, parent, width, font=None, text_color=None, back_color=None,
                 alt_field_borders=None, alt_border_gfx_ids=None):

        GfxMixin.__init__(self, alt_field_borders)
        field_gfx_ids = Skin.atlas.gfx_ids["field"]["toolbar"]
        gfx_ids = alt_border_gfx_ids if alt_border_gfx_ids else field_gfx_ids
        SliderInputField.__init__(self, parent, width, gfx_ids, self._img_offset,
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
        gfx_ids = Skin.atlas.gfx_ids["field"]["toolbar"]
        MultiValInputField.__init__(self, parent, width, gfx_ids, self._img_offset,
                                    text_color, back_color)

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

    def __init__(self, parent, gfx_ids):

        SpinnerButton.__init__(self, parent, gfx_ids)

        self.widget_type = "toolbar_spinner_button"


class ToolbarSpinnerField(SpinnerInputField):

    _border_image = None
    _img_offset = (0, 0)

    @classmethod
    def __create_border_image(cls):

        gfx_id = Skin.atlas.gfx_ids["toolbar_spin_up_button"]["normal"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        l, r, b, t = Skin.atlas.outer_borders["small_toolbar_inset"]
        cls._img_offset = (l, t)
        gfx_ids = {"": Skin.atlas.gfx_ids["spinner"]["toolbar"]}
        tmp_widget = Widget("tmp", None, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((w + r, h * 2 + b + t), is_min=True)
        tmp_widget.update_images()
        cls._border_image = tmp_widget.get_image()
        tmp_widget.destroy()

    def __init__(self, parent, width, font=None, text_color=None, back_color=None,
                 has_slider=False):

        if not self._border_image:
            self.__create_border_image()

        gfx_ids = Skin.atlas.gfx_ids["spinner_field"]["toolbar"]
        l, r, b, t = Skin.atlas.outer_borders["small_toolbar_inset"]
        borders = (l, 0, b, t)  # right field border offset must be zero

        if has_slider:
            field = ToolbarSliderField(parent, width, font, text_color, back_color, borders, gfx_ids)
        else:
            field = ToolbarInputField(parent, width, font, text_color, back_color, borders, gfx_ids)

        incr_btn_gfx_ids = Skin.atlas.gfx_ids["toolbar_spin_up_button"]
        decr_btn_gfx_ids = Skin.atlas.gfx_ids["toolbar_spin_down_button"]
        incr_btn = ToolbarSpinnerButton(parent, incr_btn_gfx_ids)
        decr_btn = ToolbarSpinnerButton(parent, decr_btn_gfx_ids)
        borders = (0, r, b, t)  # left spinner border offset must be zero
        SpinnerInputField.__init__(self, parent, field, incr_btn, decr_btn, borders)

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

    _field_borders = ()
    _img_offset = (0, 0)
    _field_borders_icon = ()
    _img_offset_icon = (0, 0)
    _height = 0

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["toolbar_combobox_field"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)
        l, r, b, t = Skin.atlas.outer_borders["toolbar_combobox_field+icon"]
        cls._field_borders_icon = (l, r, b, t)
        cls._img_offset_icon = (-l, -t)
        cls._height = Skin.options["combobox_field_height"]

    def __init__(self, parent, value_id, value_type, handler, width,
                 font=None, text_color=None, back_color=None):

        if not self._field_borders:
            self.__set_field_borders()

        gfx_ids_no_icon = Skin.atlas.gfx_ids["combo_field"]["toolbar"]
        gfx_ids_icon = Skin.atlas.gfx_ids["combo_field"]["toolbar+icon"]
        gfx_ids = gfx_ids_icon if parent.has_icon() else gfx_ids_no_icon
        img_offset = self._img_offset_icon if parent.has_icon() else self._img_offset
        InputField.__init__(self, parent, width, gfx_ids, img_offset, font,
                            text_color, back_color)

        self.widget_type = "toolbar_combo_field"
        self.value_id = value_id
        self.value_type = value_type
        self.set_value_handler(handler)

    @property
    def outer_borders(self):

        return self._field_borders_icon if self.parent.has_icon() else self._field_borders

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

        l, r, b, t = Skin.atlas.inner_borders["toolbar_combobox"]
        cls._box_borders = (l, r, b, t)
        cls._field_offset = (l, t)
        gfx_id = Skin.atlas.gfx_ids["toolbar_combobox"]["normal"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        cls._menu_offsets["top"] = (l, t)
        cls._menu_offsets["bottom"] = (l, h - b)
        l, r, b, t = Skin.atlas.inner_borders["toolbar_combobox+icon"]
        cls._box_borders_icon = (l, r, b, t)
        cls._field_offset_icon = (l, t)
        gfx_id = Skin.atlas.gfx_ids["toolbar_combobox+icon"]["normal"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        cls._menu_offsets_icon["top"] = (l, t)
        cls._menu_offsets_icon["bottom"] = (l, h - b)
        l, r, b, t = Skin.atlas.inner_borders["toolbar_combobox_field"]
        cls._field_label_offset = (l, t)
        l, r, b, t = Skin.atlas.inner_borders["toolbar_combobox_icon_area"]
        cls._icon_offset = (l, t)

    def __init__(self, parent, field_width, text="", icon_id="", tooltip_text=""):

        if not self._box_borders:
            self.__set_borders()

        gfx_ids = Skin.atlas.gfx_ids["toolbar_combobox" + ("+icon" if icon_id else "")]

        ComboBox.__init__(self, parent, field_width, gfx_ids, text, icon_id, tooltip_text)

        self.widget_type = "toolbar_combobox"

        gfx_id = Skin.atlas.gfx_ids["combo_field_back"]["toolbar"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        img = PNMImage(field_width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)

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

    def set_input_field(self, value_id, value_type, handler):

        input_field = ComboBoxInputField(self, value_id, value_type, handler, self._field_width)
        self.input_field = input_field

        return input_field

    def show_input_field(self, show=True):

        if not ComboBox.show_input_field(self, show):
            return False

        self.parent.update_composed_image(self)

        return True

    def set_size(self, size, includes_borders=True, is_min=False):

        width, height = ComboBox.set_size(self, size, includes_borders, is_min)

        l, r, b, t = self.inner_borders
        width -= l + r
        gfx_id = Skin.atlas.gfx_ids["combo_field_back"]["toolbar"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        tmp_img = PNMImage(w, h, 4)
        tmp_img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        img = PNMImage(width, h, 4)
        img.unfiltered_stretch_from(tmp_img)
        self.set_field_back_image(img)
