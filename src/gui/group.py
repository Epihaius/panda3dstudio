from .base import *


class WidgetGroup(Widget):

    _gfx = {
        "": (
            ("widget_group_topleft", "widget_group_top", "widget_group_topright"),
            ("widget_group_left", "widget_group_center", "widget_group_right"),
            ("widget_group_bottomleft", "widget_group_bottom", "widget_group_bottomright")
        )
    }

    def __init__(self, parent, label_bg_tex_id, text_id, label=""):

        Widget.__init__(self, "group", parent, self._gfx, stretch_dir="both", has_mouse_region=False)

        x, y, w, h = TextureAtlas["regions"][label_bg_tex_id]
        img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        skin_text = Skin["text"][text_id]
        font = skin_text["font"]
        color = skin_text["color"]
        label_img = font.create_image(label, color)
        w = label_img.get_x_size() + 8
        h = label_img.get_y_size()
        scaled_img = PNMImage(w, h, 4)
        scaled_img.unfiltered_stretch_from(img)
        scaled_img.blend_sub_image(label_img, 4, 0, 0, 0)
        self._label = scaled_img

        sizer = Sizer("vertical")
        self.set_sizer(sizer)
        self._client_sizer = client_sizer = Sizer("vertical")
        l, r, b, t = TextureAtlas["inner_borders"]["widget_group"]
        borders = (l, r, b, t + h)
        sizer.add(client_sizer, proportion=1., expand=True, borders=borders)

    def add(self, *args, **kwargs):

        self._client_sizer.add(*args, **kwargs)

    def add_group(self, group, add_top_border=True):

        if add_top_border:
            l, r, b, t = TextureAtlas["inner_borders"]["widget_group"]
            borders = (0, 0, 0, t)
            self._client_sizer.add(group, expand=True, borders=borders)
        else:
            self._client_sizer.add(group, expand=True)

    def update_images(self, recurse=True, size=None):

        width, height = self.get_size() if size is None else size

        if not (width and height):
            return

        tex_atlas = TextureAtlas["image"]
        tex_atlas_regions = TextureAtlas["regions"]
        images = self._images
        l, r, b, t = self.get_gfx_inner_borders()
        borders_h = l + r
        borders_v = b + t
        h_half = self._label.get_y_size() // 2
        height2 = height - h_half

        for state, part_rows in self._gfx.items():

            img = PNMImage(width, height, 4)
            images[state] = img
            y_offset = h_half
            stretch_dir = self._stretch_dir
            i_middle = len(part_rows) // 2

            for i, part_row in enumerate(part_rows):

                j_middle = len(part_row) // 2
                x_offset = 0

                for j, part_id in enumerate(part_row):

                    x, y, w, h = tex_atlas_regions[part_id]

                    if stretch_dir == "both" and i == i_middle and j == j_middle:
                        scaled_w = width - borders_h
                        scaled_h = height2 - borders_v
                        center_img = PNMImage(w, h, 4)
                        center_img.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
                        scaled_img = PNMImage(scaled_w, scaled_h, 4)
                        scaled_img.unfiltered_stretch_from(center_img)
                        img.copy_sub_image(scaled_img, x_offset, y_offset, 0, 0, scaled_w, scaled_h)
                        w = scaled_w
                        h = scaled_h
                    elif stretch_dir in ("both", "horizontal") and j == j_middle:
                        scaled_w = width - borders_h
                        center_img = PNMImage(w, h, 4)
                        center_img.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
                        scaled_img = PNMImage(scaled_w, h, 4)
                        scaled_img.unfiltered_stretch_from(center_img)
                        img.copy_sub_image(scaled_img, x_offset, y_offset, 0, 0, scaled_w, h)
                        w = scaled_w
                    elif stretch_dir in ("both", "vertical") and i == i_middle:
                        scaled_h = height2 - borders_v
                        center_img = PNMImage(w, h, 4)
                        center_img.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
                        scaled_img = PNMImage(w, scaled_h, 4)
                        scaled_img.unfiltered_stretch_from(center_img)
                        img.copy_sub_image(scaled_img, x_offset, y_offset, 0, 0, w, scaled_h)
                        h = scaled_h
                    else:
                        img.copy_sub_image(tex_atlas, x_offset, y_offset, x, y, w, h)

                    x_offset += w

                y_offset += h

        if recurse:
            self._sizer.update_images()

        return images

    def get_image(self, state=None, composed=True):

        image = Widget.get_image(self, state, composed)

        if composed:
            w = self._label.get_x_size()
            h = self._label.get_y_size()
            x = self.get_gfx_inner_borders()[0] + 3
            image.blend_sub_image(self._label, x, 0, 0, 0, w, h)
        else:
            parent_img = self.get_parent().get_image(composed=False)
            if parent_img:
                w = image.get_x_size()
                h = image.get_y_size()
                image = PNMImage(w, h, 4)
                x, y = self.get_pos()
                image.copy_sub_image(parent_img, -x, -y, 0, 0)

        return image
