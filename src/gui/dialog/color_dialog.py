from .dialog import *
import colorsys


class ColorSwatchGroup(Widget):

    _group_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset2"]
        cls._group_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    def __init__(self, parent, command):

        Widget.__init__(self, "colorswatch_group", parent, gfx_data={})

        if not self._group_borders:
            self.__set_borders()

        self.image_offset = self._img_offset
        self.outer_borders = self._group_borders
        self.mouse_region.sort = parent.sort + 1

        self._command = command

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

        w = Skin["options"]["small_colorswatch_width"]
        h = Skin["options"]["small_colorswatch_height"]
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

    def __init__(self, parent, command):

        ColorSwatchGroup.__init__(self, parent, command)

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
        gfx_data = {"": INSET2_BORDER_GFX_DATA}
        tmp_widget = Widget("tmp", self.parent, gfx_data, has_mouse_region=False)
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

        w = Skin["options"]["small_colorswatch_width"]
        h = Skin["options"]["small_colorswatch_height"]
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

    def __init__(self, parent, command):

        ColorSwatchGroup.__init__(self, parent, command)

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
        gfx_data = {"": INSET2_BORDER_GFX_DATA}
        tmp_widget = Widget("tmp", self.parent, gfx_data, has_mouse_region=False)
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
        w = Skin["options"]["small_colorswatch_width"]
        h = Skin["options"]["small_colorswatch_height"]
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

        w = Skin["options"]["colorgradient_width"]
        h = Skin["options"]["colorgradient_height"]
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

        x, y, w, h = TextureAtlas["regions"]["color_gradient_marker"]
        cls._marker = img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset2"]
        cls._gradient_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent, command):

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
        self._command = command
        r, g, b = self._gradient.get_xel(0, 0)
        color = (r, g, b)
        command(color, continuous=False, update_fields=True)

    def destroy(self):

        WidgetCard.destroy(self)

        self._listener.ignore_all()
        self._listener = None

    def __create_border_image(self):

        gradient = self._gradient
        w, h = gradient.size
        l, r, b, t = self._gradient_borders
        width = w + l + r
        height = h + b + t
        gfx_data = {"": INSET2_BORDER_GFX_DATA}
        tmp_widget = Widget("tmp", self.parent, gfx_data, has_mouse_region=False)
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

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset2"]
        cls._gradient_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    @classmethod
    def __create_marker(cls):

        x, y, w, h = TextureAtlas["regions"]["color_gradient_marker"]
        cls._marker = img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)

        w_b = cls._border_image.size[0]
        w_g = cls._gradient.size[0]
        offset_x = cls._img_offset[0]
        x = int(.5 * w_g)
        x -= offset_x
        cls._marker_x = .5 - (x / w_b) * w_b / h

    def __init__(self, parent, command):

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
        self._command = command
        self._main_color = (1., 0., 0.)
        self._luminance = self._luminance_start = .5

    def destroy(self):

        WidgetCard.destroy(self)

        self._listener.ignore_all()
        self._listener = None

    def __create_border_image(self):

        gradient = self._gradient
        w, h = gradient.size
        l, r, b, t = self._gradient_borders
        width = w + l + r
        height = h + b + t
        gfx_data = {"": INSET2_BORDER_GFX_DATA}
        tmp_widget = Widget("tmp", self.parent, gfx_data, has_mouse_region=False)
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

        r, g, b = self._main_color
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        r, g, b = colorsys.hls_to_rgb(h, self._luminance, s)
        self._command((r, g, b), continuous, update_fields)

    def set_main_color(self, color, continuous=False, update_fields=False):

        r, g, b = self._main_color = color
        self._ts1.set_color((r, g, b, 1.))
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

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset2"]
        cls._swatch_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent):

        WidgetCard.__init__(self, "new_swatch", parent)

        w = Skin["options"]["large_colorswatch_width"]
        h = Skin["options"]["large_colorswatch_height"]
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
        gfx_data = {"": INSET2_BORDER_GFX_DATA}
        tmp_widget = Widget("tmp", self.parent, gfx_data, has_mouse_region=False)
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

    def set_color(self, color):

        r, g, b = color
        self._ts1.set_color((r, g, b, 1.))

    def get_color(self):

        r, g, b, a = self._ts1.get_color()

        return (r, g, b)


