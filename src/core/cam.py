from .base import *


class MainCamera:

    def __init__(self):

        GD.cam = self

        showbase = GD.showbase
        self._mask = mask = next(camera_mask)
        self._node = showbase.camNode
        self._node.camera_mask = mask

        lens_persp = showbase.camLens
        lens_ortho = OrthographicLens()
        size_h, size_v = lens_persp.film_size
        lens_ortho.film_size = (285., 285. * size_v / size_h)
        lens_ortho.near = -100000.

        self._pivots = {}
        self._targets = {}
        self._origins = {}
        self._lens_types = {}
        self._lenses = {"persp": lens_persp, "ortho": lens_ortho}

        self._cam_np = showbase.cam
        self._camera = camera = showbase.camera
        default_light = Mgr.get("default_light")
        default_light.reparent_to(camera)

        # A separate LensNode projects the selection texture onto selected polygons

        self.projector_lenses = lenses = {"persp": PerspectiveLens(), "ortho": OrthographicLens()}
        projector_node = LensNode("projector", lenses["persp"])
        self.projector = self._cam_np.attach_new_node(projector_node)

        Mgr.expose("render_mask", lambda: self._mask)
        Mgr.expose("cam", lambda: self)

        # Create a secondary camera and DisplayRegion to render gizmos on top of the
        # 3D scene.

        dr = GD.window.make_display_region()
        GD["viewport"]["display_regions"].append(dr)
        dr.sort = 1
        gizmo_cam_mask = next(camera_mask)
        gizmo_cam_node = Camera("gizmo_cam")
        gizmo_cam_node.camera_mask = gizmo_cam_mask
        gizmo_cam_node.set_lens(lens_persp)
        gizmo_cam = Mgr.get("gizmo_root").attach_new_node(gizmo_cam_node)
        gizmo_cam.set_effect(CompassEffect.make(camera, CompassEffect.P_all))
        dr.camera = gizmo_cam
        dr.set_clear_color_active(False)
        dr.set_clear_depth_active(True)
        self._gizmo_cam = gizmo_cam
        Mgr.expose("gizmo_render_mask", lambda: gizmo_cam_mask)
        Mgr.expose("gizmo_cam", lambda: gizmo_cam)
        Mgr.add_app_updater("viewport", self.__handle_viewport_resize)

    def __call__(self):

        return self._cam_np

    def setup(self):

        if "grid_ok" not in MainObjects.get_setup_results():
            return False

        GD["view"] = "ortho"
        Mgr.update_app("view", "set", "persp")

        return "main_camera_ok"

    def __update_lens_aspect_ratio(self, w, h):

        lens_persp = self._lenses["persp"]
        fov_h, fov_v = lens_persp.fov

        if h > w:
            fov_v = max(fov_h, fov_v)
            tan = math.tan(math.radians(fov_v * .5))
            fov_h = 2. * math.degrees(math.atan(tan * w / h))
        else:
            fov_h = max(fov_h, fov_v)
            tan = math.tan(math.radians(fov_h * .5))
            fov_v = 2. * math.degrees(math.atan(tan * h / w))

        lens_persp.fov = (fov_h, fov_v)
        lens_ortho = self._lenses["ortho"]
        size_h, size_v = lens_ortho.film_size

        if h > w:
            size_v = max(size_h, size_v)
            size_h = size_v * w / h
        else:
            size_h = max(size_h, size_v)
            size_v = size_h * h / w

        lens_ortho.film_size = (size_h, size_v)

    def __handle_viewport_resize(self):

        w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
        self.__update_lens_aspect_ratio(w, h)
        GD.viewport_origin.set_scale(2. / w, 1., 2. / h)

    @property
    def origin(self):

        return self._origins[GD["view"]]

    @property
    def lens_type(self):

        return self._lens_types[GD["view"]]

    @lens_type.setter
    def lens_type(self, lens_type):

        self._lens_types[GD["view"]] = lens_type
        self.target.set_scale(1.) if lens_type == "persp" else self.origin.set_y(-500.)

    @property
    def lens(self):

        return self._lenses[self.lens_type]

    @property
    def target(self):

        return self._targets[GD["view"]]

    @property
    def pivot(self):

        return self._pivots[GD["view"]]

    @property
    def zoom(self):

        return self.origin.get_y() if self.lens_type == "persp" else self.target.get_sx()

    @zoom.setter
    def zoom(self, zoom):

        self.origin.set_y(zoom) if self.lens_type == "persp" else self.target.set_scale(zoom)

    @property
    def pivot_positions(self):

        pos = {}

        for view_id, pivot in self._pivots.items():
            pos[view_id] = pivot.get_pos()

        return pos

    @pivot_positions.setter
    def pivot_positions(self, positions):

        pivots = self._pivots

        for view_id, pos in positions.items():
            pivots[view_id].set_pos(pos)

    @property
    def pivot_hprs(self):

        hprs = {}

        for view_id, pivot in self._pivots.items():
            hprs[view_id] = pivot.get_hpr()

        return hprs

    @pivot_hprs.setter
    def pivot_hprs(self, hprs):

        pivots = self._pivots

        for view_id, hpr in hprs.items():
            pivots[view_id].set_hpr(hpr)

    @property
    def target_hprs(self):

        hprs = {}

        for view_id, target in self._targets.items():
            hprs[view_id] = target.get_hpr()

        return hprs

    @target_hprs.setter
    def target_hprs(self, hprs):

        targets = self._targets

        for view_id, hpr in hprs.items():
            targets[view_id].set_hpr(hpr)

    @property
    def zooms(self):

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

    @zooms.setter
    def zooms(self, zooms):

        lens_types = self._lens_types
        targets = self._targets
        origs = self._origins

        for view_id, zoom in zooms.items():
            if lens_types[view_id] == "persp":
                origs[view_id].set_y(zoom)
            else:
                targets[view_id].set_scale(zoom)

    def add_rig(self, view_id, front_hpr, pos, hpr, lens_type, zoom):

        pivot = GD.world.attach_new_node(f"camera_pivot_{view_id}")
        pivot.set_pos(pos)
        pivot.set_hpr(front_hpr)
        self._pivots[view_id] = pivot
        target = pivot.attach_new_node(f"camera_target_{view_id}")
        target.set_hpr(hpr)
        self._targets[view_id] = target
        orig = target.attach_new_node(f"camera_origin_{view_id}")
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
        tan = math.tan(math.radians(max(lens_persp.fov) * .5))

        if from_lens_type == "persp":
            return max(.0004, min(100000., -zoom * tan * 2. / 285.))
        else:
            near = lens_persp.near
            return min(-near, max(-1000000., -zoom * 285. * .5 / tan))

    def update(self):

        lens = self.lens
        lens_type = self.lens_type
        self._camera.reparent_to(self.origin)
        self._node.set_lens(lens)
        self._gizmo_cam.node().set_lens(lens)
        self.projector.node().set_lens(self.projector_lenses[lens_type])
        Mgr.update_app("lens_type", lens_type)
        Mgr.notify("lens_type_changed", lens_type)


