from .base import *


class SelectionTransformBase(BaseObject):

    def __init__(self, obj_level):

        self._obj_level = obj_level
        self._obj_root = Mgr.get("object_root")
        self._center = self._obj_root.attach_new_node("selection_center")
        self._pivot = self._obj_root.attach_new_node("selection_pivot")

        self._pivot_used = False
        self._pivot_start = None
        self._start_positions = []
        self._start_quats = []
        self._start_mats = []
        self._offset_vecs = []

        if obj_level == "top":
            pos_setters = {"X": NodePath.set_x,
                           "Y": NodePath.set_y, "Z": NodePath.set_z}
            hpr_setters = {"X": NodePath.set_p,
                           "Y": NodePath.set_r, "Z": NodePath.set_h}
            scal_setters = {"X": NodePath.set_sx,
                            "Y": NodePath.set_sy, "Z": NodePath.set_sz}
            self._value_setters = {"translate": pos_setters,
                                   "rotate": hpr_setters, "scale": scal_setters}
            pos_getters = {"X": NodePath.get_x,
                           "Y": NodePath.get_y, "Z": NodePath.get_z}
            hpr_getters = {"X": NodePath.get_p,
                           "Y": NodePath.get_r, "Z": NodePath.get_h}
            scal_getters = {"X": NodePath.get_sx,
                            "Y": NodePath.get_sy, "Z": NodePath.get_sz}
            self._value_getters = {"translate": pos_getters,
                                   "rotate": hpr_getters, "scale": scal_getters}

    def update_center(self):

        if not self._objs:
            return

        if self._obj_level != "top":
            self._center.set_pos(self.world, sum([obj.get_center_pos(self.world)
                                                  for obj in self._objs], Point3()) / len(self._objs))
            return

        self._center.set_pos(self.world, sum([obj.get_pivot().get_pos(self.world)
                                              for obj in self._objs], Point3()) / len(self._objs))

    def get_center_pos(self):

        return self._center.get_pos(self.world)

    def update_ui(self, force=False):

        cs_type = Mgr.get_global("coord_sys_type")
        tc_type = Mgr.get_global("transf_center_type")

        if self._obj_level == "top":

            cs_obj = Mgr.get("coord_sys_obj")
            tc_obj = Mgr.get("transf_center_obj")

            if cs_type == "local":

                if cs_obj not in self._objs:
                    Mgr.update_app("coord_sys", cs_type)

                if tc_type == "cs_origin":
                    if tc_obj not in self._objs:
                        Mgr.update_app("transf_center", tc_type)

            if tc_type == "local_origin":
                if tc_obj not in self._objs:
                    Mgr.update_app("transf_center", tc_type)

        count = len(self._objs)

        if count == 1:
            obj = self._objs[0]

        if count:

            if self._obj_level == "top":
                if tc_type == "sel_center":
                    Mgr.do("set_transf_gizmo_pos", self._center.get_pos())
                elif tc_type == "local_origin":
                    Mgr.do("set_transf_gizmo_pos", Mgr.get("transf_center_pos"))
            elif tc_type in ("sel_center", "local_origin"):
                Mgr.do("set_transf_gizmo_pos", self._center.get_pos())

        if self._obj_level == "top":

            transform_values = obj.get_transform_values() if count == 1 else None
            Mgr.update_remotely("transform_values", transform_values)

        obj_ids = set(obj.get_id() for obj in self._objs)
        prev_obj_ids = Mgr.get("sel_obj_ids")
        prev_obj_lvl = Mgr.get_global("active_obj_level")

        if not force and obj_ids == prev_obj_ids and self._obj_level == prev_obj_lvl:
            return

        if self._obj_level == "top":

            if count:
                label = obj.get_name() if count == 1 else "%s Objects selected" % count
                Mgr.update_remotely("selected_obj_name", label)

            sel_colors = set([obj.get_color() for obj in self._objs if obj.has_color()])
            sel_color_count = len(sel_colors)

            if sel_color_count == 1:
                color = sel_colors.pop()
                color_values = [x for x in color][:3]
                Mgr.update_remotely("selected_obj_color", color_values)

            Mgr.set_global("sel_color_count", sel_color_count)
            Mgr.update_app("sel_color_count")

            type_checker = lambda obj, base_type: \
                obj.get_geom_type() if base_type == "model" else base_type
            obj_types = set([type_checker(obj, obj.get_type()) for obj in self._objs])
            obj_type = obj_types.pop() if len(obj_types) == 1 else ""
            Mgr.update_app("selected_obj_type", obj_type)

            if count == 1:
                for prop_id in obj.get_type_property_ids():
                    value = obj.get_property(prop_id, for_remote_update=True)
                    Mgr.update_remotely("selected_obj_prop", obj_type, prop_id, value)

        if self._obj_level != prev_obj_lvl:
            return

        Mgr.do("update_sel_obj_ids")

        prev_count = Mgr.get_global("selection_count")

        if count != prev_count:
            Mgr.do("%s_transf_gizmo" % ("show" if count else "hide"))
            Mgr.set_global("selection_count", count)

        if self._obj_level == "top":
            Mgr.update_app("selection_count")

    def set_transform_component(self, transf_type, axis, value, is_rel_value):

        value_setter = self._value_setters[transf_type][axis]
        val = max(10e-008, value) if transf_type == "scale" else value
        cs_type = Mgr.get_global("coord_sys_type")
        grid_origin = None if cs_type == "local" else Mgr.get( ("grid", "origin") )

        if is_rel_value:

            value_getter = self._value_getters[transf_type][axis]

            for obj in self._objs:
                pivot = obj.get_pivot()
                ref_node = pivot if grid_origin is None else grid_origin
                old_value = value_getter(pivot, ref_node)
                new_value = old_value * val if transf_type == "scale" else old_value + val
                value_setter(pivot, ref_node, new_value)

        else:

            for obj in self._objs:
                pivot = obj.get_pivot()
                ref_node = pivot if grid_origin is None else grid_origin
                value_setter(pivot, ref_node, val)

        if transf_type == "translate":

            self.update_center()

            tc_type = Mgr.get_global("transf_center_type")
            tc_obj = Mgr.get("transf_center_obj")
            affects_gizmo = not ((tc_type == "object" and tc_obj not in self._objs)
                                 or (tc_type == "cs_origin" and cs_type != "local"))

            if affects_gizmo:
                gizmo_pos = tc_obj.get_pivot().get_pos() \
                    if tc_obj in self._objs else self.get_center_pos()
                Mgr.do("set_transf_gizmo_pos", gizmo_pos)

        if Mgr.get("coord_sys_obj") in self._objs:
            Mgr.do("notify_coord_sys_transformed")
            Mgr.do("update_coord_sys")

        if len(self._objs) == 1:
            Mgr.update_remotely("transform_values", self._objs[0].get_transform_values())

        self.__add_history(transf_type)

    def init_translation(self):

        grid_origin = Mgr.get(("grid", "origin"))
        obj_lvl = self._obj_level

        if obj_lvl != "top":

            self._pivot_used = True
            self._pivot_start = Mgr.get("transf_center_pos")
            self._pivot.set_pos(self._pivot_start)
            self._pivot_start = grid_origin.get_relative_point(self.world, self._pivot_start)
            self._center.wrt_reparent_to(self._pivot)

            for obj in Mgr.get("selection", "top"):

                geom_data_obj = obj.get_geom_object().get_geom_data_object()
                geom_data_obj.init_transform()

            return

        cs_obj = Mgr.get("coord_sys_obj")

        if cs_obj in self._objs:
            Mgr.do("notify_coord_sys_transformed")

        if Mgr.get_global("coord_sys_type") == "local":

            self._start_mats = [obj.get_pivot().get_mat(grid_origin)
                                for obj in self._objs]

        else:

            self._pivot_used = True
            self._pivot_start = Mgr.get("transf_center_pos")
            self._pivot.set_pos(self._pivot_start)
            self._pivot_start = grid_origin.get_relative_point(self.world, self._pivot_start)
            self._center.wrt_reparent_to(self._pivot)

            for obj in self._objs:
                obj.get_pivot().wrt_reparent_to(self._pivot)

        for obj in self._objs:
            Mgr.do("update_obj_transf_info", obj.get_id(), ["translate"])

    def translate(self, translation_vec):

        grid_origin = Mgr.get(("grid", "origin"))
        cs_type = Mgr.get_global("coord_sys_type")
        tc_type = Mgr.get_global("transf_center_type")

        obj_lvl = self._obj_level

        if obj_lvl != "top":

            for obj in Mgr.get("selection", "top"):
                geom_data_obj = obj.get_geom_object().get_geom_data_object()
                geom_data_obj.transform_selection(obj_lvl, "translate", translation_vec)

            pos = self._pivot_start + translation_vec
            self._pivot.set_pos(grid_origin, pos)
            pos = Mgr.get("transf_center_pos")
            Mgr.do("set_transf_gizmo_pos", pos)

            return

        if cs_type == "local":

            cs_obj = Mgr.get("coord_sys_obj")
            vec_local = cs_obj.get_pivot().get_relative_vector(grid_origin, translation_vec)

            for obj, start_mat in zip(self._objs, self._start_mats):
                obj.get_pivot().set_pos(grid_origin, start_mat.xform_point(vec_local))

            if tc_type == "sel_center":
                self.update_center()

        else:

            pos = self._pivot_start + translation_vec
            self._pivot.set_pos(grid_origin, pos)

        pos = Mgr.get("transf_center_pos")

        if tc_type == "cs_origin" or (tc_type == "object"
                                      and Mgr.get("transf_center_obj") not in self._objs):
            pos += self.world.get_relative_vector(grid_origin, translation_vec)

        Mgr.do("set_transf_gizmo_pos", pos)

        if Mgr.get_global("object_links_shown"):
            Mgr.do("update_obj_link_viz")

    def init_rotation(self):

        grid_origin = Mgr.get(("grid", "origin"))
        obj_lvl = self._obj_level

        cs_type = Mgr.get_global("coord_sys_type")
        tc_type = Mgr.get_global("transf_center_type")
        tc_pos = Mgr.get("transf_center_pos")
        cs_obj = Mgr.get("coord_sys_obj")

        if obj_lvl != "top":

            self._pivot_used = True
            self._pivot.set_pos(tc_pos)
            self._pivot_start = self._pivot.get_quat(grid_origin)
            self._center.wrt_reparent_to(self._pivot)

            for obj in Mgr.get("selection", "top"):

                geom_data_obj = obj.get_geom_object().get_geom_data_object()
                geom_data_obj.init_transform()

            return

        if cs_obj in self._objs:
            Mgr.do("notify_coord_sys_transformed")

        if tc_type == "local_origin":

            if cs_type == "local":
                self._start_mats = [obj.get_pivot().get_mat(grid_origin) for obj in self._objs]
            else:
                self._start_quats = [obj.get_pivot().get_quat(grid_origin) for obj in self._objs]

        elif cs_type == "local":

            self._start_mats = [obj.get_pivot().get_mat(grid_origin) for obj in self._objs]

            if tc_type != "cs_origin":
                self._offset_vecs = [Point3() - obj.get_pivot().get_relative_point(self.world, tc_pos)
                                     for obj in self._objs]

        else:

            self._pivot_used = True
            self._pivot.set_pos(tc_pos)
            self._pivot_start = self._pivot.get_quat(grid_origin)
            self._center.wrt_reparent_to(self._pivot)

            for obj in self._objs:
                obj.get_pivot().wrt_reparent_to(self._pivot)

        for obj in self._objs:
            Mgr.do("update_obj_transf_info", obj.get_id(), ["rotate"])

    def rotate(self, rotation):

        grid_origin = Mgr.get(("grid", "origin"))
        cs_type = Mgr.get_global("coord_sys_type")
        tc_type = Mgr.get_global("transf_center_type")

        obj_lvl = self._obj_level

        if obj_lvl != "top":

            for obj in Mgr.get("selection", "top"):
                geom_data_obj = obj.get_geom_object().get_geom_data_object()
                geom_data_obj.transform_selection(obj_lvl, "rotate", rotation)

            quat = self._pivot_start * rotation
            self._pivot.set_quat(grid_origin, quat)

            return

        if tc_type == "local_origin":

            if cs_type == "local":
                for obj, start_mat in zip(self._objs, self._start_mats):
                    mat = rotation * start_mat
                    obj.get_pivot().set_mat(grid_origin, mat)
            else:
                for obj, start_quat in zip(self._objs, self._start_quats):
                    quat = start_quat * rotation
                    obj.get_pivot().set_quat(grid_origin, quat)

        elif cs_type == "local":

            tc_pos = Mgr.get("transf_center_pos")

            if tc_type == "cs_origin":
                for obj, start_mat in zip(self._objs, self._start_mats):
                    mat = rotation * start_mat
                    obj.get_pivot().set_mat(grid_origin, mat)
            else:
                for obj, start_mat, start_vec in zip(self._objs, self._start_mats, self._offset_vecs):
                    pivot = obj.get_pivot()
                    mat = rotation * start_mat
                    pivot.set_mat(grid_origin, mat)
                    vec = self.world.get_relative_vector(
                        grid_origin, start_mat.xform_vec(rotation.xform(start_vec)))
                    pivot.set_pos(tc_pos + vec)

        else:

            quat = self._pivot_start * rotation
            self._pivot.set_quat(grid_origin, quat)

        if Mgr.get_global("object_links_shown"):
            Mgr.do("update_obj_link_viz")

    def init_scaling(self):

        grid_origin = Mgr.get(("grid", "origin"))
        obj_lvl = self._obj_level

        tc_type = Mgr.get_global("transf_center_type")
        tc_pos = Mgr.get("transf_center_pos")
        cs_type = Mgr.get_global("coord_sys_type")
        cs_obj = Mgr.get("coord_sys_obj")

        if obj_lvl != "top":

            self._pivot_used = True
            self._pivot.set_hpr(grid_origin.get_hpr())
            self._pivot.set_pos(tc_pos)
            self._center.wrt_reparent_to(self._pivot)

            for obj in Mgr.get("selection", "top"):

                geom_data_obj = obj.get_geom_object().get_geom_data_object()
                geom_data_obj.init_transform()

            return

        if cs_obj in self._objs:
            Mgr.do("notify_coord_sys_transformed")

        if tc_type == "local_origin":

            self._start_mats = [obj.get_pivot().get_mat(grid_origin)
                                for obj in self._objs]

            if cs_type != "local":
                self._start_positions = [obj.get_pivot().get_pos() for obj in self._objs]

        elif cs_type == "local":

            self._start_mats = [obj.get_pivot().get_mat(grid_origin)
                                for obj in self._objs]

            if tc_type != "cs_origin":
                self._offset_vecs = [Point3() - obj.get_pivot().get_relative_point(self.world, tc_pos)
                                     for obj in self._objs]

        else:

            self._pivot_used = True
            self._pivot.set_hpr(grid_origin.get_hpr())
            self._pivot.set_pos(tc_pos)
            self._center.wrt_reparent_to(self._pivot)

            for obj in self._objs:
                obj.get_pivot().wrt_reparent_to(self._pivot)

        for obj in self._objs:
            Mgr.do("update_obj_transf_info", obj.get_id(), ["scale"])

    def scale(self, scaling):

        scal_mat = Mat4.scale_mat(scaling)
        grid_origin = Mgr.get(("grid", "origin"))
        cs_type = Mgr.get_global("coord_sys_type")
        tc_type = Mgr.get_global("transf_center_type")

        obj_lvl = self._obj_level

        if obj_lvl != "top":

            for obj in Mgr.get("selection", "top"):
                geom_data_obj = obj.get_geom_object().get_geom_data_object()
                geom_data_obj.transform_selection(obj_lvl, "scale", scaling)

            self._pivot.set_scale(scaling)

            return

        if tc_type == "local_origin":

            for obj, start_mat in zip(self._objs, self._start_mats):
                mat = (scal_mat * start_mat) if cs_type == "local" else (start_mat * scal_mat)
                obj.get_pivot().set_mat(grid_origin, mat)

            if cs_type != "local":
                for obj, start_pos in zip(self._objs, self._start_positions):
                    obj.get_pivot().set_pos(start_pos)

        elif cs_type == "local":

            if tc_type == "cs_origin":

                for obj, start_mat in zip(self._objs, self._start_mats):
                    mat = scal_mat * start_mat
                    obj.get_pivot().set_mat(grid_origin, mat)

            else:

                tc_pos = Mgr.get("transf_center_pos")

                for obj, start_mat, start_vec in zip(self._objs, self._start_mats, self._offset_vecs):
                    pivot = obj.get_pivot()
                    mat = scal_mat * start_mat
                    pivot.set_mat(grid_origin, mat)
                    vec = self.world.get_relative_vector(pivot, start_vec)
                    pivot.set_pos(tc_pos + vec)

        else:

            self._pivot.set_scale(scaling)

        if Mgr.get_global("object_links_shown"):
            Mgr.do("update_obj_link_viz")

    def finalize_transform(self, cancelled=False):

        obj_lvl = self._obj_level

        if obj_lvl != "top":

            transf_type = Mgr.get_global("active_transform_type")

            if self._pivot_used:

                self._center.wrt_reparent_to(self._obj_root)
                self._center.set_hpr_scale(0., 0., 0., 1., 1., 1.)
                self._center.set_shear(0., 0., 0.)
                self._pivot.clear_transform()

                self._pivot_used = False
                self._pivot_start = None

            for obj in Mgr.get("selection", "top"):

                geom_data_obj = obj.get_geom_object().get_geom_data_object()
                geom_data_obj.finalize_transform(cancelled)

            if transf_type == "translate":
                self.update_center()

            if not cancelled:
                self.__add_history(transf_type)

            return

        Mgr.do("update_coord_sys")
        transf_type = Mgr.get_global("active_transform_type")
        cs_type = Mgr.get_global("coord_sys_type")
        cs_obj = Mgr.get("coord_sys_obj")
        tc_type = Mgr.get_global("transf_center_type")
        tc_obj = Mgr.get("transf_center_obj")

        if transf_type == "translate":

            if tc_type == "cs_origin":
                if cs_type == "world":
                    Mgr.do("set_transf_gizmo_pos", Point3())
                elif cs_type == "object" and cs_obj not in self._objs:
                    Mgr.do("set_transf_gizmo_pos", cs_obj.get_pivot().get_pos())
            elif tc_type == "object" and tc_obj not in self._objs:
                Mgr.do("set_transf_gizmo_pos", tc_obj.get_pivot().get_pos())

            self.update_center()

        if self._pivot_used:

            self._center.wrt_reparent_to(self._obj_root)
            self._center.set_hpr_scale(0., 0., 0., 1., 1., 1.)
            self._center.set_shear(0., 0., 0.)

            for obj in self._objs:
                obj.get_pivot().wrt_reparent_to(obj.get_parent_pivot())

            self._pivot.clear_transform()

        elif cs_type == "local" and tc_type == "sel_center":

            Mgr.do("set_transf_gizmo_pos", self.get_center_pos())

        self._pivot_used = False
        self._pivot_start = None
        self._start_positions = []
        self._start_quats = []
        self._start_mats = []
        self._offset_vecs = []

        if len(self._objs) == 1:
            Mgr.update_remotely("transform_values", self._objs[0].get_transform_values())

        if not cancelled:
            self.__add_history(transf_type)

        Mgr.do("update_obj_link_viz")
        Mgr.do("reset_obj_transf_info")

    def __add_history(self, transf_type):

        obj_data = {}
        event_data = {"objects": obj_data}
        Mgr.do("update_history_time")

        if self._obj_level == "top":

            sel = self._objs
            obj_count = len(sel)

            if obj_count > 1:

                event_descr = '%s %d objects:\n' % (transf_type.title(), obj_count)

                for obj in sel:
                    event_descr += '\n    "%s"' % obj.get_name()

            else:

                event_descr = '%s "%s"' % (transf_type.title(), sel[0].get_name())

            for obj in sel:
                obj_data[obj.get_id()] = {"transform": {"main": obj.get_pivot().get_mat()}}

        else:

            if self._obj_level == "vert":
                subobj_descr = "vertices"
            elif self._obj_level == "edge":
                subobj_descr = "edges"
            elif self._obj_level == "poly":
                subobj_descr = "polygons"

            event_descr = '%s %s' % (transf_type.title(), subobj_descr)
            sel = Mgr.get("selection", "top")

            for obj in sel:
                geom_data_obj = obj.get_geom_object().get_geom_data_object()
                obj_data[obj.get_id()] = geom_data_obj.get_data_to_store(
                    "prop_change", "subobj_transform")

        # make undo/redoable
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def cancel_transform(self):

        Mgr.do("notify_coord_sys_transformed", False)

        grid_origin = Mgr.get(("grid", "origin"))
        active_transform_type = Mgr.get_global("active_transform_type")
        cs_type = Mgr.get_global("coord_sys_type")
        tc_type = Mgr.get_global("transf_center_type")

        if self._pivot_used:

            if active_transform_type == "translate":
                self._pivot.set_pos(grid_origin, self._pivot_start)
            elif active_transform_type == "rotate":
                self._pivot.set_quat(grid_origin, self._pivot_start)
            elif active_transform_type == "scale":
                self._pivot.set_scale(1.)

        else:

            if active_transform_type == "translate":

                for obj, start_mat in zip(self._objs, self._start_mats):
                    obj.get_pivot().set_mat(grid_origin, start_mat)

                self.update_center()

            elif active_transform_type == "rotate":

                if tc_type == "local_origin":

                    if cs_type == "local":
                        for obj, start_mat in zip(self._objs, self._start_mats):
                            obj.get_pivot().set_mat(grid_origin, start_mat)
                    else:
                        for obj, start_quat in zip(self._objs, self._start_quats):
                            obj.get_pivot().set_quat(grid_origin, start_quat)

                elif cs_type == "local":

                    for obj, start_mat in zip(self._objs, self._start_mats):
                        obj.get_pivot().set_mat(grid_origin, start_mat)

            elif active_transform_type == "scale":

                if tc_type == "local_origin" or cs_type == "local":

                    for obj, start_mat in zip(self._objs, self._start_mats):
                        obj.get_pivot().set_mat(grid_origin, start_mat)

        pos = Mgr.get("transf_center_pos")
        Mgr.do("set_transf_gizmo_pos", pos)

        self.finalize_transform(cancelled=True)


