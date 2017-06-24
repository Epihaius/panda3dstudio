from .base import *
from .button import Button
from .field import InputField


class ComboBox(Button):

    _field_pos = None

    @classmethod
    def init(cls, field_pos):

        cls._field_pos = field_pos

    _bitmap_paths = {}

    @classmethod
    def add_bitmap_paths(cls, bitmap_paths_id, bitmap_paths):

        cls._bitmap_paths[bitmap_paths_id] = bitmap_paths

    @classmethod
    def get_bitmap_paths(cls, bitmap_paths_id):

        return cls._bitmap_paths[bitmap_paths_id]

    @staticmethod
    def create_button_bitmaps(icon_path, bitmap_paths, width, flat=False):

        if flat:
            for part in ("left", "center", "right"):
                bitmap_paths[part]["normal"] = bitmap_paths[part]["flat"]
                bitmap_paths[part]["disabled"] = bitmap_paths[part]["flat"]

        if icon_path and not icon_path.startswith("*"):
            i_w, i_h = Cache.load("image", icon_path).GetSize()
            h = Cache.load("bitmap", bitmap_paths["left"]["normal"]).GetHeight()
            icon_size = (width - 4 - (h - i_w), i_h)
        else:
            icon_size = None

        return Button.create_button_bitmaps(icon_path, bitmap_paths, width, icon_size)

    def __init__(self, button_data, active_tint=(1.8, 1.8, 1.8), direction="down"):

        Button.__init__(self, *button_data)

        width = self.get_bitmaps()["normal"].GetWidth()
        x, y = self._field_pos
        self._field_rect = wx.Rect(x, y, width - x - 10, 18)

        def create_field_bitmap(state):

            img = Cache.load("image", os.path.join(GFX_PATH, "toolbar_bg.png"))
            h = img.GetHeight()
            img = img.Scale(width, h).Mirror(horizontally=False).GetSubImage(self._field_rect)
            tint = active_tint if state == "active" else (1.6, 1.6, 1.6)

            return img.AdjustChannels(*tint).ConvertToBitmap()

        self._field_bitmaps = {}

        for state in ("normal", "active"):
            gfx_id = ("combo_field", state, width, active_tint)
            self._field_bitmaps[state] = Cache.create(
                "bitmap", gfx_id, lambda: create_field_bitmap(state))

        self._items = {}
        self._item_ids = []
        self._item_labels = {}
        self._persistent_items = []
        self._selected_item_id = None
        self._label = ""
        self._selection_handlers = {}
        self._dir = direction

        self._is_field_active = False

        self._popup_menu = wx.Menu()

        self.Bind(wx.EVT_LEFT_UP, self.__show_popup)

    def __show_popup(self, event):

        if self.is_clicked():
            self.set_active()
            x, y = self._field_pos
            y_offset = (-19 * (len(self._items) - 1) - 2) if self._dir == "up" else 18
            self.PopupMenuXY(self._popup_menu, x, y + y_offset)
            self.set_active(False)

    def _draw(self, event):

        if not self._has_back_bitmap:
            self._set_back_bitmap()
            return

        dc = wx.AutoBufferedPaintDCFactory(self)
        bitmaps = self.get_bitmaps()
        dc.DrawBitmap(bitmaps["back"], 0, 0)

        if not self._is_enabled and self.is_disabled_state_shown():
            state = "disabled"
        elif self.is_active() or self.is_clicked():
            state = "active"
        else:
            state = "hilited" if self.is_hilited() else "normal"

        bitmap = self._field_bitmaps["active" if self._is_field_active else "normal"]
        x, y, w, h = self._field_rect
        dc.DrawBitmap(bitmap, x, y)
        dc.SetFont(Fonts.get("default"))
        rect = wx.Rect(x + 4, y, w - 4, h)
        dc.DrawLabel(self._label, rect, wx.ALIGN_CENTER_VERTICAL)
        dc.DrawBitmap(bitmaps[state], 0, 0)
        icons = bitmaps["icons"]

        if icons:
            icon = icons["disabled" if state == "disabled" else "normal"]
            dc.DrawBitmap(icon, 0, 0)

    def __on_select(self, item_id):

        if self._selected_item_id == item_id:
            return

        if self._selected_item_id is not None and self._selected_item_id not in self._persistent_items:
            index = self._item_ids.index(self._selected_item_id)
            selected_item = self._items[self._selected_item_id]
            self._popup_menu.InsertItem(index, selected_item)

        self._selected_item_id = item_id
        self.set_label(self._item_labels[item_id])

        if self._selected_item_id not in self._persistent_items:
            selected_item = self._items[self._selected_item_id]
            self._popup_menu.RemoveItem(selected_item)

    def add_item(self, item_id, label, item_command, persistent=False):

        item = self._popup_menu.Append(-1, label)
        self.Bind(wx.EVT_MENU, lambda event: item_command(), item)
        self._items[item_id] = item
        self._selection_handlers[item_id] = lambda: self.__on_select(item_id)
        self._item_ids.append(item_id)
        self._item_labels[item_id] = label

        if persistent:
            self._persistent_items.append(item_id)

        if len(self._items) == 1:

            if not persistent:
                self._popup_menu.RemoveItem(item)

            self._selected_item_id = item_id
            self.set_label(label)

    def remove_item(self, item_id):

        if item_id not in self._item_ids:
            return

        item = self._items[item_id]
        self.Unbind(wx.EVT_MENU, item)
        del self._items[item_id]
        del self._item_labels[item_id]
        del self._selection_handlers[item_id]
        index = self._item_ids.index(item_id)
        size = len(self._item_ids)
        self._item_ids.remove(item_id)

        if item_id in self._persistent_items or self._selected_item_id != item_id:
            self._popup_menu.DestroyItem(item)
        else:
            item.Destroy()

        if self._selected_item_id == item_id:

            self._selected_item_id = None

            if index == size - 1:
                index -= 1

            if index >= 0:
                self.select_item(self._item_ids[index])
            else:
                self.set_label("")

        if item_id in self._persistent_items:
            self._persistent_items.remove(item_id)

    def clear(self):

        self._popup_menu.Destroy()
        self._popup_menu = wx.Menu()
        self._items = {}
        self._item_ids = []
        self._item_labels = {}
        self._persistent_items = []
        self._selected_item_id = None
        self._selection_handlers = {}
        self.set_label("")

    def set_field_active(self, is_field_active=True):

        if self._is_field_active != is_field_active:
            self._is_field_active = is_field_active
            self.Refresh()

    def select_none(self):

        if self._selected_item_id is not None and self._selected_item_id not in self._persistent_items:
            index = self._item_ids.index(self._selected_item_id)
            selected_item = self._items[self._selected_item_id]
            self._popup_menu.InsertItem(index, selected_item)

        self._selected_item_id = None
        self.set_label("")

    def select_item(self, item_id):

        if item_id not in self._item_ids:
            return

        self._selection_handlers[item_id]()

    def get_selected_item(self):

        return self._selected_item_id

    def get_item_ids(self):

        return self._item_ids

    def set_label(self, label):

        self._label = label
        tooltip_label = self.get_tooltip_label()
        self.set_tooltip(tooltip_label + ": " + label if label else tooltip_label)
        self.Refresh()

    def set_item_label(self, item_id, label):

        if item_id not in self._item_ids:
            return

        self._item_labels[item_id] = label
        item = self._items[item_id]

        if item.GetMenu():
            item.SetItemLabel(label)
        else:
            self._popup_menu.AppendItem(item)
            item.SetItemLabel(label)
            self._popup_menu.RemoveItem(item)

        if self._selected_item_id == item_id:
            self.set_label(label)

    def get_item_label(self, item_id):

        if item_id not in self._item_ids:
            return

        return self._item_labels[item_id]

    def set_item_index(self, item_id, index):

        if item_id not in self._item_ids:
            return

        self._item_ids.remove(item_id)
        self._item_ids.insert(index, item_id)
        item = self._items[item_id]

        if item.GetMenu():
            self._popup_menu.RemoveItem(item)
            self._popup_menu.InsertItem(index, item)


