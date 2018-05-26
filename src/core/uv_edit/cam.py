from .base import *


class PickingCamera(BaseObject):

    def __init__(self):

        self._tex = None
        self._tex_peeker = None
        self._buffer = None
        self._np = None
        self._mask = BitMask32.bit(25)

        self._pixel_color = VBase4()

        UVMgr.expose("picking_mask", lambda: self._mask)
        UVMgr.expose("pixel_under_mouse", lambda: VBase4(self._pixel_color))
        UVMgr.expose("picking_cam", lambda: self)
        UVMgr.expose("picked_point", self.__get_picked_point)

    def setup(self):

        base = Mgr.get("base")
        self._tex = Texture("uv_picking_texture")
        props = FrameBufferProperties()
        props.set_rgba_bits(16, 16, 16, 16)
        props.set_depth_bits(16)
        self._buffer = bfr = base.win.make_texture_buffer("uv_picking_buffer",
                                                          1, 1,
                                                          self._tex,
                                                          to_ram=True,
                                                          fbp=props)

        bfr.set_clear_color(VBase4())
        bfr.set_clear_color_active(True)
        bfr.set_sort(-100)
        self._np = base.make_camera(bfr)
        self._np.reparent_to(self.cam)
        node = self._np.node()
        self._lens = lens = OrthographicLens()
        lens.set_near(-10.)
        lens.set_film_size(.004)
        node.set_lens(lens)
        node.set_camera_mask(self._mask)

        state_np = NodePath("uv_vertex_color_state")
        state_np.set_texture_off(1)
        state_np.set_material_off(1)
        state_np.set_shader_off(1)
        state_np.set_light_off(1)
        state_np.set_color_off(1)
        state_np.set_color_scale_off(1)
        state_np.set_render_mode_thickness(5, 1)
        state_np.set_transparency(TransparencyAttrib.M_none, 1)
        node.set_initial_state(state_np.get_state())
        node.set_active(False)

        return "uv_picking_camera_ok"

    def __update_frustum(self):

        w, h = GlobalData["viewport"]["size" if GlobalData["viewport"][2] == "main" else "size_aux"]
        self._lens.set_film_size(.004 * 512. / min(w, h))

    def set_active(self, is_active=True):

        if self._np.node().is_active() == is_active:
            return

        self._buffer.set_active(is_active)
        self._np.node().set_active(is_active)

        if is_active:
            Mgr.add_task(self.__get_pixel_under_mouse, "get_uv_pixel_under_mouse", sort=0)
            Mgr.add_app_updater("viewport", self.__update_frustum, interface_id="uv")
            self.__update_frustum()
        else:
            Mgr.remove_task("get_uv_pixel_under_mouse")
            self._pixel_color = VBase4()

    def __get_pixel_under_mouse(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        screen_pos = self.mouse_watcher.get_mouse()
        far_point = Point3()
        self.cam_lens.extrude(screen_pos, Point3(), far_point)
        far_point.y = 0.
        self._np.set_pos(far_point)

        if not self._tex_peeker:
            self._tex_peeker = self._tex.peek()
            return task.cont

        self._tex_peeker.lookup(self._pixel_color, .5, .5)

        return task.cont

    def __get_picked_point(self):

        pos = self._np.get_pos(self.uv_space)
        pos.y = 0.

        return pos


# the following camera is used to detect temporary geometry created to allow subobject
# picking via polygon
class AuxiliaryPickingCamera(BaseObject):

    def __init__(self):

        self._pixel_color = VBase4()
        UVMgr.expose("aux_pixel_under_mouse", lambda: VBase4(self._pixel_color))

        base = Mgr.get("base")
        self._tex = Texture("aux_picking_texture")
        self._tex_peeker = None
        props = FrameBufferProperties()
        props.set_rgba_bits(16, 16, 16, 16)
        props.set_depth_bits(16)
        self._buffer = bfr = base.win.make_texture_buffer("aux_picking_buffer",
                                                          1, 1,
                                                          self._tex,
                                                          to_ram=True,
                                                          fbp=props)

        bfr.set_clear_color(VBase4())
        bfr.set_clear_color_active(True)
        bfr.set_sort(-100)
        self._np = base.make_camera(bfr)
        node = self._np.node()
        self._lens = lens = OrthographicLens()
        lens.set_film_size(.75)
        lens.set_near(0.)
        node.set_lens(lens)
        UVMgr.expose("aux_picking_cam", lambda: self)

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

    def __update_frustum(self):

        w, h = GlobalData["viewport"]["size" if GlobalData["viewport"][2] == "main" else "size_aux"]
        self._lens.set_film_size(.004 * 512. / min(w, h))

    def get_origin(self):

        return self._np

    def set_plane(self, plane):

        self._plane = plane

    def update_pos(self):

        if not self.mouse_watcher.has_mouse():
            return

        cam = self.cam
        screen_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        self.cam_lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.uv_space.get_relative_point(cam, point)
        point = Point3()
        self._plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))
        self._np.set_pos(point)

    def set_active(self, is_active=True):

        if self._np.node().is_active() == is_active:
            return

        self._buffer.set_active(is_active)
        self._np.node().set_active(is_active)

        if is_active:
            Mgr.add_task(self.__get_pixel_under_mouse, "get_aux_pixel_under_mouse", sort=0)
            Mgr.add_app_updater("viewport", self.__update_frustum, interface_id="uv")
            self.__update_frustum()
        else:
            Mgr.remove_task("get_aux_pixel_under_mouse")
            self._pixel_color = VBase4()

    def __get_pixel_under_mouse(self, task):

        if not self.mouse_watcher.is_mouse_open():
            self._pixel_color = VBase4()
            return task.cont

        cam = self.cam
        screen_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        self.cam_lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.uv_space.get_relative_point(cam, point)
        point = Point3()
        self._plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))
        self._np.look_at(point)

        if not self._tex_peeker:
            self._tex_peeker = self._tex.peek()
            return task.cont

        self._tex_peeker.lookup(self._pixel_color, .5, .5)

        return task.cont


