from .base import *


class ColorPickerCtrl(wx.PyWindow, BaseObject, FocusResetter):

    _size = None
    _bitmaps = {"border": {}}
    _color_rect = None

    @classmethod
    def init(cls, bitmap_paths):

        pnl_bitmap_paths = bitmap_paths["panel"]
        tlbr_bitmap_paths = bitmap_paths["toolbar"]
        offset_x = Cache.load("image", pnl_bitmap_paths["left"]).GetWidth()
        offset_y = Cache.load("image", pnl_bitmap_paths["top"]).GetHeight()
        w, height = Cache.load("bitmap", tlbr_bitmap_paths["left"]).GetSize()
        width = height - (offset_y - offset_x) * 2
        size = (width, height)
        cls._size = wx.Size(*size)
        l = height - offset_y * 2
        cls._color_rect = wx.Rect(offset_x, offset_y, l, l)

        def create_box_border(parent_type):

            return create_border(bitmap_paths[parent_type], size, parent_type)

        for parent_type in ("toolbar", "panel"):
            gfx_id = ("border", parent_type, size)
            bitmap = Cache.create(
                "bitmap", gfx_id, lambda: create_box_border(parent_type))
            cls._bitmaps["border"][parent_type] = bitmap

        x, y, w, h = cls._color_rect
        rect = wx.Rect(0, 0, w, h)

        bitmap = wx.EmptyBitmap(w, h)
        mem_dc = wx.MemoryDC(bitmap)
        mem_dc.SetPen(wx.Pen(wx.Colour(), 1, wx.TRANSPARENT))
        mem_dc.SetBrush(wx.Brush(wx.Colour(51, 38, 76)))
        mem_dc.DrawRectangleRect(rect)
        lines = [(0, 0, w, h), (0, h, w, 0)]
        mem_dc.DrawLineList(lines, wx.Pen(wx.Colour(101, 88, 126), 3))
        mem_dc.SelectObject(wx.NullBitmap)
        cls._bitmaps["none"] = bitmap

        bitmap = wx.EmptyBitmap(w, h)
        w //= 2
        h //= 2
        mem_dc.SelectObject(bitmap)
        rects = [(0, 0, w, h), (w, 0, w, h), (0, h, w, h), (w, h, w, h)]
        brushes = [wx.Brush(wx.Colour(255, 128)), wx.Brush(wx.Colour(0, 255, 128)),
                   wx.Brush(wx.Colour(0, 128, 255)), wx.Brush(wx.Colour(255, 0, 128))]
        mem_dc.DrawRectangleList(rects, wx.Pen(
            wx.Colour(), 1, wx.TRANSPARENT), brushes)
        mem_dc.SelectObject(wx.NullBitmap)
        cls._bitmaps["multiple"] = bitmap

        bitmap = bitmap.GetSubBitmap(wx.Rect(0, 0, w * 2, h * 2))
        bitmap = bitmap.ConvertToImage().Blur(10).ConvertToBitmap()
        mem_dc.SelectObject(bitmap)
        font = wx.Font(15, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        mem_dc.SetFont(font)
        mem_dc.DrawLabel("?", rect, wx.ALIGN_CENTER)
        mem_dc.SelectObject(wx.NullBitmap)
        bitmap = bitmap.ConvertToImage().Blur(2).ConvertToBitmap()
        mem_dc.SelectObject(bitmap)
        font = wx.Font(14, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        mem_dc.SetTextForeground(wx.Colour(255, 255, 0))
        mem_dc.SetFont(font)
        mem_dc.DrawLabel("?", rect, wx.ALIGN_CENTER)
        mem_dc.SelectObject(wx.NullBitmap)
        cls._bitmaps["random"] = bitmap

    def __init__(self, parent, command, parent_type="toolbar", focus_receiver=None):

        wx.PyWindow.__init__(self, parent)
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus()

        self._parent_type = parent_type
        self._command = command
        self._color = None
        self._show_color = "single"
        self._is_clicked = False
        self._has_mouse = False
        self._disablers = {}

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.__draw)
        self.Bind(wx.EVT_ENTER_WINDOW, self.__on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self.__on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.__on_left_up)

        if parent_type == "toolbar":

            def set_back_bitmap():

                self._back_bitmap = parent.get_bitmap().GetSubBitmap(self.GetRect())

            wx.CallAfter(set_back_bitmap)

    def DoGetBestSize(self):

        return self._size

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)

        if self._parent_type == "toolbar":
            dc.DrawBitmap(self._back_bitmap, 0, 0)

        if self._show_color == "single":

            if self._color:
                dc.SetPen(wx.Pen(wx.Colour(), 1, wx.TRANSPARENT))
                dc.SetBrush(wx.Brush(self._color))
                dc.DrawRectangleRect(self._color_rect)

        else:

            dc.DrawBitmap(self._bitmaps[self._show_color],
                          *self._color_rect.GetPosition())

        dc.DrawBitmap(self._bitmaps["border"][self._parent_type], 0, 0)

    def __on_enter(self, event):

        self.Bind(wx.EVT_MOTION, self.__on_motion)

    def __on_leave(self, event):

        self.Unbind(wx.EVT_MOTION)

    def __on_motion(self, event):

        has_mouse = self._color_rect.Contains(event.GetPosition())

        if self._has_mouse != has_mouse:
            self.SetCursor(
                wx.NullCursor if not has_mouse else Cursors.get("dropper"))
            self._has_mouse = has_mouse

        if self._is_clicked and not has_mouse:
            self._is_clicked = False

    def __on_left_down(self, event):

        if self._has_mouse:
            self._is_clicked = True
            Mgr.do("accept_field_input")

        self.reset_focus()

    def __on_left_up(self, event):

        if not self._is_clicked:
            return

        self._is_clicked = False

        init_color = wx.NullColour if self._color is None else self._color
        color = wx.GetColourFromUser(self, init_color, "Object color")

        if color.IsOk() and (self._color != color or self._show_color in ("multiple", "random")):
            self._command(color)

    def show_color(self, show="single"):

        if self._show_color == show:
            return

        self._show_color = show
        self.RefreshRect(self._color_rect)

    def set_color(self, color_values):

        rgb = Mgr.convert_from_remote_format("color", color_values)
        color = wx.Colour(*[int(round(x)) for x in rgb]) if rgb else None

        if self._color == color:
            return

        self._color = color
        self.RefreshRect(self._color_rect)

    def get_color(self):

        return self._color

    def add_disabler(self, disabler_id, disabler):

        self._disablers[disabler_id] = disabler

    def remove_disabler(self, disabler_id):

        del self._disablers[disabler_id]

    def enable(self, enable=True):

        if enable:
            for disabler in self._disablers.itervalues():
                if disabler():
                    return

        self.Enable(enable)

    def disable(self, show=True):

        self.Enable(False)
