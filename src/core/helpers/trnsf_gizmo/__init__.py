from .base import *
from .translate import TranslationGizmo
from .rotate import RotationGizmo
from .scale import ScalingGizmo


class TransformGizmoManager(BaseObject, PickingColorIDManager):

    def __get_root(self):

        return self._roots[self.cam.lens_type]

    root = property(__get_root)

    def __init__(self):

        PickingColorIDManager.__init__(self)

        self._pickable_type_id = PickableTypes.add("transf_gizmo", special=True)
        self._base = None
        self._roots = {}
        Mgr.expose("transf_gizmo_root", lambda: self.root)

        self._target_node = self.world.attach_new_node("transf_gizmo_target")
        Mgr.expose("transf_gizmo_target", lambda: self._target_node)
        Mgr.expose("transf_gizmo_world_pos", self._target_node.get_pos)
        compass_props = CompassEffect.P_pos | CompassEffect.P_rot
        self._compass_effect = CompassEffect.make(self._target_node, compass_props)

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
        Mgr.accept("adjust_transform_gizmo_to_lens", self.__adjust_to_lens)
        Mgr.add_app_updater("active_transform_type", self.__set_gizmo)
        Mgr.add_app_updater("axis_constraints", self.__update_active_axes)

        TransformationGizmo.set_picking_col_id_generator(self.get_next_picking_color_id)

        self._gizmos = {}
        self._active_gizmo = None
        self._transf_start_mouse = ()

    def setup(self):

        gizmo_cam = Mgr.get("gizmo_cam")
        self._base = gizmo_base = gizmo_cam.attach_new_node("transform_gizmo_base")
        root_persp = gizmo_base.attach_new_node("transform_gizmo_root_persp")
        root_ortho = gizmo_cam.attach_new_node("transform_gizmo_root_ortho")
        root_persp.hide()
        root_ortho.hide()
        root_ortho.set_scale(200.)
        bounds = BoundingSphere(Point3(), 1.5)
        root_persp.node().set_bounds(bounds)
        root_persp.node().set_final(True)
        bounds = OmniBoundingVolume()
        root_ortho.node().set_bounds(bounds)
        root_ortho.node().set_final(True)
        self._roots = roots = {"persp": root_persp, "ortho": root_ortho}

        self._gizmos = {
            "": DisabledGizmo(),
            "translate": TranslationGizmo(),
            "rotate": RotationGizmo(),
            "scale": ScalingGizmo()
        }

        for gizmo in self._gizmos.itervalues():
            gizmo.hide()

        self._active_gizmo = disabled_gizmo = self._gizmos[""]
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

        self._base.set_billboard_point_world(self._target_node, 2.)
        roots = self._roots
        roots["persp"].set_compass(self._target_node)
        roots["persp"].show()
        roots["ortho"].set_effect(self._compass_effect)
        roots["ortho"].show()
        self.__update()

        if Mgr.get_state_id() == "selection_mode":
            self.__enable_gizmo()

    def __hide(self):

        Mgr.remove_task("use_transf_gizmo")
        roots = self._roots
        roots["persp"].hide()
        roots["persp"].clear_compass()
        roots["ortho"].hide()
        roots["ortho"].clear_effect(CompassEffect.get_class_type())
        self._base.clear_billboard()

    def __set_pos(self, pos):

        self._target_node.set_pos(pos)
        self.__update()

    def __set_hpr(self, *args, **kwargs):

        self._target_node.set_hpr(*args, **kwargs)

        if self._active_gizmo is self._gizmos["scale"]:
            self._active_gizmo.face_camera()

    def __set_shear(self, shear):

        for gizmo in self._gizmos.itervalues():
            gizmo.set_shear(shear)

    def __update(self):

        if self.root.is_hidden():
            return

        if self._active_gizmo is self._gizmos["scale"]:
            self._active_gizmo.face_camera()

    def __adjust_to_lens(self, lens_type_prev, lens_type_next):

        roots = self._roots
        roots[lens_type_prev].get_children().reparent_to(roots[lens_type_next])
        self._gizmos["rotate"].adjust_to_lens(lens_type_next)


MainObjects.add_class(TransformGizmoManager)
