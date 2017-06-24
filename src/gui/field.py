from .base import *


class InputField(wx.PyWindow, FocusResetter):

    _active_inst = None
    _default_input_parsers = {}
    _default_value_parsers = {}
    _default_text_color = None
    _default_back_color = None
    _bitmap_paths = {}
    _field_pos = None
    _height = 0

    @classmethod
    def init(cls, bitmap_paths, default_text_color, default_back_color):

        cls._bitmap_paths = bitmap_paths
        pnl_bitmap_paths = bitmap_paths["panel"]
        tlbr_bitmap_paths = bitmap_paths["toolbar"]
        offset_x = Cache.load("image", pnl_bitmap_paths["left"]).GetWidth()
        offset_y = Cache.load("image", pnl_bitmap_paths["top"]).GetHeight()
        cls._height = Cache.load("bitmap", tlbr_bitmap_paths["left"]).GetHeight()
        cls._field_pos = (offset_x, offset_y)
        cls._default_text_color = default_text_color
        cls._default_back_color = default_back_color

        def accept_input():

            if cls._active_inst:
                active_inst = cls._active_inst
                cls._active_inst = None
                active_inst.accept_input()

        def reject_input():

            if cls._active_inst:
                cls._active_inst.reject_input()
                cls._active_inst = None

        Mgr.expose("active_input_field", lambda: cls._active_inst)
        Mgr.accept("accept_field_input", accept_input)
        Mgr.accept("reject_field_input", reject_input)

        def parse_to_string(input_text):

            return input_text

        def parse_to_int(input_text):

            try:
                return int(eval(input_text))
            except:
                return None

        def parse_to_float(input_text):

            try:
                return float(eval(input_text))
            except:
                return None

        cls._default_input_parsers["string"] = parse_to_string
        cls._default_input_parsers["int"] = parse_to_int
        cls._default_input_parsers["float"] = parse_to_float

        def parse_from_string(value):

            return value

        def parse_from_int(value):

            return str(value)

        def parse_from_float(value):

            return "%.3f" % value

        cls._default_value_parsers["string"] = parse_from_string
        cls._default_value_parsers["int"] = parse_from_int
        cls._default_value_parsers["float"] = parse_from_float

    @staticmethod
    def set_active_input_field(input_field):

        InputField._active_inst = input_field

    @staticmethod
    def set_default_value_parser(value_type, parser):

        InputField._default_value_parsers[value_type] = parser

    @staticmethod
    def set_default_input_parser(value_type, parser):

        InputField._default_input_parsers[value_type] = parser

    def __init__(self, parent, width, text_color=None, back_color=None,
                 parent_type="toolbar", focus_receiver=None):

        wx.PyWindow.__init__(self, parent)
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus()

        self._parent = parent
        self._parent_type = parent_type
        self._width = width
        size = (width, self._height)
        self._size = wx.Size(*size)

        def create_field_border():

            return create_border(self._bitmap_paths[parent_type], size, parent_type)

        gfx_id = ("border", parent_type, size)
        self._bitmap = Cache.create("bitmap", gfx_id, create_field_border)

        x, y = self._field_pos
        w_f = width - 2 * x
        h_f = self._height - 2 * y
        self._field_rect = wx.Rect(x, y, w_f, h_f)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self._draw)

        self._text_color = text_color if text_color else self._default_text_color
        self._back_color = back_color if back_color else self._default_back_color

        style = wx.TE_RICH2 | wx.TE_PROCESS_ENTER | wx.BORDER_NONE
        text_attr = wx.TextAttr(colText=self._text_color,
                                colBack=self._back_color)
        t_ctrl = wx.TextCtrl(self, -1, "", pos=wx.Point(x + 2, y + 3),
                             size=(w_f - 2, h_f - 4), style=style)
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
        
        self._back_bitmap = None

        if parent_type == "toolbar":

            def set_back_bitmap():

                self._back_bitmap = self._parent.get_bitmap().GetSubBitmap(self.GetRect())

            wx.CallAfter(set_back_bitmap)

    def DoGetBestSize(self):

        return self._size

    def bind_events(self):

        self._text_ctrl.Bind(wx.EVT_TEXT_ENTER, self.__on_enter)
        self._text_ctrl.Bind(wx.EVT_KEY_UP, self.__on_escape)
        self._text_ctrl.Bind(wx.EVT_SET_FOCUS, self.__on_gain_focus)

    def _draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)

        if self._parent_type == "toolbar":
            if not self._back_bitmap:
                self._back_bitmap = self._parent.get_bitmap().GetSubBitmap(self.GetRect())
            dc.DrawBitmap(self._back_bitmap, 0, 0)

        dc.SetPen(wx.Pen(self._back_color))
        dc.SetBrush(wx.Brush(self._back_color))
        dc.DrawRectangleRect(self._field_rect)

        if not self._is_enabled and self._is_text_shown:
            font = self._fonts[self._value_id]
            dc.SetFont(font if font else Fonts.get("default"))
            color = self._text_ctrl.GetDefaultStyle().GetTextColour()
            dc.SetTextForeground(color)
            x, y = self._field_rect.GetPosition()
            dc.DrawText(self._texts[self._value_id], x + 3, y + 3)

        dc.DrawBitmap(self._bitmap, 0, 0)

    def __on_enter(self, event):

        self.set_active_input_field(None)
        self.accept_input()
        self.reset_focus()

    def __on_escape(self, event):

        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.reject_input()
            self.set_active_input_field(None)
            self.reset_focus()

    def __on_gain_focus(self, event):

        if self._active_inst is self:
            return

        if self._active_inst:
            self._active_inst.accept_input()

        self.set_active_input_field(self)
        self._gained_focus = True

        def select_all_text():

            self._gained_focus = False
            self._input_init[self._value_id]()
            self._text_ctrl.SelectAll()

        wx.CallAfter(select_all_text)

    def set_input_init(self, value_id, input_init):

        self._input_init[value_id] = input_init

    def set_input_parser(self, value_id, parser):

        self._input_parsers[value_id] = parser

    def __parse_input(self, value_id, input_text):

        val_type = self._value_types[value_id]
        default_parser = self._default_input_parsers.get(val_type)
        parser = self._input_parsers.get(value_id, default_parser)

        return parser(input_text) if parser else None

    def set_value_parser(self, value_id, parser):

        self._value_parsers[value_id] = parser

    def __parse_value(self, value_id, value):

        val_type = self._value_types[value_id]
        default_parser = self._default_value_parsers.get(val_type)
        parser = self._value_parsers.get(value_id, default_parser)

        return parser(value) if parser else None

    def add_value(self, value_id, value_type="float", handler=None, font=None):

        self._value_types[value_id] = value_type
        self._texts[value_id] = ""
        self._fonts[value_id] = font
        self._input_init[value_id] = lambda: None

        if handler:
            self._value_handlers[value_id] = handler
        else:
            self._value_handlers[value_id] = lambda value_id, value: None

    def accept_input(self):

        t_ctrl = self._text_ctrl
        t_ctrl.SetSelection(0, 0)
        old_text = self._texts[self._value_id]
        input_text = t_ctrl.GetValue()

        value = self.__parse_input(self._value_id, input_text)
        accept = False

        if value is None:

            val_str = old_text

        else:

            val_str = self.__parse_value(self._value_id, value)

            if val_str is None:
                val_str = old_text
            else:
                accept = True

        t_ctrl.Clear()

        if self._is_text_shown and val_str:
            t_ctrl.WriteText(val_str)
        else:
            t_ctrl.SetDefaultStyle(t_ctrl.GetDefaultStyle())

        self._texts[self._value_id] = val_str

        if accept:
            self._value_handlers[self._value_id](self._value_id, value)

    def reject_input(self):

        t_ctrl = self._text_ctrl
        t_ctrl.SetSelection(0, 0)
        old_text = self._texts[self._value_id]
        input_text = t_ctrl.GetValue()

        if input_text == old_text:
            return

        t_ctrl.Clear()

        if self._is_text_shown and old_text:
            t_ctrl.WriteText(old_text)
        else:
            t_ctrl.SetDefaultStyle(t_ctrl.GetDefaultStyle())

    def set_value(self, value_id, value):

        val_str = self.__parse_value(value_id, value)

        if val_str is None:
            return

        t_ctrl = self._text_ctrl

        if self._is_text_shown and value_id == self._value_id and t_ctrl.GetValue() != val_str:

            t_ctrl.Clear()

            if val_str:
                t_ctrl.WriteText(val_str)
            else:
                t_ctrl.SetDefaultStyle(t_ctrl.GetDefaultStyle())

            if not self._is_enabled:
                self.Refresh()

        self._texts[value_id] = val_str

    def get_value_id(self):

        return self._value_id

    def set_input_text(self, text):

        t_ctrl = self._text_ctrl
        t_ctrl.Clear()
        t_ctrl.WriteText(text)

    def set_text(self, value_id, text):

        if self._texts[value_id] == text:
            return

        if self._value_id == value_id:
            t_ctrl = self._text_ctrl
            t_ctrl.Clear()
            t_ctrl.WriteText(text)

        self._texts[value_id] = text

        if not self._is_enabled:
            self.Refresh()

    def get_text(self, value_id):

        return self._texts[value_id]

    def show_text(self, show=True):

        if self._is_text_shown == show:
            return False

        t_ctrl = self._text_ctrl
        t_ctrl.Clear()

        if show:
            t_ctrl.WriteText(self._texts[self._value_id])
        else:
            t_ctrl.SetDefaultStyle(t_ctrl.GetDefaultStyle())

        self._is_text_shown = show

        if not self._is_enabled:
            self.Refresh()

        return True

    def set_text_color(self, color=None):

        t_ctrl = self._text_ctrl
        text_attr = t_ctrl.GetDefaultStyle()

        if text_attr.GetTextColour() == color:
            return

        t_ctrl.Clear()
        text_attr.SetTextColour(color if color else self._text_color)
        t_ctrl.SetDefaultStyle(text_attr)
        t_ctrl.SetForegroundColour(color if color else self._text_color)

        if self._is_text_shown:

            t_ctrl.WriteText(self._texts[self._value_id])

            if not self._is_enabled:
                self.Refresh()

    def get_text_color(self):

        return self._text_ctrl.GetDefaultStyle().GetTextColour()

    def clear(self):

        t_ctrl = self._text_ctrl
        t_ctrl.Clear()
        t_ctrl.SetDefaultStyle(t_ctrl.GetDefaultStyle())

        if self._is_text_shown and not self._is_enabled:
            self.Refresh()

    def show_value(self, value_id):

        if value_id in self._texts:

            self._value_id = value_id
            t_ctrl = self._text_ctrl
            t_ctrl.Clear()
            font = self._fonts[value_id] if self._fonts[value_id] else Fonts.get("default")
            text_attr = t_ctrl.GetDefaultStyle()

            if text_attr.GetFont() != font:
                text_attr.SetFont(font)

            t_ctrl.SetDefaultStyle(text_attr)

            if self._is_text_shown:

                t_ctrl.WriteText(self._texts[value_id])

                if not self._is_enabled:
                    self.Refresh()

    def set_popup_handler(self, on_popup):

        def handle_popup():

            on_popup()

            if self._gained_focus:
                self._text_ctrl.SelectAll()

            self._text_ctrl.PopupMenu(self._popup_menu)

        self._popup_handler = handle_popup

    def add_popup_menu_item(self, item_id, item_text, item_command, checkable=False):

        t_ctrl = self._text_ctrl

        if not self._popup_menu_items:
            self._popup_menu.AppendSeparator()

        if checkable:
            item = self._popup_menu.AppendCheckItem(-1, item_text)
        else:
            item = self._popup_menu.Append(-1, item_text)

        t_ctrl.Bind(wx.EVT_MENU, lambda event: item_command(), item)
        self._popup_menu_items[item_id] = item

    def check_popup_menu_item(self, item_id, check=True):

        item = self._popup_menu_items[item_id]
        item.Check(check)

    def add_disabler(self, disabler_id, disabler):

        self._disablers[disabler_id] = disabler

    def remove_disabler(self, disabler_id):

        del self._disablers[disabler_id]

    def enable(self, enable=True):

        if self._is_enabled == enable:
            return

        if enable:
            for disabler in self._disablers.itervalues():
                if disabler():
                    return

        t_ctrl = self._text_ctrl
        t_ctrl.Show(enable)
        self._is_enabled = enable

    def disable(self, show=True):

        if not self._is_enabled:
            return

        t_ctrl = self._text_ctrl
        t_ctrl.Hide()
        self._is_enabled = False
