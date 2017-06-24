from .base import *


class MainCamera(BaseObject):

    def __get_origin(self):

        return self._origins[GlobalData["view"]]

    def __get_lens_type(self):

        return self._lens_types[GlobalData["view"]]

    def __set_lens_type(self, lens_type):

        self._lens_types[GlobalData["view"]] = lens_type
        self.target.set_scale(1.) if lens_type == "persp" else self.origin.set_y(-500.)

    def __get_lens(self):

        return self._lenses[self.lens_type]

    def __get_target(self):

        return self._targets[GlobalData["view"]]

    def __get_pivot(self):

        return self._pivots[GlobalData["view"]]

    def __get_zoom(self):

        return self.origin.get_y() if self.lens_type == "persp" else self.target.get_sx()

    def __set_zoom(self, zoom):

        self.origin.set_y(zoom) if self.lens_type == "persp" else self.target.set_scale(zoom)

    origin = property(__get_origin)
    lens_type = property(__get_lens_type, __set_lens_type)
    lens = property(__get_lens)
    target = property(__get_target)
    pivot = property(__get_pivot)
    zoom = property(__get_zoom, __set_zoom)

    def __init__(self):

        BaseObject.__init__(self)
        BaseObject.set_cam(self)

        core = Mgr.get("core")
        mask_persp = BitMask32.bit(10)
        mask_ortho = BitMask32.bit(11)
        self._masks = {"persp": mask_persp, "ortho": mask_ortho, "all": mask_persp | mask_ortho}
        self._node = core.camNode
        self._node.set_camera_mask(mask_persp)

        lens_persp = core.camLens
        lens_ortho = OrthographicLens()
        size_h, size_v = lens_persp.get_film_size()
        film_size = (285., 285. * size_v / size_h)
        lens_ortho.set_film_size(film_size)
        lens_ortho.set_near(-100000.)

        self._pivots = {}
        self._targets = {}
        self._origins = {}
        self._lens_types = {}
        self._lenses = {"persp": lens_persp, "ortho": lens_ortho}

        self._cam_np = core.cam
        self._camera = camera = core.camera
        default_light = Mgr.get("default_light")
        default_light.reparent_to(camera)

        self._zoom_indicator = self.screen.attach_new_node("zoom_indicator")
        cm = CardMaker("zoom_indicator_part")
        cm.set_frame(-.0533333, .0533333, -.0533333, .0533333)
        cm.set_has_normals(False)
        zoom_indicator_ring = self._zoom_indicator.attach_new_node(cm.generate())
        zoom_indicator_ring.set_texture(Mgr.load_tex(GFX_PATH + "zoom_indic_ring.png"))
        zoom_indicator_ring.set_transparency(TransparencyAttrib.M_alpha)
        zoom_indicator_ring.set_alpha_scale(.5)
        self._zoom_indicator_dot = self._zoom_indicator.attach_new_node(cm.generate())
        self._zoom_indicator_dot.set_texture(Mgr.load_tex(GFX_PATH + "zoom_indic_dot.png"))
        self._zoom_indicator_dot.set_transparency(TransparencyAttrib.M_alpha)
        self._zoom_indicator_dot.set_alpha_scale(.5)

        self.expose("origin", lambda: self.origin)
        self.expose("node", lambda: self._node)
        self.expose("lens", lambda: self.lens)
        self.expose("target", lambda: self.target)
        Mgr.expose("render_masks", lambda: self._masks)
        Mgr.expose("cam", lambda: self)
        Mgr.accept("update_zoom_indicator", self.__update_zoom_indicator)

        # Create a secondary camera and DisplayRegion to render gizmos on top of the
        # 3D scene.

        dr = core.win.make_display_region()
        dr.set_sort(1)
        gizmo_cam_mask = BitMask32.bit(22)
        gizmo_cam_node = Camera("gizmo_cam")
        gizmo_cam_node.set_camera_mask(gizmo_cam_mask)
        gizmo_cam_node.set_lens(lens_persp)
        gizmo_cam = Mgr.get("gizmo_root").attach_new_node(gizmo_cam_node)
        gizmo_cam.set_effect(CompassEffect.make(camera, CompassEffect.P_all))
        dr.set_camera(gizmo_cam)
        dr.set_clear_color_active(False)
        dr.set_clear_depth_active(True)
        self._gizmo_cam = gizmo_cam
        Mgr.expose("gizmo_render_mask", lambda: gizmo_cam_mask)
        Mgr.expose("gizmo_cam", lambda: gizmo_cam)

    def __call__(self):

        return self._cam_np

    def setup(self):

        if "grid_ok" not in MainObjects.get_setup_results():
            return False

        GlobalData["view"] = "ortho"
        Mgr.update_app("view", "set", "persp")

        return True

    def get_pivot_positions(self):

        pos = {}

        for view, pivot in self._pivots.iteritems():
            pos[view] = pivot.get_pos()

        return pos

    def set_pivot_positions(self, positions):

        pivots = self._pivots

        for view, pos in positions.iteritems():
            pivots[view].set_pos(pos)

    def get_pivot_hprs(self):

        hprs = {}

        for view, pivot in self._pivots.iteritems():
            hprs[view] = pivot.get_hpr()

        return hprs

    def set_pivot_hprs(self, hprs):

        pivots = self._pivots

        for view, hpr in hprs.iteritems():
            pivots[view].set_hpr(hpr)

    def get_target_hprs(self):

        hprs = {}

        for view, target in self._targets.iteritems():
            hprs[view] = target.get_hpr()

        return hprs

    def set_target_hprs(self, hprs):

        targets = self._targets

        for view, hpr in hprs.iteritems():
            targets[view].set_hpr(hpr)

    def get_zooms(self):

        lens_types = self._lens_types
        targets = self._targets
        origs = self._origins
        zooms = {}

        for view, lens_type in lens_types.iteritems():
            if lens_type == "persp":
                zooms[view] = origs[view].get_y()
            else:
                zooms[view] = targets[view].get_sx()

        return zooms

    def set_zooms(self, zooms):

        lens_types = self._lens_types
        targets = self._targets
        origs = self._origins

        for view, zoom in zooms.iteritems():
            if lens_types[view] == "persp":
                origs[view].set_y(zoom)
            else:
                targets[view].set_scale(zoom)

    def add_rig(self, view, front_hpr, pos, hpr, lens_type, zoom):

        pivot = self.world.attach_new_node("camera_pivot_%s" % view)
        pivot.set_pos(pos)
        pivot.set_hpr(front_hpr)
        self._pivots[view] = pivot
        target = pivot.attach_new_node("camera_target_%s" % view)
        target.set_hpr(hpr)
        self._targets[view] = target
        orig = target.attach_new_node("camera_origin_%s" % view)
        self._origins[view] = orig
        self._lens_types[view] = lens_type

        if lens_type == "persp":
            orig.set_y(zoom)
        else:
            orig.set_y(-500.)
            target.set_scale(zoom)

    def remove_rig(self, view):

        pivot = self._pivots[view]
        pivot.remove_node()
        del self._pivots[view]
        target = self._targets[view]
        target.remove_node()
        del self._targets[view]
        orig = self._origins[view]
        orig.remove_node()
        del self._origins[view]
        del self._lens_types[view]

    def convert_zoom(self, to_lens_type, from_lens_type=None, zoom=None):

        if not from_lens_type:
            from_lens_type = self.lens_type

        if not zoom:
            zoom = self.zoom

        if from_lens_type == to_lens_type:
            return zoom

        lens_persp = self._lenses["persp"]
        tan = math.tan(math.radians(lens_persp.get_hfov() * .5))

        if from_lens_type == "persp":
            return max(.0004, min(100000., -zoom * tan * 2. / 285.))
        else:
            near = lens_persp.get_near()
            return min(-near, max(-1000000., -zoom * 285. * .5 / tan))

    def update(self):

        lens = self.lens
        self._camera.reparent_to(self.origin)
        self._node.set_lens(lens)
        self._node.set_camera_mask(self._masks[self.lens_type])
        self._gizmo_cam.node().set_lens(lens)

    def __update_zoom_indicator(self):

        if self.lens_type == "persp":
            scale = (1. / -self.origin.get_y()) ** .2
        else:
            target_scale = self.target.get_sx()
            scale = (.0004 / max(.0004, min(100000., target_scale))) ** .13

        self._zoom_indicator_dot.set_scale(scale)


