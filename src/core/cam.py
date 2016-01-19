from .base import *


class MainCamera(BaseObject):

    def __init__(self):

        BaseObject.__init__(self)

        self._target = None
        self._zoom_indicator = None
        self._zoom_indicator_dot = None
        self._mask = BitMask32.bit(20)

        self.expose("node_path", lambda: self.cam)
        self.expose("node", lambda: self.cam_node)
        self.expose("lens", lambda: self.cam_lens)
        self.expose("target", lambda: self._target)
        self.expose("zoom_indic_dot", lambda: self._zoom_indicator_dot)
        Mgr.expose("render_mask", lambda: self._mask)
        Mgr.expose("cam", lambda: self)
        Mgr.accept("reset_cam_transform", self.__reset_transform)

        # Create a secondary camera and DisplayRegion to render gizmos on top of the
        # 3D scene.

        dr = Mgr.get("core").win.make_display_region()
        dr.set_sort(1)
        gizmo_cam_mask = BitMask32.bit(22)
        gizmo_cam_node = Camera("gizmo_cam")
        gizmo_cam_node.set_camera_mask(gizmo_cam_mask)
        gizmo_cam_node.set_lens(self.cam_lens)
        gizmo_cam_node.set_scene(Mgr.get("gizmo_root"))
        gizmo_cam = self.cam.attach_new_node(gizmo_cam_node)
        dr.set_camera(gizmo_cam)
        dr.set_clear_color_active(False)
        dr.set_clear_depth_active(True)
        Mgr.expose("gizmo_render_mask", lambda: gizmo_cam_mask)
        Mgr.expose("gizmo_cam", lambda: gizmo_cam)

    def setup(self):

        default_light = Mgr.get("default_light")

        if default_light is None:
            return

        self._target = self.world.attach_new_node("camera_target")
        self._target.set_hpr(-45., -45., 0.)
        self.cam.reparent_to(self._target)

        default_light.reparent_to(self.cam)

        self.cam.set_y(-400.)
        self.cam_node.set_camera_mask(self._mask)

        self._zoom_indicator = self.screen.attach_new_node("zoom_indicator")
        cm = CardMaker("zoom_indicator_part")
        cm.set_frame(-.0533333, .0533333, -.0533333, .0533333)
        cm.set_has_normals(False)
        zoom_indicator_ring = self._zoom_indicator.attach_new_node(
            cm.generate())
        zoom_indicator_ring.set_texture(
            Mgr.load_tex(GFX_PATH + "zoom_indic_ring.png"))
        zoom_indicator_ring.set_transparency(TransparencyAttrib.M_alpha)
        zoom_indicator_ring.set_alpha_scale(.5)
        self._zoom_indicator_dot = self._zoom_indicator.attach_new_node(
            cm.generate())
        self._zoom_indicator_dot.set_texture(
            Mgr.load_tex(GFX_PATH + "zoom_indic_dot.png"))
        self._zoom_indicator_dot.set_transparency(TransparencyAttrib.M_alpha)
        self._zoom_indicator_dot.set_alpha_scale(.5)
        self._zoom_indicator_dot.set_scale((1. / -self.cam.get_y()) ** .2)

        return "main_camera_ok"

    def __reset_transform(self):

        self._target.set_pos_hpr(0., 0., 0., -45., -45., 0.)
        self.cam.set_y(-400.)
        zoom_indic_dot = self._zoom_indicator_dot
        zoom_indic_dot.set_scale((1. / -self.cam.get_y()) ** .2)


