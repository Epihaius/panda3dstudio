from ..base import *
from ..button import *
from ..toolbar import *
from ..dialog import *
from .snap import SnapToolbar


class AlignTypeComboBox(ToolbarComboBox):

    def __init__(self, toolbar):

        tooltip_text = "Align selected (sub)object(s)"

        ToolbarComboBox.__init__(self, toolbar, 70, tooltip_text=tooltip_text)

        def add_target_type_entry(target_type, target_descr):

            def set_target_type():

                Mgr.update_remotely("object_alignment", "pick_target", target_type)

            self.add_item(target_type, target_descr, set_target_type, select_initial=False)

        target_types = ("view", "object", "obj_point", "surface")
        target_descr = ("view", "object", "object (aim at point)", "surface")

        for target_type, descr in zip(target_types, target_descr):
            add_target_type_entry(target_type, descr)

        self.update_popup_menu()
        self.allow_field_text_in_tooltip(False)
        self.set_text("Align to...")


class SnapAlignToolbar(SnapToolbar):

    def __init__(self, parent):

        SnapToolbar.__init__(self, parent, "snap_align", "Snap/Align")

        borders = (0, 5, 0, 0)
        self.add(ToolbarSeparator(self), borders=borders)

        self._comboboxes = {}
        combobox = AlignTypeComboBox(self)
        self._comboboxes["align_type"] = combobox
        self.add(combobox, borders=borders, alignment="center_v")

        Mgr.add_app_updater("object_alignment", self.__show_object_alignment_dialog)
        Mgr.add_app_updater("grid_alignment", self.__show_grid_alignment_dialog)

    def setup(self):

        SnapToolbar.setup(self)

        def enter_picking_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")

            if not active and GD["active_obj_level"] != "top":
                Mgr.do("enable_selection_dialog")

        def exit_picking_mode(next_state_id, active):

            if not active and GD["active_obj_level"] != "top":
                Mgr.do("disable_selection_dialog")

        def enter_align_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            Mgr.do("enable_gui", False)

        def exit_align_mode(next_state_id, active):

            Mgr.do("enable_gui")

        add_state = Mgr.add_state
        add_state("alignment_target_picking_mode", -80, enter_picking_mode, exit_picking_mode)
        add_state("alignment_target_picking_end", -80)
        add_state("surface_alignment_mode", -80, enter_align_mode, exit_align_mode)

    def __show_object_alignment_dialog(self, dialog_type, *args):

        if dialog_type == "align":
            AlignmentDialog(*args)
        elif dialog_type == "msg":
            msg_type = args[0]
            if msg_type == "invalid_sel":
                MessageDialog(title="Invalid selection",
                              message="No suitable selection for alignment.\n" \
                                      "(Open groups must be closed before they can be aligned.)",
                              choices="ok",
                              icon_id="icon_exclamation")
            elif msg_type == "no_subobj_sel":
                MessageDialog(title="No selection",
                              message="No subobjects are selected for alignment.",
                              choices="ok",
                              icon_id="icon_exclamation")
            elif msg_type == "links":
                MessageDialog(title="Cannot align",
                              message="Object hierarchy links cannot be aligned.",
                              choices="ok",
                              icon_id="icon_exclamation")
            elif msg_type == "invalid_target":
                MessageDialog(title="Invalid alignment target",
                              message="No suitable object picked to align to.\n" \
                                      "(An open group must be closed before it can be used as target.)",
                              choices="ok",
                              icon_id="icon_exclamation")
            elif msg_type == "invalid_surface":
                MessageDialog(title="Invalid surface",
                              message="No surface picked to align to.",
                              choices="ok",
                              icon_id="icon_exclamation")

    def __show_grid_alignment_dialog(self, dialog_type, *args):

        GridAlignmentDialog(*args)


