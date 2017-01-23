from ..base import *
from ..button import Button, ButtonGroup
from ..toggle import ToggleButtonGroup
from ..combobox import ComboBox
from ..field import InputField
from ..checkbox import CheckBox
from ..colorctrl import ColorPickerCtrl
from ..panel import *


class MaterialPanel(Panel):

    def __init__(self, parent, focus_receiver=None):

        Panel.__init__(self, parent, "Materials", focus_receiver)

        self._parent = parent
        self._width = parent.get_width()

        self._picking_op = ""

        self._comboboxes = {}
        self._checkboxes = {}
        self._color_pickers = {}
        self._fields = {}
        self._btns = {}
        self._radio_btns = {}

        self._map_type = "color"
        self._tex_map_file_main = ""
        self._tex_map_file_alpha = ""
        self._layer_file_main = ""
        self._layer_file_alpha = ""

        panel_sizer = self.GetSizer()
        panel_sizer.Add(wx.Size(self._width, 0))
        parent.GetSizer().Add(self)

        bitmap_paths = Button.get_bitmap_paths("panel_button")

        # ************************** Scene section ****************************

        scene_section = section = self.add_section("scene", "Scene")
        sizer = section.get_client_sizer()
        sizer_args = (0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 2)

        label = "Clear"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, sizer, bitmaps, label,
                          "Remove materials from all objects in scene",
                          self.__clear_scene, sizer_args,
                          focus_receiver=focus_receiver)

        # ************************* Library section ***************************

        lib_section = section = self.add_section("library", "Library")
        sizer = section.get_client_sizer()

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer_args = (0, wx.ALL, 2)

        label = "Save"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label,
                          "Save material library",
                          self.__save_library, sizer_args,
                          focus_receiver=focus_receiver)

        btn_sizer.Add(wx.Size(15, 0))

        label = "Clear"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label,
                          "Remove all materials from library",
                          self.__clear_library, sizer_args,
                          focus_receiver=focus_receiver)

        sizer.Add(wx.Size(0, 5))
        group = section.add_group("Load/merge")
        grp_sizer = group.get_client_sizer()
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        grp_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer_args = (0, wx.ALL, 2)

        label = "Load"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label,
                          "Load material library",
                          self.__load_library,
                          focus_receiver=focus_receiver)

        btn_sizer.Add(wx.Size(15, 0))

        label = "Merge"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label,
                          "Merge material library",
                          lambda: self.__load_library(merge=True),
                          focus_receiver=focus_receiver)

        grp_sizer.Add(wx.Size(0, 5))
        group.add_text("From:", grp_sizer)
        grp_sizer.Add(wx.Size(0, 3))

        radio_btns = PanelRadioButtonGroup(self, group, "", grp_sizer)
        btn_ids = ("file", "scene")
        texts = ("file", "scene")

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)

        radio_btns.set_selected_button("file")
        self._radio_btns["lib_load_src"] = radio_btns

        grp_sizer.Add(wx.Size(0, 7))
        group.add_text("Duplicate materials:", grp_sizer)
        grp_sizer.Add(wx.Size(0, 3))

        radio_btns = PanelRadioButtonGroup(self, group, "", grp_sizer)
        btn_ids = ("skip", "copy", "replace")
        texts = ("skip", "add as copy", "replace existing")
        get_command = lambda handling: lambda: Mgr.update_app("dupe_material_handling", handling)

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)
            command = get_command(btn_id)
            radio_btns.set_button_command(btn_id, command)

        radio_btns.set_selected_button("skip")
        self._radio_btns["dupe_mat_load"] = radio_btns

        # ************************* Material section **************************

        section = self.add_section("material", "Material")
        sizer = section.get_client_sizer()

        combobox = EditablePanelComboBox(self, section, sizer, "Selected material",
                                         164, focus_receiver=focus_receiver)
        combobox.set_editable(False)
        self._comboboxes["material"] = combobox

        self._selected_mat_id = None
        self._selected_layer_id = None

        field = combobox.get_input_field()
        val_id = "name"
        field.add_value(val_id, "string", handler=self.__handle_value)
        field.set_input_parser(val_id, self.__parse_name)
        field.show_value(val_id)
        self._fields[val_id] = field

        sizer.Add(wx.Size(0, 2))
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 2)
        sizer_args = (0, wx.RIGHT, 15)

        icon_path = os.path.join(GFX_PATH, "icon_marker.png")
        bitmaps = PanelButton.create_button_bitmaps(icon_path, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, "",
                          "Edit selected material name",
                          self.__toggle_material_name_editable, sizer_args,
                          focus_receiver=focus_receiver)
        self._edit_mat_name_btn = btn

        icon_path = os.path.join(GFX_PATH, "icon_plus_equal.png")
        bitmaps = PanelButton.create_button_bitmaps(icon_path, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, "",
                          "Add copy of selected material",
                          self.__copy_material, sizer_args,
                          focus_receiver=focus_receiver)

        icon_path = os.path.join(GFX_PATH, "icon_plus.png")
        bitmaps = PanelButton.create_button_bitmaps(icon_path, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, "",
                          "Add new material",
                          self.__create_material, sizer_args,
                          focus_receiver=focus_receiver)

        icon_path = os.path.join(GFX_PATH, "icon_minus.png")
        bitmaps = PanelButton.create_button_bitmaps(icon_path, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, "",
                          "Remove selected material",
                          self.__remove_material, sizer_args=(),
                          focus_receiver=focus_receiver)

        sizer.Add(wx.Size(0, 2))
        group = section.add_group("Extract from objects")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer, 0, wx.ALIGN_CENTER_HORIZONTAL)

        label = "Selection"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Extract materials from selected objects",
                          self.__extract_material, focus_receiver=focus_receiver)

        subsizer.Add(wx.Size(15, 0))
        label = "Pick..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Extract material from single object",
                          lambda: self.__start_owner_picking("extract"),
                          focus_receiver=focus_receiver)
        self._btns["owner_picking_extract"] = btn

        sizer.Add(wx.Size(0, 2))
        group = section.add_group("Apply to objects")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer, 0, wx.ALIGN_CENTER_HORIZONTAL)

        label = "Selection"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Apply sel. material to sel. objects",
                          self.__apply_material, focus_receiver=focus_receiver)

        subsizer.Add(wx.Size(15, 0))
        label = "Pick..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Apply sel. material to single object",
                          lambda: self.__start_owner_picking("apply"),
                          focus_receiver=focus_receiver)
        self._btns["owner_picking_apply"] = btn

        sizer_args = (0, wx.ALIGN_CENTER_HORIZONTAL)

        sizer.Add(wx.Size(0, 2))
        group = section.add_group("Owner selection")
        grp_sizer = group.get_client_sizer()
        label = "(De)select owners"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, group, grp_sizer, bitmaps, label,
                          "Select all objects having the sel. material",
                          self.__select_material_owners, sizer_args,
                          focus_receiver=focus_receiver)
        grp_sizer.Add(wx.Size(0, 5))

        group.add_text("Current selection:", grp_sizer)
        grp_sizer.Add(wx.Size(0, 3))

        radio_btns = PanelRadioButtonGroup(self, group, "", grp_sizer)
        btn_ids = ("replace", "add_to", "remove_from")
        texts = ("replace with owners", "add owners", "remove owners")
        get_command = lambda sel_mode: lambda: Mgr.update_app("material_owner_sel_mode", sel_mode)

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)
            command = get_command(btn_id)
            radio_btns.set_button_command(btn_id, command)

        radio_btns.set_selected_button("replace")
        self._radio_btns["owner_sel"] = radio_btns

        # *********************** Basic props section *************************

        prop_section = section = self.add_section("basic_props", "Basic properties")
        sizer = section.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=3, hgap=5)
        sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        prop_id = "show_vert_colors"
        checkbox = PanelCheckBox(self, section, subsizer, self.__toggle_vertex_colors,
                                 sizer_args=sizer_args)
        self._checkboxes[prop_id] = checkbox
        section.add_text("Vertex colors", subsizer, sizer_args)
        subsizer.Add(wx.Size(0, 0))

        prop_id = "flat_color"
        subsizer.Add(wx.Size(0, 0))
        section.add_text("Flat color:", subsizer, sizer_args)
        handler = self.__handle_flat_color
        color_picker = PanelColorPickerCtrl(self, section, subsizer, handler)
        self._color_pickers[prop_id] = color_picker

        prop_ids = ("diffuse", "ambient", "emissive", "specular")
        self._base_prop_ids = prop_ids + ("shininess",)

        for prop_id in prop_ids:
            checkbox = PanelCheckBox(self, section, subsizer, self.__get_color_toggler(prop_id),
                                     sizer_args=sizer_args)
            self._checkboxes[prop_id] = checkbox
            section.add_text("%s color:" % prop_id.title(), subsizer, sizer_args)
            handler = self.__get_color_handler(prop_id)
            color_picker = PanelColorPickerCtrl(self, section, subsizer, handler)
            self._color_pickers[prop_id] = color_picker

        subsizer.Add(wx.Size(0, 0))
        section.add_text("Shininess:", subsizer, sizer_args)
        field = PanelInputField(self, section, subsizer, 60, sizer_args=sizer_args)
        val_id = "shininess"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_shininess)
        self._fields[val_id] = field

        val_id = "alpha"
        checkbox = PanelCheckBox(self, section, subsizer, self.__get_color_toggler(val_id))
        self._checkboxes[val_id] = checkbox
        section.add_text("\nTransparency/\nOpacity:\n", subsizer)
        field = PanelInputField(self, section, subsizer, 60, sizer_args=(0, wx.ALIGN_BOTTOM))
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_alpha)
        self._fields[val_id] = field

        # ************************* Texmaps section ***************************

        map_section = section = self.add_section("texmaps", "Texture maps")
        sizer = section.get_client_sizer()
        subsizer = wx.BoxSizer()
        sizer.Add(subsizer)

        val_id = "tex_map"
        checkbox = PanelCheckBox(self, section, subsizer, self.__toggle_tex_map,
                                 sizer_args=sizer_args)
        self._checkboxes[val_id] = checkbox
        subsizer.Add(wx.Size(5, 0))
        combobox = PanelComboBox(self, section, subsizer, "Selected texture map",
                                 134, sizer_args=sizer_args, focus_receiver=focus_receiver)
        self._comboboxes["map_type"] = combobox

        def get_command(map_type):

            def set_map_type():

                self._map_type = map_type
                mat_id = self._selected_mat_id
                Mgr.update_remotely("material_prop", mat_id, "tex_map_select", map_type)

            return set_map_type

        for map_type in ("color", "normal", "height", "normal+height", "gloss",
                         "color+gloss", "normal+gloss", "glow", "color+glow",
                         "vertex color"):
            combobox.add_item(map_type, map_type.title(), get_command(map_type))

        sizer.Add(wx.Size(0, 5))

        group = section.add_group("Texture files")
        grp_sizer = group.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=4)
        grp_sizer.Add(subsizer)
        label = "Main"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths, 40)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Load main texture for selected map",
                          self.__load_texture_map_main,
                          sizer_args, focus_receiver=focus_receiver)
        field = PanelInputField(self, group, subsizer, 100, sizer_args=sizer_args)
        val_id = "tex_map_file_main"
        field.add_value(val_id, "string", handler=self.__set_texture_map_main)
        field.show_value(val_id)
        field.set_input_init(val_id, self.__init_main_filename_input)
        field.set_input_parser(val_id, self.__check_texture_filename)
        field.set_value_parser(val_id, self.__parse_texture_filename)
        self._fields[val_id] = field
        label = "Alpha"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths, 40)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Load alpha texture for selected map",
                          self.__load_texture_map_alpha,
                          sizer_args, focus_receiver=focus_receiver)
        field = PanelInputField(self, group, subsizer,
                                100, sizer_args=sizer_args)
        val_id = "tex_map_file_alpha"
        field.add_value(val_id, "string", handler=self.__set_texture_map_alpha)
        field.show_value(val_id)
        field.set_input_init(val_id, self.__init_alpha_filename_input)
        field.set_input_parser(val_id, self.__check_texture_filename)
        field.set_value_parser(val_id, self.__parse_texture_filename)
        self._fields[val_id] = field

        sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        section.add_text("Border color:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        color_picker = PanelColorPickerCtrl(self, section, subsizer, self.__handle_border_color)
        self._color_pickers["tex_map_border_color"] = color_picker

        sizer.Add(wx.Size(0, 5))

        group = section.add_group("Wrapping")
        grp_sizer = group.get_client_sizer()

        mode_ids = ("repeat", "clamp", "border_color", "mirror", "mirror_once")
        mode_names = ("Repeat", "Clamp", "Border color", "Mirror", "Mirror once")
        get_command = lambda axis, mode_id: lambda: Mgr.update_remotely("material_prop",
                                                                        self._selected_mat_id,
                                                                        "tex_map_wrap_%s" % axis,
                                                                        mode_id)

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=4, vgap=4)
        grp_sizer.Add(subsizer)

        for axis in ("u", "v"):

            group.add_text("%s:" % axis.title(), subsizer, sizer_args)
            combobox = PanelComboBox(self, group, subsizer, "%s wrap mode" % axis.title(),
                                     130, sizer_args=sizer_args, focus_receiver=focus_receiver)

            for mode_id, mode_name in zip(mode_ids, mode_names):
                combobox.add_item(mode_id, mode_name, get_command(axis, mode_id))

            self._comboboxes["tex_map_wrap_%s" % axis] = combobox

        grp_sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)

        val_id = "tex_map_wrap_lock"
        checkbox = PanelCheckBox(self, group, subsizer, self.__toggle_wrap_lock,
                                 sizer_args=sizer_args)
        self._checkboxes[val_id] = checkbox
        subsizer.Add(wx.Size(4, 0))
        group.add_text("Lock U and V modes", subsizer, sizer_args)

        sizer.Add(wx.Size(0, 5))

        group = section.add_group("Filtering")
        grp_sizer = group.get_client_sizer()

        get_command = lambda minmag, type_id: lambda: Mgr.update_remotely("material_prop",
                                                                          self._selected_mat_id,
                                                                          "tex_map_filter_%s" % minmag,
                                                                          type_id)

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=4, vgap=4)
        grp_sizer.Add(subsizer)
        group.add_text("-:", subsizer, sizer_args)
        combobox = PanelComboBox(self, group, subsizer, "Minification filter",
                                 130, sizer_args=sizer_args, focus_receiver=focus_receiver)

        type_ids = ("linear", "nearest", "nearest_mipmap_nearest", "nearest_mipmap_linear",
                    "linear_mipmap_nearest", "linear_mipmap_linear", "shadow")
        type_names = ("Linear", "Nearest", "Nearest mipmap nearest", "Nearest mipmap linear",
                      "Linear mipmap nearest", "Linear mipmap linear", "Shadow")

        for type_id, type_name in zip(type_ids, type_names):
            combobox.add_item(type_id, type_name, get_command("min", type_id))

        self._comboboxes["tex_map_filter_min"] = combobox

        group.add_text("+:", subsizer, sizer_args)
        combobox = PanelComboBox(self, group, subsizer, "Magnification filter",
                                 130, sizer_args=sizer_args, focus_receiver=focus_receiver)

        type_ids = ("linear", "nearest")
        type_names = ("Linear", "Nearest")

        for type_id, type_name in zip(type_ids, type_names):
            combobox.add_item(type_id, type_name, get_command("mag", type_id))

        self._comboboxes["tex_map_filter_mag"] = combobox

        grp_sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        group.add_text("Anisotropic level:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 40, sizer_args=sizer_args)
        val_id = "tex_map_anisotropic_degree"
        field.add_value(val_id, "int", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        # *************************** Texmap transform section ****************

        map_xform_section = section = self.add_section("texmap_xform", "Tex. map transform")
        sizer = section.get_client_sizer()

        group = section.add_group("Offset")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        group.add_text("U:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 54, sizer_args=sizer_args)
        val_id = "tex_map_offset_u"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field
        subsizer.Add(wx.Size(8, 0))
        group.add_text("V:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 54, sizer_args=sizer_args)
        val_id = "tex_map_offset_v"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer)
        section.add_text("Rotation:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, section, subsizer, 90, sizer_args=sizer_args)
        val_id = "tex_map_rotate"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        sizer.Add(wx.Size(0, 5))

        group = section.add_group("Scale")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        group.add_text("U:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 54, sizer_args=sizer_args)
        val_id = "tex_map_scale_u"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field
        subsizer.Add(wx.Size(8, 0))
        group.add_text("V:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 54, sizer_args=sizer_args)
        val_id = "tex_map_scale_v"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        # *************************** Layer section ***************************

        layer_section = section = self.add_section("layers", "Layers")
        sizer = section.get_client_sizer()

        subsizer = wx.BoxSizer()
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(subsizer)
        val_id = "layers"
        checkbox = PanelCheckBox(self, section, subsizer, self.__toggle_layers,
                                 sizer_args=sizer_args)
        self._checkboxes[val_id] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("Use layers\n(overrides single color map)", subsizer, sizer_args)
        sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer)

        val_id = "layer_on"
        checkbox = PanelCheckBox(self, section, subsizer, self.__toggle_layer,
                                 sizer_args=sizer_args)
        self._checkboxes[val_id] = checkbox
        subsizer.Add(wx.Size(5, 0))
        combobox = EditablePanelComboBox(self, section, subsizer, "Selected layer",
                                         134, sizer_args=sizer_args,
                                         focus_receiver=focus_receiver)
        combobox.set_editable(False)
        self._comboboxes["layer"] = combobox

        field = combobox.get_input_field()
        val_id = "layer_name"
        field.add_value(val_id, "string", handler=self.__handle_layer_value)
        field.set_input_parser(val_id, self.__parse_name)
        field.show_value(val_id)
        self._fields[val_id] = field

        sizer.Add(wx.Size(0, 2))
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 2)
        sizer_args = (0, wx.RIGHT, 15)

        icon_path = os.path.join(GFX_PATH, "icon_marker.png")
        bitmaps = PanelButton.create_button_bitmaps(icon_path, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, "",
                          "Edit selected layer name",
                          self.__toggle_layer_name_editable, sizer_args,
                          focus_receiver=focus_receiver)
        self._edit_layer_name_btn = btn

        icon_path = os.path.join(GFX_PATH, "icon_plus_equal.png")
        bitmaps = PanelButton.create_button_bitmaps(icon_path, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, "",
                          "Add copy of selected layer",
                          self.__copy_layer, sizer_args,
                          focus_receiver=focus_receiver)

        icon_path = os.path.join(GFX_PATH, "icon_plus.png")
        bitmaps = PanelButton.create_button_bitmaps(icon_path, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, "",
                          "Add new layer",
                          self.__create_layer, sizer_args,
                          focus_receiver=focus_receiver)

        icon_path = os.path.join(GFX_PATH, "icon_minus.png")
        bitmaps = PanelButton.create_button_bitmaps(icon_path, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, "",
                          "Remove selected layer",
                          self.__remove_layer, sizer_args=(),
                          focus_receiver=focus_receiver)

        sizer.Add(wx.Size(0, 5))

        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer)
        section.add_text("Sort:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, section, subsizer, 40, sizer_args=sizer_args)
        val_id = "layer_sort"
        field.add_value(val_id, "int", handler=self.__handle_layer_value)
        field.show_value(val_id)
        self._fields[val_id] = field
        subsizer.Add(wx.Size(10, 0))
        section.add_text("Priority:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, section, subsizer, 40, sizer_args=sizer_args)
        val_id = "layer_priority"
        field.add_value(val_id, "int", handler=self.__handle_layer_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        # *************************** Layer color section *********************

        layer_color_section = section = self.add_section("layer_color", "Layer color")
        sizer = section.get_client_sizer()

        group = section.add_group("Flat color")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        group.add_text("RGB:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        color_picker = PanelColorPickerCtrl(self, group, subsizer, self.__handle_layer_rgb)
        self._color_pickers["layer_rgb"] = color_picker
        subsizer.Add(wx.Size(4, 0))
        group.add_text("Alpha:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 45, sizer_args=sizer_args)
        val_id = "layer_alpha"
        field.set_input_parser(val_id, self.__parse_alpha)
        field.add_value(val_id, "float", handler=self.__handle_layer_alpha)
        field.show_value(val_id)
        self._fields[val_id] = field

        group = section.add_group("Color scale")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.FlexGridSizer(rows=2, cols=2, hgap=4, vgap=4)
        grp_sizer.Add(subsizer)

        for channels, label in (("rgb", "RGB"), ("alpha", "Alpha")):

            group.add_text("%s:" % label, subsizer, sizer_args)
            subsizer2 = wx.BoxSizer()
            subsizer.Add(subsizer2)

            radio_btns = PanelRadioButtonGroup(self, group, "", subsizer2, size=(3, 1))
            btn_ids = (1, 2, 4)
            get_command = lambda channels, scale: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                              self._selected_mat_id,
                                                                              self._selected_layer_id,
                                                                              "%s_scale" % channels,
                                                                              scale)

            for btn_id in btn_ids:
                radio_btns.add_button(btn_id, str(btn_id))
                radio_btns.set_button_command(btn_id, get_command(channels, btn_id))

            self._radio_btns["layer_%s_scale" % channels] = radio_btns

        # *************************** Layer texture section *******************

        layer_tex_section = section = self.add_section("layer_tex", "Layer texture")
        sizer = section.get_client_sizer()

        group = section.add_group("Texture files")
        grp_sizer = group.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=4)
        grp_sizer.Add(subsizer)
        label = "Main"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths, 40)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Load main texture for selected layer",
                          self.__load_layer_main, sizer_args,
                          focus_receiver=focus_receiver)
        field = PanelInputField(self, group, subsizer, 100, sizer_args=sizer_args)
        val_id = "layer_file_main"
        field.add_value(val_id, "string", handler=self.__set_layer_main)
        field.show_value(val_id)
        field.set_input_init(val_id, self.__init_layer_main_filename_input)
        field.set_input_parser(val_id, self.__check_texture_filename)
        field.set_value_parser(val_id, self.__parse_texture_filename)
        self._fields[val_id] = field
        label = "Alpha"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths, 40)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Load alpha texture for selected layer",
                          self.__load_layer_alpha, sizer_args,
                          focus_receiver=focus_receiver)
        field = PanelInputField(self, group, subsizer, 100, sizer_args=sizer_args)
        val_id = "layer_file_alpha"
        field.add_value(val_id, "string", handler=self.__set_layer_alpha)
        field.show_value(val_id)
        field.set_input_init(val_id, self.__init_layer_alpha_filename_input)
        field.set_input_parser(val_id, self.__check_texture_filename)
        field.set_value_parser(val_id, self.__parse_texture_filename)
        self._fields[val_id] = field

        sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        section.add_text("Border color:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        color_picker = PanelColorPickerCtrl(self, section, subsizer,
                                            self.__handle_layer_border_color)
        self._color_pickers["layer_border_color"] = color_picker

        sizer.Add(wx.Size(0, 5))

        group = section.add_group("Wrapping")
        grp_sizer = group.get_client_sizer()

        mode_ids = ("repeat", "clamp", "border_color", "mirror", "mirror_once")
        mode_names = ("Repeat", "Clamp", "Border color", "Mirror", "Mirror once")
        get_command = lambda axis, mode_id: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                        self._selected_mat_id,
                                                                        self._selected_layer_id,
                                                                        "wrap_%s" % axis,
                                                                        mode_id)

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=4, vgap=4)
        grp_sizer.Add(subsizer)

        for axis in ("u", "v"):

            group.add_text("%s:" % axis.title(), subsizer, sizer_args)
            combobox = PanelComboBox(self, group, subsizer,
                                     "%s wrap mode" % axis.title(),
                                     130, sizer_args=sizer_args,
                                     focus_receiver=focus_receiver)

            for mode_id, mode_name in zip(mode_ids, mode_names):
                combobox.add_item(mode_id, mode_name, get_command(axis, mode_id))

            self._comboboxes["layer_wrap_%s" % axis] = combobox

        grp_sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)

        val_id = "layer_wrap_lock"
        checkbox = PanelCheckBox(self, group, subsizer, self.__toggle_layer_wrap_lock,
                                 sizer_args=sizer_args)
        self._checkboxes[val_id] = checkbox
        subsizer.Add(wx.Size(4, 0))
        group.add_text("Lock U and V modes", subsizer, sizer_args)

        sizer.Add(wx.Size(0, 5))

        group = section.add_group("Filtering")
        grp_sizer = group.get_client_sizer()

        get_command = lambda minmag, type_id: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                          self._selected_mat_id,
                                                                          self._selected_layer_id,
                                                                          "filter_%s" % minmag,
                                                                          type_id)

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=4, vgap=4)
        grp_sizer.Add(subsizer)
        group.add_text("-:", subsizer, sizer_args)
        combobox = PanelComboBox(self, group, subsizer, "Minification filter",
                                 130, sizer_args=sizer_args, focus_receiver=focus_receiver)

        type_ids = ("linear", "nearest", "nearest_mipmap_nearest", "nearest_mipmap_linear",
                    "linear_mipmap_nearest", "linear_mipmap_linear", "shadow")
        type_names = ("Linear", "Nearest", "Nearest mipmap nearest", "Nearest mipmap linear",
                      "Linear mipmap nearest", "Linear mipmap linear", "Shadow")

        for type_id, type_name in zip(type_ids, type_names):
            combobox.add_item(type_id, type_name, get_command("min", type_id))

        self._comboboxes["layer_filter_min"] = combobox

        group.add_text("+:", subsizer, sizer_args)
        combobox = PanelComboBox(self, group, subsizer, "Magnification filter",
                                 130, sizer_args=sizer_args, focus_receiver=focus_receiver)

        type_ids = ("linear", "nearest")
        type_names = ("Linear", "Nearest")

        for type_id, type_name in zip(type_ids, type_names):
            combobox.add_item(type_id, type_name, get_command("mag", type_id))

        self._comboboxes["layer_filter_mag"] = combobox

        grp_sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        group.add_text("Anisotropic level:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 40, sizer_args=sizer_args)
        val_id = "layer_anisotropic_degree"
        field.add_value(val_id, "int", handler=self.__handle_layer_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        section.add_text("UV set:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, section, subsizer, 40, sizer_args=sizer_args)
        val_id = "layer_uv_set"
        field.add_value(val_id, "int", handler=self.__handle_layer_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        # *************************** Layer transform section *****************

        layer_xform_section = section = self.add_section("layer_xform", "Layer transform")
        sizer = section.get_client_sizer()

        group = section.add_group("Offset")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        group.add_text("U:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 54, sizer_args=sizer_args)
        val_id = "layer_offset_u"
        field.add_value(val_id, "float", handler=self.__handle_layer_value)
        field.show_value(val_id)
        self._fields[val_id] = field
        subsizer.Add(wx.Size(8, 0))
        group.add_text("V:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 54, sizer_args=sizer_args)
        val_id = "layer_offset_v"
        field.add_value(val_id, "float", handler=self.__handle_layer_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer)
        section.add_text("Rotation:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, section, subsizer, 90, sizer_args=sizer_args)
        val_id = "layer_rotate"
        field.add_value(val_id, "float", handler=self.__handle_layer_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        sizer.Add(wx.Size(0, 5))

        group = section.add_group("Scale")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        group.add_text("U:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 54, sizer_args=sizer_args)
        val_id = "layer_scale_u"
        field.add_value(val_id, "float", handler=self.__handle_layer_value)
        field.show_value(val_id)
        self._fields[val_id] = field
        subsizer.Add(wx.Size(8, 0))
        group.add_text("V:", subsizer, sizer_args)
        subsizer.Add(wx.Size(4, 0))
        field = PanelInputField(self, group, subsizer, 54, sizer_args=sizer_args)
        val_id = "layer_scale_v"
        field.add_value(val_id, "float", handler=self.__handle_layer_value)
        field.show_value(val_id)
        self._fields[val_id] = field

        # ************************* Layer blending section ********************

        blend_section = section = self.add_section("layer_blending", "Layer blending")
        sizer = section.get_client_sizer()

        group = section.add_group("Basic blending")
        grp_sizer = group.get_client_sizer()
        combobox = PanelComboBox(self, group, grp_sizer, "Blend mode", 140)
        self._comboboxes["layer_blend_mode"] = combobox

        mode_ids = ("modulate", "blend", "replace", "decal", "add",
                    "blend_color_scale", "selector")
        mode_names = ("Modulate", "Blend", "Replace", "Decal", "Add",
                      "Blend color scale", "Selector")
        get_command = lambda mode_id: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                  self._selected_mat_id,
                                                                  self._selected_layer_id,
                                                                  "blend_mode",
                                                                  mode_id)

        for mode_id, mode_name in zip(mode_ids, mode_names):
            combobox.add_item(mode_id, mode_name, get_command(mode_id))

        group = section.add_group("Advanced combining")
        grp_sizer = group.get_client_sizer()
        group.add_text("Using any combine mode\noverrides basic blend mode", grp_sizer)
        grp_sizer.Add(wx.Size(0, 5))
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)
        val_id = "layer_combine_channels_use"
        checkbox = PanelCheckBox(self, group, subsizer, self.__toggle_layer_combine_channels,
                                 sizer_args=sizer_args)
        self._checkboxes[val_id] = checkbox
        subsizer.Add(wx.Size(5, 0))

        combobox = PanelComboBox(self, group, subsizer, "Channels", 100,
                                 sizer_args=sizer_args)
        self._comboboxes["layer_combine_channels"] = combobox
        get_command = lambda channels: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                   self._selected_mat_id,
                                                                   self._selected_layer_id,
                                                                   "combine_channels",
                                                                   channels)

        for item_id, item_label in (("rgb", "RGB"), ("alpha", "Alpha")):
            combobox.add_item(item_id, item_label, get_command(item_id))

        grp_sizer.Add(wx.Size(0, 10))

        combobox = PanelComboBox(self, group, grp_sizer, "Combine mode", 140)
        self._comboboxes["layer_combine_mode"] = combobox
        get_command = lambda mode_id: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                  self._selected_mat_id,
                                                                  self._selected_layer_id,
                                                                  "combine_mode",
                                                                  mode_id)

        mode_ids = ("modulate", "replace", "interpolate", "add", "add_signed",
                    "subtract", "dot3rgb", "dot3rgba")
        mode_names = ("Modulate", "Replace", "Interpolate", "Add", "Add signed",
                      "Subtract", "Dot3 RGB", "Dot3 RGBA")
        for mode_id, mode_name in zip(mode_ids, mode_names):
            combobox.add_item(mode_id, mode_name, get_command(mode_id))

        grp_sizer.Add(wx.Size(0, 5))

        subgroup = group.add_group("Sources")
        subgrp_sizer = subgroup.get_client_sizer()

        combobox = PanelComboBox(self, subgroup, subgrp_sizer, "Source type", 125)
        self._comboboxes["layer_combine_source_index"] = combobox

        subgrp_sizer.Add(wx.Size(0, 10))
        combobox = PanelComboBox(self, subgroup, subgrp_sizer, "Source", 125)
        self._comboboxes["layer_combine_source"] = combobox
        src_ids = ("texture", "previous_layer", "primary_color", "constant_color",
                   "const_color_scale", "last_stored_layer")
        src_names = ("Texture", "Previous layer", "Primary color", "Flat color",
                     "Color scale", "Last stored layer")
        get_command = lambda src_id: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                 self._selected_mat_id,
                                                                 self._selected_layer_id,
                                                                 "combine_source",
                                                                 src_id)

        for src_id, src_name in zip(src_ids, src_names):
            combobox.add_item(src_id, src_name, get_command(src_id))

        radio_btns = PanelRadioButtonGroup(self, subgroup, "", subgrp_sizer, size=(2, 2))
        btn_ids = ("rgb", "1-rgb", "alpha", "1-alpha")
        texts = ("RGB", "1 - RGB", "Alpha", "1 - Alpha")
        get_command = lambda channels: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                   self._selected_mat_id,
                                                                   self._selected_layer_id,
                                                                   "combine_source_channels",
                                                                   channels)

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)
            radio_btns.set_button_command(btn_id, get_command(btn_id))

        radio_btns.set_selected_button("rgb")
        self._radio_btns["layer_combine_source_channels"] = radio_btns

        grp_sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        val_id = "layer_is_stored"
        checkbox = PanelCheckBox(self, group, subsizer, self.__store_layer,
                                 sizer_args=sizer_args)
        self._checkboxes[val_id] = checkbox
        subsizer.Add(wx.Size(5, 0))
        group.add_text("Store layer", subsizer, sizer_args)

        # **************************************************************************

        parent.add_panel(self)
        self.update()
        self.finalize()

        def finalize_sections():

            scene_section.expand(False)
            lib_section.expand(False)
            prop_section.expand(False)
            map_section.expand(False)
            map_xform_section.expand(False)
            layer_section.expand(False)
            layer_color_section.expand(False)
            layer_tex_section.expand(False)
            layer_xform_section.expand(False)
            blend_section.expand(False)
            self.expand(False)
            self.update_parent()

        wx.CallAfter(finalize_sections)

        Mgr.add_app_updater("material_prop", self.__set_material_property)
        Mgr.add_app_updater("new_material", self.__update_new_material, ["select"])
        Mgr.add_app_updater("material_selection", self.__select_material)
        Mgr.add_app_updater("tex_layer_prop", self.__set_layer_property)
        Mgr.add_app_updater("new_tex_layer", self.__update_new_layer, ["select"])
        Mgr.add_app_updater("tex_layer_selection", self.__select_layer)
        Mgr.add_app_updater("material_library", self.__update_library)

    def setup(self):

        add_state = Mgr.add_state
        add_state("material_owner_picking_mode", -10, self.__enter_owner_picking_mode,
                  self.__exit_owner_picking_mode)

    def __enter_owner_picking_mode(self, prev_state_id, is_active):

        Mgr.do("set_viewport_border_color", (0, 255, 255))
        self._btns["owner_picking_%s" % self._picking_op].set_active()

    def __exit_owner_picking_mode(self, next_state_id, is_active):

        if not is_active:
            self._btns["owner_picking_%s" % self._picking_op].set_active(False)
            self._picking_op = ""

    def get_clipping_rect(self):

        panel_rect = self.GetRect()
        width, height = panel_rect.size
        y_orig = self.GetParent().GetPosition()[1] + panel_rect.y
        clipping_rect = wx.Rect(0, -y_orig, *self.GetGrandParent().GetSize())

        return clipping_rect

    def __toggle_material_name_editable(self):

        combobox = self._comboboxes["material"]
        editable = not combobox.is_editable()
        combobox.set_editable(editable)
        self._edit_mat_name_btn.set_active(editable)

    def __toggle_layer_name_editable(self):

        combobox = self._comboboxes["layer"]
        editable = not combobox.is_editable()
        combobox.set_editable(editable)
        self._edit_layer_name_btn.set_active(editable)

    def __extract_material(self):

        Mgr.update_remotely("extracted_material")

    def __apply_material(self):

        Mgr.update_remotely("applied_material")

    def __start_owner_picking(self, picking_op):

        prev_picking_op = self._picking_op
        Mgr.exit_state("material_owner_picking_mode")

        if prev_picking_op != picking_op:
            self._picking_op = picking_op
            Mgr.update_remotely("material_owner_picking", picking_op)

    def __create_material(self):

        Mgr.update_remotely("new_material", None)

    def __copy_material(self):

        Mgr.update_remotely("new_material", self._selected_mat_id)

    def __remove_material(self):

        old_id = self._selected_mat_id
        combobox = self._comboboxes["material"]
        combobox.remove_item(self._selected_mat_id)
        mat_id = combobox.get_selected_item()

        Mgr.update_remotely("removed_material", old_id)

        if mat_id:
            name = combobox.get_item_label(mat_id)
            self._fields["name"].set_value("name", name)
            self._selected_mat_id = mat_id
            self._comboboxes["layer"].clear()
            Mgr.update_remotely("material_selection", mat_id)

    def __save_library(self):

        filename = wx.FileSelector("Save material library",
                                   "", "", "mtlib", "*.mtlib",
                                   wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if filename:
            Mgr.update_remotely("material_library", "save", filename)

    def __load_library(self, merge=False):

        if self._radio_btns["lib_load_src"].get_selected_button() == "scene":
            Mgr.update_remotely("material_library", "merge" if merge else "load")
            return

        file_types = "Material libraries (*.mtlib)|*.mtlib"
        filename = wx.FileSelector("%s material library" % ("Merge" if merge else "Load"),
                                   "", "", "Material library", file_types,
                                   wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                                   self)

        if filename:
            Mgr.update_remotely("material_library", "merge" if merge else "load", filename)

    def __clear_scene(self):

        Mgr.update_remotely("scene_materials", "clear")

    def __clear_library(self):

        self._selected_mat_id = None
        self._comboboxes["material"].clear()

        Mgr.update_remotely("material_library", "clear")

    def __update_library(self, update_id):

        if update_id == "clear":
            self._selected_mat_id = None
            self._comboboxes["material"].clear()

    def __handle_value(self, value_id, value):

        mat_id = self._selected_mat_id

        if value_id in ("shininess", "alpha"):
            prop_data = {"value": value}
            Mgr.update_remotely("material_prop", mat_id, value_id, prop_data)
        else:
            Mgr.update_remotely("material_prop", mat_id, value_id, value)

    def __handle_layer_value(self, value_id, value):

        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id
        prop_id = value_id.replace("layer_", "", 1)

        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, prop_id, value)

    def __get_color_handler(self, value_id):

        def handle_color(color):

            color_values = Mgr.convert_to_remote_format("color", color.Get() + (255,))
            mat_id = self._selected_mat_id
            prop_data = {"value": color_values}
            Mgr.update_remotely("material_prop", mat_id, value_id, prop_data)

        return handle_color

    def __handle_flat_color(self, color):

        color_values = Mgr.convert_to_remote_format("color", color.Get() + (255,))
        mat_id = self._selected_mat_id
        Mgr.update_remotely("material_prop", mat_id, "flat_color", color_values)

    def __handle_layer_rgb(self, color):

        color_values = Mgr.convert_to_remote_format("color", color.Get() + (255,))
        alpha = float(self._fields["layer_alpha"].get_text("layer_alpha"))
        color_values = color_values[:3] + (alpha,)
        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id

        Mgr.update_remotely("tex_layer_prop", mat_id,layer_id, "color", color_values)

    def __handle_layer_alpha(self, value_id, value):

        color = self._color_pickers["layer_rgb"].get_color()
        color_values = Mgr.convert_to_remote_format("color", color.Get() + (255,))
        color_values = color_values[:3] + (value,)
        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id

        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, "color", color_values)

    def __handle_border_color(self, color):

        color_values = Mgr.convert_to_remote_format("color", color.Get() + (255,))
        mat_id = self._selected_mat_id

        Mgr.update_remotely("material_prop", mat_id, "tex_map_border_color", color_values)

    def __handle_layer_border_color(self, color):

        color_values = Mgr.convert_to_remote_format("color", color.Get() + (255,))
        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id

        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, "border_color", color_values)

    def __toggle_vertex_colors(self, on):

        mat_id = self._selected_mat_id
        Mgr.update_remotely("material_prop", mat_id, "show_vert_colors", on)

    def __get_color_toggler(self, value_id):

        def toggle_color(on):

            mat_id = self._selected_mat_id
            prop_data = {"on": on}
            Mgr.update_remotely("material_prop", mat_id, value_id, prop_data)

        return toggle_color

    def __toggle_tex_map(self, on):

        mat_id = self._selected_mat_id
        Mgr.update_remotely("material_prop", mat_id, "tex_map_on", on)

    def __toggle_layers(self, on):

        mat_id = self._selected_mat_id
        Mgr.update_remotely("material_prop", mat_id, "layers_on", on)

    def __toggle_layer(self, on):

        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id
        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, "on", on)

    def __toggle_wrap_lock(self, on):

        mat_id = self._selected_mat_id
        Mgr.update_remotely("material_prop", mat_id, "tex_map_wrap_lock", on)

    def __toggle_layer_wrap_lock(self, on):

        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id
        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, "wrap_lock", on)

    def __toggle_layer_combine_channels(self, on):

        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id
        prop_id = "combine_channels_use"
        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, prop_id, on)

    def __parse_name(self, name):

        parsed_name = name.strip(" *")

        return parsed_name if parsed_name else None

    def __parse_shininess(self, shininess):

        try:
            return abs(float(eval(shininess)))
        except:
            return None

    def __parse_alpha(self, alpha):

        try:
            return min(1., max(0., abs(float(eval(alpha)))))
        except:
            return None

    def __set_material_property(self, mat_id, prop_id, value):

        if prop_id == "name":
            if self._selected_mat_id == mat_id:
                self._fields[prop_id].set_value(prop_id, value)
            self._comboboxes["material"].set_item_label(mat_id, value)
        elif prop_id == "show_vert_colors":
            self._checkboxes[prop_id].check(value)
        elif prop_id == "flat_color":
            self._color_pickers[prop_id].set_color(value)
        elif prop_id == "shininess":
            self._fields[prop_id].set_value(prop_id, value["value"])
        elif prop_id == "alpha":
            self._checkboxes[prop_id].check(value["on"])
            self._fields[prop_id].set_value(prop_id, value["value"])
        elif prop_id in self._base_prop_ids:
            self._checkboxes[prop_id].check(value["on"])
            self._color_pickers[prop_id].set_color(value["value"])
        elif prop_id == "layers_on":
            self._checkboxes["layers"].check(value)
        elif prop_id == "tex_map_select":
            self._map_type = value
            self._comboboxes["map_type"].select_item(value)
        elif prop_id == "tex_map_on":
            self._checkboxes["tex_map"].check(value)
        elif prop_id == "tex_map_file_main":
            self._tex_map_file_main = value
            self._fields[prop_id].set_value(prop_id, value)
        elif prop_id == "tex_map_file_alpha":
            self._tex_map_file_alpha = value
            self._fields[prop_id].set_value(prop_id, value)
        elif prop_id == "tex_map_border_color":
            self._color_pickers[prop_id].set_color(value)
        elif prop_id == "tex_map_wrap_u":
            self._comboboxes[prop_id].select_item(value)
        elif prop_id == "tex_map_wrap_v":
            self._comboboxes[prop_id].select_item(value)
        elif prop_id == "tex_map_wrap_lock":
            self._checkboxes[prop_id].check(value)
        elif prop_id == "tex_map_filter_min":
            self._comboboxes[prop_id].select_item(value)
        elif prop_id == "tex_map_filter_mag":
            self._comboboxes[prop_id].select_item(value)
        elif prop_id == "tex_map_anisotropic_degree":
            self._fields[prop_id].set_value(prop_id, value)
        elif prop_id == "tex_map_transform":
            u, v = value["offset"]
            rot = value["rotate"][0]
            su, sv = value["scale"]
            self._fields["tex_map_offset_u"].set_value("tex_map_offset_u", u)
            self._fields["tex_map_offset_v"].set_value("tex_map_offset_v", v)
            self._fields["tex_map_rotate"].set_value("tex_map_rotate", rot)
            self._fields["tex_map_scale_u"].set_value("tex_map_scale_u", su)
            self._fields["tex_map_scale_v"].set_value("tex_map_scale_v", sv)
        elif prop_id in ("tex_map_offset_u", "tex_map_offset_v", "tex_map_rotate",
                         "tex_map_scale_u", "tex_map_scale_v"):
            self._fields[prop_id].set_value(prop_id, value)
        elif prop_id == "layers":
            get_command = lambda layer_id: lambda: self.__select_layer(layer_id)
            for layer_id, name in value:
                self._comboboxes["layer"].add_item(layer_id, name, get_command(layer_id))

    def __select_material(self, mat_id):

        combobox = self._comboboxes["material"]
        combobox.select_item(mat_id)
        name = combobox.get_item_label(mat_id)
        self._fields["name"].set_value("name", name)
        self._selected_mat_id = mat_id
        self._comboboxes["layer"].clear()
        Mgr.update_remotely("material_selection", mat_id)

    def __update_new_material(self, mat_id, name="", select=True):

        self._comboboxes["material"].add_item(mat_id, name,
                                              lambda: self.__select_material(mat_id))

        if select:
            self.__select_material(mat_id)

    def __select_material_owners(self):

        Mgr.update_remotely("material_owners", self._selected_mat_id)

    def __check_texture_filename(self, filename):

        return filename if (not filename or os.path.exists(filename)) else None

    def __parse_texture_filename(self, filename):

        return os.path.basename(filename) if filename else "<None>"

    def __load_texture_file(self, map_type, channel_type):

        file_types = "Bitmap files (*.bmp;*.jpg;*.png)|*.bmp;*.jpg;*.png"
        channel_descr = "main" if channel_type == "rgb" else "alpha channel of"
        caption = "Load " + channel_descr + " %s texture map"
        tex_filename = wx.FileSelector(caption % map_type,
                                       "", "", "bitmap", file_types,
                                       wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                                       self)

        if tex_filename:

            import cPickle

            config_data = GlobalData["config"]
            texfile_paths = config_data["texfile_paths"]
            path = os.path.dirname(tex_filename)

            if path not in texfile_paths:
                texfile_paths.append(path)

            with open("config", "wb") as config_file:
                cPickle.dump(config_data, config_file, -1)

        return tex_filename

    def __set_texture_map(self):

        mat_id = self._selected_mat_id
        tex_data = {
            "map_type": self._map_type,
            "rgb_filename": self._tex_map_file_main,
            "alpha_filename": self._tex_map_file_alpha
        }
        prop_data = {
            "layer_id": None,
            "tex_data": tex_data
        }
        Mgr.update_remotely("material_prop", mat_id, "texture", prop_data)

    def __load_texture_map_main(self):

        rgb_filename = self.__load_texture_file(self._map_type, "rgb")

        if not rgb_filename:
            return

        self._fields["tex_map_file_main"].set_value("tex_map_file_main", rgb_filename)
        self._tex_map_file_main = rgb_filename
        self.__set_texture_map()

    def __load_texture_map_alpha(self):

        alpha_filename = self.__load_texture_file(self._map_type, "alpha")

        if not alpha_filename:
            return

        self._fields["tex_map_file_alpha"].set_value("tex_map_file_alpha", alpha_filename)
        self._tex_map_file_alpha = alpha_filename

        if self._tex_map_file_main:
            self.__set_texture_map()

    def __init_main_filename_input(self):

        field = self._fields["tex_map_file_main"]

        if self._tex_map_file_main:
            field.set_input_text(self._tex_map_file_main)
        else:
            field.clear()

    def __init_alpha_filename_input(self):

        field = self._fields["tex_map_file_alpha"]

        if self._tex_map_file_alpha:
            field.set_input_text(self._tex_map_file_alpha)
        else:
            field.clear()

    def __set_texture_map_main(self, value_id, filename):

        self._tex_map_file_main = filename
        self.__set_texture_map()

    def __set_texture_map_alpha(self, value_id, filename):

        self._tex_map_file_alpha = filename

        if self._tex_map_file_main:
            self.__set_texture_map()

    def __create_layer(self):

        Mgr.update_remotely("new_tex_layer", self._selected_mat_id, None)

    def __copy_layer(self):

        Mgr.update_remotely("new_tex_layer", self._selected_mat_id, self._selected_layer_id)

    def __remove_layer(self):

        old_id = self._selected_layer_id
        combobox = self._comboboxes["layer"]
        combobox.remove_item(self._selected_layer_id)
        layer_id = combobox.get_selected_item()

        Mgr.update_remotely("removed_tex_layer", self._selected_mat_id, old_id)

        if layer_id:
            name = combobox.get_item_label(layer_id)
            self._fields["layer_name"].set_value("layer_name", name)
            self._selected_layer_id = layer_id
            Mgr.update_remotely("tex_layer_selection", self._selected_mat_id, layer_id)

    def __set_source_types(self, count):

        combobox = self._comboboxes["layer_combine_source_index"]
        combobox.clear()
        labels = ("Primary", "Secondary", "Interpolation")
        get_command = lambda index: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                self._selected_mat_id,
                                                                self._selected_layer_id,
                                                                "combine_source_index",
                                                                index)

        for i in range(count):
            combobox.add_item(i, labels[i], get_command(i))

    def __store_layer(self, on):

        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id
        prop_id = "is_stored"
        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, prop_id, on)

    def __set_layer_property(self, layer_id, prop_id, value):

        if self._selected_layer_id != layer_id:
            return

        val_id = "layer_" + prop_id

        if prop_id == "name":
            self._fields[val_id].set_value(val_id, value)
            self._comboboxes["layer"].set_item_label(layer_id, value)
        elif prop_id == "color":
            self._color_pickers["layer_rgb"].set_color(value)
            self._fields["layer_alpha"].set_value("layer_alpha", value[3])
        elif prop_id == "rgb_scale":
            self._radio_btns[val_id].set_selected_button(value)
        elif prop_id == "alpha_scale":
            self._radio_btns[val_id].set_selected_button(value)
        elif prop_id == "on":
            self._checkboxes[val_id].check(value)
        elif prop_id == "file_main":
            self._layer_file_main = value
            self._fields[val_id].set_value(val_id, value)
        elif prop_id == "file_alpha":
            self._layer_file_alpha = value
            self._fields[val_id].set_value(val_id, value)
        elif prop_id == "sort":
            self._fields[val_id].set_value(val_id, value)
            self._comboboxes["layer"].set_item_index(layer_id, value)
        elif prop_id == "priority":
            self._fields[val_id].set_value(val_id, value)
        elif prop_id == "border_color":
            self._color_pickers[val_id].set_color(value)
        elif prop_id == "wrap_u":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "wrap_v":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "wrap_lock":
            self._checkboxes[val_id].check(value)
        elif prop_id == "filter_min":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "filter_mag":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "anisotropic_degree":
            self._fields[val_id].set_value(val_id, value)
        elif prop_id == "uv_set":
            self._fields[val_id].set_value(val_id, value)
        elif prop_id == "transform":
            u, v = value["offset"]
            rot = value["rotate"][0]
            su, sv = value["scale"]
            self._fields["layer_offset_u"].set_value("layer_offset_u", u)
            self._fields["layer_offset_v"].set_value("layer_offset_v", v)
            self._fields["layer_rotate"].set_value("layer_rotate", rot)
            self._fields["layer_scale_u"].set_value("layer_scale_u", su)
            self._fields["layer_scale_v"].set_value("layer_scale_v", sv)
        elif prop_id in ("offset_u", "offset_v", "rotate", "scale_u", "scale_v"):
            self._fields[val_id].set_value(val_id, value)
        elif prop_id == "blend_mode":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "combine_mode":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "combine_channels":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "combine_channels_use":
            self._checkboxes[val_id].check(value)
        elif prop_id == "combine_source_count":
            self.__set_source_types(value)
        elif prop_id == "combine_source_index":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "combine_source":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "combine_source_channels":
            self._radio_btns[val_id].set_selected_button(value)
        elif prop_id == "is_stored":
            self._checkboxes[val_id].check(value)

    def __select_layer(self, layer_id):

        combobox = self._comboboxes["layer"]
        combobox.select_item(layer_id)
        name = combobox.get_item_label(layer_id)
        self._fields["layer_name"].set_value("layer_name", name)
        self._selected_layer_id = layer_id
        Mgr.update_remotely("tex_layer_selection", self._selected_mat_id, layer_id)

    def __update_new_layer(self, layer_id, name="", select=True):

        self._comboboxes["layer"].add_item(layer_id, name,
                                           lambda: self.__select_layer(layer_id))

        if select:
            self.__select_layer(layer_id)

    def __set_layer(self):

        tex_data = {
            "map_type": "layer",
            "rgb_filename": self._layer_file_main,
            "alpha_filename": self._layer_file_alpha
        }
        prop_data = {
            "layer_id": self._selected_layer_id,
            "tex_data": tex_data
        }
        mat_id = self._selected_mat_id
        Mgr.update_remotely("material_prop", mat_id, "texture", prop_data)

    def __load_layer_main(self):

        rgb_filename = self.__load_texture_file("layer", "rgb")

        if not rgb_filename:
            return

        self._fields["layer_file_main"].set_value("layer_file_main", rgb_filename)
        self._layer_file_main = rgb_filename
        self.__set_layer()

    def __load_layer_alpha(self):

        alpha_filename = self.__load_texture_file("layer", "alpha")

        if not alpha_filename:
            return

        self._fields["layer_file_alpha"].set_value("layer_file_alpha", alpha_filename)
        self._layer_file_alpha = alpha_filename

        if self._layer_file_main:
            self.__set_layer()

    def __init_layer_main_filename_input(self):

        field = self._fields["layer_file_main"]

        if self._layer_file_main:
            field.set_input_text(self._layer_file_main)
        else:
            field.clear()

    def __init_layer_alpha_filename_input(self):

        field = self._fields["layer_file_alpha"]

        if self._layer_file_alpha:
            field.set_input_text(self._layer_file_alpha)
        else:
            field.clear()

    def __set_layer_main(self, value_id, filename):

        self._layer_file_main = filename
        self.__set_layer()

    def __set_layer_alpha(self, value_id, filename):

        self._layer_file_alpha = filename

        if self._layer_file_main:
            self.__set_layer()

    def get_width(self):

        return self._width

    def get_client_width(self):

        return self._width - self.get_client_offset() * 2


