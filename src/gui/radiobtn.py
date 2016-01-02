from .base import *


class RadioButton(wx.PyPanel, FocusResetter):

    _bitmap = None
    _rect = None

    @classmethod
    def init(cls):

        path = os.path.join(GFX_PATH, "radio_btn.png")
        cls._bitmap = wx.Bitmap(path)
        w, h = cls._bitmap.GetSize()
        cls._rect = wx.Rect(0, 0, w, h)

    def __init__(self, parent, btn_id, group, focus_receiver=None):

        wx.PyPanel.__init__(self, parent, size=self._bitmap.GetSize())
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus(on_click=self.__on_left_down)

        self._id = btn_id
        self._group = group
        self._is_clicked = False
        self._is_selected = False
        self._command = None

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.__draw)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)
        self.Bind(wx.EVT_LEFT_UP, self.__on_left_up)

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        pen = wx.Pen(wx.Colour(), 1, wx.TRANSPARENT)
        dc.SetPen(pen)
        dc.SetBrush(wx.Brush(self._group.get_back_color()))
        dc.DrawRectangleRect(self._rect)

        if self._is_selected:
            dc.SetBrush(wx.Brush(self._group.get_dot_color()))
            dc.DrawRectangleRect(self._rect)

        dc.DrawBitmap(self._bitmap, 0, 0)

    def __on_leave(self, event):

        self._is_clicked = False

    def __on_left_down(self, event):

        self._is_clicked = True

    def __on_left_up(self, event):

        if not self._is_clicked:
            return

        self._is_clicked = False

        if self._is_selected:
            return

        self._group.set_selected_button(self._id)

        if self._command:
            self._command()

    def set_command(self, command=None):

        self._command = command

    def set_selected(self, is_selected=True):

        if self._is_selected == is_selected:
            return

        self._is_selected = is_selected
        self.Refresh()

    def enable(self, enable=True):

        if enable:
            for disabler in self._group.get_disablers():
                if disabler():
                    return

        self.Enable(enable)

    def disable(self, show=True):

        self.Disable()


class RadioButtonGroup(BaseObject):

    _default_dot_color = None
    _default_back_color = None

    @classmethod
    def init(cls, default_dot_color, default_back_color):

        cls._default_dot_color = default_dot_color
        cls._default_back_color = default_back_color

        RadioButton.init()

    def __init__(self, dot_color=None, back_color=None, focus_receiver=None):

        self._btns = {}
        self._selected_btn_id = None
        self._disablers = {}
        self._dot_color = dot_color if dot_color else self._default_dot_color
        self._back_color = back_color if back_color else self._default_back_color
        self._focus_receiver = focus_receiver

    def add_button(self, btn_id, parent):

        btn = RadioButton(parent, btn_id, self, self._focus_receiver)
        self._btns[btn_id] = btn

        return btn

    def get_button_count(self):

        return len(self._btns)

    def set_selected_button(self, btn_id=None):

        if self._selected_btn_id == btn_id:
            return

        if self._selected_btn_id is not None:
            self._btns[self._selected_btn_id].set_selected(False)

        self._selected_btn_id = btn_id

        if btn_id is not None:
            self._btns[btn_id].set_selected()

    def get_selected_button(self):

        return self._selected_btn_id

    def set_button_command(self, btn_id, command):

        self._btns[btn_id].set_command(command)

    def set_dot_color(self, color=None):

        self._dot_color = color if color else self._default_dot_color

    def get_dot_color(self):

        return self._dot_color

    def set_back_color(self, color=None):

        self._back_color = color if color else self._default_back_color

    def get_back_color(self):

        return self._back_color

    def add_disabler(self, disabler_id, disabler):

        self._disablers[disabler_id] = disabler

    def remove_disabler(self, disabler_id):

        del self._disablers[disabler_id]

    def get_disablers(self):

        return self._disablers.itervalues()

    def enable(self, enable=True):

        if enable:
            for disabler in self._disablers.itervalues():
                if disabler():
                    return

        for btn in self._btns.itervalues():
            btn.Enable(enable)

    def disable(self, show=True):

        for btn in self._btns.itervalues():
            btn.Disable()
