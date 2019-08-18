from .base import *


class PickingCamera:

    def __init__(self):

        self._tex = None
        self._tex_peeker = None
        self._buffer = None
        self._np = None
        self._mask = next(camera_mask)
        self._pixel_color = VBase4()
        self._transformer = None

        UVMgr.expose("picking_mask", lambda: self._mask)
        UVMgr.expose("pixel_under_mouse", lambda: VBase4(self._pixel_color))
        UVMgr.expose("picking_cam", lambda: self)
        UVMgr.expose("picked_point", self.__get_picked_point)

    def __call__(self):

        return self._np

    def setup(self):

        self._tex = Texture("uv_picking_texture")
        props = FrameBufferProperties()
        props.set_rgba_bits(8, 8, 8, 8)
        props.set_depth_bits(8)
        self._buffer = bfr = GD.window.make_texture_buffer("uv_picking_buffer",
                                                           15, 15,
                                                           self._tex,
                                                           to_ram=True,
                                                           fbp=props)

        bfr.clear_color = (0., 0., 0., 0.)
        bfr.set_clear_color_active(True)
        self._np = GD.showbase.make_camera(bfr)
        self._np.reparent_to(GD.uv_cam)
        node = self._np.node()
        self._lens = lens = OrthographicLens()
        lens.near = -10.
        lens.film_size = .06
        node.set_lens(lens)
        node.camera_mask = self._mask

        state_np = NodePath("uv_vertex_color_state")
        state_np.set_texture_off(1)
        state_np.set_material_off(1)
        state_np.set_shader_off(1)
        state_np.set_light_off(1)
        state_np.set_color_off(1)
        state_np.set_color_scale_off(1)
        state_np.set_render_mode_thickness(5, 1)
        state_np.set_transparency(TransparencyAttrib.M_none, 1)
        node.initial_state = state_np.get_state()
        node.active = False

        return "uv_picking_camera_ok"

    def __update_frustum(self):

        w, h = GD["viewport"]["size" if GD["viewport"][2] == "main" else "size_aux"]
        self._lens.film_size = .06 * 512. / min(w, h)

    def restore_lens(self):

        self._np.node().set_lens(self._lens)

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
        Mgr.remove_task("get_uv_pixel_under_mouse")

        if active:
            Mgr.add_task(self.__get_pixel_under_mouse, "get_uv_pixel_under_mouse", sort=0)
            Mgr.add_app_updater("viewport", self.__update_frustum, interface_id="uv")
            self.__update_frustum()
        else:
            self._pixel_color = VBase4()

    def __get_pixel_under_mouse(self, task):

        if not GD.uv_mouse_watcher.has_mouse():
            self._buffer.active = False
            self._np.node().active = False
            return task.cont

        if not self._np.node().active:
            self._buffer.active = True
            self._np.node().active = True

        if self._transformer:
            self._transformer(self._np)
        else:
            screen_pos = GD.uv_mouse_watcher.get_mouse()
            far_point = Point3()
            GD.uv_cam_lens.extrude(screen_pos, Point3(), far_point)
            far_point.y = 0.
            self._np.set_pos(far_point)

        if self._tex_peeker:
            self._tex_peeker.lookup(self._pixel_color, .5, .5)
        else:
            self._tex_peeker = self._tex.peek()

        return task.cont

    def __get_picked_point(self):

        pos = self._np.get_pos(GD.uv_space)
        pos.y = 0.

        return pos


# the following camera is used to detect temporary geometry created to allow subobject
# picking via polygon
class AuxiliaryPickingCamera:

    @property
    def origin(self):

        return self._np

    def __init__(self):

        self._pixel_color = VBase4()
        UVMgr.expose("aux_pixel_under_mouse", lambda: VBase4(self._pixel_color))

        self._tex = Texture("aux_picking_texture")
        self._tex_peeker = None
        props = FrameBufferProperties()
        props.set_rgba_bits(8, 8, 8, 8)
        props.set_depth_bits(8)
        self._buffer = bfr = GD.window.make_texture_buffer("aux_picking_buffer",
                                                           1, 1,
                                                           self._tex,
                                                           to_ram=True,
                                                           fbp=props)

        bfr.clear_color = (0., 0., 0., 0.)
        bfr.set_clear_color_active(True)
        self._np = GD.showbase.make_camera(bfr)
        node = self._np.node()
        self._lens = lens = OrthographicLens()
        lens.film_size = .75
        lens.near = 0.
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
        node.initial_state = state
        node.active = False

        self._plane = None

    def setup(self):

        self._np.reparent_to(Mgr.get("aux_picking_root"))

        return True

    def __update_frustum(self):

        w, h = GD["viewport"]["size" if GD["viewport"][2] == "main" else "size_aux"]
        self._lens.film_size = .75 * 512. / min(w, h)

    def set_plane(self, plane):

        self._plane = plane

    def update_pos(self):

        if not GD.uv_mouse_watcher.has_mouse():
            return

        cam = GD.uv_cam
        screen_pos = GD.uv_mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        GD.uv_cam_lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.uv_space.get_relative_point(cam, point)
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
            Mgr.add_app_updater("viewport", self.__update_frustum, interface_id="uv")
            self.__update_frustum()
        else:
            self._pixel_color = VBase4()

    def __get_pixel_under_mouse(self, task):

        if not GD.uv_mouse_watcher.is_mouse_open():
            self._buffer.active = False
            self._np.node().active = False
            self._pixel_color = VBase4()
            return task.cont

        if not self._np.node().active:
            self._buffer.active = True
            self._np.node().active = True

        cam = GD.uv_cam
        screen_pos = GD.uv_mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        GD.uv_cam_lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.uv_space.get_relative_point(cam, point)
        point = Point3()
        self._plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))
        self._np.look_at(point)

        if not self._tex_peeker:
            self._tex_peeker = self._tex.peek()
            return task.cont

        self._tex_peeker.lookup(self._pixel_color, .5, .5)

        return task.cont


