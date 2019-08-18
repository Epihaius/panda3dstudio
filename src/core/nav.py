from .base import *


class NavigationManager:

    def __init__(self):

        self._near = None
        self._pan_start_pos = Point3()
        self._orbit_start_pos = Point2()
        self._zoom_start = ()
        self._dolly_dir = 0.
        self._dolly_accel = 0.

        self._clock = ClockObject()

    def setup(self):

        if "views_ok" not in MainObjects.get_setup_results():
            return False

        self._near = GD.cam.lens.near
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

            Mgr.enter_state(f'dollying_{"forward" if direction == 1. else "backward"}')
            self.__init_dolly(direction)

        def end_cam_transform():

            if GD["coord_sys_type"] == "view":
                Mgr.get("selection").update_transform_values()

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
        mod_key_codes = GD["mod_key_codes"]
        mod_shift = mod_key_codes["shift"]
        mod_ctrl = mod_key_codes["ctrl"]
        bind("navigation_mode", "navigate -> dolly forward accel",
             f"{mod_shift}|arrow_up", lambda: start_dollying(1.))
        bind("navigation_mode", "navigate -> dolly backward accel",
             f"{mod_shift}|arrow_down", lambda: start_dollying(-1.))
        bind("navigation_mode", "navigate -> dolly forward decel",
             f"{mod_ctrl}|arrow_up", lambda: start_dollying(1.))
        bind("navigation_mode", "navigate -> dolly backward decel",
             f"{mod_ctrl}|arrow_down", lambda: start_dollying(-1.))
        bind("dollying_forward", "end navigation",
             "space-up", self.__quit_navigation_mode)
        bind("dollying_forward", "dolly forward -> navigate",
             "arrow_up-up", end_cam_transform)
        bind("dollying_forward", "dolly forward -> dolly backward", "arrow_down",
             lambda: start_dollying(-1.))
        bind("dollying_forward", "dolly forward -> dolly backward accel",
             f"{mod_shift}|arrow_down", lambda: start_dollying(-1.))
        bind("dollying_forward", "dolly forward -> dolly backward decel",
             f"{mod_ctrl}|arrow_down", lambda: start_dollying(-1.))
        bind("dollying_backward", "end navigation",
             "space-up", self.__quit_navigation_mode)
        bind("dollying_backward", "dolly backward -> navigate",
             "arrow_down-up", end_cam_transform)
        bind("dollying_backward", "dolly backward -> dolly forward", "arrow_up",
             lambda: start_dollying(1.))
        bind("dollying_backward", "dolly backward -> dolly forward accel",
             f"{mod_shift}|arrow_up", lambda: start_dollying(1.))
        bind("dollying_backward", "dolly backward -> dolly forward decel",
             f"{mod_ctrl}|arrow_up", lambda: start_dollying(1.))
        bind("navigation_mode", "zoom in", "wheel_up", self.__zoom_step_in)
        bind("navigation_mode", "zoom out", "wheel_down", self.__zoom_step_out)
        bind("navigation_mode", "check navigation done", "space-up",
             self.__determine_navigation_end)
        bind("navigation_mode", "navigate -> center view on objects", "c",
             lambda: Mgr.do("center_view_on_objects"))
        bind("navigation_mode", "navigation ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))

        status_data = GD["status"]
        mode_text = "Navigate"
        info_text = "LMB to orbit; RMB to pan; MWheel or LMB+RMB to zoom; <Home> to reset view;"
        info_text += " <Space-up> to end"
        status_data["navigate"] = {"mode": mode_text, "info": info_text}

        return "navigation_ok"

    def __enter_navigation_mode(self, prev_state_id, active):

        if not active:
            self._clock.reset()
            Mgr.do("hilite_world_axes")
            Mgr.do("start_updating_view_cube")

        Mgr.update_app("status", ["navigate"])

    def __exit_navigation_mode(self, next_state_id, active):

        if not active:
            Mgr.do("hilite_world_axes", False)
            Mgr.do("stop_updating_view_cube")
            Mgr.remove_task("transform_cam")

    def __determine_navigation_end(self):

        if self._clock.real_time >= .5:
            Mgr.exit_state("navigation_mode")
        else:
            Mgr.activate_bindings(["end navigation"])

    def __quit_navigation_mode(self):

        state_id = Mgr.get_state_id()

        if state_id != "navigation_mode":
            Mgr.exit_state(state_id)

        Mgr.exit_state("navigation_mode")

    def __end_cam_transform(self):

        Mgr.remove_task("transform_cam")
        self._dolly_accel = 1.

    def __zoom_step_in(self):

        if GD.cam.lens_type == "persp":
            y = GD.cam.origin.get_y()
            new_y = min(-self._near, y + (-y * .5) ** .75)
            GD.cam.origin.set_y(new_y)
        else:
            scale = GD.cam.target.get_sx()
            new_scale = max(.0004, scale * .95)
            GD.cam.target.set_scale(new_scale)

        Mgr.do("update_zoom_indicator")
        Mgr.get("transf_gizmo").update()
        Mgr.do("update_coord_sys")

    def __zoom_step_out(self):

        if GD.cam.lens_type == "persp":
            y = GD.cam.origin.get_y()
            new_y = max(-1000000., y - (-y * .5) ** .75)
            GD.cam.origin.set_y(new_y)
        else:
            scale = GD.cam.target.get_sx()
            new_scale = min(100000., scale * 1.05)
            GD.cam.target.set_scale(new_scale)

        Mgr.do("update_zoom_indicator")
        Mgr.get("transf_gizmo").update()
        Mgr.do("update_coord_sys")

    def __init_pan(self):

        Mgr.remove_task("transform_cam")

        if not GD.mouse_watcher.has_mouse():
            return

        self.__get_pan_pos(self._pan_start_pos)
        Mgr.add_task(self.__pan, "transform_cam", sort=2)

    def __pan(self, task):

        pan_pos = Point3()

        if not self.__get_pan_pos(pan_pos):
            return task.cont

        GD.cam.pivot.set_pos(GD.cam.pivot.get_pos() + (self._pan_start_pos - pan_pos))
        Mgr.get("transf_gizmo").update()
        Mgr.do("update_coord_sys")

        return task.cont

    def __get_pan_pos(self, pos):

        if not GD.mouse_watcher.has_mouse():
            return False

        target = GD.cam.target
        pivot_pos = GD.cam.pivot.get_pos()
        normal = GD.world.get_relative_vector(target, Vec3.forward())
        normal.normalize()
        plane = Plane(normal, pivot_pos)
        screen_pos = GD.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        cam = GD.cam()
        near_point = GD.world.get_relative_point(cam, near_point)
        far_point = GD.world.get_relative_point(cam, far_point)
        plane.intersects_line(pos, near_point, far_point)

        return True

    def __init_orbit(self):

        Mgr.remove_task("transform_cam")

        if not GD.mouse_watcher.has_mouse():
            return

        if GD["view"] in ("front", "back", "left", "right", "top", "bottom"):
            return

        self._orbit_start_pos = Point2(GD.mouse_watcher.get_mouse())
        Mgr.add_task(self.__orbit, "transform_cam", sort=2)

    def __orbit(self, task):

        if not GD.mouse_watcher.has_mouse():
            return task.cont

        orbit_pos = GD.mouse_watcher.get_mouse()
        d_heading, d_pitch = (orbit_pos - self._orbit_start_pos) * 100.
        self._orbit_start_pos = Point2(orbit_pos)
        target = GD.cam.target
        target.set_hpr(target.get_h() - d_heading, target.get_p() + d_pitch, 0.)
        Mgr.get("transf_gizmo").update()
        Mgr.do("update_coord_sys")

        return task.cont

    def __init_zoom(self):

        Mgr.remove_task("transform_cam")

        if not GD.mouse_watcher.has_mouse():
            return

        if GD.cam.lens_type == "persp":
            self._zoom_start = (GD.cam.origin.get_y(), GD.mouse_watcher.get_mouse_y())
        else:
            scale = GD.cam.target.get_sx()
            self._zoom_start = (scale, GD.mouse_watcher.get_mouse_y())

        Mgr.add_task(self.__zoom, "transform_cam", sort=2)

    def __zoom(self, task):

        if not GD.mouse_watcher.has_mouse():
            return task.cont

        zoom_pos = GD.mouse_watcher.get_mouse_y()

        if GD.cam.lens_type == "persp":

            start_y, mouse_start_pos = self._zoom_start
            dist = zoom_pos - mouse_start_pos

            if dist < 0.:
                dist = (start_y * dist * 10.) ** .75
                new_y = max(-1000000., start_y - dist)
            else:
                dist = (start_y * dist * -10.) ** .75
                new_y = min(-self._near, start_y + dist)

            GD.cam.origin.set_y(new_y)

        else:

            start_scale, mouse_start_pos = self._zoom_start
            dist = zoom_pos - mouse_start_pos
            # in the line below, 2. is arbitrarily chosen to allow zooming in as
            # far as allowed by the lower limit by dragging the mouse all the way
            # from the bottom to the top of the viewport, since this distance
            # equals 2 screen units
            scale = start_scale * 2. * dist / (2. + abs(dist))

            if dist < 0.:
                new_scale = min(100000., start_scale - scale * 5.)
            else:
                new_scale = max(.0004, start_scale - scale)

            GD.cam.target.set_scale(new_scale)

        Mgr.do("update_zoom_indicator")
        Mgr.get("transf_gizmo").update()
        Mgr.do("update_coord_sys")

        return task.cont

    def __init_dolly(self, direction):

        self._dolly_dir = direction
        Mgr.remove_task("transform_cam")
        Mgr.add_task(self.__dolly, "transform_cam", sort=2)

    def __dolly(self, task):

        if GD["ctrl_down"]:
            self._dolly_accel = max(.1, self._dolly_accel - .01)

        if GD["shift_down"]:
            self._dolly_accel = min(5., self._dolly_accel + .01)

        GD.cam.pivot.set_y(GD.cam.target, self._dolly_dir * self._dolly_accel)
        Mgr.get("transf_gizmo").update()
        Mgr.do("update_coord_sys")

        return task.cont


MainObjects.add_class(NavigationManager)