class UVNavigationBase(BaseObject):

    def __init__(self):

        self._pan_start_pos = Point3()

    def setup(self):

        add_state = Mgr.add_state
        add_state("panning", -100, interface_id="uv")
        add_state("zooming", -100, interface_id="uv")

        def start_panning():

            Mgr.enter_state("panning", "uv")
            self.__init_pan()

        def start_zooming():

            Mgr.enter_state("zooming", "uv")
            self.__init_zoom()

        def end_cam_transform():

            Mgr.enter_state("uv_edit_mode", "uv")
            Mgr.remove_task("transform_uv_cam")

        bind = Mgr.bind_state
        bind("uv_edit_mode", "edit uvs -> pan",
             "mouse3", start_panning, "uv")
        bind("panning", "pan -> edit uvs", "mouse3-up",
             end_cam_transform, "uv")
        bind("panning", "pan -> zoom", "mouse1", start_zooming, "uv")
        bind("zooming", "zoom -> pan", "mouse1-up", start_panning, "uv")
        bind("zooming", "zoom -> edit uvs", "mouse3-up",
             end_cam_transform, "uv")
        bind("uv_edit_mode", "zoom in", "wheel_up",
             self.__zoom_step_in, "uv")
        bind("uv_edit_mode", "zoom out", "wheel_down",
             self.__zoom_step_out, "uv")
        bind("uv_edit_mode", "reset view", "home",
             self._reset_view, "uv")

    def _reset_view(self):

        self.cam.set_pos(.5, -10., .5)
        self.cam.set_scale(1.)
        self._grid.update()
        self._transf_gizmo.set_scale(1.)

    def __init_pan(self):

        Mgr.remove_task("transform_uv_cam")

        if not self.mouse_watcher.has_mouse():
            return

        self.__get_pan_pos(self._pan_start_pos)
        Mgr.add_task(self.__pan, "transform_uv_cam", sort=2)

    def __pan(self, task):

        pan_pos = Point3()

        if not self.__get_pan_pos(pan_pos):
            return task.cont

        self.cam.set_pos(self.cam.get_pos() + (self._pan_start_pos - pan_pos))
        self._grid.update()

        return task.cont

    def __get_pan_pos(self, pos):

        if not self.mouse_watcher.has_mouse():
            return False

        pos.x, _, pos.z = UVMgr.get("picked_point")

        return True

    def __init_zoom(self):

        Mgr.remove_task("transform_uv_cam")

        if not self.mouse_watcher.has_mouse():
            return

        self._zoom_start = (self.cam.get_sx(), self.mouse_watcher.get_mouse_y())
        Mgr.add_task(self.__zoom, "transform_uv_cam", sort=2)

    def __zoom(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        mouse_y = self.mouse_watcher.get_mouse_y()
        start_scale, start_y = self._zoom_start

        if mouse_y < start_y:
            # zoom out
            zoom = 1. + start_y - mouse_y
        else:
            # zoom in
            zoom = 1. / (1. + mouse_y - start_y)

        zoom *= start_scale
        zoom = min(1000., max(.001, zoom))
        self.cam.set_scale(zoom)
        self._grid.update()
        self._transf_gizmo.set_scale(zoom)

        return task.cont

    def __zoom_step_in(self):

        zoom = self.cam.get_sx() * .9
        zoom = max(.001, zoom)
        self.cam.set_scale(zoom)
        self._grid.update()
        self._transf_gizmo.set_scale(zoom)

    def __zoom_step_out(self):

        zoom = self.cam.get_sx() * 1.1
        zoom = min(1000., zoom)
        self.cam.set_scale(zoom)
        self._grid.update()
        self._transf_gizmo.set_scale(zoom)


class UVTemplateSaver(BaseObject):

    def __init__(self):

        self._template_mask = BitMask32.bit(26)
        self._size = 512
        self._edge_color = VBase4(1., 1., 1., 1.)
        self._poly_color = VBase4(1., 1., 1., 0.)
        self._seam_color = VBase4(0., 1., 0., 1.)
        UVMgr.expose("template_mask", lambda: self._template_mask)
        self.uv_space.hide(self._template_mask)

        def update_remotely():

            Mgr.update_interface_remotely("uv", "uv_template", "size", self._size)
            r, g, b, a = self._edge_color
            Mgr.update_interface_remotely("uv", "uv_template", "edge_rgb", (r, g, b))
            Mgr.update_interface_remotely("uv", "uv_template", "edge_alpha", a)
            r, g, b, a = self._poly_color
            Mgr.update_interface_remotely("uv", "uv_template", "poly_rgb", (r, g, b))
            Mgr.update_interface_remotely("uv", "uv_template", "poly_alpha", a)
            r, g, b, a = self._seam_color
            Mgr.update_interface_remotely("uv", "uv_template", "seam_rgb", (r, g, b))
            Mgr.update_interface_remotely("uv", "uv_template", "seam_alpha", a)

        UVMgr.accept("remotely_update_template_props", update_remotely)

    def add_interface_updaters(self):

        Mgr.add_app_updater("uv_template", self.__update_uv_template, interface_id="uv")

    def __update_uv_template(self, value_id, value=None):

        if value_id == "size":
            self._size = value
        elif value_id == "edge_rgb":
            for i in range(3):
                self._edge_color[i] = value[i]
        elif value_id == "edge_alpha":
            self._edge_color[3] = value
        elif value_id == "poly_rgb":
            for i in range(3):
                self._poly_color[i] = value[i]
        elif value_id == "poly_alpha":
            self._poly_color[3] = value
        elif value_id == "seam_rgb":
            for i in range(3):
                self._seam_color[i] = value[i]
        elif value_id == "seam_alpha":
            self._seam_color[3] = value
        elif value_id == "save":
            self.__save_uv_template(value)

        if value_id != "save":
            Mgr.update_interface_remotely("uv", "uv_template", value_id, value)

    def __save_uv_template(self, filename):

        UVMgr.do("clear_unselected_poly_state")

        res = self._size
        base = Mgr.get("base")
        props = FrameBufferProperties()
        props.set_rgba_bits(32, 32, 32, 32)
        props.set_depth_bits(32)
        tex_buffer = base.win.make_texture_buffer("uv_template_buffer",
                                                  res, res,
                                                  Texture("uv_template"),
                                                  to_ram=True,
                                                  fbp=props)

        tex_buffer.set_clear_color(VBase4())
        cam = base.make_camera(tex_buffer)
        cam.reparent_to(self.uv_space)
        cam.set_pos(.5, -10., .5)
        node = cam.node()
        node.set_camera_mask(self._template_mask)
        lens = OrthographicLens()
        lens.set_film_size(1.)
        node.set_lens(lens)
        node.set_tag_state_key("uv_template")

        state_np = NodePath("uv_template_render_state")
        state_np.set_texture_off()
        state_np.set_material_off()
        state_np.set_shader_off()
        state_np.set_light_off()
        state_np.set_transparency(TransparencyAttrib.M_alpha)

        edge_state_np = NodePath(state_np.node().make_copy())
        edge_state_np.set_color(self._edge_color)
        node.set_tag_state("edge", edge_state_np.get_state())

        poly_state_np = NodePath(state_np.node().make_copy())
        poly_state_np.set_two_sided(True)
        poly_state_np.set_color(self._poly_color)
        node.set_tag_state("poly", poly_state_np.get_state())

        seam_state_np = NodePath(state_np.node().make_copy())
        seam_state_np.set_color(self._seam_color)
        node.set_tag_state("seam", seam_state_np.get_state())

        Mgr.render_frame()
        tex_buffer.save_screenshot(Filename.from_os_specific(filename))
        cam.remove_node()
        base.graphicsEngine.remove_window(tex_buffer)

        UVMgr.do("reset_unselected_poly_state")


MainObjects.add_class(PickingCamera, "uv")
MainObjects.add_class(AuxiliaryPickingCamera, "uv")
