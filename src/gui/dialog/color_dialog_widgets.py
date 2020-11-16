from ..base import *
from ..menu import Menu


class ColorSwatchGroup(Widget):

    _group_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["dialog_inset2"]
        cls._group_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    def __init__(self, parent):

        Widget.__init__(self, "colorswatch_group", parent, gfx_ids={})

        if not self._group_borders:
            self.__set_borders()

        self.image_offset = self._img_offset
        self.outer_borders = self._group_borders
        self.mouse_region.sort = parent.sort + 1

        self._command = lambda *args, **kwargs: None

    def destroy(self):

        Widget.destroy(self)

        self.command = None

    @property
    def command(self):

        return self._command

    @command.setter
    def command(self, command):

        self._command = command if command else lambda *args, **kwargs: None

    def update_images(self, recurse=True, size=None):

        Widget.update_images(self, recurse, size)
        self._images = {"": self._swatches}

        return self._images

    def get_image(self, state=None, composed=True):

        image = Widget.get_image(self, state, composed)

        if not image:
            return

        border_img = self._border_image
        img = PNMImage(*border_img.size, 4)
        offset_x, offset_y = self.image_offset
        img.copy_sub_image(image, -offset_x, -offset_y, 0, 0)
        img.blend_sub_image(border_img, 0, 0, 0, 0)

        return img

    def on_enter(self):

        Mgr.set_cursor("eyedropper")

    def on_leave(self):

        if Mgr.get("active_input_field") and not Menu.is_menu_shown():
            Mgr.set_cursor("input_commit")
        else:
            Mgr.set_cursor("main")

    def on_left_down(self):

        w, h = self.get_size()
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = int(mouse_pointer.x)
        mouse_y = int(mouse_pointer.y)
        x, y = self.get_pos(from_root=True)
        x = max(0, min(mouse_x - x, w - 1))
        y = max(0, min(mouse_y - y, h - 1))
        r, g, b = self._swatches.get_xel(x, y)
        color = (r, g, b)
        self._command(color, continuous=False, update_fields=True, update_gradients=True)


class BasicColorGroup(ColorSwatchGroup):

    _swatches = None
    _border_image = None

    @classmethod
    def __create_swatches(cls):

        w = Skin.options["small_colorswatch_width"]
        h = Skin.options["small_colorswatch_height"]
        colors = (
                ((1., 0., 0.), (1., .5, 0.), (1., 1., 0.), (.5, 1., 0.), (0., 1., 0.), (0., 1., .5)),
                ((1., .5, .5), (1., .75, .5), (1., 1., .5), (.75, 1., .5), (.5, 1., .5), (.5, 1., .75)),
                ((.75, .25, .25), (.75, .5, .25), (.75, .75, .25), (.5, .75, .25), (.25, .75, .25), (.25, .75, .5)),
                ((.5, 0., 0.), (.5, .25, 0.), (.5, .5, 0.), (.25, .5, 0.), (0., .5, 0.), (0., .5, .25)),
                ((0., 1., 1.), (0., .5, 1.), (0., 0., 1.), (.5, 0., 1.), (1., 0., 1.), (1., 0., .5)),
                ((.5, 1., 1.), (.5, .75, 1.), (.5, .5, 1.), (.75, .5, 1.), (1., .5, 1.), (1., .5, .75)),
                ((.25, .75, .75), (.25, .5, .75), (.25, .25, .75), (.5, .25, .75), (.75, .25, .75), (.75, .25, .5)),
                ((0., .5, .5), (0., .25, .5), (0., 0., .5), (.25, 0., .5), (.5, 0., .5), (.5, 0., .25)),
                ((0., 0., 0.), (.2, .2, .2), (.4, .4, .4), (.5, .5, .5), (.8, .8, .8), (1., 1., 1.))
        )
        column_count = len(colors[0])
        row_count = len(colors)
        cls._swatches = img = PNMImage(w * column_count, h * row_count, 4)
        img.alpha_fill(1.)
        swatch_img = PNMImage(w, h, 4)
        swatch_img.alpha_fill(1.)

        for i, row in enumerate(colors):

            y = i * h

            for j, color in enumerate(row):
                x = j * w
                swatch_img.fill(*color)
                img.copy_sub_image(swatch_img, x, y, 0, 0)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent):

        ColorSwatchGroup.__init__(self, parent)

        if not self._swatches:
            self.__create_swatches()
            self.__create_border_image()

        swatches = self._swatches
        w, h = swatches.size
        self.set_size((w, h), is_min=True)

    def __create_border_image(self):

        swatches = self._swatches
        w, h = swatches.size
        l, r, b, t = self._group_borders
        width = w + l + r
        height = h + b + t
        gfx_ids = Skin.atlas.gfx_ids["color_control"]
        tmp_widget = Widget("tmp", self.parent, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)


