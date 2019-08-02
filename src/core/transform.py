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
            Mgr.do("{}_transf_gizmo".format("show" if count else "hide"))
            GlobalData["selection_count"] = count

    def set_transform_component(self, objs_to_transform, transf_type, axis, value, is_rel_value,
                                rel_to_world=False, transformer=None, state="done"):

        if is_rel_value:

            if transf_type == "translate":
                self.init_translation(objs_to_transform)
                vec = Vec3()
                vec["xyz".index(axis)] = value
                self.translate(objs_to_transform, vec)
            elif transf_type == "rotate":
                self.init_rotation(objs_to_transform)
                rotation = Quat()
                hpr = VBase3()
                hpr["zxy".index(axis)] = value
                rotation.set_hpr(hpr)
                self.rotate(objs_to_transform, rotation)
            elif transf_type == "scale":
                self.init_scaling(objs_to_transform)
                scaling = VBase3(1., 1., 1.)
                value = max(10e-008, abs(value)) * (-1. if value < 0. else 1.)
                scaling["xyz".index(axis)] = value
                self.scale(objs_to_transform, scaling)

        else:

            if transf_type == "scale":
                value = max(10e-008, abs(value)) * (-1. if value < 0. else 1.)

            target_type = GlobalData["transform_target_type"]
            cs_type = GlobalData["coord_sys_type"]
            grid_origin = None if cs_type == "local" else Mgr.get(("grid", "origin"))
            value_setter = transformer if transformer else self._value_setters[transf_type][axis]
            objs = objs_to_transform[:]
            tc_type = GlobalData["transf_center_type"]
            use_transf_center = not (transf_type == "translate" or tc_type == "pivot"
                                or (cs_type == "local" and tc_type == "cs_origin"))

            if use_transf_center:
                self._pivot.set_pos(Mgr.get("transf_center_pos"))

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
                        ref_node = self.world if rel_to_world else (node if grid_origin is None else grid_origin)
                        if use_transf_center:
                            quat = node.get_quat(self.world)
                            scale = node.get_scale(self.world)
                            self._pivot.set_quat_scale(quat, scale)
                            parent_node = node.get_parent()
                            node.wrt_reparent_to(self._pivot)
                            value_setter(self._pivot, ref_node, value)
                            node.wrt_reparent_to(parent_node)
                        else:
                            value_setter(node, ref_node, value)
                        objs.remove(obj)

            if use_transf_center:
                self._pivot.clear_transform()

            if target_type != "geom":

                if Mgr.get("coord_sys_obj") in objs_to_transform:
                    Mgr.do("notify_coord_sys_transformed")

                for obj in objs_to_transform:
                    Mgr.do("update_obj_transf_info", obj.get_id(), [transf_type])

                Mgr.do("update_obj_link_viz")
                Mgr.do("reset_obj_transf_info")

    def finalize_transform_component(self, objs_to_transform, transf_type, is_rel_value,
                                     add_to_hist=True, state="done"):

        if is_rel_value:

            self.finalize_transform(objs_to_transform, add_to_hist=add_to_hist, state=state)

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

            if add_to_hist:
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

    def finalize_transform(self, objs_to_transform, cancelled=False, add_to_hist=True,
                           state="done"):

        target_type = GlobalData["transform_target_type"]

        if target_type != "geom" and state != "continuous":
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

        if not cancelled and state != "continuous":

            self.update_center_pos()
            Mgr.do("set_transf_gizmo_pos", Mgr.get("transf_center_pos"))

            if len(objs_to_transform) == 1:
                Mgr.update_remotely("transform_values", objs_to_transform[0].get_transform_values())

            for obj in objs_to_transform:

                obj.update_group_bbox()

                if target_type in ("geom", "links", "no_children"):
                    Mgr.do("update_group_bboxes", [obj.get_id()])

            if add_to_hist:
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
                event_descr = '{} {:d} objects:\n'.format(transf_type.title(), obj_count)
            elif target_type == "geom":
                event_descr = "{} {:d} objects' geometry:\n".format(transf_type.title(), obj_count)
            elif target_type == "pivot":
                event_descr = "{} {:d} objects' pivots:\n".format(transf_type.title(), obj_count)
            elif target_type == "links":
                event_descr = "{} {:d} objects' hierarchy links:\n".format(transf_type.title(), obj_count)
            elif target_type == "no_children":
                event_descr = '{} {:d} objects without children:\n'.format(transf_type.title(), obj_count)

            for obj in objs_to_transform:
                event_descr += '\n    "{}"'.format(obj.get_name())

        else:

            if target_type == "all":
                event_descr = '{} "{}"'.format(transf_type.title(), objs_to_transform[0].get_name())
            elif target_type == "geom":
                event_descr = '{} "{}" geometry'.format(transf_type.title(), objs_to_transform[0].get_name())
            elif target_type == "pivot":
                event_descr = '{} "{}" pivot'.format(transf_type.title(), objs_to_transform[0].get_name())
            elif target_type == "links":
                event_descr = '{} "{}" hierarchy links'.format(transf_type.title(), objs_to_transform[0].get_name())
            elif target_type == "no_children":
                event_descr = '{} "{}" without children'.format(transf_type.title(), objs_to_transform[0].get_name())

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

        for obj_lvl in ("vert", "edge", "poly", "normal"):
            rel_values[obj_lvl] = {"translate": True, "rotate": True, "scale": True}

        copier = lambda data: dict((key, value.copy()) for key, value in data.items())
        GlobalData.set_default("rel_transform_values", rel_values, copier)
        options = {}
        options["rotation"] = {
            "drag_method": "circular_in_rot_plane",
            "alt_method": "circular_in_view_plane",
            "method_switch_threshold": 20.,
            "show_circle": True,
            "circle_center": "start_click_pos",
            "circle_radius": 100,
            "scale_circle_to_cursor": True,
            "show_line": True,
            "line_thru_gizmo_center": False,
            "full_roll_dist": 400
        }
        GlobalData.set_default("transform_options", options, copier)

        self._obj_transf_info = {}
        self._objs_to_transform = []
        self._transforms_to_restore = {"pivot": {}, "origin": {}}

        self._tmp_pivot_mats = {}
        self._tmp_ref_root = None

        self._selection = None
        self._transf_start_pos = Point3()
        self._xform_backup = {}

        self._transf_plane = Plane(V3D(0., 1., 0.), Point3())
        self._transf_plane_normal = V3D()
        self._transf_axis = None
        self._rot_origin = Point3()
        self._rot_start_vec = V3D()
        self._rot_start_vecs = ()
        self._total_angle = None
        self._rotation_viz = {}

        for shape_type in ("circular", "linear"):
            self._rotation_viz[shape_type] = self.__create_rotation_viz(shape_type)

        self._drag_in_view_plane = False
        self._drag_linear = False
        self._snap_start_vecs = V3D()
        self._screen_axis_vec = V3D()
        self._scale_start_pos = Point3()
        self._transf_center_pos = Point3()

        Mgr.expose("obj_transf_info", lambda: self._obj_transf_info)
        Mgr.expose("xform_backup", lambda: self._xform_backup)
        Mgr.expose("sorted_hierarchy", self.__get_sorted_hierarchy)
        Mgr.accept("reset_transf_to_restore", self.__reset_transforms_to_restore)
        Mgr.accept("add_transf_to_restore", self.__add_transform_to_restore)
        Mgr.accept("restore_transforms", self.__restore_transforms)
        Mgr.accept("update_obj_transf_info", self.__update_obj_transf_info)
        Mgr.accept("reset_obj_transf_info", self.__reset_obj_transf_info)
        Mgr.accept("init_transform", self.__init_transform)
        Mgr.accept("cancel_transform_init", self.__cancel_transform_init)
        Mgr.accept("start_transform", self.__start_transform)
        Mgr.accept("create_xform_backup", self.__create_xform_backup)
        Mgr.accept("restore_xform_backup", self.__restore_xform_backup)
        Mgr.add_app_updater("transf_component", self.__set_transform_component)
        Mgr.add_app_updater("componentwise_xform", self.__update_componentwise_xform)

        add_state = Mgr.add_state
        add_state("transforming", -1)

        def end_transform(cancel=False):

            self.__end_transform(cancel)
            Mgr.exit_state("transforming")

        bind = Mgr.bind_state
        bind("transforming", "cancel transform", "mouse3", lambda: end_transform(cancel=True))
        bind("transforming", "abort transform", "focus_loss", lambda: end_transform(cancel=True))
        bind("transforming", "finalize transform", "mouse1-up", end_transform)

    def __create_rotation_viz(self, shape_type):

        from array import array

        coords = array("f", [])
        indices = array("I", [])

        if shape_type == "circular":

            from math import pi, sin, cos

            angle = pi * .02

            coords.extend((1., 0., 0., 0., 0.))

            for i in range(1, 101):
                x = cos(angle * i)
                z = -sin(angle * i)
                coords.extend((x, 0., z, i / 100., 0.))
                indices.extend((i - 1, i))

            indices.extend((i, 0))

        else:

            coords.extend((0., 0., 0., 0., 0.))
            coords.extend((1000000., 0., 0., 1., 0.))
            indices.extend((0, 1))

        vertex_format = GeomVertexFormat.get_v3t2()
        vertex_data = GeomVertexData("selection_shape", vertex_format, Geom.UH_dynamic)
        vertex_data.unclean_set_num_rows(len(coords) // 5)
        pos_array = vertex_data.modify_array(0)
        memview = memoryview(pos_array).cast("B").cast("f")
        memview[:] = coords
        lines = GeomLines(Geom.UH_static)
        lines.set_index_type(Geom.NT_uint32)
        lines_array = lines.modify_vertices()
        lines_array.unclean_set_num_rows(len(indices))
        memview = memoryview(lines_array).cast("B").cast("I")
        memview[:] = indices
        state_np = NodePath("state_np")
        state_np.set_depth_test(False)
        state_np.set_depth_write(False)
        state_np.set_bin("fixed", 101)
        state_np.set_render_mode_thickness(3)
        state1 = state_np.get_state()
        state_np.set_bin("fixed", 100)
        state_np.set_color((0., 0., 0., 1.))
        state_np.set_render_mode_thickness(5)
        state2 = state_np.get_state()
        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        geom_node = GeomNode("rotation_viz")
        geom_node.add_geom(geom, state1)
        geom = geom.make_copy()
        geom_node.add_geom(geom, state2)
        viz = NodePath(geom_node)
        img = PNMImage(1, 1)
        img.fill(1., 1., 1.)
        tex = Texture("tex")
        tex.load(img)
        sampler = SamplerState()
        sampler.set_wrap_u(SamplerState.WM_border_color)
        sampler.set_magfilter(SamplerState.FT_nearest)
        sampler.set_minfilter(SamplerState.FT_nearest)
        tex.set_default_sampler(sampler)
        tex_stage = TextureStage.get_default()
        viz.set_texture(tex_stage, tex)

        return viz

    def __reset_transforms_to_restore(self):

        self._transforms_to_restore = {"pivot": {}, "origin": {}}

    def __add_transform_to_restore(self, transf_target, obj, restore_task):

        self._transforms_to_restore[transf_target][obj] = restore_task

    def __restore_transforms(self):

        def restore():

            transforms_to_restore = self._transforms_to_restore["pivot"]
            objs_to_process = list(transforms_to_restore.keys())

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
            objs_to_process = list(transforms_to_restore.keys())

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

            objs_to_process = list(tmp_pivot_mats.keys())

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

    def __set_transform_component(self, transf_type, axis, value, is_rel_value, objects=None,
                                  add_to_hist=True, rel_to_world=False, transformer=None,
                                  state="done"):

        active_obj_lvl = GlobalData["active_obj_level"]
        target_type = GlobalData["transform_target_type"]
        selection = Mgr.get("selection")

        if target_type in ("geom", "pivot") and transf_type == "scale":
            return

        if active_obj_lvl == "top":

            objs = objects if objects else selection

            if target_type == "links":
                objs_to_transform = [obj for obj in objs if obj.get_children()]
            else:
                objs_to_transform = objs[:]

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
                                              value, is_rel_value, rel_to_world, transformer,
                                              state)

        else:

            selection.set_transform_component(transf_type, axis, value, is_rel_value, add_to_hist)

        if active_obj_lvl == "top":

            if target_type == "links":
                self.__finalize_link_transform()

            if target_type in ("all", "links"):
                for obj in objs_to_transform:
                    obj.get_pivot().wrt_reparent_to(obj.get_parent_pivot())

            if target_type == "links":
                self.__cleanup_link_transform()

            selection.finalize_transform_component(objs_to_transform, transf_type, is_rel_value,
                                                   add_to_hist, state)
            Mgr.do("init_point_helper_transform")
            Mgr.do("transform_point_helpers")
            Mgr.do("finalize_point_helper_transform")
            Mgr.do("update_xform_target_type", objs_to_transform, reset=True)

        self._objs_to_transform = []

    def __get_sorted_hierarchy(self, objects):
        """
        Return a list of objects sorted from ancestors to descendants.
        Do not include open groups.

        """

        sorted_hierarchy = []
        objs = objects[:]

        while objs:

            for obj in objs[:]:

                other_objs = objs[:]
                other_objs.remove(obj)

                for other_obj in other_objs:
                    if other_obj in obj.get_ancestors():
                        break
                else:
                    objs.remove(obj)
                    if obj.get_type() != "group" or not obj.is_open():
                        sorted_hierarchy.append(obj)

        return sorted_hierarchy

    def __create_xform_backup(self):

        backup = self._xform_backup

        if GlobalData["active_obj_level"] == "top":
            if GlobalData["transform_target_type"] == "geom":
                for obj in Mgr.get("selection_top"):
                    backup[obj] = obj.get_origin().get_transform(self.world)
            else:
                for obj in Mgr.get("selection_top"):
                    backup[obj] = obj.get_pivot().get_transform(self.world)
        else:
            backup.update(Mgr.get("selection").get_vertex_position_data())

    def __restore_xform_backup(self, clear=True):

        backup = self._xform_backup

        if not backup:
            return

        if GlobalData["active_obj_level"] == "top":

            tc_type = GlobalData["transf_center_type"]

            if tc_type != "pivot":
                GlobalData["transf_center_type"] = "pivot"

            for obj in self.__get_sorted_hierarchy(Mgr.get("selection_top")):
                self.__set_transform_component("", "",
                    backup[obj], False, [obj], False, True, NodePath.set_transform)

            if tc_type != "pivot":
                GlobalData["transf_center_type"] = tc_type

        else:

            selection = Mgr.get("selection")
            selection.prepare_transform(backup)
            selection.finalize_transform(add_to_hist=False, lock_normals=False)

        if clear:
            backup.clear()

    def __componentwise_xform(self, values, state="done", preview=True, end_preview=False):

        backup = self._xform_backup

        if end_preview:
            self.__restore_xform_backup()
            return

        if preview and not backup:
            self.__create_xform_backup()

        transf_type = GlobalData["active_transform_type"]
        default_val = 1. if transf_type == "scale" else 0.
        xforms = {}

        for axis_id, value in values.items():
            if value != default_val:
                xforms[axis_id] = value

        self.__restore_xform_backup(clear=False)

        if xforms:

            final_xform = xforms.popitem()

            for axis_id, value in xforms.items():
                self.__set_transform_component(transf_type, axis_id, value, is_rel_value=True,
                                               add_to_hist=False, state=state)

            axis_id, value = final_xform
            add_to_hist = not preview
            self.__set_transform_component(transf_type, axis_id, value, is_rel_value=True,
                                           add_to_hist=add_to_hist, state=state)

        if not preview:
            backup.clear()

    def __update_componentwise_xform(self, update_type, *args):

        if update_type == "cancel":
            self.__restore_xform_backup()
        else:
            self.__componentwise_xform(*args)

    def __init_transform(self, transf_start_pos):

        Mgr.get("picking_cam").set_active(False)
        Mgr.get("gizmo_picking_cam").node().set_active(False)
        Mgr.get("gizmo_picking_cam").node().get_display_region(0).set_active(False)
        transform_type = GlobalData["active_transform_type"]
        active_obj_level = GlobalData["active_obj_level"]
        target_type = GlobalData["transform_target_type"]
        selection = Mgr.get("selection")

        if not transform_type:
            return

        if target_type in ("geom", "pivot") and transform_type == "scale":
            return

        if active_obj_level == "top":

            if target_type == "links":
                objs_to_transform = [obj for obj in selection if obj.get_children()]
            else:
                objs_to_transform = selection[:]

            if not objs_to_transform:
                return

            self._objs_to_transform = objs_to_transform

        self._selection = selection

        snap_settings = GlobalData["snap"]

        if transform_type == "rotate" and GlobalData["axis_constraints"]["rotate"] == "trackball":
            snap_on = False
        else:
            snap_on = snap_settings["on"][transform_type]

        snap_src_type = snap_settings["src_type"][transform_type]
        snap_tgt_type = snap_settings["tgt_type"][transform_type]

        if snap_on and snap_tgt_type != "increment" and snap_src_type != "transf_center":
            Mgr.enter_state("transf_start_snap_mode")
        else:
            self.__start_transform(transf_start_pos)

    def __cancel_transform_init(self):

        Mgr.get("picking_cam").set_active()
        Mgr.get("gizmo_picking_cam").node().set_active(True)
        Mgr.get("gizmo_picking_cam").node().get_display_region(0).set_active(True)
        self._objs_to_transform = []
        self._selection = None

    def __start_transform(self, transf_start_pos):

        transform_type = GlobalData["active_transform_type"]
        snap_settings = GlobalData["snap"]

        if transform_type == "rotate" and GlobalData["axis_constraints"]["rotate"] == "trackball":
            snap_on = False
        else:
            snap_on = snap_settings["on"][transform_type]

        snap_src_type = snap_settings["src_type"][transform_type]
        snap_tgt_type = snap_settings["tgt_type"][transform_type]

        if snap_on and snap_src_type == "transf_center":
            snap_pos = Mgr.get("transf_center_pos")
        else:
            snap_pos = None

        self._transf_start_pos = snap_pos if snap_pos else transf_start_pos

        Mgr.enter_state("transforming")

        if snap_on and snap_tgt_type != "increment":
            Mgr.do("init_snap_target_checking", transform_type)

        if GlobalData["active_obj_level"] == "top":

            objs_to_transform = self._objs_to_transform
            target_type = GlobalData["transform_target_type"]

            Mgr.do("update_xform_target_type", objs_to_transform)
            Mgr.do("init_point_helper_transform")

            if target_type in ("all", "links"):

                obj_root = Mgr.get("object_root")

                for obj in objs_to_transform:
                    obj.get_pivot().wrt_reparent_to(obj_root)

            if target_type == "links":
                self.__init_link_transform()

        if transform_type == "translate":
            self.__init_translation()
        elif transform_type == "rotate":
            if GlobalData["axis_constraints"]["rotate"] == "trackball":
                self.__init_free_rotation()
            else:
                self.__init_rotation()
        elif transform_type == "scale":
            self.__init_scaling()

        Mgr.update_app("status", ["select", transform_type, "in_progress"])

    def __end_transform(self, cancel=False):

        Mgr.get("picking_cam").set_active()
        Mgr.get("gizmo_picking_cam").node().set_active(True)
        Mgr.get("gizmo_picking_cam").node().get_display_region(0).set_active(True)
        Mgr.remove_task("transform_selection")
        active_obj_lvl = GlobalData["active_obj_level"]
        transform_type = GlobalData["active_transform_type"]
        snap_settings = GlobalData["snap"]

        if transform_type == "rotate" and GlobalData["axis_constraints"]["rotate"] == "trackball":
            snap_on = False
        else:
            snap_on = snap_settings["on"][transform_type]

        snap_tgt_type = snap_settings["tgt_type"][transform_type]

        if snap_on and snap_tgt_type != "increment":
            Mgr.do("end_snap_target_checking")

        if transform_type == "rotate":
            Mgr.do("reset_rotation_gizmo_angle")
            self._rotation_viz["circular"].detach_node()
            self._rotation_viz["linear"].detach_node()
        elif transform_type == "scale":
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
                self._selection.finalize_transform()

        if active_obj_lvl == "top":

            if target_type in ("all", "links"):
                for obj in self._objs_to_transform:
                    obj.get_pivot().wrt_reparent_to(obj.get_parent_pivot())

            if target_type == "links":
                self.__cleanup_link_transform(cancel)

            Mgr.do("finalize_point_helper_transform", cancel)
            Mgr.do("update_xform_target_type", self._objs_to_transform, reset=True)
            self._objs_to_transform = []

        if transform_type == "rotate" and GlobalData["axis_constraints"]["rotate"] == "trackball":
            prev_constraints = GlobalData["prev_axis_constraints_rotate"]
            Mgr.update_app("axis_constraints", "rotate", prev_constraints)

        self._selection = None

    def __init_translation(self):

        axis_constraints = GlobalData["axis_constraints"]["translate"]
        grid_origin = Mgr.get(("grid", "origin"))
        cam = self.cam()
        lens_type = self.cam.lens_type

        if axis_constraints == "view":
            normal = V3D(grid_origin.get_relative_vector(cam, Vec3.forward()).normalized())
            self._transf_axis = None
        elif len(axis_constraints) == 1:
            normal = None
            axis = Vec3()
            axis["xyz".index(axis_constraints)] = 1.
            self._transf_axis = axis
        else:
            normal = V3D()
            normal["xyz".index("".join(a for a in "xyz" if a not in axis_constraints))] = 1.
            self._transf_axis = None

        if normal is None:

            cam_forward_vec = grid_origin.get_relative_vector(cam, Vec3.forward()).normalized()
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
        # a projection of the vector in the plane onto the transformation axis).

        if not self.mouse_watcher.has_mouse():
            Mgr.do("set_projected_snap_marker_pos", None)
            return task.cont

        grid_origin = Mgr.get(("grid", "origin"))
        translation_vec = None
        snap_settings = GlobalData["snap"]
        snap_on = snap_settings["on"]["translate"]
        snap_tgt_type = snap_settings["tgt_type"]["translate"]
        snap_target_point = None

        if snap_on and snap_tgt_type != "increment":

            snap_target_point = Mgr.get("snap_target_point")

            if snap_target_point:

                if snap_settings["use_axis_constraints"]["translate"]:
                    if self._transf_axis is None:
                        snap_target_point = self._transf_plane.project(snap_target_point)

                pos = grid_origin.get_relative_point(self.world, self._transf_start_pos)
                translation_vec = snap_target_point - pos

        if translation_vec is None:

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
                    Mgr.do("set_projected_snap_marker_pos", None)
                    return task.cont

            point = Point3()

            if self._transf_plane.intersects_line(point, near_point, far_point):
                pos = grid_origin.get_relative_point(self.world, self._transf_start_pos)
                translation_vec = point - pos

        if self._transf_axis is not None:
            if not snap_target_point or snap_settings["use_axis_constraints"]["translate"]:
                translation_vec = translation_vec.project(self._transf_axis)

        if snap_on and snap_tgt_type == "increment":

            axis_constraints = GlobalData["axis_constraints"]["translate"]
            offset_incr = snap_settings["increment"]["translate"]

            if axis_constraints == "view":
                translation_vec = cam.get_relative_vector(grid_origin, translation_vec)
                offset_incr /= cam.get_sx(grid_origin)

            x, y, z = translation_vec
            x = round(x / offset_incr) * offset_incr
            y = round(y / offset_incr) * offset_incr
            z = round(z / offset_incr) * offset_incr
            translation_vec = Vec3(x, y, z)

            if axis_constraints == "view":
                translation_vec = grid_origin.get_relative_vector(cam, translation_vec)

        if snap_on and snap_settings["use_axis_constraints"]["translate"]:
            if snap_target_point:
                pos = self.world.get_relative_point(grid_origin, pos + translation_vec)
                Mgr.do("set_projected_snap_marker_pos", pos)
            else:
                Mgr.do("set_projected_snap_marker_pos", None)

        if GlobalData["active_obj_level"] == "top":
            self._selection.translate(self._objs_to_transform, translation_vec)
        else:
            self._selection.translate(translation_vec)

        Mgr.do("transform_point_helpers")

        return task.cont

    def __init_rotation(self):

        grid_origin = Mgr.get(("grid", "origin"))
        axis_constraints = GlobalData["axis_constraints"]["rotate"]
        rotation_options = GlobalData["transform_options"]["rotation"]
        cam = self.cam()
        lens_type = self.cam.lens_type
        cam_pos = cam.get_pos(self.world)
        cam_vec = V3D(self.world.get_relative_vector(cam, Vec3.forward()).normalized())

        if axis_constraints == "view":

            normal = cam_vec
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

        drag_in_view_plane = False
        drag_linear = rotation_options["drag_method"] == "linear"

        if not drag_linear:

            method_switch_threshold = rotation_options["method_switch_threshold"]
            drag_method = rotation_options["drag_method"]
            drag_in_view_plane = drag_method != "circular_in_rot_plane"
            angle = max(cam_vec.angle_deg(normal), cam_vec.angle_deg(-normal)) - 90.

            if axis_constraints != "view" and angle < method_switch_threshold:
                drag_in_view_plane = True
                drag_linear = rotation_options["alt_method"] == "linear"

        self._drag_in_view_plane = drag_in_view_plane or drag_linear
        self._drag_linear = drag_linear

        snap_settings = GlobalData["snap"]
        snap_on = snap_settings["on"]["rotate"]
        snap_tgt_type = snap_settings["tgt_type"]["rotate"]

        if snap_on and snap_tgt_type != "increment":

            rot_start_pos = self._transf_plane.project(self._transf_start_pos)

        else:

            rot_start_pos = Point3()

            if lens_type == "persp":
                line_start = cam_pos
            else:
                line_start = cam.get_relative_point(self.world, self._transf_start_pos)
                line_start.y -= 1000.
                line_start = self.world.get_relative_point(cam, line_start)

            if not (self._transf_plane.intersects_line(rot_start_pos,
                    line_start, self._transf_start_pos) or self._drag_in_view_plane):
                return

        Mgr.do("init_rotation_gizmo_angle", rot_start_pos)

        rot_start_vec = V3D(rot_start_pos - self._rot_origin)
        rot_ref_vec = normal ** rot_start_vec
        self._rot_start_vecs = (rot_start_vec, rot_ref_vec)

        if not rot_start_vec.normalize():
            return

        if lens_type == "persp":
            if normal * V3D(self._transf_plane.project(cam_pos) - cam_pos) < .0001:
                normal *= -1.

        if (not snap_on or snap_tgt_type == "increment") and (lens_type == "persp"
                and not self._drag_in_view_plane):
            # no rotation can occur if the cursor points away from the plane of
            # rotation
            if V3D(self._transf_start_pos - cam_pos) * normal < .0001:
                return

        if snap_on and snap_tgt_type == "increment":
            self._snap_start_vecs = (V3D(rot_start_vec), V3D(rot_ref_vec))
            self._total_angle = 0.
        else:
            self._total_angle = None

        self._transf_plane_normal = normal

        if GlobalData["active_obj_level"] == "top":
            self._selection.init_rotation(self._objs_to_transform)
        else:
            self._selection.init_rotation()

        if self._drag_in_view_plane:

            w, h = GlobalData["viewport"]["size_aux"
                if GlobalData["viewport"][2] == "main" else "size"]
            point = cam.get_relative_point(self.world, self._rot_origin)
            screen_pos = Point2()
            self.cam.lens.project(point, screen_pos)
            x, y = screen_pos
            x = (x + 1.) * .5 * w
            y = -(1. - (y + 1.) * .5) * h
            center = Point3(x, 0., y)
            point = cam.get_relative_point(self.world, self._transf_start_pos)
            screen_pos = Point2()
            self.cam.lens.project(point, screen_pos)
            x, y = screen_pos
            x = (x + 1.) * .5 * w
            y = -(1. - (y + 1.) * .5) * h
            point = Point3(x, 0., y)
            vec = point - center
            angle = Vec3(1., 0., 0.).signed_angle_deg(vec.normalized(), Vec3(0., 1., 0.))

            if drag_linear:

                viz = self._rotation_viz["linear"]
                viz.set_pos(point)

                if not rotation_options["line_thru_gizmo_center"]:
                    x, y = GlobalData["viewport"]["pos_aux"
                        if GlobalData["viewport"][2] == "main" else "pos"]
                    mouse_pointer = Mgr.get("mouse_pointer", 0)
                    mouse_x = mouse_pointer.get_x()
                    mouse_y = mouse_pointer.get_y()
                    point2 = Point3(mouse_x - x, 0., -mouse_y + y)
                    vec = point2 - point
                    angle = Vec3(1., 0., 0.).signed_angle_deg(vec.normalized(), Vec3(0., 1., 0.))

                viz.set_r(angle)

            else:

                viz = self._rotation_viz["circular"]
                viz.set_r(angle)

                if rotation_options["circle_center"] == "gizmo_center":
                    viz.set_pos(center)
                else:
                    viz.set_pos(point)

                if rotation_options["show_circle"]:
                    if not rotation_options["scale_circle_to_cursor"]:
                        viz.set_scale(rotation_options["circle_radius"])
                    elif rotation_options["circle_center"] == "gizmo_center":
                        viz.set_scale(vec.length())
                    else:
                        viz.set_scale(.1)

            if rotation_options["show_line" if drag_linear else "show_circle"]:

                if axis_constraints == "view":
                    color = (.5, .5, .5, 1.)
                else:
                    color = VBase4()
                    color["xyz".index(axis_constraints)] = 1.

                tex_stage = TextureStage.get_default()
                tex = viz.get_texture(tex_stage)
                sampler = SamplerState(tex.get_default_sampler())
                sampler.set_border_color(color)
                tex.set_default_sampler(sampler)
                viz.reparent_to(self.viewport)

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

        rotation_vec = None
        snap_settings = GlobalData["snap"]
        snap_on = snap_settings["on"]["rotate"]
        snap_tgt_type = snap_settings["tgt_type"]["rotate"]
        snap_target_point = None
        axis_constraints = GlobalData["axis_constraints"]["rotate"]
        rotation_options = GlobalData["transform_options"]["rotation"]
        drag_in_view_plane = self._drag_in_view_plane
        drag_linear = self._drag_linear
        grid_origin = Mgr.get(("grid", "origin"))

        if drag_in_view_plane:
            viz = self._rotation_viz["linear" if drag_linear else "circular"]
            show_viz = rotation_options["show_line" if drag_linear else "show_circle"]
            viz.show() if show_viz else viz.hide()

        if snap_on and snap_tgt_type != "increment":

            snap_target_point = Mgr.get("snap_target_point")

            if snap_target_point:

                snap_target_point = self.world.get_relative_point(grid_origin, snap_target_point)
                pos = self._transf_plane.project(snap_target_point)
                rotation_vec = V3D(pos - self._rot_origin)

                if drag_in_view_plane:
                    viz.hide()

                if not rotation_vec.normalize():
                    Mgr.do("set_projected_snap_marker_pos", None)
                    return task.cont

            if snap_settings["use_axis_constraints"]["rotate"]:
                if snap_target_point:
                    Mgr.do("set_projected_snap_marker_pos", pos)
                else:
                    Mgr.do("set_projected_snap_marker_pos", None)

        if rotation_vec is None:

            if not self.mouse_watcher.has_mouse():
                Mgr.do("set_projected_snap_marker_pos", None)
                return task.cont

            cam = self.cam()
            lens_type = self.cam.lens_type

            if drag_in_view_plane:

                x, y = GlobalData["viewport"]["pos_aux"
                    if GlobalData["viewport"][2] == "main" else "pos"]
                mouse_pointer = Mgr.get("mouse_pointer", 0)
                mouse_x = mouse_pointer.get_x()
                mouse_y = mouse_pointer.get_y()
                point = Point3(mouse_x - x, 0., -mouse_y + y)
                vec = V3D(point - viz.get_pos())

                if show_viz and not drag_linear and rotation_options["scale_circle_to_cursor"]:
                    viz.set_scale(max(1., vec.length()))

                if drag_linear:

                    dir_vec = Vec3(1., 0., 0.) * viz.get_scale()[0]
                    dir_vec = self.viewport.get_relative_vector(viz, dir_vec)
                    full_roll_dist = rotation_options["full_roll_dist"]
                    angle = vec.project(dir_vec).length() * 360. / full_roll_dist

                    if vec * dir_vec < 0.:
                        angle *= -1.
                        angle_offset = angle // 360. + 1.
                        viz.set_scale(-1.)
                        use_angle_complement = True
                    else:
                        angle_offset = angle // 360.
                        viz.set_scale(1.)
                        use_angle_complement = False

                else:

                    angle = Vec3.right().signed_angle_deg(vec.normalized(), Vec3.forward())
                    angle -= viz.get_r()

                    if axis_constraints == "view":

                        use_angle_complement = False

                    else:

                        vec = V3D()
                        vec["xyz".index(axis_constraints)] = 1.

                        if vec * grid_origin.get_relative_vector(self.cam(), Vec3.forward()) < 0.:
                            angle *= -1.
                            use_angle_complement = True
                        else:
                            use_angle_complement = False

                quat = Quat()

                if axis_constraints == "view":
                    quat.set_from_axis_angle(angle, self._screen_axis_vec)
                else:
                    hpr = VBase3()
                    hpr["zxy".index(axis_constraints)] = angle
                    quat.set_hpr(hpr)

                vec = quat.xform(self._rot_start_vecs[0])
                point = self._rot_origin + vec
                near_point = point - self._transf_plane_normal
                far_point = point + self._transf_plane_normal

            else:

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
                    Mgr.do("set_projected_snap_marker_pos", None)
                    return task.cont

            point = Point3()

            if self._transf_plane.intersects_line(point, near_point, far_point):

                rotation_vec = V3D(point - self._rot_origin)

                if not rotation_vec.normalize():
                    Mgr.do("set_projected_snap_marker_pos", None)
                    return task.cont

                if snap_on and snap_tgt_type == "increment":

                    angle_incr = snap_settings["increment"]["rotate"]
                    snap_vec, snap_ref_vec = self._snap_start_vecs
                    a = rotation_vec.angle_deg(snap_vec)

                    if a > angle_incr * .75:

                        n = (1 + a // angle_incr)

                        if rotation_vec * snap_ref_vec < 0.:
                            n *= -1.

                        # rotate both snap_vec and snap_ref_vec about the rotation plane
                        # normal by an angle equal to angle_incr * n
                        angle = angle_incr * n
                        self._total_angle += angle
                        q = Quat()
                        q.set_from_axis_angle(angle, self._transf_plane.get_normal())
                        snap_vec = V3D(q.xform(snap_vec))
                        self._snap_start_vecs = (snap_vec, V3D(q.xform(snap_ref_vec)))

                    rotation_vec = snap_vec

        if rotation_vec is not None:

            angle = self._rot_start_vecs[0].angle_deg(rotation_vec)

            if self._rot_start_vecs[1] * rotation_vec < 0. and angle > .001:
                angle = 360. - angle

            rotation = Quat()

            if axis_constraints == "view":
                rotation.set_from_axis_angle(angle, self._screen_axis_vec)
            else:
                hpr = VBase3()
                hpr["zxy".index(axis_constraints)] = angle
                rotation.set_hpr(hpr)

            if (snap_on and snap_tgt_type != "increment" and snap_target_point
                    and not snap_settings["use_axis_constraints"]["rotate"]):

                snap_target_vec = (snap_target_point - self._rot_origin).normalized()
                start_vec = self._transf_start_pos - self._rot_origin
                start_vec = grid_origin.get_relative_vector(self.world, start_vec)
                start_vec = rotation.xform(start_vec)
                start_vec = self.world.get_relative_vector(grid_origin, start_vec)
                ref_vec = rotation_vec ** self._transf_plane_normal
                pitch = start_vec.normalized().signed_angle_deg(snap_target_vec, ref_vec)
                ref_vec = grid_origin.get_relative_vector(self.world, ref_vec)

                if not ref_vec.normalize():
                    Mgr.do("set_projected_snap_marker_pos", None)
                    return task.cont

                pitch_quat = Quat()
                pitch_quat.set_from_axis_angle(pitch, ref_vec)
                rotation = rotation * pitch_quat

            Mgr.do("set_rotation_gizmo_angle", angle)

            if drag_in_view_plane and not viz.is_hidden():

                if use_angle_complement:
                    angle = 360. - angle

                if drag_linear:
                    scale = 360000000. / (max(.001, angle) * full_roll_dist)
                else:
                    scale = 360./max(.001, angle)

                tex_stage = TextureStage.get_default()
                viz.set_tex_scale(tex_stage, scale, 1.)

                if drag_linear:

                    if self._total_angle is not None:

                        angle_offset = self._total_angle // 360.

                        if use_angle_complement:
                            angle_offset += 1.

                    offset = -(full_roll_dist * angle_offset) / 1000000.
                    viz.set_tex_offset(tex_stage, offset * scale * viz.get_scale()[0], 0.)

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

        if not self.mouse_watcher.has_mouse():
            return task.cont

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
        normal = self.world.get_relative_vector(cam, Vec3.forward()).normalized()
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
            line_start.y -= 1000.
            line_start2 = self.world.get_relative_point(cam, line_start)

        start_pos = Point3()

        if not self._transf_plane.intersects_line(start_pos, line_start1, self._transf_start_pos):
            return

        scaling_origin = Point3()

        if not self._transf_plane.intersects_line(scaling_origin, line_start2, tc_pos):
            return

        self._scale_start_pos = start_pos
        self._transf_axis = start_pos - scaling_origin

        if not self._transf_axis.normalize():
            return

        if lens_type == "ortho":
            self._transf_axis *= .005 / self.cam.zoom

        scale_dir_vec = V3D(cam.get_relative_vector(self.world, scaling_origin - start_pos))
        h, p, _ = scale_dir_vec.get_hpr()
        Mgr.do("show_scale_indicator", start_pos, h, p)

        if GlobalData["active_obj_level"] == "top":
            self._selection.init_scaling(self._objs_to_transform)
        else:
            self._selection.init_scaling()

        snap_settings = GlobalData["snap"]
        snap_on = snap_settings["on"]["scale"]
        snap_tgt_type = snap_settings["tgt_type"]["scale"]

        if snap_on and snap_tgt_type != "increment":
            grid_origin = Mgr.get(("grid", "origin"))
            vec = self._transf_start_pos - tc_pos
            self._scale_start_vec = grid_origin.get_relative_vector(self.world, vec)
            self._transf_start_pos = grid_origin.get_relative_point(self.world, self._transf_start_pos)
            self._transf_center_pos = grid_origin.get_relative_point(self.world, tc_pos)

        Mgr.add_task(self.__scale_selection, "transform_selection", sort=3)

    def __scale_selection(self, task):

        # To scale selected items, the new size is computed as the starting size
        # multiplied by a factor, based on the distance of the mouse to the center
        # of transformation.

        scaling = None
        snap_settings = GlobalData["snap"]
        snap_on = snap_settings["on"]["scale"]
        snap_tgt_type = snap_settings["tgt_type"]["scale"]
        axis_constraints = GlobalData["axis_constraints"]["scale"]

        if snap_on and snap_tgt_type != "increment":

            snap_target_point = Mgr.get("snap_target_point")

            if snap_target_point:

                x1, y1, z1 = self._scale_start_vec
                x2, y2, z2 = snap_target_point - self._transf_center_pos
                x = 1. if x1 == 0. else x2 / x1
                y = 1. if y1 == 0. else y2 / y1
                z = 1. if z1 == 0. else z2 / z1
                x = max(.001, abs(x)) * (-1. if x < 0. else 1.)
                y = max(.001, abs(y)) * (-1. if y < 0. else 1.)
                z = max(.001, abs(z)) * (-1. if z < 0. else 1.)

                if not snap_settings["use_axis_constraints"]["scale"] or axis_constraints == "xyz":

                    scaling = VBase3(x, y, z)

                else:

                    scaling = VBase3(1., 1., 1.)
                    values = (x, y, z)

                    for axis in axis_constraints:
                        index = "xyz".index(axis)
                        scaling[index] = values[index]

            if snap_settings["use_axis_constraints"]["scale"] and axis_constraints != "xyz":
                if snap_target_point:
                    grid_origin = Mgr.get(("grid", "origin"))
                    p = self._transf_start_pos - self._transf_center_pos
                    point = Point3(*[a * b for a, b in zip(p, scaling)])
                    point = point + self._transf_center_pos
                    pos = self.world.get_relative_point(grid_origin, point)
                    Mgr.do("set_projected_snap_marker_pos", pos)
                else:
                    Mgr.do("set_projected_snap_marker_pos", None)

        if scaling is None:

            if not self.mouse_watcher.has_mouse():
                Mgr.do("set_projected_snap_marker_pos", None)
                return task.cont

            cam = self.cam()
            screen_pos = self.mouse_watcher.get_mouse()

            near_point = Point3()
            far_point = Point3()
            self.cam.lens.extrude(screen_pos, near_point, far_point)
            rel_pt = lambda point: self.world.get_relative_point(cam, point)

            point = Point3()

            if self._transf_plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point)):

                vec = V3D(point - self._scale_start_pos)
                dot_prod = vec * self._transf_axis

                if dot_prod < 0.:
                    dot_prod *= -1.0
                    scaling_factor = (1. - dot_prod * .99 / (1. + dot_prod)) ** 2.
                else:
                    dot_prod *= 10.
                    s = dot_prod * .99 / (1. + dot_prod)
                    scaling_factor = (1. + s / (1. - s)) ** 2.

                if snap_on and snap_tgt_type == "increment":
                    perc_incr = snap_settings["increment"]["scale"] / 100.
                    scaling_factor = (1. + scaling_factor // perc_incr) * perc_incr

                if axis_constraints == "xyz":

                    scaling = VBase3(scaling_factor, scaling_factor, scaling_factor)

                else:

                    scaling = VBase3(1., 1., 1.)

                    for axis in axis_constraints:
                        scaling["xyz".index(axis)] = scaling_factor

        if scaling is not None:

            if GlobalData["active_obj_level"] == "top":
                self._selection.scale(self._objs_to_transform, scaling)
            else:
                self._selection.scale(scaling)

            Mgr.do("transform_point_helpers")

        return task.cont


MainObjects.add_class(TransformationManager)