class TransformationManager(BaseObject):

    def __init__(self):

        Mgr.set_global("active_transform_type", "")

        for transf_type, axes in (("translate", "XY"), ("rotate", "Z"), ("scale", "XYZ")):
            Mgr.set_global("axis_constraints_%s" % transf_type, axes)
            Mgr.set_global("using_rel_%s_values" % transf_type, False)

        self._obj_transf_info = {}

        self._selection = None
        self._transf_start_pos = Point3()

        self._transf_plane = Plane(V3D(0., 1., 0.), Point3())
        self._transf_plane_normal = V3D()
        self._transf_axis = None
        self._rot_origin = Point3()
        self._rot_start_vec = V3D()
        self._screen_axis_vec = V3D()

        Mgr.expose("obj_transf_info", lambda: self._obj_transf_info)
        Mgr.accept("update_obj_transf_info", self.__update_obj_transf_info)
        Mgr.accept("reset_obj_transf_info", self.__reset_obj_transf_info)
        Mgr.accept("init_transform", self.__init_transform)
        Mgr.add_app_updater("transf_component", self.__set_transform_component)

    def setup(self):

        sort = PendingTasks.get_sort("object_removal", "object")

        if sort is None:
            return False

        PendingTasks.add_task_id("obj_transf_info_reset", "object", sort + 1)

        add_state = Mgr.add_state
        add_state("transforming", -1)

        def end_transform(cancel=False):

            Mgr.exit_state("transforming")
            self.__end_transform(cancel)

        bind = Mgr.bind_state
        bind("transforming", "cancel transform",
             "mouse3-up", lambda: end_transform(cancel=True))
        bind("transforming", "finalize transform", "mouse1-up", end_transform)

        return True

    def __update_obj_transf_info(self, obj_id, transform_types=None):

        obj_transf_info = self._obj_transf_info

        if transform_types is None:
            if obj_id in obj_transf_info:
                del obj_transf_info[obj_id]
            return

        obj_transf_info.setdefault(obj_id, set()).update(transform_types)

    def __reset_obj_transf_info(self):

        def reset():

            self._obj_transf_info = {}

        task = reset
        task_id = "obj_transf_info_reset"
        PendingTasks.add(task, task_id, "object")

    def __set_transform_component(self, transf_type, axis, value, is_rel_value):

        selection = Mgr.get("selection")
        selection.set_transform_component(transf_type, axis, value, is_rel_value)

    def __init_transform(self, transf_start_pos):

        active_transform_type = Mgr.get_global("active_transform_type")

        if not active_transform_type:
            return

        Mgr.enter_state("transforming")

        self._selection = Mgr.get("selection")
        self._transf_start_pos = transf_start_pos

        if active_transform_type == "translate":
            self.__init_translation()
        elif active_transform_type == "rotate":
            if Mgr.get_global("axis_constraints_rotate") == "trackball":
                self.__init_free_rotation()
            else:
                self.__init_rotation()
        if active_transform_type == "scale":
            self.__init_scaling()

        Mgr.update_app("status", "select", active_transform_type, "in_progress")

    def __end_transform(self, cancel=False):

        Mgr.remove_task("transform_selection")
        active_transform_type = Mgr.get_global("active_transform_type")

        if active_transform_type == "rotate":
            Mgr.do("reset_rotation_gizmo_angle")
        elif active_transform_type == "scale":
            Mgr.do("set_gizmo_scale", 1., 1., 1.)
            Mgr.do("hide_scale_indicator")

        if cancel:
            self._selection.cancel_transform()
        else:
            self._selection.finalize_transform()

        if active_transform_type == "rotate" \
                and Mgr.get_global("axis_constraints_rotate") == "trackball":
            prev_constraints = Mgr.get_global("prev_axis_constraints_rotate")
            Mgr.update_app("axis_constraints", "rotate", prev_constraints)

        self._selection = None

    def __init_translation(self):

        axis_constraints = Mgr.get_global("axis_constraints_translate")
        grid_origin = Mgr.get(("grid", "origin"))

        if axis_constraints == "screen":
            normal = V3D(grid_origin.get_relative_vector(self.cam, Vec3(0., 1., 0.)))
            self._transf_axis = None
        elif len(axis_constraints) == 1:
            normal = None
            axis = Vec3()
            axis["XYZ".index(axis_constraints)] = 1.
            self._transf_axis = axis
        else:
            normal = V3D()
            normal["XYZ".index(filter(lambda a: a not in axis_constraints, "XYZ"))] = 1.
            self._transf_axis = None

        if normal is None:

            cam_forward_vec = grid_origin.get_relative_vector(self.cam, Vec3(0., 1., 0.))
            normal = V3D(cam_forward_vec - cam_forward_vec.project(self._transf_axis))

            # If the plane normal is the null vector, the axis must be parallel to
            # the forward camera direction. In this case, a new normal can be chosen
            # arbitrarily, e.g. a horizontal vector perpendicular to the axis.

            if normal.length_squared() < .0001:

                x, y, z = self._transf_axis

                # if the axis of transformation is nearly vertical, any horizontal
                # vector will qualify as plane normal, e.g. a vector pointing in the
                # positive X-direction; otherwise, the plane normal can be computed
                # as perpendicular to the axis
                normal = V3D(1., 0., 0.) if max(abs(x), abs(y)) < .0001 else V3D(y, -x, 0.)

        pos = grid_origin.get_relative_point(self.world, self._transf_start_pos)
        self._transf_plane = Plane(normal, pos)
        cam_pos = self.cam.get_pos(grid_origin)

        if normal * V3D(self._transf_plane.project(cam_pos) - cam_pos) < .0001:
            normal *= -1.

        self._transf_plane_normal = normal
        self._selection.init_translation()

        Mgr.add_task(self.__translate_selection, "transform_selection", sort=3)

    def __translate_selection(self, task):

        # To translate selected items, the new position is computed as the
        # starting position with a vector added to it. This movement vector points
        # from the initial intersection of the "mouse ray" (line going through the
        # camera and the on-screen mouse position) and the items (or translation
        # gizmo), to the current intersection of the mouse ray and the plane of
        # translation, which passes through that initial intersection point.
        # The normal to this plane of translation is either orthogonal to the axis
        # constraints if there are two (XY, XZ or YZ), or, if there is only one axis
        # constraint, perpendicular to this axis and as close as possible to the
        # direction of the camera. This will yield a plane that faces the camera as
        # much as possible, keeping the resulting drag position as close as possible
        # to the mouse pointer (keeping in mind that the actual movement vector is
        # a projection of the vector in the plane onto the transformation
        # axis).

        grid_origin = Mgr.get(("grid", "origin"))
        screen_pos = self.mouse_watcher.get_mouse()

        far_point_local = Point3()
        self.cam_lens.extrude(screen_pos, Point3(), far_point_local)
        far_point = grid_origin.get_relative_point(self.cam, far_point_local)
        cam_pos = self.cam.get_pos(grid_origin)

        # the selected items should not move if the cursor points away from the
        # plane of translation
        if V3D(far_point - cam_pos) * self._transf_plane_normal < .0001:
            return task.cont

        point = Point3()

        if self._transf_plane.intersects_line(point, cam_pos, far_point):

            pos = grid_origin.get_relative_point(self.world, self._transf_start_pos)
            translation_vec = point - pos

            if self._transf_axis is not None:
                translation_vec = translation_vec.project(self._transf_axis)

            self._selection.translate(translation_vec)

        return task.cont

    def __init_rotation(self):

        grid_origin = Mgr.get(("grid", "origin"))
        axis_constraints = Mgr.get_global("axis_constraints_rotate")

        if axis_constraints == "screen":

            normal = V3D(self.world.get_relative_vector(self.cam, Vec3(0., 1., 0.)))
            self._screen_axis_vec = grid_origin.get_relative_vector(self.cam, Vec3(0., 1., 0.))

            if not self._screen_axis_vec.normalize():
                return

        else:

            axis_index = "XYZ".index(axis_constraints)
            axis1_index = axis_index - 2
            axis2_index = axis_index - 1
            axis1_vec = V3D()
            axis1_vec[axis1_index] = 1.
            axis2_vec = V3D()
            axis2_vec[axis2_index] = 1.
            axis1_vec = V3D(self.world.get_relative_vector(grid_origin, axis1_vec))
            axis2_vec = V3D(self.world.get_relative_vector(grid_origin, axis2_vec))
            normal = axis1_vec ** axis2_vec

            if not normal.normalize():
                return

        self._rot_origin = Mgr.get("transf_center_pos")
        self._transf_plane = Plane(normal, self._rot_origin)

        rot_start_pos = Point3()
        cam_pos = self.cam.get_pos(self.world)

        if not self._transf_plane.intersects_line(rot_start_pos, cam_pos, self._transf_start_pos):
            return

        Mgr.do("init_rotation_gizmo_angle", rot_start_pos)

        rot_start_vec = V3D(rot_start_pos - self._rot_origin)
        self._rot_start_vec = (rot_start_vec, normal ** rot_start_vec)

        if not self._rot_start_vec[0].normalize():
            return

        if normal * V3D(self._transf_plane.project(cam_pos) - cam_pos) < .0001:
            normal *= -1.

        # no rotation can occur if the cursor points away from the plane of
        # rotation
        if V3D(self._transf_start_pos - cam_pos) * normal < .0001:
            return

        self._transf_plane_normal = normal
        self._selection.init_rotation()

        Mgr.add_task(self.__rotate_selection, "transform_selection", sort=3)

    def __rotate_selection(self, task):

        # To rotate selected items, the new orientation is computed as the
        # starting orientation with an angle added to it. This angle is measured
        # in the plane of rotation (whose normal points in the direction of the
        # chosen axis of rotation) between two vectors: the starting vector and the
        # current vector, both originating at the center of transformation.
        # The starting vector points to the initial "mouse ray"-item intersection
        # point, while the current vector points to the current intersection of the
        # mouse ray and the plane of rotation.

        screen_pos = self.mouse_watcher.get_mouse()
        far_point_local = Point3()
        self.cam_lens.extrude(screen_pos, Point3(), far_point_local)
        far_point = self.world.get_relative_point(self.cam, far_point_local)
        cam_pos = self.cam.get_pos(self.world)

        # the selected items should not rotate if the cursor points away from the
        # plane of rotation
        if V3D(far_point - cam_pos) * self._transf_plane_normal < .0001:
            return task.cont

        point = Point3()

        if self._transf_plane.intersects_line(point, cam_pos, far_point):

            rotation_vec = V3D(point - self._rot_origin)

            if not rotation_vec.normalize():
                return task.cont

            angle = self._rot_start_vec[0].angle_deg(rotation_vec)

            if self._rot_start_vec[1] * rotation_vec < 0.:
                angle = 360. - angle

            rotation = Quat()
            axis_constraints = Mgr.get_global("axis_constraints_rotate")

            if axis_constraints == "screen":
                rotation.set_from_axis_angle(angle, self._screen_axis_vec)
            else:
                hpr = VBase3()
                hpr["ZXY".index(axis_constraints)] = angle
                rotation.set_hpr(hpr)

            Mgr.do("set_rotation_gizmo_angle", angle)
            self._selection.rotate(rotation)

        return task.cont

    def __init_free_rotation(self):

        self._selection.init_rotation()

        screen_pos = self.mouse_watcher.get_mouse()
        self._rot_start_vec = Mgr.get("trackball_data", screen_pos)[0]

        Mgr.add_task(self.__freely_rotate_selection,"transform_selection", sort=3)

    def __freely_rotate_selection(self, task):

        # To freely rotate selected items, the new orientation is computed as the
        # starting orientation with an angle added to it. This angle is measured
        # between two vectors: the starting vector and the current vector, both
        # originating at the center of transformation.
        # The starting vector points to the initial "mouse ray"-trackball intersection
        # point, while the current vector points to the current intersection of the
        # mouse ray and the trackball.
        # The axis of rotation points in the direction of the cross product of both
        # vectors.
        # When dragging the mouse outside of the trackball, the distance to its edge
        # is measured in radians and added to the angle.

        grid_origin = Mgr.get(("grid", "origin"))
        screen_pos = self.mouse_watcher.get_mouse()
        angle_vec, radians = Mgr.get("trackball_data", screen_pos)
        axis_vec = self._rot_start_vec ** angle_vec
        axis_vec = grid_origin.get_relative_vector(self.cam, axis_vec)

        if not axis_vec.normalize():
            return task.cont

        angle = self._rot_start_vec.angle_rad(angle_vec) + radians
        rotation = Quat()
        rotation.set_from_axis_angle_rad(angle, axis_vec)
        self._selection.rotate(rotation)

        return task.cont

    def __init_scaling(self):

        normal = self.world.get_relative_vector(self.cam, Vec3(0., 1., 0.))
        point = self.world.get_relative_point(self.cam, Point3(0., 2., 0.))
        self._transf_plane = Plane(normal, point)
        cam_pos = self.cam.get_pos(self.world)
        scaling_origin = Point3()
        start_pos = Point3()

        if not self._transf_plane.intersects_line(start_pos, cam_pos, self._transf_start_pos):
            return

        tc_pos = Mgr.get("transf_center_pos")

        if not self._transf_plane.intersects_line(scaling_origin, cam_pos, tc_pos):
            return

        self._transf_start_pos = start_pos
        self._transf_axis = start_pos - scaling_origin

        if not self._transf_axis.normalize():
            return

        scale_dir_vec = V3D(self.cam.get_relative_vector(self.world,
                                                         scaling_origin - start_pos))
        hpr = scale_dir_vec.get_hpr()
        Mgr.do("show_scale_indicator", start_pos, hpr)
        self._selection.init_scaling()

        Mgr.add_task(self.__scale_selection, "transform_selection", sort=3)

    def __scale_selection(self, task):

        # To scale selected items, the new size is computed as the starting size
        # multiplied by a factor, based on the distance of the mouse to the center
        # of transformation.

        screen_pos = self.mouse_watcher.get_mouse()

        far_point_local = Point3()
        self.cam_lens.extrude(screen_pos, Point3(), far_point_local)
        far_point = self.world.get_relative_point(self.cam, far_point_local)
        cam_pos = self.cam.get_pos(self.world)

        point = Point3()

        if self._transf_plane.intersects_line(point, cam_pos, far_point):

            vec = V3D(point - self._transf_start_pos)
            dot_prod = vec * self._transf_axis

            if dot_prod < 0.:
                dot_prod *= -1.0
                scaling_factor = (1. - dot_prod * .99 / (1. + dot_prod)) ** 2.
            else:
                dot_prod *= 10.
                s = dot_prod * .99 / (1. + dot_prod)
                scaling_factor = (1. + s / (1. - s)) ** 2.

            axis_constraints = Mgr.get_global("axis_constraints_scale")

            if axis_constraints == "XYZ":

                scaling = VBase3(scaling_factor, scaling_factor, scaling_factor)

            else:

                scaling = VBase3(1., 1., 1.)

                for axis in axis_constraints:
                    scaling["XYZ".index(axis)] = scaling_factor

            Mgr.do("set_gizmo_scale", *scaling)
            self._selection.scale(scaling)

        return task.cont


