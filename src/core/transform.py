from .base import *


class SelectionTransformBase(BaseObject):

    def __init__(self):

        self._obj_root = Mgr.get("object_root")
        self._pivot = Mgr.get("selection_pivot")

        self._pivot_used = False
        self._start_positions = []
        self._start_quats = []
        self._start_mats = []
        self._offset_vecs = []

        self._center_pos = Point3()

        pos_setters = {"x": NodePath.set_x, "y": NodePath.set_y, "z": NodePath.set_z}
        hpr_setters = {"x": NodePath.set_p, "y": NodePath.set_r, "z": NodePath.set_h}
        scal_setters = {"x": NodePath.set_sx, "y": NodePath.set_sy, "z": NodePath.set_sz}
        self._value_setters = {"translate": pos_setters, "rotate": hpr_setters, "scale": scal_setters}

    def update_center_pos(self):

        if not self._objs:
            return

        self._center_pos = sum([obj.get_center_pos(self.world)
                               for obj in self._objs], Point3()) / len(self._objs)

    def get_center_pos(self):

        return Point3(self._center_pos)

    def update_ui(self):

        cs_type = GlobalData["coord_sys_type"]
        tc_type = GlobalData["transf_center_type"]

        if tc_type == "adaptive":
            adaptive_tc_type = Mgr.get("adaptive_transf_center_type")
        else:
            adaptive_tc_type = ""

        cs_obj = Mgr.get("coord_sys_obj", check_valid=True)
        tc_obj = Mgr.get("transf_center_obj", check_valid=True)

        if cs_type == "local":

            if cs_obj not in self._objs:
                # the object previously used as local coordinate system has been
                # deselected, so it can no longer serve that purpose
                Mgr.update_locally("coord_sys", cs_type)

            if tc_type == "cs_origin" and tc_obj not in self._objs:
                # the object previously used as local coordinate system origin
                # has been deselected, so it can no longer serve that purpose
                Mgr.update_locally("transf_center", tc_type)

        if "pivot" in (tc_type, adaptive_tc_type) and tc_obj not in self._objs:
            # the pivot previously used as transform center belongs to an object
            # that has been deselected, so it can no longer serve that purpose
            Mgr.update_locally("transf_center", tc_type)
        elif adaptive_tc_type == "sel_center" and tc_obj:
            # the pivot previously used as transform center can no longer serve
            # that purpose, since the selection center will now be used
            Mgr.update_locally("transf_center", tc_type)

        count = len(self._objs)

        if count == 1:
            obj = self._objs[0]

        if count:
            if "sel_center" in (tc_type, adaptive_tc_type):
                Mgr.do("set_transf_gizmo_pos", self.get_center_pos())
            elif "pivot" in (tc_type, adaptive_tc_type):
                Mgr.do("set_transf_gizmo_pos", Mgr.get("transf_center_pos"))

        transform_values = obj.get_transform_values() if count == 1 else None
        Mgr.update_remotely("transform_values", transform_values)

        prev_count = GlobalData["selection_count"]

        if count != prev_count:
            Mgr.do("%s_transf_gizmo" % ("show" if count else "hide"))
            GlobalData["selection_count"] = count

    def set_transform_component(self, objs_to_transform, transf_type, axis, value, is_rel_value):

        if is_rel_value:

            if transf_type == "translate":
                self.init_translation()
                vec = Vec3()
                vec["xyz".index(axis)] = value
                self.translate(vec)
            elif transf_type == "rotate":
                self.init_rotation()
                rotation = Quat()
                hpr = VBase3()
                hpr["zxy".index(axis)] = value
                rotation.set_hpr(hpr)
                self.rotate(rotation)
            elif transf_type == "scale":
                self.init_scaling()
                scaling = VBase3(1., 1., 1.)
                scaling["xyz".index(axis)] = max(10e-008, value)
                self.scale(scaling)

        else:

            val = max(10e-008, value) if transf_type == "scale" else value
            target_type = GlobalData["transform_target_type"]
            cs_type = GlobalData["coord_sys_type"]
            grid_origin = None if cs_type == "local" else Mgr.get(("grid", "origin"))
            value_setter = self._value_setters[transf_type][axis]
            objs = objs_to_transform[:]

            while objs:

                for obj in objs:

                    other_objs = objs[:]
                    other_objs.remove(obj)
                    ancestor_found = False

                    for other_obj in other_objs:
                        if other_obj in obj.get_ancestors():
                            ancestor_found = True
                            break

                    if not ancestor_found:
                        node = obj.get_origin() if target_type == "geom" else obj.get_pivot()
                        ref_node = node if grid_origin is None else grid_origin
                        value_setter(node, ref_node, val)
                        objs.remove(obj)

            if target_type != "geom":

                if Mgr.get("coord_sys_obj") in objs_to_transform:
                    Mgr.do("notify_coord_sys_transformed")

                for obj in objs_to_transform:
                    Mgr.do("update_obj_transf_info", obj.get_id(), [transf_type])

                Mgr.do("update_obj_link_viz")
                Mgr.do("reset_obj_transf_info")

    def finalize_transform_component(self, objs_to_transform, transf_type, is_rel_value):

        if is_rel_value:

            self.finalize_transform(objs_to_transform)

        else:

            self.update_center_pos()
            Mgr.do("set_transf_gizmo_pos", Mgr.get("transf_center_pos"))
            target_type = GlobalData["transform_target_type"]

            if target_type != "geom":

                if Mgr.get("coord_sys_obj") in objs_to_transform:
                    Mgr.do("update_coord_sys")

            if len(self._objs) == 1:
                Mgr.update_remotely("transform_values", objs_to_transform[0].get_transform_values())

            for obj in objs_to_transform:

                obj.update_group_bbox()

                if target_type in ("geom", "links", "no_children"):
                    Mgr.do("update_group_bboxes", [obj.get_id()])

            self.__add_history(objs_to_transform, transf_type)

    def update_transform_values(self):

        if len(self._objs) == 1:
            Mgr.update_remotely("transform_values", self._objs[0].get_transform_values())

    def init_translation(self, objs_to_transform):

        target_type = GlobalData["transform_target_type"]
        grid_origin = Mgr.get(("grid", "origin"))
        cs_obj = Mgr.get("coord_sys_obj")

        if cs_obj in objs_to_transform and target_type != "geom":
            Mgr.do("notify_coord_sys_transformed")

        if GlobalData["coord_sys_type"] == "local":

            if target_type == "geom":
                self._start_mats = [Mat4(obj.get_origin().get_mat())
                                    for obj in objs_to_transform]
            else:
                self._start_mats = [obj.get_pivot().get_mat(grid_origin)
                                    for obj in objs_to_transform]

        else:

            self._pivot_used = True
            self._pivot.set_pos(grid_origin, 0., 0., 0.)

            if target_type == "geom":
                for obj in objs_to_transform:
                    obj.get_origin().wrt_reparent_to(self._pivot)
            else:
                for obj in objs_to_transform:
                    obj.get_pivot().wrt_reparent_to(self._pivot)

        for obj in objs_to_transform:
            Mgr.do("update_obj_transf_info", obj.get_id(), ["translate"])

    def translate(self, objs_to_transform, translation_vec):

        grid_origin = Mgr.get(("grid", "origin"))
        target_type = GlobalData["transform_target_type"]
        cs_type = GlobalData["coord_sys_type"]
        tc_type = GlobalData["transf_center_type"]

        if tc_type == "adaptive":
            adaptive_tc_type = Mgr.get("adaptive_transf_center_type")
        else:
            adaptive_tc_type = ""

        if cs_type == "local":

            cs_obj = Mgr.get("coord_sys_obj")
            vec_local = cs_obj.get_pivot().get_relative_vector(grid_origin, translation_vec)

            if target_type == "geom":
                for obj, start_mat in zip(objs_to_transform, self._start_mats):
                    orig = obj.get_origin()
                    pivot = obj.get_pivot()
                    pivot_mat = pivot.get_mat(grid_origin)
                    mat = start_mat * Mat4.translate_mat(translation_vec) * pivot_mat
                    orig.set_mat(grid_origin, mat)
            else:
                for obj, start_mat in zip(objs_to_transform, self._start_mats):
                    obj.get_pivot().set_pos(grid_origin, start_mat.xform_point(vec_local))

        else:

            self._pivot.set_pos(grid_origin, Point3(translation_vec))

        if GlobalData["object_links_shown"] and target_type != "geom":
            Mgr.do("update_obj_link_viz")

    def init_rotation(self, objs_to_transform):

        target_type = GlobalData["transform_target_type"]
        grid_origin = Mgr.get(("grid", "origin"))
        cs_type = GlobalData["coord_sys_type"]
        tc_type = GlobalData["transf_center_type"]
        tc_pos = Mgr.get("transf_center_pos")
        cs_obj = Mgr.get("coord_sys_obj")

        if tc_type == "adaptive":
            adaptive_tc_type = Mgr.get("adaptive_transf_center_type")
        else:
            adaptive_tc_type = ""

        if cs_obj in objs_to_transform and target_type != "geom":
            Mgr.do("notify_coord_sys_transformed")

        if tc_type == "pivot" or adaptive_tc_type == "pivot":

            if target_type == "geom":
                if cs_type == "local":
                    self._start_mats = [Mat4(obj.get_origin().get_mat())
                                        for obj in objs_to_transform]
                else:
                    self._start_mats = [Mat4(obj.get_origin().get_mat())
                                        for obj in objs_to_transform]
            else:
                if cs_type == "local":
                    self._start_mats = [obj.get_pivot().get_mat(grid_origin)
                                        for obj in objs_to_transform]
                else:
                    self._start_quats = [obj.get_pivot().get_quat(grid_origin)
                                         for obj in objs_to_transform]

        elif cs_type == "local":

            if target_type == "geom":

                self._start_mats = [Mat4(obj.get_origin().get_mat())
                                    for obj in objs_to_transform]

                if tc_type != "cs_origin":
                    self._offset_vecs = [Point3() - obj.get_pivot().get_relative_point(self.world, tc_pos)
                                         for obj in objs_to_transform]

            else:

                self._start_mats = [obj.get_pivot().get_mat(grid_origin)
                                    for obj in objs_to_transform]

                if tc_type != "cs_origin":
                    self._offset_vecs = [Point3() - obj.get_pivot().get_relative_point(self.world, tc_pos)
                                         for obj in objs_to_transform]

        else:

            self._pivot_used = True
            self._pivot.set_pos(tc_pos)
            self._pivot.set_hpr(grid_origin, 0., 0., 0.)

            if target_type == "geom":
                for obj in objs_to_transform:
                    obj.get_origin().wrt_reparent_to(self._pivot)
            else:
                for obj in objs_to_transform:
                    obj.get_pivot().wrt_reparent_to(self._pivot)

        for obj in objs_to_transform:
            Mgr.do("update_obj_transf_info", obj.get_id(), ["rotate"])

    def rotate(self, objs_to_transform, rotation):

        grid_origin = Mgr.get(("grid", "origin"))
        target_type = GlobalData["transform_target_type"]
        cs_type = GlobalData["coord_sys_type"]
        tc_type = GlobalData["transf_center_type"]

        if tc_type == "adaptive":
            adaptive_tc_type = Mgr.get("adaptive_transf_center_type")
        else:
            adaptive_tc_type = ""

        if tc_type == "pivot" or adaptive_tc_type == "pivot":

            if target_type == "geom":
                if cs_type == "local":
                    for obj, start_mat in zip(objs_to_transform, self._start_mats):
                        orig = obj.get_origin()
                        pivot = obj.get_pivot()
                        pivot_mat = pivot.get_mat(grid_origin)
                        mat = start_mat * (rotation * pivot_mat)
                        orig.set_mat(grid_origin, mat)
                else:
                    for obj, start_mat in zip(objs_to_transform, self._start_mats):
                        mat = Mat4()
                        rotation.extract_to_matrix(mat)
                        orig = obj.get_origin()
                        pivot = obj.get_pivot()
                        pivot_mat = pivot.get_mat(grid_origin)
                        pivot_mat.set_row(3, VBase3())
                        mat = start_mat * pivot_mat * mat * Mat4.translate_mat(pivot.get_pos(grid_origin))
                        orig.set_mat(grid_origin, mat)
            else:
                if cs_type == "local":
                    for obj, start_mat in zip(objs_to_transform, self._start_mats):
                        mat = rotation * start_mat
                        obj.get_pivot().set_mat(grid_origin, mat)
                else:
                    for obj, start_quat in zip(objs_to_transform, self._start_quats):
                        quat = start_quat * rotation
                        obj.get_pivot().set_quat(grid_origin, quat)

        elif cs_type == "local":

            tc_pos = Mgr.get("transf_center_pos")

            if target_type == "geom":
                if tc_type == "cs_origin":
                    for obj, start_mat in zip(objs_to_transform, self._start_mats):
                        orig = obj.get_origin()
                        pivot = obj.get_pivot()
                        pivot_mat = pivot.get_mat(grid_origin)
                        mat = start_mat * (rotation * pivot_mat)
                        orig.set_mat(grid_origin, mat)
                else:
                    for obj, start_mat, start_vec in zip(objs_to_transform, self._start_mats,
                                                         self._offset_vecs):
                        orig = obj.get_origin()
                        pivot = obj.get_pivot()
                        pivot_mat = pivot.get_mat(grid_origin)
                        mat = rotation * pivot_mat
                        vec = pivot_mat.xform_vec(rotation.xform(start_vec))
                        mat.set_row(3, grid_origin.get_relative_point(self.world, tc_pos) + vec)
                        mat = start_mat * mat
                        orig.set_mat(grid_origin, mat)
            else:
                if tc_type == "cs_origin":
                    for obj, start_mat in zip(objs_to_transform, self._start_mats):
                        mat = rotation * start_mat
                        obj.get_pivot().set_mat(grid_origin, mat)
                else:
                    for obj, start_mat, start_vec in zip(objs_to_transform, self._start_mats,
                                                         self._offset_vecs):
                        pivot = obj.get_pivot()
                        mat = rotation * start_mat
                        pivot.set_mat(grid_origin, mat)
                        vec = self.world.get_relative_vector(grid_origin,
                            start_mat.xform_vec(rotation.xform(start_vec)))
                        pivot.set_pos(self.world, tc_pos + vec)

        else:

            self._pivot.set_quat(grid_origin, rotation)

        if GlobalData["object_links_shown"] and target_type != "geom":
            Mgr.do("update_obj_link_viz")

    def init_scaling(self, objs_to_transform):

        grid_origin = Mgr.get(("grid", "origin"))
        tc_type = GlobalData["transf_center_type"]
        tc_pos = Mgr.get("transf_center_pos")
        cs_type = GlobalData["coord_sys_type"]
        cs_obj = Mgr.get("coord_sys_obj")

        if tc_type == "adaptive":
            adaptive_tc_type = Mgr.get("adaptive_transf_center_type")
        else:
            adaptive_tc_type = ""

        if cs_obj in objs_to_transform:
            Mgr.do("notify_coord_sys_transformed")

        if tc_type == "pivot" or adaptive_tc_type == "pivot":

            self._start_mats = [obj.get_pivot().get_mat(grid_origin)
                                for obj in objs_to_transform]

            if cs_type != "local":
                self._start_positions = [obj.get_pivot().get_pos()
                                         for obj in objs_to_transform]

        elif cs_type == "local":

            self._start_mats = [obj.get_pivot().get_mat(grid_origin)
                                for obj in objs_to_transform]

            if tc_type != "cs_origin":
                self._offset_vecs = [Point3() - obj.get_pivot().get_relative_point(self.world, tc_pos)
                                     for obj in objs_to_transform]

        else:

            self._pivot_used = True
            self._pivot.set_hpr(grid_origin.get_hpr())
            self._pivot.set_pos(tc_pos)

            for obj in objs_to_transform:
                obj.get_pivot().wrt_reparent_to(self._pivot)

        for obj in objs_to_transform:
            Mgr.do("update_obj_transf_info", obj.get_id(), ["scale"])

    def scale(self, objs_to_transform, scaling):

        scal_mat = Mat4.scale_mat(scaling)
        grid_origin = Mgr.get(("grid", "origin"))
        cs_type = GlobalData["coord_sys_type"]
        tc_type = GlobalData["transf_center_type"]

        if tc_type == "adaptive":
            adaptive_tc_type = Mgr.get("adaptive_transf_center_type")
        else:
            adaptive_tc_type = ""

        if tc_type == "pivot" or adaptive_tc_type == "pivot":

            for obj, start_mat in zip(objs_to_transform, self._start_mats):
                mat = (scal_mat * start_mat) if cs_type == "local" else (start_mat * scal_mat)
                obj.get_pivot().set_mat(grid_origin, mat)

            if cs_type != "local":
                for obj, start_pos in zip(objs_to_transform, self._start_positions):
                    obj.get_pivot().set_pos(start_pos)

        elif cs_type == "local":

            if tc_type == "cs_origin":

                for obj, start_mat in zip(objs_to_transform, self._start_mats):
                    mat = scal_mat * start_mat
                    obj.get_pivot().set_mat(grid_origin, mat)

            else:

                tc_pos = Mgr.get("transf_center_pos")

                for obj, start_mat, start_vec in zip(objs_to_transform, self._start_mats,
                                                     self._offset_vecs):
                    pivot = obj.get_pivot()
                    mat = scal_mat * start_mat
                    pivot.set_mat(grid_origin, mat)
                    vec = self.world.get_relative_vector(pivot, start_vec)
                    pivot.set_pos(self.world, tc_pos + vec)

        else:

            self._pivot.set_scale(scaling)

        if GlobalData["object_links_shown"]:
            Mgr.do("update_obj_link_viz")

    def finalize_transform(self, objs_to_transform, cancelled=False):

        target_type = GlobalData["transform_target_type"]

        if target_type != "geom":
            Mgr.do("update_coord_sys")

        transf_type = GlobalData["active_transform_type"]

        if self._pivot_used:

            if target_type == "geom":
                for obj in objs_to_transform:
                    obj.get_origin().wrt_reparent_to(obj.get_pivot())
            else:
                for obj in objs_to_transform:
                    obj.get_pivot().wrt_reparent_to(obj.get_parent_pivot())

            self._pivot.clear_transform()
            self._pivot_used = False

        self._start_positions = []
        self._start_quats = []
        self._start_mats = []
        self._offset_vecs = []

        if not cancelled:

            self.update_center_pos()
            Mgr.do("set_transf_gizmo_pos", Mgr.get("transf_center_pos"))

            if len(objs_to_transform) == 1:
                Mgr.update_remotely("transform_values", objs_to_transform[0].get_transform_values())

            for obj in objs_to_transform:

                obj.update_group_bbox()

                if target_type in ("geom", "links", "no_children"):
                    Mgr.do("update_group_bboxes", [obj.get_id()])

            self.__add_history(objs_to_transform, transf_type)

        if target_type != "geom":
            Mgr.do("update_obj_link_viz")

        Mgr.do("reset_obj_transf_info")

    def __add_history(self, objs_to_transform, transf_type):

        obj_data = {}
        event_data = {"objects": obj_data}
        Mgr.do("update_history_time")

        obj_count = len(objs_to_transform)
        target_type = GlobalData["transform_target_type"]

        if obj_count > 1:

            if target_type == "all":
                event_descr = '%s %d objects:\n' % (transf_type.title(), obj_count)
            elif target_type == "geom":
                event_descr = "%s %d objects' geometry:\n" % (transf_type.title(), obj_count)
            elif target_type == "pivot":
                event_descr = "%s %d objects' pivots:\n" % (transf_type.title(), obj_count)
            elif target_type == "links":
                event_descr = "%s %d objects' hierarchy links:\n" % (transf_type.title(), obj_count)
            elif target_type == "no_children":
                event_descr = '%s %d objects without children:\n' % (transf_type.title(), obj_count)

            for obj in objs_to_transform:
                event_descr += '\n    "%s"' % obj.get_name()

        else:

            if target_type == "all":
                event_descr = '%s "%s"' % (transf_type.title(), objs_to_transform[0].get_name())
            elif target_type == "geom":
                event_descr = '%s "%s" geometry' % (transf_type.title(), objs_to_transform[0].get_name())
            elif target_type == "pivot":
                event_descr = '%s "%s" pivot' % (transf_type.title(), objs_to_transform[0].get_name())
            elif target_type == "links":
                event_descr = '%s "%s" hierarchy links' % (transf_type.title(), objs_to_transform[0].get_name())
            elif target_type == "no_children":
                event_descr = '%s "%s" without children' % (transf_type.title(), objs_to_transform[0].get_name())

        if target_type == "all":

            for obj in objs_to_transform:
                obj_data[obj.get_id()] = obj.get_data_to_store("prop_change", "transform")

        elif target_type == "geom":

            for obj in objs_to_transform:
                obj_data[obj.get_id()] = obj.get_data_to_store("prop_change", "origin_transform")

        else:

            objs = set(objs_to_transform)

            for obj in objs_to_transform:
                objs.update(obj.get_descendants() if target_type == "links"
                            else obj.get_children())

            for obj in objs:
                obj_data[obj.get_id()] = data = {}
                data.update(obj.get_data_to_store("prop_change", "transform"))

            if target_type != "links":
                for obj in objs_to_transform:
                    data = obj_data[obj.get_id()]
                    data.update(obj.get_data_to_store("prop_change", "origin_transform"))

        if target_type == "pivot":
            for obj in objs_to_transform:
                if obj.get_type() == "group":
                    for member in obj.get_members():
                        data = member.get_data_to_store("prop_change", "transform")
                        obj_data.setdefault(member.get_id(), {}).update(data)

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def cancel_transform(self, objs_to_transform):

        Mgr.do("notify_coord_sys_transformed", False)

        grid_origin = Mgr.get(("grid", "origin"))
        active_transform_type = GlobalData["active_transform_type"]
        target_type = GlobalData["transform_target_type"]
        cs_type = GlobalData["coord_sys_type"]
        tc_type = GlobalData["transf_center_type"]

        if tc_type == "adaptive":
            adaptive_tc_type = Mgr.get("adaptive_transf_center_type")
        else:
            adaptive_tc_type = ""

        if self._pivot_used:

            if active_transform_type == "translate":
                self._pivot.set_pos(grid_origin, 0., 0., 0.)
            elif active_transform_type == "rotate":
                self._pivot.set_hpr(grid_origin, 0., 0., 0.)
            elif active_transform_type == "scale":
                self._pivot.set_scale(1.)

        else:

            if active_transform_type == "translate":

                if target_type == "geom":
                    for obj, start_mat in zip(objs_to_transform, self._start_mats):
                        obj.get_origin().set_mat(start_mat)
                else:
                    for obj, start_mat in zip(objs_to_transform, self._start_mats):
                        obj.get_pivot().set_mat(grid_origin, start_mat)

            elif active_transform_type == "rotate":

                if tc_type == "pivot" or adaptive_tc_type == "pivot":

                    if target_type == "geom":
                        for obj, start_mat in zip(objs_to_transform, self._start_mats):
                            obj.get_origin().set_mat(start_mat)
                    else:
                        if cs_type == "local":
                            for obj, start_mat in zip(objs_to_transform, self._start_mats):
                                obj.get_pivot().set_mat(grid_origin, start_mat)
                        else:
                            for obj, start_quat in zip(objs_to_transform, self._start_quats):
                                obj.get_pivot().set_quat(grid_origin, start_quat)

                elif cs_type == "local":

                    if target_type == "geom":
                        for obj, start_mat in zip(objs_to_transform, self._start_mats):
                            obj.get_origin().set_mat(start_mat)
                    else:
                        for obj, start_mat in zip(objs_to_transform, self._start_mats):
                            obj.get_pivot().set_mat(grid_origin, start_mat)

            elif active_transform_type == "scale":

                if (tc_type == "pivot" or adaptive_tc_type == "pivot") or cs_type == "local":
                    for obj, start_mat in zip(objs_to_transform, self._start_mats):
                        obj.get_pivot().set_mat(grid_origin, start_mat)

        self.finalize_transform(objs_to_transform, cancelled=True)


