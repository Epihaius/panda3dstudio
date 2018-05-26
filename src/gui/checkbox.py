from .base import *


class CheckBox(Widget):

    _default_mark_color = None
    _default_back_color = None
    _checkmark = None
    _box_size = (0, 0)

    @classmethod
    def init(cls):

        cls._default_mark_color = Skin["colors"]["checkmark"]
        cls._default_back_color = Skin["colors"]["checkbox"]

        x, y, w, h = TextureAtlas["regions"]["checkmark"]
        cls._checkmark = img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)

        options = Skin["options"]
        cls._box_size = (options["checkbox_width"], options["checkbox_height"])

    def __init__(self, parent, command, mark_color=None, back_color=None):

        Widget.__init__(self, "checkbox", parent, gfx_data={})

        self.set_size(self._box_size, is_min=True)

        self._is_clicked = False
        self._is_checked = False
        self._command = command
        self._mark_color = mark_color if mark_color else self._default_mark_color
        self._back_color = back_color if back_color else self._default_back_color
        self._delay_card_update = False

    def destroy(self):

        Widget.destroy(self)

        self._command = lambda: None

    def delay_card_update(self, delay=True):

        self._delay_card_update = delay

    def is_card_update_delayed(self):

        return self._delay_card_update

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

        if self._delay_card_update:
            task_id = "update_card_image"
            PendingTasks.add(task, task_id, sort=1, id_prefix=self.get_widget_id(),
                             batch_id="widget_card_update")
        else:
            task()

    def update_images(self, recurse=True, size=None):

        Widget.update_images(self, recurse, size)
        w, h = self._box_size
        image = PNMImage(w, h, 4)
        r, g, b, a = self._back_color
        image.fill(r, g, b)
        image.alpha_fill(a)
        self._images = {"": image}

        return self._images

    def get_image(self, state=None, composed=True):

        image = Widget.get_image(self, state, composed)

        if not image:
            return

        if self._is_checked:
            w, h = self._box_size
            checkmark = PNMImage(self._checkmark) * self._mark_color
            w_c, h_c = checkmark.get_x_size(), checkmark.get_y_size()
            x = (w - w_c) // 2
            y = (h - h_c) // 2
            image.blend_sub_image(checkmark, x, y, 0, 0)

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
            self._is_checked = not self._is_checked
            self._command(self._is_checked)
            self._is_clicked = False
            self.__update_card_image()

    def set_checkmark_color(self, color=None):

        checkmark_color = color if color else self._default_mark_color

        if self._mark_color != checkmark_color:
            self._mark_color = checkmark_color
            self.__update_card_image()

    def check(self, check=True):

        if self._is_checked != check:
            self._is_checked = check
            self.__update_card_image()

    def is_checked(self):

        return self._is_checked

    def enable(self, enable=True):

        if not Widget.enable(self, enable):
            return False

        self.__update_card_image()

        return True