class TransformCenterManager(BaseObject):

    def __init__(self):

        self._tc_obj = None
        self._tc_obj_picked = None
        self._tc_transformed = False

        Mgr.set_global("transf_center_type", "sel_center")

        self._pixel_under_mouse = VBase4()
        Mgr.expose("transf_center_obj", lambda: self._tc_obj)
        Mgr.expose("transf_center_pos", self.__get_transform_center_pos)
        Mgr.add_app_updater("transf_center", self.__set_transform_center)

    def setup(self):

        add_state = Mgr.add_state
        add_state("transf_center_picking_mode", -80,
                  self.__enter_picking_mode, self.__exit_picking_mode)

        def exit_transf_center_picking_mode():

            Mgr.exit_state("transf_center_picking_mode")

        bind = Mgr.bind_state
        bind("transf_center_picking_mode", "pick transf center -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("transf_center_picking_mode",
             "pick transf center", "mouse1", self.__pick)
        bind("transf_center_picking_mode", "exit transf center picking", "escape",
             exit_transf_center_picking_mode)
        bind("transf_center_picking_mode", "cancel transf center picking", "mouse3-up",
             exit_transf_center_picking_mode)

        status_data = Mgr.get_global("status_data")
        mode = "Pick transform center"
        info = "LMB to pick object; RMB to end"
        status_data["pick_transf_center"] = {"mode": mode, "info": info}

        return True

    def __set_transform_center(self, tc_type, obj=None):

        Mgr.set_global("transf_center_type", tc_type)

        self._tc_obj = None

        if tc_type == "local_origin":

            selection = Mgr.get("selection")

            if obj:
                self._tc_obj = obj
            elif selection:
                if Mgr.get_global("active_obj_level") == "top":
                    self._tc_obj = selection[0]

        elif tc_type == "object":

            self._tc_obj = obj

        if tc_type != "object":
            self._tc_obj_picked = None

        tc_pos = self.__get_transform_center_pos()
        Mgr.do("set_transf_gizmo_pos", tc_pos)

    def __get_transform_center_pos(self):

        tc_type = Mgr.get_global("transf_center_type")

        if tc_type == "sel_center":
            pos = Mgr.get("selection").get_center_pos()
        elif tc_type == "cs_origin":
            pos = Mgr.get(("grid", "origin")).get_pos()
        elif tc_type == "object":
            pos = self._tc_obj.get_pivot().get_pos(self.world)
        else:  # tc_type == "local_origin"
            if Mgr.get_global("active_obj_level") == "top":
                if self._tc_obj:
                    pos = self._tc_obj.get_pivot().get_pos(self.world)
                else:
                    pos = Mgr.get("selection").get_center_pos()
            else:
                pos = Mgr.get("selection").get_center_pos()

        return pos

    def __enter_picking_mode(self, prev_state_id, is_active):

        Mgr.add_task(self.__update_cursor, "update_tc_picking_cursor")
        Mgr.update_app("status", "pick_transf_center")

    def __exit_picking_mode(self, next_state_id, is_active):

        if not is_active:

            if not self._tc_obj_picked:
                tc_type_prev = Mgr.get_global("transf_center_type")
                obj = self._tc_obj
                name = obj.get_name() if obj else None
                Mgr.update_locally("transf_center", tc_type_prev, obj)
                Mgr.update_remotely("transf_center", tc_type_prev, name)

            self._tc_obj_picked = None

        self._pixel_under_mouse = VBase4() # force an update of the cursor
                                           # next time self.__update_cursor()
                                           # is called
        Mgr.remove_task("update_tc_picking_cursor")
        Mgr.set_cursor("main")

    def __pick(self):

        obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if obj:
            self._tc_obj_picked = obj
            Mgr.update_locally("transf_center", "object", obj)
            Mgr.update_remotely("transf_center", "object", obj.get_name())

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont


MainObjects.add_class(TransformationManager)
MainObjects.add_class(TransformCenterManager)