class EditField(InputField):

    def __init__(self, parent, width, height, text_color=None, back_color=None,
                 focus_receiver=None):

        self._size = wx.Size(width, height)

        wx.PyWindow.__init__(self, parent, size=self._size)
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus()

        self._parent = parent
        self._field_rect = wx.Rect(0, 0, width, height)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self._text_color = text_color if text_color else self._default_text_color
        self._back_color = back_color if back_color else self._default_back_color

        style = wx.TE_RICH2 | wx.TE_PROCESS_ENTER | wx.BORDER_NONE
        text_attr = wx.TextAttr(colText=self._text_color,
                                colBack=self._back_color)
        t_ctrl = wx.TextCtrl(self, -1, "", pos=wx.Point(2, 2),
                             size=(width - 2, height - 4), style=style)
        t_ctrl.SetBackgroundColour(self._back_color)
        t_ctrl.SetDefaultStyle(text_attr)
        self._text_ctrl = t_ctrl
        self.bind_events()

        self._is_enabled = True
        self._disablers = {}
        self._gained_focus = False

        self._is_text_shown = True
        self._texts = {}
        self._fonts = {}
        self._value_id = None
        self._value_types = {}
        self._value_handlers = {}
        self._value_parsers = {}
        self._input_parsers = {}
        self._input_init = {}

        self._popup_menu = menu = wx.Menu()
        self._popup_menu_items = {}
        self._popup_handler = lambda: None
        self.set_popup_handler(lambda: None)
        menu.Append(wx.ID_UNDO, "Undo")
        menu.Append(wx.ID_REDO, "Redo")
        menu.AppendSeparator()
        menu.Append(wx.ID_CUT, "Cut")
        menu.Append(wx.ID_COPY, "Copy")
        menu.Append(wx.ID_PASTE, "Paste")
        menu.Append(wx.ID_SELECTALL, "Select All")
        t_ctrl.Bind(wx.EVT_CONTEXT_MENU, lambda event: self._popup_handler())
        self.Bind(wx.EVT_PAINT, self._draw)

    def _draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        dc.SetPen(wx.Pen(self._back_color))
        dc.SetBrush(wx.Brush(self._back_color))
        dc.DrawRectangleRect(self._field_rect)

        if not self._is_enabled and self._is_text_shown:
            font = self._fonts[self._value_id]
            dc.SetFont(font if font else Fonts.get("default"))
            color = self._text_ctrl.GetDefaultStyle().GetTextColour()
            dc.SetTextForeground(color)
            x, y = self._field_rect.GetPosition()
            dc.DrawText(self._texts[self._value_id], x + 3, y + 2)