class CustomColorGroup(ColorSwatchGroup):

    _swatches = None
    _border_image = None

    @classmethod
    def __create_swatches(cls):

        w = Skin.options["small_colorswatch_width"]
        h = Skin.options["small_colorswatch_height"]
        colors = GD["config"]["custom_colors"]
        cls._swatches = img = PNMImage(w * 6, h * 5, 4)
        img.fill(1., 1., 1.)
        img.alpha_fill(1.)
        swatch_img = PNMImage(w, h, 4)
        swatch_img.alpha_fill(1.)

        for i, color in enumerate(colors):
            y = ((i % 30) // 6) * h
            x = (i % 6) * w
            swatch_img.fill(*color)
            img.copy_sub_image(swatch_img, x, y, 0, 0)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent):

        ColorSwatchGroup.__init__(self, parent)

        if not self._swatches:
            self.__create_swatches()
            self.__create_border_image()

        swatches = self._swatches
        w, h = swatches.size
        self.set_size((w, h), is_min=True)

    def __create_border_image(self):

        swatches = self._swatches
        w, h = swatches.size
        l, r, b, t = self._group_borders
        width = w + l + r
        height = h + b + t
        gfx_ids = Skin.atlas.gfx_ids["color_control"]
        tmp_widget = Widget("tmp", self.parent, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def add_swatch(self, color):

        config_data = GD["config"]
        colors = config_data["custom_colors"]

        if color in colors:
            return

        color_count = len(colors)
        colors.append(color)

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

        img = self._swatches
        w = Skin.options["small_colorswatch_width"]
        h = Skin.options["small_colorswatch_height"]
        swatch_img = PNMImage(w, h, 4)
        swatch_img.alpha_fill(1.)
        y = ((color_count % 30) // 6) * h
        x = (color_count % 6) * w
        swatch_img.fill(*color)
        img.copy_sub_image(swatch_img, x, y, 0, 0)

        image = self.get_image(composed=False)

        if image:
            w, h = image.size
            x, y = self.image_offset
            self.card.copy_sub_image(self, image, w, h, x, y)


class HueSatControl(WidgetCard):

    _gradient_borders = ()
    _gradient = None
    _img_offset = (0, 0)
    _border_image = None
    _marker = None

    @classmethod
    def __create_gradient(cls):

        from math import sin, pi

        w = Skin.options["colorgradient_width"]
        h = Skin.options["colorgradient_height"]
        w_ = w - 1.
        h_ = h - 1.
        rng = w_ / 3.
        cls._gradient = img = PNMImage(w, h, 4)
        img.alpha_fill(1.)

        for x in range(w):

            for y in range(h):

                if 0. <= x < rng:
                    # between red and green
                    b = 0.
                    g = x / rng
                    r = 1. - g
                    factor = 1. + sin(g * pi)
                    r *= factor
                    g *= factor
                elif rng <= x < 2. * rng:
                    # between green and blue
                    r = 0.
                    b = (x - rng) / rng
                    g = 1. - b
                    factor = 1. + sin(b * pi)
                    g *= factor
                    b *= factor
                elif 2. * rng <= x < w:
                    # between blue and red
                    g = 0.
                    r = (x - 2. * rng) / rng
                    b = 1. - r
                    factor = 1. + sin(r * pi)
                    b *= factor
                    r *= factor

                img.set_xel(x, y, r, g, b)

        img_tmp = PNMImage(w, h, 4)
        img_tmp.fill(.5, .5, .5)

        for y in range(h):

            a = y / h_

            for x in range(w):
                img_tmp.set_alpha(x, y, a)

        img.blend_sub_image(img_tmp, 0, 0, 0, 0)

    @classmethod
    def __create_marker(cls):

        gfx_id = Skin.atlas.gfx_ids["color_control"]["marker"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        cls._marker = img = PNMImage(w, h, 4)
        img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["dialog_inset2"]
        cls._gradient_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent):

        WidgetCard.__init__(self, "hue_sat_control", parent)

        if not self._gradient:
            self.__create_gradient()
            self.__set_borders()
            self.__create_border_image()
            self.__create_marker()

        self.outer_borders = self._gradient_borders
        gradient = self._gradient
        w, h = gradient.size
        self.set_size((w, h), is_min=True)
        border_image = self._border_image
        w_b, h_b = border_image.size
        marker = self._marker
        w_m, h_m = marker.size
        offset_x, offset_y = self._img_offset

        # Create the texture stages

        # the first texture stage should show a hue-saturation gradient
        ts1 = TextureStage("hue_sat")
        # the second texture stage should show the marker
        self._ts2 = ts2 = TextureStage("marker")
        ts2.sort = 1
        ts2.mode = TextureStage.M_decal
        # the third texture stage should show the border
        ts3 = TextureStage("border")
        ts3.sort = 2
        ts3.mode = TextureStage.M_decal

        gradient_tex = Texture("hue_sat")
        image = PNMImage(w_b, h_b, 4)
        image.copy_sub_image(gradient, -offset_x, -offset_y, 0, 0)
        gradient_tex.load(image)
        marker_tex = Texture("marker")
        marker_tex.load(self._marker)
        marker_tex.wrap_u = SamplerState.WM_border_color
        marker_tex.wrap_v = SamplerState.WM_border_color
        marker_tex.border_color = (0., 0., 0., 0.)
        border_tex = Texture("border")
        border_tex.load(border_image)

        sort = parent.sort + 1

        quad = self.create_quad((offset_x, w_b + offset_x, -h_b - offset_y, -offset_y))
        quad.set_bin("dialog", sort)
        quad.set_texture(ts1, gradient_tex)
        quad.set_texture(ts2, marker_tex)
        quad.set_tex_scale(ts2, w_b / w_m, h_b / h_m)
        quad.set_texture(ts3, border_tex)

        self.mouse_region = mouse_region = MouseWatcherRegion("hue_sat_control", 0., 0., 0., 0.)
        mouse_region.sort = sort
        self.mouse_watcher.add_region(mouse_region)
        listener = self._listener = DirectObject()
        listener.accept("gui_region_enter", self.__on_enter)
        listener.accept("gui_region_leave", self.__on_leave)
        listener.accept("gui_mouse1", self.__on_left_down)

        self._picking_color = False
        self._marker_start_pos = (0., 0.)
        self._prev_mouse_pos = (0, 0)
        self._command = lambda *args, **kwargs: None

    def destroy(self):

        WidgetCard.destroy(self)

        self._listener.ignore_all()
        self._listener = None
        self.command = None

    @property
    def command(self):

        return self._command

    @command.setter
    def command(self, command):

        self._command = command if command else lambda *args, **kwargs: None
        r, g, b = self._gradient.get_xel(0, 0)
        color = (r, g, b)
        self._command(color, continuous=False, update_fields=True)

    def __create_border_image(self):

        gradient = self._gradient
        w, h = gradient.size
        l, r, b, t = self._gradient_borders
        width = w + l + r
        height = h + b + t
        gfx_ids = Skin.atlas.gfx_ids["color_control"]
        tmp_widget = Widget("tmp", self.parent, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def update_images(self, recurse=True, size=None): pass

    def update_mouse_region_frames(self, exclude="", recurse=True):

        w, h = self.get_size()
        x, y = self.get_pos(from_root=True)
        l = x
        r = x + w
        b = -y - h
        t = -y
        self.mouse_region.frame = (l, r, b, t)

    def __get_marker_pos(self):

        w, h = self.get_size()
        w_b, h_b = self._border_image.size
        marker = self._marker
        w_m, h_m = marker.size
        offset_x, offset_y = self._img_offset
        x, y = self.quad.get_tex_offset(self._ts2)
        x = (.5 - x) * w_m
        x += offset_x
        y = h_b - (.5 - y) * h_m
        y += offset_y
        x = min(w - 1, max(0, int(round(x))))
        y = min(h - 1, max(0, int(round(y))))

        return x, y

    def __set_marker_pos(self, x, y):

        w, h = self.get_size()
        w_b, h_b = self._border_image.size
        marker = self._marker
        w_m, h_m = marker.size
        offset_x, offset_y = self._img_offset
        x -= offset_x
        x = .5 - x / w_m
        y -= offset_y
        y = .5 - (h_b - y) / h_m
        self.quad.set_tex_offset(self._ts2, x, y)

    def set_hue_sat(self, hue, saturation):

        w, h = self.get_size()
        marker = self._marker
        w_m, h_m = marker.size
        offset_x, offset_y = self._img_offset
        x = int(w * hue)
        x -= offset_x
        x = .5 - x / w_m
        y = int(h * saturation)
        y -= offset_y
        y = .5 - y / h_m
        self.quad.set_tex_offset(self._ts2, x, y)

    def __pick_color(self, task):

        w, h = self.get_size()
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = int(mouse_pointer.x)
        mouse_y = int(mouse_pointer.y)
        mouse_pos = (mouse_x, mouse_y)

        if self._prev_mouse_pos != mouse_pos:
            x, y = self.get_pos(from_root=True)
            x = max(0, min(mouse_x - x, w - 1))
            y = max(0, min(mouse_y - y, h - 1))
            r, g, b = self._gradient.get_xel(x, y)
            self.__set_marker_pos(x, y)
            color = (r, g, b)
            self._command(color, continuous=True, update_fields=True)
            self._prev_mouse_pos = mouse_pos

        return task.cont

    def __end_color_picking(self, cancel=False):

        if self._picking_color:

            self._listener.ignore("gui_mouse1-up")
            self._listener.ignore("gui_mouse3")
            Mgr.remove_task("pick_color")
            w, h = self.get_size()

            if cancel:
                x, y = self._marker_start_pos
                self.__set_marker_pos(x, y)
            else:
                mouse_pointer = Mgr.get("mouse_pointer", 0)
                x, y = self.get_pos(from_root=True)
                x = max(0, min(int(mouse_pointer.x - x), w - 1))
                y = max(0, min(int(mouse_pointer.y - y), h - 1))

            self._picking_color = False
            r, g, b = self._gradient.get_xel(x, y)
            color = (r, g, b)
            self._command(color, continuous=False, update_fields=True)

            if self.mouse_watcher.get_over_region() != self.mouse_region:
                Mgr.set_cursor("main")

    def __on_enter(self, *args):

        if args[0] == self.mouse_region:
            Mgr.set_cursor("eyedropper")

    def __on_leave(self, *args):

        if args[0] == self.mouse_region and not self._picking_color:
            if Mgr.get("active_input_field") and not Menu.is_menu_shown():
                Mgr.set_cursor("input_commit")
            else:
                Mgr.set_cursor("main")

    def __on_left_down(self):

        region = Mgr.get("mouse_watcher").get_over_region()

        if region == self.mouse_region:
            self._picking_color = True
            self._marker_start_pos = self.__get_marker_pos()
            Mgr.add_task(self.__pick_color, "pick_color")
            self._listener.accept("gui_mouse1-up", self.__end_color_picking)
            self._listener.accept("gui_mouse3", lambda: self.__end_color_picking(cancel=True))


class LuminanceControl(WidgetCard):

    _gradient_borders = ()
    _gradient = None
    _img_offset = (0, 0)
    _border_image = None
    _marker = None
    _marker_x = 0

    @classmethod
    def __create_gradient(cls):

        w = 20
        h = 256
        h_ = h - 1
        cls._gradient = img = PNMImage(w, h, 4)

        for y in range(h):

            c = 1. if y < h_ / 2 else 0.
            a = 1. - 2. * y / h_ if y < h_ / 2 else 2. * y / h_ - 1.

            for x in range(w):
                img.set_xel(x, y, c, c, c)
                img.set_alpha(x, y, a)

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["dialog_inset2"]
        cls._gradient_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    @classmethod
    def __create_marker(cls):

        gfx_id = Skin.atlas.gfx_ids["color_control"]["marker"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        cls._marker = img = PNMImage(w, h, 4)
        img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)

        w_b = cls._border_image.size[0]
        w_g = cls._gradient.size[0]
        offset_x = cls._img_offset[0]
        x = int(.5 * w_g)
        x -= offset_x
        cls._marker_x = .5 - (x / w_b) * w_b / h

    def __init__(self, parent):

        WidgetCard.__init__(self, "lum_control", parent)

        if not self._gradient:
            self.__create_gradient()
            self.__set_borders()
            self.__create_border_image()
            self.__create_marker()

        self.outer_borders = self._gradient_borders
        gradient = self._gradient
        w, h = gradient.size
        self.set_size((w, h), is_min=True)
        border_image = self._border_image
        w_b, h_b = border_image.size
        marker = self._marker
        w_m, h_m = marker.size
        offset_x, offset_y = self._img_offset

        # Create the texture stages

        # the first texture stage should show a constant color
        self._ts1 = ts1 = TextureStage("flat_color")
        ts1.color = (1., 0., 0., 1.)
        ts1.set_combine_rgb(TextureStage.CM_modulate,
                            TextureStage.CS_constant, TextureStage.CO_src_color,
                            TextureStage.CS_previous, TextureStage.CO_src_color)
        # the second texture stage should allow the constant color to show through
        # a semi-transparent gradient texture
        ts2 = TextureStage("luminance")
        ts2.sort = 1
        ts2.mode = TextureStage.M_decal
        # the third texture stage should show the marker
        self._ts3 = ts3 = TextureStage("marker")
        ts3.sort = 2
        ts3.mode = TextureStage.M_decal
        # the fourth texture stage should show the border
        ts4 = TextureStage("border")
        ts4.sort = 3
        ts4.mode = TextureStage.M_decal

        gradient_tex = Texture("luminance")
        image = PNMImage(w_b, h_b, 4)
        image.copy_sub_image(gradient, -offset_x, -offset_y, 0, 0)
        gradient_tex.load(image)
        marker_tex = Texture("marker")
        marker_tex.load(self._marker)
        marker_tex.wrap_u = SamplerState.WM_border_color
        marker_tex.wrap_v = SamplerState.WM_border_color
        marker_tex.border_color = (0., 0., 0., 0.)
        border_tex = Texture("border")
        border_tex.load(border_image)

        sort = parent.sort + 1

        quad = self.create_quad((offset_x, w_b + offset_x, -h_b - offset_y, -offset_y))
        quad.set_bin("dialog", sort)
        quad.set_texture(ts1, self.texture)
        quad.set_texture(ts2, gradient_tex)
        quad.set_texture(ts3, marker_tex)
        quad.set_tex_scale(ts3, w_b / w_m, h_b / h_m)
        quad.set_texture(ts4, border_tex)

        self.mouse_region = mouse_region = MouseWatcherRegion("lum_control", 0., 0., 0., 0.)
        mouse_region.sort = sort
        Mgr.get("mouse_watcher").add_region(mouse_region)
        listener = self._listener = DirectObject()
        listener.accept("gui_region_enter", self.__on_enter)
        listener.accept("gui_region_leave", self.__on_leave)
        listener.accept("gui_mouse1", self.__on_left_down)

        self._picking_color = False
        self._prev_mouse_pos = (0, 0)
        self._command = lambda *args, **kwargs: None
        self._main_color = (1., 0., 0.)
        self._luminance = self._luminance_start = .5

    def destroy(self):

        WidgetCard.destroy(self)

        self._listener.ignore_all()
        self._listener = None
        self.command = None

    @property
    def command(self):

        return self._command

    @command.setter
    def command(self, command):

        self._command = command if command else lambda *args, **kwargs: None

    def __create_border_image(self):

        gradient = self._gradient
        w, h = gradient.size
        l, r, b, t = self._gradient_borders
        width = w + l + r
        height = h + b + t
        gfx_ids = Skin.atlas.gfx_ids["color_control"]
        tmp_widget = Widget("tmp", self.parent, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def update_images(self): pass

    def update_mouse_region_frames(self, exclude="", recurse=True):

        w, h = self.get_size()
        x, y = self.get_pos(from_root=True)
        l = x
        r = x + w
        b = -y - h
        t = -y
        self.mouse_region.frame = (l, r, b, t)

    def set_luminance(self, luminance):

        border_img = self._border_image
        h = self.get_size()[1]
        h_b = border_img.size[1]
        marker = self._marker
        h_m = marker.size[1]
        offset_y = self._img_offset[1]
        y = int(h * luminance)
        y -= offset_y
        y = .5 - (y / h_b) * h_b / h_m
        self.quad.set_tex_offset(self._ts3, self._marker_x, y)
        self._luminance = luminance

    def __apply_luminance(self, continuous, update_fields):

        import colorsys

        r, g, b = self._main_color
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        r, g, b = colorsys.hls_to_rgb(h, self._luminance, s)
        self._command((r, g, b), continuous, update_fields)

    def set_main_color(self, color, continuous=False, update_fields=False):

        r, g, b = self._main_color = color
        self._ts1.color = (r, g, b, 1.)
        self.__apply_luminance(continuous, update_fields)

    def __pick_color(self, task):

        w, h = self.get_size()
        h_ = h - 1
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = int(mouse_pointer.x)
        mouse_y = int(mouse_pointer.y)
        mouse_pos = (mouse_x, mouse_y)

        if self._prev_mouse_pos != mouse_pos:
            x, y = self.get_pos(from_root=True)
            y = max(0, min(mouse_y - y, h_))
            lum = 1. - y / h_
            self.set_luminance(lum)
            self.__apply_luminance(continuous=True, update_fields=True)
            self._prev_mouse_pos = mouse_pos

        return task.cont

    def __end_color_picking(self, cancel=False):

        if self._picking_color:

            self._listener.ignore("gui_mouse1-up")
            self._listener.ignore("gui_mouse3")
            Mgr.remove_task("pick_color")

            if cancel:
                self.set_luminance(self._luminance_start)

            self.__apply_luminance(continuous=False, update_fields=True)

            if self.mouse_watcher.get_over_region() != self.mouse_region:
                Mgr.set_cursor("main")

            self._picking_color = False

    def __on_enter(self, *args):

        if args[0] == self.mouse_region:
            Mgr.set_cursor("eyedropper")

    def __on_leave(self, *args):

        if args[0] == self.mouse_region and not self._picking_color:
            if Mgr.get("active_input_field") and not Menu.is_menu_shown():
                Mgr.set_cursor("input_commit")
            else:
                Mgr.set_cursor("main")

    def __on_left_down(self):

        region = Mgr.get("mouse_watcher").get_over_region()

        if region == self.mouse_region:
            self._picking_color = True
            self._luminance_start = self._luminance
            Mgr.add_task(self.__pick_color, "pick_color")
            self._listener.accept("gui_mouse1-up", self.__end_color_picking)
            self._listener.accept("gui_mouse3", lambda: self.__end_color_picking(cancel=True))


class NewColorSwatch(WidgetCard):

    _swatch_borders = ()
    _img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["dialog_inset2"]
        cls._swatch_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent):

        WidgetCard.__init__(self, "new_swatch", parent)

        w = Skin.options["large_colorswatch_width"]
        h = Skin.options["large_colorswatch_height"]
        self.set_size((w, h), is_min=True)

        if not self._swatch_borders:
            self.__set_borders()

        self.outer_borders = self._swatch_borders
        self._ts1 = TextureStage("flat_color")

    def __create_border_image(self):

        w, h = self.get_size()
        l, r, b, t = self._swatch_borders
        width = w + l + r
        height = h + b + t
        gfx_ids = Skin.atlas.gfx_ids["color_control"]
        tmp_widget = Widget("tmp", self.parent, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def __finalize_image(self):

        # Create the texture stages

        ts1 = self._ts1
        ts1.color = (1., 0., 0., 1.)
        ts1.sort = 0
        # the first texture stage should show a constant color
        ts1.set_combine_rgb(TextureStage.CM_modulate,
                            TextureStage.CS_constant, TextureStage.CO_src_color,
                            TextureStage.CS_previous, TextureStage.CO_src_color)
        ts2 = TextureStage("luminance")
        ts2.sort = 1
        # the second texture stage should allow the constant color to show through
        # a semi-transparent border texture
        ts2.mode = TextureStage.M_decal

        tex = Texture("border")
        tex.load(self._border_image)
        sort = self.parent.sort + 1
        w_b, h_b = self._border_image.size
        offset_x, offset_y = self._img_offset
        quad = self.create_quad((offset_x, w_b + offset_x, -h_b - offset_y, -offset_y))
        quad.set_texture(ts1, self.texture)
        quad.set_texture(ts2, tex)
        quad.set_bin("dialog", sort)

    def update_images(self):

        if not self._border_image:
            self.__create_border_image()

        self.__finalize_image()

    def update_mouse_region_frames(self, exclude="", recurse=True): pass

    @property
    def color(self):

        r, g, b, a = self._ts1.color

        return (r, g, b)

    @color.setter
    def color(self, color):

        r, g, b = color
        self._ts1.color = (r, g, b, 1.)


class CurrentColorSwatch(Widget):

    _swatch_borders = ()
    _img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = Skin.atlas.outer_borders["dialog_inset2"]
        cls._swatch_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent):

        Widget.__init__(self, "current_swatch", parent, gfx_ids={})

        self.mouse_region.sort = parent.sort + 1
        w = Skin.options["large_colorswatch_width"]
        h = Skin.options["large_colorswatch_height"]
        self.set_size((w, h), is_min=True)

        if not self._swatch_borders:
            self.__set_borders()

        self.image_offset = self._img_offset
        self.outer_borders = self._swatch_borders
        self.color = (1., 1., 1.)
        self._command = lambda *args, **kwargs: None

    @property
    def command(self):

        return self._command

    @command.setter
    def command(self, command):

        self._command = command if command else lambda *args, **kwargs: None

    def __create_border_image(self):

        w, h = self.get_size()
        l, r, b, t = self._swatch_borders
        width = w + l + r
        height = h + b + t
        gfx_ids = Skin.atlas.gfx_ids["color_control"]
        tmp_widget = Widget("tmp", self.parent, gfx_ids, has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        self.__set_border_image(image)

    def update_images(self, recurse=True, size=None):

        if not self._border_image:
            self.__create_border_image()

    def get_image(self, state=None, composed=True):

        border_img = self._border_image
        image = PNMImage(*border_img.size, 4)
        image.fill(*self.color)
        image.alpha_fill(1.)
        image.blend_sub_image(border_img, 0, 0, 0, 0)

        return image

    def on_enter(self):

        Mgr.set_cursor("eyedropper")

    def on_leave(self):

        if Mgr.get("active_input_field") and not Menu.is_menu_shown():
            Mgr.set_cursor("input_commit")
        else:
            Mgr.set_cursor("main")

    def on_left_down(self):

        self._command(self.color, update_gradients=True)