class TransformationManager(BaseObject):

    def __init__(self):

        GlobalData.set_default("active_transform_type", "")
        axis_constraints = {"translate": "xy", "rotate": "z", "scale": "xyz"}
        copier = dict.copy
        GlobalData.set_default("axis_constraints", axis_constraints, copier)
        rel_values = {}

        for obj_lvl in ("top",):
            rel_values[obj_lvl] = {"translate": False, "rotate": False, "scale": False}

        for obj_lvl in ("vert", "edge", "poly"):
            rel_values[obj_lvl] = {"translate": True, "rotate": True, "scale": True}

        copier = lambda data: dict((key, value.copy()) for key, value in data.iteritems())
        GlobalData.set_default("rel_transform_values", rel_values, copier)

        self._obj_transf_info = {}
        self._objs_to_transform = []
        self._transforms_to_restore = {"pivot": {}, "origin": {}}

        self._tmp_pivot_mats = {}
        self._tmp_ref_root = None

        self._selection = None
        self._transf_start_pos = Point3()

        self._transf_plane = Plane(V3D(0., 1., 0.), Point3())
        self._transf_plane_normal = V3D()
        self._transf_axis = None
        self._rot_origin = Point3()
        self._rot_start_vec = V3D()
        self._screen_axis_vec = V3D()

        Mgr.expose("obj_transf_info", lambda: self._obj_transf_info)
        Mgr.accept("reset_transf_to_restore", self.__reset_transforms_to_restore)
        Mgr.accept("add_transf_to_restore", self.__add_transform_to_restore)
        Mgr.accept("restore_transforms", self.__restore_transforms)
        Mgr.accept("update_obj_transf_info", self.__update_obj_transf_info)
        Mgr.accept("reset_obj_transf_info", self.__reset_obj_transf_info)
        Mgr.accept("init_transform", self.__init_transform)
        Mgr.add_app_updater("transf_component", self.__set_transform_component)

    def setup(self):

        sort = PendingTasks.get_sort("object_removal", "object")

        if sort is None:
            return False

        PendingTasks.add_task_id("pivot_transform", "object", sort + 1)
        PendingTasks.add_task_id("origin_transform", "object", sort + 2)
        PendingTasks.add_task_id("obj_transf_info_reset", "object", sort + 3)

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

    def __reset_transforms_to_restore(self):

        self._transforms_to_restore = {"pivot": {}, "origin": {}}

    def __add_transform_to_restore(self, transf_target, obj, restore_task):

        self._transforms_to_restore[transf_target][obj] = restore_task

    def __restore_transforms(self):

        def restore():

            transforms_to_restore = self._transforms_to_restore["pivot"]
            objs_to_process = transforms_to_restore.keys()

            while objs_to_process:

                for obj in objs_to_process[:]:

                    other_objs = objs_to_process[:]
                    other_objs.remove(obj)
                    ancestor_found = False

                    for other_obj in other_objs:
                        if other_obj in obj.get_ancestors():
                            ancestor_found = True
                            break

                    if not ancestor_found:
                        transforms_to_restore[obj]()
                        objs_to_process.remove(obj)

            transforms_to_restore.clear()

        PendingTasks.add(restore, "pivot_transform", "object")

        def restore():

            transforms_to_restore = self._transforms_to_restore["origin"]
            objs_to_process = transforms_to_restore.keys()

            while objs_to_process:

                for obj in objs_to_process[:]:

                    other_objs = objs_to_process[:]
                    other_objs.remove(obj)
                    ancestor_found = False

                    for other_obj in other_objs:
                        if other_obj in obj.get_ancestors():
                            ancestor_found = True
                            break

                    if not ancestor_found:
                        transforms_to_restore[obj]()
                        objs_to_process.remove(obj)

            transforms_to_restore.clear()

        PendingTasks.add(restore, "origin_transform", "object")

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

    def __init_link_transform(self):

        obj_root = Mgr.get("object_root")
        self._tmp_ref_root = ref_root = obj_root.attach_new_node("tmp_ref_nodes")
        ref_root.node().set_bounds(OmniBoundingVolume())
        ref_root.node().set_final(True)
        objs = set(self._objs_to_transform)
        compass_props = CompassEffect.P_rot | CompassEffect.P_scale

        for obj in self._objs_to_transform:
            objs.update(obj.get_descendants(include_group_members=False))

        for obj in objs:

            pivot = obj.get_pivot()
            ref_node = ref_root.attach_new_node("ref_node")
            ref_node.set_mat(pivot.get_mat(obj_root))
            self._tmp_pivot_mats[obj] = Mat4(pivot.get_mat(obj_root))

            if obj.get_type() == "group":
                for member in obj.get_members():
                    member.get_pivot().wrt_reparent_to(obj.get_origin())

            if obj.get_type() != "point_helper":
                compass_effect = CompassEffect.make(ref_node, compass_props)
                origin = obj.get_origin()
                origin.set_effect(compass_effect)

    def __finalize_link_transform(self, cancel=False):

        obj_root = Mgr.get("object_root")
        tmp_pivot_mats = self._tmp_pivot_mats
        positions = {}

        for obj in tmp_pivot_mats:

            if obj.get_type() != "point_helper":
                origin = obj.get_origin()
                origin.clear_effect(CompassEffect.get_class_type())

            if obj.get_type() == "group":
                for member in obj.get_members():
                    member.get_pivot().wrt_reparent_to(obj.get_pivot())

            pivot = obj.get_pivot()
            positions[obj] = pivot.get_pos(obj_root)

        if not cancel:

            objs_to_process = tmp_pivot_mats.keys()

            while objs_to_process:

                for obj in objs_to_process[:]:

                    other_objs = objs_to_process[:]
                    other_objs.remove(obj)
                    ancestor_found = False

                    for other_obj in other_objs:
                        if other_obj in obj.get_ancestors():
                            ancestor_found = True
                            break

                    if not ancestor_found:
                        pivot = obj.get_pivot()
                        pivot.set_mat(obj_root, tmp_pivot_mats[obj])
                        pivot.set_pos(obj_root, positions[obj])
                        objs_to_process.remove(obj)

        positions.clear()

    def __cleanup_link_transform(self, cancel=False):

        tmp_pivot_mats = self._tmp_pivot_mats

        if not cancel:
            Mgr.do("update_obj_link_viz", [obj.get_id() for obj in tmp_pivot_mats])

        tmp_pivot_mats.clear()
        self._tmp_ref_root.remove_node()
        self._tmp_ref_root = None

    def __set_transform_component(self, transf_type, axis, value, is_rel_value):

        active_obj_lvl = GlobalData["active_obj_level"]
        target_type = GlobalData["transform_target_type"]
        selection = Mgr.get("selection")

        if target_type in ("geom", "pivot") and transf_type == "scale":
            return

        if active_obj_lvl == "top":

            if target_type == "links":
                objs_to_transform = [obj for obj in selection if obj.get_children()]
            else:
                objs_to_transform = selection[:]

            if not objs_to_transform:
                return

            self._objs_to_transform = objs_to_transform
            Mgr.do("update_xform_target_type", objs_to_transform)

            if target_type in ("all", "links"):

                obj_root = Mgr.get("object_root")

                for obj in objs_to_transform:
                    obj.get_pivot().wrt_reparent_to(obj_root)

            if target_type == "links":
                self.__init_link_transform()

            selection.set_transform_component(objs_to_transform, transf_type, axis,
                                              value, is_rel_value)

        else:

            process = selection.set_transform_component(transf_type, axis, value, is_rel_value)

            if process.next():
                descr = "Finalizing transformation..."
                Mgr.do_gradually(process, "subobj_transformation", descr)

        if active_obj_lvl == "top":

            if target_type == "links":
                self.__finalize_link_transform()

            if target_type in ("all", "links"):
                for obj in objs_to_transform:
                    obj.get_pivot().wrt_reparent_to(obj.get_parent_pivot())

            if target_type == "links":
                self.__cleanup_link_transform()

            selection.finalize_transform_component(objs_to_transform, transf_type, is_rel_value)
            Mgr.do("init_point_helper_transform")
            Mgr.do("transform_point_helpers")
            Mgr.do("finalize_point_helper_transform")
            Mgr.do("update_xform_target_type", objs_to_transform, reset=True)

        self._objs_to_transform = []

    def __init_transform(self, transf_start_pos):

        active_transform_type = GlobalData["active_transform_type"]
        active_obj_level = GlobalData["active_obj_level"]
        target_type = GlobalData["transform_target_type"]
        selection = Mgr.get("selection")

        if not active_transform_type:
            return

        if target_type in ("geom", "pivot") and active_transform_type == "scale":
            return

        if active_obj_level == "top":

            if target_type == "links":
                objs_to_transform = [obj for obj in selection if obj.get_children()]
            else:
                objs_to_transform = selection[:]

            if not objs_to_transform:
                return

            self._objs_to_transform = objs_to_transform

        Mgr.enter_state("transforming")
        Mgr.do("enable_view_tiles", False)

        self._selection = selection
        self._transf_start_pos = transf_start_pos

        if active_obj_level == "top":

            Mgr.do("update_xform_target_type", objs_to_transform)
            Mgr.do("init_point_helper_transform")

            if target_type in ("all", "links"):

                obj_root = Mgr.get("object_root")

                for obj in objs_to_transform:
                    obj.get_pivot().wrt_reparent_to(obj_root)

            if target_type == "links":
                self.__init_link_transform()

        if active_transform_type == "translate":
            self.__init_translation()
        elif active_transform_type == "rotate":
            if GlobalData["axis_constraints"]["rotate"] == "trackball":
                self.__init_free_rotation()
            else:
                self.__init_rotation()
        if active_transform_type == "scale":
            self.__init_scaling()

        Mgr.update_app("status", "select", active_transform_type, "in_progress")

    def __end_transform(self, cancel=False):

        Mgr.remove_task("transform_selection")
        Mgr.do("enable_view_tiles")
        active_obj_lvl = GlobalData["active_obj_level"]
        active_transform_type = GlobalData["active_transform_type"]

        if active_transform_type == "rotate":
            Mgr.do("reset_rotation_gizmo_angle")
        elif active_transform_type == "scale":
            Mgr.do("hide_scale_indicator")

        if active_obj_lvl == "top":

            target_type = GlobalData["transform_target_type"]

            if target_type == "links":
                self.__finalize_link_transform(cancel)

        if cancel:
            if active_obj_lvl == "top":
                self._selection.cancel_transform(self._objs_to_transform)
            else:
                self._selection.cancel_transform()
        else:
            if active_obj_lvl == "top":
                self._selection.finalize_transform(self._objs_to_transform)
            else:
                process = self._selection.finalize_transform()
                if process.next():
                    descr = "Finalizing transformation..."
                    Mgr.do_gradually(process, "subobj_transformation", descr)

        if active_obj_lvl == "top":

            if target_type in ("all", "links"):
                for obj in self._objs_to_transform:
                    obj.get_pivot().wrt_reparent_to(obj.get_parent_pivot())

            if target_type == "links":
                self.__cleanup_link_transform(cancel)

            Mgr.do("finalize_point_helper_transform", cancel)
            Mgr.do("update_xform_target_type", self._objs_to_transform, reset=True)
            self._objs_to_transform = []

        if active_transform_type == "rotate" \
                and GlobalData["axis_constraints"]["rotate"] == "trackball":
            prev_constraints = GlobalData["prev_axis_constraints_rotate"]
            Mgr.update_app("axis_constraints", "rotate", prev_constraints)

        self._selection = None

    def __init_translation(self):

        axis_constraints = GlobalData["axis_constraints"]["translate"]
        grid_origin = Mgr.get(("grid", "origin"))
        cam = self.cam()
        lens_type = self.cam.lens_type

        if axis_constraints == "screen":
            normal = V3D(grid_origin.get_relative_vector(cam, Vec3.forward()))
            self._transf_axis = None
        elif len(axis_constraints) == 1:
            normal = None
            axis = Vec3()
            axis["xyz".index(axis_constraints)] = 1.
            self._transf_axis = axis
        else:
            normal = V3D()
            normal["xyz".index(filter(lambda a: a not in axis_constraints, "xyz"))] = 1.
            self._transf_axis = None

        if normal is None:

            cam_forward_vec = grid_origin.get_relative_vector(cam, Vec3.forward())
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

        if lens_type == "persp":

            cam_pos = cam.get_pos(grid_origin)

            if normal * V3D(self._transf_plane.project(cam_pos) - cam_pos) < .0001:
                normal *= -1.

        self._transf_plane_normal = normal

        if GlobalData["active_obj_level"] == "top":
            self._selection.init_translation(self._objs_to_transform)
        else:
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
        cam = self.cam()
        lens_type = self.cam.lens_type

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: grid_origin.get_relative_point(cam, point)
        near_point = rel_pt(near_point)
        far_point = rel_pt(far_point)

        if lens_type == "persp":
            # the selected items should not move if the cursor points away from the
            # plane of translation
            if V3D(far_point - near_point) * self._transf_plane_normal < .0001:
                return task.cont

        point = Point3()

        if self._transf_plane.intersects_line(point, near_point, far_point):

            pos = grid_origin.get_relative_point(self.world, self._transf_start_pos)
            translation_vec = point - pos

            if self._transf_axis is not None:
                translation_vec = translation_vec.project(self._transf_axis)

            if GlobalData["active_obj_level"] == "top":
                self._selection.translate(self._objs_to_transform, translation_vec)
            else:
                self._selection.translate(translation_vec)

            Mgr.do("transform_point_helpers")

        return task.cont

    def __init_rotation(self):

        grid_origin = Mgr.get(("grid", "origin"))
        axis_constraints = GlobalData["axis_constraints"]["rotate"]
        cam = self.cam()
        lens_type = self.cam.lens_type

        if axis_constraints == "screen":

            normal = V3D(self.world.get_relative_vector(cam, Vec3.forward()))
            self._screen_axis_vec = grid_origin.get_relative_vector(cam, Vec3.forward())

            if not self._screen_axis_vec.normalize():
                return

        else:

            axis_index = "xyz".index(axis_constraints)
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

        if lens_type == "persp":
            line_start = cam.get_pos(self.world)
        else:
            line_start = cam.get_relative_point(self.world, self._transf_start_pos)
            line_start.y -= 100.
            line_start = self.world.get_relative_point(cam, line_start)

        if not self._transf_plane.intersects_line(rot_start_pos, line_start, self._transf_start_pos):
            return

        Mgr.do("init_rotation_gizmo_angle", rot_start_pos)

        rot_start_vec = V3D(rot_start_pos - self._rot_origin)
        self._rot_start_vec = (rot_start_vec, normal ** rot_start_vec)

        if not self._rot_start_vec[0].normalize():
            return

        if lens_type == "persp":

            if normal * V3D(self._transf_plane.project(line_start) - line_start) < .0001:
                normal *= -1.

            # no rotation can occur if the cursor points away from the plane of
            # rotation
            if V3D(self._transf_start_pos - line_start) * normal < .0001:
                return

        self._transf_plane_normal = normal

        if GlobalData["active_obj_level"] == "top":
            self._selection.init_rotation(self._objs_to_transform)
        else:
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

        cam = self.cam()
        lens_type = self.cam.lens_type
        screen_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)
        near_point = rel_pt(near_point)
        far_point = rel_pt(far_point)

        if lens_type == "persp":
            # the selected items should not rotate if the cursor points away from the
            # plane of rotation
            if V3D(far_point - near_point) * self._transf_plane_normal < .0001:
                return task.cont

        point = Point3()

        if self._transf_plane.intersects_line(point, near_point, far_point):

            rotation_vec = V3D(point - self._rot_origin)

            if not rotation_vec.normalize():
                return task.cont

            angle = self._rot_start_vec[0].angle_deg(rotation_vec)

            if self._rot_start_vec[1] * rotation_vec < 0.:
                angle = 360. - angle

            rotation = Quat()
            axis_constraints = GlobalData["axis_constraints"]["rotate"]

            if axis_constraints == "screen":
                rotation.set_from_axis_angle(angle, self._screen_axis_vec)
            else:
                hpr = VBase3()
                hpr["zxy".index(axis_constraints)] = angle
                rotation.set_hpr(hpr)

            Mgr.do("set_rotation_gizmo_angle", angle)

            if GlobalData["active_obj_level"] == "top":
                self._selection.rotate(self._objs_to_transform, rotation)
            else:
                self._selection.rotate(rotation)

            Mgr.do("transform_point_helpers")

        return task.cont

    def __init_free_rotation(self):

        if GlobalData["active_obj_level"] == "top":
            self._selection.init_rotation(self._objs_to_transform)
        else:
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
        axis_vec = grid_origin.get_relative_vector(self.cam(), axis_vec)

        if not axis_vec.normalize():
            return task.cont

        angle = self._rot_start_vec.angle_rad(angle_vec) + radians
        rotation = Quat()
        rotation.set_from_axis_angle_rad(angle, axis_vec)

        if GlobalData["active_obj_level"] == "top":
            self._selection.rotate(self._objs_to_transform, rotation)
        else:
            self._selection.rotate(rotation)

        Mgr.do("transform_point_helpers")

        return task.cont

    def __init_scaling(self):

        cam = self.cam()
        lens_type = self.cam.lens_type
        normal = self.world.get_relative_vector(cam, Vec3.forward())
        point = self.world.get_relative_point(cam, Point3(0., 2., 0.))
        self._transf_plane = Plane(normal, point)
        tc_pos = Mgr.get("transf_center_pos")

        if lens_type == "persp":
            line_start1 = line_start2 = cam.get_pos(self.world)
        else:
            line_start = cam.get_relative_point(self.world, self._transf_start_pos)
            line_start.y -= 100.
            line_start1 = self.world.get_relative_point(cam, line_start)
            line_start = cam.get_relative_point(self.world, tc_pos)
            line_start.y -= 100.
            line_start2 = self.world.get_relative_point(cam, line_start)

        start_pos = Point3()

        if not self._transf_plane.intersects_line(start_pos, line_start1, self._transf_start_pos):
            return

        scaling_origin = Point3()

        if not self._transf_plane.intersects_line(scaling_origin, line_start2, tc_pos):
            return

        self._transf_start_pos = start_pos
        self._transf_axis = start_pos - scaling_origin

        if not self._transf_axis.normalize():
            return

        if lens_type == "ortho":
            self._transf_axis *= .005 / self.cam.zoom

        scale_dir_vec = V3D(cam.get_relative_vector(self.world, scaling_origin - start_pos))
        hpr = scale_dir_vec.get_hpr()
        Mgr.do("show_scale_indicator", start_pos, hpr)

        if GlobalData["active_obj_level"] == "top":
            self._selection.init_scaling(self._objs_to_transform)
        else:
            self._selection.init_scaling()

        Mgr.add_task(self.__scale_selection, "transform_selection", sort=3)

    def __scale_selection(self, task):

        # To scale selected items, the new size is computed as the starting size
        # multiplied by a factor, based on the distance of the mouse to the center
        # of transformation.

        cam = self.cam()
        screen_pos = self.mouse_watcher.get_mouse()

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)

        point = Point3()

        if self._transf_plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point)):

            vec = V3D(point - self._transf_start_pos)
            dot_prod = vec * self._transf_axis

            if dot_prod < 0.:
                dot_prod *= -1.0
                scaling_factor = (1. - dot_prod * .99 / (1. + dot_prod)) ** 2.
            else:
                dot_prod *= 10.
                s = dot_prod * .99 / (1. + dot_prod)
                scaling_factor = (1. + s / (1. - s)) ** 2.

            axis_constraints = GlobalData["axis_constraints"]["scale"]

            if axis_constraints == "xyz":

                scaling = VBase3(scaling_factor, scaling_factor, scaling_factor)

            else:

                scaling = VBase3(1., 1., 1.)

                for axis in axis_constraints:
                    scaling["xyz".index(axis)] = scaling_factor

            if GlobalData["active_obj_level"] == "top":
                self._selection.scale(self._objs_to_transform, scaling)
            else:
                self._selection.scale(scaling)

            Mgr.do("transform_point_helpers")

        return task.cont


MainObjects.add_class(TransformationManager)
