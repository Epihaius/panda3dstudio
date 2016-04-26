from .base import *


class SelectionTransformBase(BaseObject):

    def __init__(self):

        self._center = self.uv_space.attach_new_node("uv_selection_center")
        self._pivot = self.uv_space.attach_new_node("uv_selection_pivot")

        self._pivot_start = None
        self._start_positions = []
        self._start_quats = []
        self._start_mats = []
        self._offset_vecs = []

    def update_center(self):

        if not self._objs:
            return

        pos = sum([obj.get_center_pos(self.uv_space)
                   for obj in self._objs], Point3()) / len(self._objs)
        pos[1] = 0.
        self._center.set_pos(self.uv_space, pos)

    def get_center_pos(self):

        return self._center.get_pos(self.uv_space)

    def update_ui(self, force=False):

        count = len(self._objs)

        if count == 1:
            obj = self._objs[0]

        if count:
            UVMgr.do("set_transf_gizmo_pos", self._center.get_pos())

        obj_ids = set(obj.get_id() for obj in self._objs)
        prev_obj_ids = UVMgr.get("sel_obj_ids")
        prev_obj_lvl = UVMgr.get("active_obj_level")

        if not force and obj_ids == prev_obj_ids and self._obj_level == prev_obj_lvl:
            return

        if self._obj_level != prev_obj_lvl:
            return

        UVMgr.do("update_sel_obj_ids", obj_ids)

        prev_count = Mgr.get_global("uv_selection_count")

        if count != prev_count:

            if count:
                UVMgr.do("show_transf_gizmo")
            else:
                UVMgr.do("hide_transf_gizmo")

            Mgr.set_global("uv_selection_count", count)
            Mgr.update_interface("uv_window", "selection_count")

    def set_transform_component(self, transf_type, axis, value):

        obj_lvl = self._obj_level
        uv_data_objs = self.get_uv_data_objects()

        for uv_data_obj in uv_data_objs:
            uv_data_obj.init_transform()

        if transf_type == "translate":

            if axis == "u":
                transform = Vec3(value, 0., 0.)
            else:
                transform = Vec3(0., 0., value)

            center = self._center
            center.set_pos(center, Point3(*transform))
            UVMgr.do("set_transf_gizmo_pos", self.get_center_pos())

        elif transf_type == "rotate":

            hpr = VBase3(0., 0., value)
            transform = Quat()
            transform.set_hpr(hpr)

        elif transf_type == "scale":

            if axis == "u":
                transform = Vec3(max(.01, value), 1., 1.)
            else:
                transform = Vec3(1., 1., max(.01, value))

        for uv_data_obj in uv_data_objs:
            uv_data_obj.transform_selection(obj_lvl, transf_type, transform)
            uv_data_obj.finalize_transform()

    def init_translation(self):

        self._pivot_start = self.get_center_pos()
        self._pivot.set_pos(self._pivot_start)
        self._center.wrt_reparent_to(self._pivot)

        for uv_data_obj in self.get_uv_data_objects():
            uv_data_obj.init_transform()

    def translate(self, translation_vec):

        obj_lvl = self._obj_level

        for uv_data_obj in self.get_uv_data_objects():
            uv_data_obj.transform_selection(obj_lvl, "translate", translation_vec)

        pos = self._pivot_start + translation_vec
        self._pivot.set_pos(pos)

        UVMgr.do("set_transf_gizmo_pos", self.get_center_pos())

    def init_rotation(self):

        self._pivot.set_pos(self.get_center_pos())
        self._pivot_start = self._pivot.get_quat()
        self._center.wrt_reparent_to(self._pivot)

        for uv_data_obj in self.get_uv_data_objects():
            uv_data_obj.init_transform()

    def rotate(self, rotation):

        obj_lvl = self._obj_level

        for uv_data_obj in self.get_uv_data_objects():
            uv_data_obj.transform_selection(obj_lvl, "rotate", rotation)

        quat = self._pivot_start * rotation
        self._pivot.set_quat(quat)

    def init_scaling(self):

        self._pivot.set_pos(self.get_center_pos())
        self._center.wrt_reparent_to(self._pivot)

        for uv_data_obj in self.get_uv_data_objects():
            uv_data_obj.init_transform()

    def scale(self, scaling):

        obj_lvl = self._obj_level

        for uv_data_obj in self.get_uv_data_objects():
            uv_data_obj.transform_selection(obj_lvl, "scale", scaling)

        self._pivot.set_scale(scaling)

    def finalize_transform(self, cancelled=False):

        self._center.wrt_reparent_to(self.uv_space)
        self._center.set_hpr_scale(0., 0., 0., 1., 1., 1.)
        self._center.set_shear(0., 0., 0.)
        self._pivot.clear_transform()
        self._pivot_start = None

        for uv_data_obj in self.get_uv_data_objects():
            uv_data_obj.finalize_transform(cancelled)

    def cancel_transform(self):

        active_transform_type = Mgr.get_global("active_uv_transform_type")

        if active_transform_type == "translate":
            self._pivot.set_pos(self._pivot_start)
        elif active_transform_type == "rotate":
            self._pivot.set_quat(self._pivot_start)
        elif active_transform_type == "scale":
            self._pivot.set_scale(1.)

        UVMgr.do("set_transf_gizmo_pos", self.get_center_pos())

        self.finalize_transform(cancelled=True)


