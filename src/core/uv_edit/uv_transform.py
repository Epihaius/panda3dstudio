from .base import *


class TransformMixin:
    """ UVSelection class mix-in """

    def __init__(self):

        self._center_pos = Point3()

    def update_center_pos(self):

        if not self._objs:
            return

        pos = sum([obj.get_center_pos(GD.uv_space)
                   for obj in self._objs], Point3()) / len(self._objs)
        pos[1] = 0.
        self._center_pos = pos

    def get_center_pos(self):

        return Point3(self._center_pos)

    def update_ui(self, force=False):

        count = len(self._objs)

        if self._obj_level == "part":

            if len(self._objs) == 1:
                u, v = self._objs[0].get_pos()
                transform_values = {"translate": (u, v)}
                rotation = self._objs[0].get_rotation()
                transform_values.update({"rotate": (rotation,)})
                su, sv = self._objs[0].get_scale()
                transform_values.update({"scale": (su, sv)})
            else:
                transform_values = None

            Mgr.update_interface_remotely("uv", "transform_values", transform_values)

        elif self._obj_level == "vert":

            if count == 1:
                u, _, v = self._objs[0].get_pos()
                transform_values = {"translate": (u, v)}
            else:
                transform_values = None

            Mgr.update_interface_remotely("uv", "transform_values", transform_values)

        if count:
            UVMgr.get("transf_gizmo").set_pos(self.get_center_pos())

        obj_ids = set(obj.id for obj in self._objs)
        prev_obj_ids = UVMgr.get("sel_obj_ids")
        prev_obj_lvl = UVMgr.get("active_obj_level")

        if not force and obj_ids == prev_obj_ids and self._obj_level == prev_obj_lvl:
            return

        if self._obj_level != prev_obj_lvl:
            return

        UVMgr.do("update_sel_obj_ids", obj_ids)

        prev_count = GD["uv_selection_count"]

        if count != prev_count:
            transf_gizmo = UVMgr.get("transf_gizmo")
            transf_gizmo.show() if count else transf_gizmo.hide()
            GD["uv_selection_count"] = count
            Mgr.update_interface("uv", "selection_count")

    def set_transform_component(self, transf_type, axis, value, is_rel_value, mat=None):

        obj_lvl = self._obj_level

        if obj_lvl == "part":

            uv_prims = self.uv_prims

            if is_rel_value:
                for uv_prim in uv_prims:
                    uv_prim.init_transform()

        else:

            uv_data_objs = self.uv_data_objects

            for uv_data_obj in uv_data_objs:
                uv_data_obj.init_transform()

        if is_rel_value:

            if obj_lvl == "part":
                for uv_prim in uv_prims:
                    uv_prim.transform_selection(mat)
                    uv_prim.finalize_transform(mat)
            else:
                for uv_data_obj in uv_data_objs:
                    uv_data_obj.transform_selection(obj_lvl, mat)
                    uv_data_obj.finalize_transform()

            if len(self._objs) == 1:
                if obj_lvl == "part":
                    u, v = self._objs[0].get_pos()
                    transform_values = {"translate": (u, v)}
                    rotation = self._objs[0].get_rotation()
                    transform_values.update({"rotate": (rotation,)})
                    su, sv = self._objs[0].get_scale()
                    transform_values.update({"scale": (su, sv)})
                    Mgr.update_interface_remotely("uv", "transform_values", transform_values)
                elif obj_lvl == "vert":
                    u, _, v = self._objs[0].get_pos()
                    transform_values = {"translate": (u, v)}
                    Mgr.update_interface_remotely("uv", "transform_values", transform_values)

        elif obj_lvl == "part":

            for uv_prim in uv_prims:
                uv_prim.set_transform_component(transf_type, axis, value)

            if len(self._objs) == 1:
                u, v = self._objs[0].get_pos()
                transform_values = {"translate": (u, v)}
                rotation = self._objs[0].get_rotation()
                transform_values.update({"rotate": (rotation,)})
                su, sv = self._objs[0].get_scale()
                transform_values.update({"scale": (su, sv)})
                Mgr.update_interface_remotely("uv", "transform_values", transform_values)

        else:

            # set absolute coordinate for selected vertices

            for uv_data_obj in uv_data_objs:
                uv_data_obj.set_vert_sel_coordinate(axis, value)
                uv_data_obj.finalize_transform()

            if len(self._objs) == 1:
                u, _, v = self._objs[0].get_pos()
                transform_values = {"translate": (u, v)}
                Mgr.update_interface_remotely("uv", "transform_values", transform_values)

        self.update_center_pos()
        UVMgr.get("transf_gizmo").set_pos(self.get_center_pos())

    def init_transform(self):

        if self._obj_level == "part":
            for uv_prim in self.uv_prims:
                uv_prim.init_transform()
        else:
            for uv_data_obj in self.uv_data_objects:
                uv_data_obj.init_transform()

    def transform(self, mat):

        obj_lvl = self._obj_level

        if obj_lvl == "part":
            for uv_prim in self.uv_prims:
                uv_prim.transform_selection(mat)
        else:
            for uv_data_obj in self.uv_data_objects:
                uv_data_obj.transform_selection(obj_lvl, mat)

    def finalize_transform(self, mat, cancelled=False):

        obj_lvl = self._obj_level

        if obj_lvl == "part":
            for uv_prim in self.uv_prims:
                uv_prim.finalize_transform(mat, cancelled)
        else:
            for uv_data_obj in self.uv_data_objects:
                uv_data_obj.finalize_transform(cancelled)

        if not cancelled:

            self.update_center_pos()
            UVMgr.get("transf_gizmo").set_pos(self.get_center_pos())

            if obj_lvl == "part":

                if len(self._objs) == 1:
                    u, v = self._objs[0].get_pos()
                    transform_values = {"translate": (u, v)}
                    rotation = self._objs[0].get_rotation()
                    transform_values.update({"rotate": (rotation,)})
                    su, sv = self._objs[0].get_scale()
                    transform_values.update({"scale": (su, sv)})
                else:
                    transform_values = None

                Mgr.update_interface_remotely("uv", "transform_values", transform_values)

            elif obj_lvl == "vert":

                if len(self._objs) == 1:
                    u, _, v = self._objs[0].get_pos()
                    transform_values = {"translate": (u, v)}
                else:
                    transform_values = None

                Mgr.update_interface_remotely("uv", "transform_values", transform_values)


