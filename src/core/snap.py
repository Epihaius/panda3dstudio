from .base import *
from collections import defaultdict
import copy


# the following module-level functions are used to retrieve default snap
# setting values from within a defaultdict, so the latter can be pickled
def get_default_state(): return False
def get_default_point_type(): return "grid_point"
def get_default_size(): return 10.
def get_default_viz_display(): return True
def get_default_constraints(): return False
def get_default_increment(): return 1.


class SnapManager:

    def __init__(self):

        states = defaultdict(get_default_state)
        states["creation_start"] = True
        src_types = defaultdict(get_default_point_type)
        src_types["translate"] = "transf_center"
        tgt_types = defaultdict(get_default_point_type)
        rubber_band_display = defaultdict(get_default_viz_display)
        creation_phase_ids = tuple(f"creation_phase_{i + 1}" for i in range(3))

        for snap_type in ("translate", "rotate", "scale") + creation_phase_ids:
            tgt_types[snap_type] = "increment"

        for snap_type in creation_phase_ids:
            rubber_band_display[snap_type] = False

        increments = defaultdict(get_default_increment)
        increments["rotate"] = 5.
        increments["scale"] = 10.

        snap_settings = {
            "prev_type": "",
            "type": "",
            "on": states,
            "src_type": src_types,
            "tgt_type": tgt_types,
            "size": defaultdict(get_default_size),
            "show_marker": defaultdict(get_default_viz_display),
            "marker_size": defaultdict(get_default_size),
            "show_rubber_band": rubber_band_display,
            "show_proj_line": defaultdict(get_default_viz_display),
            "show_proj_marker": defaultdict(get_default_viz_display),
            "proj_marker_size": defaultdict(get_default_size),
            "use_axis_constraints": defaultdict(get_default_constraints),
            "increment": increments
        }

        copier = copy.deepcopy
        GD.set_default("snap", snap_settings, copier)

        self._pixel_under_mouse = None
        self._snap_target_point = None
        self._transf_start_pos = Point3()
        self._start_creation = False
        self._start_transform_mode = False
        self._snapping_transf_center = False
        self._snapping_coord_origin = False
        self._transf_center_snap_cancelled = True
        self._coord_origin_snap_cancelled = True
        self._default_cursor = "main"
        marker, proj_marker, rubber_band = self.__create_snap_viz()
        self._snap_target_marker = marker
        self._projected_snap_target_marker = proj_marker
        self._rubber_band = rubber_band

        Mgr.expose("snap_target_point", lambda: self._snap_target_point)
        Mgr.accept("set_creation_start_snap", self.__set_creation_start)
        Mgr.accept("init_snap_target_checking", self.__init_target_checking)
        Mgr.accept("end_snap_target_checking", self.__end_target_checking)
        Mgr.accept("set_projected_snap_marker_pos", self.__set_projected_snap_marker_pos)
        Mgr.add_app_updater("object_snap", self.__update_snapping)
        Mgr.add_notification_handler("pickable_geom_altered", "snap_mgr",
                                     self.__handle_pickable_geom_change)
        Mgr.add_notification_handler("render_mode_changed", "snap_mgr",
                                     self.__handle_render_mode_change)
        Mgr.add_notification_handler("lens_type_changed", "snap_mgr",
                                     self.__handle_lens_type_change)

        add_state = Mgr.add_state
        add_state("transf_start_snap_mode", -1, self.__enter_transf_start_snap_mode,
                  self.__exit_transf_start_snap_mode)
        add_state("transf_center_snap_mode", -80, self.__enter_transf_center_snap_mode,
                  self.__exit_transf_center_snap_mode)
        add_state("coord_origin_snap_mode", -80, self.__enter_coord_origin_snap_mode,
                  self.__exit_coord_origin_snap_mode)

        def end_transf_start_snap(cancelled=True):

            if cancelled:
                Mgr.exit_state("transf_start_snap_mode")
                Mgr.do("cancel_transform_init")
            elif self._snap_target_point:
                point = GD.world.get_relative_point(Mgr.get("grid").origin, self._snap_target_point)
                Mgr.do("start_transform", point)

        def end_transf_center_snap(cancelled=True):

            if cancelled or self._snap_target_point:
                self._transf_center_snap_cancelled = cancelled
                Mgr.exit_state("transf_center_snap_mode")
                self._transf_center_snap_cancelled = True

        def end_coord_origin_snap(cancelled=True):

            if cancelled or self._snap_target_point:
                self._coord_origin_snap_cancelled = cancelled
                Mgr.exit_state("coord_origin_snap_mode")
                self._coord_origin_snap_cancelled = True

        bind = Mgr.bind_state
        bind("transf_start_snap_mode", "choose transf start snap", "control",
             lambda: end_transf_start_snap(False))
        bind("transf_start_snap_mode", "check transf start snap", "mouse1",
             lambda: end_transf_start_snap(False))
        bind("transf_start_snap_mode", "exit transf start snap", "escape",
             end_transf_start_snap)
        bind("transf_start_snap_mode", "cancel transf start snap", "mouse3",
             end_transf_start_snap)
        bind("transf_start_snap_mode", "abort transf start snap", "focus_loss",
             end_transf_start_snap)
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("transf_center_snap_mode", "snap transf center -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("transf_center_snap_mode", "quit transf center snap", "mouse1",
             lambda: end_transf_center_snap(False))
        bind("transf_center_snap_mode", "exit transf center snap", "escape",
             end_transf_center_snap)
        bind("transf_center_snap_mode", "cancel transf center snap", "mouse3",
             end_transf_center_snap)
        bind("transf_center_snap_mode", "snap transf center ctrl-right-click",
             f"{mod_ctrl}|mouse3", lambda: Mgr.update_remotely("main_context"))
        bind("coord_origin_snap_mode", "snap coord origin -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("coord_origin_snap_mode", "quit coord origin snap", "mouse1",
             lambda: end_coord_origin_snap(False))
        bind("coord_origin_snap_mode", "exit coord origin snap", "escape",
             end_coord_origin_snap)
        bind("coord_origin_snap_mode", "cancel coord origin snap", "mouse3",
             end_coord_origin_snap)
        bind("coord_origin_snap_mode", "snap coord origin ctrl-right-click",
             f"{mod_ctrl}|mouse3", lambda: Mgr.update_remotely("main_context"))

        status_data = GD["status"]
        mode = "Pick transf. start point"
        info = "<Ctrl> or LMB to pick point and start transforming; RMB to cancel"
        status_data["snap_transf_start"] = {"mode": mode, "info": info}
        mode = "Pick transf. center point"
        info = "LMB to pick point; RMB to cancel; use Snap/Align toolbar to set options"
        status_data["snap_transf_center"] = {"mode": mode, "info": info}
        mode = "Pick ref. coord. origin point"
        status_data["snap_coord_origin"] = {"mode": mode, "info": info}

    def __update_snapping(self):

        snap_settings = GD["snap"]
        state_id = Mgr.get_state_id()

        if snap_settings["type"] == "creation" and state_id == "creation_mode":
            if snap_settings["on"]["creation_start"]:
                if snap_settings["on"]["creation"]:
                    self._start_creation = True
                    self.__init_target_checking("create")
                else:
                    self.__end_target_checking()
                    self._start_creation = False
                    Mgr.set_cursor("create")

    def __create_snap_viz(self):

        state_np = NodePath("state_np")
        state_np.set_depth_test(False)
        state_np.set_depth_write(False)
        state_np.set_bin("fixed", 101)
        state_np.set_color(0., 1., 1., 1.)
        state1 = state_np.get_state()
        state_np.set_bin("fixed", 100)
        state_np.set_color((0., 0., 0., 1.))
        state_np.set_render_mode_thickness(3)
        state2 = state_np.get_state()

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("snap_tgt_marker_data", vertex_format, Geom.UH_static)
        vertex_data.unclean_set_num_rows(4)
        array = vertex_data.modify_array(0)
        stride = array.array_format.stride
        memview = memoryview(array).cast("B")
        positions = ((-1., 0., 0.), (1., 0., 0.), (0., 0., -1.), (0., 0., 1.))

        for i, pos in enumerate(positions):
            memview[stride * i:stride * (i + 1)] = struct.pack("fff", *pos)

        lines = GeomLines(Geom.UH_static)
        lines.add_next_vertices(4)
        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        geom_node = GeomNode("snap_tgt_marker")
        geom_node.add_geom(geom, state1)
        geom = geom.make_copy()
        geom_node.add_geom(geom, state2)
        marker = NodePath(geom_node)

        vertex_data = GeomVertexData("proj_snap_tgt_marker_data", vertex_format, Geom.UH_static)
        vertex_data.unclean_set_num_rows(4)
        array = vertex_data.modify_array(0)
        stride = array.array_format.stride
        memview = memoryview(array).cast("B")
        positions = ((-1., 0., -1.), (1., 0., 1.), (1., 0., -1.), (-1., 0., 1.))

        for i, pos in enumerate(positions):
            memview[stride * i:stride * (i + 1)] = struct.pack("fff", *pos)

        lines = GeomLines(Geom.UH_static)
        lines.add_next_vertices(4)
        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        geom_node = GeomNode("proj_snap_tgt_marker")
        geom_node.add_geom(geom, state1)
        geom = geom.make_copy()
        geom_node.add_geom(geom, state2)
        proj_marker = NodePath(geom_node)

        vertex_data = GeomVertexData("snap_rubber_band_data", vertex_format, Geom.UH_static)
        vertex_data.set_num_rows(2)
        lines = GeomLines(Geom.UH_static)
        lines.add_next_vertices(2)
        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        geom_node = GeomNode("snap_rubber_band")
        geom_node.add_geom(geom, state1)
        geom = geom.make_copy()
        geom_node.add_geom(geom, state2)
        rubber_band = NodePath(geom_node)
        rubber_band.hide(Mgr.get("picking_masks"))

        return marker, proj_marker, rubber_band

    def __get_objs_to_transform(self):

        sel = Mgr.get("selection_top")[:]

        for obj in sel[:]:
            sel.extend(obj.descendants)

        return sel

    def __get_selected_models(self, include_linked=False):

        sel = Mgr.get("selection_top")
        models = [o for o in sel if o.type == "model" and o.geom_type != "basic_geom"]

        if include_linked:
            for obj in sel:
                models.extend(obj.descendants)

        return models

    def __make_subobj_sel_unpickable(self, subobj_lvl):

        # While translating a subobject selection, it should not be possible to snap to the
        # geometry that is being transformed. To this end, all of the vertices that are part
        # of this geometry (visible to the picking camera) will be given a position of 1 unit
        # directly behind the main camera, so the picking camera will not be able to render
        # them. To get them all to this same position, a zero-scale matrix, combined with
        # a (0., -1., 0.) translation matrix, will be applied to them.

        selection = Mgr.get("selection")
        cam = GD.cam()
        # the transformation in camera space
        local_xform = Mat4.scale_mat(0., 0., 0.) * Mat4.translate_mat(0., -1., 0.)

        for model in self.__get_selected_models():

            rows_to_transf = SparseArray()
            origin = model.origin
            orig_to_cam = origin.get_mat(cam)
            cam_to_orig = cam.get_mat(origin)
            mat = orig_to_cam * local_xform * cam_to_orig
            geom_data_obj = model.geom_obj.geom_data_obj
            geom_data_obj.set_picking_geom_xform_locked()

            subobjs = set()

            for subobj in selection.get_subobjects(geom_data_obj):
                subobjs.update(subobj.get_connected_subobjs(subobj_lvl))

            for subobj in subobjs:
                for row in subobj.row_indices:
                    rows_to_transf.set_bit(row)

            vertex_data = geom_data_obj.get_pickable_vertex_data(subobj_lvl)
            vertex_data.transform_vertices(mat, rows_to_transf)

    def __make_subobjs_pickable(self, subobj_lvl, pickable=True):

        obj_lvl = GD["active_obj_level"]
        models = set(m for m in Mgr.get("model_objs") if m.geom_type != "basic_geom")
        exclude_selection = Mgr.get_state_id() == "transforming"

        if obj_lvl == "top" and exclude_selection:
            models.difference_update(self.__get_selected_models(include_linked=True))

        if pickable:
            for model in models:
                geom_data_obj = model.geom_obj.geom_data_obj
                geom_data_obj.make_subobjs_pickable(subobj_lvl, 1)
            if obj_lvl != "top" and exclude_selection:
                self.__make_subobj_sel_unpickable(subobj_lvl)
        else:
            for model in models:
                geom_data_obj = model.geom_obj.geom_data_obj
                geom_data_obj.make_subobjs_pickable(subobj_lvl, 1, False)

    def __handle_pickable_geom_change(self, obj):

        if not (self._snapping_transf_center or self._snapping_coord_origin or self._start_creation):
            return

        if self._start_creation:
            snap_type = "creation_start"
        elif self._snapping_transf_center:
            snap_type = "transf_center"
        elif self._snapping_coord_origin:
            snap_type = "coord_origin"

        snap_settings = GD["snap"]
        tgt_type = snap_settings["tgt_type"][snap_type]

        if "obj" in tgt_type:
            if obj.type == "point_helper":
                obj.make_pickable()
            else:
                obj.make_pickable(1)
        elif tgt_type in ("vert", "edge", "poly"):
            if obj.type == "model" and obj.geom_type != "basic_geom":
                geom_data_obj = obj.geom_obj.geom_data_obj
                geom_data_obj.make_subobjs_pickable(tgt_type, 1)

    def __handle_render_mode_change(self, old_mode, new_mode):

        if not (self._snapping_transf_center or self._snapping_coord_origin or self._start_creation):
            return

        if self._start_creation:
            snap_type = "creation_start"
        elif self._snapping_transf_center:
            snap_type = "transf_center"
        elif self._snapping_coord_origin:
            snap_type = "coord_origin"

        snap_settings = GD["snap"]
        tgt_type = snap_settings["tgt_type"][snap_type]
        old_subobj_lvl = "poly" if "shaded" in old_mode else "edge"
        new_subobj_lvl = "poly" if "shaded" in new_mode else "edge"

        if "obj" in tgt_type and old_subobj_lvl != new_subobj_lvl:

            models = set(Mgr.get("model_objs"))
            selection = Mgr.get("selection_top")

            for obj in selection:
                if obj.type == "model" and obj.geom_type != "basic_geom":
                    geom_data_obj = obj.geom_obj.geom_data_obj
                    geom_data_obj.make_subobjs_pickable(new_subobj_lvl, 1, False)

            for model in models:
                if model.geom_type != "basic_geom":
                    geom_data_obj = model.geom_obj.geom_data_obj
                    geom_data_obj.make_subobjs_pickable(old_subobj_lvl, 1, False)
                    geom_data_obj.make_subobjs_pickable(new_subobj_lvl, 1)

    def __handle_lens_type_change(self, lens_type):

        if not (self._snapping_transf_center or self._snapping_coord_origin or self._start_creation):
            return

        if self._start_creation:
            snap_type = "creation_start"
        elif self._snapping_transf_center:
            snap_type = "transf_center"
        elif self._snapping_coord_origin:
            snap_type = "coord_origin"

        snap_settings = GD["snap"]
        tgt_type = snap_settings["tgt_type"][snap_type]

        if "obj" in tgt_type:
            for helper in Mgr.get("dummy_objs") + Mgr.get("group_objs"):
                helper.make_pickable(1)

    def __init_target_checking(self, default_cursor="main"):

        if Mgr.get_state_id() != "transforming":
            self._snap_target_point = None

        self._default_cursor = default_cursor
        snap_settings = GD["snap"]
        snap_type = snap_settings["type"]

        if self._start_creation:
            snap_type = "creation_start"
        elif self._snapping_transf_center:
            snap_type = "transf_center"
        elif self._snapping_coord_origin:
            snap_type = "coord_origin"

        if snap_settings["show_marker"][snap_type]:
            self._snap_target_marker.reparent_to(GD.viewport_origin)
            size = snap_settings["marker_size"][snap_type]
            self._snap_target_marker.set_scale(size)

        picking_cam = Mgr.get("picking_cam")
        picking_cam.active = True
        point_size = snap_settings["size"][snap_type]
        picking_cam.set_film_scale(point_size / 5.)
        picking_cam.set_mask(1)
        pt_type = "src_type" if self._start_transform_mode else "tgt_type"

        if self._snapping_transf_center:

            tgt_type = snap_settings[pt_type]["transf_center"]

        elif self._snapping_coord_origin:

            tgt_type = snap_settings[pt_type]["coord_origin"]

        elif self._start_creation:

            tgt_type = snap_settings[pt_type]["creation_start"]

        elif "creation_phase" in snap_type:

            tgt_type = snap_settings[pt_type][snap_type]

            if snap_settings["show_proj_marker"][snap_type]:
                self._projected_snap_target_marker.reparent_to(GD.viewport_origin)
                self._projected_snap_target_marker.hide()
                size = snap_settings["proj_marker_size"][snap_type]
                self._projected_snap_target_marker.set_scale(size)

            if snap_settings["show_proj_line"][snap_type]:
                dashed_line = Mgr.get("dashed_line")
                dashed_line.reparent_to(GD.world)
                dashed_line.hide()

        else:

            src_type = snap_settings["src_type"][snap_type]
            tgt_type = snap_settings[pt_type][snap_type]

            if not self._start_transform_mode and snap_settings["show_rubber_band"][snap_type]:

                self._rubber_band.reparent_to(GD.world)

                if src_type == "transf_center":
                    pos = Mgr.get("transf_center_pos")
                else:
                    grid_origin = Mgr.get("grid").origin
                    pos = GD.world.get_relative_point(grid_origin, self._snap_target_point)

                self._transf_start_pos = pos
                self._rubber_band.set_pos(pos)

            if snap_settings["use_axis_constraints"][snap_type]:

                if snap_settings["show_proj_marker"][snap_type]:
                    self._projected_snap_target_marker.reparent_to(GD.viewport_origin)
                    self._projected_snap_target_marker.hide()
                    size = snap_settings["proj_marker_size"][snap_type]
                    self._projected_snap_target_marker.set_scale(size)

                if snap_settings["show_proj_line"][snap_type]:
                    dashed_line = Mgr.get("dashed_line")
                    dashed_line.reparent_to(GD.world)
                    dashed_line.hide()

        GD.world.hide(Mgr.get("picking_mask", 1))

        if tgt_type == "grid_point":
            Mgr.get("grid").make_pickable(1)
        elif "obj" in tgt_type:
            Mgr.do("make_point_helpers_pickable", True, 1, True)
            objects = set(Mgr.get("objects"))
            objs_to_xform = self.__get_objs_to_transform()
            incl_objs_to_xform = (self._snapping_transf_center or self._snapping_coord_origin
                                  or self._start_transform_mode or self._start_creation
                                  or "creation_phase" in snap_type)
            objs = objects if incl_objs_to_xform else objects.difference(objs_to_xform)
            for obj in objs:
                if obj.type != "point_helper":
                    obj.make_pickable(1)
            if not incl_objs_to_xform:
                for obj in objs_to_xform:
                    if obj.type == "point_helper":
                        obj.make_pickable(False)
        else:
            self.__make_subobjs_pickable(tgt_type)

        Mgr.render_frame()
        Mgr.remove_task("update_snap_target_cursor")
        Mgr.add_task(self.__update_cursor, "update_snap_target_cursor", sort=0)

    def __end_target_checking(self):

        self._snap_target_marker.detach_node()
        self._projected_snap_target_marker.detach_node()
        self._rubber_band.detach_node()
        Mgr.get("dashed_line").detach_node()
        picking_cam = Mgr.get("picking_cam")
        picking_cam.set_film_scale(1.)
        picking_cam.set_mask(0)
        GD.world.show(Mgr.get("picking_mask", 1))
        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self.__update_cursor()
                                        # is called
        Mgr.set_cursor("main")
        Mgr.remove_task("update_snap_target_cursor")
        snap_settings = GD["snap"]
        snap_type = snap_settings["type"]

        if self._start_creation:
            snap_type = "creation_start"
        elif self._snapping_transf_center:
            snap_type = "transf_center"
        elif self._snapping_coord_origin:
            snap_type = "coord_origin"

        pt_type = "src_type" if self._start_transform_mode else "tgt_type"
        tgt_type = snap_settings[pt_type][snap_type]

        if tgt_type == "grid_point":
            Mgr.get("grid").make_pickable(1, False)
        elif "obj" in tgt_type:
            Mgr.do("make_point_helpers_pickable", False, 1)
            objects = set(Mgr.get("objects"))
            objs_to_xform = self.__get_objs_to_transform()
            incl_objs_to_xform = (self._snapping_transf_center or self._snapping_coord_origin
                                  or self._start_transform_mode or self._start_creation
                                  or "creation_phase" in snap_type)
            objs = objects if incl_objs_to_xform else objects.difference(objs_to_xform)
            for obj in objs:
                if obj.type != "point_helper":
                    obj.make_pickable(1, False)
            if not incl_objs_to_xform:
                for obj in objs_to_xform:
                    if obj.type == "point_helper":
                        obj.make_pickable()
        else:
            self.__make_subobjs_pickable(tgt_type, False)

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            Mgr.set_cursor(self._default_cursor if pixel_under_mouse == VBase4() else "select")
            snap_settings = GD["snap"]
            snap_type = snap_settings["type"]

            if self._start_creation:
                snap_type = "creation_start"

            pt_type = "src_type" if self._start_transform_mode else "tgt_type"
            tgt_type = snap_settings[pt_type][snap_type]
            grid = Mgr.get("grid")
            grid_origin = grid.origin

            if tgt_type == "grid_point":
                self._snap_target_point = grid.get_snap_point(pixel_under_mouse)
            elif "obj" in tgt_type:
                self._snap_target_point = None
                r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                pickable_type = PickableTypes.get(a)
                if pickable_type:
                    color_id = r << 16 | g << 8 | b
                    subobj = Mgr.get(pickable_type, color_id)
                    if subobj:
                        obj = subobj.get_toplevel_object(get_group=True)
                        if tgt_type == "obj_pivot":
                            self._snap_target_point = obj.pivot.get_pos(grid_origin)
                        else:
                            self._snap_target_point = obj.get_center_pos(grid_origin)
            else:
                r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                pickable_type = PickableTypes.get(a)
                if pickable_type == tgt_type:
                    color_id = r << 16 | g << 8 | b
                    subobj = Mgr.get(tgt_type, color_id)
                    self._snap_target_point = subobj.get_center_pos(grid_origin)
                else:
                    self._snap_target_point = None

            if self._snap_target_point:

                if snap_settings["show_marker"][snap_type]:
                    self._snap_target_marker.show()
                    vp_data = GD["viewport"]
                    w, h = vp_data["size_aux" if vp_data[2] == "main" else "size"]
                    cam = GD.cam()
                    snap_target_point = cam.get_relative_point(grid_origin, self._snap_target_point)
                    point = Point2()
                    GD.cam.lens.project(snap_target_point, point)
                    mouse_x, mouse_y = point
                    x = (mouse_x + 1.) * .5 * w
                    y = -(1. - (mouse_y + 1.) * .5) * h
                    self._snap_target_marker.set_pos(x, 0., y)

                if not (self._snapping_transf_center or self._snapping_coord_origin
                        or self._start_transform_mode or self._start_creation):

                    point = GD.world.get_relative_point(grid_origin, self._snap_target_point)

                    if snap_settings["show_rubber_band"][snap_type]:
                        rubber_band = self._rubber_band
                        rubber_band.show()
                        pos = point - self._transf_start_pos
                        pos_data = struct.pack("fff", *pos)
                        array = rubber_band.node().modify_geom(0).modify_vertex_data().modify_array(0)
                        stride = array.array_format.stride
                        memview = memoryview(array).cast("B")
                        memview[stride:] = pos_data
                        array = rubber_band.node().modify_geom(1).modify_vertex_data().modify_array(0)
                        memview = memoryview(array).cast("B")
                        memview[stride:] = pos_data

                    if snap_settings["show_proj_line"][snap_type] and ("creation_phase" in snap_type
                            or snap_settings["use_axis_constraints"][snap_type]):
                        Mgr.do("set_dashed_line_start_pos", point)

            else:

                self._snap_target_marker.hide()
                self._rubber_band.hide()

            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __set_projected_snap_marker_pos(self, projected_point):

        snap_settings = GD["snap"]
        snap_type = snap_settings["type"]
        grid_origin = Mgr.get("grid").origin

        if projected_point:

            if snap_settings["show_proj_marker"][snap_type]:
                self._projected_snap_target_marker.show()
                vp_data = GD["viewport"]
                w, h = vp_data["size_aux" if vp_data[2] == "main" else "size"]
                cam = GD.cam()
                proj_point = cam.get_relative_point(GD.world, projected_point)
                point = Point2()
                GD.cam.lens.project(proj_point, point)
                mouse_x, mouse_y = point
                x = (mouse_x + 1.) * .5 * w
                y = -(1. - (mouse_y + 1.) * .5) * h
                self._projected_snap_target_marker.set_pos(x, 0., y)

            if snap_settings["show_proj_line"][snap_type]:
                Mgr.do("draw_dashed_line", projected_point)
                Mgr.get("dashed_line").show()

        else:

            if snap_settings["show_proj_marker"][snap_type]:
                self._projected_snap_target_marker.hide()

            if snap_settings["show_proj_line"][snap_type]:
                Mgr.get("dashed_line").hide()

    def __set_creation_start(self, start_creation=True):

        self._start_creation = start_creation

    def __enter_transf_start_snap_mode(self, prev_state_id, active):

        self._start_transform_mode = True
        self.__init_target_checking("main")
        Mgr.update_app("status", ["snap_transf_start"])

    def __exit_transf_start_snap_mode(self, next_state_id, active):

        self.__end_target_checking()
        self._start_transform_mode = False

    def __enter_transf_center_snap_mode(self, prev_state_id, active):

        self._snapping_transf_center = True
        self.__init_target_checking("main")
        Mgr.update_app("status", ["snap_transf_center"])

        if not active:
            Mgr.get("gizmo_picking_cam").node().active = False
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = False

    def __exit_transf_center_snap_mode(self, next_state_id, active):

        self.__end_target_checking()
        self._snapping_transf_center = False

        if not active:

            Mgr.get("gizmo_picking_cam").node().active = True
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = True

            def cancel_snap():

                tc_type_prev = GD["transf_center_type"]
                obj = Mgr.get("transf_center_obj")
                name_obj = obj.name_obj if obj else None
                Mgr.update_locally("transf_center", tc_type_prev, obj)
                Mgr.update_remotely("transf_center", tc_type_prev, name_obj)

            if self._transf_center_snap_cancelled:
                cancel_snap()
                return

            if self._snap_target_point:
                pos = GD.world.get_relative_point(Mgr.get("grid").origin, self._snap_target_point)
                Mgr.do("set_custom_transf_center_transform", pos)
                Mgr.update_app("transf_center", "snap_pt")
            else:
                cancel_snap()

    def __enter_coord_origin_snap_mode(self, prev_state_id, active):

        self._snapping_coord_origin = True
        self.__init_target_checking("main")
        Mgr.update_app("status", ["snap_coord_origin"])

        if not active:
            Mgr.get("gizmo_picking_cam").node().active = False
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = False

    def __exit_coord_origin_snap_mode(self, next_state_id, active):

        self.__end_target_checking()
        self._snapping_coord_origin = False

        if not active:

            Mgr.get("gizmo_picking_cam").node().active = True
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = True

            def cancel_snap():

                cs_type_prev = GD["coord_sys_type"]
                obj = Mgr.get("coord_sys_obj")
                name_obj = obj.name_obj if obj else None
                Mgr.update_locally("coord_sys", cs_type_prev, obj)
                Mgr.update_remotely("coord_sys", cs_type_prev, name_obj)

            if self._coord_origin_snap_cancelled:
                cancel_snap()
                return

            if self._snap_target_point:
                pos = GD.world.get_relative_point(Mgr.get("grid").origin, self._snap_target_point)
                Mgr.do("set_custom_coord_sys_transform", pos)
                Mgr.update_app("coord_sys", "snap_pt")
            else:
                cancel_snap()


MainObjects.add_class(SnapManager)
