from .base import *


class ToolTip(object):

    _inst = None
    _font = None
    _parent = None
    _bitmap = None
    _timer = None
    _use_timer = False

    @classmethod
    def init(cls, parent):

        cls._inst = wx.PopupWindow(parent)
        cls._font = wx.Font(8, wx.FONTFAMILY_DEFAULT,
                            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        cls._inst.Disable()
        cls._inst.Hide()
        cls._parent = parent
        cls._timer = wx.Timer(cls._inst)
        cls._inst.Bind(wx.EVT_TIMER, cls.__on_timer, cls._timer)
        cls._inst.Bind(wx.EVT_PAINT, cls.__draw)

    @classmethod
    def create_bitmap(cls, label, text_color=wx.Colour(127, 178, 229)):

        mem_dc = wx.MemoryDC()
        mem_dc.SetFont(cls._font)
        w, h = mem_dc.GetTextExtent(label)
        bitmap = wx.EmptyBitmap(w + 6, h + 6)
        mem_dc.SelectObject(bitmap)
        pen = wx.Pen(wx.Colour(153, 76, 229), 2)
        mem_dc.SetPen(pen)
        brush = wx.Brush(wx.Colour(51, 38, 76))
        mem_dc.SetBrush(brush)
        rect = wx.Rect(0, 0, w + 7, h + 7)
        mem_dc.DrawRectangleRect(rect)
        mem_dc.SetTextForeground(text_color)
        rect.SetHeight(h + 5)
        mem_dc.DrawLabel(label, rect, alignment=wx.ALIGN_CENTER)
        mem_dc.SelectObject(wx.NullBitmap)

        return bitmap

    @classmethod
    def set_bitmap(cls, bitmap):

        cls._bitmap = bitmap
        cls._inst.SetClientSize(bitmap.GetSize())

    @classmethod
    def __draw(cls, event):

        dc = wx.PaintDC(cls._inst)
        dc.DrawBitmap(cls._bitmap, 0, 0)

    @classmethod
    def __on_timer(cls, event):

        x, y = wx.GetMousePosition()
        w, h = cls._bitmap.GetSize()
        w_d, h_d = wx.GetDisplaySize()
        x = max(0, min(x, w_d - w))
        y = max(0, min(y, h_d - h))
        cls._inst.SetPosition((x, y - 21))
        cls._inst.Show()

    @classmethod
    def show(cls, bitmap, pos, use_timer=True, delay=500):

        cls.set_bitmap(bitmap)
        cls._use_timer = use_timer

        if use_timer:
            cls._timer.Start(delay, oneShot=True)
        else:
            x, y = pos
            cls._inst.SetPosition((x, y - 30))
            cls._inst.Show()

    @classmethod
    def hide(cls):

        cls._inst.Hide()

        if cls._use_timer:
            cls._timer.Stop()
            cls._use_timer = False
