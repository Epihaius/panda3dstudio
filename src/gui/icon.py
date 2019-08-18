from .base import *


class Icon(Widget):

    def __init__(self, parent, icon_id):

        self.type = "widget"
        self.widget_type = "icon"
        self._parent = parent
        self._id = icon_id
        self.node = parent.node.attach_new_node("icon_widget")
        self._image_offset = (0, 0)

        self._image = img = self.__create_icon(icon_id)
        self._size = self._min_size = (w, h) = img.size
        self._sizer = None
        self._sizer_item = None
        self._stretch_dir = ""
        self.mouse_region = None
        self._is_hidden = False

    def __create_icon(self, icon_id):

        x, y, w, h = TextureAtlas["regions"][icon_id]
        image = PNMImage(w, h, 4)
        image.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)

        return image

    def destroy(self):

        if self.node:
            self.node.remove_node()
            self.node = None

        self._parent = None
        self._sizer_item = None

    def set_icon(self, icon_id):

        if not icon_id or self._id == icon_id:
            return False

        self._image = img = self.__create_icon(icon_id)
        self._size = (w, h) = img.size

        self._id = icon_id

        return True

    def set_size(self, size, includes_borders=True, is_min=False):

        self._size = size

        if is_min:
            self._min_size = size

        return size

    def get_outer_borders(self):

        return (0, 0, 0, 0)

    def update_images(self, recurse=True, size=None): pass

    def get_image(self, state=None, composed=True):

        return PNMImage(self._image)

    def enable(self, enable=True): pass


class LayeredIcon(Widget):

    def __init__(self, parent, icon_ids):

        self.type = "widget"
        self.widget_type = "layered_icon"
        self._parent = parent
        self._ids = icon_ids
        self._icons_shown = [icon_ids[0]]
        self.node = parent.node.attach_new_node("layered_icon_widget")
        self._image_offset = (0, 0)

        self._icon_images = images = {}

        for icon_id in icon_ids:
            img = self.__create_icon(icon_id)
            images[icon_id] = img

        self._image = img = images[icon_ids[0]]
        self._size = self._min_size = (w, h) = img.size
        self._sizer = None
        self._sizer_item = None
        self._stretch_dir = ""
        self.mouse_region = None
        self._is_hidden = False

    def __create_icon(self, icon_id):

        x, y, w, h = TextureAtlas["regions"][icon_id]
        image = PNMImage(w, h, 4)
        image.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)

        return image

    def destroy(self):

        if self.node:
            self.node.remove_node()
            self.node = None

        self._parent = None
        self._sizer_item = None

    def update(self):

        w, h = self._size
        self._image = img = PNMImage(w, h, 4)
        images = self._icon_images
        icons_shown = self._icons_shown

        for i_id in self._ids:
            if i_id in icons_shown:
                img.blend_sub_image(images[i_id], 0, 0, 0, 0)

    def show_icon(self, icon_id, show=True, update=False):

        if icon_id not in self._ids:
            return False

        if show:
            if icon_id in self._icons_shown:
                return False
        elif icon_id not in self._icons_shown:
                return False

        icons_shown = self._icons_shown
        icons_shown.append(icon_id) if show else icons_shown.remove(icon_id)

        if update:
            self.update()

        return True

    def set_size(self, size, includes_borders=True, is_min=False):

        self._size = size

        if is_min:
            self._min_size = size

        return size

    def get_outer_borders(self):

        return (0, 0, 0, 0)

    def update_images(self, recurse=True, size=None): pass

    def get_image(self, state=None, composed=True):

        return PNMImage(self._image)

    def enable(self, enable=True): pass
