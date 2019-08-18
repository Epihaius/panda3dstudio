from .base import *
from .translate import TranslationGizmo
from .rotate import RotationGizmo
from .scale import ScalingGizmo


class TransformGizmos(PickingColorIDManager):

    def __init__(self):

        PickingColorIDManager.__init__(self)

        self._pickable_type_id = PickableTypes.add("transf_gizmo", special=True)
        self._base = None
        self._roots = {}

        self._target_node = GD.world.attach_new_node("transf_gizmo_target")
        compass_props = CompassEffect.P_pos | CompassEffect.P_rot
        self._compass_effect = CompassEffect.make(self._target_node, compass_props)

        Mgr.expose("transf_gizmo", lambda: self)
        Mgr.add_app_updater("active_transform_type", self.__set_gizmo)
        Mgr.add_app_updater("axis_constraints", self.update_active_axes)
        Mgr.add_app_updater("viewport", self.__handle_viewport_resize)

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
        root_persp.node().final = True
        bounds = OmniBoundingVolume()
        root_ortho.node().set_bounds(bounds)
        root_ortho.node().final = True
        self._roots = roots = {"persp": root_persp, "ortho": root_ortho}

        self._gizmos = {
            "": DisabledGizmo(),
            "translate": TranslationGizmo(),
            "rotate": RotationGizmo(),
            "scale": ScalingGizmo()
        }

        for gizmo in self._gizmos.values():
            gizmo.hide()

        self._active_gizmo = disabled_gizmo = self._gizmos[""]
        disabled_gizmo.show()

        for transf_type in ("translate", "rotate", "scale"):
            axes = GD["axis_constraints"][transf_type]
            self._gizmos[transf_type].set_active_axes(axes)

        return True

    def get_managed_object_type(self):

        return "transf_gizmo"

    @property
    def root(self):

        return self._roots[GD.cam.lens_type]

    @property
    def target(self):

        return self._target_node

    def __handle_viewport_resize(self):

        w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
        scale = 800. / max(w, h)
        self._base.set_scale(scale)
        self._roots["ortho"].set_scale(200. * scale)

    def __use_gizmo(self, task):

        if self._active_gizmo is self._gizmos[""]:
            return task.cont

        pixel_color = Mgr.get("pixel_under_mouse")
        r, g, b, a = [int(round(c * 255.)) for c in pixel_color]
        color_id = r << 16 | g << 8 | b

        if color_id and a == self._pickable_type_id:
            self._active_gizmo.hilite_handle(color_id)
        else:
            self._active_gizmo.remove_hilite()

        return task.cont

    def select_handle(self, color_id):

        self._active_gizmo.select_handle(color_id)

        return self._active_gizmo

    def __set_gizmo(self, transf_type):

        if self._active_gizmo is self._gizmos[transf_type]:
            return

        self._active_gizmo.hide()
        self._active_gizmo = self._gizmos[transf_type]
        self._active_gizmo.show()

    def update_active_axes(self, transf_type, axes):

        GD["axis_constraints"][transf_type] = axes
        self._gizmos[transf_type].set_active_axes(axes)

    def enable(self, enable=True):

        if enable:
            Mgr.add_task(self.__use_gizmo, "use_transf_gizmo", sort=1)
        else:
            Mgr.remove_task("use_transf_gizmo")
            self._active_gizmo.remove_hilite()

    def show(self):

        self._base.set_billboard_point_world(self._target_node, 2.)
        roots = self._roots
        roots["persp"].set_compass(self._target_node)
        roots["persp"].show()
        roots["ortho"].set_effect(self._compass_effect)
        roots["ortho"].show()
        self.update()

        if Mgr.get_state_id() == "selection_mode":
            self.enable()

    def hide(self):

        Mgr.remove_task("use_transf_gizmo")
        roots = self._roots
        roots["persp"].hide()
        roots["persp"].clear_compass()
        roots["ortho"].hide()
        roots["ortho"].clear_effect(CompassEffect)
        self._base.clear_billboard()

    def set_pickable(self, pickable=True):

        picking_mask = Mgr.get("gizmo_picking_mask")

        for root in self._roots.values():
            root.show(picking_mask) if pickable else root.hide(picking_mask)

    @property
    def pos(self):

        return self._target_node.get_pos()

    def set_pos(self, pos):

        self._target_node.set_pos(pos)
        self.update()

    @pos.setter
    def pos(self, pos):

        self.set_pos(pos)

    @property
    def hpr(self):

        return self._target_node.get_hpr()

    @hpr.setter
    def hpr(self, hpr):

        self.set_hpr(hpr)

    def set_hpr(self, *args, **kwargs):

        self._target_node.set_hpr(*args, **kwargs)

        if self._active_gizmo is self._gizmos["scale"]:
            self._active_gizmo.face_camera()

    def update(self):

        if self.root.is_hidden():
            return

        if self._active_gizmo is self._gizmos["scale"]:
            self._active_gizmo.face_camera()

    def adjust_to_lens(self, lens_type_prev, lens_type_next):

        roots = self._roots
        roots[lens_type_prev].children.reparent_to(roots[lens_type_next])
        self._gizmos["rotate"].adjust_to_lens(lens_type_next)


MainObjects.add_class(TransformGizmos)
