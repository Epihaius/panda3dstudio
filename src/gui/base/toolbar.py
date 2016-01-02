from .base import *
from .mgr import GUIManager as Mgr
from .focus_resetter import FocusResetter


class ToolSeparator(object):

    def __init__(self, bitmap_path):

        self._bitmap = Cache.load("bitmap", bitmap_path)
        self._sizer = wx.BoxSizer()
        self._sizer.Add(self._bitmap.GetSize())

    def get_bitmap(self):

        return self._bitmap

    def get_sizer(self):

        return self._sizer


class BasicToolbar(wx.PyPanel, FocusResetter):

    def __init__(self, parent, pos, bitmap, focus_receiver=None):

        wx.PyPanel.__init__(self, parent, pos=pos, size=bitmap.GetSize())
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus()

        self._bitmap = bitmap
        self._text_items = []
        self._separators = []

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.__draw)

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        dc.DrawBitmap(self._bitmap, 0, 0)
        dc.SetFont(Fonts.get("default"))

        for item in self._text_items:
            sizer = item.get_sizer()
            x, y = sizer.GetPosition()
            dc.DrawLabel(item.get(), wx.Rect(x, y, 0, 0))

        for separator in self._separators:
            sizer = separator.get_sizer()
            x, y = sizer.GetPosition()
            dc.DrawBitmap(separator.get_bitmap(), x, y)

    def add_text(self, text, sizer, sizer_args=None, insertion_index=-1):

        text_item = Text(text)
        self._text_items.append(text_item)
        text_sizer = text_item.get_sizer()
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, text_sizer, *args)
        else:
            sizer.Add(text_sizer, *args)

    def add_separator(self, bitmap_path, insertion_index=-1):

        separator = ToolSeparator(bitmap_path)
        self._separators.append(separator)
        sep_sizer = separator.get_sizer()
        sizer = self.GetSizer()

        if insertion_index > -1:
            sizer.Insert(insertion_index, sep_sizer,
                         0, wx.ALIGN_CENTER_VERTICAL)
        else:
            sizer.Add(sep_sizer, 0, wx.ALIGN_CENTER_VERTICAL)

        return separator

    def get_bitmap(self):

        return self._bitmap

    def show(self):

        return self.Show()

    def hide(self):

        return self.Hide()


class Toolbar(BasicToolbar):

    def __init__(self, parent, pos, width, focus_receiver=None):

        image = Cache.load("image", os.path.join(GFX_PATH, "toolbar_bg.png"))
        h = image.GetHeight()
        bitmap = image.Scale(width, h).ConvertToBitmap()

        BasicToolbar.__init__(self, parent, pos, bitmap, focus_receiver)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.SetDimension(0, 0, *self.GetSize())
        self.SetSizer(sizer)