class EditableComboBox(ComboBox):

    def __init__(self, btn_data, text_color=None, back_color=None, focus_receiver=None,
                 *args, **kwargs):

        ComboBox.__init__(self, btn_data, *args, **kwargs)

        w, h = self._field_rect.size
        self._input_field = EditField(self, w - 23, h, text_color, back_color, focus_receiver)
        x, y = self._field_pos
        self._input_field.SetPosition(wx.Point(x + 4, y))

        self._is_editable = True

        self._text_color = text_color if text_color else InputField._default_text_color
        self._back_color = back_color if back_color else InputField._default_back_color

    def _draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        bitmaps = self.get_bitmaps()
        dc.DrawBitmap(bitmaps["back"], 0, 0)

        if self._is_editable:
            dc.SetPen(wx.Pen(self._back_color))
            dc.SetBrush(wx.Brush(self._back_color))
            dc.DrawRectangleRect(self._field_rect)

        if not self._is_enabled and self.is_disabled_state_shown():
            state = "disabled"
        elif self.is_active() or self.is_clicked():
            state = "active"
        else:
            state = "hilited" if self.is_hilited() else "normal"

        if not self._is_editable:
            bitmap = self._field_bitmaps["active" if self._is_field_active else "normal"]
            x, y, w, h = self._field_rect
            dc.DrawBitmap(bitmap, x, y)
            dc.SetFont(Fonts.get("default"))
            rect = wx.Rect(x + 4, y, w - 4, h)
            dc.DrawLabel(self._label, rect, wx.ALIGN_CENTER_VERTICAL)

        dc.DrawBitmap(bitmaps[state], 0, 0)
        icons = bitmaps["icons"]

        if icons:
            icon = icons["disabled" if state == "disabled" else "normal"]
            dc.DrawBitmap(icon, 0, 0)

    def _on_enter_window(self, event):

        if self._is_enabled or not self._is_editable:
            Button._on_enter_window(self, event)

    def _on_leave_window(self, event):

        if self._is_enabled or not self._is_editable:
            Button._on_leave_window(self, event)

    def _on_left_down(self, event):

        if self._is_enabled or not self._is_editable:
            Button._on_left_down(self, event)

    def _on_left_up(self, event):

        if self._is_enabled or not self._is_editable:
            Button._on_left_up(self, event)

    def set_editable(self, is_editable=True):

        if self._is_editable == is_editable:
            return

        self._input_field.Show(is_editable)
        self._is_editable = is_editable
        self.Refresh()

    def is_editable(self):

        return self._is_editable

    def get_input_field(self):

        return self._input_field

    def enable(self, enable=True):

        if not self._is_editable:
            Button.enable(self, enable)
            return

        if self._is_enabled == enable:
            return

        if Button.enable(self, enable):
            self.Enable(True)
            self._input_field.enable(enable)

    def disable(self, show=True):

        if not self._is_editable:
            Button.disable(self, show)
            return

        if Button.disable(self, show):
            self.Enable(True)
            self._input_field.disable(show)
