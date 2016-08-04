from ....base import *
from ....panel import *


class BackgroundPanel(Panel):

    def __init__(self, parent, focus_receiver=None):

        Panel.__init__(self, parent, "Background", focus_receiver, "uv_window")

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

        self._tex_filename = ""

        bitmap_paths = PanelButton.get_bitmap_paths("panel_button")

        sizer = self.get_top_ctrl_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=4, vgap=4)
        sizer.Add(subsizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)
        label = "Load"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, self, subsizer, bitmaps, label,
                          "Load background texture", self.__load_tex,
                          sizer_args, focus_receiver=focus_receiver)
        field = PanelInputField(self, self, subsizer, 100, sizer_args=sizer_args,
                                focus_receiver=focus_receiver)
        val_id = "tex_filename"
        field.add_value(val_id, "string", handler=self.__set_tex)
        field.show_value(val_id)
        field.set_input_init(val_id, self.__init_tex_filename_input)
        field.set_input_parser(val_id, self.__check_texture_filename)
        field.set_value_parser(val_id, self.__parse_texture_filename)
        self._fields[val_id] = field

        self.add_text("Brightness:", subsizer, sizer_args)
        field = PanelInputField(self, self, subsizer, 45, sizer_args=sizer_args,
                                focus_receiver=focus_receiver)
        val_id = "brightness"
        field.set_input_parser(val_id, self.__parse_brightness)
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        self.add_text("Tiling:", subsizer, sizer_args)
        field = PanelInputField(self, self, subsizer, 40, sizer_args=sizer_args,
                                focus_receiver=focus_receiver)
        val_id = "tiling"
        field.add_value(val_id, "int", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_tiling)
        self._fields[val_id] = field

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer, 0, wx.ALL, 10)
        checkbox = PanelCheckBox(self, self, subsizer,
                                 lambda val: self.__handle_value("show_on_models", val),
                                 sizer_args=sizer_args, focus_receiver=focus_receiver)
        checkbox.check(False)
        self._checkboxes["show_on_models"] = checkbox
        self.add_text("Show on models", subsizer, sizer_args)

        parent.add_panel(self)
        self.update()
        self.finalize()
        self.update_parent()

        Mgr.add_interface_updater("uv_window", "uv_background", self.__set_background_property)

    def get_clipping_rect(self):

        panel_rect = self.GetRect()
        width, height = panel_rect.size
        y_orig = self.GetParent().GetPosition()[1] + panel_rect.y
        clipping_rect = wx.Rect(0, -y_orig, *self.GetGrandParent().GetSize())

        return clipping_rect

    def __handle_value(self, value_id, value):

        Mgr.update_interface_remotely("uv_window", "uv_background", value_id, value)

    def __load_tex(self):

        file_types = "Bitmap files (*.bmp;*.jpg;*.png)|*.bmp;*.jpg;*.png"
        tex_filename = wx.FileSelector("Load background texture",
                                       "", "", "bitmap", file_types,
                                       wx.FD_OPEN | wx.FD_FILE_MUST_EXIST, self)

        if not tex_filename:
            return

        self._fields["tex_filename"].set_value("tex_filename", tex_filename)
        self._tex_filename = tex_filename

        Mgr.update_interface_remotely("uv_window", "uv_background", "tex_filename", tex_filename)

    def __set_tex(self, value_id, tex_filename):

        self._tex_filename = tex_filename

        Mgr.update_interface_remotely("uv_window", "uv_background", "tex_filename", tex_filename)

    def __init_tex_filename_input(self):

        field = self._fields["tex_filename"]

        if self._tex_filename:
            field.set_input_text(self._tex_filename)
        else:
            field.clear()

    def __check_texture_filename(self, filename):

        return filename if (not filename or os.path.exists(filename)) else None

    def __parse_texture_filename(self, filename):

        return os.path.basename(filename) if filename else "<None>"

    def __parse_brightness(self, brightness):

        try:
            return min(1., max(0., float(eval(brightness))))
        except:
            return None

    def __parse_tiling(self, tiling):

        try:
            return max(0, abs(int(eval(tiling))))
        except:
            return None

    def __set_background_property(self, prop_id, value):

        if prop_id == "show_on_models":
            self._checkboxes[prop_id].check(value)
            return

        self._fields[prop_id].set_value(prop_id, value)

        if prop_id == "tex_filename":
            self._tex_filename = value