class UVTransformationBase(BaseObject):

    def __init__(self):

        Mgr.set_global("active_uv_transform_type", "")

        for transf_type, axes in (("translate", "uv"), ("scale", "uv")):
            Mgr.set_global("uv_axis_constraints_%s" % transf_type, axes)

        self._selection = None
        self._transf_start_pos = Point3()

        self._transf_axis = None
        self._rot_origin = Point3()
        self._rot_start_vec = V3D()

        UVMgr.accept("init_transform", self.__init_transform)

    def setup(self):

        add_state = Mgr.add_state
        add_state("transforming", -1, interface_id="uv_window")

        def end_transform(cancel=False):

            Mgr.exit_state("transforming", "uv_window")
            self.__end_transform(cancel)

        bind = Mgr.bind_state
        bind("transforming", "cancel transform", "mouse3-up",
             lambda: end_transform(cancel=True), "uv_window")
        bind("transforming", "finalize transform", "mouse1-up",
             end_transform, "uv_window")

        Mgr.add_interface_updater("uv_window", "transf_component",
                                  self.__set_transform_component)

    def __set_transform_component(self, transf_type, axis, value):

        selection = self._selections[self._uv_set_id][self._obj_lvl]
        selection.set_transform_component(transf_type, axis, value)

    def __init_transform(self, transf_start_pos):

        active_transform_type = Mgr.get_global("active_uv_transform_type")

        if not active_transform_type:
            return

        Mgr.enter_state("transforming", "uv_window")

        self._selection = self._selections[self._uv_set_id][self._obj_lvl]
        self._transf_start_pos = transf_start_pos

        if active_transform_type == "translate":
            self.__init_translation()
        elif active_transform_type == "rotate":
            self.__init_rotation()
        if active_transform_type == "scale":
            self.__init_scaling()

    def __end_transform(self, cancel=False):

        Mgr.remove_task("transform_selection")

        if cancel:
            self._selection.cancel_transform()
        else:
            self._selection.finalize_transform()

        self._selection = None

    def __init_translation(self):

        axis_constraints = Mgr.get_global("uv_axis_constraints_translate")

        if len(axis_constraints) == 1:
            axis = Vec3()
            axis[0 if axis_constraints == "u" else 2] = 1.
            self._transf_axis = axis
        else:
            self._transf_axis = None

        self._selection.init_translation()

        Mgr.add_task(self.__translate_selection, "transform_selection", sort=3)

    def __translate_selection(self, task):

        translation_vec = UVMgr.get("picked_point") - self._transf_start_pos

        if self._transf_axis is not None:
            translation_vec = translation_vec.project(self._transf_axis)

        self._selection.translate(translation_vec)

        return task.cont

    def __init_rotation(self):

        self._rot_origin = self._selection.get_center_pos()
        rot_start_vec = V3D(self._transf_start_pos - self._rot_origin)

        if not rot_start_vec.normalize():
            return

        self._rot_start_vec = (rot_start_vec, V3D(0., 1., 0.) ** rot_start_vec)
        self._selection.init_rotation()

        Mgr.add_task(self.__rotate_selection, "transform_selection", sort=3)

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

        self._selection.rotate(rotation)

        return task.cont

    def __init_scaling(self):

        start_pos = self._transf_start_pos
        scaling_origin = self._selection.get_center_pos()
        transf_axis = V3D(start_pos - scaling_origin)

        if not transf_axis.normalize():
            return

        self._transf_axis = transf_axis
        scale_dir_vec = transf_axis * -1.
        hpr = scale_dir_vec.get_hpr()
        self._selection.init_scaling()

        Mgr.add_task(self.__scale_selection, "transform_selection", sort=3)

    def __scale_selection(self, task):

        vec = V3D(UVMgr.get("picked_point") - self._transf_start_pos)
        vec *= 1. / self.cam.get_sx()
        dot_prod = vec * self._transf_axis

        if dot_prod < 0.:
            dot_prod *= -1.0
            scaling_factor = (1. - dot_prod * .99 / (1. + dot_prod)) ** 2.
        else:
            dot_prod *= 10.
            s = dot_prod * .99 / (1. + dot_prod)
            scaling_factor = (1. + s / (1. - s)) ** 2.

        axis_constraints = Mgr.get_global("uv_axis_constraints_scale")

        if axis_constraints == "uv":
            scaling = VBase3(scaling_factor, 1., scaling_factor)
        else:
            scaling = VBase3(1., 1., 1.)
            scaling[0 if axis_constraints == "u" else 2] = scaling_factor

        self._selection.scale(scaling)

        return task.cont
