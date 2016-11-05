from .base import *
from .tooltip import ToolTip


class Button(wx.PyControl, FocusResetter):

    _btns = {}

    def set_hotkey(self, hotkey=None, interface_id=""):

        btns = self._btns.setdefault(interface_id, {})

        if hotkey is None:
            if self._hotkey in btns:
                del btns[self._hotkey]
        else:
            btns[hotkey] = self

        self._hotkey = hotkey

    @classmethod
    def handle_hotkey(cls, hotkey, is_repeat, interface_id=""):

        btns = cls._btns.get(interface_id, {})

        if hotkey in btns:

            btn = btns[hotkey]

            if btn.IsEnabled():

                if not is_repeat:
                    btn.press()

                return True

        return False

    @classmethod
    def remove_interface(cls, interface_id=""):

        if interface_id in cls._btns:
            del cls._btns[interface_id]

    _bitmap_paths = {}

    @classmethod
    def add_bitmap_paths(cls, bitmap_paths_id, bitmap_paths):

        cls._bitmap_paths[bitmap_paths_id] = bitmap_paths

    @classmethod
    def get_bitmap_paths(cls, bitmap_paths_id):

        return cls._bitmap_paths[bitmap_paths_id]

    @staticmethod
    def __get_alpha(img, alpha_map):

        for y in xrange(img.GetHeight()):

            row = []
            alpha_map.append(row)

            for x in xrange(img.GetWidth()):
                row.append(img.GetAlpha(x, y))

    @staticmethod
    def __create_button_icons(icon_path, bitmaps, w, h, mem_dc, icon_size=None):

        bitmaps["icons"] = {}

        if PLATFORM_ID == "Linux":
            alpha_map = []

        def create_icon(state):

            img = Cache.load("image", icon_path)

            if not img.HasAlpha():
                img.InitAlpha()

            if PLATFORM_ID == "Linux" and not alpha_map:
                get_alpha(img, alpha_map)

            if state == "disabled":
                img = img.ConvertToGreyscale().AdjustChannels(.7, .7, .7)

            icon = img.ConvertToBitmap()
            w_i, h_i = icon_size if icon_size else icon.GetSize()
            offset_x = (w - w_i) // 2
            offset_y = (h - h_i) // 2

            if PLATFORM_ID == "Linux":
                bitmap = wx.EmptyBitmap(w, h)
            else:
                bitmap = wx.EmptyBitmapRGBA(w, h)

            mem_dc.SelectObject(bitmap)
            mem_dc.DrawBitmap(icon, offset_x, offset_y)
            mem_dc.SelectObject(wx.NullBitmap)

            if PLATFORM_ID == "Linux":

                img = bitmap.ConvertToImage()
                w_i, h_i = icon.GetSize()

                if not img.HasAlpha():
                    img.InitAlpha()

                for y, row in enumerate(alpha_map):
                    for x, alpha in enumerate(row):
                        img.SetAlpha(x + offset_x, y + offset_y, alpha)

                for y in xrange(offset_y):
                    for x in xrange(w):
                        img.SetAlpha(x, y, 0)

                for y in xrange(offset_y + h_i, h):
                    for x in xrange(w):
                        img.SetAlpha(x, y, 0)

                for y in xrange(offset_y, offset_y + h_i):
                    for x in xrange(offset_x):
                        img.SetAlpha(x, y, 0)

                for y in xrange(offset_y, offset_y + h_i):
                    for x in xrange(offset_x + w_i, w):
                        img.SetAlpha(x, y, 0)

                bitmap = img.ConvertToBitmap()

            return bitmap

        for state in ("normal", "disabled"):
            gfx_id = ("icon", icon_path, state, w, h, icon_size)
            bitmaps["icons"][state] = Cache.create(
                "bitmap", gfx_id, lambda: create_icon(state))

    @classmethod
    def create_button_bitmaps(cls, icon_path, bitmap_paths, width=None,
                              icon_size=None, flat=False):

        bitmaps = {}

        parts = ("left", "center", "right")
        states = ("pressed", "active") + (() if flat else ("hilited", "disabled"))

        if icon_path.startswith("*"):
            label = icon_path.replace("*", "", 1)
        else:
            label = ""

        mem_dc = wx.MemoryDC()

        if PLATFORM_ID == "Linux":
            all_states = ("normal", "hilited", "pressed", "active", "disabled")
            alpha_maps = dict((state, dict((part, []) for part in parts)) for state in all_states)

        def create_bitmap(state, w_sides=None, w=None, h=None):

            bitmap_parts = {}

            for part in ("left", "right"):

                bitmap_parts[part] = bitmap = Cache.load("bitmap", bitmap_paths[part][state])

                if PLATFORM_ID == "Linux" and not alpha_maps[state][part]:

                    img = bitmap.ConvertToImage()

                    if not img.HasAlpha():
                        img.InitAlpha()

                    get_alpha(img, alpha_maps[state][part])

            center_image = Cache.load("image", bitmap_paths["center"][state])

            if not center_image.HasAlpha():
                center_image.InitAlpha()

            if w_sides is None:

                w_sides, h = bitmap_parts["left"].GetSize()
                w_sides += bitmap_parts["right"].GetWidth()

                if width is None:
                    if label:
                        mem_dc.SetFont(Fonts.get("default"))
                        w_center, h_l = mem_dc.GetTextExtent(label)
                        w = w_sides + w_center
                    else:
                        w_center = h - w_sides
                        w = h
                else:
                    w_center = width - w_sides
                    w = width

            else:

                w_center = w - w_sides

            center_image = center_image.Scale(w_center, h)
            bitmap_parts["center"] = center_image.ConvertToBitmap()

            if PLATFORM_ID == "Linux" and not alpha_maps[state]["center"]:
                get_alpha(center_image, alpha_maps[state]["center"])

            if PLATFORM_ID == "Linux":
                bitmap = wx.EmptyBitmap(w, h)
            else:
                bitmap = wx.EmptyBitmapRGBA(w, h)

            mem_dc.SelectObject(bitmap)
            x = 0

            for part in parts:
                bitmap_part = bitmap_parts[part]
                mem_dc.DrawBitmap(bitmap_part, x, 0)
                x += bitmap_part.GetWidth()

            mem_dc.SelectObject(wx.NullBitmap)

            if PLATFORM_ID == "Linux":

                img = bitmap.ConvertToImage()
                offset_x = 0

                if not img.HasAlpha():
                    img.InitAlpha()

                for part in parts:

                    bitmap_part = bitmap_parts[part]
                    alpha_map = alpha_maps[state][part]

                    for y, row in enumerate(alpha_map):
                        for x, alpha in enumerate(row):
                            img.SetAlpha(x + offset_x, y, alpha)

                    offset_x += bitmap_part.GetWidth()

                bitmap = img.ConvertToBitmap()

            return bitmap

        if flat:
            for state in ("normal", "disabled"):
                gfx_id = "pixel"
                bitmaps[state] = Cache.create("bitmap", gfx_id,
                                              lambda: wx.EmptyBitmapRGBA(1, 1))

        state = "hilited" if flat else "normal"
        paths = tuple(bitmap_paths[part][state] for part in parts)
        gfx_id = (paths, width, label)
        bitmap = Cache.create("bitmap", gfx_id, lambda: create_bitmap(state))
        bitmaps[state] = bitmap
        w, h = bitmap.GetSize()
        w_sides = Cache.load("bitmap", bitmap_paths["left"][state]).GetWidth()
        w_sides += Cache.load("bitmap", bitmap_paths["right"][state]).GetWidth()

        for state in states:
            paths = tuple(bitmap_paths[part][state] for part in parts)
            gfx_id = (paths, width, label)
            bitmaps[state] = Cache.create("bitmap", gfx_id, lambda:
                                          create_bitmap(state, w_sides, w, h))

        if icon_path and not label:
            cls.__create_button_icons(icon_path, bitmaps, w, h, mem_dc, icon_size)
        else:
            bitmaps["icons"] = None

        mem_dc.SelectObject(wx.NullBitmap)

        return bitmaps

    def __init__(self, parent, bitmaps, label="", tooltip_label="", command=None,
                 parent_type="toolbar", focus_receiver=None, pos=None):

        wx.PyControl.__init__(self, parent, style=wx.BORDER_NONE)
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus(reject_field_input=True, on_click=self._on_left_down)

        self._parent = parent
        self._parent_type = parent_type
        self._bitmaps = bitmaps
        self._label = label
        self._tooltip_label = tooltip_label
        self._hotkey = None

        if label:
            mem_dc = wx.MemoryDC()
            mem_dc.SetFont(Fonts.get("default"))
            w_l, h_l = mem_dc.GetTextExtent(label)
            w, h = bitmaps["active"].GetSize()
            offset_x = (w - w_l) // 2
            offset_y = (h - h_l) // 2
            self._label_rect = wx.Rect(offset_x, offset_y, w_l, h_l)
        else:
            self._label_rect = None

        self._is_clicked = False
        self._is_hilited = False
        self._is_active = False
        self._show_disabled_state = True
        self._disablers = {}
        self._command = command if command else lambda: None

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.Bind(wx.EVT_PAINT, self._draw)
        self.Bind(wx.EVT_ENTER_WINDOW, self._on_enter_window)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave_window)
        self.Bind(wx.EVT_LEFT_UP, self._on_left_up)

        self.SetClientSize(self.GetBestSize())

        self._has_back_bitmap = False

        if pos:
            self.SetPosition(pos)

        if tooltip_label:
            self._tooltip_bitmap = ToolTip.create_bitmap(tooltip_label)
        else:
            self._tooltip_bitmap = None

        wx.CallAfter(self._set_back_bitmap)

    def _set_back_bitmap(self):

        w, h = self.GetSize()

        def create_background():

            panel_color = self._parent.get_main_color()
            bitmap = wx.EmptyBitmap(w, h)
            mem_dc = wx.MemoryDC(bitmap)
            mem_dc.SetPen(wx.Pen(wx.Colour(), 1, wx.TRANSPARENT))
            mem_dc.SetBrush(wx.Brush(panel_color))
            mem_dc.DrawRectangle(0, 0, w, h)
            mem_dc.SelectObject(wx.NullBitmap)

            return bitmap

        if self._parent_type == "panel":
            gfx_id = ("panel_region", w, h)
            self._bitmaps["back"] = Cache.create("bitmap", gfx_id, create_background)
        else:
            self._bitmaps["back"] = self._parent.get_bitmap().GetSubBitmap(self.GetRect())

        self._has_back_bitmap = True
        self.Refresh()

    def destroy(self):

        self.Destroy()

    def DoGetBestSize(self):

        return self._bitmaps["active"].GetSize()

    def _draw(self, event):

        if not self._has_back_bitmap:
            return

        dc = wx.AutoBufferedPaintDCFactory(self)
        dc.DrawBitmap(self._bitmaps["back"], 0, 0)

        if not self.IsEnabled() and self._show_disabled_state:
            state = "disabled"
        elif self._is_clicked:
            state = "pressed"
        elif self._is_active:
            state = "active"
        else:
            state = "hilited" if self._is_hilited else "normal"

        dc.DrawBitmap(self._bitmaps[state], 0, 0)
        icons = self._bitmaps["icons"]

        if self._label:
            dc.SetFont(Fonts.get("default"))
            gray = wx.Colour(127, 127, 127)
            dc.SetTextForeground(gray if state == "disabled" else wx.Colour())
            dc.DrawLabel(self._label, self._label_rect)
        elif icons:
            icon = icons["disabled" if state == "disabled" else "normal"]
            dc.DrawBitmap(icon, 0, 0)

    def get_parent(self):

        return self._parent

    def get_bitmaps(self):

        return self._bitmaps

    def set_pos(self, pos):

        self.SetPosition(pos)

    def set_tooltip_label(self, tooltip_label):

        self._tooltip_label = tooltip_label

    def get_tooltip_label(self):

        return self._tooltip_label

    def set_tooltip(self, tooltip_label):

        if tooltip_label:
            self._tooltip_bitmap = ToolTip.create_bitmap(tooltip_label)
        else:
            self._tooltip_bitmap = None

        rect = self.GetScreenRect()

        if rect.Contains(wx.GetMousePosition()):
            ToolTip.update(self._tooltip_bitmap)

    def _on_enter_window(self, event):

        self.set_hilited()

        if self._tooltip_bitmap:
            pos = self.GetScreenPosition() + event.GetPosition()
            ToolTip.show(self._tooltip_bitmap, pos)

    def _on_leave_window(self, event):

        self.set_hilited(False)

        if self._is_clicked:
            self._is_clicked = False

        if self._tooltip_bitmap:
            ToolTip.hide()

    def _on_left_down(self, event):

        self._is_clicked = True
        self.Refresh()

    def _on_left_up(self, event):

        if self._is_clicked:
            self._command()
            self._is_clicked = False
            self.Refresh()

    def is_clicked(self):

        return self._is_clicked

    def press(self):

        self._command()

    def set_hilited(self, is_hilited=True):

        if self._is_hilited != is_hilited:
            self._is_hilited = is_hilited
            self.Refresh()

    def is_hilited(self):

        return self._is_hilited

    def set_active(self, is_active=True):

        if self._is_active != is_active:
            self._is_active = is_active
            self.Refresh()

    def is_active(self):

        return self._is_active

    def show(self):

        self.Show()

    def hide(self):

        self.Hide()

    def add_disabler(self, disabler_id, disabler):

        self._disablers[disabler_id] = disabler

    def remove_disabler(self, disabler_id):

        del self._disablers[disabler_id]

    def is_disabled_state_shown(self):

        return self._show_disabled_state

    def enable(self, enable=True):

        if self.IsEnabled() == enable:
            return True

        if enable:
            for disabler in self._disablers.itervalues():
                if disabler():
                    return False

        self.Enable(enable)
        self.Refresh()

        return True

    def disable(self, show=True):

        if not self.IsEnabled():
            return

        self.Disable()
        ToolTip.hide()

        if show:
            self._is_active = False
            self.Refresh()

        self._show_disabled_state = show


class ButtonGroup(BaseObject):

    def __init__(self):

        self._btns = {}
        self._disablers = {}

    def add_button(self, button, button_id):

        self._btns[button_id] = button

    def get_buttons(self):

        return self._btns.values()

    def get_button(self, btn_id):

        return self._btns[btn_id]

    def add_disabler(self, disabler_id, disabler):

        self._disablers[disabler_id] = disabler

    def remove_disabler(self, disabler_id):

        del self._disablers[disabler_id]

    def enable_button(self, btn_id):

        self._btns[btn_id].enable()

    def disable_button(self, btn_id, show=True):

        self._btns[btn_id].disable(show)

    def enable(self, enable=True):

        if enable:
            for disabler in self._disablers.itervalues():
                if disabler():
                    return False

        for btn in self._btns.itervalues():
            btn.enable(enable)

        return True

    def disable(self, show=True):

        for btn in self._btns.itervalues():
            btn.disable(show)
