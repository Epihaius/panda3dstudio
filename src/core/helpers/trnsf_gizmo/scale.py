from .base import *


class ScalingGizmo(TransformationGizmo):

    def _create_handles(self):

        root = Mgr.get("transf_gizmo_root")
        self._origin = root.attach_new_node("scaling_gizmo")

        self._scale = VBase3(1., 1., 1.)

        red = VBase4(.7, 0., 0., 1.)
        green = VBase4(0., .7, 0., 1.)
        blue = VBase4(0., 0., .7, 1.)

        self._axis_colors = {"x": red, "y": green, "z": blue}
        pickable_type_id = PickableTypes.get_id("transf_gizmo")

        # Create single-axis handles

        for i, axis in enumerate("xyz"):

            color_id = self.get_next_picking_color_id()
            color_vec = get_color_vec(color_id, pickable_type_id)
            self._handle_names[color_id] = axis
            pos = Point3()
            pos[i] = .2
            handle, point = self.__create_axis_handle(self._origin, color_vec, pos,
                                                      "{}_axis_handle".format(axis))
            color = self._axis_colors[axis]
            handle.set_color(color)
            point.set_color(color)
            self._handles["axes"][axis] = handle

        # Create double-axis handles

        for plane in ("xy", "xz", "yz"):

            color_id = self.get_next_picking_color_id()
            color_vec = get_color_vec(color_id, pickable_type_id)
            self._handle_names[color_id] = plane
            index1 = "xyz".index(plane[0])
            index2 = "xyz".index(plane[1])
            pos1 = Point3()
            pos2 = Point3()
            pos3 = Point3()
            pos4 = Point3()
            pos1[index1] = pos3[index2] = .1
            pos2[index1] = pos4[index2] = .14
            handle, quad = self.__create_plane_handle(self._origin, color_vec, pos1, pos2, pos3,
                                                      pos4, "{}_plane_handle".format(plane))
            self._handles["planes"][plane] = handle
            self._handles["quads"][plane] = quad
            handle[0].set_color(self._axis_colors[plane[0]])
            handle[1].set_color(self._axis_colors[plane[1]])

        # Create center handle

        color_id = self.get_next_picking_color_id()
        color_vec = get_color_vec(color_id, pickable_type_id)
        self._handle_names[color_id] = "xyz"
        handle = self.__create_center_handle(self._origin, color_vec,
                                             Point3(.1, 0., 0.), Point3(.0, .1, 0.),
                                             Point3(0., 0., .1), "center_handle")
        self._center_handle = handle

        # Create scale indicator

        self._scale_indicator = self.__create_scale_indicator(root, "scale_indicator")
        self._scale_indicator.set_color(1., 1., 1., 1.)
        self._scale_indicator.hide()

        Mgr.accept("show_scale_indicator", self.__show_scale_indicator)
        Mgr.accept("hide_scale_indicator", self._scale_indicator.hide)

    def __create_axis_handle(self, parent, color, pos, node_name):

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("axis_line_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.add_data3f(0., 0., 0.)
        pos_writer.add_data3f(pos)

        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.add_data4f(color)
        col_writer.add_data4f(color)

        lines = GeomLines(Geom.UH_static)
        lines.add_vertices(0, 1)
        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        lines_node = GeomNode(node_name)
        lines_node.add_geom(lines_geom)
        lines_np = parent.attach_new_node(lines_node)

        vertex_data = GeomVertexData("axis_point_data", vertex_format, Geom.UH_static)
        GeomVertexWriter(vertex_data, "vertex").add_data3f(pos)
        GeomVertexWriter(vertex_data, "color").add_data4f(color)

        points = GeomPoints(Geom.UH_static)
        points.add_vertex(0)
        points_geom = Geom(vertex_data)
        points_geom.add_primitive(points)
        points_node = GeomNode("axis_point")
        points_node.add_geom(points_geom)
        points_np = parent.attach_new_node(points_node)
        points_np.set_render_mode_thickness(7)

        return lines_np, points_np

    def __create_plane_handle(self, parent, color, pos1, pos2, pos3, pos4, node_name):

        pos5 = (pos1 + pos3) * .5
        pos6 = (pos2 + pos4) * .5

        vertex_format = GeomVertexFormat.get_v3c4()

        def create_line(pos1, pos2):

            vertex_data = GeomVertexData("axes_plane_data", vertex_format, Geom.UH_static)

            pos_writer = GeomVertexWriter(vertex_data, "vertex")

            pos_writer.add_data3f(pos1)
            pos_writer.add_data3f(pos2)
            pos_writer.add_data3f(pos5)
            pos_writer.add_data3f(pos6)

            lines = GeomLines(Geom.UH_static)
            lines.add_vertices(0, 2)
            lines.add_vertices(1, 3)
            lines_geom = Geom(vertex_data)
            lines_geom.add_primitive(lines)
            lines_node = GeomNode(node_name)
            lines_node.add_geom(lines_geom)

            return lines_node

        lines1_np = parent.attach_new_node(create_line(pos1, pos2))
        lines1_np.hide(self._picking_mask)
        lines2_np = parent.attach_new_node(create_line(pos3, pos4))
        lines2_np.hide(self._picking_mask)

        # Create quad

        vertex_data = GeomVertexData("axes_quad_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        for pos in (pos2, pos1, pos3, pos4):
            pos_writer.add_data3f(pos)
            col_writer.add_data4f(color)

        tris = GeomTriangles(Geom.UH_static)
        tris.add_vertices(0, 1, 2)
        tris.add_vertices(2, 3, 0)
        quad_geom = Geom(vertex_data)
        quad_geom.add_primitive(tris)
        quad_node = GeomNode("plane_quad")
        quad_node.add_geom(quad_geom)
        quad_np = parent.attach_new_node(quad_node)
        quad_np.set_two_sided(True)
        quad_np.set_transparency(TransparencyAttrib.M_alpha)

        return (lines1_np, lines2_np), quad_np

    def __create_center_handle(self, parent, color, pos1, pos2, pos3, node_name):

        vertex_format = GeomVertexFormat.get_v3c4()

        vertex_data = GeomVertexData("axes_quad_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        for pos in (pos1, pos2, pos3):
            pos_writer.add_data3f(pos)
            col_writer.add_data4f(color)

        tris = GeomTriangles(Geom.UH_static)
        tris.add_vertices(0, 1, 2)
        tris_geom = Geom(vertex_data)
        tris_geom.add_primitive(tris)
        tris_node = GeomNode("center_triangle")
        tris_node.add_geom(tris_geom)
        tris_np = parent.attach_new_node(tris_node)
        tris_np.set_two_sided(True)
        tris_np.set_transparency(TransparencyAttrib.M_alpha)

        return tris_np

    def __create_scale_indicator(self, parent, node_name):

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("scale_indicator_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        lines = GeomLines(Geom.UH_static)

        coord = .015

        for y, z in ((-coord, -coord), (-coord, coord), (coord, coord), (coord, -coord)):
            pos = VBase3(0., y + .06, z)
            pos_writer.add_data3f(pos)

        for i in range(4):
            lines.add_vertices(i, (i + 1) % 4)

        coord = .03

        for y, z in ((-coord, -coord), (-coord, coord), (coord, coord), (coord, -coord)):
            pos = VBase3(0., y - .08, z)
            pos_writer.add_data3f(pos)

        for i in range(4):
            lines.add_vertices(i + 4, (i + 1) % 4 + 4)

        pos_writer.add_data3f(0., 0., -.05)
        pos_writer.add_data3f(0., 0., .05)

        lines.add_vertices(8, 9)

        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        lines_node = GeomNode(node_name)
        lines_node.add_geom(lines_geom)
        lines_np = parent.attach_new_node(lines_node)
        lines_np.set_bin("fixed", 100)
        lines_np.set_depth_test(False)
        lines_np.set_depth_write(False)
        lines_np.hide(self._picking_mask)

        return lines_np

    def __show_scale_indicator(self, pos, hpr):

        self._scale_indicator.set_pos(self.world, pos)
        self._scale_indicator.set_hpr(self.cam(), hpr)
        self._scale_indicator.show()

    def hilite_handle(self, color_id):

        if color_id not in self._handle_names:
            return

        hilited_handles = []
        handle_name = self._handle_names[color_id]

        for axis in handle_name:
            hilited_handles.append(axis)

        if handle_name == "xyz":

            hilited_handles.append(handle_name)

            for plane in self._handles["planes"]:
                hilited_handles.append(plane)

        if handle_name in self._handles["planes"]:
            hilited_handles.append(handle_name)
            self._handles["quads"][handle_name].show(self._render_mask)

        if self._hilited_handles != hilited_handles:

            self.remove_hilite()
            self._hilited_handles = hilited_handles

            cyan = VBase4(0., 1., 1., 1.)
            cyan_alpha = VBase4(0., 1., 1., .25)

            for handle_name in hilited_handles:

                if handle_name == "xyz":

                    self._center_handle.set_color(cyan_alpha)
                    self._center_handle.show(self._render_mask)

                elif handle_name in self._handles["planes"]:

                    handle = self._handles["planes"][handle_name]
                    handle[0].set_color(cyan)
                    handle[1].set_color(cyan)

                    if "xyz" not in hilited_handles:
                        self._handles["quads"][handle_name].set_color(cyan_alpha)

                else:

                    self._handles["axes"][handle_name].set_color(cyan)

    def remove_hilite(self):

        if self._hilited_handles:

            yellow = VBase4(1., 1., 0., 1.)
            yellow_alpha = VBase4(1., 1., 0., .25)

            if self._selected_axes == "xyz":
                self._center_handle.set_color(yellow_alpha)
                self._center_handle.show(self._render_mask)
            else:
                self._center_handle.hide(self._render_mask)

            for plane in self._handles["quads"]:
                if plane == self._selected_axes:
                    self._handles["quads"][plane].set_color(yellow_alpha)
                    self._handles["quads"][plane].show(self._render_mask)
                else:
                    self._handles["quads"][plane].hide(self._render_mask)

            for handle_name in self._hilited_handles:

                if handle_name == "xyz":
                    continue

                if handle_name in self._handles["planes"]:

                    if self._selected_axes in (handle_name, "xyz"):
                        color1 = color2 = yellow
                    else:
                        color1 = self._axis_colors[handle_name[0]]
                        color2 = self._axis_colors[handle_name[1]]

                    handle = self._handles["planes"][handle_name]
                    handle[0].set_color(color1)
                    handle[1].set_color(color2)

                else:

                    if handle_name in self._selected_axes:
                        color = yellow
                    else:
                        color = self._axis_colors[handle_name]

                    self._handles["axes"][handle_name].set_color(color)

            self._hilited_handles = []

    def select_handle(self, color_id):

        if color_id not in self._handle_names:
            return

        axes = self._handle_names[color_id]
        Mgr.update_app("axis_constraints", "scale", axes)

    def set_active_axes(self, axes):

        self._selected_axes = axes
        self.remove_hilite()
        yellow = VBase4(1., 1., 0., 1.)
        yellow_alpha = VBase4(1., 1., 0., .25)

        for axis in "xyz":
            if axis in axes:
                self._handles["axes"][axis].set_color(yellow)
            else:
                self._handles["axes"][axis].set_color(self._axis_colors[axis])

        if axes == "xyz":

            self._center_handle.set_color(yellow_alpha)
            self._center_handle.show(self._render_mask)

            for plane in self._handles["planes"]:
                handle = self._handles["planes"][plane]
                handle[0].set_color(yellow)
                handle[1].set_color(yellow)
                self._handles["quads"][plane].hide(self._render_mask)

        else:

            self._center_handle.hide(self._render_mask)

            for plane in self._handles["planes"]:

                quad = self._handles["quads"][plane]

                if plane == axes:
                    handle = self._handles["planes"][plane]
                    handle[0].set_color(yellow)
                    handle[1].set_color(yellow)
                    quad.set_color(yellow_alpha)
                    quad.show(self._render_mask)
                else:
                    handle = self._handles["planes"][plane]
                    handle[0].set_color(self._axis_colors[plane[0]])
                    handle[1].set_color(self._axis_colors[plane[1]])
                    quad.hide(self._render_mask)

    def get_point_at_screen_pos(self, screen_pos):

        cam = self.cam()
        rel_pt = lambda point: self.world.get_relative_point(cam, point)
        normal = self.world.get_relative_vector(cam, Vec3.forward())
        point = rel_pt(Point3(0., 2., 0.))
        plane = Plane(normal, point)

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point

    def face_camera(self):

        root = Mgr.get("transf_gizmo_root")
        cam = self.cam()

        if self.cam.lens_type == "persp":
            vec = V3D(root.get_pos(cam))
        else:
            vec = V3D(Vec3.forward())

        x_vec = V3D(cam.get_relative_vector(root, Vec3.unit_x()))
        y_vec = V3D(cam.get_relative_vector(root, Vec3.unit_y()))
        z_vec = V3D(cam.get_relative_vector(root, Vec3.unit_z()))

        sx = -1. if vec * x_vec > 0. else 1.
        sy = -1. if vec * y_vec > 0. else 1.
        sz = -1. if vec * z_vec > 0. else 1.

        self._scale = VBase3(sx, sy, sz)
        self._origin.set_scale(self._scale)

    def show(self):

        TransformationGizmo.show(self)

        self.face_camera()