class MaterialToolbar(Toolbar):

    def __init__(self, parent, pos, width):

        Toolbar.__init__(self, parent, pos, width)

        sizer = self.GetSizer()
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        self._comboboxes = {}
        bitmap_paths = ComboBox.get_bitmap_paths("toolbar_button")
        icon_path = os.path.join(GFX_PATH, "icon_arrow_down.png")
        bitmaps = ComboBox.create_button_bitmaps(icon_path, bitmap_paths, 135, flat=True)
        btn_data = (self, bitmaps, "", "Selected texture map")
        self._comboboxes["map_type"] = ComboBox(btn_data)
        bitmaps = ComboBox.create_button_bitmaps(icon_path, bitmap_paths, 105, flat=True)
        btn_data = (self, bitmaps, "", "Selected material color")
        self._comboboxes["color_type"] = ComboBox(btn_data)

        sizer.AddSpacer(5)
        combobox = self._comboboxes["map_type"]
        sizer.Add(combobox, *sizer_args)
        self._map_type = "color"

        def get_command(map_type):

            def set_map_type():

                self._map_type = map_type
                self._comboboxes["map_type"].select_item(map_type)

            return set_map_type

        for map_type in ("color", "normal", "height", "normal+height", "gloss",
                         "color+gloss", "normal+gloss", "glow", "color+glow",
                         "vertex color"):
            combobox.add_item(map_type, map_type.title(), get_command(map_type))

        self._btns = {}
        bitmap_paths = Button.get_bitmap_paths("toolbar_button")

        sizer.AddSpacer(5)

        icon_path = os.path.join(GFX_PATH, "icon_open.png")
        bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
        tooltip_label = "Load texture map"
        btn = Button(self, bitmaps, "", tooltip_label, self.__load_texture)
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self._btns["load_map"] = btn

        icon_path = os.path.join(GFX_PATH, "icon_clear_one.png")
        bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
        tooltip_label = "Clear selected texture map"
        btn = Button(self, bitmaps, "", tooltip_label, self.__clear_texture)
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self._btns["clear_map"] = btn

        icon_path = os.path.join(GFX_PATH, "icon_clear_all.png")
        bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
        tooltip_label = "Clear all texture maps"
        btn = Button(self, bitmaps, "", tooltip_label, self.__clear_all_textures)
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self._btns["clear_all_maps"] = btn

        separator_bitmap_path = os.path.join(GFX_PATH, "toolbar_separator.png")
        sizer.AddSpacer(5)
        self.add_separator(separator_bitmap_path)
        self.add_separator(separator_bitmap_path)
        sizer.AddSpacer(5)

        self._color_type = "diffuse"

        self._checkboxes = {}
        checkbox = CheckBox(self, self.__toggle_color)
        checkbox.check()
        sizer.Add(checkbox, *sizer_args)
        self._checkboxes["color_type"] = checkbox

        combobox = self._comboboxes["color_type"]

        def get_command(color_type):

            def set_color_type():

                Mgr.update_remotely("ready_material_color_selection", color_type)

            return set_color_type

        color_types = ("diffuse", "ambient", "emissive", "specular", "alpha")
        labels = ("Diffuse", "Ambient", "Emissive", "Specular", "Transp./opacity")

        for color_type, label in zip(color_types, labels):
            combobox.add_item(color_type, label, get_command(color_type))

        sizer.Add(combobox, *sizer_args)

        self._color_pickers = {}
        color_picker = ColorPickerCtrl(self, self.__handle_color)
        sizer.Add(color_picker, *sizer_args)
        self._color_pickers["color_type"] = color_picker

        icon_path = os.path.join(GFX_PATH, "icon_apply_one.png")
        bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
        tooltip_label = "Apply selected material color"
        command = lambda: Mgr.update_remotely("selected_obj_mat_prop", self._color_type)
        btn = Button(self, bitmaps, "", tooltip_label, command)
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self._btns["apply_color"] = btn

        sizer.AddSpacer(5)
        self.add_separator(separator_bitmap_path)
        sizer.AddSpacer(5)

        self._fields = {}

        self.add_text("Shininess: ", sizer, sizer_args)
        field = InputField(self, 60)
        sizer.Add(field, *sizer_args)
        val_id = "shininess"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_value(val_id, 1.)
        field.set_input_parser(val_id, self.__parse_shininess)
        self._fields[val_id] = field

        tooltip_label = "Apply shininess"
        command = lambda: Mgr.update_remotely("selected_obj_mat_prop", "shininess")
        btn = Button(self, bitmaps, "", tooltip_label, command)
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self._btns["apply_shininess"] = btn

        sizer.AddSpacer(5)
        self.add_separator(separator_bitmap_path)
        sizer.AddSpacer(5)

        icon_path = os.path.join(GFX_PATH, "icon_apply_all.png")
        bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
        tooltip_label = "Apply all material properties"
        command = lambda: Mgr.update_remotely("selected_obj_mat_props")
        btn = Button(self, bitmaps, "", tooltip_label, command)
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self._btns["apply_all"] = btn

        sizer.AddSpacer(5)

        icon_path = os.path.join(GFX_PATH, "icon_reset_all.png")
        bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
        tooltip_label = "Reset all material properties"
        command = lambda: Mgr.update_remotely("reset_ready_material_props")
        btn = Button(self, bitmaps, "", tooltip_label, command)
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self._btns["reset_all"] = btn

        sizer.AddSpacer(5)

        icon_path = os.path.join(GFX_PATH, "icon_clear.png")
        bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
        tooltip_label = "Clear material"
        command = lambda: Mgr.update_remotely("applied_material", None, True)
        btn = Button(self, bitmaps, "", tooltip_label, command)
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self._btns["clear_material"] = btn

        sizer.Layout()

        Mgr.add_app_updater("ready_material_prop", self.__set_material_property)

    def setup(self): pass

    def __add_path_to_config(self, path):

        import cPickle

        config_data = GlobalData["config"]
        texfile_paths = config_data["texfile_paths"]

        if path not in texfile_paths:
            texfile_paths.append(path)

        with open("config", "wb") as config_file:
            cPickle.dump(config_data, config_file, -1)

    def __load_texture(self):

        map_type = self._map_type
        file_types = "Bitmap files (*.bmp;*.jpg;*.png)|*.bmp;*.jpg;*.png"

        rgb_filename = wx.FileSelector("Load main %s texture map" % map_type,
                                       "", "", "bitmap", file_types,
                                       wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                                       self)

        if not rgb_filename:
            return

        self.__add_path_to_config(os.path.dirname(rgb_filename))

        alpha_filename = wx.FileSelector("Load alpha channel of %s texture map" % map_type,
                                         "", "", "bitmap", file_types,
                                         wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                                         self)

        if alpha_filename:
            self.__add_path_to_config(os.path.dirname(alpha_filename))

        tex_data = {
            "map_type": map_type,
            "rgb_filename": rgb_filename,
            "alpha_filename": alpha_filename
        }

        Mgr.update_remotely("selected_obj_tex", tex_data)

    def __clear_texture(self):

        map_type = self._map_type
        tex_data = {
            "map_type": map_type,
            "rgb_filename": "",
            "alpha_filename": ""
        }

        Mgr.update_remotely("selected_obj_tex", tex_data)

    def __clear_all_textures(self):

        tex_data = {
            "map_type": "all",
            "rgb_filename": "",
            "alpha_filename": ""
        }

        Mgr.update_remotely("selected_obj_tex", tex_data)

    def __handle_value(self, value_id, value):

        if value_id == "shininess":
            prop_data = {"value": value}
            Mgr.update_remotely("ready_material_prop", value_id, prop_data)

    def __handle_color(self, color):

        color_values = Mgr.convert_to_remote_format("color", color.Get() + (255,))

        if self._color_type == "alpha":
            intensity = sum(color_values[:3]) / 3.
            prop_data = {"value": intensity}
        else:
            prop_data = {"value": color_values}

        Mgr.update_remotely("ready_material_prop", self._color_type, prop_data)

        return None, None

    def __toggle_color(self, on):

        prop_data = {"on": on}
        Mgr.update_remotely("ready_material_prop", self._color_type, prop_data)

    def __parse_shininess(self, shininess):

        try:
            return abs(float(eval(shininess)))
        except:
            return None

    def __set_material_property(self, prop_id, value):

        if prop_id == "shininess":
            self._fields[prop_id].set_value(prop_id, value["value"])
        else:
            self._color_type = prop_id
            self._comboboxes["color_type"].select_item(prop_id)
            check = value["on"]
            self._checkboxes["color_type"].check(check)
            val = value["value"]
            color_values = (val,) * 3 + (1.,) if prop_id == "alpha" else val
            self._color_pickers["color_type"].set_color(color_values)

    def __enable_fields(self, enable=True):

        for field in self._fields.itervalues():
            field.enable(enable)

    def enable(self):

        for combobox in self._comboboxes.itervalues():
            combobox.enable()

        for btn in self._btns.itervalues():
            btn.enable()

        for picker in self._color_pickers.itervalues():
            picker.enable()

        self.__enable_fields()

    def disable(self, show=True):

        for combobox in self._comboboxes.itervalues():
            combobox.disable(show)

        for btn in self._btns.itervalues():
            btn.disable(show)

        for picker in self._color_pickers.itervalues():
            picker.disable(show)

        self.__enable_fields(False)