class AlignmentDialog(Dialog):

    def __init__(self, target_type, obj_name=""):

        if target_type == "view":
            title = 'Align to current view'
        elif "obj" in target_type:
            title = f'Align to object ("{obj_name}")'
        else:
            title = f'Align to surface ("{obj_name}")'

        Dialog.__init__(self, title, "okcancel", "Align", self.__on_yes, on_cancel=self.__on_cancel)

        obj_lvl = GD["active_obj_level"]
        xform_target_type = GD["transform_target_type"]
        sel_point_type = "pivot" if xform_target_type == "pivot" else "center"
        align = True if obj_lvl == "normal" or target_type == "obj_point" else False
        tgt_axis = "z" if obj_lvl == "normal" and target_type in ("view", "object") else "y"

        self._options = {
            "axes": {
                "x": {"tgt": "x", "align": False, "inv": False},
                "y": {"tgt": tgt_axis, "align": align, "inv": False},
                "z": {"tgt": "z", "align": False, "inv": False}
            },
            "points": {
                "x": {"sel": sel_point_type, "tgt": "center", "align": False},
                "y": {"sel": sel_point_type, "tgt": "center", "align": align},
                "z": {"sel": sel_point_type, "tgt": "center", "align": False}
            },
            "local_minmax": False,
            "per_vertex": False,
            "planar": False
        }
        self._coord_axis = "x"
        self._sel_obj_axis = "y" if obj_lvl == "normal" or target_type == "obj_point" else "z"
        self._preview = False if obj_lvl == "normal" or target_type == "obj_point" else True

        self._checkbuttons = checkbtns = {}
        self._radio_btns = radio_btn_groups = {}
        self._axis_toggle_btns = None
        self._point_toggle_btns = None
        client_sizer = self.get_client_sizer()

        if obj_lvl == "top" or "obj" in target_type:
            if target_type == "obj_point":
                btn_ids = ("pivot", "center")
                texts = ("Pivot", "Center")
            else:
                btn_ids = ("pivot", "center", "min", "max")
                texts = ("Pivot", "Center", "Minimum", "Maximum")

        def create_axis_align_group(title, add_checkbox=True):

            group = DialogWidgetGroup(self, title)
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            if add_checkbox:

                def align_to_dir(align):

                    self._options["axes"][self._sel_obj_axis]["align"] = align

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                text = "Align local axis:"
                checkbtn = DialogCheckButton(group, align_to_dir, text)
                borders = (5, 0, 10, 0)
                group.add(checkbtn, borders=borders)
                checkbtns["axis"] = checkbtn

            return group

        def create_axis_radio_buttons():

            radio_btns = DialogRadioButtonGroup(group, rows=1, gap_h=10, stretch=True)

            def get_command(axis_id):

                def command():

                    axis_options = self._options["axes"]
                    axis_options[self._sel_obj_axis]["tgt"] = axis_id
                    sel_axis1, sel_axis2 = "xyz".replace(self._sel_obj_axis, "")
                    tgt_axis1, tgt_axis2 = "xyz".replace(axis_id, "")

                    if axis_options[sel_axis1]["tgt"] == axis_id:
                        tgt_axis = tgt_axis1 if axis_options[sel_axis2]["tgt"] != tgt_axis1 else tgt_axis2
                        axis_options[sel_axis1]["tgt"] = tgt_axis
                    elif axis_options[sel_axis2]["tgt"] == axis_id:
                        tgt_axis = tgt_axis1 if axis_options[sel_axis1]["tgt"] != tgt_axis1 else tgt_axis2
                        axis_options[sel_axis2]["tgt"] = tgt_axis

                    if self._preview and axis_options[self._sel_obj_axis]["align"]:
                        Mgr.update_remotely("object_alignment", "", self._options)

                return command

            if target_type == "view":
                radio_btns.add_button("x", "view X-axis")
                radio_btns.set_button_command("x", get_command("x"))
                radio_btns.add_button("y", "view Y-axis")
                radio_btns.set_button_command("y", get_command("y"))
                radio_btns.add_button("z", "view Z-axis")
                radio_btns.set_button_command("z", get_command("z"))
            else:
                for axis_id in "xyz":
                    radio_btns.add_button(axis_id, f"{axis_id.upper()}-axis")
                    radio_btns.set_button_command(axis_id, get_command(axis_id))

            radio_btns.set_selected_button("y" if target_type == "obj_point" else "z")
            enable = "all_axes" not in checkbtns
            radio_btns.enable(enable)
            color = None if enable else (.5, .5, .5, 1.)
            radio_btns.set_bullet_color(color, update=True)
            borders = (5, 0, 0, 0)
            group.add(radio_btns.get_sizer(), expand=True, borders=borders)
            radio_btn_groups["axis"] = radio_btns

        def add_inverted_dir_option(top_border):

            def set_dir_inverted(invert):

                axis_options = self._options["axes"]
                axis_options[self._sel_obj_axis]["inv"] = invert

                if self._preview and axis_options[self._sel_obj_axis]["align"]:
                    Mgr.update_remotely("object_alignment", "", self._options)

            text = "Invert"
            checkbtn = DialogCheckButton(group, set_dir_inverted, text)
            borders = (5, 0, 0, top_border)
            group.add(checkbtn, borders=borders)
            checkbtns["invert"] = checkbtn

        def create_target_point_group(title, group_sizer, axis_id="", borders=None):

            subgroup = DialogWidgetGroup(group, title)

            if obj_lvl == "top" and target_type == "object":
                group_sizer.add((10, 0))
                group_sizer.add(subgroup, proportion=1., expand=True, borders=borders)
                radio_btns = DialogRadioButtonGroup(subgroup, columns=1, gap_v=2)
                subgroup.add(radio_btns.get_sizer())
            else:
                group_sizer.add(subgroup, proportion=1., expand=True, borders=borders)
                radio_btns = DialogRadioButtonGroup(subgroup, columns=2, gap_h=5, gap_v=2, stretch=True)
                subgroup.add(radio_btns.get_sizer(), expand=True)

            def get_command(point_id):

                def command():

                    a_id = axis_id if axis_id else self._coord_axis
                    point_options = self._options["points"]
                    point_options[a_id]["tgt"] = point_id

                    if self._preview and point_options[a_id]["align"]:
                        Mgr.update_remotely("object_alignment", "", self._options)

                return command

            for btn_id, text in zip(btn_ids, texts):
                radio_btns.add_button(btn_id, text)
                radio_btns.set_button_command(btn_id, get_command(btn_id))

            radio_btns.set_selected_button("center")
            radio_btn_groups["tgt_point"] = radio_btns

        if target_type == "surface":

            if obj_lvl == "normal":

                group = DialogWidgetGroup(self, "Align normals")
                borders = (20, 20, 0, 10)
                client_sizer.add(group, expand=True, borders=borders)

            else:

                group = create_axis_align_group("Align to normal")

        elif target_type == "obj_point":

            group_title = f'Aim {"normals" if obj_lvl == "normal" else "local axis"} at point'
            group = create_axis_align_group(group_title, False)

            if obj_lvl != "normal":
                create_axis_radio_buttons()

            add_inverted_dir_option(0 if obj_lvl == "normal" else 10)
            borders = (5, 5, 5, 5)
            create_target_point_group("Target point", group, "y", borders)

        else:

            if obj_lvl == "normal":

                group = DialogWidgetGroup(self, "Align normals")
                borders = (20, 20, 0, 10)
                client_sizer.add(group, expand=True, borders=borders)

            else:

                group = DialogWidgetGroup(self, "Align local axes")
                borders = (20, 20, 0, 10)
                client_sizer.add(group, expand=True, borders=borders)

                subsizer = Sizer("horizontal")
                borders = (5, 0, 2, 0)
                group.add(subsizer, expand=True, borders=borders)

                def align_all_axes(align):

                    checkbtns["all_axes"].check(align)
                    axis_options = self._options["axes"]

                    if align:
                        other_axis_ids = "xyz".replace(self._sel_obj_axis, "")
                        for axis_id in "xyz":
                            if axis_options[axis_id]["align"]:
                                other_axis_ids = other_axis_ids.replace(axis_id, "")
                                axis2_id = axis_id
                        if len(other_axis_ids) == 2:
                            axis2_id, axis3_id = other_axis_ids
                        else:
                            axis3_id = other_axis_ids
                        self._axis_toggle_btns.get_button(axis3_id).enable(False)
                        checkbtn = checkbtns[f"{axis3_id}_axis"]
                        checkbtn.enable(False)
                        checkbtn.set_checkmark_color((.5, .5, .5, 1.))
                        checkbtn.check()
                        for axis_id in (self._sel_obj_axis, axis2_id):
                            checkbtns[f"{axis_id}_axis"].check()
                            axis_options[axis_id]["align"] = True
                    else:
                        for axis_id in "xyz":
                            self._axis_toggle_btns.get_button(axis_id).enable()
                            checkbtn = checkbtns[f"{axis_id}_axis"]
                            checkbtn.enable()
                            checkbtn.set_checkmark_color()
                            checkbtn.check(False)
                            axis_options[axis_id]["align"] = False

                    radio_btn_groups["axis"].enable(align)
                    color = None if align else (.5, .5, .5, 1.)
                    radio_btn_groups["axis"].set_bullet_color(color, update=True)

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                def get_checkbox_command(axis_id):

                    def align_to_dir(align):

                        axis_options = self._options["axes"]
                        axes_aligned = [a_id for a_id in "xyz" if axis_options[a_id]["align"]]
                        axis_count = len(axes_aligned)
                        axis_options[axis_id]["align"] = align
                        checkbtns["all_axes"].check(axis_count == 1 and align)

                        if self._sel_obj_axis == axis_id:
                            radio_btn_groups["axis"].enable(align)
                            color = None if align else (.5, .5, .5, 1.)
                            radio_btn_groups["axis"].set_bullet_color(color, update=True)

                        if axis_count == 2:
                            axis3_id = "xyz".replace(axes_aligned[0], "").replace(axes_aligned[1], "")
                            checkbtn = checkbtns[f"{axis3_id}_axis"]
                            checkbtn.enable()
                            checkbtn.set_checkmark_color()
                            checkbtn.check(False)
                            self._axis_toggle_btns.get_button(axis3_id).enable()
                        elif axis_count == 1 and align:
                            axis3_id = "xyz".replace(axis_id, "").replace(axes_aligned[0], "")
                            checkbtn = checkbtns[f"{axis3_id}_axis"]
                            checkbtn.enable(False)
                            checkbtn.set_checkmark_color((.5, .5, .5, 1.))
                            checkbtn.check()
                            self._axis_toggle_btns.get_button(axis3_id).enable(False)
                            if self._sel_obj_axis == axis3_id:
                                self._axis_toggle_btns.set_active_button(axis_id)
                                options = axis_options[axis_id]
                                checkbtns["invert"].check(options["inv"])
                                radio_btns = radio_btn_groups["axis"]
                                radio_btns.enable()
                                radio_btns.set_bullet_color(update=True)
                                radio_btns.set_selected_button(options["tgt"])
                                self._sel_obj_axis = axis_id

                        if self._preview:
                            Mgr.update_remotely("object_alignment", "", self._options)

                    return align_to_dir

                def get_btn_command(axis_id):

                    def command():

                        self._axis_toggle_btns.set_active_button(axis_id)
                        options = self._options["axes"][axis_id]
                        checkbtns["invert"].check(options["inv"])
                        radio_btn_groups["axis"].enable(options["align"])
                        color = None if options["align"] else (.5, .5, .5, 1.)
                        radio_btn_groups["axis"].set_bullet_color(color, update=True)
                        radio_btn_groups["axis"].set_selected_button(options["tgt"])
                        self._sel_obj_axis = axis_id

                    return command

                text = "XYZ"
                checkbtn = DialogCheckButton(group, align_all_axes, text)
                borders = (0, 10, 0, 0)
                subsizer.add(checkbtn, alignment="center_v", borders=borders)
                checkbtns["all_axes"] = checkbtn
                subsizer.add((0, 0), proportion=1.)

                self._axis_toggle_btns = toggle_btns = ToggleButtonGroup()
                borders = (5, 10, 0, 0)

                for axis_id in "xyz":
                    checkbtn = DialogCheckButton(group, get_checkbox_command(axis_id))
                    subsizer.add(checkbtn, alignment="center_v")
                    checkbtns[f"{axis_id}_axis"] = checkbtn
                    text = axis_id.upper()
                    tooltip_text = f"Selected obj. {axis_id.upper()}-axis"
                    btn = DialogButton(group, text, "", tooltip_text)
                    toggle = (get_btn_command(axis_id), lambda: None)
                    toggle_btns.add_button(btn, axis_id, toggle)
                    subsizer.add(btn, alignment="center_v", borders=borders)
                    subsizer.add((0, 0), proportion=1.)

                toggle_btns.set_active_button("z")

            subgroup = DialogWidgetGroup(group, "Target direction")
            borders = (5, 5, 5, 5)
            group.add(subgroup, proportion=1., expand=True, borders=borders)
            group = subgroup

        if target_type != "obj_point":

            if obj_lvl != "normal" or target_type in ("view", "object"):
                create_axis_radio_buttons()
                top_border = 10
            else:
                top_border = 0

            add_inverted_dir_option(top_border)

        if obj_lvl != "normal" and target_type != "obj_point":

            if target_type == "view":
                text = " to view center"
            elif target_type == "surface":
                text = " to surface point"
            else:
                text = "s" if obj_lvl == "top" else " to point"

            title = f'Align {"point" if obj_lvl == "top" else "center"}{text}'
            group = DialogWidgetGroup(self, title)
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            subsizer = Sizer("horizontal")

            def create_all_coords_checkbox():

                def align_to_point(align):

                    point_options = self._options["points"]
                    axis_ids = "xy" if target_type == "view" else "xyz"

                    for axis_id in axis_ids:
                        checkbtns[f"{axis_id}_coord"].check(align)
                        point_options[axis_id]["align"] = align

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                text = "XY" if target_type == "view" else "XYZ"
                checkbtn = DialogCheckButton(group, align_to_point, text)
                borders = (0, 10, 0, 0)
                subsizer.add(checkbtn, alignment="center_v", borders=borders)
                checkbtns["all_coords"] = checkbtn
                subsizer.add((0, 0), proportion=1.)

            def get_checkbox_command(axis_id):

                def align_to_point(align):

                    point_options = self._options["points"]
                    point_options[axis_id]["align"] = align
                    axis_ids = "xy" if target_type == "view" else "xyz"
                    coords_aligned = [a_id for a_id in axis_ids if point_options[a_id]["align"]]
                    checkbtns["all_coords"].check(len(coords_aligned) == len(axis_ids))

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                return align_to_point

            if obj_lvl == "top" or target_type == "object":

                borders = (5, 0, 0, 0)
                group.add(subsizer, expand=True, borders=borders)

                def get_btn_command(axis_id):

                    def command():

                        self._point_toggle_btns.set_active_button(axis_id)
                        options = self._options["points"][axis_id]

                        if "sel_point" in radio_btn_groups:
                            radio_btn_groups["sel_point"].set_selected_button(options["sel"])

                        if "tgt_point" in radio_btn_groups:
                            radio_btn_groups["tgt_point"].set_selected_button(options["tgt"])

                        self._coord_axis = axis_id

                    return command

                self._point_toggle_btns = toggle_btns = ToggleButtonGroup()

                create_all_coords_checkbox()
                borders = (5, 10, 0, 0)
                tooltip_str = "View {}-axis" if target_type == "view" else "Ref. coord. {}-axis"

                for axis_id in ("xy" if target_type == "view" else "xyz"):
                    checkbtn = DialogCheckButton(group, get_checkbox_command(axis_id))
                    subsizer.add(checkbtn, alignment="center_v")
                    checkbtns[f"{axis_id}_coord"] = checkbtn
                    text = axis_id.upper()
                    tooltip_text = tooltip_str.format(axis_id.upper())
                    btn = DialogButton(group, text, "", tooltip_text)
                    toggle = (get_btn_command(axis_id), lambda: None)
                    toggle_btns.add_button(btn, axis_id, toggle)
                    subsizer.add(btn, alignment="center_v", borders=borders)
                    subsizer.add((0, 0), proportion=1.)

                toggle_btns.set_active_button("x")

            else:

                text_str = f'Along the {"view" if target_type == "view" else "ref. coord."} axes:'
                text = DialogText(group, text_str)
                borders = (5, 0, 5, 0)
                group.add(text, borders=borders)

                borders = (5, 0, 0, 0)
                group.add(subsizer, expand=True, borders=borders)
                create_all_coords_checkbox()
                borders = (0, 10, 0, 0)

                for axis_id in ("xy" if target_type == "view" else "xyz"):
                    text = axis_id.upper()
                    checkbtn = DialogCheckButton(group, get_checkbox_command(axis_id), text)
                    subsizer.add(checkbtn, borders=borders)
                    checkbtns[f"{axis_id}_coord"] = checkbtn
                    subsizer.add((0, 0), proportion=1.)

            subgroup_sizer = Sizer("horizontal")
            borders = (5, 5, 5, 5)
            group.add(subgroup_sizer, expand=True, borders=borders)

            if obj_lvl == "top":

                subgroup = DialogWidgetGroup(group, "Sel. object(s)")
                subgroup_sizer.add(subgroup, proportion=1., expand=True)

                if target_type == "object":
                    radio_btns = DialogRadioButtonGroup(subgroup, columns=1, gap_v=2)
                    subgroup.add(radio_btns.get_sizer())
                else:
                    radio_btns = DialogRadioButtonGroup(subgroup, columns=2, gap_h=10, gap_v=2, stretch=True)
                    subgroup.add(radio_btns.get_sizer(), expand=True)

                def get_command(point_id):

                    def command():

                        point_options = self._options["points"]

                        if point_id == "pivot":
                            if xform_target_type == "geom":
                                prev_point_id = point_options[self._coord_axis]["sel"]
                                radio_btn_groups["sel_point"].set_selected_button(prev_point_id)
                                return
                        elif xform_target_type == "pivot":
                            radio_btn_groups["sel_point"].set_selected_button("pivot")
                            return

                        point_options[self._coord_axis]["sel"] = point_id

                        if self._preview and point_options[self._coord_axis]["align"]:
                            Mgr.update_remotely("object_alignment", "", self._options)

                    return command

                for btn_id, text in zip(btn_ids, texts):
                    radio_btns.add_button(btn_id, text)
                    radio_btns.set_button_command(btn_id, get_command(btn_id))

                radio_btns.set_selected_button("pivot" if xform_target_type == "pivot" else "center")
                radio_btn_groups["sel_point"] = radio_btns

            if target_type == "object":

                create_target_point_group("Target object", subgroup_sizer)

            if obj_lvl == "top" or target_type == "object":

                def command(local):

                    self._options["local_minmax"] = local

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                s = "view" if target_type == "view" else "ref."
                text = f"Local min./max. (ignore {s} coord. sys.)"
                checkbtn = DialogCheckButton(group, command, text)
                borders = (5, 0, 0, 0)
                group.add(checkbtn, borders=borders)
                checkbtns["local_minmax"] = checkbtn

                def command():

                    point_options = self._options["points"]
                    axis_ids = "xy" if target_type == "view" else "xyz"

                    for axis_id in axis_ids:
                        point_options[axis_id]["sel"] = point_options[self._coord_axis]["sel"]
                        point_options[axis_id]["tgt"] = point_options[self._coord_axis]["tgt"]

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                text = "For all axes"
                tooltip_text = "Use these settings for all axes"
                btn = DialogButton(group, text, "", tooltip_text, command)
                borders = (5, 5, 5, 5)
                group.add(btn, borders=borders)

            if obj_lvl != "top":

                def set_align_points_per_vertex(per_vertex):

                    self._options["per_vertex"] = per_vertex

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                text = "Per vertex in selection"
                checkbtn = DialogCheckButton(group, set_align_points_per_vertex, text)
                borders = (5, 0, 0, 0)
                group.add(checkbtn, borders=borders)
                checkbtns["per_vertex"] = checkbtn

        if obj_lvl not in ("top", "normal") and target_type == "view":

            def make_planar(planar):

                self._options["planar"] = planar

                if self._preview:
                    Mgr.update_remotely("object_alignment", "", self._options)

            text = "Make planar"
            checkbtn = DialogCheckButton(self, make_planar, text)
            borders = (20, 20, 0, 10)
            client_sizer.add(checkbtn, borders=borders)
            checkbtns["planar"] = checkbtn

        def enable_preview(preview):

            self._preview = preview
            Mgr.update_remotely("object_alignment", "", self._options, preview, not preview)

        text = "Preview"
        checkbtn = DialogCheckButton(self, enable_preview, text)
        checkbtn.check(False if obj_lvl == "normal" or target_type == "obj_point" else True)
        borders = (20, 20, 15, 10)
        client_sizer.add(checkbtn, borders=borders)
        checkbtns["preview"] = checkbtn

        self.finalize()

    def close(self, answer=""):

        self._checkbuttons = None
        self._radio_btns = None
        self._axis_toggle_btns = None
        self._point_toggle_btns = None

        Dialog.close(self, answer)

    def __on_yes(self):

        Mgr.update_remotely("object_alignment", "", self._options, False)

    def __on_cancel(self):

        Mgr.update_remotely("object_alignment", "cancel")


