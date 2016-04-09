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
        self._menu_names = {}
        self._menu_items = {}
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
        names = self._menu_names

        if self._rect_under_mouse:
            dc.SetPen(wx.Pen(wx.Colour(80, 80, 120), 1, wx.SOLID))
            dc.SetBrush(wx.Brush(wx.Colour(150, 150, 255)))
            dc.DrawRectangleRect(rects[self._rect_under_mouse])

        for menu_id, rect in rects.iteritems():
            dc.DrawLabel(names[menu_id], rect, wx.ALIGN_CENTRE)

    def __on_motion(self, event):

        if not self._is_enabled:
            return

        mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
        prev_rect = self._rect_under_mouse
        self._rect_under_mouse = None

        for menu_id, rect in self._rects.iteritems():
            if rect.Contains(mouse_pos):
                self._rect_under_mouse = menu_id
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

        for menu_id, rect in self._rects.iteritems():
            if rect.Contains(mouse_pos):
                menu = self._menus[menu_id]
                self._rect_under_mouse = menu_id
                self.Refresh()
                self._menu_open = True
                self.PopupMenuXY(menu, rect.x, rect.y + rect.height)
                wx.CallAfter(notify_menu_close)
                break

    def add_menu(self, menu_id, menu_name, parent_menu_id=None):

        if not parent_menu_id:
            mem_dc = wx.MemoryDC()
            w, h = mem_dc.GetTextExtent(menu_name)
            w += 20
            rect = wx.Rect(self._menu_x, 0, w, self._height)
            self._menu_x += w
            self._rects[menu_id] = rect
            self._menu_names[menu_id] = menu_name

        menu = wx.Menu()
        self._menus[menu_id] = menu

        if parent_menu_id:
            self._menus[parent_menu_id].AppendMenu(-1, menu_name, menu)

    def add_menu_item(self, menu_id, item_id, item_label, item_command, hotkey=None):

        item = self._menus[menu_id].Append(-1, item_label)
        self.Bind(wx.EVT_MENU, lambda event: item_command(), item)
        self._menu_items[item_id] = item

        if hotkey is not None:
            self._commands[hotkey] = item_command

    def add_menu_item_separator(self, menu_id):

        self._menus[menu_id].AppendSeparator()

    def remove_menu_item(self, menu_id, item_id):

        item = self._menu_items[item_id]
        self.Unbind(wx.EVT_MENU, item)
        del self._menu_items[item_id]
        self._menus[menu_id].DestroyItem(item)

    def rename_menu_item(self, item_id, item_label):

        item = self._menu_items[item_id]
        item.SetItemLabel(item_label)

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
