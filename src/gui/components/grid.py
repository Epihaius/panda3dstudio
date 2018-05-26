from ..base import *
from ..button import *
from ..toolbar import *


class GridSpacingBox(Widget):

    _border_gfx_data = (("large_toolbar_inset_border_left", "large_toolbar_inset_border_center",
                         "large_toolbar_inset_border_right"),)
    _box_borders = ()
    _border_image = None
    _background_image = None
    _img_offset = (0, 0)
    _box_size = (0, 0)

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["large_toolbar_inset"]
        cls._box_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    @classmethod
    def __set_background_image(cls):

        tex_atlas = TextureAtlas["image"]
        tex_atlas_regions = TextureAtlas["regions"]
        x, y, w, h = tex_atlas_regions["gridspacing_background"]
        cls._background_image = image = PNMImage(w, h, 4)
        image.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
        cls._box_size = (w, h)

    def __init__(self, parent):

        if not self._box_borders:
            self.__set_borders()

        Widget.__init__(self, "gridspacing_box", parent, gfx_data={})

        if not self._border_image:
            self.__set_background_image()
            self.set_size(self._box_size, is_min=True)
            self.__create_border_image()

        skin_text = Skin["text"]["grid_spacing"]
        self._font = skin_text["font"]
        self._text_color = skin_text["color"]

        self.set_image_offset(self._img_offset)
        self.set_outer_borders(self._box_borders)
        self._grid_spacing = str(0.)
        self._grid_spacing_label = None

        Mgr.add_app_updater("gridspacing", self.__update_grid_spacing)

    def __create_border_image(self):

        w, h = self.get_size()
        l, r, b, t = self._box_borders
        width = w + l + r
        height = h + b + t
        gfx_data = {"": self._border_gfx_data}
        tmp_widget = Widget("tmp", self.get_parent(), gfx_data, stretch_dir="both", has_mouse_region=False)
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
            w, h = image.get_x_size(), image.get_y_size()
            img_offset_x, img_offset_y = self.get_image_offset()
            self.get_card().copy_sub_image(self, image, w, h, img_offset_x, img_offset_y)

    def update_images(self, recurse=True, size=None): pass

    def get_image(self, state=None, composed=True):

        image = PNMImage(self._background_image)
        bg_img = self._background_image
        label = self._grid_spacing_label

        if label:
            w, h = self._box_size
            w_l, h_l = label.get_x_size(), label.get_y_size()
            x = (w - w_l) // 2
            y = h - h_l
            image.blend_sub_image(label, x, y, 0, 0)

        border_img = self._border_image
        w, h = border_img.get_x_size(), border_img.get_y_size()
        img = PNMImage(w, h, 4)
        img_offset_x, img_offset_y = self.get_image_offset()
        img.copy_sub_image(image, -img_offset_x, -img_offset_y, 0, 0)
        img.blend_sub_image(border_img, 0, 0, 0, 0)

        return img

    def __update_grid_spacing(self, grid_spacing):

        if self._grid_spacing != grid_spacing:
            self._grid_spacing = grid_spacing
            self._grid_spacing_label = self._font.create_image(grid_spacing, self._text_color)
            self.__update_card_image()
            offset_x, offset_y = self.get_image_offset()
            self.get_parent().update_composed_image(self, None, offset_x, offset_y)


class GridPlaneButtons(ToggleButtonGroup):

    def __init__(self, toolbar):

        ToggleButtonGroup.__init__(self)

        btn_data = {
            "xz": ("icon_gridplane_xz", "Grid plane XZ"),
            "yz": ("icon_gridplane_yz", "Grid plane YZ")
        }

        def add_toggle(grid_plane):

            def toggle_on():

                Mgr.update_app("active_grid_plane", grid_plane)

            toggle = (toggle_on, lambda: None)

            if grid_plane == "xy":
                self.set_default_toggle(grid_plane, toggle)
            else:
                icon_id, tooltip_text = btn_data[grid_plane]
                btn = ToolbarButton(toolbar, icon_id=icon_id, tooltip_text=tooltip_text)
                self.add_button(btn, grid_plane, toggle)

        for grid_plane in ("xy", "xz", "yz"):
            add_toggle(grid_plane)

        def set_active_grid_plane(plane):

            if plane == "xy":
                self.deactivate()
            else:
                self.set_active_button(plane)

        Mgr.add_app_updater("active_grid_plane", set_active_grid_plane)


class GridToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "grid", "Grid")

        borders = (0, 5, 0, 0)

        self._grid_spacing_box = box = GridSpacingBox(self)
        self.add(box, borders=borders, alignment="center_v")

        self._plane_btns = btns = GridPlaneButtons(self)

        for grid_plane in ("xz", "yz"):
            btn = btns.get_button(grid_plane)
            self.add(btn, borders=borders, alignment="center_v")

        # TODO: add "Hide/Show Grid" button