class GridAlignmentDialog(Dialog):

    def __init__(self, target_type, obj_name=""):

        if target_type == "view":
            title = 'Align grid to current view'
        elif "obj" in target_type:
            title = f'Align grid to object ("{obj_name}")'
        else:
            title = f'Align grid to surface ("{obj_name}")'

        Dialog.__init__(self, title, "okcancel", "Align", self.__on_yes, on_cancel=self.__on_cancel)

        align = target_type == "obj_point"

        self._options = {
            "axes": {
                "x": {"tgt": "x", "align": False, "inv": False},
                "y": {"tgt": "y", "align": align, "inv": False},
                "z": {"tgt": "z", "align": False, "inv": False}
            },
            "points": {
                "x": {"tgt": "center", "align": False},
                "y": {"tgt": "center", "align": align},
                "z": {"tgt": "center", "align": False}
            },
            "local_minmax": False
        }
        self._coord_axis = "x"
        self._sel_obj_axis = "y" if target_type == "obj_point" else "z"
        self._preview = target_type != "obj_point"

        self._checkbuttons = checkbtns = {}
        self._radio_btns = radio_btn_groups = {}
        self._axis_toggle_btns = None
        self._point_toggle_btns = None
        client_sizer = self.get_client_sizer()

        if "obj" in target_type:
            if target_type == "obj_point":
                btn_ids = ("pivot", "center")
                texts = ("Pivot", "Center")
            else:
                btn_ids = ("pivot", "center", "min", "max")
                texts = ("Pivot", "Center", "Minimum", "Maximum")

        def create_axis_align_group(title, add_checkbox=True):

            group = DialogWidgetGroup(self, title)
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            if add_checkbox:

                def align_to_dir(align):

                    self._options["axes"][self._sel_obj_axis]["align"] = align

                    if self._preview:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                text = "Align grid axis:"
                checkbtn = DialogCheckButton(group, align_to_dir, text)
                borders = (5, 0, 10, 0)
                group.add(checkbtn, borders=borders)
                checkbtns["axis"] = checkbtn

            return group

        def create_axis_radio_buttons():

            radio_btns = DialogRadioButtonGroup(group, rows=1, gap_h=10, stretch=True)

            def get_command(axis_id):

                def command():

                    axis_options = self._options["axes"]
                    axis_options[self._sel_obj_axis]["tgt"] = axis_id
                    sel_axis1, sel_axis2 = "xyz".replace(self._sel_obj_axis, "")
                    tgt_axis1, tgt_axis2 = "xyz".replace(axis_id, "")

                    if axis_options[sel_axis1]["tgt"] == axis_id:
                        tgt_axis = tgt_axis1 if axis_options[sel_axis2]["tgt"] != tgt_axis1 else tgt_axis2
                        axis_options[sel_axis1]["tgt"] = tgt_axis
                    elif axis_options[sel_axis2]["tgt"] == axis_id:
                        tgt_axis = tgt_axis1 if axis_options[sel_axis1]["tgt"] != tgt_axis1 else tgt_axis2
                        axis_options[sel_axis2]["tgt"] = tgt_axis

                    if self._preview and axis_options[self._sel_obj_axis]["align"]:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                return command

            if target_type == "view":
                radio_btns.add_button("x", "view X-axis")
                radio_btns.set_button_command("x", get_command("x"))
                radio_btns.add_button("y", "view Y-axis")
                radio_btns.set_button_command("y", get_command("y"))
                radio_btns.add_button("z", "view Z-axis")
                radio_btns.set_button_command("z", get_command("z"))
            else:
                for axis_id in "xyz":
                    radio_btns.add_button(axis_id, f"{axis_id.upper()}-axis")
                    radio_btns.set_button_command(axis_id, get_command(axis_id))

            radio_btns.set_selected_button("y" if target_type == "obj_point" else "z")
            enable = "all_axes" not in checkbtns
            radio_btns.enable(enable)
            color = None if enable else (.5, .5, .5, 1.)
            radio_btns.set_bullet_color(color, update=True)
            borders = (5, 0, 0, 0)
            group.add(radio_btns.get_sizer(), expand=True, borders=borders)
            radio_btn_groups["axis"] = radio_btns

        def add_inverted_dir_option(top_border):

            def set_dir_inverted(invert):

                axis_options = self._options["axes"]
                axis_options[self._sel_obj_axis]["inv"] = invert

                if self._preview and axis_options[self._sel_obj_axis]["align"]:
                    Mgr.update_remotely("grid_alignment", "", self._options)

            text = "Invert"
            checkbtn = DialogCheckButton(group, set_dir_inverted, text)
            borders = (5, 0, 0, top_border)
            group.add(checkbtn, borders=borders)
            checkbtns["invert"] = checkbtn

        def create_target_point_group(title, group_sizer, axis_id="", borders=None):

            subgroup = DialogWidgetGroup(group, title)

            if target_type == "object":
                group_sizer.add((10, 0))
                group_sizer.add(subgroup, proportion=1., expand=True, borders=borders)
                radio_btns = DialogRadioButtonGroup(subgroup, columns=1, gap_v=2)
                subgroup.add(radio_btns.get_sizer())
            else:
                group_sizer.add(subgroup, proportion=1., expand=True, borders=borders)
                radio_btns = DialogRadioButtonGroup(subgroup, columns=2, gap_h=5, gap_v=2, stretch=True)
                subgroup.add(radio_btns.get_sizer(), expand=True)

            def get_command(point_id):

                def command():

                    a_id = axis_id if axis_id else self._coord_axis
                    point_options = self._options["points"]
                    point_options[a_id]["tgt"] = point_id

                    if self._preview and point_options[a_id]["align"]:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                return command

            for btn_id, text in zip(btn_ids, texts):
                radio_btns.add_button(btn_id, text)
                radio_btns.set_button_command(btn_id, get_command(btn_id))

            radio_btns.set_selected_button("center")
            radio_btn_groups["tgt_point"] = radio_btns

        if target_type == "surface":

            group = create_axis_align_group("Align to normal")

        elif target_type == "obj_point":

            group_title = "Aim grid axis at point"
            group = create_axis_align_group(group_title, False)
            create_axis_radio_buttons()
            add_inverted_dir_option(10)
            borders = (5, 5, 5, 5)
            create_target_point_group("Target point", group, "y", borders)

        else:

            group = DialogWidgetGroup(self, "Align grid axes")
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            subsizer = Sizer("horizontal")
            borders = (5, 0, 2, 0)
            group.add(subsizer, expand=True, borders=borders)

            def align_all_axes(align):

                checkbtns["all_axes"].check(align)
                axis_options = self._options["axes"]

                if align:
                    other_axis_ids = "xyz".replace(self._sel_obj_axis, "")
                    for axis_id in "xyz":
                        if axis_options[axis_id]["align"]:
                            other_axis_ids = other_axis_ids.replace(axis_id, "")
                            axis2_id = axis_id
                    if len(other_axis_ids) == 2:
                        axis2_id, axis3_id = other_axis_ids
                    else:
                        axis3_id = other_axis_ids
                    self._axis_toggle_btns.get_button(axis3_id).enable(False)
                    checkbtn = checkbtns[f"{axis3_id}_axis"]
                    checkbtn.enable(False)
                    checkbtn.set_checkmark_color((.5, .5, .5, 1.))
                    checkbtn.check()
                    for axis_id in (self._sel_obj_axis, axis2_id):
                        checkbtns[f"{axis_id}_axis"].check()
                        axis_options[axis_id]["align"] = True
                else:
                    for axis_id in "xyz":
                        self._axis_toggle_btns.get_button(axis_id).enable()
                        checkbtn = checkbtns[f"{axis_id}_axis"]
                        checkbtn.enable()
                        checkbtn.set_checkmark_color()
                        checkbtn.check(False)
                        axis_options[axis_id]["align"] = False

                radio_btn_groups["axis"].enable(align)
                color = None if align else (.5, .5, .5, 1.)
                radio_btn_groups["axis"].set_bullet_color(color, update=True)

                if self._preview:
                    Mgr.update_remotely("grid_alignment", "", self._options)

            def get_checkbox_command(axis_id):

                def align_to_dir(align):

                    axis_options = self._options["axes"]
                    axes_aligned = [a_id for a_id in "xyz" if axis_options[a_id]["align"]]
                    axis_count = len(axes_aligned)
                    axis_options[axis_id]["align"] = align
                    checkbtns["all_axes"].check(axis_count == 1 and align)

                    if self._sel_obj_axis == axis_id:
                        radio_btn_groups["axis"].enable(align)
                        color = None if align else (.5, .5, .5, 1.)
                        radio_btn_groups["axis"].set_bullet_color(color, update=True)

                    if axis_count == 2:
                        axis3_id = "xyz".replace(axes_aligned[0], "").replace(axes_aligned[1], "")
                        checkbtn = checkbtns[f"{axis3_id}_axis"]
                        checkbtn.enable()
                        checkbtn.set_checkmark_color()
                        checkbtn.check(False)
                        self._axis_toggle_btns.get_button(axis3_id).enable()
                    elif axis_count == 1 and align:
                        axis3_id = "xyz".replace(axis_id, "").replace(axes_aligned[0], "")
                        checkbtn = checkbtns[f"{axis3_id}_axis"]
                        checkbtn.enable(False)
                        checkbtn.set_checkmark_color((.5, .5, .5, 1.))
                        checkbtn.check()
                        self._axis_toggle_btns.get_button(axis3_id).enable(False)
                        if self._sel_obj_axis == axis3_id:
                            self._axis_toggle_btns.set_active_button(axis_id)
                            options = axis_options[axis_id]
                            checkbtns["invert"].check(options["inv"])
                            radio_btns = radio_btn_groups["axis"]
                            radio_btns.enable()
                            radio_btns.set_bullet_color(update=True)
                            radio_btns.set_selected_button(options["tgt"])
                            self._sel_obj_axis = axis_id

                    if self._preview:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                return align_to_dir

            def get_btn_command(axis_id):

                def command():

                    self._axis_toggle_btns.set_active_button(axis_id)
                    options = self._options["axes"][axis_id]
                    checkbtns["invert"].check(options["inv"])
                    radio_btn_groups["axis"].enable(options["align"])
                    color = None if options["align"] else (.5, .5, .5, 1.)
                    radio_btn_groups["axis"].set_bullet_color(color, update=True)
                    radio_btn_groups["axis"].set_selected_button(options["tgt"])
                    self._sel_obj_axis = axis_id

                return command

            text = "XYZ"
            checkbtn = DialogCheckButton(group, align_all_axes, text)
            borders = (0, 10, 0, 0)
            subsizer.add(checkbtn, alignment="center_v", borders=borders)
            checkbtns["all_axes"] = checkbtn
            subsizer.add((0, 0), proportion=1.)

            self._axis_toggle_btns = toggle_btns = ToggleButtonGroup()
            borders = (5, 10, 0, 0)

            for axis_id in "xyz":
                checkbtn = DialogCheckButton(group, get_checkbox_command(axis_id))
                subsizer.add(checkbtn, alignment="center_v")
                checkbtns[f"{axis_id}_axis"] = checkbtn
                text = axis_id.upper()
                tooltip_text = f"Grid {axis_id.upper()}-axis"
                btn = DialogButton(group, text, "", tooltip_text)
                toggle = (get_btn_command(axis_id), lambda: None)
                toggle_btns.add_button(btn, axis_id, toggle)
                subsizer.add(btn, alignment="center_v", borders=borders)
                subsizer.add((0, 0), proportion=1.)

            toggle_btns.set_active_button("z")
            subgroup = DialogWidgetGroup(group, "Target direction")
            borders = (5, 5, 5, 5)
            group.add(subgroup, proportion=1., expand=True, borders=borders)
            group = subgroup

        if target_type != "obj_point":

            if target_type in ("view", "object", "surface"):
                create_axis_radio_buttons()
                top_border = 10
            else:
                top_border = 0

            add_inverted_dir_option(top_border)

            if target_type == "view":
                text = "to view center"
            elif target_type == "surface":
                text = "to surface point"
            else:
                text = "to point"

            title = f'Align grid origin {text}'
            group = DialogWidgetGroup(self, title)
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            subsizer = Sizer("horizontal")

            def create_all_coords_checkbox():

                def align_to_point(align):

                    point_options = self._options["points"]
                    axis_ids = "xy" if target_type == "view" else "xyz"

                    for axis_id in axis_ids:
                        checkbtns[f"{axis_id}_coord"].check(align)
                        point_options[axis_id]["align"] = align

                    if self._preview:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                text = "XY" if target_type == "view" else "XYZ"
                checkbtn = DialogCheckButton(group, align_to_point, text)
                borders = (0, 10, 0, 0)
                subsizer.add(checkbtn, alignment="center_v", borders=borders)
                checkbtns["all_coords"] = checkbtn
                subsizer.add((0, 0), proportion=1.)

            def get_checkbox_command(axis_id):

                def align_to_point(align):

                    point_options = self._options["points"]
                    point_options[axis_id]["align"] = align
                    axis_ids = "xy" if target_type == "view" else "xyz"
                    coords_aligned = [a_id for a_id in axis_ids if point_options[a_id]["align"]]
                    checkbtns["all_coords"].check(len(coords_aligned) == len(axis_ids))

                    if self._preview:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                return align_to_point

            if target_type == "object":

                borders = (5, 0, 0, 0)
                group.add(subsizer, expand=True, borders=borders)

                def get_btn_command(axis_id):

                    def command():

                        self._point_toggle_btns.set_active_button(axis_id)
                        options = self._options["points"][axis_id]

                        if "sel_point" in radio_btn_groups:
                            radio_btn_groups["sel_point"].set_selected_button(options["sel"])

                        if "tgt_point" in radio_btn_groups:
                            radio_btn_groups["tgt_point"].set_selected_button(options["tgt"])

                        self._coord_axis = axis_id

                    return command

                self._point_toggle_btns = toggle_btns = ToggleButtonGroup()

                create_all_coords_checkbox()
                borders = (5, 10, 0, 0)
                tooltip_str = "View {}-axis" if target_type == "view" else "Ref. coord. {}-axis"

                for axis_id in ("xy" if target_type == "view" else "xyz"):
                    checkbtn = DialogCheckButton(group, get_checkbox_command(axis_id))
                    subsizer.add(checkbtn, alignment="center_v")
                    checkbtns[f"{axis_id}_coord"] = checkbtn
                    text = axis_id.upper()
                    tooltip_text = tooltip_str.format(axis_id.upper())
                    btn = DialogButton(group, text, "", tooltip_text)
                    toggle = (get_btn_command(axis_id), lambda: None)
                    toggle_btns.add_button(btn, axis_id, toggle)
                    subsizer.add(btn, alignment="center_v", borders=borders)
                    subsizer.add((0, 0), proportion=1.)

                toggle_btns.set_active_button("x")

            else:

                text_str = f'Along the {"view" if target_type == "view" else "ref. coord."} axes:'
                text = DialogText(group, text_str)
                borders = (5, 0, 5, 0)
                group.add(text, borders=borders)

                borders = (5, 0, 0, 0)
                group.add(subsizer, expand=True, borders=borders)
                create_all_coords_checkbox()
                borders = (0, 10, 0, 0)

                for axis_id in ("xy" if target_type == "view" else "xyz"):
                    text = axis_id.upper()
                    checkbtn = DialogCheckButton(group, get_checkbox_command(axis_id), text)
                    subsizer.add(checkbtn, borders=borders)
                    checkbtns[f"{axis_id}_coord"] = checkbtn
                    subsizer.add((0, 0), proportion=1.)

            subgroup_sizer = Sizer("horizontal")
            borders = (5, 5, 5, 5)
            group.add(subgroup_sizer, expand=True, borders=borders)

            if target_type == "object":

                create_target_point_group("Target object", subgroup_sizer)

                def command(local):

                    self._options["local_minmax"] = local

                    if self._preview:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                s = "view" if target_type == "view" else "ref."
                text = f"Local min./max. (ignore {s} coord. sys.)"
                checkbtn = DialogCheckButton(group, command, text)
                borders = (5, 0, 0, 0)
                group.add(checkbtn, borders=borders)
                checkbtns["local_minmax"] = checkbtn

                def command():

                    point_options = self._options["points"]
                    axis_ids = "xy" if target_type == "view" else "xyz"

                    for axis_id in axis_ids:
                        point_options[axis_id]["tgt"] = point_options[self._coord_axis]["tgt"]

                    if self._preview:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                text = "For all axes"
                tooltip_text = "Use these settings for all axes"
                btn = DialogButton(group, text, "", tooltip_text, command)
                borders = (5, 5, 5, 5)
                group.add(btn, borders=borders)

        def enable_preview(preview):

            self._preview = preview
            Mgr.update_remotely("grid_alignment", "", self._options, preview, not preview)

        text = "Preview"
        checkbtn = DialogCheckButton(self, enable_preview, text)
        checkbtn.check(target_type != "obj_point")
        borders = (20, 20, 15, 10)
        client_sizer.add(checkbtn, borders=borders)
        checkbtns["preview"] = checkbtn

        self.finalize()

    def close(self, answer=""):

        self._checkbuttons = None
        self._radio_btns = None
        self._axis_toggle_btns = None
        self._point_toggle_btns = None

        Dialog.close(self, answer)

    def __on_yes(self):

        Mgr.update_remotely("grid_alignment", "", self._options, False)
        Mgr.get("coord_sys_combobox").set_field_tint(None)

    def __on_cancel(self):

        Mgr.update_remotely("grid_alignment", "cancel")
        Mgr.get("coord_sys_combobox").set_field_tint(None)
