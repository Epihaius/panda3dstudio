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

        # *********************** Active UV set section ************************

        uv_section = section = self.add_section("active_uv_set", "Active UV set")
        sizer = section.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=4, hgap=4, vgap=4)
        sizer.Add(subsizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)

        self._uv_set_btns = uv_set_btns = PanelToggleButtonGroup()
        bitmap_paths = PanelButton.get_bitmap_paths("panel_button")

        def set_active_uv_set(uv_set_id):

            Mgr.update_interface_remotely("uv_window", "active_uv_set", uv_set_id)
            self._uv_set_btns.set_active_button(str(uv_set_id))

        for i in range(8):
            bitmaps = PanelButton.create_button_bitmaps("*%d" % i, bitmap_paths)
            get_command = lambda i: lambda: set_active_uv_set(i)
            toggle = (get_command(i), lambda: None)
            btn = uv_set_btns.add_button(self, self, subsizer, str(i), toggle,
                                         bitmaps, "UV set %d" % i, str(i),
                                         focus_receiver=focus_receiver)

        uv_set_btns.set_active_button("0")

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        sizer_args = (0, wx.RIGHT, 20)

        def command():

            Mgr.update_interface_remotely("uv_window", "uv_set_copy")

        label = "Copy"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, self, btn_sizer, bitmaps, label, "Copy active UV set",
                          command, sizer_args, focus_receiver=focus_receiver)
        btn.set_hotkey((ord("C"), wx.MOD_CONTROL), "uv_window")

        def command():

            Mgr.update_interface_remotely("uv_window", "uv_set_paste")

        label = "Paste"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, self, btn_sizer, bitmaps, label,
                          "Replace active UV set with copied one",
                          command, focus_receiver=focus_receiver)
        btn.set_hotkey((ord("V"), wx.MOD_CONTROL), "uv_window")

        # ************************ UV set name section *************************

        name_section = section = self.add_section("uv_set_name", "Active UV set name")
        sizer = section.get_client_sizer()

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.TOP | wx.ALIGN_CENTER_HORIZONTAL, 5)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        section.add_text("For", subsizer, sizer_args)
        subsizer.Add(wx.Size(5, 0))
        combobox = PanelComboBox(self, section, subsizer, "Object", 140,
                                 focus_receiver=focus_receiver)
        self._comboboxes["uv_name_target"] = combobox

        sizer_args = (0, wx.TOP | wx.ALIGN_CENTER_HORIZONTAL, 5)

        field = PanelInputField(self, section, sizer,
                                160, sizer_args=sizer_args,
                                focus_receiver=focus_receiver)
        val_id = "uv_name"
        field.add_value(val_id, "string", handler=self.__handle_value)
        field.show_value(val_id)
        field.clear()
        field.set_input_parser(val_id, self.__parse_uv_name)
        self._fields[val_id] = field

        # **********************************************************************

        def finalize():

            name_section.expand(False)
            self.update_parent()

        wx.CallAfter(finalize)

        parent.add_panel(self)
        self.update()
        self.finalize()
        self.update_parent()

        Mgr.add_interface_updater("uv_window", "uv_name_targets", self.__set_uv_name_targets)
        Mgr.add_interface_updater("uv_window", "uv_name", self.__set_uv_name)
        Mgr.add_interface_updater("uv_window", "target_uv_name", self.__set_target_uv_name)

    def get_clipping_rect(self):

        panel_rect = self.GetRect()
        width, height = panel_rect.size
        y_orig = self.GetParent().GetPosition()[1] + panel_rect.y
        clipping_rect = wx.Rect(0, -y_orig, *self.GetGrandParent().GetSize())

        return clipping_rect

    def __select_uv_name_target(self, obj_id):

        self._comboboxes["uv_name_target"].select_item(obj_id)
        Mgr.update_interface_remotely("uv_window", "uv_name_target_select", obj_id)

    def __set_uv_name_targets(self, names):

        combobox = self._comboboxes["uv_name_target"]
        name_field = self._fields["uv_name"]

        if not names:
            combobox.enable(False)
            self._fields["uv_name"].enable(False)
            return

        get_command = lambda obj_id: lambda: self.__select_uv_name_target(obj_id)

        for obj_id, name in names.iteritems():
            combobox.add_item(obj_id, name, get_command(obj_id))

        obj_id = names.keys()[0]
        self.__select_uv_name_target(obj_id)

    def __handle_value(self, value_id, value):

        obj_id = self._comboboxes["uv_name_target"].get_selected_item()
        Mgr.update_interface_remotely("uv_window", value_id, obj_id, value)

    def __parse_uv_name(self, name):

        parsed_name = name.strip().replace(".", "")

        return parsed_name

    def __set_uv_name(self, uv_set_name):

        self._fields["uv_name"].set_value("uv_name", uv_set_name)

    def __set_target_uv_name(self, uv_set_names):

        obj_id = self._comboboxes["uv_name_target"].get_selected_item()
        uv_set_name = uv_set_names[obj_id]
        self._fields["uv_name"].set_value("uv_name", uv_set_name)
