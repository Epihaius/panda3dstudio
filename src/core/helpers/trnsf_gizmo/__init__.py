from .base import *
from .translate import TranslationGizmo
from .rotate import RotationGizmo
from .scale import ScalingGizmo


class TransformGizmoManager(BaseObject, PickingColorIDManager):

    def __init__(self):

        PickingColorIDManager.__init__(self)

        self._pickable_type_id = PickableTypes.add(
            "transf_gizmo", special=True)
        gizmo_root = Mgr.get("gizmo_root")
        self._root = gizmo_root.attach_new_node("transform_gizmo_root")
        self._root.set_scale(10.)
        self._root.hide()
        Mgr.expose("transf_gizmo_root", lambda: self._root)

        self._world_pos = Point3()
        Mgr.expose("transf_gizmo_world_pos", lambda: self._world_pos)

        Mgr.accept("set_transf_gizmo", self.__set_gizmo)
        Mgr.accept("set_transf_gizmo_pos", self.__set_pos)
        Mgr.accept("set_transf_gizmo_hpr", self.__set_hpr)
        Mgr.accept("set_transf_gizmo_shear", self.__set_shear)
        Mgr.accept("update_transf_gizmo", self.__update)
        Mgr.accept("show_transf_gizmo", self.__show)
        Mgr.accept("hide_transf_gizmo", self.__hide)
        Mgr.accept("select_transf_gizmo_handle", self.__select_gizmo_handle)
        Mgr.accept("enable_transf_gizmo", self.__enable_gizmo)
        Mgr.accept("disable_transf_gizmo", self.__disable_gizmo)
        Mgr.add_app_updater("active_transform_type", self.__set_gizmo)
        Mgr.add_app_updater("axis_constraints", self.__update_active_axes)

        TransformationGizmo.set_picking_col_id_generator(
            self.get_next_picking_color_id)

        self._gizmos = {}
        self._active_gizmo = None
        self._transf_start_mouse = ()

    def setup(self):

        disabled_gizmo = DisabledGizmo()
        self._gizmos = {
            "translate": TranslationGizmo(),
            "rotate": RotationGizmo(),
            "scale": ScalingGizmo()
        }

        for gizmo in self._gizmos.itervalues():
            gizmo.hide()

        self._active_gizmo = self._gizmos[""] = disabled_gizmo
        disabled_gizmo.show()

        for transf_type in ("translate", "rotate", "scale"):
            axes = Mgr.get_global("axis_constraints_%s" % transf_type)
            self._gizmos[transf_type].set_active_axes(axes)

        return True

    def get_managed_object_type(self):

        return "transf_gizmo"

    def __use_gizmo(self, task):

        if self._active_gizmo is self._gizmos[""]:
            return task.cont

        pixel_color = Mgr.get("pixel_under_mouse")
        r, g, b, a = [int(round(c * 255.)) for c in pixel_color]
        color_id = r << 16 | g << 8 | b  # credit to coppertop @ panda3d.org

        if color_id and a == self._pickable_type_id:
            self._active_gizmo.hilite_handle(color_id)
        else:
            self._active_gizmo.remove_hilite()

        return task.cont

    def __select_gizmo_handle(self, color_id):

        self._active_gizmo.select_handle(color_id)

        return self._active_gizmo

    def __set_gizmo(self, transf_type):

        if self._active_gizmo is self._gizmos[transf_type]:
            return

        self._active_gizmo.hide()
        self._active_gizmo = self._gizmos[transf_type]
        self._active_gizmo.show()

    def __update_active_axes(self, transf_type, axes):

        Mgr.set_global("axis_constraints_%s" % transf_type, axes)
        self._gizmos[transf_type].set_active_axes(axes)

    def __enable_gizmo(self):

        Mgr.add_task(self.__use_gizmo, "use_transf_gizmo", sort=1)

    def __disable_gizmo(self):

        Mgr.remove_task("use_transf_gizmo")
        self._active_gizmo.remove_hilite()

    def __show(self):

        self._root.show()
        self.__update()

        if Mgr.get_state_id() == "selection_mode":
            self.__enable_gizmo()

    def __hide(self):

        Mgr.remove_task("use_transf_gizmo")
        self._root.hide()

    def __set_pos(self, pos):

        self._world_pos = pos
        self.__update()

    def __set_hpr(self, *args, **kwargs):

        self._root.set_hpr(*args, **kwargs)

        if self._active_gizmo is self._gizmos["scale"]:
            self._active_gizmo.face_camera()

    def __set_shear(self, shear):

        for gizmo in self._gizmos.itervalues():
            gizmo.set_shear(shear)

    def __update(self):

        if self._root.is_hidden():
            return

        normal = self.world.get_relative_vector(self.cam, Vec3(0., 1., 0.))
        point = self.world.get_relative_point(self.cam, Point3(0., 20., 0.))
        plane = Plane(normal, point)

        cam_pos = self.cam.get_pos(self.world)

        # if the apparent position of the gizmo is behind the camera, it should not
        # be seen
        if V3D(self._world_pos - cam_pos) * normal < .0001:
            self._root.set_pos(self.cam, 0., -100., 0.)
            return

        gizmo_pos = Point3()

        if not plane.intersects_line(gizmo_pos, cam_pos, self._world_pos):
            self._root.set_pos(self.cam, 0., -100., 0.)
            return

        self._root.set_pos(gizmo_pos)

        if self._active_gizmo is self._gizmos["scale"]:
            self._active_gizmo.face_camera()


MainObjects.add_class(TransformGizmoManager)