class PickingCamera(BaseObject):

    def __init__(self):

        self._tex = None
        self._tex_peeker = None
        self._buffer = None
        self._np = None
        self._lenses = {}
        self._cull_bounds = {}
        mask_persp = BitMask32.bit(15)
        mask_ortho = BitMask32.bit(16)
        self._masks = {"persp": mask_persp, "ortho": mask_ortho, "all": mask_persp | mask_ortho}
        self._pixel_color = VBase4()

        Mgr.expose("picking_masks", lambda: self._masks)
        Mgr.expose("pixel_under_mouse", lambda: VBase4(self._pixel_color))

    def setup(self):

        core = Mgr.get("core")
        self._tex = Texture("picking_texture")
        props = FrameBufferProperties()
        props.set_rgba_bits(16, 16, 16, 16)
        props.set_depth_bits(16)
        self._buffer = bfr = core.win.make_texture_buffer("picking_buffer",
                                                          1, 1,
                                                          self._tex,
                                                          to_ram=True,
                                                          fbp=props)

        bfr.set_clear_color(VBase4())
        bfr.set_clear_color_active(True)
        bfr.set_sort(-100)
        self._np = core.make_camera(bfr)
        node = self._np.node()
        lens_persp = node.get_lens()
        lens_persp.set_fov(1.)
        cull_bounds_persp = lens_persp.make_bounds()
        node.set_cull_bounds(cull_bounds_persp)
        lens_persp.set_fov(.1)
        lens_ortho = OrthographicLens()
        lens_ortho.set_film_size(.75)
        lens_ortho.set_near(-100000.)
        cull_bounds_ortho = lens_ortho.make_bounds()
        self._lenses = {"persp": lens_persp, "ortho": lens_ortho}
        self._cull_bounds = {"persp": cull_bounds_persp, "ortho": cull_bounds_ortho}
        node.set_camera_mask(self._masks["persp"])
        Mgr.expose("picking_cam", lambda: self)

        state_np = NodePath("state_np")
        state_np.set_texture_off(1)
        state_np.set_material_off(1)
        state_np.set_light_off(1)
        state_np.set_color_off(1)
        state_np.set_color_scale_off(1)
        state_np.set_render_mode_thickness(5, 1)
        state_np.set_transparency(TransparencyAttrib.M_none, 1)
        state = state_np.get_state()
        node.set_initial_state(state)

        # For rendering BasicGeoms as pickable geometry
        node.set_tag_state_key("picking_color")
        Mgr.accept("set_basic_geom_picking_color", node.set_tag_state)
        Mgr.accept("clear_basic_geom_picking_color", node.clear_tag_state)

        # Create a secondary camera and DisplayRegion to render gizmos on top of the
        # 3D scene.

        dr = self._buffer.make_display_region()
        dr.set_sort(1)
        gizmo_cam_mask = BitMask32.bit(23)
        gizmo_cam_node = Camera("gizmo_cam")
        gizmo_cam_node.set_camera_mask(gizmo_cam_mask)
        gizmo_cam_node.set_lens(lens_persp)
        gizmo_cam_node.set_cull_bounds(cull_bounds_persp)
        gizmo_cam_node.set_initial_state(state)
        gizmo_cam = Mgr.get("gizmo_cam").attach_new_node(gizmo_cam_node)
        gizmo_cam.set_effect(CompassEffect.make(self._np, CompassEffect.P_all))
        dr.set_camera(gizmo_cam)
        dr.set_clear_color_active(False)
        dr.set_clear_depth_active(True)
        self._gizmo_cam = gizmo_cam
        Mgr.expose("gizmo_picking_mask", lambda: gizmo_cam_mask)

        Mgr.accept("adjust_picking_cam_to_lens", self.__adjust_to_lens)
        Mgr.add_task(self.__get_pixel_under_mouse, "get_pixel_under_mouse", sort=0)

        return "picking_camera_ok"

    def __adjust_to_lens(self):

        lens_type = self.cam.lens_type
        lens = self._lenses[lens_type]
        bounds = self._cull_bounds[lens_type]
        node = self._np.node()
        node.set_lens(lens)
        node.set_cull_bounds(bounds)
        node.set_camera_mask(self._masks[lens_type])
        gizmo_cam_node = self._gizmo_cam.node()
        gizmo_cam_node.set_lens(lens)
        gizmo_cam_node.set_cull_bounds(bounds)

        if lens_type == "persp":
            self._np.set_pos(0., 0., 0.)
        else:
            self._np.set_hpr(0., 0., 0.)

    def set_active(self, is_active=True):

        if self._np.node().is_active() == is_active:
            return

        self._np.node().set_active(is_active)

        if is_active:
            Mgr.add_task(self.__get_pixel_under_mouse, "get_pixel_under_mouse", sort=0)
        else:
            Mgr.remove_task("get_pixel_under_mouse")
            self._pixel_color = VBase4()

    def __get_pixel_under_mouse(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        screen_pos = self.mouse_watcher.get_mouse()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, Point3(), far_point)

        if self.cam.lens_type == "persp":
            self._np.look_at(far_point)
        else:
            far_point.y = 0.
            self._np.set_pos(far_point)

        if not self._tex_peeker:
            self._tex_peeker = self._tex.peek()
            return task.cont

        self._tex_peeker.lookup(self._pixel_color, .5, .5)

        return task.cont