class ToolbarSpinner(Toolbar):

    def __init__(self, owner, parent, pos, focus_receiver=None):

        self._arrow_bitmaps = {}

        for direction in ("up", "down"):
            for state in ("normal", "hilited", "active"):
                path = os.path.join(
                    GFX_PATH, "arrow_%s_%s.png" % (direction, state))
                bitmap = Cache.load("bitmap", path)
                self._arrow_bitmaps.setdefault(direction, {})[state] = bitmap

        w_arrow, h_arrow = bitmap.GetSize()

        path = os.path.join(GFX_PATH, "toolbar_separator.png")
        sep_bitmap = Cache.load("bitmap", path)
        w = sep_bitmap.GetWidth()
        width = w_arrow + w + 4

        Toolbar.__init__(self, parent, pos, width, focus_receiver)
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus(on_click=self.__on_left_down)

        bitmap = self.get_bitmap()
        mem_dc = wx.MemoryDC(bitmap)
        mem_dc.DrawBitmap(sep_bitmap, width - w, 0)
        mem_dc.SelectObject(wx.NullBitmap)
        self._height = bitmap.GetHeight()

        self._arrow_pos = {"up": (2, 3), "down": (
            2, self._height - h_arrow - 3)}
        self._spinning = False
        self._spin_start_y = 0
        self._spin = 0

        self._owner = owner
        self._directions = ("up", "down")
        self._is_clicked = dict((d, False) for d in self._directions)
        self._is_hilited = dict((d, False) for d in self._directions)

        self.Bind(wx.EVT_PAINT, self.__draw)
        self.Bind(wx.EVT_ENTER_WINDOW, self.__on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)
        self.Bind(wx.EVT_LEFT_DCLICK, self.__on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.__on_left_up)
        self.Bind(wx.EVT_MOUSE_CAPTURE_CHANGED, self.__on_release_mouse)

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        dc.DrawBitmap(self.get_bitmap(), 0, 0)

        for direction in self._directions:
            is_clicked = self._is_clicked[direction]
            is_hilited = self._is_hilited[direction]
            state = "active" if is_clicked else (
                "hilited" if is_hilited else "normal")
            dc.DrawBitmap(self._arrow_bitmaps[direction][
                          state], *self._arrow_pos[direction])

    def __on_enter(self, event=None):

        self.Bind(wx.EVT_MOTION, self.__on_motion)

    def __on_leave(self, event=None):

        self.Unbind(wx.EVT_MOTION)

        self._is_hilited = dict((d, False) for d in self._directions)
        self._is_clicked = dict((d, False) for d in self._directions)
        self.Refresh()

    def __on_motion(self, event):

        mouse_y = event.GetPosition().y

        if self.HasCapture():

            x_m, y_m = wx.GetMousePosition()
            x, y = self.GetScreenPosition()
            h = wx.GetDisplaySize()[1]

            if y_m == 0:
                self.WarpPointer(x_m - x, h - y - 2)  # does not work on Mac
                self._spin_start_y += h
                return
            elif y_m == h - 1:
                self.WarpPointer(x_m - x, -y + 2)  # does not work on Mac
                self._spin_start_y -= h
                return

            mouse_dist = mouse_y - self._spin_start_y
            spin = abs(mouse_dist) // self._height * \
                (-1 if mouse_dist < 0 else 1)

            if spin != self._spin:
                self._spinning = True
                self._owner.rotate(self._spin - spin)
                self._spin = spin

            return

        hilited_direction = "up" if mouse_y < self._height // 2 else "down"
        other_direction = "down" if hilited_direction == "up" else "up"

        if not self._is_hilited[hilited_direction]:
            self._is_hilited[other_direction] = False
            self._is_clicked[other_direction] = False
            self._is_hilited[hilited_direction] = True
            self.Refresh()

    def __on_left_down(self, event):

        self.Unbind(wx.EVT_ENTER_WINDOW)
        self.Unbind(wx.EVT_LEAVE_WINDOW)
        self.CaptureMouse()

        mouse_y = event.GetPosition().y
        direction = "up" if mouse_y < self._height // 2 else "down"
        self._is_clicked[direction] = True
        self._spinning = False
        self._spin_start_y = mouse_y
        self._spin = 0
        self.Refresh()

        Mgr.do("reject_field_input")

    def __on_left_up(self, event):

        mouse_y = event.GetPosition().y
        direction = "up" if mouse_y < self._height // 2 else "down"

        if self._is_clicked[direction]:

            if self._spinning:
                self._spinning = False
            else:
                self._owner.rotate(1 if direction == "up" else -1)

            self._is_clicked[direction] = False
            self.Refresh()

        if self.HasCapture():
            self.ReleaseMouse()

    def __on_release_mouse(self, event):

        self._is_clicked = dict((d, False) for d in self._directions)
        self.Bind(wx.EVT_ENTER_WINDOW, self.__on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)

        mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
        rect = self.GetRect()
        rect.SetPosition(wx.Point())

        if rect.Contains(mouse_pos):
            self.__on_enter()
        else:
            self.__on_leave()

        self.Refresh()


class RotatingToolbars(object):

    def __init__(self, parent, spinner_pos, focus_receiver=None):

        self._toolbars = {}
        self._toolbar_ids = collections.deque()
        self._active_toolbar_id = ""
        self._spinner = ToolbarSpinner(
            self, parent, spinner_pos, focus_receiver)

    def get_spinner_width(self):

        return self._spinner.GetSize()[0]

    def add_toolbar(self, toolbar_id, toolbar):

        if self._toolbars:
            toolbar.Hide()
        else:
            self._active_toolbar_id = toolbar_id

        self._toolbar_ids.append(toolbar_id)
        self._toolbars[toolbar_id] = toolbar

    def setup(self):

        for toolbar in self._toolbars.itervalues():
            toolbar.setup()

    def rotate(self, direction):

        old_toolbar = self._toolbars[self._active_toolbar_id]
        self._toolbar_ids.rotate(direction)
        self._active_toolbar_id = self._toolbar_ids[0]
        toolbar = self._toolbars[self._active_toolbar_id]
        toolbar.Show()
        old_toolbar.Hide()

    def show(self):

        self._toolbars[self._active_toolbar_id].Show()
        self._spinner.Show()

    def hide(self):

        self._toolbars[self._active_toolbar_id].Hide()
        self._spinner.Hide()

    def enable(self):

        self._toolbars[self._active_toolbar_id].enable()
        self._spinner.Enable()

    def disable(self, show=True):

        self._toolbars[self._active_toolbar_id].disable(show)
        self._spinner.Disable()

    def deactivate(self):

        self._toolbars[self._active_toolbar_id].deactivate()
