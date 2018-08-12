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

        base = Mgr.get("base")
        self._mask = mask = BitMask32.bit(10)
        self._node = base.camNode
        self._node.set_camera_mask(mask)

        lens_persp = base.camLens
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

        self._cam_np = base.cam
        self._camera = camera = base.camera
        default_light = Mgr.get("default_light")
        default_light.reparent_to(camera)

        # A separate LensNode projects the selection texture onto selected polygons

        self._projector_lenses = lenses = {"persp": PerspectiveLens(), "ortho": OrthographicLens()}
        projector_node = LensNode("projector", lenses["persp"])
        self._projector = self._cam_np.attach_new_node(projector_node)

        self._zoom_indicator = self.viewport.attach_new_node("zoom_indicator")
        cm = CardMaker("zoom_indicator_part")
        cm.set_frame(-16, 16, -16, 16)
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
        Mgr.expose("render_mask", lambda: self._mask)
        Mgr.expose("cam", lambda: self)
        Mgr.accept("update_zoom_indicator", self.__update_zoom_indicator)

        # Create a secondary camera and DisplayRegion to render gizmos on top of the
        # 3D scene.

        dr = base.win.make_display_region()
        GlobalData["viewport"]["display_regions"].append(dr)
        dr.set_sort(1)
        gizmo_cam_mask = BitMask32.bit(11)
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
        Mgr.add_app_updater("viewport", self.__update_lens_aspect_ratio)

    def __call__(self):

        return self._cam_np

    def setup(self):

        if "grid_ok" not in MainObjects.get_setup_results():
            return False

        GlobalData["view"] = "ortho"
        Mgr.update_app("view", "set", "persp")

        return "main_camera_ok"

    def __update_lens_aspect_ratio(self):

        w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "main" else "size"]
        lens_persp = self._lenses["persp"]
        fov_h, fov_v = lens_persp.get_fov()

        if h > w:
            fov_v = max(fov_h, fov_v)
            tan = math.tan(math.radians(fov_v * .5))
            fov_h = 2. * math.degrees(math.atan(tan * w / h))
        else:
            fov_h = max(fov_h, fov_v)
            tan = math.tan(math.radians(fov_h * .5))
            fov_v = 2. * math.degrees(math.atan(tan * h / w))

        lens_persp.set_fov(fov_h, fov_v)
        lens_ortho = self._lenses["ortho"]
        size_h, size_v = lens_ortho.get_film_size()

        if h > w:
            size_v = max(size_h, size_v)
            size_h = size_v * w / h
        else:
            size_h = max(size_h, size_v)
            size_v = size_h * h / w

        lens_ortho.set_film_size(size_h, size_v)

        self._zoom_indicator.set_pos(w * .5, 0., -h * .5)
        self.viewport.set_scale(2./w, 1., 2./h)

    def get_projector(self):

        return self._projector

    def get_projector_lenses(self):

        return self._projector_lenses

    def get_pivot_positions(self):

        pos = {}

        for view_id, pivot in self._pivots.items():
            pos[view_id] = pivot.get_pos()

        return pos

    def set_pivot_positions(self, positions):

        pivots = self._pivots

        for view_id, pos in positions.items():
            pivots[view_id].set_pos(pos)

    def get_pivot_hprs(self):

        hprs = {}

        for view_id, pivot in self._pivots.items():
            hprs[view_id] = pivot.get_hpr()

        return hprs

    def set_pivot_hprs(self, hprs):

        pivots = self._pivots

        for view_id, hpr in hprs.items():
            pivots[view_id].set_hpr(hpr)

    def get_target_hprs(self):

        hprs = {}

        for view_id, target in self._targets.items():
            hprs[view_id] = target.get_hpr()

        return hprs

    def set_target_hprs(self, hprs):

        targets = self._targets

        for view_id, hpr in hprs.items():
            targets[view_id].set_hpr(hpr)

    def get_zooms(self):

        lens_types = self._lens_types
        targets = self._targets
        origs = self._origins
        zooms = {}

        for view_id, lens_type in lens_types.items():
            if lens_type == "persp":
                zooms[view_id] = origs[view_id].get_y()
            else:
                zooms[view_id] = targets[view_id].get_sx()

        return zooms

    def set_zooms(self, zooms):

        lens_types = self._lens_types
        targets = self._targets
        origs = self._origins

        for view_id, zoom in zooms.items():
            if lens_types[view_id] == "persp":
                origs[view_id].set_y(zoom)
            else:
                targets[view_id].set_scale(zoom)

    def add_rig(self, view_id, front_hpr, pos, hpr, lens_type, zoom):

        pivot = self.world.attach_new_node("camera_pivot_{}".format(view_id))
        pivot.set_pos(pos)
        pivot.set_hpr(front_hpr)
        self._pivots[view_id] = pivot
        target = pivot.attach_new_node("camera_target_{}".format(view_id))
        target.set_hpr(hpr)
        self._targets[view_id] = target
        orig = target.attach_new_node("camera_origin_{}".format(view_id))
        self._origins[view_id] = orig
        self._lens_types[view_id] = lens_type

        if lens_type == "persp":
            orig.set_y(zoom)
        else:
            orig.set_y(-500.)
            target.set_scale(zoom)

    def remove_rig(self, view_id):

        pivot = self._pivots[view_id]
        pivot.remove_node()
        del self._pivots[view_id]
        target = self._targets[view_id]
        target.remove_node()
        del self._targets[view_id]
        orig = self._origins[view_id]
        orig.remove_node()
        del self._origins[view_id]
        del self._lens_types[view_id]

    def convert_zoom(self, to_lens_type, from_lens_type=None, zoom=None):

        if not from_lens_type:
            from_lens_type = self.lens_type

        if not zoom:
            zoom = self.zoom

        if from_lens_type == to_lens_type:
            return zoom

        lens_persp = self._lenses["persp"]
        tan = math.tan(math.radians(max(lens_persp.get_fov()) * .5))

        if from_lens_type == "persp":
            return max(.0004, min(100000., -zoom * tan * 2. / 285.))
        else:
            near = lens_persp.get_near()
            return min(-near, max(-1000000., -zoom * 285. * .5 / tan))

    def update(self):

        lens = self.lens
        lens_type = self.lens_type
        self._camera.reparent_to(self.origin)
        self._node.set_lens(lens)
        self._gizmo_cam.node().set_lens(lens)
        self._projector.node().set_lens(self._projector_lenses[lens_type])
        Mgr.update_app("lens_type", lens_type)

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
        self._mask = BitMask32.bit(12)
        self._pixel_color = VBase4()

        Mgr.expose("picking_mask", lambda: self._mask)
        Mgr.expose("pixel_under_mouse", lambda: VBase4(self._pixel_color))
        Mgr.add_app_updater("viewport", self.__update_frustum)

    def setup(self):

        base = Mgr.get("base")
        self._tex = Texture("picking_texture")
        props = FrameBufferProperties()
        props.set_rgba_bits(8, 8, 8, 8)
        props.set_depth_bits(16)
        self._buffer = bfr = base.win.make_texture_buffer("picking_buffer",
                                                          16, 16,
                                                          self._tex,
                                                          to_ram=True,
                                                          fbp=props)

        bfr.set_clear_color(VBase4())
        bfr.set_clear_color_active(True)
        self._np = base.make_camera(bfr)
        node = self._np.node()
        lens_persp = node.get_lens()
        lens_persp.set_fov(1.5)
        lens_ortho = OrthographicLens()
        lens_ortho.set_film_size(11.25)
        lens_ortho.set_near(-100000.)
        self._lenses = {"persp": lens_persp, "ortho": lens_ortho}
        node.set_camera_mask(self._mask)
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
        gizmo_cam_mask = BitMask32.bit(13)
        gizmo_cam_node = Camera("gizmo_cam")
        gizmo_cam_node.set_camera_mask(gizmo_cam_mask)
        gizmo_cam_node.set_lens(lens_persp)
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

    def __update_frustum(self):

        w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "main" else "size"]
        s = 800. / max(w, h)
        self._lenses["persp"].set_fov(1.5 * s)
        self._lenses["ortho"].set_film_size(11.25 * s)

    def __adjust_to_lens(self):

        lens_type = self.cam.lens_type
        lens = self._lenses[lens_type]
        node = self._np.node()
        node.set_lens(lens)
        gizmo_cam_node = self._gizmo_cam.node()
        gizmo_cam_node.set_lens(lens)

        if lens_type == "persp":
            self._np.set_pos(0., 0., 0.)
        else:
            self._np.set_hpr(0., 0., 0.)

    def set_active(self, is_active=True):

        self._buffer.set_active(is_active)
        self._np.node().set_active(is_active)
        Mgr.remove_task("get_pixel_under_mouse")

        if is_active:
            Mgr.add_task(self.__get_pixel_under_mouse, "get_pixel_under_mouse", sort=0)
        else:
            self._pixel_color = VBase4()

    def __get_pixel_under_mouse(self, task):

        if not self.mouse_watcher.is_mouse_open():
            self._buffer.set_active(False)
            self._np.node().set_active(False)
            self._pixel_color = VBase4()
            return task.cont

        if not self._np.node().is_active():
            self._buffer.set_active(True)
            self._np.node().set_active(True)

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

        base = Mgr.get("base")
        self._tex = Texture("aux_picking_texture")
        self._tex_peeker = None
        props = FrameBufferProperties()
        props.set_rgba_bits(8, 8, 8, 8)
        props.set_depth_bits(16)
        self._buffer = bfr = base.win.make_texture_buffer("aux_picking_buffer",
                                                          1, 1,
                                                          self._tex,
                                                          to_ram=True,
                                                          fbp=props)

        bfr.set_active(False)
        bfr.set_clear_color(VBase4())
        bfr.set_clear_color_active(True)
        self._np = base.make_camera(bfr)
        node = self._np.node()
        self._lens = lens = OrthographicLens()
        lens.set_film_size(.75)
        lens.set_near(0.)
        node.set_lens(lens)
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

        Mgr.add_app_updater("viewport", self.__update_frustum)

    def setup(self):

        self._np.reparent_to(Mgr.get("aux_picking_root"))

        return True

    def __update_frustum(self):

        w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "main" else "size"]
        self._lens.set_film_size(.75 * 800. / max(w, h))

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

        self._buffer.set_active(is_active)
        self._np.node().set_active(is_active)
        Mgr.remove_task("get_aux_pixel_under_mouse")

        if is_active:
            Mgr.add_task(self.__get_pixel_under_mouse, "get_aux_pixel_under_mouse", sort=0)
        else:
            self._pixel_color = VBase4()

    def __get_pixel_under_mouse(self, task):

        if not self.mouse_watcher.is_mouse_open():
            self._buffer.set_active(False)
            self._np.node().set_active(False)
            return task.cont

        if not self._np.node().is_active():
            self._buffer.set_active(True)
            self._np.node().set_active(True)

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