class CurrentColorSwatch(Widget):

    _swatch_borders = ()
    _img_offset = (0, 0)
    _border_image = None

    @classmethod
    def __set_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset2"]
        cls._swatch_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def __set_border_image(cls, border_image):

        cls._border_image = border_image

    def __init__(self, parent, color, command):

        Widget.__init__(self, "current_swatch", parent, gfx_data={})

        self.mouse_region.sort = parent.sort + 1
        w = Skin["options"]["large_colorswatch_width"]
        h = Skin["options"]["large_colorswatch_height"]
        self.set_size((w, h), is_min=True)

        if not self._swatch_borders:
            self.__set_borders()

        self.image_offset = self._img_offset
        self.outer_borders = self._swatch_borders
        self._color = color
        self._command = command

    def __create_border_image(self):

        w, h = self.get_size()
        l, r, b, t = self._swatch_borders
        width = w + l + r
        height = h + b + t
        gfx_data = {"": INSET2_BORDER_GFX_DATA}
        tmp_widget = Widget("tmp", self.parent, gfx_data, has_mouse_region=False)
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
        image.fill(*self._color)
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

        self._command(self._color, update_gradients=True)


class ColorDialog(Dialog):

    _clock = ClockObject()
    _rgb_range_id = "255"

    @classmethod
    def __set_rgb_range(cls, range_id, fields):

        cls._rgb_range_id = range_id
        value_range = (0., 255.) if range_id == "255" else (0., 1.)
        step = 1. if range_id == "255" else .001

        for field in fields:
            field.set_value_range(value_range)
            field.set_step(step)

    def __init__(self, title="", color=(1., 1., 1.), choices="okcancel", ok_alias="OK",
                 on_yes=None, on_no=None, on_cancel=None):

        def command():

            if on_yes:
                on_yes(self._new_color)

        Dialog.__init__(self, title, choices, ok_alias, command, on_no, on_cancel)

        self._controls = ctrls = {}
        self._fields = fields = {}
        client_sizer = self.get_client_sizer()
        subsizer = Sizer("horizontal")
        swatch_sizer = Sizer("vertical")
        swatch_sizer.add(DialogText(self, "Basic colors:"))
        basic_colors = BasicColorGroup(self, self.__set_color)
        self._custom_colors = custom_colors = CustomColorGroup(self, self.__set_color)
        btn = DialogButton(self, "Add New", command=self.__add_custom_color)
        swatch_sizer.add(basic_colors)
        swatch_sizer.add((0, 20))
        swatch_sizer.add(DialogText(self, "Custom colors:"))
        swatch_sizer.add(custom_colors)
        swatch_sizer.add((0, 5))
        swatch_sizer.add(btn, alignment="center_h")
        borders = (20, 20, 10, 20)
        subsizer.add(swatch_sizer, expand=True, borders=borders)
        control_sizer = Sizer("vertical")
        gradient_sizer = Sizer("horizontal")
        control_subsizer = Sizer("horizontal")
        control_sizer.add(gradient_sizer, expand=True, borders=borders)
        borders = (20, 20, 10, 0)
        control_sizer.add(control_subsizer, expand=True, borders=borders)
        subsizer.add(control_sizer, expand=True)
        client_sizer.add(subsizer, expand=True)

        self._new_color = color
        self._new_color_swatch = new_swatch = NewColorSwatch(self)
        self._current_color_swatch = cur_swatch = CurrentColorSwatch(self, color, self.__set_color)
        ctrls["luminance"] = lum_control = LuminanceControl(self, self.__set_color)
        ctrls["hue_sat"] = hue_sat_control = HueSatControl(self, self.__set_main_luminance_color)
        gradient_sizer.add(hue_sat_control)
        borders = (20, 0, 0, 0)
        gradient_sizer.add(lum_control, borders=borders)
        main_swatch_sizer = Sizer("vertical")
        gradient_sizer.add(main_swatch_sizer, expand=True, borders=borders)
        main_swatch_sizer.add(DialogText(self, "New"), alignment="center_h")
        main_swatch_sizer.add(new_swatch, proportion=1.)
        main_swatch_sizer.add((0, 5))
        main_swatch_sizer.add(DialogText(self, "Current"), alignment="center_h")
        main_swatch_sizer.add(cur_swatch, proportion=1.)
        rgb_field_sizer = Sizer("vertical")
        hsl_field_sizer = Sizer("vertical")
        control_subsizer.add(rgb_field_sizer, proportion=1., alignment="center_v")
        control_subsizer.add((20, 0))
        control_subsizer.add(hsl_field_sizer, proportion=1., alignment="center_v")
        r_sizer = Sizer("horizontal")
        r_sizer.add(DialogText(self, "R:"), alignment="center_v")
        rgb_field_sizer.add(r_sizer, expand=True)
        g_sizer = Sizer("horizontal")
        g_sizer.add(DialogText(self, "G:"), alignment="center_v")
        rgb_field_sizer.add(g_sizer, expand=True)
        b_sizer = Sizer("horizontal")
        b_sizer.add(DialogText(self, "B:"), alignment="center_v")
        rgb_field_sizer.add(b_sizer, expand=True)
        h_sizer = Sizer("horizontal")
        h_sizer.add(DialogText(self, "H:"), alignment="center_v")
        hsl_field_sizer.add(h_sizer, expand=True)
        s_sizer = Sizer("horizontal")
        s_sizer.add(DialogText(self, "S:"), alignment="center_v")
        hsl_field_sizer.add(s_sizer, expand=True)
        l_sizer = Sizer("horizontal")
        l_sizer.add(DialogText(self, "L:"), alignment="center_v")
        hsl_field_sizer.add(l_sizer, expand=True)

        borders = (5, 0, 0, 0)
        rgb_fields = []
        handler = self.__handle_color_component

        val_rng = (0., 255.) if self._rgb_range_id == "255" else (0., 1.)
        step = 1. if self._rgb_range_id == "255" else .001
        field = DialogSpinnerField(self, "red", "float", val_rng, step,
                                  handler, 100, has_slider=True)
        r_sizer.add(field, proportion=1., borders=borders)
        rgb_fields.append(field)
        fields["red"] = field
        field = DialogSpinnerField(self, "green", "float", val_rng, step,
                                  handler, 100, has_slider=True)
        g_sizer.add(field, proportion=1., borders=borders)
        rgb_fields.append(field)
        fields["green"] = field
        field = DialogSpinnerField(self, "blue", "float", val_rng, step,
                                  handler, 100, has_slider=True)
        b_sizer.add(field, proportion=1., borders=borders)
        rgb_fields.append(field)
        fields["blue"] = field

        val_rng = (0., 1.)
        step = .001
        field = DialogSpinnerField(self, "hue", "float", val_rng, step,
                                   handler, 100, has_slider=True)
        h_sizer.add(field, proportion=1., borders=borders)
        fields["hue"] = field
        field = DialogSpinnerField(self, "sat", "float", val_rng, step,
                                   handler, 100, has_slider=True)
        s_sizer.add(field, proportion=1., borders=borders)
        fields["sat"] = field
        field = DialogSpinnerField(self, "lum", "float", val_rng, step,
                                   handler, 100, has_slider=True)
        l_sizer.add(field, proportion=1., borders=borders)
        fields["lum"] = field

        range_sizer = Sizer("horizontal")
        borders = (20, 20, 20, 0)
        control_sizer.add(range_sizer, expand=True, borders=borders)
        range_sizer.add(DialogText(self, "RGB range:"), alignment="center_v")
        radio_btns = DialogRadioButtonGroup(self, columns=2, gap_h=10)
        radio_btns.add_button("255", "0-255")
        command = lambda: self.__set_rgb_range("255", rgb_fields)
        radio_btns.set_button_command("255", command)
        radio_btns.add_button("1", "0-1")
        command = lambda: self.__set_rgb_range("1", rgb_fields)
        radio_btns.set_button_command("1", command)
        radio_btns.set_selected_button(self._rgb_range_id)
        borders = (5, 0, 0, 0)
        range_sizer.add(radio_btns.sizer, alignment="center_v", borders=borders)

        self.finalize()
        self.__set_color(color, update_gradients=True)

    def close(self, answer=""):

        self._controls = None
        self._fields = None
        self._custom_colors = None
        self._new_color_swatch = None
        self._current_color_swatch = None

        Dialog.close(self, answer)

    def __set_main_luminance_color(self, color, continuous=False, update_fields=False):

        self._controls["luminance"].set_main_color(color, continuous, update_fields)

    def __set_color(self, color, continuous=False, update_fields=True, update_gradients=False):

        self._new_color = color
        self._new_color_swatch.set_color(color)
        fields = self._fields

        if fields:

            if continuous:
                if self._clock.real_time > .1:
                    self._clock.reset()
                else:
                    update_fields = False

            if update_fields:

                rgb_scale = 255. if self._rgb_range_id == "255" else 1.
                r, g, b = [c * rgb_scale for c in color]
                fields["red"].set_value(r)
                fields["green"].set_value(g)
                fields["blue"].set_value(b)
                h, l, s = colorsys.rgb_to_hls(*color)
                fields["hue"].set_value(h)
                fields["sat"].set_value(s)
                fields["lum"].set_value(l)

                if update_gradients:
                    lum_ctrl = self._controls["luminance"]
                    lum_ctrl.set_luminance(l)
                    r, g, b = colorsys.hls_to_rgb(h, .5, s)
                    lum_ctrl.set_main_color((r, g, b), continuous=False, update_fields=False)
                    self._controls["hue_sat"].set_hue_sat(h, s)

    def __handle_color_component(self, component_id, value, state="done"):

        fields = self._fields
        rgb_components = ["red", "green", "blue"]
        hsl_components = ["hue", "sat", "lum"]
        rgb_scale = 255. if self._rgb_range_id == "255" else 1.

        if component_id in rgb_components:

            r, g, b = [fields[c].get_value() / rgb_scale for c in rgb_components]
            h, l, s = colorsys.rgb_to_hls(r, g, b)
            fields["hue"].set_value(h)
            fields["sat"].set_value(s)
            fields["lum"].set_value(l)
            self._controls["luminance"].set_luminance(l)
            r_, g_, b_ = colorsys.hls_to_rgb(h, .5, s)
            self._controls["luminance"].set_main_color((r_, g_, b_), continuous=False)
            self._controls["hue_sat"].set_hue_sat(h, s)

        else:

            h, s, l = [fields[c].get_value() for c in hsl_components]
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            fields["red"].set_value(r * rgb_scale)
            fields["green"].set_value(g * rgb_scale)
            fields["blue"].set_value(b * rgb_scale)

            if component_id == "lum":
                self._controls["luminance"].set_luminance(l)
            else:
                r_, g_, b_ = colorsys.hls_to_rgb(h, .5, s)
                self._controls["luminance"].set_main_color((r_, g_, b_), continuous=False)
                self._controls["hue_sat"].set_hue_sat(h, s)

        self._new_color = color = (r, g, b)
        self._new_color_swatch.set_color(color)

    def __add_custom_color(self):

        self._custom_colors.add_swatch(self._new_color)

    def update_widget_positions(self):

        self._new_color_swatch.update_quad_pos()
        self._controls["luminance"].update_quad_pos()
        self._controls["hue_sat"].update_quad_pos()