# the following camera is used to detect temporary geometry created to allow subobject
# picking via polygon
class AuxiliaryPickingCamera(BaseObject):

    def __init__(self):

        self._pixel_color = VBase4()
        Mgr.expose("aux_pixel_under_mouse", lambda: VBase4(self._pixel_color))

        core = Mgr.get("core")
        self._tex = Texture("aux_picking_texture")
        self._tex_peeker = None
        props = FrameBufferProperties()
        props.set_rgba_bits(16, 16, 16, 16)
        props.set_depth_bits(16)
        self._buffer = bfr = core.win.make_texture_buffer("aux_picking_buffer",
                                                          1, 1,
                                                          self._tex,
                                                          to_ram=True,
                                                          fbp=props)

        bfr.set_clear_color(VBase4())
        bfr.set_clear_color_active(True)
        bfr.set_sort(-100)
        self._np = core.make_camera(bfr)
        node = self._np.node()
        lens = OrthographicLens()
        lens.set_film_size(.75)
        lens.set_near(0.)
        bounds = lens.make_bounds()
        node.set_lens(lens)
        node.set_cull_bounds(bounds)
        Mgr.expose("aux_picking_cam", lambda: self)

        state_np = NodePath("state_np")
        state_np.set_texture_off(1)
        state_np.set_material_off(1)
        state_np.set_light_off(1)
        state_np.set_color_off(1)
        state_np.set_color_scale_off(1)
        state_np.set_transparency(TransparencyAttrib.M_none, 1)
        state = state_np.get_state()
        node.set_initial_state(state)
        node.set_active(False)

        self._plane = None

    def setup(self):

        self._np.reparent_to(Mgr.get("aux_picking_root"))

        return True

    def get_origin(self):

        return self._np

    def set_plane(self, plane):

        self._plane = plane

    def update_pos(self):

        if not self.mouse_watcher.has_mouse():
            return

        cam = self.cam()
        screen_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)
        point = Point3()
        self._plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))
        self._np.set_pos(point)

    def set_active(self, is_active=True):

        if self._np.node().is_active() == is_active:
            return

        self._np.node().set_active(is_active)

        if is_active:
            Mgr.add_task(self.__get_pixel_under_mouse, "get_aux_pixel_under_mouse", sort=0)
        else:
            Mgr.remove_task("get_aux_pixel_under_mouse")
            self._pixel_color = VBase4()

    def __get_pixel_under_mouse(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        cam = self.cam()
        screen_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)
        point = Point3()
        self._plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))
        self._np.look_at(point)

        if not self._tex_peeker:
            self._tex_peeker = self._tex.peek()
            return task.cont

        self._tex_peeker.lookup(self._pixel_color, .5, .5)

        return task.cont


MainObjects.add_class(MainCamera)
MainObjects.add_class(PickingCamera)
MainObjects.add_class(AuxiliaryPickingCamera)
