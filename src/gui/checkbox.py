from .base import *


class CheckBox(wx.PyPanel, FocusResetter):

    _bitmaps = {"border": {}, "checkmark": {}}
    _default_mark_color = None
    _default_back_color = None
    _checkmark_rect = None

    @classmethod
    def init(cls, bitmap_paths, default_mark_color, default_back_color):

        path = os.path.join(GFX_PATH, "check_mark.png")
        checkmark_img = wx.Image(path)

        if not checkmark_img.HasAlpha():
            checkmark_img.InitAlpha()

        cls._bitmaps["checkmark"][None] = checkmark_img

        for parent_type in ("toolbar", "panel"):

            path = os.path.join(GFX_PATH, "%s_checkbox.png" % parent_type)
            checkbox_img = wx.Image(path)

            if not checkbox_img.HasAlpha():
                checkbox_img.InitAlpha()

            cls._bitmaps["border"][
                parent_type] = checkbox_img.ConvertToBitmap()

        cb_w, cb_h = checkbox_img.GetSize()
        cm_w, cm_h = checkmark_img.GetSize()
        offset_x = (cb_w - cm_w) // 2
        offset_y = (cb_h - cm_h) // 2
        cls._checkmark_rect = wx.Rect(offset_x, offset_y, cm_w, cm_w)

        cls._default_mark_color = default_mark_color
        cls._default_back_color = default_back_color

    def __init__(self, parent, command, mark_color=None, back_color=None,
                 parent_type="toolbar", focus_receiver=None):

        wx.PyPanel.__init__(self, parent, size=self._bitmaps[
                            "border"][parent_type].GetSize())
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus(on_click=self.__on_left_down)

        self._parent_type = parent_type
        self._is_clicked = False
        self._is_checked = True
        self._disablers = {}
        self._command = command
        self._mark_color = mark_color if mark_color else self._default_mark_color
        self._back_color = back_color if back_color else self._default_back_color

        if self._mark_color not in self._bitmaps["checkmark"]:
            checkmark_img = self._bitmaps["checkmark"][None]
            r, g, b = self._mark_color
            checkmark_img = checkmark_img.AdjustChannels(
                r / 255., g / 255., b / 255.)
            self._bitmaps["checkmark"][
                self._mark_color] = checkmark_img.ConvertToBitmap()

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.__draw)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)
        self.Bind(wx.EVT_LEFT_UP, self.__on_left_up)

        if parent_type == "toolbar":

            def set_back_bitmap():

                self._back_bitmap = parent.get_bitmap().GetSubBitmap(self.GetRect())

            wx.CallAfter(set_back_bitmap)

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)

        if self._parent_type == "toolbar":
            dc.DrawBitmap(self._back_bitmap, 0, 0)

        pen = wx.Pen(wx.Colour(), 1, wx.TRANSPARENT)
        brush = wx.Brush(self._back_color)
        dc.SetPen(pen)
        dc.SetBrush(brush)
        dc.DrawRectangleRect(self._checkmark_rect)
        dc.DrawBitmap(self._bitmaps["border"][self._parent_type], 0, 0)

        if self._is_checked:
            x, y = self._checkmark_rect.GetPosition()
            dc.DrawBitmap(self._bitmaps["checkmark"][self._mark_color], x, y)

    def __on_leave(self, event):

        self._is_clicked = False

    def __on_left_down(self, event):

        self._is_clicked = True

    def __on_left_up(self, event):

        if self._is_clicked:
            self._is_clicked = False
            self._is_checked = not self._is_checked
            self.Refresh()
            self._command(self._is_checked)

    def set_checkmark_color(self, color=None):

        self._mark_color = color if color else self._default_mark_color

        if self._mark_color not in self._bitmaps["checkmark"]:
            checkmark_img = self._bitmaps["checkmark"][None]
            r, g, b = self._mark_color
            checkmark_img = checkmark_img.AdjustChannels(
                r / 255., g / 255., b / 255.)
            self._bitmaps["checkmark"][
                self._mark_color] = checkmark_img.ConvertToBitmap()

    def check(self, check=True):

        self._is_checked = check
        self.Refresh()

    def is_checked(self):

        return self._is_checked

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

        self.Disable()
