from ..base import *


class ViewportBorder(wx.Panel):

    def __init__(self, parent, pos, size, rects, default_color):

        wx.Panel.__init__(self, parent, -1, pos, size)

        self._rects = rects
        self._color = self._default_color = default_color
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.__draw)

    def set_color(self, color=None):

        if color is None:
            color = self._default_color

        if color == self._color:
            return

        self._color = color

        for rect in self._rects:
            self.RefreshRect(rect)

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        dc.SetPen(wx.Pen(wx.Colour(), 1, wx.TRANSPARENT))
        dc.SetBrush(wx.Brush(self._color))
        dc.DrawRectangleList(self._rects)


class Viewport(wx.Window, FocusResetter):

    def __init__(self, border_width, parent, pos, size, name, focus_receiver=None):

        self._border_width = b_w = border_width

        wx.Window.__init__(self, parent=parent, pos=pos +
                           wx.Point(b_w, b_w), size=size, name=name)
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus(reject_field_input=True)

        w, h = size
        w += 2 * b_w
        h += 2 * b_w
        rects = []
        rect = wx.Rect(0, 0, w, b_w)
        rects.append(rect)
        rect = wx.Rect(0, h - b_w, w, b_w)
        rects.append(rect)
        rect = wx.Rect(0, b_w, b_w, h - 2 * b_w)
        rects.append(rect)
        rect = wx.Rect(w - b_w, b_w, b_w, h - 2 * b_w)
        rects.append(rect)
        default_color = wx.Colour(106, 101, 141)
        self._border = ViewportBorder(
            parent, pos, (w, h), rects, default_color)
        self._border.Disable()

        self.SetBackgroundColour(wx.Colour(0, 0, 0))

        self._has_focus = {"": False, "uv_window": False}

        Mgr.accept("set_viewport_border_color", self.__set_border_color)
        Mgr.accept("reset_viewport_border_color", self.__reset_border_color)

    def get_size(self):

        return self.GetClientSize()

    def get_callback(self):

        def viewport_callback(viewport_name, has_focus):

            if self._has_focus[viewport_name] != has_focus:

                self._has_focus[viewport_name] = has_focus

                if has_focus:
                    Mgr.do("reject_field_input")
                    Mgr.set_global("active_viewport", viewport_name)

        return viewport_callback

    def get_border_width(self):

        return self._border_width

    def __set_border_color(self, color):

        self._border.set_color(wx.Colour(*color))

    def __reset_border_color(self):

        self._border.set_color()
