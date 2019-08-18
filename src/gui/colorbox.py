from .base import *
from .dialog import *


class ColorBox(Widget):

    _box_size = (0, 0)
    _disabled_img = None
    _multi_img = None

    @classmethod
    def init(cls):

        x, y, w, h = TextureAtlas["regions"]["color_disabled"]
        cls._disabled_img = img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        x, y, w, h = TextureAtlas["regions"]["color_multi"]
        cls._multi_img = img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)

        options = Skin["options"]
        cls._box_size = (options["colorbox_width"], options["colorbox_height"])

    def __init__(self, parent, command=None, color=None, dialog_title=""):

        Widget.__init__(self, "colorbox", parent, gfx_data={})

        self.set_size(self._box_size, is_min=True)

        self._command = command if command else lambda color: None
        self._color = color
        self._color_type = "single"
        self._is_clicked = False
        self._dialog_title = dialog_title if dialog_title else "Pick color"
        self._delay_card_update = False

    def destroy(self):

        Widget.destroy(self)

        self._command = lambda color: None

    def delay_card_update(self, delay=True):

        self._delay_card_update = delay

    def is_card_update_delayed(self):

        return self._delay_card_update

    def __card_update_task(self):

        if self.is_hidden():
            return

        image = self.get_image(composed=False)

        if image:
            w, h = image.size
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

    def update_images(self, recurse=True, size=None): pass

    def get_image(self, state=None, composed=True):

        w, h = self._box_size
        image = PNMImage(w, h, 4)
        color_type = self._color_type

        if not color_type:
            image.copy_sub_image(self._disabled_img, 0, 0, 0, 0)
        elif color_type == "multi":
            image.copy_sub_image(self._multi_img, 0, 0, 0, 0)
        elif color_type == "single":
            color = self._color if self._color else (1., 1., 1.)
            r, g, b = color
            image.fill(r, g, b)
            image.alpha_fill(1.)

        border_img = self.get_border_image()
        w, h = border_img.size
        img = PNMImage(w, h, 4)
        img_offset_x, img_offset_y = self.get_image_offset()
        img.copy_sub_image(image, -img_offset_x, -img_offset_y, 0, 0)
        img.blend_sub_image(border_img, 0, 0, 0, 0)

        return img

    def on_leave(self):

        self._is_clicked = False

    def on_left_down(self):

        self._is_clicked = True

    def __set_color(self, color):

        if self._color != color or self._color_type == "multi":
            self._color = color
            self._color_type = "single"
            self._command(color)
            self.__update_card_image()

    def on_left_up(self):

        if self._is_clicked:
            color = self._color if self._color else (1., 1., 1.)
            ColorDialog(title=self._dialog_title, color=color, on_yes=self.__set_color)
            self._is_clicked = False

    def set_color_type(self, color_type="single"):

        if self._color_type != color_type:
            self._color_type = color_type
            self.__update_card_image()

    def set_color(self, color):

        if self._color != color:
            self._color = color
            self.__update_card_image()

    def get_color(self):

        return self._color