class UVNavigationMixin:
    """ UVEditor class mix-in """

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

        GD.uv_cam.set_pos(.5, -10., .5)
        GD.uv_cam.set_scale(1.)
        self._grid.update()
        self._transf_gizmo.set_scale(1.)

    def __init_pan(self):

        Mgr.remove_task("transform_uv_cam")

        if not GD.uv_mouse_watcher.has_mouse():
            return

        self.__get_pan_pos(self._pan_start_pos)
        Mgr.add_task(self.__pan, "transform_uv_cam", sort=2)

    def __pan(self, task):

        pan_pos = Point3()

        if not self.__get_pan_pos(pan_pos):
            return task.cont

        GD.uv_cam.set_pos(GD.uv_cam.get_pos() + (self._pan_start_pos - pan_pos))
        self._grid.update()

        return task.cont

    def __get_pan_pos(self, pos):

        if not GD.uv_mouse_watcher.has_mouse():
            return False

        pos.x, _, pos.z = UVMgr.get("picked_point")

        return True

    def __init_zoom(self):

        Mgr.remove_task("transform_uv_cam")

        if not GD.uv_mouse_watcher.has_mouse():
            return

        self._zoom_start = (GD.uv_cam.get_sx(), GD.uv_mouse_watcher.get_mouse_y())
        Mgr.add_task(self.__zoom, "transform_uv_cam", sort=2)

    def __zoom(self, task):

        if not GD.uv_mouse_watcher.has_mouse():
            return task.cont

        mouse_y = GD.uv_mouse_watcher.get_mouse_y()
        start_scale, start_y = self._zoom_start

        if mouse_y < start_y:
            # zoom out
            zoom = 1. + start_y - mouse_y
        else:
            # zoom in
            zoom = 1. / (1. + mouse_y - start_y)

        zoom *= start_scale
        zoom = min(1000., max(.001, zoom))
        GD.uv_cam.set_scale(zoom)
        self._grid.update()
        self._transf_gizmo.set_scale(zoom)

        return task.cont

    def __zoom_step_in(self):

        zoom = GD.uv_cam.get_sx() * .9
        zoom = max(.001, zoom)
        GD.uv_cam.set_scale(zoom)
        self._grid.update()
        self._transf_gizmo.set_scale(zoom)

    def __zoom_step_out(self):

        zoom = GD.uv_cam.get_sx() * 1.1
        zoom = min(1000., zoom)
        GD.uv_cam.set_scale(zoom)
        self._grid.update()
        self._transf_gizmo.set_scale(zoom)


class UVTemplateSaver:

    def __init__(self):

        self._template_mask = next(camera_mask)
        self._size = 512
        self._edge_color = VBase4(1., 1., 1., 1.)
        self._poly_color = VBase4(1., 1., 1., 0.)
        self._seam_color = VBase4(0., 1., 0., 1.)
        UVMgr.expose("template_mask", lambda: self._template_mask)
        GD.uv_space.hide(self._template_mask)

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
        props = FrameBufferProperties()
        props.set_rgba_bits(8, 8, 8, 8)
        props.set_depth_bits(8)
        tex_buffer = GD.window.make_texture_buffer("uv_template_buffer",
                                                   res, res,
                                                   Texture("uv_template"),
                                                   to_ram=True,
                                                   fbp=props)

        tex_buffer.clear_color = (0., 0., 0., 0.)
        cam = GD.showbase.make_camera(tex_buffer)
        cam.reparent_to(GD.uv_space)
        cam.set_pos(.5, -10., .5)
        node = cam.node()
        node.camera_mask = self._template_mask
        lens = OrthographicLens()
        lens.film_size = 1.
        node.set_lens(lens)
        node.tag_state_key = "uv_template"

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
        GD.showbase.graphicsEngine.remove_window(tex_buffer)

        UVMgr.do("reset_unselected_poly_state")


MainObjects.add_class(PickingCamera, "uv")
MainObjects.add_class(AuxiliaryPickingCamera, "uv")
