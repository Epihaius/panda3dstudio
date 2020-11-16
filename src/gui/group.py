from .base import *


class WidgetGroup(Widget):

    def __init__(self, parent, title_bg_tex_id, text_id, title=""):

        gfx_ids = Skin.atlas.gfx_ids["widget_group"]

        Widget.__init__(self, "group", parent, gfx_ids, has_mouse_region=False)

        self._title_bg_tex_id = title_bg_tex_id
        self._text_id = text_id
        tex_atlas_regions = Skin.atlas.regions
        x, y, w, h = tex_atlas_regions[title_bg_tex_id]
        img = PNMImage(w, h, 4)
        img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        skin_text = Skin.text[text_id]
        font = skin_text["font"]
        color = skin_text["color"]
        offset = Skin.options["group_title_offset"]
        label_img = font.create_image(title, color)
        w, h = label_img.size
        scaled_img = PNMImage(w + offset * 2, h, 4)
        scaled_img.unfiltered_stretch_from(img)
        scaled_img.blend_sub_image(label_img, offset, 0, 0, 0)
        self._label = scaled_img
        self._title = title

        sizer = Sizer("vertical")
        sizer.set_column_proportion(0, 1.)
        sizer.set_row_proportion(0, 1.)
        self.sizer = sizer
        w_l = tex_atlas_regions[gfx_ids[""][0][0]][2]
        w_r = tex_atlas_regions[gfx_ids[""][0][2]][2]
        sizer.default_size = (int(round((w_l + w_r) * 1.5)) + w + offset * 2, 1)
        self._client_sizer = client_sizer = Sizer("vertical")
        client_sizer.set_column_proportion(0, 1.)
        l, r, b, t = Skin.atlas.inner_borders["widget_group"]
        borders = (l, r, b, t + h)
        sizer.add(client_sizer, borders=borders)

    @property
    def client_sizer(self):

        return self._client_sizer

    def set_title(self, title):

        tex_atlas_regions = Skin.atlas.regions
        gfx_ids = Skin.atlas.gfx_ids["widget_group"]
        x, y, w, h = tex_atlas_regions[self._title_bg_tex_id]
        img = PNMImage(w, h, 4)
        img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        skin_text = Skin.text[self._text_id]
        font = skin_text["font"]
        color = skin_text["color"]
        offset = Skin.options["group_title_offset"]
        label_img = font.create_image(title, color)
        w, h = label_img.size
        scaled_img = PNMImage(w + offset * 2, h, 4)
        scaled_img.unfiltered_stretch_from(img)
        scaled_img.blend_sub_image(label_img, offset, 0, 0, 0)
        self._label = scaled_img
        self._title = title
        w_l = tex_atlas_regions[gfx_ids[""][0][0]][2]
        w_r = tex_atlas_regions[gfx_ids[""][0][2]][2]
        self.sizer.default_size = (int(round((w_l + w_r) * 1.5)) + w + offset * 2, 1)

    def update_images(self, recurse=True, size=None):

        width, height = self.get_size() if size is None else size

        if not (width and height):
            return

        tex_atlas = Skin.atlas.image
        tex_atlas_regions = Skin.atlas.regions
        gfx_ids = Skin.atlas.gfx_ids["widget_group"]
        images = self._images
        l, r, b, t = self.gfx_inner_borders
        borders_h = l + r
        borders_v = b + t
        h_half = self._label.size[1] // 2
        height2 = height - h_half

        for state, part_rows in gfx_ids.items():

            img = PNMImage(width, height, 4)
            images[state] = img
            y_offset = h_half
            i_middle = len(part_rows) // 2

            for i, part_row in enumerate(part_rows):

                j_middle = len(part_row) // 2
                x_offset = 0

                for j, part_id in enumerate(part_row):

                    x, y, w, h = tex_atlas_regions[part_id]

                    if i == i_middle and j == j_middle:
                        scaled_w = width - borders_h
                        scaled_h = height2 - borders_v
                        center_img = PNMImage(w, h, 4)
                        center_img.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
                        scaled_img = PNMImage(scaled_w, scaled_h, 4)
                        scaled_img.unfiltered_stretch_from(center_img)
                        img.copy_sub_image(scaled_img, x_offset, y_offset, 0, 0, scaled_w, scaled_h)
                        w = scaled_w
                        h = scaled_h
                    elif j == j_middle:
                        scaled_w = width - borders_h
                        center_img = PNMImage(w, h, 4)
                        center_img.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
                        scaled_img = PNMImage(scaled_w, h, 4)
                        scaled_img.unfiltered_stretch_from(center_img)
                        img.copy_sub_image(scaled_img, x_offset, y_offset, 0, 0, scaled_w, h)
                        w = scaled_w
                    elif i == i_middle:
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
            x = int(round(self.gfx_inner_borders[0] * 1.5))
            image.blend_sub_image(self._label, x, 0, 0, 0, *self._label.size)
        else:
            parent_img = self.parent.get_image(composed=False)
            if parent_img:
                image = PNMImage(*image.size, 4)
                x, y = self.get_pos()
                image.copy_sub_image(parent_img, -x, -y, 0, 0)

        return image
