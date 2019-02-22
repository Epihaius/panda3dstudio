from .base import *


class AlignmentManager(BaseObject):

    def __init__(self):

        self._pixel_under_mouse = None
        self._picked_point = None
        self._target_type = None
        self._target_start_xforms = None
        self._restore_picking_via_poly = False

        self._target_id = None
        self._surface_normal = Vec3()
        self._surface_pos = Point3()

        self._normal_viz = self.__create_normal_viz()
        self._normal_viz_size = 1.
        self._normal_peeker = None
        self._depth_peeker = None
        self._listener = DirectObject()

        cam = Camera("surface_align_cam")
        cam.set_active(False)
        self._surf_align_cam = NodePath(cam)
        lens = cam.get_lens()
        lens.set_fov(.1)

        Mgr.add_app_updater("object_alignment", self.__update_alignment)

        add_state = Mgr.add_state
        add_state("alignment_target_picking_mode", -10, self.__enter_target_picking_mode,
                  self.__exit_target_picking_mode)
        add_state("surface_alignment_mode", -10, self.__enter_surface_align_mode,
                  self.__exit_surface_align_mode)

        mod_alt = GlobalData["mod_key_codes"]["alt"]
        mod_ctrl = GlobalData["mod_key_codes"]["ctrl"]
        mod_shift = GlobalData["mod_key_codes"]["shift"]
        bind = Mgr.bind_state
        bind("alignment_target_picking_mode", "align target picking -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("alignment_target_picking_mode", "pick align target", "mouse1",
             self.__pick)
        bind("alignment_target_picking_mode", "quit align target picking", "escape",
             self.__cancel_target_picking)
        bind("alignment_target_picking_mode", "cancel align target picking", "mouse3",
             self.__cancel_target_picking)
        bind("alignment_target_picking_mode", "abort align target picking", "focus_loss",
             self.__cancel_target_picking)
        bind("alignment_target_picking_mode", "align ctrl-right-click", "{:d}|mouse3".format(mod_ctrl),
             lambda: Mgr.update_remotely("main_context"))
        bind("surface_alignment_mode", "quit surface-align", "escape",
             self.__cancel_surface_align)
        bind("surface_alignment_mode", "cancel surface-align", "mouse3",
             self.__cancel_surface_align)
        bind("surface_alignment_mode", "abort surface-align", "focus_loss",
             self.__cancel_surface_align)
        bind("surface_alignment_mode", "incr. normal viz size", "wheel_up",
             self.__incr_normal_viz_size)
        bind("surface_alignment_mode", "decr. normal viz size", "wheel_down",
             self.__decr_normal_viz_size)
        bind("surface_alignment_mode", "align to surface", "mouse1",
             self.__align_to_surface)

        status_data = GlobalData["status_data"]
        mode_text = "Pick object to align to"
        info_text = "LMB to pick object; RMB or <Escape> to cancel"
        status_data["pick_alignment_target_obj"] = {"mode": mode_text, "info": info_text}
        mode_text = "Pick surface to align to"
        info_text = "LMB to pick model; RMB or <Escape> to cancel"
        status_data["pick_alignment_target_surface"] = {"mode": mode_text, "info": info_text}
        mode_text = "Align to surface"
        info_text = "Click surface point to align selection; MWheel or <+>/<-> to change" \
            " display size of surface normal; RMB or <Escape> to cancel alignment"
        status_data["surface_alignment"] = {"mode": mode_text, "info": info_text}

    def __enter_target_picking_mode(self, prev_state_id, is_active):

        obj_lvl = GlobalData["active_obj_level"]
        picking_mask = Mgr.get("picking_mask")

        if not is_active:

            models = set(Mgr.get("model_objs"))
            selection = Mgr.get("selection_top")

            if "obj" in self._target_type:
                if obj_lvl != "top":
                    Mgr.do("enable_object_name_checking")
                    Mgr.get("object_root").show(picking_mask)
                    if obj_lvl != "poly":
                        if GlobalData["subobj_edit_options"]["pick_via_poly"]:
                            Mgr.update_locally("picking_via_poly", False)
                            self._restore_picking_via_poly = True
                        for model in selection:
                            model.get_geom_object().get_geom_data_object().make_polys_pickable()
            elif self._target_type == "surface":
                if obj_lvl == "top":
                    Mgr.get("object_root").hide(picking_mask)
                    for model in models:
                        model.get_origin().show_through(picking_mask)
                else:
                    Mgr.do("enable_object_name_checking")
                    for model in models:
                        model.get_origin().show_through(picking_mask)
                    if obj_lvl != "poly":
                        if GlobalData["subobj_edit_options"]["pick_via_poly"]:
                            Mgr.update_locally("picking_via_poly", False)
                            self._restore_picking_via_poly = True
                        for model in selection:
                            model.get_geom_object().get_geom_data_object().make_polys_pickable()

            def handler(obj_ids):

                if obj_ids:
                    obj = Mgr.get("object", obj_ids[0])
                    self.__pick(picked_obj=obj)

            object_types = ["model"] if self._target_type == "surface" else None
            Mgr.update_remotely("selection_by_name", "", "Pick alignment target",
                                object_types, False, "Pick", handler)

        Mgr.add_task(self.__update_cursor, "update_align_picking_cursor")

        if self._target_type == "surface":
            Mgr.update_app("status", ["pick_alignment_target_surface"])
        else:
            Mgr.update_app("status", ["pick_alignment_target_obj"])

    def __exit_target_picking_mode(self, next_state_id, is_active):

        obj_lvl = GlobalData["active_obj_level"]
        picking_mask = Mgr.get("picking_mask")

        if not is_active:

            models = set(Mgr.get("model_objs"))
            selection = Mgr.get("selection_top")

            if "obj" in self._target_type:
                if obj_lvl != "top":
                    Mgr.do("disable_object_name_checking")
                    Mgr.get("object_root").hide(picking_mask)
                    if obj_lvl != "poly":
                        for model in selection:
                            model.get_geom_object().get_geom_data_object().make_polys_pickable(False)
                        if self._restore_picking_via_poly:
                            Mgr.update_locally("picking_via_poly", True)
                            self._restore_picking_via_poly = False
            elif self._target_type == "surface":
                if obj_lvl == "top":
                    Mgr.get("object_root").show(picking_mask)
                    for model in models:
                        model.get_origin().show(picking_mask)
                else:
                    Mgr.do("disable_object_name_checking")
                    for model in models:
                        model.get_origin().show(picking_mask)
                    if obj_lvl != "poly":
                        for model in selection:
                            model.get_geom_object().get_geom_data_object().make_polys_pickable(False)
                        if self._restore_picking_via_poly:
                            Mgr.update_locally("picking_via_poly", True)
                            self._restore_picking_via_poly = False

            Mgr.update_remotely("selection_by_name", "default")

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self.__update_cursor()
                                        # is called
        Mgr.remove_task("update_align_picking_cursor")
        Mgr.set_cursor("main")

    def __pick(self, picked_obj=None):

        obj = picked_obj if picked_obj else Mgr.get("object", pixel_color=self._pixel_under_mouse)
        Mgr.exit_state("alignment_target_picking_mode")

        if obj and (obj.get_type() != "group" or not obj.is_open()):
            self._target_id = obj.get_id()
            if self._target_type == "surface":
                Mgr.enter_state("surface_alignment_mode")
            else:
                Mgr.update_remotely("object_alignment", "align", self._target_type, obj.get_name())
        elif self._target_type == "surface":
            Mgr.update_remotely("object_alignment", "msg", "invalid_surface")
        else:
            Mgr.update_remotely("object_alignment", "msg", "invalid_target")

    def __cancel_target_picking(self):

        Mgr.exit_state("alignment_target_picking_mode")

    def __create_normal_viz(self):

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("normal_viz", vertex_format, Geom.UH_static)
        vertex_data.set_num_rows(2)
        lines = GeomLines(Geom.UH_static)
        lines.add_next_vertices(2)
        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        geom_node = GeomNode("normal_viz")
        geom_node.add_geom(geom)
        normal_viz = NodePath(geom_node)
        normal_viz.hide(Mgr.get("picking_mask"))
        normal_viz.set_color(0., 1., 0., 1.)

        return normal_viz

    def __incr_normal_viz_size(self):

        self._normal_viz_size += max(.01, self._normal_viz_size * .1)
        self._normal_viz.set_scale(self._normal_viz_size)

    def __decr_normal_viz_size(self):

        self._normal_viz_size = max(.01, self._normal_viz_size - max(.01, self._normal_viz_size * .1))
        self._normal_viz.set_scale(self._normal_viz_size)

    def __draw_normal_viz(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        model = Mgr.get("model", self._target_id)
        origin = model.get_origin()
        normal_viz = self._normal_viz

        if self._normal_peeker:
            pixel = VBase4()
            self._normal_peeker.lookup(pixel, .5, .5)
            x, y, z, _ = (pixel - Vec3(.5, .5, .5)) * 2.
            if x == y == z == -1.:
                normal_viz.detach_node()
                Mgr.set_cursor("main")
                return task.cont
            Mgr.set_cursor("select")
            normal_viz.reparent_to(origin)
            normal_viz.set_pos(0., 0., 0.)
            normal_viz.look_at(x, y, z)
            x_vec = self.world.get_relative_vector(normal_viz, Vec3.right())
            z_vec = self.world.get_relative_vector(normal_viz, Vec3.up())
            x, y, z = self._surface_normal = z_vec.cross(x_vec).normalized()
            array = normal_viz.node().modify_geom(0).modify_vertex_data().modify_array(0)
            stride = array.array_format.stride
            memview = memoryview(array).cast("B")
            memview[stride:] = struct.pack("fff", x, y, z)
            normal_viz.set_hpr(0., 0., 0.)
            normal_viz.detach_node()
        else:
            self._normal_peeker = self._normal_tex.peek()
            return task.cont

        if self._depth_peeker:
            surf_align_cam = self._surf_align_cam
            pixel = VBase4()
            self._depth_peeker.lookup(pixel, .5, .5)
            lens = surf_align_cam.node().get_lens()
            point = Point3()
            lens.extrude_depth(Point3(0., 0., pixel[0]), point)
            depth = point[1] * .5
            screen_pos = self.mouse_watcher.get_mouse()
            far_point = Point3()
            self.cam.lens.extrude(screen_pos, Point3(), far_point)
            dir_vec = surf_align_cam.get_relative_vector(self.cam(), Vec3(*far_point)).normalized()
            dist_vec = self.world.get_relative_vector(surf_align_cam, dir_vec * depth)
            self._surface_pos = pos = surf_align_cam.get_pos(self.world) + dist_vec
            normal_viz.reparent_to(self.world)
            normal_viz.set_pos(pos)
        else:
            self._depth_peeker = self._depth_tex.peek()

        return task.cont

    def __enter_surface_align_mode(self, prev_state_id, is_active):

        cam = self._surf_align_cam
        cam_node = cam.node()
        base = Mgr.get("base")
        self._normal_tex = Texture("normal")
        props = FrameBufferProperties()
        props.set_rgba_bits(16, 16, 16, 16)
        props.set_depth_bits(16)
        base = Mgr.get("base")
        self._normal_buffer = bfr = base.win.make_texture_buffer(
                                                                 "buffer",
                                                                 1, 1,
                                                                 self._normal_tex,
                                                                 to_ram=True,
                                                                 fbp=props
                                                                )
        self._depth_tex = Texture("depth")
        self._depth_tex.set_format(Texture.F_depth_component)
        bfr.add_render_texture(self._depth_tex, GraphicsOutput.RTM_copy_ram, DrawableRegion.RTP_depth)
        bfr.set_clear_color((0., 0., 0., 0.))
        bfr.set_clear_color_active(True)
        cam_node.set_active(True)
        base.make_camera(bfr, useCamera=cam)
        cam.reparent_to(Mgr.get("picking_cam")())

        state_np = NodePath("state_np")
        sh = shaders.surface_normal
        vs = sh.VERT_SHADER
        fs = sh.FRAG_SHADER
        shader = Shader.make(Shader.SL_GLSL, vs, fs)
        state_np.set_shader(shader, 1)
        state_np.set_light_off(1)
        state_np.set_color_off(1)
        state_np.set_material_off(1)
        state_np.set_texture_off(1)
        state_np.set_transparency(TransparencyAttrib.M_none, 1)
        state = state_np.get_state()
        cam_node.set_initial_state(state)
        model = Mgr.get("model", self._target_id)

        if model.get_geom_type() == "basic_geom":
            cam_node.set_scene(model.get_geom_object().get_geom())
        else:
            cam_node.set_scene(model.get_geom_object().get_geom_data_object().get_toplevel_geom())

        self._listener.accept("+", self.__incr_normal_viz_size)
        self._listener.accept("+-repeat", self.__incr_normal_viz_size)
        self._listener.accept("-", self.__decr_normal_viz_size)
        self._listener.accept("--repeat", self.__decr_normal_viz_size)

        Mgr.add_task(self.__draw_normal_viz, "draw_normal_viz", sort=3)
        Mgr.update_app("status", ["surface_alignment"])

    def __exit_surface_align_mode(self, next_state_id, is_active):

        if not self._normal_buffer:
            return

        self._listener.ignore_all()
        Mgr.remove_task("draw_normal_viz")
        base = Mgr.get("base")
        base.graphics_engine.remove_window(self._normal_buffer)
        self._normal_buffer = None
        cam = self._surf_align_cam
        cam_node = cam.node()
        cam_node.set_active(False)
        cam_node.set_scene(Mgr.get("object_root"))
        cam_node.set_initial_state(RenderState.make_empty())
        self._normal_peeker = None
        self._depth_peeker = None

    def __cancel_surface_align(self):

        Mgr.exit_state("surface_alignment_mode")
        self._normal_viz.detach_node()

    def __align_to_surface(self):

        if self._normal_viz.has_parent():
            Mgr.exit_state("surface_alignment_mode")
            model = Mgr.get("model", self._target_id)
            Mgr.update_remotely("object_alignment", "align", "surface", model.get_name())

    def __align(self, options, preview=True, end_preview=False):

        backup = Mgr.get("xform_backup")

        if end_preview:
            Mgr.do("restore_xform_backup")
            return

        if preview and not backup:
            Mgr.do("create_xform_backup")

        target_type = self._target_type
        obj_axis_point = target_type == "obj_axis_point"

        obj_lvl = GlobalData["active_obj_level"]
        xform_target_type = GlobalData["transform_target_type"]
        cs_type = GlobalData["coord_sys_type"]
        tc_type = GlobalData["transf_center_type"]

        if obj_lvl != "top":
            Mgr.do("restore_xform_backup", clear=False)

        if obj_lvl == "top" and tc_type != "pivot":
            GlobalData["transf_center_type"] = "pivot"

        if target_type == "view":
            grid_origin = self.cam.target.attach_new_node("view_center")
            grid_origin.set_p(90.)
        else:
            grid_origin = None if cs_type == "local" else Mgr.get(("grid", "origin"))

        target_obj = None if target_type == "view" else Mgr.get("object", self._target_id)

        if obj_lvl == "top":

            selection = Mgr.get("sorted_hierarchy", Mgr.get("selection_top"))

            if target_obj in selection:
                cur_pivot_xform = target_obj.get_pivot().get_transform(self.world)
                cur_origin_xform = target_obj.get_origin().get_transform(self.world)
                if not self._target_start_xforms:
                    self._target_start_xforms = (cur_pivot_xform, cur_origin_xform)
                else:
                    pivot_xform, origin_xform = self._target_start_xforms
                    target_obj.get_pivot().set_transform(self.world, pivot_xform)
                    target_obj.get_origin().set_transform(self.world, origin_xform)

        else:

            selection = Mgr.get("selection")

        axis_opts = options["axes"]
        point_opts = options["points"]

        if target_type != "surface":
            if target_type == "view":
                tgt_quat = grid_origin.get_quat(self.world)
            else:
                tgt_quat = target_obj.get_pivot().get_quat(self.world)
            tgt_vecs = {"x": tgt_quat.get_right(), "y": tgt_quat.get_forward(), "z": tgt_quat.get_up()}

        if obj_lvl == "top" and target_obj in selection:
            target_obj.get_pivot().set_transform(self.world, cur_pivot_xform)
            target_obj.get_origin().set_transform(self.world, cur_origin_xform)

        quat = Quat()

        axis_vecs = {}

        if target_type == "surface":
            axis_id = "y" if obj_lvl == "normal" else "z"
            if axis_opts[axis_id]["align"]:
                vec = self._surface_normal
                if axis_opts[axis_id]["inv"]:
                    vec = vec * -1.
                axis_vecs[axis_opts[axis_id]["tgt"]] = vec
        elif target_type != "obj_axis_point":
            for axis_id in "xyz":
                if axis_opts[axis_id]["align"]:
                    axis_vecs[axis_id] = vec = tgt_vecs[axis_opts[axis_id]["tgt"]]
                    if axis_opts[axis_id]["inv"]:
                        vec *= -1.

        if len(axis_vecs) == 2:
            if "y" in axis_vecs:
                fwd_vec = axis_vecs["y"]
            else:
                fwd_vec = axis_vecs["z"].cross(axis_vecs["x"])
            if "z" in axis_vecs:
                up_vec = axis_vecs["z"]
            else:
                up_vec = axis_vecs["x"].cross(axis_vecs["y"])
            look_at(quat, fwd_vec, up_vec)

        def get_min_max(obj, ref_node):

            if obj.get_type() == "model":
                bbox_origin = obj.get_bbox().get_origin()
                bbox_origin.detach_node()

            obj_origin = obj.get_origin()
            bounds = obj_origin.get_tight_bounds()

            if not bounds:
                center_pos = obj.get_center_pos(ref_node)
                bounds = (center_pos, center_pos)

            if obj.get_type() == "model":
                bbox_origin.reparent_to(obj_origin)

            return bounds

        def get_target_point(axis_id, ref_node):

            if target_type == "view":
                return grid_origin.get_pos(ref_node)
            elif target_type == "surface":
                return ref_node.get_relative_point(self.world, self._surface_pos)

            if obj_lvl == "top" and target_obj in selection:
                xform1, xform2 = self._target_start_xforms
                pivot = NodePath("tmp_pivot")
                pivot.set_transform(xform1)
                origin = target_obj.get_origin()
                origin_xform = origin.get_transform()
                origin.reparent_to(pivot)
                origin.set_transform(self.world, xform2)
            else:
                pivot = target_obj.get_pivot()

            point_type = point_opts[axis_id]["tgt"]
            local_minmax = not grid_origin or options["local_minmax"]

            if point_type == "pivot":
                point = pivot.get_pos(self.world)
            elif point_type == "center":
                point = target_obj.get_center_pos(self.world)
            else:
                if local_minmax:
                    point_min, point_max = get_min_max(target_obj, pivot)
                    point_min = self.world.get_relative_point(pivot, point_min)
                    point_max = self.world.get_relative_point(pivot, point_max)
                else:
                    target_obj.get_origin().wrt_reparent_to(grid_origin)
                    point_min, point_max = get_min_max(target_obj, grid_origin)
                    target_obj.get_origin().wrt_reparent_to(pivot)
                point = point_min if point_type == "min" else point_max

            if obj_lvl == "top" and target_obj in selection:
                origin.reparent_to(target_obj.get_pivot())
                origin.set_transform(origin_xform)

            if point_type in ("pivot", "center") or local_minmax:
                point = ref_node.get_relative_point(self.world, point)

            return point

        tgt_points = {}

        def get_rel_target_pos(obj):

            node = obj.get_origin() if xform_target_type == "geom" else obj.get_pivot()
            point = node.get_pos(grid_origin) if grid_origin else Point3()

            if obj_lvl != "top":
                center_pos = selection.get_center_pos()

            for i, axis_id in enumerate("xyz"):

                if axis_id not in tgt_points:
                    continue

                point_type = point_opts[axis_id]["sel"] if obj_lvl == "top" else "center"
                tgt_point = tgt_points[axis_id]

                if point_type == "pivot":
                    if tgt_point:
                        point[i] = tgt_point[i]
                    else:
                        point[i] = get_target_point(axis_id, obj.get_pivot())[i]
                elif point_type == "center":
                    if tgt_point:
                        node_pos = node.get_pos(grid_origin)
                        if obj_lvl == "top":
                            sel_point = obj.get_center_pos(grid_origin)
                        else:
                            sel_point = grid_origin.get_relative_point(self.world, center_pos)
                        point[i] = (node_pos + (tgt_point - sel_point))[i]
                    else:
                        tgt_point = get_target_point(axis_id, node)
                        if obj_lvl == "top":
                            sel_point = obj.get_center_pos(node)
                        else:
                            sel_point = node.get_relative_point(self.world, center_pos)
                        point[i] = (tgt_point - sel_point)[i]
                else:
                    if tgt_point:
                        node_pos = node.get_pos(grid_origin)
                        if options["local_minmax"] or (target_type == "view" and cs_type == "local"):
                            if xform_target_type == "geom":
                                origin = obj.get_origin()
                                xform = origin.get_transform()
                                origin.set_transform(TransformState.make_identity())
                                point_min, point_max = get_min_max(obj, origin)
                                origin.set_transform(xform)
                            else:
                                point_min, point_max = get_min_max(obj, node)
                            sel_point = point_min if point_type == "min" else point_max
                            sel_point = grid_origin.get_relative_point(node, sel_point)
                        else:
                            obj.get_origin().wrt_reparent_to(grid_origin)
                            point_min, point_max = get_min_max(obj, grid_origin)
                            obj.get_origin().wrt_reparent_to(obj.get_pivot())
                            sel_point = point_min if point_type == "min" else point_max
                        point[i] = (node_pos + (tgt_point - sel_point))[i]
                    else:
                        tgt_point = get_target_point(axis_id, node)
                        if xform_target_type == "geom":
                            origin = obj.get_origin()
                            xform = origin.get_transform()
                            origin.set_transform(TransformState.make_identity())
                            point_min, point_max = get_min_max(obj, origin)
                            origin.set_transform(xform)
                        else:
                            point_min, point_max = get_min_max(obj, node)
                        sel_point = point_min if point_type == "min" else point_max
                        point[i] = (tgt_point - sel_point)[i]

            point = self.world.get_relative_point(grid_origin if grid_origin else node, point)

            return point

        if target_type == "obj_axis_point":
            tgt_point = get_target_point("y", self.world) if grid_origin else None
        elif obj_lvl != "normal":
            for axis_id in "xyz":
                if point_opts[axis_id]["align"]:
                    tgt_point = get_target_point(axis_id, grid_origin) if grid_origin else None
                    tgt_points[axis_id] = tgt_point

        change = False
        lock_normals = not preview

        for obj in (selection if obj_lvl == "top" else Mgr.get("selection_top")):

            if obj_lvl == "top":
                if backup:
                    Mgr.update_locally("transf_component", "", "",
                        backup[obj], False, [obj], False, True, NodePath.set_transform)
            else:
                geom_data_obj = obj.get_geom_object().get_geom_data_object()

            node = obj.get_origin() if xform_target_type == "geom" else obj.get_pivot()

            if target_type == "obj_axis_point":
                sel_point = node.get_pos(self.world)
                if not tgt_point:
                    ref_node = obj.get_pivot() if point_opts["y"]["tgt"] == "pivot" else node
                    tgt_point = self.world.get_relative_point(ref_node, get_target_point("y", ref_node))
                vec = (tgt_point - sel_point).normalized()
                if axis_opts["y"]["inv"]:
                    vec = vec * -1.
                axis_vecs[axis_opts["y"]["tgt"]] = vec

            if len(axis_vecs) == 1:

                axis_id, vec = list(axis_vecs.items())[0]

                if obj_lvl == "normal":

                    if target_type == "obj_axis_point":
                        toward = not axis_opts["y"]["inv"]
                        selection.aim_at_point(tgt_point, self.world, toward, add_to_hist=False,
                                               objects=[obj], lock_normals=lock_normals)
                    else:
                        vec = obj.get_origin().get_relative_vector(self.world, vec)
                        mat = Mat4.scale_mat(0., 0., 0.) * Mat4.translate_mat(*vec)
                        data = {"mats": [(mat, "origin")]}
                        selection.custom_transform(data, add_to_hist=False, objects=[obj],
                                                   lock_normals=lock_normals)

                else:

                    old_quat = node.get_quat(self.world)
                    old_vecs = {
                        "x": old_quat.get_right(),
                        "y": old_quat.get_forward(),
                        "z": old_quat.get_up()
                    }
                    new_quat = Quat()

                    if vec.dot(old_vecs[axis_id]) < .9999:

                        if axis_id == "x":
                            if vec == old_vecs["z"]:
                                fwd_vec = old_vecs["y"]
                                up_vec = -old_vecs["x"]
                            elif vec == -old_vecs["z"]:
                                fwd_vec = old_vecs["y"]
                                up_vec = old_vecs["x"]
                            else:
                                fwd_vec = old_vecs["z"].cross(vec)
                                up_vec = vec.cross(fwd_vec)
                        elif axis_id == "y":
                            fwd_vec = vec
                            if vec == old_vecs["z"]:
                                up_vec = -old_vecs["y"]
                            elif vec == -old_vecs["z"]:
                                up_vec = old_vecs["y"]
                            else:
                                up_vec = old_vecs["z"]
                        elif axis_id == "z":
                            up_vec = vec
                            if vec == -old_vecs["z"]:
                                fwd_vec = old_vecs["y"]
                            else:
                                right_vec = old_vecs["z"].cross(vec)
                                if old_vecs["x"].dot(right_vec) < 0.:
                                    right_vec *= -1.
                                fwd_vec = vec.cross(right_vec)

                        look_at(new_quat, fwd_vec, up_vec)

                        if obj_lvl == "top":
                            Mgr.update_locally("transf_component", "", "",
                                new_quat, False, [obj], False, True, NodePath.set_quat)
                        else:
                            tmp_node = node.attach_new_node("tmp")
                            tmp_node.set_quat(self.world, new_quat)
                            mat = tmp_node.get_mat(node)
                            tmp_node.detach_node()
                            data = {"mats": [(mat, "pivot")]}
                            selection.custom_transform(data, add_to_hist=False, objects=[obj])

                change = True

            elif len(axis_vecs) == 2:

                if obj_lvl == "top":
                    Mgr.update_locally("transf_component", "", "",
                        quat, False, [obj], False, True, NodePath.set_quat)
                else:
                    tmp_node = node.attach_new_node("tmp")
                    tmp_node.set_quat(self.world, quat)
                    mat = tmp_node.get_mat(node)
                    tmp_node.detach_node()
                    data = {"mats": [(mat, "pivot")]}
                    selection.custom_transform(data, add_to_hist=False, objects=[obj],
                                               lock_normals=lock_normals)

                change = True

            if tgt_points:

                if obj_lvl == "top":

                    point = get_rel_target_pos(obj)
                    Mgr.update_locally("transf_component", "", "",
                        point, False, [obj], False, True, NodePath.set_pos)

                else:

                    if options["per_vertex"]:

                        point = Point3()
                        scale = VBase3(1., 1., 1.)

                        for i, axis_id in enumerate("xyz"):
                            if axis_id in tgt_points:
                                scale[i] = 0.
                                tgt_point = tgt_points[axis_id]
                                point[i] = (tgt_point if tgt_point else get_target_point(axis_id, node))[i]

                        mat = Mat4.scale_mat(scale) * Mat4.translate_mat(point)
                        # use "custom", in case subobjects are aligned to the view
                        data = {"mats": [(mat, "custom" if grid_origin else "pivot")], "ref_node": grid_origin}

                    else:

                        tmp_node = node.attach_new_node("tmp")
                        tmp_node.set_pos(self.world, get_rel_target_pos(obj))
                        mat = tmp_node.get_mat(node)
                        tmp_node.detach_node()
                        data = {"mats": [(mat, "pivot")]}

                    selection.custom_transform(data, add_to_hist=False, objects=[obj],
                                               lock_normals=lock_normals)

                change = True

        if obj_lvl == "top" and tc_type != "pivot":
            GlobalData["transf_center_type"] = tc_type

        if target_type == "view":

            if options["planar"]:
                point = grid_origin.get_relative_point(self.world, selection.get_center_pos())
                mat = Mat4.scale_mat(1., 1., 0.) * Mat4.translate_mat(0., 0., point.z)
                data = {"mats": [(mat, "custom")], "ref_node": grid_origin}
                selection.custom_transform(data, add_to_hist=False, lock_normals=lock_normals)
                change = True

            grid_origin.detach_node()

        if not preview:

            if target_type == "surface":
                self._normal_viz.detach_node()

            backup.clear()
            self._target_start_xforms = None

            if change:

                if obj_lvl == "top":

                    self.__add_history(selection, point_opts)

                else:

                    event_descr = "Aim {}" if obj_axis_point else "Align {}"

                    if obj_axis_point:
                        obj = Mgr.get("object", self._target_id)
                        point_type = point_opts["y"]["tgt"]
                        target_descr = '"{}" {}'.format(obj.get_name(), point_type)
                    elif target_type == "view":
                        target_descr = "view"
                    elif target_type == "surface":
                        obj = Mgr.get("object", self._target_id)
                        target_descr = 'surface of "{}"'.format(obj.get_name())
                    else:
                        obj = Mgr.get("object", self._target_id)
                        target_descr = '"{}"'.format(obj.get_name())

                    event_descr += '\n\n{} {}'.format("at" if obj_axis_point else "to", target_descr)
                    selection.add_history("custom", descr=event_descr)

    def __add_history(self, objs_to_align, point_opts):

        obj_data = {}
        event_data = {"objects": obj_data}
        Mgr.do("update_history_time")

        target_type = self._target_type
        obj_axis_point = target_type == "obj_axis_point"
        obj_count = len(objs_to_align)
        xform_target_type = GlobalData["transform_target_type"]
        event_descr = "Aim " if obj_axis_point else "Align "

        if obj_count > 1:

            if xform_target_type == "all":
                event_descr += '{:d} objects:\n'.format(obj_count)
            elif xform_target_type == "geom":
                event_descr += "{:d} objects' geometry:\n".format(obj_count)
            elif xform_target_type == "pivot":
                event_descr += "{:d} objects' pivots:\n".format(obj_count)
            elif xform_target_type == "no_children":
                event_descr += '{:d} objects without children:\n'.format(obj_count)

            for obj in objs_to_align:
                event_descr += '\n    "{}"'.format(obj.get_name())

        else:

            if xform_target_type == "all":
                event_descr += '"{}"'.format(objs_to_align[0].get_name())
            elif xform_target_type == "geom":
                event_descr += '"{}" geometry'.format(objs_to_align[0].get_name())
            elif xform_target_type == "pivot":
                event_descr += '"{}" pivot'.format(objs_to_align[0].get_name())
            elif xform_target_type == "no_children":
                event_descr += '"{}" without children'.format(objs_to_align[0].get_name())

        if obj_axis_point:
            obj = Mgr.get("object", self._target_id)
            point_type = point_opts["y"]["tgt"]
            target_descr = '"{}" {}'.format(obj.get_name(), point_type)
        elif target_type == "view":
            target_descr = "view"
        elif target_type == "surface":
            obj = Mgr.get("object", self._target_id)
            target_descr = 'surface of "{}"'.format(obj.get_name())
        else:
            obj = Mgr.get("object", self._target_id)
            target_descr = '"{}"'.format(obj.get_name())

        event_descr += '\n\n{} {}'.format("at" if obj_axis_point else "to", target_descr)

        if xform_target_type == "all":

            for obj in objs_to_align:
                obj_data[obj.get_id()] = obj.get_data_to_store("prop_change", "transform")

        elif xform_target_type == "geom":

            for obj in objs_to_align:
                obj_data[obj.get_id()] = obj.get_data_to_store("prop_change", "origin_transform")

        else:

            objs = set(objs_to_align)

            for obj in objs_to_align:
                objs.update(obj.get_children())

            for obj in objs:
                obj_data[obj.get_id()] = data = {}
                data.update(obj.get_data_to_store("prop_change", "transform"))

            for obj in objs_to_align:
                data = obj_data[obj.get_id()]
                data.update(obj.get_data_to_store("prop_change", "origin_transform"))

        if xform_target_type == "pivot":
            for obj in objs_to_align:
                if obj.get_type() == "group":
                    for member in obj.get_members():
                        data = member.get_data_to_store("prop_change", "transform")
                        obj_data.setdefault(member.get_id(), {}).update(data)

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __update_alignment(self, update_type="", *args):

        if GlobalData["transform_target_type"] == "links":
            Mgr.update_remotely("object_alignment", "msg", "links")
            return

        if GlobalData["active_obj_level"] == "top":
            if not Mgr.get("sorted_hierarchy", Mgr.get("selection_top")):
                Mgr.update_remotely("object_alignment", "msg", "invalid_sel")
                return
        elif not Mgr.get("selection"):
            Mgr.update_remotely("object_alignment", "msg", "no_subobj_sel")
            return

        if update_type == "pick_target":
            target_type = args[0]
            if target_type == "view":
                Mgr.exit_states(min_persistence=-99)
                Mgr.update_remotely("object_alignment", "align", target_type)
                self._target_type = target_type
            else:
                if Mgr.get_state_id() == "alignment_target_picking_mode":
                    Mgr.exit_state("alignment_target_picking_mode")
                self._target_type = target_type
                Mgr.enter_state("alignment_target_picking_mode")
        elif update_type == "cancel":
            if self._target_type == "surface":
                self._normal_viz.detach_node()
            Mgr.do("restore_xform_backup")
            self._target_start_xforms = None
        else:
            self.__align(*args)

    def __update_cursor(self, task):

        if not Mgr.get("selection"):
            Mgr.exit_state("alignment_target_picking_mode")

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont


MainObjects.add_class(AlignmentManager)
