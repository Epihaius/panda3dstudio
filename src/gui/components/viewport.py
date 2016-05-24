from ..base import *


class ViewportBorder(wx.Panel, FocusResetter):

    def __init__(self, parent, pos, size, default_color, focus_receiver=None):

        wx.Panel.__init__(self, parent, -1, pos, size)
        FocusResetter.__init__(self, focus_receiver)

        wx.CallAfter(lambda: self.refuse_focus())

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.__draw)

        self._color = default_color

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        dc.SetPen(wx.Pen(wx.Colour(), 1, wx.TRANSPARENT))
        dc.SetBrush(wx.Brush(self._color))
        x, y, w, h = self.GetRect()
        dc.DrawRectangle(0, 0, w, h)

    def set_color(self, color):

        self._color = color
        self.Refresh()


class ViewportBorders(object):

    def __init__(self, parent, border_width, pos, size, focus_receiver=None):

        self._borders = []
        default_color = wx.Colour(106, 101, 141)
        self._color = self._default_color = default_color

        b_w = border_width
        w, h = size
        w += 2 * b_w
        h += 2 * b_w
        border = ViewportBorder(parent, pos, (w, b_w), default_color, focus_receiver)
        self._borders.append(border)
        border = ViewportBorder(parent, pos+wx.Point(0, h - b_w), (w, b_w),
                                default_color, focus_receiver)
        self._borders.append(border)
        border = ViewportBorder(parent, pos+wx.Point(0, b_w), (b_w, h - 2 * b_w),
                                default_color, focus_receiver)
        self._borders.append(border)
        rect = wx.Rect(w - b_w, b_w, b_w, h - 2 * b_w)
        border = ViewportBorder(parent, pos+wx.Point(w - b_w, b_w), (b_w, h - 2 * b_w),
                                default_color, focus_receiver)
        self._borders.append(border)

    def set_color(self, color=None):

        if color is None:
            color = self._default_color

        if color == self._color:
            return

        self._color = color

        for border in self._borders:
            border.set_color(color)


class Viewport(wx.Panel, FocusResetter):

    def __init__(self, border_width, parent, pos, size, name, focus_receiver=None):

        self._border_width = b_w = border_width

        wx.Panel.__init__(self, parent=parent, pos=pos+wx.Point(b_w, b_w),
                           size=size, name=name)
        FocusResetter.__init__(self, focus_receiver)

        wx.CallAfter(lambda: self.refuse_focus(reject_field_input=True))

        self._borders = ViewportBorders(parent, b_w, pos, size, focus_receiver)

        self.SetBackgroundColour(wx.Colour(0, 0, 0))

        self._has_focus = {"": False, "uv_window": False}

        Mgr.accept("set_viewport_border_color", self.__set_border_color)
        Mgr.accept("reset_viewport_border_color", self.__reset_border_color)

    def get_size(self):

        return self.GetClientSize()

    def get_callback(self):

        def viewport_callback(viewport_name, has_focus):

            if viewport_name not in self._has_focus:
                return

            if self._has_focus[viewport_name] != has_focus:

                self._has_focus[viewport_name] = has_focus

                if has_focus:
                    Mgr.do("reject_field_input")
                    GlobalData["active_viewport"] = viewport_name

        return viewport_callback

    def get_border_width(self):

        return self._border_width

    def __set_border_color(self, color):

        self._borders.set_color(wx.Colour(*color))

    def __reset_border_color(self):

        self._borders.set_color()
