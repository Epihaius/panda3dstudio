from ..base import *
from .section import PanelSection


class Panel(wx.PyPanel, BaseObject, FocusResetter):

    _gfx = {"arrows": {}, "body": {}, "header": {}}
    _heights = {}
    _main_color = None

    @classmethod
    def init(cls):

        PanelSection.init()

        arrows = cls._gfx["arrows"]

        for extent, direction in (("expanded", "up"), ("collapsed", "down")):

            arrows[extent] = {}

            for state in ("normal", "hilited"):
                values = (direction, state)
                path = os.path.join(GFX_PATH, "panel_arrow_%s_%s.png" % values)
                arrows[extent][state] = wx.Bitmap(path)

        cls._heights["arrow"] = arrows["expanded"]["normal"].GetHeight()

        imgs = []
        body = cls._gfx["body"]

        for part in ("top", "bottom", "bottom_hilited", "collapsed"):
            path = os.path.join(GFX_PATH, "panel_%s.png" % part)
            img = wx.Image(path)
            body[part] = img
            cls._heights[part] = img.GetHeight()

        path = os.path.join(GFX_PATH, "panel_main.png")
        img = Cache.load("image", path)
        r = img.GetRed(0, 0)
        g = img.GetGreen(0, 0)
        b = img.GetBlue(0, 0)
        cls._main_color = wx.Colour(r, g, b)

        header = cls._gfx["header"]

        for size in ("exp", "coll"):

            header[size] = {}

            for part in ("left", "right"):
                values = (size, part)
                path = os.path.join(GFX_PATH, "panel_%s_header_%s.png" % values)
                header[size][part] = wx.Bitmap(path)

            path = os.path.join(GFX_PATH, "panel_%s_header_center.png" % size)
            header_center = wx.Image(path)
            imgs.append(header_center)
            header[size]["center"] = header_center

        for img in imgs:
            if not img.HasAlpha():
                img.InitAlpha()

    @classmethod
    def get_main_color(cls):

        return cls._main_color

    def __init__(self, parent, header_text="", focus_receiver=None, interface_id=""):

        self._is_finalized = False

        wx.PyPanel.__init__(self, parent)
        BaseObject.__init__(self, interface_id)
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus(on_click=self.__on_left_down)

        self._bitmaps = {}
        self._arrow_pos = None
        self._bottom_hilited = None
        self._bottom_rect = None
        self._header_text = header_text
        self._header_bitmaps = {}
        self._header_rect = None
        self._text_items = {"top": [], "bottom": []}
        self._child_controls = []
        self._sections = {}

        self._is_enabled = True
        self._has_mouse = False
        self._is_clicked = False
        self._is_expanded = True

        self._are_top_ctrls_shown = True
        self._are_bottom_ctrls_shown = True

        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self._top_ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        self._section_sizer = wx.BoxSizer(wx.VERTICAL)
        self._bottom_ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        h_top = self._heights["top"]
        h_header = self._gfx["header"]["exp"]["left"].GetHeight()
        self._sizer.Add(wx.Size(0, h_top + 1))
        self._sizer.Add(wx.Size(0, h_header + 7 - h_top))
        self._sizer.Add(self._top_ctrl_sizer, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 2)
        self._sizer.Add(self._section_sizer, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 2)
        self._sizer.Add(self._bottom_ctrl_sizer, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 2)
        h_bottom = self._heights["bottom"]
        self._sizer.Add(wx.Size(0, h_bottom + 1))
        self.SetSizer(self._sizer)

    def finalize(self):

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.__draw)
        self.Bind(wx.EVT_ENTER_WINDOW, self.__on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)
        self.Bind(wx.EVT_RIGHT_DOWN, self.__on_right_down)
        self.Bind(wx.EVT_LEFT_UP, self.__on_left_up)
        self.Bind(wx.EVT_LEFT_DCLICK, self.__on_left_doubleclick)
        self.Bind(wx.EVT_SIZE, self.__on_size)

        self._sizer.Layout()
        self._sizer.Fit(self)
        w, h = self.GetSize()

        for section in self._sections.itervalues():
            section.finalize()

        body = self._gfx["body"]
        image_top = body["top"]
        image_bottom = body["bottom"]
        image_collapsed = body["collapsed"]
        image_bottom_hilited = body["bottom_hilited"]
        h_top = self._heights["top"]
        h_bottom = self._heights["bottom"]
        h_main = h - h_top - h_bottom

        header_parts = self._gfx["header"].copy()

        for state in header_parts:
            header_parts[state] = header_parts[state].copy()

        header_center_imgs = {}
        w_header_side, h_header = header_parts["exp"]["left"].GetSize()
        header_center = header_parts["exp"]["center"]
        header_center_img = header_center.Scale(w - 2 * w_header_side - 16, h_header)
        header_center_imgs["exp"] = header_center_img
        header_center = header_center_img.ConvertToBitmap()
        header_parts["exp"]["center"] = header_center
        header_center = header_parts["coll"]["center"]
        header_center_img = header_center.Scale(w - 2 * w_header_side - 16, h_header)
        header_center_imgs["coll"] = header_center_img
        header_center = header_center_img.ConvertToBitmap()
        header_parts["coll"]["center"] = header_center

        gfx_id = ("panel", "top", w)
        self._bitmaps["top"] = Cache.create("bitmap", gfx_id, lambda:
            image_top.Scale(w, h_top).ConvertToBitmap())
        gfx_id = ("panel", "bottom", w)
        self._bitmaps["bottom"] = Cache.create("bitmap", gfx_id, lambda:
            image_bottom.Scale(w, h_bottom).ConvertToBitmap())
        arrows = self._gfx["arrows"]
        arrow_up_normal = arrows["expanded"]["normal"]
        w_a, h_a = arrow_up_normal.GetSize()
        self._arrow_pos = wx.Size((w - w_a) // 2, h - h_a)
        h_b = self._heights["bottom_hilited"]
        gfx_id = ("panel", "bottom_hilited", w)
        self._bottom_hilited = Cache.create("bitmap", gfx_id, lambda:
            image_bottom_hilited.Scale(w, h_b).ConvertToBitmap())
        self._bottom_rect = wx.Rect(0, h - h_b, w, h_b)
        self._header_rect = wx.Rect(8, 8, w - 16, h_header)
        dc = wx.MemoryDC()

        def create_header(state):

            if PLATFORM_ID == "Linux":
                header_bitmap = wx.EmptyBitmap(w - 16, h_header)
            else:
                header_bitmap = wx.EmptyBitmapRGBA(w - 16, h_header)

            dc.SelectObject(header_bitmap)
            dc.DrawBitmap(header_parts[state]["left"], 0, 0)
            dc.DrawBitmap(header_parts[state]["center"], w_header_side, 0)
            dc.DrawBitmap(header_parts[state]["right"], w - w_header_side - 16, 0)
            dc.SelectObject(wx.NullBitmap)

            if PLATFORM_ID == "Linux":

                img = header_bitmap.ConvertToImage()

                if not img.HasAlpha():
                    img.InitAlpha()

                center_img = header_center_imgs[state]

                if not center_img.HasAlpha():
                    center_img.InitAlpha()

                alpha_map = []
                get_alpha(center_img, alpha_map)
            
                for y, row in enumerate(alpha_map):
                    for x, alpha in enumerate(row):
                        img.SetAlpha(x + w_header_side, y, alpha)

                left_img = header_parts[state]["left"].ConvertToImage()

                if not left_img.HasAlpha():
                    left_img.InitAlpha()

                alpha_map = []
                get_alpha(left_img, alpha_map)

                for y, row in enumerate(alpha_map):
                    for x, alpha in enumerate(row):
                        img.SetAlpha(x, y, alpha)

                header_bitmap = img.ConvertToBitmap()

                right_img = header_parts[state]["right"].ConvertToImage()

                if not right_img.HasAlpha():
                    right_img.InitAlpha()

                alpha_map = []
                get_alpha(right_img, alpha_map)
                offset_x = w - w_header_side - 16

                for y, row in enumerate(alpha_map):
                    for x, alpha in enumerate(row):
                        img.SetAlpha(x + offset_x, y, alpha)

                header_bitmap = img.ConvertToBitmap()

            return header_bitmap

        gfx_id = ("panel", "header_expanded", w)
        self._header_bitmaps["expanded"] = Cache.create("bitmap", gfx_id, lambda:
            create_header("exp"))
        gfx_id = ("panel", "header_collapsed", w)
        self._header_bitmaps["collapsed"] = Cache.create("bitmap", gfx_id, lambda:
            create_header("coll"))
        h = self._heights["collapsed"]
        gfx_id = ("panel", "collapsed", w)
        self._bitmaps["collapsed"] = Cache.create("bitmap", gfx_id, lambda:
            image_collapsed.Scale(w, h).ConvertToBitmap())

        def create_header_back(state):

            header_back_bitmap = wx.EmptyBitmap(w - 8, h_header + 8)
            dc.SelectObject(header_back_bitmap)
            dc.SetPen(wx.Pen(wx.Colour(), 1, wx.TRANSPARENT))
            dc.SetBrush(wx.Brush(self._main_color))
            dc.DrawRectangle(0, 0, w - 8, h_header + 8)
            dc.DrawBitmap(self._bitmaps["top"], 0, 0)
            header_back = header_back_bitmap.ConvertToImage().GetSubImage(self._header_rect)
            intensity = [1.6 if state == "expanded" else 1.2] * 3

            return header_back.AdjustChannels(*intensity).ConvertToBitmap()

        gfx_id = ("panel", "header_back_expanded", w)
        header_back_expanded = Cache.create("bitmap", gfx_id, lambda:
            create_header_back("expanded"))
        gfx_id = ("panel", "header_back_collapsed", w)
        header_back_collapsed = Cache.create("bitmap", gfx_id, lambda:
            create_header_back("collapsed"))
        self._bitmaps["header_back_expanded"] = header_back_expanded
        self._bitmaps["header_back_collapsed"] = header_back_collapsed
        dc.SelectObject(wx.NullBitmap)

        self.Refresh()

        self._is_finalized = True

    def get_header(self):

        return self._header_text

    def get_section_sizer(self):

        return self._section_sizer

    def get_top_ctrl_sizer(self):

        return self._top_ctrl_sizer

    def get_bottom_ctrl_sizer(self):

        return self._bottom_ctrl_sizer

    def add_child_control(self, child_control):

        self._child_controls.append(child_control)

    def add_text(self, text, sizer, sizer_args=None, insertion_index=-1, top=True):

        text_item = Text(text)
        self._text_items["top" if top else "bottom"].append(text_item)
        text_sizer = text_item.get_sizer()
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, text_sizer, *args)
        else:
            sizer.Add(text_sizer, *args)

    def add_section(self, section_id, title=""):

        section = PanelSection(self, title)
        self._sections[section_id] = section

        return section

    def insert_section(self, section_id, title="", index=0, update=True):

        section = PanelSection(self, title, index)
        self._sections[section_id] = section

        if update and self._is_expanded:
            self.update_parent()
            self._sizer.Layout()

        return section

    def remove_section(self, section_id):

        section = self._sections[section_id]
        del self._sections[section_id]
        self._section_sizer.Remove(section.get_sizer())
        section.destroy()

        if self._is_expanded:
            self.update_parent()
            self._sizer.Layout()

    def get_sections(self):

        return self._sections.values()

    def get_section(self, section_id):

        return self._sections[section_id]

    def show_section(self, section_id, show=True, update=True):

        section = self._sections[section_id]
        section.show(show)

        if self._is_expanded and update:
            self.GetParent().Refresh()
            self._sizer.Layout()

    def show_top_controls(self, show=True, update=True):

        if self._are_top_ctrls_shown == show:
            return

        if self._is_expanded:
            self._sizer.Show(1, show)

        self._are_top_ctrls_shown = show

        if self._is_expanded and update:
            self.GetParent().Refresh()
            self._sizer.Layout()

    def show_bottom_controls(self, show=True, update=True):

        if self._are_bottom_ctrls_shown == show:
            return

        if self._is_expanded:
            self._sizer.Show(4, show)

        self._are_bottom_ctrls_shown = show

        if self._is_expanded and update:
            self.GetParent().Refresh()
            self._sizer.Layout()

    def get_clipping_rect(self):
        """
        Return Rect to which the drawing of this panel will be restricted.

        Override in derived class.

        """

        return

    def __draw(self, event):

        panel_rect = self.GetRect()
        panel_rect.y = 0
        clipping_rect = self.get_clipping_rect()

        dc = wx.AutoBufferedPaintDCFactory(self)

        if clipping_rect and not clipping_rect.Intersects(panel_rect):
            return

        if clipping_rect:
            dc.ClippingRect = clipping_rect

        extent = "expanded" if self._is_expanded else "collapsed"

        if self._is_expanded:
            width, height = panel_rect.size
            h_t = self._heights["top"]
            h_b = self._heights["bottom"]
            pen = wx.Pen(wx.Colour(), 1, wx.TRANSPARENT)
            brush = wx.Brush(self._main_color)
            dc.SetPen(pen)
            dc.SetBrush(brush)
            dc.DrawRectangle(0, h_t, width, height - h_t - h_b)
            dc.DrawBitmap(self._bitmaps["top"], 0, 0)
            dc.DrawBitmap(self._bitmaps["bottom"], 0, height - h_b)
        else:
            dc.DrawBitmap(self._bitmaps["collapsed"], 0, 0)

        header_back = self._bitmaps["header_back_%s" % extent]
        x, y, w, h = self._header_rect
        dc.DrawBitmap(header_back, x, y)
        dc.SetFont(Fonts.get("default"))
        dc.DrawLabel(self._header_text, self._header_rect, wx.ALIGN_CENTER)
        dc.DrawBitmap(self._header_bitmaps[extent], x, y)

        if self._has_mouse:
            dc.DrawBitmap(self._bottom_hilited, * self._bottom_rect.GetPosition())
            arrow = self._gfx["arrows"][extent]["hilited"]
        else:
            arrow = self._gfx["arrows"][extent]["normal"]

        dc.DrawBitmap(arrow, *self._arrow_pos)

        if not self._is_expanded:
            return

        dc.SetPen(wx.NullPen)

        if self._are_top_ctrls_shown:
            for item in self._text_items["top"]:
                sizer = item.get_sizer()
                x, y = sizer.GetPosition()
                dc.DrawLabel(item.get(), wx.Rect(x, y, 0, 0))

        if self._are_bottom_ctrls_shown:
            for item in self._text_items["bottom"]:
                sizer = item.get_sizer()
                x, y = sizer.GetPosition()
                dc.DrawLabel(item.get(), wx.Rect(x, y, 0, 0))

        for section in self._sections.itervalues():
            section.draw(dc, clipping_rect)

    def __on_size(self, event):

        if not self._is_finalized:
            return

        w, h = self.GetSize()
        self._bottom_rect.y = h - self._heights["bottom_hilited"]
        self._arrow_pos.y = h - self._heights["arrow"]

    def __on_enter(self, event=None):

        self.Bind(wx.EVT_MOTION, self.__on_motion)
        self.SetCursor(Cursors.get("drag"))

    def __on_leave(self, event=None):

        self.Unbind(wx.EVT_MOTION)
        self._has_mouse = False
        self._is_clicked = False
        self.RefreshRect(self._bottom_rect)
        self.SetCursor(wx.NullCursor)

    def __on_motion(self, event):

        mouse_pos = event.GetPosition()
        has_mouse = self._bottom_rect.Contains(mouse_pos)

        if self._has_mouse != has_mouse:
            self.RefreshRect(self._bottom_rect)
            self._has_mouse = has_mouse

        show_drag_cursor = not self._has_mouse

        if show_drag_cursor:
            for section in self._sections.itervalues():
                if section.title_has_mouse(mouse_pos):
                    show_drag_cursor = False
                    break

        self.SetCursor(Cursors.get("drag") if show_drag_cursor else wx.NullCursor)

        if self._is_clicked and not has_mouse:
            self._is_clicked = False

    def __on_right_down(self, event):

        self.dispatch_event("panel_right_down", event, self)

    def __on_left_down(self, event):

        if self._has_mouse:

            self._is_clicked = True
            Mgr.do("reject_field_input")

        else:

            mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()

            for section in self._sections.itervalues():
                if section.handle_left_down(mouse_pos):
                    return

            self.dispatch_event("panel_left_down", event)

    def __on_left_doubleclick(self, event):

        mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()

        if mouse_pos.y < self._header_rect.bottom:
            self.expand(not self._is_expanded)
        else:
            self.__on_left_down(event)

    def __on_left_up(self, event):

        if self._is_clicked:
            self._is_clicked = False
            self.expand(not self._is_expanded)

    def expand(self, expand=True):

        if self._is_expanded == expand:
            return

        self._sizer.Show(1, expand)
        self._sizer.Show(2, expand)
        self._sizer.Show(3, expand)
        self._sizer.Show(4, expand)
        self._is_expanded = expand

        if expand:

            if not self._are_top_ctrls_shown:
                self._sizer.Show(1, False)

            if not self._are_bottom_ctrls_shown:
                self._sizer.Show(4, False)

            for section in self._sections.itervalues():
                section.check_collapsed_state()

        self.update_parent()
        self._sizer.Layout()

    def is_expanded(self):

        return self._is_expanded

    def update_parent(self):

        parent = self.GetParent()
        sizer = parent.GetSizer()
        sizer.Layout()
        sizer.Fit(parent)
        parent.Refresh()

    def update(self):

        self._sizer.Layout()
        self._sizer.Fit(self)

    def enable(self, enable=True):

        if self._is_enabled == enable:
            return False

        for ctrl in self._child_controls:
            ctrl.enable(enable)

        for section in self._sections.itervalues():
            section.enable(enable)

        self._is_enabled = enable

        if enable:

            self.Bind(wx.EVT_ENTER_WINDOW, self.__on_enter)
            self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)
            self.Bind(wx.EVT_LEFT_UP, self.__on_left_up)
            self.Bind(wx.EVT_LEFT_DCLICK, self.__on_left_doubleclick)
            self.refuse_focus(on_click=self.__on_left_down)

            mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
            rect = wx.Rect(0, 0, *self.GetSize())

            if rect.Contains(mouse_pos):
                self.__on_enter()

        else:

            self.Unbind(wx.EVT_ENTER_WINDOW)
            self.Unbind(wx.EVT_LEAVE_WINDOW)
            self.Unbind(wx.EVT_LEFT_DOWN)
            self.Unbind(wx.EVT_LEFT_UP)
            self.Unbind(wx.EVT_LEFT_DCLICK)
            self.__on_leave()

        return True

    def disable(self, show=True):

        if not self._is_enabled:
            return False

        for ctrl in self._child_controls:
            ctrl.disable(show)

        for section in self._sections.itervalues():
            section.disable(show)

        self._is_enabled = False
        self.Unbind(wx.EVT_ENTER_WINDOW)
        self.Unbind(wx.EVT_LEAVE_WINDOW)
        self.Unbind(wx.EVT_LEFT_DOWN)
        self.Unbind(wx.EVT_LEFT_UP)
        self.Unbind(wx.EVT_LEFT_DCLICK)
        self.__on_leave()

        return True
