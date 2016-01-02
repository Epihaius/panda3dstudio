# DeepShelf module.

# Implements the tool button dialogs.

from .base import *
from .tool_btn import ToolButton


class ToolButtonPropertiesDialog(DeepShelfObject, wx.Dialog):

    def __init__(self, defaults):

        wx.Dialog.__init__(
            self, None, -1, "Button properties", size=(400, 400))

        self._btn = None

        btn_id = defaults["id"]
        description = defaults["label"]

        icon_bitmap = defaults["icon_bitmap"]
        old_icon = wx.StaticBitmap(self, -1, icon_bitmap)
        self._icon = wx.StaticBitmap(self, -1, icon_bitmap)
        self._icon_path_old = self._icon_path_new = defaults["icon_path"]

        self._btn_data = self._mgr.do("get_tool_button_data")
        hotkey_string = defaults["hotkey"]
        self._hotkey_old = self._hotkey_new = ToolButton.getHotkeyFromString(
            hotkey_string)

        self._f_keys = {
            wx.WXK_F1: "F1", wx.WXK_F2: "F2", wx.WXK_F3: "F3",
            wx.WXK_F4: "F4", wx.WXK_F5: "F5", wx.WXK_F6: "F6",
            wx.WXK_F7: "F7", wx.WXK_F8: "F8", wx.WXK_F9: "F9",
            wx.WXK_F10: "F10", wx.WXK_F11: "F11", wx.WXK_F12: "F12"
        }

        main_staticbox = wx.StaticBox(self, -1, "Main")
        icon_staticbox = wx.StaticBox(self, -1, "Icon")
        old_icon_staticbox = wx.StaticBox(self, -1, "Old")
        new_icon_staticbox = wx.StaticBox(self, -1, "New")

        sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer = wx.StaticBoxSizer(main_staticbox, wx.HORIZONTAL)
        icon_sizer = wx.StaticBoxSizer(icon_staticbox, wx.VERTICAL)
        icon_sub_sizer = wx.BoxSizer(wx.HORIZONTAL)
        icon_preview_sizer = wx.BoxSizer(wx.HORIZONTAL)
        old_icon_sizer = wx.StaticBoxSizer(old_icon_staticbox, wx.VERTICAL)
        new_icon_sizer = wx.StaticBoxSizer(new_icon_staticbox, wx.VERTICAL)

        old_icon_sizer.Add(old_icon, 0, wx.ALL, 8)
        new_icon_sizer.Add(self._icon, 0, wx.ALL, 8)
        icon_preview_sizer.Add(old_icon_sizer, 1, wx.ALL, 8)
        icon_preview_sizer.Add(new_icon_sizer, 1, wx.ALL, 8)
        icon_sub_sizer.Add(icon_preview_sizer, 0, wx.ALIGN_LEFT)

        label_id = wx.StaticText(self, -1, "ID:")
        label_descr = wx.StaticText(self, -1, "Label:")
        label_hotkey = wx.StaticText(self, -1, "Hotkey:")

        label_sizer = wx.BoxSizer(wx.VERTICAL)
        label_sizer.AddMany([
            (label_id, 1, wx.TOP, 5),
            (label_descr, 1, wx.TOP, 5),
            (label_hotkey, 1, wx.TOP, 5)
        ])
        main_sizer.Add(label_sizer, 0, wx.ALL | wx.EXPAND, 8)

        self._field_id = wx.ComboBox(self, -1, btn_id,
                                     choices=self._btn_data.keys(),
                                     style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.__onChooseID, self._field_id)
        self._field_descr = wx.TextCtrl(self, -1, "")
        self._field_hotkey = wx.TextCtrl(self, -1, "", style=wx.TE_READONLY)
        wx.EVT_KEY_DOWN(self._field_hotkey, self.__onHotkeyDown)

        field_sizer = wx.BoxSizer(wx.VERTICAL)
        field_sizer.AddMany([
            (self._field_id, 1, wx.ALL | wx.EXPAND, 2),
            (self._field_descr, 1, wx.ALL | wx.EXPAND, 2),
            (self._field_hotkey, 1, wx.ALL | wx.EXPAND, 2)
        ])
        main_sizer.Add(field_sizer, 1, wx.ALL | wx.EXPAND, 8)

        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        sizer.Add(main_sizer, 0, wx.ALL | wx.EXPAND, 8)
        sizer.Add(icon_sizer, 1, wx.ALL | wx.EXPAND, 8)
        sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 8)

        self.SetSizer(sizer)

        self._field_descr.SetValue(description)
        self._field_id.SetValue(btn_id)
        self._field_hotkey.SetValue(hotkey_string)

        btn_load_icon = wx.Button(self, -1, "Load icon")
        btn_load_icon.Bind(wx.EVT_BUTTON, self.__loadIcon)
        icon_sub_sizer.AddStretchSpacer()
        icon_sub_sizer.Add(btn_load_icon, 0, wx.ALL | wx.ALIGN_RIGHT, 4)
        icon_sizer.Add(icon_sub_sizer, 0, wx.EXPAND)

    def __loadIcon(self, event):

        wildcard = "Icon image 32x32 (*.png)|*.png|All files (*.*)|*.*"
        dlg = wx.FileDialog(
            self, "Select an icon image", "",
            self._icon_path_old, wildcard,
            wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if dlg.ShowModal() == wx.ID_OK:
            self._icon_path_new = dlg.GetPath()
            self._icon.SetBitmap(wx.Bitmap(self._icon_path_new))

    def __onChooseID(self, event):

        btn_id = self._field_id.GetValue()
        label, icon_path = self._btn_data[btn_id]
        self._field_descr.SetValue(label)
        icon_bitmap = wx.Bitmap(icon_path)

        if icon_bitmap:
            self._icon.SetBitmap(icon_bitmap)
            self._icon_path_new = icon_path

    def __onHotkeyDown(self, event):

        key = event.GetKeyCode()
        # "Alt+Ctrl+Shift+F6"

        if key in xrange(48, 91) or key in self._f_keys:
            # print "Key is '" + chr(key) + "'"

            hotkey_string = ""
            mods = 0

            if event.AltDown():
                hotkey_string += "Alt+"
                mods |= wx.MOD_ALT

            if event.ControlDown():
                hotkey_string += "Ctrl+"
                mods |= wx.MOD_CONTROL

            if event.ShiftDown():
                hotkey_string += "Shift+"
                mods |= wx.MOD_SHIFT

            hotkey_string += self._f_keys[
                key] if key in self._f_keys else chr(key)
            hotkey = (key, mods)

            if hotkey_string in ("Ctrl+A", "Ctrl+I", "Ctrl+X", "Ctrl+V", "Ctrl+H") \
                    or (hotkey != self._hotkey_old and ToolButton.isHotkeyInUse(hotkey)):
                self._field_hotkey.SetValue("")
                self._hotkey_new = None
            else:
                self._field_hotkey.SetValue(hotkey_string)
                self._hotkey_new = hotkey

        elif key in (wx.WXK_DELETE, wx.WXK_BACK):

            self._field_hotkey.SetValue("")
            self._hotkey_new = None


class ToolButtonEditingDialog(ToolButtonPropertiesDialog):

    def __init__(self, button):

        btn_props = button.getProps()

        icon_bitmap = button.getIcon()
        icon_path = Icons.get_path(icon_bitmap)

        defaults = {
            "id": decode_string(btn_props["id"]),
            "label": decode_string(btn_props["label"]),
            "icon_path": icon_path,
            "icon_bitmap": icon_bitmap,
            "hotkey": decode_string(btn_props["hotkey"])
        }

        ToolButtonPropertiesDialog.__init__(self, defaults)

        self._btn = button

    def saveChanges(self):

        label = self._field_descr.GetValue()

        if not label:
            return

        self._btn.set_label(label)
        btn_props = self._btn.getProps()
        btn_id = self._field_id.GetValue()
        btn_props["id"] = encode_string(btn_id)

        if self._hotkey_new != self._hotkey_old:

            hotkey_string = self._field_hotkey.GetValue()

            if ToolButton.set_hotkey(self._hotkey_new, btn_id, self._hotkey_old):
                btn_props["hotkey"] = encode_string(hotkey_string)

        if self._icon_path_new != self._icon_path_old:
            Icons.remove(self._icon_path_old)
            icon_bitmap = self._icon.GetBitmap()
            Icons.add(icon_bitmap, self._icon_path_new)
            btn_props["icon"] = encode_string(self._icon_path_new)
            self._btn.setIcon(icon_bitmap)


class ToolButtonCreationDialog(ToolButtonPropertiesDialog):

    def __init__(self, shelf, x):

        self._shelf = shelf
        self._x = x
        self._icon_bitmap = wx.EmptyBitmapRGBA(32, 32)

        defaults = {
            "id": u"",
            "label": u"",
            "icon_path": u"",
            "icon_bitmap": self._icon_bitmap,
            "hotkey": u""
        }

        ToolButtonPropertiesDialog.__init__(self, defaults)

    def create_button(self):

        label = self._field_descr.GetValue()

        if not label:
            return

        icon_bitmap = self._icon.GetBitmap()
        Icons.add(icon_bitmap, self._icon_path_new)

        btn_props = {
            "id": encode_string(self._field_id.GetValue()),
            "label": encode_string(label),
            "icon": encode_string(self._icon_path_new),
            "hotkey": encode_string(self._field_hotkey.GetValue())
        }

        return self._shelf.insertToolButton(self._x, props=btn_props)
