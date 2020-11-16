from ..base import *
from ..menu import Menu


class SeparatorGhostImage:

    def __init__(self):

        gfx_id = Skin.atlas.gfx_ids["statusbar"]["separator_ghost"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        img = PNMImage(w, h, 4)
        img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        tex = Texture("ghost_tex")
        tex.minfilter = SamplerState.FT_nearest
        tex.magfilter = SamplerState.FT_nearest
        tex.load(img)
        cm = CardMaker("ghost_image")
        cm.set_frame(0, w, -h, 0)
        self._geom = geom = Mgr.get("gui_root").attach_new_node(cm.generate())
        geom.set_texture(tex)
        geom.set_transparency(TransparencyAttrib.M_alpha)
        geom.set_bin("gui", 4)
        geom.set_depth_test(False)
        geom.set_depth_write(False)
        geom.hide()

    def hide(self):

        self._geom.hide()

    def show(self):

        self._geom.show()

    def set_pos(self, pos):

        x, y = pos
        self._geom.set_x(x)
        self._geom.set_z(-y)

    def set_x(self, x):

        self._geom.set_x(x)

    def set_y(self, y):

        self._geom.set_z(-y)


class StatusBarSeparator(Widget):

    def __init__(self, statusbar):

        gfx_ids = {"": Skin.atlas.gfx_ids["statusbar"]["separator"]}

        Widget.__init__(self, "statusbar_separator", statusbar, gfx_ids)

        self._listener = DirectObject()
        self._mouse_start_x = 0
        self._offset = 0
        self._is_dragged = False
        self._ghost_image = SeparatorGhostImage()

    def set_pos(self, pos):

        Widget.set_pos(self, pos)

        self._ghost_image.set_pos(self.get_pos(from_root=True))

    def __drag(self, task):

        offset = int(Mgr.get("mouse_pointer", 0).x - self._mouse_start_x)

        if self._offset != offset:
            self._offset = offset
            self._ghost_image.set_x(self.get_pos(from_root=True)[0] + offset)

        return task.cont

    def on_enter(self):

        Mgr.set_cursor("move_ew")

    def on_leave(self):

        if not self._is_dragged:
            if Mgr.get("active_input_field") and not Menu.is_menu_shown():
                Mgr.set_cursor("input_commit")
            else:
                Mgr.set_cursor("main")

    def on_left_down(self):

        self._is_dragged = True
        self._mouse_start_x = Mgr.get("mouse_pointer", 0).x
        self._ghost_image.show()
        Mgr.add_task(self.__drag, "drag_separator")
        self._listener.accept_once("gui_mouse1-up", self.on_left_up)

    def on_left_up(self):

        if self._is_dragged:
            Mgr.remove_task("drag_separator")
            self.parent.offset_separator(self._offset)
            self._mouse_start_x = 0
            self._ghost_image.hide()
            Mgr.set_cursor("main")
            self._is_dragged = False


class StatusBar(Widget):

    def __init__(self, parent):

        gfx_ids = {"": Skin.atlas.gfx_ids["statusbar"][""]}

        Widget.__init__(self, "statusbar", parent, gfx_ids)

        sizer = Sizer("horizontal")
        sizer.add((Skin.options["statusbar_mode_area_min_width"], 0))
        sizer.add((0, 0))
        self._separator = separator = StatusBarSeparator(self)
        sizer.add(separator)
        sizer.add((0, 0), proportions=(1., 0))
        gfx_id = Skin.atlas.gfx_ids["statusbar"]["fader"][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        sizer.add((w + self.gfx_inner_borders[1], 0))
        sizer.default_size = self.min_size
        self.sizer = sizer
        img = PNMImage(w, h, 4)
        img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        self._text_fader = img

        self._mode_text = ""
        self._info_text = ""
        self._mode_label = None
        self._info_label = None
        self._interface_status = {}

        Mgr.accept("set_interface_status", self.__set_interface_status)
        Mgr.add_app_updater("status", self.__update_status)

    def get_docking_data(self, point):

        if GD["shift_down"]:
            return

        l, r, b, t = self.mouse_region.frame
        x, y = point

        if l < x < r and b < -y < t:
            return self, "top", ((l + r) // 2, t)

    def __set_interface_status(self, interface_id="main"):

        interface_status = self._interface_status[interface_id]
        mode_text = interface_status["mode"]
        info_text = interface_status["info"]

        if mode_text and mode_text != self._mode_text:
            self.__set_mode_text(mode_text)

        if info_text != self._info_text:
            self.__set_info_text(info_text)

    def __update_status(self, status_specs, interface_id="main"):

        data = GD["status"][status_specs[0]]

        for spec in status_specs[1:]:
            data = data[spec]

        mode_text = data["mode"]
        info_text = data["info"]
        self._interface_status[interface_id] = {"mode": mode_text, "info": info_text}

        if GD["viewport"][GD["viewport"]["active"]] != interface_id:
            return

        if mode_text and mode_text != self._mode_text:
            self.__set_mode_text(mode_text)

        if info_text != self._info_text:
            self.__set_info_text(info_text)

    def __set_mode_text(self, text):

        self._mode_text = text
        skin_text = Skin.text["status"]
        font = skin_text["font"]
        color = skin_text["color"]
        self._mode_label = label = font.create_image(text, color)

        if self.is_hidden():
            return

        x = self.gfx_inner_borders[0]
        w = self._separator.get_pos()[0] - x
        h = self.min_size[1]
        img = PNMImage(w, h, 4)
        img.copy_sub_image(self.get_image(composed=False), 0, 0, x, 0, w, h)
        y = 1 + int(h - label.size[1]) // 2
        img.blend_sub_image(label, 0, y, 0, 0)
        fader = self._text_fader
        w_f = fader.size[0]
        img.blend_sub_image(fader, w - w_f, 0, 0, 0, w_f, h)
        self.card.copy_sub_image(self, img, w, h, x)

    def __set_info_text(self, text):

        self._info_text = text
        skin_text = Skin.text["status"]
        font = skin_text["font"]
        color = skin_text["color"]
        self._info_label = label = font.create_image(text, color)

        if self.is_hidden():
            return

        x_d = self._separator.get_pos()[0]
        w_d, h_d = self._separator.min_size
        x = x_d + w_d
        w = self.get_size()[0] - x - self.gfx_inner_borders[1]
        h = self.min_size[1]
        img = PNMImage(w, h, 4)
        img.copy_sub_image(self.get_image(composed=False), 0, 0, x, 0, w, h)
        y = 1 + int(h - label.size[1]) // 2
        img.blend_sub_image(label, 0, y, 0, 0)
        fader = self._text_fader
        w_f = fader.size[0]
        img.blend_sub_image(fader, w - w_f, 0, 0, 0)
        self.card.copy_sub_image(self, img, w, h, x)

    def get_image(self, state=None, composed=True):

        image = Widget.get_image(self, state, composed)
        label = self._mode_label

        if not (composed and label):
            return image

        width, height = self.get_size()
        l, r, b, t = self.gfx_inner_borders
        x = l
        x_d = self._separator.get_pos()[0]
        w = x_d - x
        h = label.size[1]
        truncated_img = PNMImage(w, h, 4)
        truncated_img.blend_sub_image(label, 0, 0, 0, 0)
        y = 1 + int(height - h) // 2
        image.blend_sub_image(truncated_img, x, y, 0, 0)
        fader = self._text_fader
        w_f = fader.size[0]
        image.blend_sub_image(fader, x + w - w_f, 0, 0, 0)

        label = self._info_label
        w_d, h_d = self._separator.min_size
        x = x_d + w_d
        w = width - x - r
        truncated_img = PNMImage(w, h, 4)
        truncated_img.blend_sub_image(label, 0, 0, 0, 0)
        image.blend_sub_image(truncated_img, x, y, 0, 0)
        image.blend_sub_image(fader, x + w - w_f, 0, 0, 0)

        return image

    def offset_separator(self, offset):

        w, h = size = self.get_size()
        w_sep = self._separator.min_size[0]
        sizer = self.sizer
        sizer_cell = sizer.pop_cell(0)
        x = sizer_cell.object[0]
        d = sizer.cells[3].object[0]
        x_prop = Skin.options["statusbar_proportional_sep"]

        if x == x_prop:
            x += (w - x_prop - w_sep - d) * sizer.cells[0].proportions[0]

        l, r, b, t = self.gfx_inner_borders
        x += offset
        x_min = self._text_fader.size[0] + l + 1
        x_max = w - w_sep - d
        x = min(x_max, max(x_min, x))

        if x > x_prop:
            p = float(w - x_prop - w_sep - d)
            proportion1 = (x - x_prop) / p
            proportion2 = (p - (x - x_prop)) / p
            sizer.cells[0].proportions = (proportion1, 0.)
            sizer.cells[2].proportions = (proportion2, 0.)
            x = x_prop
        else:
            sizer.cells[0].proportions = (0., 0.)
            sizer.cells[2].proportions = (1., 0.)

        sizer.add((x, 0), index=0)
        sizer.update(size)
        sizer.update_mouse_region_frames(exclude="bt")
        self.card.copy_sub_image(self, self.get_image(), w, h)
