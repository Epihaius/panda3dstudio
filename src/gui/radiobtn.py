from .base import *
from .text import Text


class RadioButton(Widget):

    _bullet = None
    _btn_size = (0, 0)

    @classmethod
    def init(cls):

        x, y, w, h = TextureAtlas["regions"]["bullet"]
        cls._bullet = img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)

        options = Skin["options"]
        cls._btn_size = (options["radiobutton_width"], options["radiobutton_height"])

    def __init__(self, parent, btn_id, group):

        Widget.__init__(self, "radiobutton", parent, gfx_data={})

        self.set_size(self._btn_size, is_min=True)

        self._btn_id = btn_id
        self._group = group
        self._is_clicked = False
        self._is_selected = False
        self._command = lambda: None

    def destroy(self):

        if Widget.destroy(self):
            self._group.destroy()
            self._group = None
            self._command = lambda: None

    def __card_update_task(self):

        if self.is_hidden():
            return

        image = self.get_image(composed=False)

        if image:
            w, h = image.get_x_size(), image.get_y_size()
            img_offset_x, img_offset_y = self.get_image_offset()
            self.get_card().copy_sub_image(self, image, w, h, img_offset_x, img_offset_y)

    def __update_card_image(self):

        task = self.__card_update_task

        if self._group.is_card_update_delayed():
            task_id = "update_card_image"
            PendingTasks.add(task, task_id, sort=1, id_prefix=self.get_widget_id(),
                             batch_id="widget_card_update")
        else:
            task()

    def update_images(self, recurse=True, size=None):

        Widget.update_images(self, recurse, size)
        w, h = self._btn_size
        image = PNMImage(w, h, 4)
        r, g, b, a = self._group.get_back_color()
        image.fill(r, g, b)
        image.alpha_fill(a)
        self._images = {"": image}

        return self._images

    def update(self):

        self.update_images(recurse=False)
        self.__update_card_image()

    def get_image(self, state=None, composed=True):

        image = Widget.get_image(self, state, composed)

        if not image:
            return

        if self._is_selected:
            w, h = self._btn_size
            bullet = PNMImage(self._bullet) * self._group.get_bullet_color()
            w_b, h_b = bullet.get_x_size(), bullet.get_y_size()
            x = (w - w_b) // 2
            y = (h - h_b) // 2
            image.blend_sub_image(bullet, x, y, 0, 0)

        border_img = self.get_border_image()
        w, h = border_img.get_x_size(), border_img.get_y_size()
        img = PNMImage(w, h, 4)
        img_offset_x, img_offset_y = self.get_image_offset()
        img.copy_sub_image(image, -img_offset_x, -img_offset_y, 0, 0)
        img.blend_sub_image(border_img, 0, 0, 0, 0)

        return img

    def on_leave(self):

        self._is_clicked = False

    def on_left_down(self):

        self._is_clicked = True

    def on_left_up(self):

        if self._is_clicked:

            if not self._is_selected:
                self._group.set_selected_button(self._btn_id)
                self._command()
                self.__update_card_image()

            self._is_clicked = False

    def set_command(self, command):

        self._command = command

    def set_selected(self, is_selected=True):

        if self._is_selected == is_selected:
            return

        self._is_selected = is_selected
        self.__update_card_image()

    def enable(self, enable=True, check_group_disablers=True):

        if enable and not self.is_always_enabled() and check_group_disablers:
            for disabler in self._group.get_disablers().values():
                if disabler():
                    return False

        if not Widget.enable(self, enable):
            return False

        if not self.is_hidden():
            self.__update_card_image()


class RadioButtonGroup(object):

    def __init__(self, bullet_color, back_color, rows=0, columns=0, gap_h=0, gap_v=0, stretch=False):

        self._btns = {}
        self._selected_btn_id = None
        self._is_enabled = True
        self._disablers = {}
        self._default_bullet_color = self._bullet_color = bullet_color
        self._default_back_color = self._back_color = back_color
        self._text_borders = (5, 0, 0, 0)
        self._sizer = GridSizer(rows, columns, gap_h, gap_v)
        self._stretch = stretch
        self._delay_card_update = False

    def destroy(self):

        if not self._btns:
            return

        self._btns.clear()
        self._disablers.clear()

    def get_sizer(self):

        return self._sizer

    def delay_card_update(self, delay=True):

        self._delay_card_update = delay

    def is_card_update_delayed(self):

        return self._delay_card_update

    def add_button(self, btn_id, button, text):

        self._btns[btn_id] = button
        subsizer = Sizer("horizontal")
        subsizer.add(button, alignment="center_v")
        subsizer.add(text, alignment="center_v", borders=self._text_borders)
        proportion = 1. if self._stretch else 0.
        self._sizer.add(subsizer, alignment_v="center_v", proportion_h=proportion)

    def get_button_count(self):

        return len(self._btns)

    def set_selected_button(self, btn_id=None):

        if self._selected_btn_id == btn_id:
            return

        if self._selected_btn_id is not None:
            self._btns[self._selected_btn_id].set_selected(False)

        self._selected_btn_id = btn_id

        if btn_id is not None:
            self._btns[btn_id].set_selected()

    def get_selected_button(self):

        return self._selected_btn_id

    def set_button_command(self, btn_id, command):

        self._btns[btn_id].set_command(command)

    def set_bullet_color(self, color=None, update=False):

        bullet_color = color if color else self._default_bullet_color

        if self._bullet_color != bullet_color:

            self._bullet_color = bullet_color

            if update:
                self._btns[self._selected_btn_id].update()

    def get_bullet_color(self):

        return self._bullet_color

    def set_back_color(self, color=None, update=False):

        back_color = color if color else self._default_back_color

        if self._back_color != back_color:

            self._back_color = back_color

            if update:
                for btn in self._btns.values():
                    btn.update()

    def get_back_color(self):

        return self._back_color

    def add_disabler(self, disabler_id, disabler):

        self._disablers[disabler_id] = disabler

    def remove_disabler(self, disabler_id):

        del self._disablers[disabler_id]

    def get_disablers(self):

        return self._disablers

    def enable(self, enable=True):

        if self._is_enabled == enable:
            return

        self._is_enabled = enable

        if enable:
            for disabler in self._disablers.values():
                if disabler():
                    return

        for btn in self._btns.values():
            btn.enable(enable)
