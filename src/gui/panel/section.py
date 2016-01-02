from ..base import *


class PanelSectionGroup(object):

    def __init__(self, container, title=""):

        self._container = container
        self._title = title
        mem_dc = wx.MemoryDC()
        mem_dc.SetFont(Fonts.get("default"))
        w, h = mem_dc.GetTextExtent(title)
        w += 8
        self._title_rect = wx.Rect(0, 0, w, h)
        self._text_items = []
        self._child_controls = []
        self._groups = []

        s = .75
        main_color = container.get_panel().get_main_color()
        self._border_color = wx.Colour(*[int(s * c) for c in main_color.Get()])

        container_sizer = container.get_client_sizer()
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(wx.Size(0, h))
        self._client_sizer = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(self._client_sizer, 0, wx.ALL | wx.EXPAND, 10)
        container_sizer.Add(self._sizer, 0, wx.BOTTOM | wx.EXPAND, 5)

    def get_panel(self):

        return self._container.get_panel()

    def get_sizer(self):

        return self._sizer

    def get_client_sizer(self):

        return self._client_sizer

    def add_child_control(self, child_control):

        self._child_controls.append(child_control)

    def add_text(self, text, sizer, sizer_args=None, insertion_index=-1):

        text_item = Text(text)
        self._text_items.append(text_item)
        text_sizer = text_item.get_sizer()
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, text_sizer, *args)
        else:
            sizer.Add(text_sizer, *args)

    def add_group(self, title=""):

        group = PanelSectionGroup(self, title)
        self._groups.append(group)

        return group

    def draw(self, dc, clipping_rect=None):

        x, y = self._sizer.GetPosition()
        w, h = self._sizer.GetSize()
        rect = wx.Rect(x, y, w, h)

        if clipping_rect and not clipping_rect.Intersects(rect):
            return

        h_title = self._title_rect.height
        rect = wx.Rect(x, y + h_title // 2, w, h - h_title // 2)
        self._title_rect.x = x + 8
        self._title_rect.y = y

        main_color = self.get_panel().get_main_color()
        dc.SetPen(wx.Pen(self._border_color))
        dc.DrawRoundedRectangleRect(rect, 5)
        dc.SetPen(wx.Pen(main_color))
        dc.SetBrush(wx.Brush(main_color))
        dc.DrawRectangleRect(self._title_rect)
        dc.SetPen(wx.NullPen)
        self._title_rect.x += 1
        dc.DrawLabel(self._title, self._title_rect, wx.ALIGN_CENTER)

        for item in self._text_items:
            sizer = item.get_sizer()
            x, y = sizer.GetPosition()
            dc.DrawLabel(item.get(), wx.Rect(x, y, 0, 0))

        for group in self._groups:
            group.draw(dc, clipping_rect)

    def enable(self, enable=True):

        for ctrl in self._child_controls:
            ctrl.enable(enable)

        for group in self._groups:
            group.enable(enable)

    def disable(self, show=True):

        for ctrl in self._child_controls:
            ctrl.disable(show)

        for group in self._groups:
            group.disable(show)


class PanelSection(object):

    _gfx = {"border": {}, "title_box": {}, "title_hilite": {}}
    _corner = 0
    _title_box_height = 0
    _expand_btn_rect = None
    _side_width = 0

    @classmethod
    def init(cls):

        imgs = []
        border = cls._gfx["border"]

        for part in ("topleft", "topright", "bottomright", "bottomleft"):
            path = os.path.join(GFX_PATH, "panel_border_etched_%s.png" % part)
            img = Cache.load("image", path)
            imgs.append(img)
            border[part] = img

        cls._corner = border["topleft"].GetWidth()

        for part in ("vert", "hor"):
            path = os.path.join(GFX_PATH, "panel_border_etched_%s.png" % part)
            img = Cache.load("image", path)
            imgs.append(img)
            border[part] = img

        cls._side_width = border["vert"].GetWidth()

        for part in ("box", "hilite"):

            part_gfx = cls._gfx["title_%s" % part]

            for side in ("left", "right"):
                path = os.path.join(
                    GFX_PATH, "panel_section_title_%s_%s.png" % (part, side))
                part_gfx[side] = Cache.load("bitmap", path)

            path = os.path.join(
                GFX_PATH, "panel_section_title_%s_center.png" % part)
            center = Cache.load("image", path)
            imgs.append(center)
            part_gfx["center"] = center

        h_title = cls._gfx["title_box"]["left"].GetHeight()
        cls._title_box_height = h_title
        cls._expand_btn_rect = wx.Rect(0, 0, h_title, h_title)

        for img in imgs:
            if not img.HasAlpha():
                img.InitAlpha()

        for part in ("topleft", "topright", "bottomright", "bottomleft"):
            border[part] = border[part].ConvertToBitmap()

    @classmethod
    def get_client_offset(cls):

        return cls._corner

    def __init__(self, panel, title="", index=None):

        self._panel = panel
        self._title = title
        self._is_title_hilited = False
        self._title_hilite_color = (1., 1., 1., 1.)
        self._bitmaps = {}
        self._width = 0
        self._groups = []
        self._text_items = []
        self._child_controls = []
        self._title_rect = wx.Rect()

        self._is_shown = True
        self._is_expanded = True

        panel_sizer = panel.get_section_sizer()
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(wx.Size(0, self._title_box_height))
        self._client_sizer = wx.BoxSizer(wx.VERTICAL)
        self._sizer.Add(self._client_sizer, 0, wx.ALL |
                        wx.EXPAND, self._corner)

        if index is None:
            panel_sizer.Add(self._sizer, 0, wx.TOP | wx.EXPAND, 5)
        else:
            panel_sizer.Insert(index, self._sizer, 0, wx.TOP | wx.EXPAND, 5)

    def finalize(self):

        corner = self._corner
        h_title = self._title_box_height
        w, h = self._sizer.GetSize()
        self._width = w
        self._title_rect = wx.Rect(0, 0, w, h_title)
        h_side = h - h_title - corner

        dc = wx.MemoryDC()

        def create_title_part(part_id):

            bitmap_type = wx.EmptyBitmap if part_id == "box" else wx.EmptyBitmapRGBA
            bitmap = bitmap_type(w, h_title)
            title_part = self._gfx["title_%s" % part_id]
            img = title_part["center"]
            bitmap_center = img.Scale(
                w - corner * 2, h_title).ConvertToBitmap()
            dc.SelectObject(bitmap)
            dc.DrawBitmap(title_part["left"], 0, 0)
            dc.DrawBitmap(bitmap_center, corner, 0)
            dc.DrawBitmap(title_part["right"], w - corner, 0)
            dc.SelectObject(wx.NullBitmap)

            return bitmap

        def create_collapsed():

            bitmap = wx.EmptyBitmapRGBA(w, h_title)
            border = self._gfx["border"]
            img = border["hor"]
            h_bottom = img.GetHeight()
            bitmap_hor = img.Scale(w - corner * 2, h_bottom).ConvertToBitmap()
            dc.SelectObject(bitmap)
            dc.DrawBitmap(border["topleft"], 0, 0)
            dc.DrawBitmap(border["bottomleft"], 0, corner)
            dc.DrawBitmap(bitmap_hor, corner, 0)
            dc.DrawBitmap(bitmap_hor, corner, h_title - h_bottom)
            dc.DrawBitmap(border["topright"], w - corner, 0)
            dc.DrawBitmap(border["bottomright"], w - corner, corner)
            dc.SelectObject(wx.NullBitmap)

            return bitmap

        def create_bottom():

            bitmap = wx.EmptyBitmapRGBA(w, corner)
            border = self._gfx["border"]
            img = border["hor"]
            h_bottom = img.GetHeight()
            bitmap_hor = img.Scale(w - corner * 2, h_bottom).ConvertToBitmap()
            dc.SelectObject(bitmap)
            dc.DrawBitmap(border["bottomleft"], 0, 0)
            dc.DrawBitmap(bitmap_hor, corner, corner - h_bottom)
            dc.DrawBitmap(border["bottomright"], w - corner, 0)
            dc.SelectObject(wx.NullBitmap)

            return bitmap

        def create_side():

            img = self._gfx["border"]["vert"]

            return img.Scale(self._side_width, h_side).ConvertToBitmap()

        for part_id in ("box", "hilite"):
            gfx_id = ("panel_section_title_%s" % part_id, w)
            gfx_id += (self._title_hilite_color,
                       ) if part_id == "hilite" else ()
            bitmap = Cache.create(
                "bitmap", gfx_id, lambda: create_title_part(part_id))
            value = bitmap if part_id == "box" else {
                self._title_hilite_color: bitmap}
            self._bitmaps["title_%s" % part_id] = value

        gfx_id = ("panel_section_collapsed", w)
        bitmap = Cache.create("bitmap", gfx_id, create_collapsed)
        self._bitmaps["collapsed"] = bitmap
        gfx_id = ("panel_section_bottom", w)
        bitmap = Cache.create("bitmap", gfx_id, create_bottom)
        self._bitmaps["bottom"] = bitmap
        gfx_id = ("panel_section_side", w, h_side)
        self._bitmaps["side"] = Cache.create("bitmap", gfx_id, create_side)

    def destroy(self):

        self._groups = []
        self._child_controls = []
        self._text_items = []
        self._sizer = None
        self._client_sizer = None

    def draw(self, dc, clipping_rect=None):

        if not self._is_shown:
            return

        x, y = self._sizer.GetPosition()
        w, h = self._sizer.GetSize()
        rect = wx.Rect(x, y, w, h)

        if clipping_rect and not clipping_rect.Intersects(rect):
            return

        corner = self._corner
        h_title = self._title_box_height
        w_side = self._side_width
        h_side = h - h_title - corner
        self._title_rect.x = x
        self._title_rect.y = y

        l = h_title // 2
        a = h_title // 2 - 6

        if not self._is_expanded:

            dc.DrawBitmap(self._bitmaps["collapsed"], x, y)

            if self._is_title_hilited:
                bitmap = self._bitmaps["title_hilite"][
                    self._title_hilite_color]
                dc.DrawBitmap(bitmap, x, y)

            dc.DrawLine(x + l, y + l, x + l + 7, y + l)
            dc.DrawLine(x + l + 3, y + l - 3, x + l + 3, y + l + 4)
            dc.DrawLabel(self._title, self._title_rect, wx.ALIGN_CENTER)

            return

        dc.DrawBitmap(self._bitmaps["title_box"], x, y)
        dc.DrawBitmap(self._bitmaps["side"], x, y + h_title)
        dc.DrawBitmap(self._bitmaps["side"], x + w - w_side, y + h_title)
        dc.DrawBitmap(self._bitmaps["bottom"], x, y + h - corner)

        if self._is_title_hilited:
            bitmap = self._bitmaps["title_hilite"][self._title_hilite_color]
            dc.DrawBitmap(bitmap, x, y)

        dc.DrawLine(x + l, y + l, x + l + 7, y + l)
        dc.DrawLabel(self._title, self._title_rect, wx.ALIGN_CENTER)

        for item in self._text_items:
            sizer = item.get_sizer()
            x, y = sizer.GetPosition()
            dc.DrawLabel(item.get(), wx.Rect(x, y, 0, 0))

        for group in self._groups:
            group.draw(dc, clipping_rect)

    def get_panel(self):

        return self._panel

    def get_sizer(self):

        return self._sizer

    def get_client_sizer(self):

        return self._client_sizer

    def add_group(self, title=""):

        group = PanelSectionGroup(self, title)
        self._groups.append(group)

        return group

    def add_child_control(self, child_control):

        self._child_controls.append(child_control)

    def add_text(self, text, sizer, sizer_args=None, insertion_index=-1):

        text_item = Text(text)
        self._text_items.append(text_item)
        text_sizer = text_item.get_sizer()
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, text_sizer, *args)
        else:
            sizer.Add(text_sizer, *args)

    def title_has_mouse(self, mouse_pos):

        self._title_rect.SetPosition(self._sizer.GetPosition())

        return self._title_rect.Contains(mouse_pos)

    def set_title_hilited(self, hilited=True):

        self._is_title_hilited = hilited
        self._panel.Refresh()

    def set_title_hilite_color(self, color):

        self._title_hilite_color = color

        if color not in self._bitmaps["title_hilite"]:

            def create_hilite():

                r, g, b, a = color
                title_hilite_bitmap = self._bitmaps[
                    "title_hilite"][(1., 1., 1., 1.)]
                img = title_hilite_bitmap.ConvertToImage().AdjustChannels(r, g, b, a)

                return img.ConvertToBitmap()

            gfx_id = ("panel_section_title_hilite", self._width, color)
            self._bitmaps["title_hilite"][color] = Cache.create(
                "bitmap", gfx_id, create_hilite)

    def handle_left_down(self, mouse_pos):

        if not self._is_shown:
            return False

        self._title_rect.SetPosition(self._sizer.GetPosition())

        if self._title_rect.Contains(mouse_pos):
            self.expand(not self._is_expanded)
            return True

        return False

    def expand(self, expand=True):

        if not self._is_shown or self._is_expanded == expand:
            return

        self._sizer.Show(1, expand)
        self._is_expanded = expand

        panel = self._panel
        panel.update_parent()
        panel.GetSizer().Layout()

    def is_expanded(self):

        return self._is_expanded

    def check_collapsed_state(self):

        if not self._is_expanded:
            self._sizer.Hide(1)

        if not self._is_shown:
            panel = self._panel
            sizer = panel.get_section_sizer()
            sizer.Hide(self._sizer)

    def show(self, show=True):

        if self._is_shown == show:
            return

        self._is_shown = show

        panel = self._panel

        if not panel.is_expanded():
            return

        sizer = panel.get_section_sizer()
        sizer.Show(self._sizer, show)

        if show and not self._is_expanded:
            self._sizer.Hide(1)

    def is_shown(self):

        return self._is_shown

    def enable(self, enable=True):

        for ctrl in self._child_controls:
            ctrl.enable(enable)

        for group in self._groups:
            group.enable(enable)

    def disable(self, show=True):

        for ctrl in self._child_controls:
            ctrl.disable(show)

        for group in self._groups:
            group.disable(show)
