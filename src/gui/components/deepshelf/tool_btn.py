# DeepShelf module.

# Implements the tool buttons.

from __future__ import division
from .base import *


class ToolButton(DeepShelfObject):

    _bitmaps = {"hilited": None, "pressed": None, "active": None}
    _size = 0

    _ids = {}
    _inactive_hotkeys = []

    _on_btn = {"down": lambda: None, "up": lambda: None}

    @classmethod
    def init(cls, bitmap_name):

        for state in cls._bitmaps:
            cls._bitmaps[state] = wx.Bitmap(bitmap_name + state + ".png")

        cls._size = cls._bitmaps["hilited"].GetHeight()

        cls._mgr.set_hotkey_manager(cls)
        cls._mgr.accept("set_btn_down_handler", cls.__set_btn_down_handler)
        cls._mgr.accept("set_btn_up_handler", cls.__set_btn_up_handler)

    @staticmethod
    def get_hotkey_from_string(hotkey_string):

        if not hotkey_string:
            return None

        f_keys = {
            "F1": wx.WXK_F1, "F2": wx.WXK_F2, "F3": wx.WXK_F3,
            "F4": wx.WXK_F4, "F5": wx.WXK_F5, "F6": wx.WXK_F6,
            "F7": wx.WXK_F7, "F8": wx.WXK_F8, "F9": wx.WXK_F9,
            "F10": wx.WXK_F10, "F11": wx.WXK_F11, "F12": wx.WXK_F12
        }

        key = hotkey_string
        mods = 0

        if "Alt+" in hotkey_string:
            key = key.replace("Alt+", "")
            mods |= wx.MOD_ALT

        if "Ctrl+" in hotkey_string:
            key = key.replace("Ctrl+", "")
            mods |= wx.MOD_CONTROL

        if "Shift+" in hotkey_string:
            key = key.replace("Shift+", "")
            mods |= wx.MOD_SHIFT

        key_code = f_keys[key] if key in f_keys else ord(key)

        return (key_code, mods)

    @classmethod
    def set_hotkey(cls, hotkey=None, tool_btn_id=None, hotkey_old=None):

        if hotkey in cls._ids or hotkey in cls._inactive_hotkeys:
            return False

        if hotkey_old in cls._ids:
            del cls._ids[hotkey_old]

        if hotkey:
            cls._ids[hotkey] = tool_btn_id

        return True

    @classmethod
    def is_hotkey_in_use(cls, hotkey):

        if hotkey in cls._ids or hotkey in cls._inactive_hotkeys:
            return True

        return False

    @classmethod
    def clear_hotkeys(cls):

        cls._ids = {}
        cls._inactive_hotkeys = []

    @classmethod
    def activate_hotkey(cls, hotkey):

        if not hotkey:
            return False

        if hotkey not in cls._inactive_hotkeys:
            return False

        cls._inactive_hotkeys.remove(hotkey)

        return True

    @classmethod
    def deactivate_hotkey(cls, hotkey):

        if not hotkey:
            return False

        if hotkey in cls._inactive_hotkeys:
            return False

        cls._inactive_hotkeys.append(hotkey)

        return True

    @classmethod
    def handle_hotkey(cls, hotkey, is_repeat):

        if hotkey in cls._ids:

            if not is_repeat:
                btn_id = cls._ids[hotkey]
                cls._mgr.do_remotely("deepshelf_task %s" % btn_id)
                cls._on_btn["up"]()

            return True

        return False

    @classmethod
    def __set_btn_down_handler(cls, handler=None):

        cls._on_btn["down"] = handler if handler else lambda: None

    @classmethod
    def __set_btn_up_handler(cls, handler=None):

        cls._on_btn["up"] = handler if handler else lambda: None

    @classmethod
    def get_size(cls):

        return cls._size

    def __del__(self):

        Icons.remove(bitmap=self._icon)

    def __init__(self, shelf, x, props):

        self._shelf = shelf
        self._rect = wx.Rect(x, 0, self._size, self._size)
        self._props = props
        self._label = decode_string(props["label"])
        self._tooltip_bitmap = ToolTip.create_bitmap(self._label)
        self._icon = Icons.get(decode_string(props["icon"]))
        self._has_mouse = False
        self._is_down = False
        self._is_selected = False
        self._is_cut = False
        self._is_toggled_on = False

    def set_shelf(self, shelf):

        self._shelf = shelf

    def get_shelf(self):

        return self._shelf

    def set_icon(self, icon):

        self._icon = icon

    def get_icon(self):

        return self._icon

    def get_bitmap(self):

        rect = wx.Rect(4, 4, self._size - 8, self._size - 8)
        bitmap = self._bitmaps["hilited"].GetSubBitmap(rect)
        mem_dc = wx.MemoryDC(bitmap)
        mem_dc.DrawBitmap(self._icon, 0, 0)
        mem_dc.SelectObject(wx.NullBitmap)

        return bitmap

    def set_label(self, label):

        self._label = label
        self._tooltip_bitmap = ToolTip.create_bitmap(label)
        self._props["label"] = encode_string(label)

    def get_label(self):

        return self._label

    def get_id(self):

        return decode_string(self._props["id"])

    def get_hotkey_string(self):

        return decode_string(self._props["hotkey"])

    def get_hotkey(self):

        hotkey_string = decode_string(self._props["hotkey"])

        return self.get_hotkey_from_string(hotkey_string)

    def get_props(self):

        return self._props

    def set_x(self, x):

        self._rect.SetX(x)

    def get_x(self):

        return self._rect.GetX()

    def move(self, d_x):

        self._rect.OffsetXY(d_x, 0)

    def set_selected(self, is_selected=True):

        self._is_selected = is_selected

    def is_selected(self):

        return self._is_selected

    def set_cut(self, is_cut=True):

        self._is_cut = is_cut

    def is_cut(self):

        return self._is_cut

    def draw(self, dc, y, flat=False):

        x = self._rect.GetX()
        self._rect.SetY(y)

        if self._has_mouse or self._is_toggled_on:
            state = "pressed" if self._is_down else (
                "active" if self._is_toggled_on else "hilited")
            dc.DrawBitmap(self._bitmaps[state], x, y)

        dc.DrawBitmap(self._icon, x + 4, y + 4)

    def check_has_mouse(self, mouse_pos):

        has_mouse = self._rect.Contains(mouse_pos)

        if self._has_mouse != has_mouse:

            self._has_mouse = has_mouse

            if has_mouse:
                ToolTip.show(self._tooltip_bitmap)
            else:
                ToolTip.hide()
                self._is_down = False

        return has_mouse

    def has_mouse(self):

        return self._has_mouse

    def notify_mouse_hover(self): pass

    def notify_mouse_leave(self):

        self._has_mouse = False
        self._is_down = False
        ToolTip.hide()

    def press(self):

        self._is_down = True
        self._shelf.get_panel().Refresh()
        ToolTip.hide()
        self._on_btn["down"]()

    def release(self, disabled=False):

        if self._is_down:

            self._is_down = False
            panel = self._shelf.get_panel()
            panel.Refresh()

            if not disabled:
                panel.add_shelf_to_history(self._shelf)
                btn_id = decode_string(self._props["id"])
                self._mgr.do_remotely("deepshelf_task %s" % btn_id)
                self._on_btn["up"]()

    def toggle(self):

        self._is_toggled_on = not self._is_toggled_on
        self._shelf.get_panel().Refresh()

    def is_toggled_on(self):

        return self._is_toggled_on
