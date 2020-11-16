from ..base import *
from ..button import *
from ..dialog import *
from .message_dialog import MessageDialog


class AlignmentDialog(Dialog):

    def __init__(self, target_type, obj_name=""):

        if target_type == "view":
            align_descr = 'to current view'
        elif "obj" in target_type:
            align_descr = f'to object ("{obj_name}")'
        else:
            align_descr = f'to surface ("{obj_name}")'

        Dialog.__init__(self, "", "okcancel", "Align", self.__on_yes, on_cancel=self.__on_cancel)

        obj_lvl = GD["active_obj_level"]
        cs_descr = "view" if target_type == "view" else "ref."
        pt_align_descr = axes_descr = ""

        if obj_lvl == "top":
            if target_type == "view":
                dir_align_descr = "Align local axes"
                pt_align_descr = "point to view center"
                axes_descr = "View"
                component_ids = [
                    "direction", "local axes", "target axis", "direction axis",
                    "point to point", "point 2D coords", "source point"
                ]
            elif target_type == "surface":
                dir_align_descr = "Align to normal"
                pt_align_descr = "point to surface point"
                axes_descr = "Ref. coord."
                component_ids = [
                    "direction", "axis toggle", "direction axis",
                    "point to point", "point 3D coords", "source point"
                ]
            elif target_type == "object":
                dir_align_descr = "Align local axes"
                pt_align_descr = "points"
                axes_descr = "Ref. coord."
                component_ids = [
                    "direction", "local axes", "target axis", "direction axis",
                    "point to point", "point 3D coords", "source point", "target point"
                ]
            elif target_type == "obj_point":
                dir_align_descr = "Aim local axis at point"
                component_ids = ["direction", "direction axis", "point aimed at"]
        elif obj_lvl == "normal":
            dir_align_descr = "Align normals"
            if target_type in ("view", "object"):
                component_ids = ["direction", "target axis", "direction axis"]
            elif target_type == "surface":
                component_ids = ["direction"]
            elif target_type == "obj_point":
                dir_align_descr = "Aim normals at point"
                component_ids = ["direction", "point aimed at"]
        elif target_type == "view":
            dir_align_descr = "Align local axes"
            pt_align_descr = "center to view center"
            axes_descr = "view"
            component_ids = [
                "direction", "local axes", "target axis", "direction axis",
                "center to point", "center 2D coords", "center per vertex", "planar"
            ]
        elif target_type == "surface":
            dir_align_descr = "Align to normal"
            pt_align_descr = "center to surface point"
            axes_descr = "ref. coord."
            component_ids = [
                "direction", "axis toggle", "direction axis",
                "center to point", "center 3D coords", "center per vertex"
            ]
        elif target_type == "object":
            dir_align_descr = "Align local axes"
            pt_align_descr = "center to point"
            axes_descr = "Ref. coord."
            component_ids = [
                "direction", "local axes", "target axis", "direction axis",
                "point to point", "point 3D coords", "target point", "point per vertex"
            ]
        elif target_type == "obj_point":
            dir_align_descr = "Aim local axis at point"
            component_ids = ["direction", "direction axis", "point aimed at"]

        text_vars = {
            "align_descr": align_descr,
            "src_descr": "Selected obj.",
            "local_axis_descr": "local",
            "dir_align_descr": dir_align_descr,
            "pt_align_descr": pt_align_descr,
            "axes_descr": axes_descr,
            "cs_descr": cs_descr
        }

        widgets = Skin.layout.create(self, "alignment", text_vars, component_ids)
        self._checkbuttons = checkbtns = widgets["checkbuttons"]
        self._radio_btns = radio_btn_groups = widgets["radiobutton_groups"]
        btns = widgets["buttons"]

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

        self._axis_toggle_btns = None
        self._point_toggle_btns = None

        if obj_lvl == "top" or "obj" in target_type:
            if target_type == "obj_point":
                btn_ids = ("pivot", "center")
            else:
                btn_ids = ("pivot", "center", "min", "max")

        def setup_axis_align_checkbtn():

            def align_to_dir(align):

                self._options["axes"][self._sel_obj_axis]["align"] = align

                if self._preview:
                    Mgr.update_remotely("object_alignment", "", self._options)

            checkbtn = checkbtns["axis"]
            checkbtn.command = align_to_dir

        def setup_axis_radio_buttons():

            radio_btns = radio_btn_groups["axis"]

            def set_target_axis(axis_id):

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

            for axis_id in "xyz":
                command = lambda a=axis_id: set_target_axis(a)
                radio_btns.set_button_command(axis_id, command)

            radio_btns.set_selected_button("y" if target_type == "obj_point" else "z")
            enable = "all_axes" not in checkbtns
            radio_btns.enable(enable)
            color = None if enable else Skin.colors["dialog_bullet_disabled"]
            radio_btns.set_bullet_color(color, update=True)

        def setup_inverted_dir_checkbtn():

            def set_dir_inverted(invert):

                axis_options = self._options["axes"]
                axis_options[self._sel_obj_axis]["inv"] = invert

                if self._preview and axis_options[self._sel_obj_axis]["align"]:
                    Mgr.update_remotely("object_alignment", "", self._options)

            checkbtn = checkbtns["invert"]
            checkbtn.command = set_dir_inverted

        def setup_target_point_btns(axis_id=""):

            radio_btns = radio_btn_groups["tgt_point"]

            def set_target_point(point_id):

                a_id = axis_id if axis_id else self._coord_axis
                point_options = self._options["points"]
                point_options[a_id]["tgt"] = point_id

                if self._preview and point_options[a_id]["align"]:
                    Mgr.update_remotely("object_alignment", "", self._options)

            for btn_id in btn_ids:
                command = lambda point_id=btn_id: set_target_point(point_id)
                radio_btns.set_button_command(btn_id, command)

            radio_btns.set_selected_button("center")

        if target_type == "surface":

            if obj_lvl != "normal":
                setup_axis_align_checkbtn()

        elif target_type == "obj_point":

            if obj_lvl != "normal":
                setup_axis_radio_buttons()

            setup_inverted_dir_checkbtn()
            setup_target_point_btns("y")

        elif obj_lvl != "normal":

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
                    checkbtn.set_checkmark_color(Skin.colors["dialog_checkmark_disabled"])
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
                color = None if align else Skin.colors["dialog_bullet_disabled"]
                radio_btn_groups["axis"].set_bullet_color(color, update=True)

                if self._preview:
                    Mgr.update_remotely("object_alignment", "", self._options)

            def align_to_dir(axis_id, align):

                axis_options = self._options["axes"]
                axes_aligned = [a_id for a_id in "xyz" if axis_options[a_id]["align"]]
                axis_count = len(axes_aligned)
                axis_options[axis_id]["align"] = align
                checkbtns["all_axes"].check(axis_count == 1 and align)

                if self._sel_obj_axis == axis_id:
                    radio_btn_groups["axis"].enable(align)
                    color = None if align else Skin.colors["dialog_bullet_disabled"]
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
                    checkbtn.set_checkmark_color(Skin.colors["dialog_checkmark_disabled"])
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

            def show_axis_dir_settings(axis_id):

                self._axis_toggle_btns.set_active_button(axis_id)
                options = self._options["axes"][axis_id]
                checkbtns["invert"].check(options["inv"])
                radio_btn_groups["axis"].enable(options["align"])
                color = None if options["align"] else Skin.colors["dialog_bullet_disabled"]
                radio_btn_groups["axis"].set_bullet_color(color, update=True)
                radio_btn_groups["axis"].set_selected_button(options["tgt"])
                self._sel_obj_axis = axis_id

            checkbtn = checkbtns["all_axes"]
            checkbtn.command = align_all_axes

            self._axis_toggle_btns = toggle_btns = ToggleButtonGroup()

            for axis_id in "xyz":
                checkbtn = checkbtns[f"{axis_id}_axis"]
                checkbtn.command = lambda align, a=axis_id: align_to_dir(a, align)
                btn = btns[f"{axis_id}_axis"]
                command = lambda a=axis_id: show_axis_dir_settings(a)
                toggle = (command, lambda: None)
                toggle_btns.add_button(btn, axis_id, toggle)

            toggle_btns.set_active_button("z")

        if target_type != "obj_point":

            if obj_lvl != "normal" or target_type in ("view", "object"):
                setup_axis_radio_buttons()

            setup_inverted_dir_checkbtn()

        if obj_lvl != "normal" and target_type != "obj_point":

            def setup_all_coords_checkbox():

                def align_to_point(align):

                    point_options = self._options["points"]
                    axis_ids = "xy" if target_type == "view" else "xyz"

                    for axis_id in axis_ids:
                        checkbtns[f"{axis_id}_coord"].check(align)
                        point_options[axis_id]["align"] = align

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                checkbtn = checkbtns["all_coords"]
                checkbtn.command = align_to_point

            def align_to_point(axis_id, align):

                point_options = self._options["points"]
                point_options[axis_id]["align"] = align
                axis_ids = "xy" if target_type == "view" else "xyz"
                coords_aligned = [a_id for a_id in axis_ids if point_options[a_id]["align"]]
                checkbtns["all_coords"].check(len(coords_aligned) == len(axis_ids))

                if self._preview:
                    Mgr.update_remotely("object_alignment", "", self._options)

            if obj_lvl == "top" or target_type == "object":

                def show_axis_pt_settings(axis_id):

                    self._point_toggle_btns.set_active_button(axis_id)
                    options = self._options["points"][axis_id]

                    if "sel_point" in radio_btn_groups:
                        radio_btn_groups["sel_point"].set_selected_button(options["sel"])

                    if "tgt_point" in radio_btn_groups:
                        radio_btn_groups["tgt_point"].set_selected_button(options["tgt"])

                    self._coord_axis = axis_id

                self._point_toggle_btns = toggle_btns = ToggleButtonGroup()

                setup_all_coords_checkbox()

                for axis_id in ("xy" if target_type == "view" else "xyz"):
                    checkbtn = checkbtns[f"{axis_id}_coord"]
                    checkbtn.command = lambda align, a=axis_id: align_to_point(a, align)
                    btn = btns[f"{axis_id}_coord"]
                    command = lambda a=axis_id: show_axis_pt_settings(a)
                    toggle = (command, lambda: None)
                    toggle_btns.add_button(btn, axis_id, toggle)

                toggle_btns.set_active_button("x")

            else:

                setup_all_coords_checkbox()

                for axis_id in ("xy" if target_type == "view" else "xyz"):
                    checkbtn = checkbtns[f"{axis_id}_coord"]
                    checkbtn.command = lambda align, a=axis_id: align_to_point(a, align)

            if obj_lvl == "top":

                radio_btns = radio_btn_groups["sel_point"]

                def set_sel_point(point_id):

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

                for btn_id in btn_ids:
                    command = lambda point_id=btn_id: set_sel_point(point_id)
                    radio_btns.set_button_command(btn_id, command)

                radio_btns.set_selected_button("pivot" if xform_target_type == "pivot" else "center")

            if target_type == "object":
                setup_target_point_btns()

            if obj_lvl == "top" or target_type == "object":

                def command(local):

                    self._options["local_minmax"] = local

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                checkbtn = checkbtns["local_minmax"]
                checkbtn.command = command

                def command():

                    point_options = self._options["points"]
                    axis_ids = "xy" if target_type == "view" else "xyz"

                    for axis_id in axis_ids:
                        point_options[axis_id]["sel"] = point_options[self._coord_axis]["sel"]
                        point_options[axis_id]["tgt"] = point_options[self._coord_axis]["tgt"]

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                btn = btns["all_axes"]
                btn.command = command

            if obj_lvl != "top":

                def set_align_points_per_vertex(per_vertex):

                    self._options["per_vertex"] = per_vertex

                    if self._preview:
                        Mgr.update_remotely("object_alignment", "", self._options)

                checkbtn = checkbtns["per_vertex"]
                checkbtn.command = set_align_points_per_vertex

        if obj_lvl not in ("top", "normal") and target_type == "view":

            def make_planar(planar):

                self._options["planar"] = planar

                if self._preview:
                    Mgr.update_remotely("object_alignment", "", self._options)

            checkbtn = checkbtns["planar"]
            checkbtn.command = make_planar

        def enable_preview(preview):

            self._preview = preview
            Mgr.update_remotely("object_alignment", "", self._options, preview, not preview)

        checkbtn = checkbtns["preview"]
        checkbtn.command = enable_preview
        checkbtn.check(False if obj_lvl == "normal" or target_type == "obj_point" else True)

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
            align_descr = 'grid to current view'
        elif "obj" in target_type:
            align_descr = f'grid to object ("{obj_name}")'
        else:
            align_descr = f'grid to surface ("{obj_name}")'

        Dialog.__init__(self, "", "okcancel", "Align", self.__on_yes, on_cancel=self.__on_cancel)

        cs_descr = "view" if target_type == "view" else "ref."
        pt_align_descr = axes_descr = ""

        if target_type == "view":
            dir_align_descr = "Align grid axes"
            pt_align_descr = "grid origin to view center"
            axes_descr = "view"
            component_ids = [
                "direction", "local axes", "target axis", "direction axis",
                "center to point", "center 2D coords"
            ]
        elif target_type == "surface":
            dir_align_descr = "Align to normal"
            pt_align_descr = "grid origin to surface point"
            axes_descr = "ref. coord."
            component_ids = [
                "direction", "axis toggle", "direction axis",
                "center to point", "center 3D coords"
            ]
        elif target_type == "object":
            dir_align_descr = "Align grid axes"
            pt_align_descr = "grid origin to point"
            axes_descr = "Ref. coord."
            component_ids = [
                "direction", "local axes", "target axis", "direction axis",
                "point to point", "point 3D coords", "target point"
            ]
        elif target_type == "obj_point":
            dir_align_descr = "Aim grid axis at point"
            component_ids = ["direction", "direction axis", "point aimed at"]

        text_vars = {
            "align_descr": align_descr,
            "src_descr": "Grid",
            "local_axis_descr": "grid",
            "dir_align_descr": dir_align_descr,
            "pt_align_descr": pt_align_descr,
            "axes_descr": axes_descr,
            "cs_descr": cs_descr
        }

        widgets = Skin.layout.create(self, "alignment", text_vars, component_ids)
        self._checkbuttons = checkbtns = widgets["checkbuttons"]
        self._radio_btns = radio_btn_groups = widgets["radiobutton_groups"]
        btns = widgets["buttons"]

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

        self._axis_toggle_btns = None
        self._point_toggle_btns = None

        if "obj" in target_type:
            if target_type == "obj_point":
                btn_ids = ("pivot", "center")
            else:
                btn_ids = ("pivot", "center", "min", "max")

        def setup_axis_align_checkbtn():

            def align_to_dir(align):

                self._options["axes"][self._sel_obj_axis]["align"] = align

                if self._preview:
                    Mgr.update_remotely("grid_alignment", "", self._options)

            checkbtn = checkbtns["axis"]
            checkbtn.command = align_to_dir

        def setup_axis_radio_buttons():

            radio_btns = radio_btn_groups["axis"]

            def set_target_axis(axis_id):

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

            for axis_id in "xyz":
                command = lambda a=axis_id: set_target_axis(a)
                radio_btns.set_button_command(axis_id, command)

            radio_btns.set_selected_button("y" if target_type == "obj_point" else "z")
            enable = "all_axes" not in checkbtns
            radio_btns.enable(enable)
            color = None if enable else Skin.colors["dialog_bullet_disabled"]
            radio_btns.set_bullet_color(color, update=True)

        def setup_inverted_dir_checkbtn():

            def set_dir_inverted(invert):

                axis_options = self._options["axes"]
                axis_options[self._sel_obj_axis]["inv"] = invert

                if self._preview and axis_options[self._sel_obj_axis]["align"]:
                    Mgr.update_remotely("grid_alignment", "", self._options)

            checkbtn = checkbtns["invert"]
            checkbtn.command = set_dir_inverted

        def setup_target_point_btns(axis_id=""):

            radio_btns = radio_btn_groups["tgt_point"]

            def set_target_point(point_id):

                a_id = axis_id if axis_id else self._coord_axis
                point_options = self._options["points"]
                point_options[a_id]["tgt"] = point_id

                if self._preview and point_options[a_id]["align"]:
                    Mgr.update_remotely("grid_alignment", "", self._options)

            for btn_id in btn_ids:
                command = lambda point_id=btn_id: set_target_point(point_id)
                radio_btns.set_button_command(btn_id, command)

            radio_btns.set_selected_button("center")

        if target_type == "surface":

            setup_axis_align_checkbtn()

        elif target_type == "obj_point":

            setup_axis_radio_buttons()
            setup_inverted_dir_checkbtn()
            setup_target_point_btns("y")

        else:

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
                    checkbtn.set_checkmark_color(Skin.colors["dialog_checkmark_disabled"])
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
                color = None if align else Skin.colors["dialog_bullet_disabled"]
                radio_btn_groups["axis"].set_bullet_color(color, update=True)

                if self._preview:
                    Mgr.update_remotely("grid_alignment", "", self._options)

            def align_to_dir(axis_id, align):

                axis_options = self._options["axes"]
                axes_aligned = [a_id for a_id in "xyz" if axis_options[a_id]["align"]]
                axis_count = len(axes_aligned)
                axis_options[axis_id]["align"] = align
                checkbtns["all_axes"].check(axis_count == 1 and align)

                if self._sel_obj_axis == axis_id:
                    radio_btn_groups["axis"].enable(align)
                    color = None if align else Skin.colors["dialog_bullet_disabled"]
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
                    checkbtn.set_checkmark_color(Skin.colors["dialog_checkmark_disabled"])
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

            def show_axis_dir_settings(axis_id):

                self._axis_toggle_btns.set_active_button(axis_id)
                options = self._options["axes"][axis_id]
                checkbtns["invert"].check(options["inv"])
                radio_btn_groups["axis"].enable(options["align"])
                color = None if options["align"] else Skin.colors["dialog_bullet_disabled"]
                radio_btn_groups["axis"].set_bullet_color(color, update=True)
                radio_btn_groups["axis"].set_selected_button(options["tgt"])
                self._sel_obj_axis = axis_id

            checkbtn = checkbtns["all_axes"]
            checkbtn.command = align_all_axes

            self._axis_toggle_btns = toggle_btns = ToggleButtonGroup()

            for axis_id in "xyz":
                checkbtn = checkbtns[f"{axis_id}_axis"]
                checkbtn.command = lambda align, a=axis_id: align_to_dir(a, align)
                btn = btns[f"{axis_id}_axis"]
                command = lambda a=axis_id: show_axis_dir_settings(a)
                toggle = (command, lambda: None)
                toggle_btns.add_button(btn, axis_id, toggle)

            toggle_btns.set_active_button("z")

        if target_type != "obj_point":

            if target_type in ("view", "object", "surface"):
                setup_axis_radio_buttons()

            setup_inverted_dir_checkbtn()

            def setup_all_coords_checkbox():

                def align_to_point(align):

                    point_options = self._options["points"]
                    axis_ids = "xy" if target_type == "view" else "xyz"

                    for axis_id in axis_ids:
                        checkbtns[f"{axis_id}_coord"].check(align)
                        point_options[axis_id]["align"] = align

                    if self._preview:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                checkbtn = checkbtns["all_coords"]
                checkbtn.command = align_to_point

            def align_to_point(axis_id, align):

                point_options = self._options["points"]
                point_options[axis_id]["align"] = align
                axis_ids = "xy" if target_type == "view" else "xyz"
                coords_aligned = [a_id for a_id in axis_ids if point_options[a_id]["align"]]
                checkbtns["all_coords"].check(len(coords_aligned) == len(axis_ids))

                if self._preview:
                    Mgr.update_remotely("grid_alignment", "", self._options)

            if target_type == "object":

                def show_axis_pt_settings(axis_id):

                    self._point_toggle_btns.set_active_button(axis_id)
                    options = self._options["points"][axis_id]

                    if "sel_point" in radio_btn_groups:
                        radio_btn_groups["sel_point"].set_selected_button(options["sel"])

                    if "tgt_point" in radio_btn_groups:
                        radio_btn_groups["tgt_point"].set_selected_button(options["tgt"])

                    self._coord_axis = axis_id

                self._point_toggle_btns = toggle_btns = ToggleButtonGroup()

                setup_all_coords_checkbox()

                for axis_id in ("xy" if target_type == "view" else "xyz"):
                    checkbtn = checkbtns[f"{axis_id}_coord"]
                    checkbtn.command = lambda align, a=axis_id: align_to_point(a, align)
                    btn = btns[f"{axis_id}_coord"]
                    command = lambda a=axis_id: show_axis_pt_settings(a)
                    toggle = (command, lambda: None)
                    toggle_btns.add_button(btn, axis_id, toggle)

                toggle_btns.set_active_button("x")

            else:

                setup_all_coords_checkbox()

                for axis_id in ("xy" if target_type == "view" else "xyz"):
                    checkbtn = checkbtns[f"{axis_id}_coord"]
                    checkbtn.command = lambda align, a=axis_id: align_to_point(a, align)

            if target_type == "object":

                setup_target_point_btns()

                def command(local):

                    self._options["local_minmax"] = local

                    if self._preview:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                checkbtn = checkbtns["local_minmax"]
                checkbtn.command = command

                def command():

                    point_options = self._options["points"]
                    axis_ids = "xy" if target_type == "view" else "xyz"

                    for axis_id in axis_ids:
                        point_options[axis_id]["tgt"] = point_options[self._coord_axis]["tgt"]

                    if self._preview:
                        Mgr.update_remotely("grid_alignment", "", self._options)

                btn = btns["all_axes"]
                btn.command = command

        def enable_preview(preview):

            self._preview = preview
            Mgr.update_remotely("grid_alignment", "", self._options, preview, not preview)

        checkbtn = checkbtns["preview"]
        checkbtn.command = enable_preview
        checkbtn.check(target_type != "obj_point")

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
