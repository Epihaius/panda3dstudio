from ....base import *
from ....panel import *


class ExportPanel(Panel):

    def __init__(self, parent, focus_receiver=None):

        Panel.__init__(self, parent, "Template export", focus_receiver, "uv_window")

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

        # ************************* Options section ***************************

        subobj_section = section = self.add_section("export_options", "Export options")
        sizer = section.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)
        section.add_text("Width, height:", subsizer, sizer_args)
        field = PanelInputField(self, section, subsizer, 80, sizer_args=sizer_args,
                                focus_receiver=focus_receiver)
        field.add_value("size", "int", handler=self.__handle_value)
        field.show_value("size")
        field.set_input_parser("size", self.__parse_size)
        self._fields["size"] = field

        group = section.add_group("Edge color")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        group.add_text("RGB:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        color_picker = PanelColorPickerCtrl(self, group, subsizer,
                                            lambda col: self.__handle_subobj_rgb("edge", col),
                                            focus_receiver=focus_receiver)
        self._color_pickers["edge_rgb"] = color_picker
        subsizer.Add(wx.Size(4, 0))
        group.add_text("Alpha:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 45, sizer_args=sizer_args,
                                focus_receiver=focus_receiver)
        val_id = "edge_alpha"
        field.set_input_parser(val_id, self.__parse_alpha)
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        group = section.add_group("Polygon color")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        group.add_text("RGB:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        color_picker = PanelColorPickerCtrl(self, group, subsizer,
                                            lambda col: self.__handle_subobj_rgb("poly", col),
                                            focus_receiver=focus_receiver)
        self._color_pickers["poly_rgb"] = color_picker
        subsizer.Add(wx.Size(4, 0))
        group.add_text("Alpha:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 45, sizer_args=sizer_args,
                                focus_receiver=focus_receiver)
        val_id = "poly_alpha"
        field.set_input_parser(val_id, self.__parse_alpha)
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        group = section.add_group("Seam color")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        group.add_text("RGB:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        color_picker = PanelColorPickerCtrl(self, group, subsizer,
                                            lambda col: self.__handle_subobj_rgb("seam", col),
                                            focus_receiver=focus_receiver)
        self._color_pickers["seam_rgb"] = color_picker
        subsizer.Add(wx.Size(4, 0))
        group.add_text("Alpha:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 45, sizer_args=sizer_args,
                                focus_receiver=focus_receiver)
        val_id = "seam_alpha"
        field.set_input_parser(val_id, self.__parse_alpha)
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        # **************************************************************************

        sizer = self.get_bottom_ctrl_sizer()
        sizer_args = (0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)

        label = "Export"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, self, sizer, bitmaps, label, "Export UV template",
                          self.__export, sizer_args, focus_receiver=focus_receiver)
        self._btns["export"] = btn

        parent.add_panel(self)
        self.update()
        self.finalize()
        self.update_parent()

        Mgr.add_interface_updater("uv_window", "uv_template", self.__set_template_property)

    def get_clipping_rect(self):

        panel_rect = self.GetRect()
        width, height = panel_rect.size
        y_orig = self.GetParent().GetPosition()[1] + panel_rect.y
        clipping_rect = wx.Rect(0, -y_orig, *self.GetGrandParent().GetSize())

        return clipping_rect

    def __handle_value(self, value_id, value):

        Mgr.update_interface_remotely("uv_window", "uv_template", value_id, value)

    def __parse_size(self, size):

        try:
            return max(1, abs(int(eval(size))))
        except:
            return None

    def __parse_alpha(self, alpha):

        try:
            return min(1., max(0., float(eval(alpha))))
        except:
            return None

    def __handle_subobj_rgb(self, subobj_type, color):

        color_values = Mgr.convert_to_remote_format("color", color.Get())

        Mgr.update_interface_remotely("uv_window", "uv_template", "%s_rgb" % subobj_type, color_values)

    def __export(self):

        filename = wx.FileSelector("Save UV template",
                                   "", "", "png", "*.png",
                                   wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, self)

        if filename:
            Mgr.update_interface_remotely("uv_window", "uv_template", "save", filename)

    def __set_template_property(self, prop_id, value):

        if prop_id in ("size", "edge_alpha", "poly_alpha", "seam_alpha"):
            self._fields[prop_id].set_value(prop_id, value)
        else:
            self._color_pickers[prop_id].set_color(value)
