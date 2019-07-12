from .base import *


class CheckButton(Widget):

    _checkmark = None
    _box_size = (0, 0)

    @classmethod
    def init(cls):

        x, y, w, h = TextureAtlas["regions"]["checkmark"]
        cls._checkmark = img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)

        options = Skin["options"]
        cls._box_size = (options["checkbox_width"], options["checkbox_height"])

    def __init__(self, parent, parent_type, command, mark_color, back_color,
                 text="", text_offset=5):

        Widget.__init__(self, parent_type + "_checkbutton", parent, gfx_data={})

        self._is_clicked = False
        self._is_checked = False
        self._command = command
        self._default_mark_color = self._mark_color = mark_color
        self._default_back_color = self._back_color = back_color
        self._delay_card_update = False
        self._text_offset = text_offset

        if text:
            widget_type = parent_type + "_checkbutton"
            skin_text = Skin["text"][widget_type]
            font = skin_text["font"]
            color = skin_text["color"]
            self._label = label = font.create_image(text, color)
            color = Skin["colors"]["disabled_{}_text".format(widget_type)]
            self._label_disabled = font.create_image(text, color)
            x, y, w, h = TextureAtlas["regions"][parent_type + "_checkbox"]
            l, _, b, t = self._btn_borders
            w += text_offset + label.get_x_size() - l
            h = max(h - b - t, label.get_y_size())
            self.set_size((w, h), is_min=True)
        else:
            self._label = self._label_disabled = None
            self.set_size(self._box_size, is_min=True)

        if not text:
            widget_type = parent_type + "_checkbox"
            l, r, b, t = TextureAtlas["outer_borders"][widget_type]
            btn_borders = (l, r, b, t)
            img_offset = (-l, -t)
        elif "\n" in text:
            l, _, b, t = TextureAtlas["outer_borders"][parent_type + "_checkbox"]
            font = Skin["text"][parent_type + "_checkbutton"]["font"]
            h_f = font.get_height() * (text.count("\n") + 1)
            h = Skin["options"]["checkbox_height"]
            dh = max(0, h_f - h) // 2
            b = max(0, b - dh)
            t = max(0, t - dh)
            btn_borders = (l, 0, b, t)
            img_offset = (-l, -t)
        else:
            btn_borders = self._btn_borders
            img_offset = self._img_offset

        self.set_outer_borders(btn_borders)
        self.set_image_offset(img_offset)

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
        parent = self.get_parent()

        if not (image and parent):
            return

        if self._label:

            x, y = self.get_pos()
            w, h = self.get_size()
            img_offset_x, img_offset_y = self.get_image_offset()
            w -= img_offset_x
            h -= img_offset_y
            y += img_offset_y
            img = PNMImage(w, h, 4)
            parent_img = parent.get_image(composed=False)

            if parent_img:
                img.copy_sub_image(parent_img, 0, 0, x, y, w, h)

            img.blend_sub_image(image, 0, 0, 0, 0)
            self.get_card().copy_sub_image(self, img, w, h, img_offset_x, img_offset_y)

        else:

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

    def create_overlay_image(self, border_image):

        w_b, h_b = border_image.get_x_size(), border_image.get_y_size()
        label = self._label
        w_l, h_l = label.get_x_size(), label.get_y_size()
        x_l = w_b + self._text_offset
        w = x_l + w_l
        h = max(h_b, h_l)
        y_l = (h - h_l) // 2
        y_b = (h - h_b) // 2
        img_offset_x, img_offset_y = self.get_box_image_offset()
        self._box_pos = (-img_offset_x, y_b - img_offset_y)
        self._label_pos = (x_l, y_l)
        self._overlay_img = img = PNMImage(w, h, 4)
        img.copy_sub_image(border_image, 0, y_b, 0, 0)

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

        if not self.is_enabled():
            label = self._label_disabled
        else:
            label = self._label

        if label:
            overlay_img = self._overlay_img
            w, h = overlay_img.get_x_size(), overlay_img.get_y_size()
            img = PNMImage(w, h, 4)
            img.copy_sub_image(image, *self._box_pos, 0, 0)
            img.blend_sub_image(overlay_img, 0, 0, 0, 0)
            img.copy_sub_image(label, *self._label_pos, 0, 0)
        else:
            border_img = self.get_border_image()
            w, h = border_img.get_x_size(), border_img.get_y_size()
            img = PNMImage(w, h, 4)
            img_offset_x, img_offset_y = self.get_image_offset()
            img.copy_sub_image(image, -img_offset_x, -img_offset_y, 0, 0)
            img.blend_sub_image(border_img, 0, 0, 0, 0)

        return img

    def get_label_pos(self):

        return self._label_pos

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
