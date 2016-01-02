from ....base import *
from ....panel import *


class UVSetPanel(Panel):

    def __init__(self, parent, focus_receiver=None):

        Panel.__init__(self, parent, "UV sets", focus_receiver, "uv_window")

        self._parent = parent
        self._width = parent.get_width()

        panel_sizer = self.GetSizer()
        panel_sizer.Add(wx.Size(self._width, 0))
        parent.GetSizer().Add(self)

        self._btns = {}
        self._comboboxes = {}
        self._checkboxes = {}
        self._color_pickers = {}
        self._fields = {}
        self._radio_btns = {}

        bitmap_paths = PanelButton.get_bitmap_paths("panel_button")

        sizer = self.get_top_ctrl_sizer()
        sizer.Add(wx.Size(0, 10))

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)
        self.add_text("Active UV set:", subsizer, sizer_args)
        field = PanelInputField(self, self, subsizer,
                                40, focus_receiver=focus_receiver)
        val_id = "active_uv_set"
        field.add_value(val_id, "int", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_set_id)
        field.set_value(val_id, 0)
        self._fields[val_id] = field

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)
        sizer_args = (0, wx.RIGHT, 20)

        def command():

            Mgr.update_interface_remotely("uv_window", "uv_set_copy")

        label = "Copy"
        bitmaps = PanelButton.create_button_bitmaps(
            "*%s" % label, bitmap_paths)
        btn = PanelButton(self, self, btn_sizer, bitmaps, label, "Copy active UV set",
                          command, sizer_args, focus_receiver=focus_receiver)
        btn.set_hotkey((ord("C"), wx.MOD_CONTROL), "uv_window")

        def command():

            Mgr.update_interface_remotely("uv_window", "uv_set_paste")

        label = "Paste"
        bitmaps = PanelButton.create_button_bitmaps(
            "*%s" % label, bitmap_paths)
        btn = PanelButton(self, self, btn_sizer, bitmaps, label,
                          "Replace active UV set with copied one",
                          command, focus_receiver=focus_receiver)
        btn.set_hotkey((ord("V"), wx.MOD_CONTROL), "uv_window")

        parent.add_panel(self)
        self.update()
        self.finalize()
        self.update_parent()

    def get_clipping_rect(self):

        panel_rect = self.GetRect()
        width, height = panel_rect.size
        y_orig = self.GetParent().GetPosition()[1] + panel_rect.y
        clipping_rect = wx.Rect(0, -y_orig, *self.GetGrandParent().GetSize())

        return clipping_rect

    def __handle_value(self, value_id, value):

        Mgr.update_interface_remotely("uv_window", value_id, value)

    def __parse_set_id(self, uv_set_id):

        try:
            return min(7, max(0, int(eval(uv_set_id))))
        except:
            return None
