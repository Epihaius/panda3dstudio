from ..base import *
import array


class Grid:

    def __init__(self):

        self.origin = GD.world.attach_new_node("grid")
        self._grid_lines = self.origin.attach_new_node("grid_lines")
        self._axes = self._grid_lines.attach_new_node("grid_axis_lines")
        self._grid_planes = {}
        self._planes = {}
        self._plane_hprs = {"xy": (0., 0., 0.), "xz": (0., 90., 0.), "yz": (0., 0., 90.)}
        self._horizon_line = None
        self._horizon_point_pivot = None
        self._horizon_point = None
        self._axis_indicator = None

        Mgr.expose("grid", lambda: self)
        Mgr.add_app_updater("active_grid_plane", self.__set_plane)
        Mgr.add_app_updater("viewport", self.__handle_viewport_resize)
        Mgr.add_app_updater("lens_type", self.__show_horizon)

        self._ref_dist = 1.
        self._scale = 1.
        self._spacing = 10.

        GD.set_default("active_grid_plane", "xy")

        self._active_plane_id = "yz"

    def setup(self):

        if "views_ok" not in MainObjects.get_setup_results():
            return False

        angle = GD.cam.lens.fov[1] * .5
        self._ref_dist = .25 * 300. / math.tan(math.radians(angle))

        picking_mask = Mgr.get("picking_mask")

        if picking_mask is None:
            return False

        self.origin.hide(picking_mask)

        for plane_id in ("xy", "xz", "yz"):
            plane = self.__create_plane(plane_id)
            plane.reparent_to(self._grid_lines)
            plane.hide()
            self._grid_planes[plane_id] = plane

        self.__create_horizon()
        self.__create_axis_indicator()

        self.origin.set_transparency(TransparencyAttrib.M_alpha)
        self._grid_lines.set_shader(shaders.Shaders.grid)
        self._grid_lines.set_shader_input("offset", Vec3())

        for i, axis_id in enumerate("xyz"):
            plane_id = "xyz".replace(axis_id, "")
            normal = Vec3(0., 0., 0.)
            normal[i] = 1.
            plane_node = PlaneNode(f"grid_plane_{plane_id.lower()}", Plane(normal, Point3()))
            self._planes[plane_id] = self.origin.attach_new_node(plane_node)

        self.__set_plane("xy")

        return "grid_ok"

    @property
    def plane_id(self):

        return self._active_plane_id

    def __handle_viewport_resize(self):

        w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
        scale = 800. / max(w, h)
        self._axis_indicator.set_scale(scale)

    def __show_horizon(self, lens_type):

        render_mask = Mgr.get("render_mask")

        if lens_type == "persp":
            self._horizon_line.show(render_mask)
            self._axis_indicator.show(render_mask)
        else:
            self._horizon_line.hide(render_mask)
            self._axis_indicator.hide(render_mask)

    def __create_horizon(self):

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("horizon_data", vertex_format, Geom.UH_static)
        vertex_data.unclean_set_num_rows(3)
        data_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
        data_view[:] = array.array("f", (-10., 10., 0., 10., 10., 0., 0., -10., 0.))
        horizon_geom = Geom(vertex_data)
        horizon_line = GeomLines(Geom.UH_static)
        prim_array = horizon_line.modify_vertices()
        prim_array.unclean_set_num_rows(6)
        prim_view = memoryview(prim_array).cast("B").cast("H")
        prim_view[:] = array.array("H", (0, 1, 1, 2, 0, 2))
        horizon_geom.add_primitive(horizon_line)
        horizon_node = GeomNode("horizon")
        horizon_node.add_geom(horizon_geom)
        pivot = GD.cam().attach_new_node("horizon_pivot")
        pivot.set_compass(self.origin)
        self._horizon_line = pivot.attach_new_node(horizon_node)
        self._horizon_line.set_color(.35, .35, .35)
        self._horizon_line.set_bin("background", 0)
        self._horizon_line.set_depth_test(False)
        self._horizon_line.set_depth_write(False)
        self._horizon_line.hide(Mgr.get("picking_masks"))

    def __create_axis_indicator(self):

        vertex_format = GeomVertexFormat()
        array_format = GeomVertexArrayFormat()
        array_format.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)
        array_format.add_column(InternalName.make("color"), 4, Geom.NT_float32, Geom.C_color)
        vertex_format.add_array(array_format)
        vertex_format = GeomVertexFormat.register_format(vertex_format)
        vertex_data = GeomVertexData("axis_indicator_data", vertex_format, Geom.UH_static)
        vertex_data.unclean_set_num_rows(6)
        data_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
        data_array = array.array("f", [])
        axis_indicator_geom = Geom(vertex_data)
        axis_indicator_line = GeomLines(Geom.UH_static)

        for i in range(3):
            pos = VBase3()
            pos[i] = 5.
            color = VBase4(0., 0., 0., 1.)
            color[i] = .35
            data_array.extend((0., 0., 0.))
            data_array.extend(color)
            data_array.extend(pos)
            data_array.extend(color)
            axis_indicator_line.add_next_vertices(2)

        data_view[:] = data_array
        vertex_data.set_format(GeomVertexFormat.get_v3c4())
        axis_indicator_geom.add_primitive(axis_indicator_line)
        axis_indicator_node = GeomNode("axis_indicator")
        axis_indicator_node.add_geom(axis_indicator_geom)
        self._axis_indicator = self.origin.attach_new_node(axis_indicator_node)
        self._axis_indicator.set_bin("background", 0)
        self._axis_indicator.set_depth_test(False)
        self._axis_indicator.set_depth_write(False)
        self._horizon_point_pivot = self.origin.attach_new_node("horizon_point_pivot")
        self._horizon_point = self._horizon_point_pivot.attach_new_node("horizon_point")

    def __create_line(self, axis_id):

        coord_index = "xyz".index(axis_id)
        data_array = array.array("f", [])
        pos = VBase3()
        pos[coord_index] = -1000.
        data_array.extend(pos)
        pos = VBase3()
        pos[coord_index] = 1000.
        data_array.extend(pos)
        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("gridline_data", vertex_format, Geom.UH_static)
        vertex_data.unclean_set_num_rows(2)
        data_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
        data_view[:] = data_array
        line = GeomLines(Geom.UH_static)
        line.add_vertices(0, 1)
        line_geom = Geom(vertex_data)
        line_geom.add_primitive(line)
        line_node = GeomNode(f"grid_line_{axis_id.lower()}")
        line_node.add_geom(line_geom)

        return NodePath(line_node)

    def __create_plane(self, plane_id):

        geom_node = GeomNode(f"grid_plane_{plane_id.lower()}")
        node_path = NodePath(geom_node)

        axis_id1, axis_id2 = plane_id

        color1 = VBase4(0., 0., 0., 1.0)
        color_index1 = "xyz".index(axis_id1)
        color1[color_index1] = .3
        color2 = VBase4(0., 0., 0., 1.0)
        color_index2 = "xyz".index(axis_id2)
        color2[color_index2] = .3

        def create_lines(axis_id, color):

            grid_half_np = node_path.attach_new_node("")

            grey_lines = grid_half_np.attach_new_node("")
            grey_lines.set_color(.35, .35, .35, 1.)

            colored_lines = grid_half_np.attach_new_node("")
            colored_lines.set_color(color)

            line = self.__create_line(axis_id)

            coord_index = "xyz".index(axis_id1 if axis_id == axis_id2 else axis_id2)

            for i in range(1, 101):

                if i % 5 == 0:
                    line_copy = line.copy_to(colored_lines)
                else:
                    line_copy = line.copy_to(grey_lines)

                pos = VBase3()
                pos[coord_index] = i * 10.
                line_copy.set_pos(pos)

            mirrored_half = grid_half_np.copy_to(node_path)
            scale = VBase3(1., 1., 1.)
            scale_index = "xyz".index(axis_id1 if axis_id == axis_id2 else axis_id2)
            scale[scale_index] = -1.
            mirrored_half.set_scale(scale)

        create_lines(axis_id1, color1)
        create_lines(axis_id2, color2)

        central_line1 = self.__create_line(axis_id1)
        central_line1.reparent_to(node_path)
        central_line1.set_color(color1)
        central_line2 = self.__create_line(axis_id2)
        central_line2.reparent_to(node_path)
        central_line2.set_color(color2)

        node_path.flatten_strong()
        child = node_path.get_child(0)
        child_node = child.node()
        geom_node.add_geom(child_node.modify_geom(0))
        child_node.remove_geom(0)
        child.detach_node()

        # Create the grid points (used for snapping)

        vertex_format = GeomVertexFormat()
        array_format = GeomVertexArrayFormat()
        array_format.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)
        array_format.add_column(InternalName.make("color"), 4, Geom.NT_float32, Geom.C_color)
        vertex_format.add_array(array_format)
        vertex_format = GeomVertexFormat.register_format(vertex_format)
        vertex_data = GeomVertexData("gridpoint_data", vertex_format, Geom.UH_static)
        vertex_data.unclean_set_num_rows(40000)
        data_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
        data_array = array.array("f", [])
        index1 = "xyz".index(axis_id1)
        index2 = "xyz".index(axis_id2)
        start_color = VBase4(100. / 255.)
        start_color.w = 254. / 255.

        for i1 in range(-1000, 1000, 10):
            for i2 in range(-1000, 1000, 10):
                pos = Point3()
                pos[index1] = i1
                pos[index2] = i2
                data_array.extend(pos)
                color = VBase4(start_color)
                color[index1] = (i1 / 10 + 100) / 255.
                color[index2] = (i2 / 10 + 100) / 255.
                data_array.extend(color)

        data_view[:] = data_array
        vertex_data.set_format(GeomVertexFormat.get_v3c4())
        points = GeomPoints(Geom.UH_static)
        points.reserve_num_vertices(40000)
        points.add_next_vertices(40000)
        point_geom = Geom(vertex_data)
        point_geom.add_primitive(points)
        point_node = GeomNode("points")
        point_node.add_geom(point_geom)
        grid_points_np = node_path.attach_new_node(point_node)
        grid_points_np.hide(Mgr.get("render_mask"))
        grid_points_np.set_shader_off()

        return node_path

    def update(self, force=False):

        cam = GD.cam()
        lens_type = GD.cam.lens_type
        cam_pos = cam.get_pos(self.origin)

        if lens_type == "persp":

            point = cam_pos

        else:

            point = Point3()
            plane = self._planes[self._active_plane_id].node().get_plane()
            cam_vec = self.origin.get_relative_vector(cam, Vec3(0., 10000., 0.))

            if not plane.intersects_line(point, cam_pos, cam_pos + cam_vec):
                point = Point3()

        axis_id1, axis_id2 = self._active_plane_id
        axis_id3 = "xyz".replace(axis_id1, "").replace(axis_id2, "")
        a_index = "xyz".index(axis_id1)
        b_index = "xyz".index(axis_id2)
        a = point[a_index]
        b = point[b_index]

        if lens_type == "persp":
            c_index = "xyz".index(axis_id3)
            c = point[c_index] * (-1. if c_index == 1 else 1.)
            c_offset = min(1000000., abs(c))
            d = c_offset / self._ref_dist
        else:
            d = GD.cam.target.get_sx()

        if d > .0005:
            ceil1 = 10. ** math.ceil(math.log(d, 10.))
            ceil2 = ceil1 * .5
            scale = ceil2 if ceil2 > d else ceil1
        else:
            scale = .0005

        if force or scale != self._scale:
            self._grid_planes[self._active_plane_id].set_scale(scale)
            self._scale = scale
            spacing_str = str(self._spacing * scale)
            Mgr.update_app("gridspacing", spacing_str)

        size = 50. * self._scale
        a_offset = abs(a) // size * (-size if a < 0. else size)
        b_offset = abs(b) // size * (-size if b < 0. else size)
        offset = VBase3()
        offset[a_index] = a_offset
        offset[b_index] = b_offset
        self._grid_lines.set_shader_input("offset", offset / scale)
        self._grid_planes[self._active_plane_id].set_pos(offset)
        offset = VBase3()
        offset[a_index] = a_offset
        offset = VBase3()
        offset[b_index] = b_offset

        if lens_type == "persp":
            self._horizon_point_pivot.set_pos(cam_pos)
            self._horizon_point.set_h(cam.get_h(self._horizon_point_pivot))
            proj = -5. * c / (5. + abs(c))
            pos = self.origin.get_relative_point(self._horizon_point, Point3(0., 100., proj))
            self._axis_indicator.set_pos(pos)

    def __change_plane(self, plane_id):

        self._grid_planes[self._active_plane_id].hide()
        self._grid_planes[plane_id].show()

        self._active_plane_id = plane_id

        axis_id1, axis_id2 = plane_id
        axis_id3 = "xyz".replace(axis_id1, "").replace(axis_id2, "")

        hpr = self._plane_hprs[plane_id]
        self._horizon_line.set_hpr(hpr)
        self._horizon_point_pivot.set_hpr(hpr)
        vec = Vec3()
        vec["xyz".index(axis_id3)] = 1.
        self._grid_lines.set_shader_input("plane_normal", vec)

    def align_to_view(self, align=True):

        if align:
            self.__change_plane("xy")
        else:
            self.__change_plane(GD["active_grid_plane"])

        self.update(force=True)

    def __set_plane(self, plane_id):

        GD["active_grid_plane"] = plane_id

        if GD["coord_sys_type"] != "view" and plane_id != self._active_plane_id:
            self.__change_plane(plane_id)

        self.update(force=True)

    def get_point_at_screen_pos(self, screen_pos, point_in_plane=None):

        cam = GD.cam()
        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.origin.get_relative_point(cam, point)

        point = Point3()
        plane = self._planes[self._active_plane_id].node().get_plane()

        if point_in_plane:
            plane = Plane(plane.get_normal(), point_in_plane)

        if plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point)):
            return point

    def get_projected_point(self, point, point_in_plane=None):

        plane = self._planes[self._active_plane_id].node().get_plane()

        if point_in_plane:
            plane = Plane(plane.get_normal(), point_in_plane)

        return plane.project(point)

    def get_snap_point(self, color):

        r, g, b, a = color

        if round(a * 255.) == 254.:
            x = round(r * 255. - 100.) * 10.
            y = round(g * 255. - 100.) * 10.
            z = round(b * 255. - 100.) * 10.
            point = Point3(x, y, z)
            plane = self._grid_planes[self._active_plane_id]
            return self.origin.get_relative_point(plane, point)

    def make_pickable(self, mask_index, pickable=True):

        picking_mask = Mgr.get("picking_mask", mask_index)

        for plane in self._grid_planes.values():
            if pickable:
                plane.get_child(0).show_through(picking_mask)
            else:
                plane.get_child(0).hide(picking_mask)


MainObjects.add_class(Grid)