class UVTransformationMixin:
    """ UVEditor class mix-in """

    def __init__(self):

        GD.set_default("active_uv_transform_type", "")
        rel_values = {}

        for transf_type, axes in (("translate", "uv"), ("scale", "uv")):
            GD.set_default(f"uv_axis_constraints_{transf_type}", axes)

        for obj_lvl in ("vert", "edge", "poly", "part"):
            rel_values[obj_lvl] = {"translate": True, "rotate": True, "scale": True}

        copier = lambda data: {key: value.copy() for key, value in data.items()}
        GD.set_default("rel_uv_transform_values", rel_values, copier)

        self._selection = None
        self._transf_start_pos = Point3()

        self._transf_axis = None
        self._rot_origin = Point3()
        self._rot_start_vec = V3D()
        self._mat = None

        UVMgr.accept("init_transform", self.__init_transform)

    def setup(self):

        add_state = Mgr.add_state
        add_state("transforming", -1, interface_id="uv")

        def end_transform(cancel=False):

            Mgr.exit_state("transforming", "uv")
            self.__end_transform(cancel)

        bind = Mgr.bind_state
        bind("transforming", "cancel transform", "mouse3",
             lambda: end_transform(cancel=True), "uv")
        bind("transforming", "finalize transform", "mouse1-up",
             end_transform, "uv")

        Mgr.add_app_updater("transf_component", self.__set_transform_component, interface_id="uv")

    def __set_transform_component(self, transf_type, axis, value, is_rel_value):

        mat = None

        if is_rel_value:

            if transf_type == "translate":

                if axis == "u":
                    translation_vec = Vec3(value, 0., 0.)
                else:
                    translation_vec = Vec3(0., 0., value)

                mat = Mat4.translate_mat(translation_vec)

            elif transf_type == "rotate":

                hpr = VBase3(0., 0., value)
                rotation = Quat()
                rotation.set_hpr(hpr)
                tc_pos = UVMgr.get("selection_center")
                quat_mat = Mat4()
                rotation.extract_to_matrix(quat_mat)
                offset_mat = Mat4.translate_mat(-tc_pos)
                mat = offset_mat * quat_mat
                offset_mat = Mat4.translate_mat(tc_pos)
                mat *= offset_mat

            elif transf_type == "scale":

                if axis == "u":
                    scaling = Vec3(max(.01, value), 1., 1.)
                else:
                    scaling = Vec3(1., 1., max(.01, value))

                tc_pos = UVMgr.get("selection_center")
                mat = Mat4.scale_mat(scaling)
                offset_mat = Mat4.translate_mat(-tc_pos)
                mat = offset_mat * mat
                offset_mat = Mat4.translate_mat(tc_pos)
                mat *= offset_mat

        selection = self._selections[self._uv_set_id][self._obj_lvl]
        selection.set_transform_component(transf_type, axis, value, is_rel_value, mat)

    def __init_transform(self, transf_start_pos):

        active_transform_type = GD["active_uv_transform_type"]

        if not active_transform_type:
            return

        self._selection = self._selections[self._uv_set_id][self._obj_lvl]
        self._transf_start_pos = transf_start_pos

        if active_transform_type == "translate":
            self.__init_translation()
        elif active_transform_type == "rotate":
            if not self.__init_rotation():
                return
        if active_transform_type == "scale":
            if not self.__init_scaling():
                return

        Mgr.enter_state("transforming", "uv")
        self._selection.init_transform()

        Mgr.update_app("status", ["select_uvs", active_transform_type, "in_progress"], "uv")

    def __end_transform(self, cancel=False):

        Mgr.remove_task("transform_selection")
        self._selection.finalize_transform(self._mat, cancel)
        self._selection = None
        self._mat = None

    def __init_translation(self):

        axis_constraints = GD["uv_axis_constraints_translate"]

        if len(axis_constraints) == 1:
            axis = Vec3()
            axis[0 if axis_constraints == "u" else 2] = 1.
            self._transf_axis = axis
        else:
            self._transf_axis = None

        Mgr.add_task(self.__translate_selection, "transform_selection", sort=3)

    def __translate_selection(self, task):

        translation_vec = UVMgr.get("picked_point") - self._transf_start_pos

        if self._transf_axis is not None:
            translation_vec = translation_vec.project(self._transf_axis)

        mat = Mat4.translate_mat(translation_vec)
        self._mat = mat

        self._selection.transform(mat)

        return task.cont

    def __init_rotation(self):

        self._rot_origin = self._selection.get_center_pos()
        rot_start_vec = V3D(self._transf_start_pos - self._rot_origin)

        if not rot_start_vec.normalize():
            return False

        self._rot_start_vec = (rot_start_vec, V3D(0., 1., 0.) ** rot_start_vec)

        Mgr.add_task(self.__rotate_selection, "transform_selection", sort=3)

        return True

    def __rotate_selection(self, task):

        rotation_vec = V3D(UVMgr.get("picked_point") - self._rot_origin)

        if not rotation_vec.normalize():
            return task.cont

        angle = self._rot_start_vec[0].angle_deg(rotation_vec)

        if self._rot_start_vec[1] * rotation_vec < 0.:
            angle = 360. - angle

        hpr = VBase3(0., 0., angle)
        rotation = Quat()
        rotation.set_hpr(hpr)

        tc_pos = UVMgr.get("selection_center")
        quat_mat = Mat4()
        rotation.extract_to_matrix(quat_mat)
        offset_mat = Mat4.translate_mat(-tc_pos)
        mat = offset_mat * quat_mat
        offset_mat = Mat4.translate_mat(tc_pos)
        mat *= offset_mat
        self._mat = mat

        self._selection.transform(mat)

        return task.cont

    def __init_scaling(self):

        start_pos = self._transf_start_pos
        scaling_origin = self._selection.get_center_pos()
        transf_axis = V3D(start_pos - scaling_origin)

        if not transf_axis.normalize():
            return False

        self._transf_axis = transf_axis
        scale_dir_vec = transf_axis * -1.
        hpr = scale_dir_vec.get_hpr()

        Mgr.add_task(self.__scale_selection, "transform_selection", sort=3)

        return True

    def __scale_selection(self, task):

        vec = V3D(UVMgr.get("picked_point") - self._transf_start_pos)
        vec *= 1. / GD.uv_cam.get_sx()
        dot_prod = vec * self._transf_axis

        if dot_prod < 0.:
            dot_prod *= -1.0
            scaling_factor = (1. - dot_prod * .99 / (1. + dot_prod)) ** 2.
        else:
            dot_prod *= 10.
            s = dot_prod * .99 / (1. + dot_prod)
            scaling_factor = (1. + s / (1. - s)) ** 2.

        axis_constraints = GD["uv_axis_constraints_scale"]

        if axis_constraints == "uv":
            scaling = VBase3(scaling_factor, 1., scaling_factor)
        else:
            scaling = VBase3(1., 1., 1.)
            scaling[0 if axis_constraints == "u" else 2] = scaling_factor

        tc_pos = UVMgr.get("selection_center")
        mat = Mat4.scale_mat(scaling)
        offset_mat = Mat4.translate_mat(-tc_pos)
        mat = offset_mat * mat
        offset_mat = Mat4.translate_mat(tc_pos)
        mat *= offset_mat
        self._mat = mat

        self._selection.transform(mat)

        return task.cont
