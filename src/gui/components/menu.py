from ..base import *


class MenuBar(wx.PyPanel, FocusResetter):

    def __init__(self, parent, pos, width, focus_receiver=None):

        image = Cache.load("image", os.path.join(GFX_PATH, "statusbar_bg.png"))
        self._height = h = image.GetHeight()
        bitmap = image.AdjustChannels(1.3, 1.3, 1.3).Scale(width, h).ConvertToBitmap()

        wx.PyPanel.__init__(self, parent, pos=pos, size=bitmap.GetSize())
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus()

        self._bitmap = bitmap
        self._commands = {}
        self._rects = {}
        self._menus = {}
        self._menu_x = 0
        self._menu_open = False
        self._is_enabled = True
        self._rect_under_mouse = None

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.__draw)
        self.Bind(wx.EVT_MOTION, self.__on_motion)
        self.Bind(wx.EVT_LEFT_DOWN, self.__show_popup)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.SetDimension(0, 0, *self.GetSize())
        self.SetSizer(sizer)

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        dc.DrawBitmap(self._bitmap, 0, 0)
        dc.SetFont(Fonts.get("default"))
        rects = self._rects

        if self._rect_under_mouse:
            dc.SetPen(wx.Pen(wx.Colour(80, 80, 120), 1, wx.SOLID))
            dc.SetBrush(wx.Brush(wx.Colour(150, 150, 255)))
            dc.DrawRectangleRect(rects[self._rect_under_mouse])

        for menu_name, rect in rects.iteritems():
            dc.DrawLabel(menu_name, rect, wx.ALIGN_CENTRE)

    def __on_motion(self, event):

        if not self._is_enabled:
            return

        mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
        prev_rect = self._rect_under_mouse
        self._rect_under_mouse = None

        for menu_name, rect in self._rects.iteritems():
            if rect.Contains(mouse_pos):
                self._rect_under_mouse = menu_name
                break

        if self._rect_under_mouse != prev_rect:
            self.Refresh()

    def __on_leave(self, event):

        if self._menu_open:
            return

        self._rect_under_mouse = None
        self.Refresh()

    def __show_popup(self, event):

        if not self._is_enabled:
            return

        mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()

        def notify_menu_close():

            self._menu_open = False
            self._rect_under_mouse = None
            self.Refresh()

        for menu_name, rect in self._rects.iteritems():
            if rect.Contains(mouse_pos):
                menu = self._menus[menu_name]
                self._rect_under_mouse = menu_name
                self.Refresh()
                self._menu_open = True
                self.PopupMenuXY(menu, rect.x, rect.y + rect.height)
                wx.CallAfter(notify_menu_close)
                break

    def add_menu(self, menu_name):

        mem_dc = wx.MemoryDC()
        w, h = mem_dc.GetTextExtent(menu_name)
        w += 20
        rect = wx.Rect(self._menu_x, 0, w, self._height)
        self._rects[menu_name] = rect
        menu = wx.Menu()
        self._menus[menu_name] = menu
        self._menu_x += w

    def add_menu_item(self, menu_name, item_label, item_command, hotkey=None):

        item = self._menus[menu_name].Append(-1, item_label)
        self.Bind(wx.EVT_MENU, lambda event: item_command(), item)

        if hotkey is not None:
            self._commands[hotkey] = item_command

    def add_menu_item_separator(self, menu_name):

        self._menus[menu_name].AppendSeparator()

    def enable(self, enable=True):

        if self._is_enabled == enable:
            return

        self._is_enabled = enable

    def disable(self, show=True):

        if not self._is_enabled:
            return

        self._is_enabled = False

    def is_enabled(self):

        return self._is_enabled

    def handle_hotkey(self, hotkey):

        if hotkey in self._commands:
            self._commands[hotkey]()
