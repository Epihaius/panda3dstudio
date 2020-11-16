from ..base import *
from ..button import *
from ..toolbar import *
from ..panel import *
from ..dialogs import *


class MaterialPanel(ControlPanel):

    def __init__(self, pane):

        ControlPanel.__init__(self, pane, "materials")

        widgets = Skin.layout.create(self, "materials")
        self._btns = btns = widgets["buttons"]
        self._radio_btn_grps = radio_btn_grps = widgets["radiobutton_groups"]
        self._comboboxes = comboboxes = widgets["comboboxes"]
        self._checkbuttons = checkbuttons = widgets["checkbuttons"]
        self._colorboxes = colorboxes = widgets["colorboxes"]
        self._fields = fields = widgets["fields"]

        self._picking_op = ""

        self._map_type = "color"
        self._tex_map_file_main = ""
        self._tex_map_file_alpha = ""
        self._layer_file_main = ""
        self._layer_file_alpha = ""

        # ************************** Scene section ****************************

        btn = btns["clear_scene_mats"]
        btn.command = self.__clear_scene

        # ************************* Library section ***************************

        btn = btns["save_lib"]
        btn.command = self.__save_library

        btn = btns["clear_lib"]
        btn.command = self.__clear_library

        btn = btns["load_lib"]
        btn.command = self.__load_library

        btn = btns["merge_lib"]
        btn.command = lambda: self.__load_library(merge=True)

        radio_btns = radio_btn_grps["lib_load_src"]
        radio_btns.set_selected_button("file")

        radio_btns = radio_btn_grps["dupe_mat_load"]
        btn_ids = ("skip", "copy", "replace")

        for btn_id in btn_ids:
            command = lambda handling=btn_id: Mgr.update_app("dupe_material_handling", handling)
            radio_btns.set_button_command(btn_id, command)

        radio_btns.set_selected_button("skip")

        # ************************* Material section **************************

        val_id = "name"
        combobox = comboboxes["material"]
        field = combobox.set_input_field(val_id, "string", self.__handle_value)
        field.set_input_parser(self.__parse_name)
        self._fields[val_id] = field
        combobox.show_input_field(False)

        self._selected_mat_id = None
        self._selected_layer_id = None

        btn = btns["edit_mat_name"]
        btn.command = self.__toggle_material_name_editable

        btn = btns["copy_mat"]
        btn.command = self.__copy_material

        btn = btns["add_mat"]
        btn.command = self.__create_material

        btn = btns["remove_mat"]
        btn.command = self.__remove_material

        btn = btns["extract_mat"]
        btn.command = self.__extract_material

        btn = btns["owner_picking_extract"]
        btn.command = lambda: self.__start_owner_picking("extract")

        btn = btns["apply_mat"]
        btn.command = self.__apply_material

        btn = btns["owner_picking_apply"]
        btn.command = lambda: self.__start_owner_picking("apply")

        btn = btns["owner_select"]
        btn.command = self.__select_material_owners

        radio_btns = radio_btn_grps["owner_sel"]
        btn_ids = ("replace", "add_to", "remove_from")

        for btn_id in btn_ids:
            command = lambda sel_mode=btn_id: Mgr.update_app("material_owner_sel_mode", sel_mode)
            radio_btns.set_button_command(btn_id, command)

        radio_btns.set_selected_button("replace")

        # *********************** Basic props section *************************

        checkbtn = checkbuttons["show_vert_colors"]
        checkbtn.command = self.__toggle_vertex_colors

        colorbox = colorboxes["flat_color"]
        colorbox.command = self.__handle_flat_color
        colorbox.dialog_title = "Pick flat color"

        prop_ids = ("diffuse", "ambient", "emissive", "specular")
        self._base_prop_ids = prop_ids + ("shininess",)

        for prop_id in prop_ids:
            checkbtn = checkbuttons[prop_id]
            checkbtn.command = lambda on, i=prop_id: self.__toggle_color(i, on)
            colorbox = colorboxes[prop_id]
            colorbox.command = lambda color, i=prop_id: self.__handle_color(i, color)
            colorbox.dialog_title = f"Pick {prop_id} color"

        val_id = "shininess"
        field = fields[val_id]
        field.value_id = val_id
        field.value_type = "float"
        field.set_value_handler(self.__handle_value)
        field.set_input_parser(self.__parse_shininess_input)

        val_id = "alpha"
        checkbtn = checkbuttons[val_id]
        checkbtn.command = lambda on, i=val_id: self.__toggle_color(i, on)

        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_value)
        field.set_value_range((0., 1.), False, "float")

        # ************************* Texture maps section ***************************

        checkbtn = checkbuttons["tex_map"]
        checkbtn.command = self.__toggle_tex_map

        combobox = comboboxes["map_type"]

        def set_map_type(map_type):

            self._map_type = map_type
            mat_id = self._selected_mat_id
            Mgr.update_remotely("material_prop", mat_id, "tex_map_select", map_type)

        for map_type in ("color", "normal", "height", "normal+height", "gloss",
                         "color+gloss", "normal+gloss", "glow", "color+glow",
                         "vertex color"):
            command = lambda m=map_type: set_map_type(m)
            combobox.add_item(map_type, map_type.title(), command)

        combobox.update_popup_menu()

        val_id = "tex_map_file_main"
        btn = btns[val_id]
        btn.command = self.__load_texture_map_main

        handler = lambda *args: self.__set_texture_map_main(args[1])
        field = fields[val_id]
        field.value_id = val_id
        field.value_type = "string"
        field.set_input_init(self.__init_main_filename_input)
        field.set_input_parser(self.__check_texture_filename)
        field.set_value_parser(self.__parse_texture_filename)
        field.set_value_handler(handler)

        val_id = "tex_map_file_alpha"
        btn = btns[val_id]
        btn.command = self.__load_texture_map_alpha

        handler = lambda *args: self.__set_texture_map_alpha(args[1])
        field = fields[val_id]
        field.value_id = val_id
        field.value_type = "string"
        field.set_input_init(self.__init_alpha_filename_input)
        field.set_input_parser(self.__check_texture_filename)
        field.set_value_parser(self.__parse_texture_filename)
        field.set_value_handler(handler)

        colorbox = colorboxes["tex_map_border_color"]
        colorbox.command = self.__handle_border_color
        colorbox.dialog_title = "Pick texture border color"

        mode_ids = ("repeat", "clamp", "border_color", "mirror", "mirror_once")
        mode_names = ("Repeat", "Clamp", "Border color", "Mirror", "Mirror once")

        for axis_id in ("u", "v"):

            combobox = comboboxes[f"tex_map_wrap_{axis_id}"]

            for mode_id, mode_name in zip(mode_ids, mode_names):
                command = lambda a=axis_id, m=mode_id: Mgr.update_remotely("material_prop",
                    self._selected_mat_id, f"tex_map_wrap_{a}", m)
                combobox.add_item(mode_id, mode_name, command)

            combobox.update_popup_menu()

        checkbtn = checkbuttons["tex_map_wrap_lock"]
        checkbtn.command = self.__toggle_wrap_lock

        combobox = comboboxes["tex_map_filter_min"]
        type_ids = ("linear", "nearest", "nearest_mipmap_nearest", "nearest_mipmap_linear",
                    "linear_mipmap_nearest", "linear_mipmap_linear", "shadow")
        type_names = ("Linear", "Nearest", "Nearest mipmap nearest", "Nearest mipmap linear",
                      "Linear mipmap nearest", "Linear mipmap linear", "Shadow")

        for type_id, type_name in zip(type_ids, type_names):
            command = lambda t=type_id: Mgr.update_remotely("material_prop",
                self._selected_mat_id, "tex_map_filter_min", t)
            combobox.add_item(type_id, type_name, command)

        combobox.update_popup_menu()

        combobox = comboboxes["tex_map_filter_mag"]
        type_ids = ("linear", "nearest")
        type_names = ("Linear", "Nearest")

        for type_id, type_name in zip(type_ids, type_names):
            command = lambda t=type_id: Mgr.update_remotely("material_prop",
                self._selected_mat_id, "tex_map_filter_mag", t)
            combobox.add_item(type_id, type_name, command)

        combobox.update_popup_menu()

        val_id = "tex_map_anisotropic_degree"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_value)
        field.set_value_range((1, 16), False, "int")
        field.set_step(1)

        # *************************** Tex. map transform section ****************

        for val_id in ("tex_map_offset_u", "tex_map_offset_v"):
            field = fields[val_id]
            field.value_id = val_id
            field.set_value_handler(self.__handle_value)
            field.set_value_range(None, False, "float")
            field.set_step(.001)

        val_id = "tex_map_rotate"
        field = fields[val_id]
        field.value_id = val_id
        field.set_input_parser(self.__parse_angle_input)
        field.set_value_handler(self.__handle_value)
        field.set_value_range((-180., 180.), False, "float")
        field.set_step(.1)
        field.set_value(0.)

        for val_id in ("tex_map_scale_u", "tex_map_scale_v"):
            field = fields[val_id]
            field.value_id = val_id
            field.set_value_handler(self.__handle_value)
            field.set_value_range(None, False, "float")
            field.set_step(.01)

        # *************************** Layer section ***************************

        checkbtn = checkbuttons["layers"]
        checkbtn.command = self.__toggle_layers

        checkbtn = checkbuttons["layer_on"]
        checkbtn.command = self.__toggle_layer

        combobox = comboboxes["layer"]
        val_id = "layer_name"
        field = combobox.set_input_field(val_id, "string", self.__handle_layer_value)
        field.set_input_parser(self.__parse_name)
        fields[val_id] = field
        combobox.show_input_field(False)

        btn = btns["edit_layer_name"]
        btn.command = self.__toggle_layer_name_editable

        btn = btns["copy_layer"]
        btn.command = self.__copy_layer

        btn = btns["add_layer"]
        btn.command = self.__create_layer

        btn = btns["remove_layer"]
        btn.command = self.__remove_layer

        val_id = "layer_sort"
        field = fields[val_id]
        field.value_id = val_id
        field.value_type = "int"
        field.set_value_handler(self.__handle_layer_value)

        val_id = "layer_priority"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_layer_value)
        field.set_value_range(None, False, "int")
        field.set_step(1)

        # *************************** Layer color section *********************

        colorbox = colorboxes["layer_rgb"]
        colorbox.command = self.__handle_layer_rgb
        colorbox.dialog_title = "Pick layer color"

        val_id = "layer_alpha"
        field = fields[val_id]
        field.value_id = val_id
        handler = lambda *args: self.__handle_layer_alpha(args[1])
        field.set_value_handler(handler)
        field.set_value_range((0., 1.), False, "float")

        for channels in ("rgb", "alpha"):

            radio_btns = radio_btn_grps[f"layer_{channels}_scale"]
            btn_ids = ("1", "2", "4")
            scales = (1, 2, 4)

            for btn_id, scale in zip(btn_ids, scales):
                command = lambda ch=channels, sc=scale: Mgr.update_remotely("tex_layer_prop",
                    self._selected_mat_id, self._selected_layer_id, f"{ch}_scale", sc)
                radio_btns.set_button_command(btn_id, command)

        # *************************** Layer texture section *******************

        val_id = "layer_file_main"
        btn = btns[val_id]
        btn.command = self.__load_layer_main

        field = fields[val_id]
        field.value_id = val_id
        field.value_type = "string"
        field.set_input_init(self.__init_layer_main_filename_input)
        field.set_input_parser(self.__check_texture_filename)
        field.set_value_parser(self.__parse_texture_filename)
        handler = lambda *args: self.__set_layer_main(args[1])
        field.set_value_handler(handler)

        val_id = "layer_file_alpha"
        btn = btns[val_id]
        btn.command = self.__load_layer_alpha

        field = fields[val_id]
        field.value_id = val_id
        field.value_type = "string"
        field.set_input_init(self.__init_layer_alpha_filename_input)
        field.set_input_parser(self.__check_texture_filename)
        field.set_value_parser(self.__parse_texture_filename)
        handler = lambda *args: self.__set_layer_alpha(args[1])
        field.set_value_handler(handler)

        colorbox = colorboxes["layer_border_color"]
        colorbox.command = self.__handle_layer_border_color
        colorbox.dialog_title = "Pick layer border color"

        mode_ids = ("repeat", "clamp", "border_color", "mirror", "mirror_once")
        mode_names = ("Repeat", "Clamp", "Border color", "Mirror", "Mirror once")

        for axis_id in ("u", "v"):

            combobox = comboboxes[f"layer_wrap_{axis_id}"]

            for mode_id, mode_name in zip(mode_ids, mode_names):
                command = lambda a=axis_id, m=mode_id: Mgr.update_remotely("tex_layer_prop",
                    self._selected_mat_id, self._selected_layer_id, f"wrap_{a}", m)
                combobox.add_item(mode_id, mode_name, command)

            combobox.update_popup_menu()

        checkbtn = checkbuttons["layer_wrap_lock"]
        checkbtn.command = self.__toggle_layer_wrap_lock

        combobox = comboboxes["layer_filter_min"]
        type_ids = ("linear", "nearest", "nearest_mipmap_nearest", "nearest_mipmap_linear",
                    "linear_mipmap_nearest", "linear_mipmap_linear", "shadow")
        type_names = ("Linear", "Nearest", "Nearest mipmap nearest", "Nearest mipmap linear",
                      "Linear mipmap nearest", "Linear mipmap linear", "Shadow")

        for type_id, type_name in zip(type_ids, type_names):
            command = lambda t=type_id: Mgr.update_remotely("tex_layer_prop",
                self._selected_mat_id, self._selected_layer_id,
                "filter_min", t)
            combobox.add_item(type_id, type_name, command)

        combobox.update_popup_menu()

        combobox = comboboxes["layer_filter_mag"]
        type_ids = ("linear", "nearest")
        type_names = ("Linear", "Nearest")

        for type_id, type_name in zip(type_ids, type_names):
            command = lambda t=type_id: Mgr.update_remotely("tex_layer_prop",
                self._selected_mat_id, self._selected_layer_id,
                "filter_mag", t)
            combobox.add_item(type_id, type_name, command)

        combobox.update_popup_menu()

        val_id = "layer_anisotropic_degree"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_layer_value)
        field.set_value_range((1, 16), False, "int")
        field.set_step(1)

        val_id = "layer_uv_set"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_layer_value)
        field.set_value_range((0, 7), False, "int")
        field.set_step(1)

        # *************************** Layer transform section *****************

        for val_id in ("layer_offset_u", "layer_offset_v"):
            field = fields[val_id]
            field.value_id = val_id
            field.set_value_handler(self.__handle_layer_value)
            field.set_value_range(None, False, "float")
            field.set_step(.001)

        val_id = "layer_rotate"
        field = fields[val_id]
        field.value_id = val_id
        field.set_input_parser(self.__parse_angle_input)
        field.set_value_handler(self.__handle_layer_value)
        field.set_value_range((-180., 180.), False, "float")
        field.set_step(.1)
        field.set_value(0.)

        for val_id in ("layer_scale_u", "layer_scale_v"):
            field = fields[val_id]
            field.value_id = val_id
            field.set_value_handler(self.__handle_layer_value)
            field.set_value_range(None, False, "float")
            field.set_step(.01)

        # ************************* Layer blending section ********************

        combobox = comboboxes["layer_blend_mode"]
        mode_ids = ("modulate", "blend", "replace", "decal", "add",
                    "blend_color_scale", "selector")
        mode_names = ("Modulate", "Blend", "Replace", "Decal", "Add",
                      "Blend color scale", "Selector")

        for mode_id, mode_name in zip(mode_ids, mode_names):
            command = lambda m=mode_id: Mgr.update_remotely("tex_layer_prop",
                self._selected_mat_id, self._selected_layer_id,
                "blend_mode", m)
            combobox.add_item(mode_id, mode_name, command)

        combobox.update_popup_menu()

        checkbtn = checkbuttons["layer_combine_channels_use"]
        checkbtn.command = self.__toggle_layer_combine_channels

        combobox = comboboxes["layer_combine_channels"]

        for item_id, item_label in (("rgb", "RGB"), ("alpha", "Alpha")):
            command = lambda channels=item_id: Mgr.update_remotely("tex_layer_prop",
                self._selected_mat_id, self._selected_layer_id,
                "combine_channels", channels)
            combobox.add_item(item_id, item_label, command)

        combobox.update_popup_menu()

        combobox = comboboxes["layer_combine_mode"]
        mode_ids = ("modulate", "replace", "interpolate", "add", "add_signed",
                    "subtract", "dot3rgb", "dot3rgba")
        mode_names = ("Modulate", "Replace", "Interpolate", "Add", "Add signed",
                      "Subtract", "Dot3 RGB", "Dot3 RGBA")

        for mode_id, mode_name in zip(mode_ids, mode_names):
            command = lambda m=mode_id: Mgr.update_remotely("tex_layer_prop",
                self._selected_mat_id, self._selected_layer_id,
                "combine_mode", m)
            combobox.add_item(mode_id, mode_name, command)

        combobox.update_popup_menu()

        combobox = comboboxes["layer_combine_source"]
        src_ids = ("texture", "previous_layer", "primary_color", "constant_color",
                   "const_color_scale", "last_stored_layer")
        src_names = ("Texture", "Previous layer", "Primary color", "Flat color",
                     "Color scale", "Last stored layer")

        for src_id, src_name in zip(src_ids, src_names):
            command = lambda s=src_id: Mgr.update_remotely("tex_layer_prop",
                self._selected_mat_id, self._selected_layer_id,
                "combine_source", s)
            combobox.add_item(src_id, src_name, command)

        combobox.update_popup_menu()

        radio_btns = radio_btn_grps["layer_combine_source_channels"]
        btn_ids = ("rgb", "1-rgb", "alpha", "1-alpha")

        for btn_id in btn_ids:
            command = lambda channels=btn_id: Mgr.update_remotely("tex_layer_prop",
                self._selected_mat_id, self._selected_layer_id,
                "combine_source_channels", channels)
            radio_btns.set_button_command(btn_id, command)

        checkbtn = checkbuttons["layer_stored"]
        checkbtn.command = self.__store_layer

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
        self._btns["edit_mat_name"].active = show

    def __toggle_layer_name_editable(self):

        combobox = self._comboboxes["layer"]
        show = combobox.is_input_field_hidden()
        combobox.show_input_field(show)
        self._btns["edit_layer_name"].active = show

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

        if self._radio_btn_grps["lib_load_src"].get_selected_button() == "scene":
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

    def __handle_color(self, value_id, color):

        r, g, b = color
        mat_id = self._selected_mat_id
        prop_data = {"value": (r, g, b, 1.)}
        Mgr.update_remotely("material_prop", mat_id, value_id, prop_data)

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

        r, g, b = self._colorboxes["layer_rgb"].color
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

    def __toggle_color(self, value_id, on):

        mat_id = self._selected_mat_id
        prop_data = {"on": on}
        Mgr.update_remotely("material_prop", mat_id, value_id, prop_data)

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

    def __set_material_property(self, mat_id, prop_id, value):

        if prop_id == "name":
            if self._selected_mat_id == mat_id:
                self._fields[prop_id].set_value(value)
            self._comboboxes["material"].set_item_text(mat_id, value)
        elif prop_id == "show_vert_colors":
            self._checkbuttons[prop_id].check(value)
        elif prop_id == "flat_color":
            self._colorboxes[prop_id].color = value[:3]
        elif prop_id == "shininess":
            self._fields[prop_id].set_value(value["value"])
        elif prop_id == "alpha":
            self._checkbuttons[prop_id].check(value["on"])
            self._fields[prop_id].set_value(value["value"])
        elif prop_id in self._base_prop_ids:
            self._checkbuttons[prop_id].check(value["on"])
            self._colorboxes[prop_id].color = value["value"][:3]
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
            self._colorboxes[prop_id].color = value[:3]
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
            combobox = self._comboboxes["layer"]
            for layer_id, name in value:
                command = lambda l=layer_id: self.__select_layer(l)
                combobox.add_item(layer_id, name, command)
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

        for i in range(count):
            command = lambda index=i: Mgr.update_remotely("tex_layer_prop",
                self._selected_mat_id, self._selected_layer_id,
                "combine_source_index", index)
            combobox.add_item(i, labels[i], command)

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
            self._colorboxes["layer_rgb"].color = value[:3]
            self._fields["layer_alpha"].set_value(value[3])
        elif prop_id == "rgb_scale":
            self._radio_btn_grps[val_id].set_selected_button(str(value))
        elif prop_id == "alpha_scale":
            self._radio_btn_grps[val_id].set_selected_button(str(value))
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
            self._colorboxes[val_id].color = value[:3]
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
            self._radio_btn_grps[val_id].set_selected_button(value)
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

        Toolbar.__init__(self, parent, "material")

        widgets = Skin.layout.create(self, "material")
        self._btns = widgets["buttons"]
        self._fields = widgets["fields"]
        self._comboboxes = widgets["comboboxes"]
        self._checkbuttons = widgets["checkbuttons"]
        self._colorboxes = widgets["colorboxes"]

        combobox = self._comboboxes["map_type"]

        self._map_type = "color"

        def set_map_type(map_type):

            self._map_type = map_type
            self._comboboxes["map_type"].select_item(map_type)

        for map_type in ("color", "normal", "height", "normal+height", "gloss",
                         "color+gloss", "normal+gloss", "glow", "color+glow",
                         "vertex color"):
            command = lambda m=map_type: set_map_type(m)
            combobox.add_item(map_type, map_type.title(), command)

        combobox.update_popup_menu()

        btn = self._btns["load_map"]
        btn.command = self.__load_texture

        btn = self._btns["clear_map"]
        btn.command = self.__clear_texture

        btn = self._btns["clear_all_maps"]
        btn.command = self.__clear_all_textures

        checkbtn = self._checkbuttons["color_type"]
        checkbtn.command = self.__toggle_color
        checkbtn.check()

        combobox = self._comboboxes["color_type"]

        self._color_type = "diffuse"

        color_types = ("diffuse", "ambient", "emissive", "specular", "alpha")
        texts = ("Diffuse", "Ambient", "Emissive", "Specular", "Transp./opacity")
        update_id = "ready_material_color_selection"

        for color_type, text in zip(color_types, texts):
            command = lambda u=update_id, c=color_type: Mgr.update_remotely(u, c)
            combobox.add_item(color_type, text, command)

        combobox.update_popup_menu()

        colorbox = self._colorboxes["color_type"]
        colorbox.command = self.__handle_color

        btn = self._btns["apply_color"]
        btn.command = lambda: Mgr.update_remotely("selected_obj_mat_prop", self._color_type)

        val_id = "shininess"
        field = self._fields[val_id]
        field.value_id = val_id
        field.set_input_parser(self.__parse_shininess_input)
        field.set_value_handler(self.__handle_value)
        field.set_value_range((0., None), False, "float")
        field.set_step(.1)

        command = lambda: Mgr.update_remotely("selected_obj_mat_prop", "shininess")
        btn = self._btns["apply_shininess"]
        btn.command = command

        btn = self._btns["apply_all"]
        btn.command = lambda: Mgr.update_remotely("selected_obj_mat_props")

        btn = self._btns["reset_all"]
        btn.command = lambda: Mgr.update_remotely("reset_ready_material_props")

        btn = self._btns["clear_material"]
        btn.command = lambda: Mgr.update_remotely("applied_material", None, True)

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
            self._colorboxes["color_type"].color = color