class PickingCamera:

    def __init__(self):

        self._tex = None
        self._tex_peeker = None
        self._buffer = None
        self._np = None
        self._lenses = {}
        self._focal_length = 1.
        self._film_scale = 1.
        mask = next(camera_mask)
        self._masks = [mask]
        alt_masks = [next(camera_mask) for _ in range(2)]
        self._masks.extend(alt_masks)
        comb_mask = mask

        for alt_mask in alt_masks:
            comb_mask = comb_mask | alt_mask

        self._combined_mask = comb_mask
        self._pixel_color = VBase4()
        self._transformer = None

        Mgr.expose("picking_mask", lambda index=0: self._masks[index])
        Mgr.expose("picking_masks", lambda: self._combined_mask)
        Mgr.expose("pixel_under_mouse", lambda: VBase4(self._pixel_color))
        Mgr.add_app_updater("viewport", self.__update_frustum)

    def __call__(self):

        return self._np

    def setup(self):

        self._tex = Texture("picking_texture")
        props = FrameBufferProperties()
        props.set_rgba_bits(8, 8, 8, 8)
        props.set_depth_bits(16)
        self._buffer = bfr = GD.window.make_texture_buffer("picking_buffer",
                                                           15, 15,
                                                           self._tex,
                                                           to_ram=True,
                                                           fbp=props)
        bfr.clear_color = (0., 0., 0., 0.)
        bfr.set_clear_color_active(True)
        self._np = GD.showbase.make_camera(bfr)
        node = self._np.node()
        lens_persp = node.get_lens()
        lens_persp.fov = 1.5
        self._focal_length = lens_persp.focal_length
        lens_ortho = OrthographicLens()
        lens_ortho.film_size = 11.25
        lens_ortho.near = -100000.
        self._lenses = {"persp": lens_persp, "ortho": lens_ortho}
        node.camera_mask = self._masks[0]
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
        node.initial_state = state

        # For rendering BasicGeoms as pickable geometry
        node.tag_state_key = "picking_color"
        Mgr.accept("set_basic_geom_picking_color", node.set_tag_state)
        Mgr.accept("clear_basic_geom_picking_color", node.clear_tag_state)

        # Create a secondary camera and DisplayRegion to render gizmos on top of the
        # 3D scene.

        dr = bfr.make_display_region()
        dr.sort = 1
        gizmo_cam_mask = next(camera_mask)
        gizmo_cam_node = Camera("gizmo_cam")
        gizmo_cam_node.camera_mask = gizmo_cam_mask
        gizmo_cam_node.set_lens(lens_persp)
        gizmo_cam_node.initial_state = state
        gizmo_cam = Mgr.get("gizmo_cam").attach_new_node(gizmo_cam_node)
        gizmo_cam.set_effect(CompassEffect.make(self._np, CompassEffect.P_all))
        dr.camera = gizmo_cam
        dr.set_clear_color_active(False)
        dr.set_clear_depth_active(True)
        self._gizmo_cam = gizmo_cam
        Mgr.expose("gizmo_picking_cam", lambda: gizmo_cam)
        Mgr.expose("gizmo_picking_mask", lambda: gizmo_cam_mask)

        Mgr.add_task(self.__get_pixel_under_mouse, "get_pixel_under_mouse", sort=0)

        return "picking_camera_ok"

    def set_mask(self, index):

        self._np.node().camera_mask = self._masks[index]

    def set_film_scale(self, scale):

        self._film_scale = scale
        self.__update_frustum()

    def __update_frustum(self):

        w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
        s = 800. / max(w, h) * self._film_scale
        lens = self._lenses["persp"]
        self._lenses["persp"].film_size = s
        self._lenses["persp"].focal_length = self._focal_length
        self._lenses["ortho"].film_size = 11.25 * s

    def adjust_to_lens(self):

        lens_type = GD.cam.lens_type
        lens = self._lenses[lens_type]
        self._np.node().set_lens(lens)
        self._gizmo_cam.node().set_lens(lens)

        if lens_type == "persp":
            self._np.set_pos(0., 0., 0.)
        else:
            self._np.set_hpr(0., 0., 0.)

    def set_transformer(self, transformer):
        """
        This method is used to change the way this camera is transformed (specifically
        in __get_pixel_under_mouse).
        The callable passed in for transformer must take one argument: the Camera used
        by this class.
        Pass in None for transformer to restore the default transformation behavior.

        """

        self._transformer = transformer

    @property
    def active(self):

        return self._np.node().active

    @active.setter
    def active(self, active):

        self._buffer.active = active
        self._np.node().active = active
        Mgr.remove_task("get_pixel_under_mouse")

        if active:
            Mgr.add_task(self.__get_pixel_under_mouse, "get_pixel_under_mouse", sort=0)
        else:
            self._pixel_color = VBase4()

    def __get_pixel_under_mouse(self, task):

        if not GD.mouse_watcher.is_mouse_open():
            self._buffer.active = False
            self._np.node().active = False
            self._pixel_color = VBase4()
            return task.cont

        if not self._np.node().active:
            self._buffer.active = True
            self._np.node().active = True

        if self._transformer:

            self._transformer(self._np)

        else:

            screen_pos = GD.mouse_watcher.get_mouse()
            far_point = Point3()
            GD.cam.lens.extrude(screen_pos, Point3(), far_point)

            if GD.cam.lens_type == "persp":
                self._np.look_at(far_point)
            else:
                far_point.y = 0.
                self._np.set_pos(far_point)

        if self._tex_peeker:
            self._tex_peeker.lookup(self._pixel_color, .5, .5)
        else:
            self._tex_peeker = self._tex.peek()

        return task.cont