class PickingCamera(BaseObject):

    def __init__(self):

        BaseObject.__init__(self)

        self._tex = None
        self._img = None
        self._buffer = None
        self._np = None
        self._mask = BitMask32.bit(21)
        self._pixel_color = VBase4()

        Mgr.expose("picking_mask", lambda: self._mask)
        Mgr.expose("pixel_under_mouse", lambda: self._pixel_color)

    def setup(self):

        core = Mgr.get("core")
        self._tex = Texture("picking_texture")
        self._img = PNMImage(1, 1)
        props = FrameBufferProperties()
        props.set_float_color(True)
        props.set_alpha_bits(32)
        props.set_depth_bits(32)
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
        lens = node.get_lens()
        lens.set_fov(1.)
        cull_bounds = lens.make_bounds()
        lens.set_fov(.1)
        node.set_cull_bounds(cull_bounds)
        node.set_camera_mask(self._mask)
        Mgr.expose("picking_cam", lambda: self)

        state_np = NodePath("flat_color_state")
        state_np.set_texture_off(1)
        state_np.set_material_off(1)
        state_np.set_shader_off(1)
        state_np.set_light_off(1)
        state_np.set_color_off(1)
        state_np.set_color_scale_off(1)
        state_np.set_render_mode_thickness(5, 1)
        state_np.set_transparency(TransparencyAttrib.M_none, 1)
        state = state_np.get_state()
        node.set_initial_state(state)

        # Create a secondary camera and DisplayRegion to render gizmos on top of the
        # 3D scene.

        dr = self._buffer.make_display_region()
        dr.set_sort(1)
        gizmo_cam_mask = BitMask32.bit(23)
        gizmo_cam_node = Camera("gizmo_cam")
        gizmo_cam_node.set_camera_mask(gizmo_cam_mask)
        gizmo_cam_node.set_lens(lens)
        gizmo_cam_node.set_cull_bounds(cull_bounds)
        gizmo_cam_node.set_scene(Mgr.get("gizmo_root"))
        gizmo_cam_node.set_initial_state(state)
        gizmo_cam = self._np.attach_new_node(gizmo_cam_node)
        dr.set_camera(gizmo_cam)
        dr.set_clear_color_active(False)
        dr.set_clear_depth_active(True)
        Mgr.expose("gizmo_picking_mask", lambda: gizmo_cam_mask)

        Mgr.add_task(self.__check_pixel, "get_pixel_under_mouse", sort=0)

        return "picking_camera_ok"

    def set_active(self, is_active=True):

        if self._np.node().is_active() == is_active:
            return

        self._np.node().set_active(is_active)

        if is_active:
            Mgr.add_task(self.__check_pixel, "get_pixel_under_mouse", sort=0)
        else:
            Mgr.remove_task("get_pixel_under_mouse")
            self._pixel_color = VBase4()

    def __check_pixel(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        screen_pos = self.mouse_watcher.get_mouse()
        far_point = Point3()
        self.cam_lens.extrude(screen_pos, Point3(), far_point)
        self._np.look_at(far_point)
        self._tex.store(self._img)
        self._pixel_color = self._img.get_xel_a(0, 0)

        return task.cont


class NavigationManager(BaseObject):

    def __init__(self):

        self._cam_target = None
        self._zoom_indic_dot = None
        self._near = None
        self._pan_start_pos = Point3()
        self._orbit_start_pos = Point2()
        self._zoom_start_pos = ()
        self._dolly_dir = 0.
        self._dolly_accel = 0.

        self._clock = ClockObject()

    def setup(self):

        if "main_camera_ok" not in MainObjects.get_setup_results():
            return

        self._cam_target = Mgr.get(("cam", "target"))
        self._zoom_indic_dot = Mgr.get(("cam", "zoom_indic_dot"))
        self._near = self.cam_lens.get_near()
        self._nav_states = ("panning", "orbiting", "zooming", "dollying_forward",
                            "dollying_backward")

        add_state = Mgr.add_state
        add_state("navigation_mode", -100, self.__enter_navigation_mode,
                  self.__exit_navigation_mode)

        for state_id in self._nav_states:
            add_state(state_id, -110)

        def start_panning():

            Mgr.enter_state("panning")
            self.__init_pan()

        def start_orbiting():

            Mgr.enter_state("orbiting")
            self.__init_orbit()

        def start_zooming():

            Mgr.enter_state("zooming")
            self.__init_zoom()

        def start_dollying(direction):

            Mgr.enter_state("dollying_%s" %
                            ("forward" if direction == 1. else "backward"))
            self.__init_dolly(direction)

        def end_cam_transform():

            Mgr.enter_state("navigation_mode")
            self.__end_cam_transform()

        bind = Mgr.bind_state
        bind("navigation_mode", "navigate -> pan", "mouse3", start_panning)
        bind("panning", "end navigation", "space-up", self.__quit_navigation_mode)
        bind("panning", "pan -> navigate", "mouse3-up", end_cam_transform)
        bind("panning", "pan -> zoom", "mouse1", start_zooming)
        bind("navigation_mode", "navigate -> orbit", "mouse1", start_orbiting)
        bind("orbiting", "end navigation",
             "space-up", self.__quit_navigation_mode)
        bind("orbiting", "orbit -> navigate", "mouse1-up", end_cam_transform)
        bind("orbiting", "orbit -> zoom", "mouse3", start_zooming)
        bind("zooming", "end navigation", "space-up", self.__quit_navigation_mode)
        bind("zooming", "zoom -> pan", "mouse1-up", start_panning)
        bind("zooming", "zoom -> orbit", "mouse3-up", start_orbiting)
        bind("navigation_mode", "navigate -> dolly forward", "arrow_up",
             lambda: start_dollying(1.))
        bind("navigation_mode", "navigate -> dolly backward", "arrow_down",
             lambda: start_dollying(-1.))
        mod_shift = Mgr.get("mod_shift")
        mod_ctrl = Mgr.get("mod_ctrl")
        bind("navigation_mode", "navigate -> dolly forward accel",
             "%d|arrow_up" % mod_shift, lambda: start_dollying(1.))
        bind("navigation_mode", "navigate -> dolly backward accel",
             "%d|arrow_down" % mod_shift, lambda: start_dollying(-1.))
        bind("navigation_mode", "navigate -> dolly forward decel",
             "%d|arrow_up" % mod_ctrl, lambda: start_dollying(1.))
        bind("navigation_mode", "navigate -> dolly backward decel",
             "%d|arrow_down" % mod_ctrl, lambda: start_dollying(-1.))
        bind("dollying_forward", "end navigation",
             "space-up", self.__quit_navigation_mode)
        bind("dollying_forward", "dolly forward -> navigate",
             "arrow_up-up", end_cam_transform)
        bind("dollying_forward", "dolly forward -> dolly backward", "arrow_down",
             lambda: start_dollying(-1.))
        bind("dollying_forward", "dolly forward -> dolly backward accel",
             "%d|arrow_down" % mod_shift, lambda: start_dollying(-1.))
        bind("dollying_forward", "dolly forward -> dolly backward decel",
             "%d|arrow_down" % mod_ctrl, lambda: start_dollying(-1.))
        bind("dollying_backward", "end navigation",
             "space-up", self.__quit_navigation_mode)
        bind("dollying_backward", "dolly backward -> navigate",
             "arrow_down-up", end_cam_transform)
        bind("dollying_backward", "dolly backward -> dolly forward", "arrow_up",
             lambda: start_dollying(1.))
        bind("dollying_backward", "dolly backward -> dolly forward accel",
             "%d|arrow_up" % mod_shift, lambda: start_dollying(1.))
        bind("dollying_backward", "dolly backward -> dolly forward decel",
             "%d|arrow_up" % mod_ctrl, lambda: start_dollying(1.))
        bind("navigation_mode", "reset view", "home", self.__reset_view)
        bind("navigation_mode", "target object", "t", self.__target_object)
        bind("navigation_mode", "zoom in", "wheel_up", self.__zoom_step_in)
        bind("navigation_mode", "zoom out", "wheel_down", self.__zoom_step_out)
        bind("navigation_mode", "check navigation done", "space-up",
             self.__determine_navigation_end)

        status_data = Mgr.get_global("status_data")
        mode_text = "Navigate"
        info_text = "LMB to orbit; RMB to pan; LMB+RMB to zoom; <Home> to reset view;" \
            " <space-up> to end"
        status_data["navigate"] = {"mode": mode_text, "info": info_text}

        return "navigation_ok"

    def __enter_navigation_mode(self, prev_state_id, is_active):

        if not is_active:
            self._clock.reset()
            Mgr.do("start_updating_world_axes")
            Mgr.do("start_updating_nav_gizmo")

        Mgr.update_app("status", "navigate")

    def __exit_navigation_mode(self, next_state_id, is_active):

        if not is_active:
            Mgr.do("stop_updating_world_axes")
            Mgr.do("stop_updating_nav_gizmo")
            Mgr.remove_task("transform_cam")

    def __determine_navigation_end(self):

        if self._clock.get_real_time() >= .5:
            Mgr.exit_state("navigation_mode")
        else:
            Mgr.activate_bindings(["end navigation"])

    def __quit_navigation_mode(self):

        state_id = Mgr.get_state_id()

        if state_id != "navigation_mode":
            Mgr.exit_state(state_id)

        Mgr.exit_state("navigation_mode")

    def __reset_view(self):

        Mgr.do("reset_cam_transform")
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")

    def __target_object(self):

        pixel_color = Mgr.get("pixel_under_mouse")
        obj = Mgr.get("object", pixel_color=pixel_color)

        if obj:

            self._cam_target.set_pos(obj.get_origin().get_pos(self.world))
            Mgr.do("update_transf_gizmo")
            Mgr.do("update_coord_sys")

        else:

            selection = Mgr.get("selection")

            if selection:
                self._cam_target.set_pos(selection.get_center_pos())
                Mgr.do("update_transf_gizmo")
                Mgr.do("update_coord_sys")

    def __end_cam_transform(self):

        Mgr.remove_task("transform_cam")
        self._dolly_accel = 1.

    def __zoom_step_in(self):

        y = self.cam.get_y()
        new_y = min(-self._near, y + (-y * .5) ** .75)
        self.cam.set_y(new_y)
        self._zoom_indic_dot.set_scale((1. / -new_y) ** .2)
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")

    def __zoom_step_out(self):

        y = self.cam.get_y()
        new_y = max(-10000., y - (-y * .5) ** .75)
        self.cam.set_y(new_y)
        self._zoom_indic_dot.set_scale((1. / -new_y) ** .2)
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")

    def __init_pan(self):

        Mgr.remove_task("transform_cam")

        if not self.mouse_watcher.has_mouse():
            return

        self.__get_pan_pos(self._pan_start_pos)
        Mgr.add_task(self.__pan, "transform_cam", sort=2)

    def __pan(self, task):

        pan_pos = Point3()

        if not self.__get_pan_pos(pan_pos):
            return task.cont

        self._cam_target.set_pos(
            self._cam_target.get_pos() + (self._pan_start_pos - pan_pos))
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")

        return task.cont

    def __get_pan_pos(self, pos):

        if not self.mouse_watcher.has_mouse():
            return False

        target = self._cam_target
        target_pos = target.get_pos()
        normal = self.world.get_relative_vector(target, Vec3(0., 1., 0.))
        plane = Plane(normal, target_pos)
        m_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        self.cam_lens.extrude(m_pos, near_point, far_point)
        near_point = self.world.get_relative_point(self.cam, near_point)
        far_point = self.world.get_relative_point(self.cam, far_point)
        plane.intersects_line(pos, near_point, far_point)

        return True

    def __init_orbit(self):

        Mgr.remove_task("transform_cam")

        if not self.mouse_watcher.has_mouse():
            return

        self._orbit_start_pos = Point2(self.mouse_watcher.get_mouse())
        Mgr.add_task(self.__orbit, "transform_cam", sort=2)

    def __orbit(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        orbit_pos = self.mouse_watcher.get_mouse()
        d_heading, d_pitch = (orbit_pos - self._orbit_start_pos) * 100.
        self._orbit_start_pos = Point2(orbit_pos)
        target = self._cam_target
        target.set_hpr(target.get_h() - d_heading,
                       target.get_p() + d_pitch, 0.)
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")

        return task.cont

    def __init_zoom(self):

        Mgr.remove_task("transform_cam")

        if not self.mouse_watcher.has_mouse():
            return

        self._zoom_start_pos = (
            self.cam.get_y(), self.mouse_watcher.get_mouse_y())
        Mgr.add_task(self.__zoom, "transform_cam", sort=2)

    def __zoom(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        zoom_pos = self.mouse_watcher.get_mouse_y()
        target_start_pos, mouse_start_pos = self._zoom_start_pos
        dist = zoom_pos - mouse_start_pos

        if dist < 0.:
            dist = (target_start_pos * dist * 10.) ** .75
            new_y = max(-10000., target_start_pos - dist)
        else:
            dist = (target_start_pos * dist * -10.) ** .75
            new_y = min(-self._near, target_start_pos + dist)

        self.cam.set_y(new_y)
        self._zoom_indic_dot.set_scale((1. / -new_y) ** .2)
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")

        return task.cont

    def __init_dolly(self, direction):

        self._dolly_dir = direction
        Mgr.remove_task("transform_cam")
        Mgr.add_task(self.__dolly, "transform_cam", sort=2)

    def __dolly(self, task):

        if Mgr.get_global("ctrl_down"):
            self._dolly_accel = max(.1, self._dolly_accel - .01)

        if Mgr.get_global("shift_down"):
            self._dolly_accel = min(5., self._dolly_accel + .01)

        self._cam_target.set_y(
            self._cam_target, self._dolly_dir * self._dolly_accel)
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")

        return task.cont


MainObjects.add_class(MainCamera)
MainObjects.add_class(PickingCamera)
MainObjects.add_class(NavigationManager)
