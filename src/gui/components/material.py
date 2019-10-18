from ..base import *
from ..button import *
from ..toolbar import *
from ..panel import *
from ..dialog import *


class MaterialPanel(Panel):

    def __init__(self, stack):

        Panel.__init__(self, stack, "materials", "Materials")

        self._picking_op = ""

        self._comboboxes = {}
        self._checkbuttons = {}
        self._colorboxes = {}
        self._fields = {}
        self._btns = {}
        self._radio_btns = {}

        self._map_type = "color"
        self._tex_map_file_main = ""
        self._tex_map_file_alpha = ""
        self._layer_file_main = ""
        self._layer_file_alpha = ""

        # ************************** Scene section ****************************

        section = self.add_section("scene", "Scene")

        text = "Clear"
        tooltip_text = "Remove materials from all objects in scene"
        btn = PanelButton(section, text, "", tooltip_text, self.__clear_scene)
        section.add(btn, alignment="center_h")

        # ************************* Library section ***************************

        section = self.add_section("library", "Library")

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        sizer.add((0, 0), proportion=1.)

        text = "Save"
        tooltip_text = "Save material library"
        btn = PanelButton(section, text, "", tooltip_text, self.__save_library)
        sizer.add(btn)

        sizer.add((0, 0), proportion=1.)

        text = "Clear"
        tooltip_text = "Remove all materials from library"
        btn = PanelButton(section, text, "", tooltip_text, self.__clear_library)
        sizer.add(btn)

        sizer.add((0, 0), proportion=1.)

        group = section.add_group("Load/merge")
        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        sizer.add((0, 0), proportion=1.)

        text = "Load"
        tooltip_text = "Load material library"
        btn = PanelButton(group, text, "", tooltip_text, self.__load_library)
        sizer.add(btn)

        sizer.add((0, 0), proportion=1.)

        text = "Merge"
        tooltip_text = "Merge material library"
        btn = PanelButton(group, text, "", tooltip_text, lambda: self.__load_library(merge=True))
        self._btns["merge_lib"] = btn
        sizer.add(btn)

        sizer.add((0, 0), proportion=1.)

        group.add((0, 5))

        text = "From:"
        group.add(PanelText(group, text))

        group.add((0, 3))

        radio_btns = PanelRadioButtonGroup(group, columns=1)
        btn_ids = ("file", "scene")
        texts = ("file", "scene")

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)

        radio_btns.set_selected_button("file")
        self._radio_btns["lib_load_src"] = radio_btns
        group.add(radio_btns.sizer)

        group.add((0, 5))

        text = "Duplicate materials:"
        group.add(PanelText(group, text))

        group.add((0, 3))

        radio_btns = PanelRadioButtonGroup(group, columns=1)
        btn_ids = ("skip", "copy", "replace")
        texts = ("skip", "add as copy", "replace existing")
        get_command = lambda handling: lambda: Mgr.update_app("dupe_material_handling", handling)

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)
            command = get_command(btn_id)
            radio_btns.set_button_command(btn_id, command)

        radio_btns.set_selected_button("skip")
        self._radio_btns["dupe_mat_load"] = radio_btns
        group.add(radio_btns.sizer)

        # ************************* Material section **************************

        section = self.add_section("material", "Material")

        val_id = "name"
        combobox = PanelComboBox(section, 100, tooltip_text="Selected material",
                                 editable=True, value_id=val_id,
                                 handler=self.__handle_value)
        self._comboboxes["material"] = combobox
        section.add(combobox, expand=True)

        self._selected_mat_id = None
        self._selected_layer_id = None

        field = combobox.get_input_field()
        field.set_input_parser(self.__parse_name)
        self._fields[val_id] = field
        combobox.show_input_field(False)

        section.add((0, 5))
        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        icon_id = "icon_caret"
        tooltip_text = "Edit selected material name"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__toggle_material_name_editable)
        self._edit_mat_name_btn = btn
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_copy"
        tooltip_text = "Add copy of selected material"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__copy_material)
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_add"
        tooltip_text = "Add new material"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__create_material)
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_remove"
        tooltip_text = "Remove selected material"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__remove_material)
        btn_sizer.add(btn, proportion=1.)

        group = section.add_group("Extract from objects")
        btn_sizer = Sizer("horizontal")
        group.add(btn_sizer, expand=True)

        btn_sizer.add((0, 0), proportion=1.)

        text = "Selection"
        tooltip_text = "Extract materials from selected objects"
        btn = PanelButton(group, text, "", tooltip_text, self.__extract_material)
        btn_sizer.add(btn)

        btn_sizer.add((0, 0), proportion=1.)

        text = "Pick..."
        tooltip_text = "Extract material from single object"
        command = lambda: self.__start_owner_picking("extract")
        btn = PanelButton(group, text, "", tooltip_text, command)
        self._btns["owner_picking_extract"] = btn
        btn_sizer.add(btn)

        btn_sizer.add((0, 0), proportion=1.)

        group = section.add_group("Apply to objects")
        btn_sizer = Sizer("horizontal")
        group.add(btn_sizer, expand=True)

        btn_sizer.add((0, 0), proportion=1.)

        text = "Selection"
        tooltip_text = "Apply sel. material to sel. objects"
        btn = PanelButton(group, text, "", tooltip_text, self.__apply_material)
        btn_sizer.add(btn)

        btn_sizer.add((0, 0), proportion=1.)

        text = "Pick..."
        tooltip_text = "Apply sel. material to single object"
        command = lambda: self.__start_owner_picking("apply")
        btn = PanelButton(group, text, "", tooltip_text, command)
        self._btns["owner_picking_apply"] = btn
        btn_sizer.add(btn)

        btn_sizer.add((0, 0), proportion=1.)

        group = section.add_group("Owner selection")

        text = "(De)select owners"
        tooltip_text = "Select all objects having the sel. material"
        btn = PanelButton(group, text, "", tooltip_text, self.__select_material_owners)
        group.add(btn, alignment="center_h")

        group.add((0, 5))

        text = "Current selection:"
        group.add(PanelText(group, text))

        group.add((0, 3))

        radio_btns = PanelRadioButtonGroup(group, columns=1)
        btn_ids = ("replace", "add_to", "remove_from")
        texts = ("replace with owners", "add owners", "remove owners")
        get_command = lambda sel_mode: lambda: Mgr.update_app("material_owner_sel_mode", sel_mode)

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)
            command = get_command(btn_id)
            radio_btns.set_button_command(btn_id, command)

        radio_btns.set_selected_button("replace")
        self._radio_btns["owner_sel"] = radio_btns
        group.add(radio_btns.sizer)

        # *********************** Basic props section *************************

        section = self.add_section("basic_props", "Basic properties")

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        section.add(sizer, expand=True)

        prop_id = "show_vert_colors"
        text = "Vertex colors"
        checkbtn = PanelCheckButton(section, self.__toggle_vertex_colors, text)
        self._checkbuttons[prop_id] = checkbtn
        checkbtn_w = checkbtn.get_label_pos()[0]
        sizer.add(checkbtn)
        sizer.add((0, 0))

        text = PanelText(section, "Flat color:")
        borders = (checkbtn_w, 0, 0, 0)
        sizer.add(text, alignment_v="center_v", borders=borders)
        prop_id = "flat_color"
        dialog_title = "Pick flat color"
        colorbox = PanelColorBox(section, self.__handle_flat_color, dialog_title=dialog_title)
        self._colorboxes[prop_id] = colorbox
        sizer.add(colorbox, alignment_v="center_v")

        prop_ids = ("diffuse", "ambient", "emissive", "specular")
        self._base_prop_ids = prop_ids + ("shininess",)

        for prop_id in prop_ids:
            text = f"{prop_id.title()} color:"
            checkbtn = PanelCheckButton(section, self.__get_color_toggler(prop_id), text)
            self._checkbuttons[prop_id] = checkbtn
            sizer.add(checkbtn, alignment_v="center_v")
            dialog_title = f"Pick {prop_id} color"
            colorbox = PanelColorBox(section, self.__get_color_handler(prop_id),
                                     dialog_title=dialog_title)
            self._colorboxes[prop_id] = colorbox
            sizer.add(colorbox, alignment_v="center_v")

        text = PanelText(section, "Shininess:")
        sizer.add(text, alignment_v="center_v", borders=borders)
        val_id = "shininess"
        field = PanelInputField(section, val_id, "float", self.__handle_value, 60)
        field.set_input_parser(self.__parse_shininess_input)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        val_id = "alpha"
        text = "Alpha:"
        checkbtn = PanelCheckButton(section, self.__get_color_toggler(val_id), text)
        self._checkbuttons[val_id] = checkbtn
        sizer.add(checkbtn, alignment_v="center_v")
        field = PanelSliderField(section, val_id, "float", (0., 1.),
                                 self.__handle_value, 60)
        field.set_input_parser(self.__parse_alpha_input)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        # ************************* Texture maps section ***************************

        section = self.add_section("tex_maps", "Texture maps")

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        val_id = "tex_map"
        checkbtn = PanelCheckButton(section, self.__toggle_tex_map)
        self._checkbuttons[val_id] = checkbtn
        borders = (0, 5, 0, 0)
        sizer.add(checkbtn, alignment="center_v", borders=borders)
        combobox = PanelComboBox(section, 135, tooltip_text="Selected texture map")
        self._comboboxes["map_type"] = combobox
        sizer.add(combobox, proportion=1., alignment="center_v")

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

        combobox.update_popup_menu()

        group = section.add_group("Texture files")
        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        group.add(sizer, expand=True)

        text = "Main"
        tooltip_text = "Load main texture for selected map"
        btn = PanelButton(group, text, "", tooltip_text, self.__load_texture_map_main)
        sizer.add(btn, expand_h=True, alignment_v="center_v")
        val_id = "tex_map_file_main"
        handler = lambda *args: self.__set_texture_map_main(args[1])
        field = PanelInputField(group, val_id, "string", handler, 100)
        field.set_input_init(self.__init_main_filename_input)
        field.set_input_parser(self.__check_texture_filename)
        field.set_value_parser(self.__parse_texture_filename)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        text = "Alpha"
        tooltip_text = "Load alpha texture for selected map"
        btn = PanelButton(group, text, "", tooltip_text, self.__load_texture_map_alpha)
        sizer.add(btn, expand_h=True, alignment_v="center_v")
        val_id = "tex_map_file_alpha"
        handler = lambda *args: self.__set_texture_map_alpha(args[1])
        field = PanelInputField(group, val_id, "string", handler, 100)
        field.set_input_init(self.__init_alpha_filename_input)
        field.set_input_parser(self.__check_texture_filename)
        field.set_value_parser(self.__parse_texture_filename)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        section.add((0, 5))

        sizer = Sizer("horizontal")
        section.add(sizer)
        text = "Border color:"
        borders = (0, 5, 0, 0)
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        dialog_title = "Pick texture border color"
        colorbox = PanelColorBox(section, self.__handle_border_color, dialog_title=dialog_title)
        self._colorboxes["tex_map_border_color"] = colorbox
        sizer.add(colorbox, alignment="center_v")

        group = section.add_group("Wrapping")

        mode_ids = ("repeat", "clamp", "border_color", "mirror", "mirror_once")
        mode_names = ("Repeat", "Clamp", "Border color", "Mirror", "Mirror once")
        get_command = lambda axis, mode_id: lambda: Mgr.update_remotely("material_prop",
                                                                        self._selected_mat_id,
                                                                        f"tex_map_wrap_{axis}",
                                                                        mode_id)

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=5)
        group.add(sizer, expand=True)

        for axis in ("u", "v"):

            text = f"{axis.title()}:"
            sizer.add(PanelText(group, text), alignment_v="center_v")
            tooltip_text = f"{axis.title()} wrap mode"
            combobox = PanelComboBox(group, 130, tooltip_text=tooltip_text)

            for mode_id, mode_name in zip(mode_ids, mode_names):
                combobox.add_item(mode_id, mode_name, get_command(axis, mode_id))

            combobox.update_popup_menu()
            self._comboboxes[f"tex_map_wrap_{axis}"] = combobox
            sizer.add(combobox, proportion_h=1., alignment_v="center_v")

        group.add((0, 5))

        val_id = "tex_map_wrap_lock"
        text = "Lock U and V modes"
        checkbtn = PanelCheckButton(group, self.__toggle_wrap_lock, text)
        self._checkbuttons[val_id] = checkbtn
        group.add(checkbtn)

        group = section.add_group("Filtering")

        get_command = lambda minmag, type_id: lambda: Mgr.update_remotely("material_prop",
                                                                          self._selected_mat_id,
                                                                          f"tex_map_filter_{minmag}",
                                                                          type_id)

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=5)
        group.add(sizer, expand=True)

        text = "-:"
        sizer.add(PanelText(group, text), alignment_v="center_v")
        tooltip_text = "Minification filter"
        combobox = PanelComboBox(group, 130, tooltip_text=tooltip_text)

        type_ids = ("linear", "nearest", "nearest_mipmap_nearest", "nearest_mipmap_linear",
                    "linear_mipmap_nearest", "linear_mipmap_linear", "shadow")
        type_names = ("Linear", "Nearest", "Nearest mipmap nearest", "Nearest mipmap linear",
                      "Linear mipmap nearest", "Linear mipmap linear", "Shadow")

        for type_id, type_name in zip(type_ids, type_names):
            combobox.add_item(type_id, type_name, get_command("min", type_id))

        combobox.update_popup_menu()
        self._comboboxes["tex_map_filter_min"] = combobox
        sizer.add(combobox, proportion_h=1., alignment_v="center_v")

        text = "+:"
        sizer.add(PanelText(group, text), alignment_v="center_v")
        tooltip_text = "Magnification filter"
        combobox = PanelComboBox(group, 130, tooltip_text=tooltip_text)

        type_ids = ("linear", "nearest")
        type_names = ("Linear", "Nearest")

        for type_id, type_name in zip(type_ids, type_names):
            combobox.add_item(type_id, type_name, get_command("mag", type_id))

        combobox.update_popup_menu()
        self._comboboxes["tex_map_filter_mag"] = combobox
        sizer.add(combobox, proportion_h=1., alignment_v="center_v")

        group.add((0, 5))

        sizer = Sizer("horizontal")
        group.add(sizer)
        borders = (0, 5, 0, 0)
        text = "Anisotropic level:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "tex_map_anisotropic_degree"
        field = PanelSliderField(group, val_id, "int", (1, 16), self.__handle_value, 60)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        # *************************** Tex. map transform section ****************

        section = self.add_section("tex_map_xform", "Tex. map transform")

        group = section.add_group("Offset")
        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        borders = (0, 5, 0, 0)

        text = "U:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "tex_map_offset_u"
        field = PanelInputField(group, val_id, "float", self.__handle_value, 55)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        sizer.add((0, 0), proportion=1.)

        text = "V:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "tex_map_offset_v"
        field = PanelInputField(group, val_id, "float", self.__handle_value, 55)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        section.add((0, 10))

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)
        text = "Rotation:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        val_id = "tex_map_rotate"
        field = PanelSliderField(section, val_id, "float", (-180., 180.), self.__handle_value, 90)
        field.set_input_parser(self.__parse_angle_input)
        field.set_value(0.)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v", proportion=1.)

        group = section.add_group("Scale")
        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        text = "U:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "tex_map_scale_u"
        field = PanelInputField(group, val_id, "float", self.__handle_value, 55)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        sizer.add((0, 0), proportion=1.)

        text = "V:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "tex_map_scale_v"
        field = PanelInputField(group, val_id, "float", self.__handle_value, 55)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        # *************************** Layer section ***************************

        section = self.add_section("layers", "Layers")

        val_id = "layers"
        text = "Use layers\n(overrides single color map)"
        checkbtn = PanelCheckButton(section, self.__toggle_layers, text)
        self._checkbuttons[val_id] = checkbtn
        section.add(checkbtn)

        section.add((0, 5))

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)
        val_id = "layer_on"
        checkbtn = PanelCheckButton(section, self.__toggle_layer)
        self._checkbuttons[val_id] = checkbtn
        sizer.add(checkbtn, alignment="center_v", borders=borders)
        val_id = "layer_name"
        combobox = PanelComboBox(section, 100, tooltip_text="Selected layer",
                                 editable=True, value_id=val_id,
                                 handler=self.__handle_layer_value)
        self._comboboxes["layer"] = combobox
        sizer.add(combobox, proportion=1., alignment="center_v")
        field = combobox.get_input_field()
        field.set_input_parser(self.__parse_name)
        self._fields[val_id] = field
        combobox.show_input_field(False)

        section.add((0, 5))
        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        icon_id = "icon_caret"
        tooltip_text = "Edit selected layer name"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__toggle_layer_name_editable)
        self._edit_layer_name_btn = btn
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_copy"
        tooltip_text = "Add copy of selected layer"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__copy_layer)
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_add"
        tooltip_text = "Add new layer"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__create_layer)
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_remove"
        tooltip_text = "Remove selected layer"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__remove_layer)
        btn_sizer.add(btn, proportion=1.)

        section.add((0, 5))

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        text = "Sort:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        val_id = "layer_sort"
        field = PanelInputField(section, val_id, "int", self.__handle_layer_value, 40)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        sizer.add((0, 0), proportion=1.)

        text = "Priority:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        val_id = "layer_priority"
        field = PanelInputField(section, val_id, "int", self.__handle_layer_value, 40)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        # *************************** Layer color section *********************

        section = self.add_section("layer_color", "Layer color")

        group = section.add_group("Flat color")
        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        text = "RGB:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        dialog_title = "Pick layer color"
        colorbox = PanelColorBox(group, self.__handle_layer_rgb, dialog_title=dialog_title)
        self._colorboxes["layer_rgb"] = colorbox
        sizer.add(colorbox, alignment="center_v")

        sizer.add((5, 0), proportion=1.)

        text = "Alpha:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "layer_alpha"
        handler = lambda *args: self.__handle_layer_alpha(args[1])
        field = PanelSliderField(group, val_id, "float", (0., 1.), handler, 60)
        field.set_input_parser(self.__parse_alpha_input)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        group = section.add_group("Color scale")
        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        group.add(sizer, expand=True)

        for channels, text in (("rgb", "RGB"), ("alpha", "Alpha")):

            sizer.add(PanelText(group, f"{text}:"), alignment_v="center_v")

            radio_btns = PanelRadioButtonGroup(group, rows=1, gap_h=10)
            btn_ids = (1, 2, 4)
            get_command = lambda channels, scale: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                              self._selected_mat_id,
                                                                              self._selected_layer_id,
                                                                              f"{channels}_scale",
                                                                              scale)

            for btn_id in btn_ids:
                radio_btns.add_button(btn_id, str(btn_id))
                radio_btns.set_button_command(btn_id, get_command(channels, btn_id))

            self._radio_btns[f"layer_{channels}_scale"] = radio_btns
            sizer.add(radio_btns.sizer, alignment_v="center_v")

        # *************************** Layer texture section *******************

        layer_tex_section = section = self.add_section("layer_tex", "Layer texture")

        group = section.add_group("Texture files")
        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        group.add(sizer, expand=True)

        text = "Main"
        tooltip_text = "Load main texture for selected layer"
        btn = PanelButton(group, text, "", tooltip_text, self.__load_layer_main)
        sizer.add(btn, expand_h=True, alignment_v="center_v")
        val_id = "layer_file_main"
        handler = lambda *args: self.__set_layer_main(args[1])
        field = PanelInputField(group, val_id, "string", handler, 100)
        field.set_input_init(self.__init_layer_main_filename_input)
        field.set_input_parser(self.__check_texture_filename)
        field.set_value_parser(self.__parse_texture_filename)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        text = "Alpha"
        tooltip_text = "Load alpha texture for selected layer"
        btn = PanelButton(group, text, "", tooltip_text, self.__load_layer_alpha)
        sizer.add(btn, expand_h=True, alignment_v="center_v")
        val_id = "layer_file_alpha"
        handler = lambda *args: self.__set_layer_alpha(args[1])
        field = PanelInputField(group, val_id, "string", handler, 100)
        field.set_input_init(self.__init_layer_alpha_filename_input)
        field.set_input_parser(self.__check_texture_filename)
        field.set_value_parser(self.__parse_texture_filename)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        section.add((0, 5))

        sizer = Sizer("horizontal")
        section.add(sizer)
        text = "Border color:"
        borders = (0, 5, 0, 0)
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        dialog_title = "Pick layer border color"
        colorbox = PanelColorBox(section, self.__handle_layer_border_color, dialog_title=dialog_title)
        self._colorboxes["layer_border_color"] = colorbox
        sizer.add(colorbox, alignment="center_v")

        group = section.add_group("Wrapping")

        mode_ids = ("repeat", "clamp", "border_color", "mirror", "mirror_once")
        mode_names = ("Repeat", "Clamp", "Border color", "Mirror", "Mirror once")
        get_command = lambda axis, mode_id: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                        self._selected_mat_id,
                                                                        self._selected_layer_id,
                                                                        f"wrap_{axis}", mode_id)

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=5)
        group.add(sizer, expand=True)

        for axis in ("u", "v"):

            text = f"{axis.title()}:"
            sizer.add(PanelText(group, text), alignment_v="center_v")
            tooltip_text = f"{axis.title()} wrap mode"
            combobox = PanelComboBox(group, 130, tooltip_text=tooltip_text)

            for mode_id, mode_name in zip(mode_ids, mode_names):
                combobox.add_item(mode_id, mode_name, get_command(axis, mode_id))

            combobox.update_popup_menu()
            self._comboboxes[f"layer_wrap_{axis}"] = combobox
            sizer.add(combobox, proportion_h=1., alignment_v="center_v")

        group.add((0, 5))

        val_id = "layer_wrap_lock"
        text = "Lock U and V modes"
        checkbtn = PanelCheckButton(group, self.__toggle_layer_wrap_lock, text)
        self._checkbuttons[val_id] = checkbtn
        group.add(checkbtn)

        group = section.add_group("Filtering")

        get_command = lambda minmag, type_id: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                          self._selected_mat_id,
                                                                          self._selected_layer_id,
                                                                          f"filter_{minmag}",
                                                                          type_id)

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=5)
        group.add(sizer, expand=True)

        text = "-:"
        sizer.add(PanelText(group, text), alignment_v="center_v")
        tooltip_text = "Minification filter"
        combobox = PanelComboBox(group, 130, tooltip_text=tooltip_text)

        type_ids = ("linear", "nearest", "nearest_mipmap_nearest", "nearest_mipmap_linear",
                    "linear_mipmap_nearest", "linear_mipmap_linear", "shadow")
        type_names = ("Linear", "Nearest", "Nearest mipmap nearest", "Nearest mipmap linear",
                      "Linear mipmap nearest", "Linear mipmap linear", "Shadow")

        for type_id, type_name in zip(type_ids, type_names):
            combobox.add_item(type_id, type_name, get_command("min", type_id))

        combobox.update_popup_menu()
        self._comboboxes["layer_filter_min"] = combobox
        sizer.add(combobox, proportion_h=1., alignment_v="center_v")

        text = "+:"
        sizer.add(PanelText(group, text), alignment_v="center_v")
        tooltip_text = "Magnification filter"
        combobox = PanelComboBox(group, 130, tooltip_text=tooltip_text)

        type_ids = ("linear", "nearest")
        type_names = ("Linear", "Nearest")

        for type_id, type_name in zip(type_ids, type_names):
            combobox.add_item(type_id, type_name, get_command("mag", type_id))

        combobox.update_popup_menu()
        self._comboboxes["layer_filter_mag"] = combobox
        sizer.add(combobox, proportion_h=1., alignment_v="center_v")

        group.add((0, 5))

        sizer = Sizer("horizontal")
        group.add(sizer)
        borders = (0, 5, 0, 0)
        text = "Anisotropic level:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "layer_anisotropic_degree"
        field = PanelSliderField(group, val_id, "int", (1, 16), self.__handle_layer_value, 60)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        section.add((0, 5))

        sizer = Sizer("horizontal")
        section.add(sizer, alignment="center_h")
        text = "UV set:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        val_id = "layer_uv_set"
        field = PanelSliderField(section, val_id, "int", (0, 7), self.__handle_layer_value, 60)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        # *************************** Layer transform section *****************

        section = self.add_section("layer_xform", "Layer transform")

        group = section.add_group("Offset")
        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        borders = (0, 5, 0, 0)

        text = "U:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "layer_offset_u"
        field = PanelInputField(group, val_id, "float", self.__handle_layer_value, 55)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        sizer.add((0, 0), proportion=1.)

        text = "V:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "layer_offset_v"
        field = PanelInputField(group, val_id, "float", self.__handle_layer_value, 55)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        section.add((0, 10))

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)
        text = "Rotation:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        val_id = "layer_rotate"
        field = PanelSliderField(section, val_id, "float", (-180., 180.), self.__handle_layer_value, 90)
        field.set_input_parser(self.__parse_angle_input)
        field.set_value(0.)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v", proportion=1.)

        group = section.add_group("Scale")
        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        text = "U:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "layer_scale_u"
        field = PanelInputField(group, val_id, "float", self.__handle_layer_value, 55)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        sizer.add((0, 0), proportion=1.)

        text = "V:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "layer_scale_v"
        field = PanelInputField(group, val_id, "float", self.__handle_layer_value, 55)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        # ************************* Layer blending section ********************

        section = self.add_section("layer_blending", "Layer blending")

        group = section.add_group("Basic blending")
        combobox = PanelComboBox(group, 140, tooltip_text="Blend mode")

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

        combobox.update_popup_menu()
        self._comboboxes["layer_blend_mode"] = combobox
        group.add(combobox, expand=True)

        group = section.add_group("Advanced combining")

        text = "Using any combine mode\noverrides basic blend mode"
        group.add(PanelText(group, text))

        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        val_id = "layer_combine_channels_use"
        checkbtn = PanelCheckButton(group, self.__toggle_layer_combine_channels)
        self._checkbuttons[val_id] = checkbtn
        sizer.add(checkbtn, alignment="center_v", borders=borders)

        combobox = PanelComboBox(group, 100, tooltip_text="Channels")
        get_command = lambda channels: lambda: Mgr.update_remotely("tex_layer_prop",
                                                                   self._selected_mat_id,
                                                                   self._selected_layer_id,
                                                                   "combine_channels",
                                                                   channels)

        for item_id, item_label in (("rgb", "RGB"), ("alpha", "Alpha")):
            combobox.add_item(item_id, item_label, get_command(item_id))

        combobox.update_popup_menu()
        self._comboboxes["layer_combine_channels"] = combobox
        sizer.add(combobox, proportion=1., alignment="center_v")

        group.add((0, 10))

        combobox = PanelComboBox(group, 140, tooltip_text="Combine mode")
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

        combobox.update_popup_menu()
        self._comboboxes["layer_combine_mode"] = combobox
        group.add(combobox, expand=True)

        subgroup = group.add_group("Sources")

        combobox = PanelComboBox(subgroup, 125, tooltip_text="Source type")
        self._comboboxes["layer_combine_source_index"] = combobox
        subgroup.add(combobox, expand=True)

        subgroup.add((0, 10))
        combobox = PanelComboBox(subgroup, 125, tooltip_text="Source")
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

        combobox.update_popup_menu()
        self._comboboxes["layer_combine_source"] = combobox
        subgroup.add(combobox, expand=True)

        radio_btns = PanelRadioButtonGroup(subgroup, columns=2, gap_h=10)
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

        self._radio_btns["layer_combine_source_channels"] = radio_btns
        subgroup.add(radio_btns.sizer)

        group.add((0, 5))

        val_id = "layer_stored"
        text = "Store layer"
        checkbtn = PanelCheckButton(group, self.__store_layer, text)
        self._checkbuttons[val_id] = checkbtn
        group.add(checkbtn)

        # **************************************************************************

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

        self.get_section("scene").expand(False)
        self.get_section("library").expand(False)
        self.get_section("basic_props").expand(False)
        self.get_section("tex_maps").expand(False)
        self.get_section("tex_map_xform").expand(False)
        self.get_section("layers").expand(False)
        self.get_section("layer_color").expand(False)
        self.get_section("layer_tex").expand(False)
        self.get_section("layer_xform").expand(False)
        self.get_section("layer_blending").expand(False)
        self.expand(False)

    def __enter_owner_picking_mode(self, prev_state_id, active):

        Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
        self._btns[f"owner_picking_{self._picking_op}"].active = True

    def __exit_owner_picking_mode(self, next_state_id, active):

        if not active:
            self._btns[f"owner_picking_{self._picking_op}"].active = False
            self._picking_op = ""

    def __toggle_material_name_editable(self):

        combobox = self._comboboxes["material"]
        show = combobox.is_input_field_hidden()
        combobox.show_input_field(show)
        self._edit_mat_name_btn.active = show

    def __toggle_layer_name_editable(self):

        combobox = self._comboboxes["layer"]
        show = combobox.is_input_field_hidden()
        combobox.show_input_field(show)
        self._edit_layer_name_btn.active = show

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
            name = combobox.get_item_text(mat_id)
            self._fields["name"].set_value(name)
            self._selected_mat_id = mat_id
            self._comboboxes["layer"].clear()
            Mgr.update_remotely("material_selection", mat_id)

    def __save_library(self):

        on_yes = lambda filename: Mgr.update_remotely("material_library", "save", filename)
        file_types = ("Material libraries|mtlib", "All types|*")
        FileDialog(title="Save material library",
                   ok_alias="Save",
                   on_yes=on_yes,
                   file_op="write",
                   incr_filename=True,
                   file_types=file_types)

    def __load_library(self, merge=False):

        if self._radio_btns["lib_load_src"].get_selected_button() == "scene":
            Mgr.update_remotely("material_library", "merge" if merge else "load")
            return

        alias = "Merge" if merge else "Load"
        on_yes = lambda filename: Mgr.update_remotely("material_library", alias.lower(), filename)
        file_types = ("Material libraries|mtlib", "All types|*")
        FileDialog(title=f"{alias} material library",
                   ok_alias=alias,
                   file_op="read",
                   on_yes=on_yes,
                   file_types=file_types)

    def __clear_scene(self):

        Mgr.update_remotely("scene_materials", "clear")

    def __clear_library(self):

        self._selected_mat_id = None
        self._comboboxes["material"].clear()

        Mgr.update_remotely("material_library", "clear")

    def __update_library(self, update_type):

        if update_type == "clear":
            self._selected_mat_id = None
            self._comboboxes["material"].clear()

    def __parse_angle_input(self, input_text):

        try:
            return (float(eval(input_text)) + 180.) % 360. - 180.
        except:
            return None

    def __handle_value(self, value_id, value, state="done"):

        mat_id = self._selected_mat_id

        if value_id in ("shininess", "alpha"):
            prop_data = {"value": value}
            Mgr.update_remotely("material_prop", mat_id, value_id, prop_data)
        else:
            Mgr.update_remotely("material_prop", mat_id, value_id, value)

    def __handle_layer_value(self, value_id, value, state="done"):

        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id
        prop_id = value_id.replace("layer_", "", 1)

        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, prop_id, value)

    def __get_color_handler(self, value_id):

        def handle_color(color):

            r, g, b = color
            mat_id = self._selected_mat_id
            prop_data = {"value": (r, g, b, 1.)}
            Mgr.update_remotely("material_prop", mat_id, value_id, prop_data)

        return handle_color

    def __handle_flat_color(self, color):

        r, g, b = color
        mat_id = self._selected_mat_id
        Mgr.update_remotely("material_prop", mat_id, "flat_color", (r, g, b, 1.))

    def __handle_layer_rgb(self, color):

        r, g, b = color
        alpha = self._fields["layer_alpha"].get_value()
        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id

        Mgr.update_remotely("tex_layer_prop", mat_id,layer_id, "color", (r, g, b, alpha))

    def __handle_layer_alpha(self, alpha):

        r, g, b = self._colorboxes["layer_rgb"].get_color()
        color = (r, g, b, alpha)
        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id

        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, "color", color)

    def __handle_border_color(self, color):

        r, g, b = color
        mat_id = self._selected_mat_id

        Mgr.update_remotely("material_prop", mat_id, "tex_map_border_color", (r, g, b, 1.))

    def __handle_layer_border_color(self, color):

        r, g, b = color
        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id

        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, "border_color", (r, g, b, 1.))

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

    def __parse_name(self, input_text):

        name = input_text.strip(" *")

        return name if name else None

    def __parse_shininess_input(self, input_text):

        try:
            return abs(float(eval(input_text)))
        except:
            return None

    def __parse_alpha_input(self, input_text):

        try:
            return min(1., max(0., abs(float(eval(input_text)))))
        except:
            return None

    def __set_material_property(self, mat_id, prop_id, value):

        if prop_id == "name":
            if self._selected_mat_id == mat_id:
                self._fields[prop_id].set_value(value)
            self._comboboxes["material"].set_item_text(mat_id, value)
        elif prop_id == "show_vert_colors":
            self._checkbuttons[prop_id].check(value)
        elif prop_id == "flat_color":
            self._colorboxes[prop_id].set_color(value[:3])
        elif prop_id == "shininess":
            self._fields[prop_id].set_value(value["value"])
        elif prop_id == "alpha":
            self._checkbuttons[prop_id].check(value["on"])
            self._fields[prop_id].set_value(value["value"])
        elif prop_id in self._base_prop_ids:
            self._checkbuttons[prop_id].check(value["on"])
            self._colorboxes[prop_id].set_color(value["value"][:3])
        elif prop_id == "layers_on":
            self._checkbuttons["layers"].check(value)
        elif prop_id == "tex_map_select":
            self._map_type = value
            self._comboboxes["map_type"].select_item(value)
        elif prop_id == "tex_map_on":
            self._checkbuttons["tex_map"].check(value)
        elif prop_id == "tex_map_file_main":
            self._tex_map_file_main = value
            self._fields[prop_id].set_value(value)
        elif prop_id == "tex_map_file_alpha":
            self._tex_map_file_alpha = value
            self._fields[prop_id].set_value(value)
        elif prop_id == "tex_map_border_color":
            self._colorboxes[prop_id].set_color(value[:3])
        elif prop_id == "tex_map_wrap_u":
            self._comboboxes[prop_id].select_item(value)
        elif prop_id == "tex_map_wrap_v":
            self._comboboxes[prop_id].select_item(value)
        elif prop_id == "tex_map_wrap_lock":
            self._checkbuttons[prop_id].check(value)
        elif prop_id == "tex_map_filter_min":
            self._comboboxes[prop_id].select_item(value)
        elif prop_id == "tex_map_filter_mag":
            self._comboboxes[prop_id].select_item(value)
        elif prop_id == "tex_map_anisotropic_degree":
            self._fields[prop_id].set_value(value)
        elif prop_id == "tex_map_transform":
            u, v = value["offset"]
            rot = value["rotate"][0]
            su, sv = value["scale"]
            self._fields["tex_map_offset_u"].set_value(u)
            self._fields["tex_map_offset_v"].set_value(v)
            self._fields["tex_map_rotate"].set_value(rot)
            self._fields["tex_map_scale_u"].set_value(su)
            self._fields["tex_map_scale_v"].set_value(sv)
        elif prop_id in ("tex_map_offset_u", "tex_map_offset_v", "tex_map_rotate",
                         "tex_map_scale_u", "tex_map_scale_v"):
            self._fields[prop_id].set_value(value)
        elif prop_id == "layers":
            get_command = lambda layer_id: lambda: self.__select_layer(layer_id)
            combobox = self._comboboxes["layer"]
            for layer_id, name in value:
                combobox.add_item(layer_id, name, get_command(layer_id))
            combobox.update_popup_menu()

    def __select_material(self, mat_id):

        combobox = self._comboboxes["material"]
        combobox.select_item(mat_id)
        name = combobox.get_item_text(mat_id)
        self._fields["name"].set_value(name)
        self._selected_mat_id = mat_id
        self._comboboxes["layer"].clear()
        Mgr.update_remotely("material_selection", mat_id)

    def __update_new_material(self, mat_id, name="", select=True):

        self._comboboxes["material"].add_item(mat_id, name,
                                              lambda: self.__select_material(mat_id),
                                              update=True)

        if select:
            self.__select_material(mat_id)

    def __select_material_owners(self):

        Mgr.update_remotely("material_owners", self._selected_mat_id)

    def __check_texture_filename(self, filename):

        return filename if (not filename or os.path.exists(filename)) else None

    def __parse_texture_filename(self, filename):

        return os.path.basename(filename) if filename else "<None>"

    def __load_texture_file(self, map_type, channel_type, command):

        def load(tex_filename):

            config_data = GD["config"]
            texfile_paths = config_data["texfile_paths"]
            path = os.path.dirname(tex_filename)

            if path not in texfile_paths:
                texfile_paths.append(path)

            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

            command(tex_filename)

        channel_descr = "main" if channel_type == "rgb" else "alpha channel of"
        caption = "Load " + channel_descr + f" {map_type} texture map"
        file_types = ("Bitmap files|bmp;jpg;png", "All types|*")

        FileDialog(title=caption,
                   ok_alias="Load",
                   on_yes=load,
                   file_op="read",
                   file_types=file_types)

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

        def command(rgb_filename):

            self._fields["tex_map_file_main"].set_value(rgb_filename)
            self._tex_map_file_main = rgb_filename
            self.__set_texture_map()

        self.__load_texture_file(self._map_type, "rgb", command)

    def __load_texture_map_alpha(self):

        def command(alpha_filename):

            self._fields["tex_map_file_alpha"].set_value(alpha_filename)
            self._tex_map_file_alpha = alpha_filename

            if self._tex_map_file_main:
                self.__set_texture_map()

        self.__load_texture_file(self._map_type, "alpha", command)

    def __init_main_filename_input(self):

        field = self._fields["tex_map_file_main"]

        if self._tex_map_file_main:
            field.set_input_text(self._tex_map_file_main)
        else:
            field.clear(forget=False)

    def __init_alpha_filename_input(self):

        field = self._fields["tex_map_file_alpha"]

        if self._tex_map_file_alpha:
            field.set_input_text(self._tex_map_file_alpha)
        else:
            field.clear(forget=False)

    def __set_texture_map_main(self, filename):

        self._tex_map_file_main = filename
        self.__set_texture_map()

    def __set_texture_map_alpha(self, filename):

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
            name = combobox.get_item_text(layer_id)
            self._fields["layer_name"].set_value(name)
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

        combobox.update_popup_menu()

    def __store_layer(self, on):

        mat_id = self._selected_mat_id
        layer_id = self._selected_layer_id
        prop_id = "stored"
        Mgr.update_remotely("tex_layer_prop", mat_id, layer_id, prop_id, on)

    def __set_layer_property(self, layer_id, prop_id, value):

        if self._selected_layer_id != layer_id:
            return

        val_id = "layer_" + prop_id

        if prop_id == "name":
            self._fields[val_id].set_value(value)
            self._comboboxes["layer"].set_item_text(layer_id, value)
        elif prop_id == "color":
            self._colorboxes["layer_rgb"].set_color(value[:3])
            self._fields["layer_alpha"].set_value(value[3])
        elif prop_id == "rgb_scale":
            self._radio_btns[val_id].set_selected_button(value)
        elif prop_id == "alpha_scale":
            self._radio_btns[val_id].set_selected_button(value)
        elif prop_id == "on":
            self._checkbuttons[val_id].check(value)
        elif prop_id == "file_main":
            self._layer_file_main = value
            self._fields[val_id].set_value(value)
        elif prop_id == "file_alpha":
            self._layer_file_alpha = value
            self._fields[val_id].set_value(value)
        elif prop_id == "sort":
            self._fields[val_id].set_value(value)
            self._comboboxes["layer"].set_item_index(layer_id, value)
        elif prop_id == "priority":
            self._fields[val_id].set_value(value)
        elif prop_id == "border_color":
            self._colorboxes[val_id].set_color(value[:3])
        elif prop_id == "wrap_u":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "wrap_v":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "wrap_lock":
            self._checkbuttons[val_id].check(value)
        elif prop_id == "filter_min":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "filter_mag":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "anisotropic_degree":
            self._fields[val_id].set_value(value)
        elif prop_id == "uv_set":
            self._fields[val_id].set_value(value)
        elif prop_id == "transform":
            u, v = value["offset"]
            rot = value["rotate"][0]
            su, sv = value["scale"]
            self._fields["layer_offset_u"].set_value(u)
            self._fields["layer_offset_v"].set_value(v)
            self._fields["layer_rotate"].set_value(rot)
            self._fields["layer_scale_u"].set_value(su)
            self._fields["layer_scale_v"].set_value(sv)
        elif prop_id in ("offset_u", "offset_v", "rotate", "scale_u", "scale_v"):
            self._fields[val_id].set_value(value)
        elif prop_id == "blend_mode":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "combine_mode":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "combine_channels":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "combine_channels_use":
            self._checkbuttons[val_id].check(value)
        elif prop_id == "combine_source_count":
            self.__set_source_types(value)
        elif prop_id == "combine_source_index":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "combine_source":
            self._comboboxes[val_id].select_item(value)
        elif prop_id == "combine_source_channels":
            self._radio_btns[val_id].set_selected_button(value)
        elif prop_id == "stored":
            self._checkbuttons[val_id].check(value)

    def __select_layer(self, layer_id):

        combobox = self._comboboxes["layer"]
        combobox.select_item(layer_id)
        name = combobox.get_item_text(layer_id)
        self._fields["layer_name"].set_value(name)
        self._selected_layer_id = layer_id
        Mgr.update_remotely("tex_layer_selection", self._selected_mat_id, layer_id)

    def __update_new_layer(self, layer_id, name="", select=True):

        self._comboboxes["layer"].add_item(layer_id, name,
                                           lambda: self.__select_layer(layer_id),
                                           update=True)

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

        def command(rgb_filename):

            self._fields["layer_file_main"].set_value(rgb_filename)
            self._layer_file_main = rgb_filename
            self.__set_layer()

        self.__load_texture_file("layer", "rgb", command)

    def __load_layer_alpha(self):

        def command(alpha_filename):

            self._fields["layer_file_alpha"].set_value(alpha_filename)
            self._layer_file_alpha = alpha_filename

            if self._layer_file_main:
                self.__set_layer()

        self.__load_texture_file("layer", "alpha", command)

    def __init_layer_main_filename_input(self):

        field = self._fields["layer_file_main"]

        if self._layer_file_main:
            field.set_input_text(self._layer_file_main)
        else:
            field.clear(forget=False)

    def __init_layer_alpha_filename_input(self):

        field = self._fields["layer_file_alpha"]

        if self._layer_file_alpha:
            field.set_input_text(self._layer_file_alpha)
        else:
            field.clear(forget=False)

    def __set_layer_main(self, filename):

        self._layer_file_main = filename
        self.__set_layer()

    def __set_layer_alpha(self, filename):

        self._layer_file_alpha = filename

        if self._layer_file_main:
            self.__set_layer()


class MaterialToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "material", "Material")

        self._btns = {}
        self._fields = {}
        self._comboboxes = {}
        self._checkbuttons = {}
        self._colorboxes = {}

        borders = (0, 5, 0, 0)

        tooltip_text = "Selected texture map"
        combobox = ToolbarComboBox(self, 95, "", "", tooltip_text)
        self.add(combobox, borders=borders, alignment="center_v")
        self._comboboxes["map_type"] = combobox

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

        combobox.update_popup_menu()

        icon_id = "icon_open"
        tooltip_text = "Load texture map"
        btn = ToolbarButton(self, "", icon_id, tooltip_text, self.__load_texture)
        self.add(btn, borders=borders, alignment="center_v")
        self._btns["load_map"] = btn

        icon_id = "icon_clear_one"
        tooltip_text = "Clear selected texture map"
        btn = ToolbarButton(self, "", icon_id, tooltip_text, self.__clear_texture)
        self.add(btn, borders=borders, alignment="center_v")
        self._btns["clear_map"] = btn

        icon_id = "icon_clear_all"
        tooltip_text = "Clear all texture maps"
        btn = ToolbarButton(self, "", icon_id, tooltip_text, self.__clear_all_textures)
        self.add(btn, borders=borders, alignment="center_v")
        self._btns["clear_all_maps"] = btn

        self.add(ToolbarSeparator(self), borders=borders)

        checkbtn = ToolbarCheckButton(self, self.__toggle_color)
        checkbtn.check()
        self.add(checkbtn, borders=borders, alignment="center_v")
        self._checkbuttons["color_type"] = checkbtn

        tooltip_text = "Selected material color"
        combobox = ToolbarComboBox(self, 95, "", "", tooltip_text)
        self.add(combobox, borders=borders, alignment="center_v")
        self._comboboxes["color_type"] = combobox

        self._color_type = "diffuse"

        def get_command(color_type):

            def set_color_type():

                Mgr.update_remotely("ready_material_color_selection", color_type)

            return set_color_type

        color_types = ("diffuse", "ambient", "emissive", "specular", "alpha")
        texts = ("Diffuse", "Ambient", "Emissive", "Specular", "Transp./opacity")

        for color_type, text in zip(color_types, texts):
            combobox.add_item(color_type, text, get_command(color_type))

        colorbox = ToolbarColorBox(self, self.__handle_color)
        self.add(colorbox, borders=borders, alignment="center_v")
        self._colorboxes["color_type"] = colorbox

        icon_id = "icon_apply_one"
        tooltip_text = "Apply selected material color"
        command = lambda: Mgr.update_remotely("selected_obj_mat_prop", self._color_type)
        btn = ToolbarButton(self, "", icon_id, tooltip_text, command)
        self.add(btn, borders=borders, alignment="center_v")
        self._btns["apply_color"] = btn

        self.add(ToolbarSeparator(self), borders=borders)

        self.add(ToolbarText(self, "Shininess: "), borders=borders, alignment="center_v")
        val_id = "shininess"
        field = ToolbarInputField(self, val_id, "float", self.__handle_value, 70)
        self.add(field, borders=borders, alignment="center_v")
        field.set_input_parser( self.__parse_shininess_input)
        self._fields[val_id] = field

        tooltip_text = "Apply shininess"
        command = lambda: Mgr.update_remotely("selected_obj_mat_prop", "shininess")
        btn = ToolbarButton(self, "", icon_id, tooltip_text, command)
        self.add(btn, borders=borders, alignment="center_v")
        self._btns["apply_shininess"] = btn

        self.add(ToolbarSeparator(self), borders=borders)

        icon_id = "icon_apply_all"
        tooltip_text = "Apply all material properties"
        command = lambda: Mgr.update_remotely("selected_obj_mat_props")
        btn = ToolbarButton(self, "", icon_id, tooltip_text, command)
        self.add(btn, borders=borders, alignment="center_v")
        self._btns["apply_all"] = btn

        icon_id = "icon_reset_all"
        tooltip_text = "Reset all material properties"
        command = lambda: Mgr.update_remotely("reset_ready_material_props")
        btn = ToolbarButton(self, "", icon_id, tooltip_text, command)
        self.add(btn, borders=borders, alignment="center_v")
        self._btns["reset_all"] = btn

        self.add(ToolbarSeparator(self), borders=borders)

        icon_id = "icon_clear"
        tooltip_text = "Clear material"
        command = lambda: Mgr.update_remotely("applied_material", None, True)
        btn = ToolbarButton(self, "", icon_id, tooltip_text, command)
        self.add(btn, borders=borders, alignment="center_v")
        self._btns["clear_material"] = btn

        Mgr.add_app_updater("ready_material_prop", self.__set_material_property)

    def __add_path_to_config(self, path):

        config_data = GD["config"]
        texfile_paths = config_data["texfile_paths"]

        if path not in texfile_paths:
            texfile_paths.append(path)

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

    def __load_texture(self):

        map_type = self._map_type
        file_types = ("Bitmap files|bmp;jpg;png", "All types|*")

        def load(rgb_filename):

            self.__add_path_to_config(os.path.dirname(rgb_filename))
            tex_data = {
                "map_type": map_type,
                "rgb_filename": rgb_filename,
                "alpha_filename": ""
            }

            def update_obj_tex():

                Mgr.update_remotely("selected_obj_tex", tex_data)

            def show_alpha_dialog():

                def load_alpha_channel(alpha_filename=""):

                    self.__add_path_to_config(os.path.dirname(alpha_filename))
                    tex_data["alpha_filename"] = alpha_filename
                    Mgr.update_remotely("selected_obj_tex", tex_data)

                default_filename = Filename.from_os_specific(rgb_filename)
                FileDialog(title=f"Load alpha channel of {map_type} texture map",
                           ok_alias="Load",
                           on_yes=load_alpha_channel,
                           file_op="read",
                           file_types=file_types,
                           default_filename=default_filename)

            MessageDialog(title="Load alpha channel",
                          message="Do you want to load the alpha channel\nfrom a separate file?",
                          choices="yesnocancel",
                          on_yes=show_alpha_dialog,
                          on_no=update_obj_tex)

        FileDialog(title=f"Load main {map_type} texture map",
                   ok_alias="Load",
                   on_yes=load,
                   file_op="read",
                   file_types=file_types)

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

    def __handle_value(self, value_id, value, state="done"):

        if value_id == "shininess":
            prop_data = {"value": value}
            Mgr.update_remotely("ready_material_prop", value_id, prop_data)

    def __handle_color(self, color):

        if self._color_type == "alpha":
            alpha = sum(color) / 3.
            prop_data = {"value": alpha}
        else:
            r, g, b = color
            prop_data = {"value": (r, g, b, 1.)}

        Mgr.update_remotely("ready_material_prop", self._color_type, prop_data)

        return None, None

    def __toggle_color(self, on):

        prop_data = {"on": on}
        Mgr.update_remotely("ready_material_prop", self._color_type, prop_data)

    def __parse_shininess_input(self, input_text):

        try:
            return abs(float(eval(input_text)))
        except:
            return None

    def __set_material_property(self, prop_id, value):

        if prop_id == "shininess":
            self._fields[prop_id].set_value(value["value"])
        else:
            self._color_type = prop_id
            self._comboboxes["color_type"].select_item(prop_id)
            check = value["on"]
            self._checkbuttons["color_type"].check(check)
            val = value["value"]
            color = (val,) * 3 if prop_id == "alpha" else val[:3]
            self._colorboxes["color_type"].set_color(color)