# the following camera is used to detect temporary geometry created to allow subobject
# picking via polygon
class AuxiliaryPickingCamera:

    def __init__(self):

        self._pixel_color = VBase4()
        Mgr.expose("aux_pixel_under_mouse", lambda: VBase4(self._pixel_color))

        self._tex = Texture("aux_picking_texture")
        self._tex_peeker = None
        props = FrameBufferProperties()
        props.set_rgba_bits(8, 8, 8, 8)
        props.set_depth_bits(16)
        self._buffer = bfr = GD.window.make_texture_buffer("aux_picking_buffer",
                                                           1, 1,
                                                           self._tex,
                                                           to_ram=True,
                                                           fbp=props)

        bfr.active = False
        bfr.clear_color = (0., 0., 0., 0.)
        bfr.set_clear_color_active(True)
        self._np = GD.showbase.make_camera(bfr)
        node = self._np.node()
        self._lens = lens = OrthographicLens()
        lens.film_size = .75
        lens.near = 0.
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
        node.initial_state = state
        node.active = False

        self._plane = None

        Mgr.add_app_updater("viewport", self.__update_frustum)

    def setup(self):

        self._np.reparent_to(Mgr.get("aux_picking_root"))

        return True

    @property
    def origin(self):

        return self._np

    def __update_frustum(self):

        w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
        self._lens.film_size = .75 * 800. / max(w, h)

    def set_plane(self, plane):

        self._plane = plane

    def update_pos(self):

        if not GD.mouse_watcher.has_mouse():
            return

        cam = GD.cam()
        screen_pos = GD.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.world.get_relative_point(cam, point)
        point = Point3()
        self._plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))
        self._np.set_pos(point)

    @property
    def active(self):

        return self._np.node().active

    @active.setter
    def active(self, active):

        self._buffer.active = active
        self._np.node().active = active
        Mgr.remove_task("get_aux_pixel_under_mouse")

        if active:
            Mgr.add_task(self.__get_pixel_under_mouse, "get_aux_pixel_under_mouse", sort=0)
        else:
            self._pixel_color = VBase4()

    def __get_pixel_under_mouse(self, task):

        if not GD.mouse_watcher.is_mouse_open():
            self._buffer.active = False
            self._np.node().active = False
            return task.cont

        if not self._np.node().active:
            self._buffer.active = True
            self._np.node().active = True

        cam = GD.cam()
        screen_pos = GD.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.world.get_relative_point(cam, point)
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
