from .base import *


class TranslationGizmo(TransformationGizmo):

    def _create_handles(self):

        root = Mgr.get("transf_gizmo_root")
        self._origin = root.attach_new_node("translation_gizmo")
        self._handle_root = self._origin.attach_new_node("handle_root")

        red = VBase4(.7, 0., 0., 1.)
        green = VBase4(0., .7, 0., 1.)
        blue = VBase4(0., 0., .7, 1.)
        grey = VBase4(.5, .5, .5, 1.)

        self._axis_colors = {"x": red, "y": green, "z": blue, "screen": grey}
        pickable_type_id = PickableTypes.get_id("transf_gizmo")

        # Create single-axis handles

        for i, axis in enumerate("xyz"):

            color_id = self.get_next_picking_color_id()
            color_vec = get_color_vec(color_id, pickable_type_id)
            self._handle_names[color_id] = axis
            pos1 = Point3()
            pos1[i] = .04
            pos2 = Point3()
            pos2[i] = .16
            handle = self.__create_axis_handle(self._handle_root, color_vec, pos1, pos2,
                                               "{}_axis_handle".format(axis))
            color = self._axis_colors[axis]
            handle.set_color(color)
            self._handles["axes"][axis] = handle

            pos = Point3()
            pos[i] = .2
            axis_vec = Vec3()
            axis_vec[i] = 1.
            cone_vec = Vec3()
            cone_vec[i] = -.05
            cone_vec[(i + 1) % 3] = .01
            cone, cap = self.__create_axis_arrow(self._handle_root, color_vec, pos, axis_vec,
                                                 cone_vec, 6, "{}_axis_arrow".format(axis))
            cone.set_color(color)
            cap.set_color(color * .5)

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
            pos1[index1] = pos2[index1] = pos2[index2] = pos3[index2] = .07
            handle, quad = self.__create_plane_handle(self._handle_root, color_vec, pos1, pos2, pos3,
                                                      "{}_plane_handle".format(plane))
            self._handles["planes"][plane] = handle
            self._handles["quads"][plane] = quad
            handle[0].set_color(self._axis_colors[plane[0]])
            handle[1].set_color(self._axis_colors[plane[1]])

        # Create screen handle

        color_id = self.get_next_picking_color_id()
        color_vec = get_color_vec(color_id, pickable_type_id)
        self._handle_names[color_id] = "screen"
        handle = self.__create_screen_handle(self._origin, color_vec, .03, "screen_handle")
        self._handles["planes"]["screen"] = handle
        handle.set_color(grey)

    def __create_axis_handle(self, parent, color, pos1, pos2, node_name):

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("axis_line_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.add_data3(pos1)
        pos_writer.add_data3(pos2)

        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.add_data4(color)
        col_writer.add_data4(color)

        lines = GeomLines(Geom.UH_static)
        lines.add_vertices(0, 1)
        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        lines_node = GeomNode(node_name)
        lines_node.add_geom(lines_geom)

        return parent.attach_new_node(lines_node)

    def __create_axis_arrow(self, parent, color, pos, axis_vec, cone_vec, segments, node_name):

        # Create the arrow cone

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("axis_arrow_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        pos_writer.add_data3(pos)
        col_writer.add_data4(color)

        angle = 360. / segments
        quat = Quat()
        points = []

        for i in range(segments):
            quat.set_from_axis_angle(angle * i, axis_vec)
            points.append(pos + quat.xform(cone_vec))

        for point in points:
            pos_writer.add_data3(point)
            col_writer.add_data4(color)

        cone = GeomTriangles(Geom.UH_static)

        indexes = range(1, segments + 1)

        for i in indexes:
            cone.add_vertices(0, i, indexes[i % segments])

        cone_geom = Geom(vertex_data)
        cone_geom.add_primitive(cone)
        cone_node = GeomNode(node_name)
        cone_node.add_geom(cone_geom)

        cone_np = parent.attach_new_node(cone_node)

        # Create the cap of the arrow cone

        vertex_data = GeomVertexData("axis_arrow_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        for point in points:
            pos_writer.add_data3(point)
            col_writer.add_data4(color)

        cap = GeomTriangles(Geom.UH_static)

        for i in range(1, segments - 1):
            cap.add_vertices(0, i + 1, i)

        cap_geom = Geom(vertex_data)
        cap_geom.add_primitive(cap)
        cap_node = GeomNode(node_name)
        cap_node.add_geom(cap_geom)

        cap_np = parent.attach_new_node(cap_node)

        return cone_np, cap_np

    def __create_plane_handle(self, parent, color, pos1, pos2, pos3, node_name):

        vertex_format = GeomVertexFormat.get_v3c4()

        def create_line(pos1, pos2):

            vertex_data = GeomVertexData("axes_plane_data", vertex_format, Geom.UH_static)

            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            col_writer = GeomVertexWriter(vertex_data, "color")

            pos_writer.add_data3(pos1)
            col_writer.add_data4(color)
            pos_writer.add_data3(pos2)
            col_writer.add_data4(color)

            lines = GeomLines(Geom.UH_static)
            lines.add_vertices(0, 1)
            lines_geom = Geom(vertex_data)
            lines_geom.add_primitive(lines)
            lines_node = GeomNode(node_name)
            lines_node.add_geom(lines_geom)

            return lines_node

        line1_np = parent.attach_new_node(create_line(pos1, pos2))
        line2_np = parent.attach_new_node(create_line(pos2, pos3))

        # Create quad

        vertex_data = GeomVertexData("axes_quad_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        for pos in (Point3(), pos1, pos2, pos3):
            pos_writer.add_data3(pos)

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
        quad_np.hide(self._picking_mask)

        return (line1_np, line2_np), quad_np

    def __create_screen_handle(self, parent, color, size, node_name):

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("screen_handle_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        coord = size * .5

        for x, z in ((-coord, -coord), (-coord, coord), (coord, coord), (coord, -coord)):
            pos = VBase3(x, 0., z)
            pos_writer.add_data3(pos)
            col_writer.add_data4(color)

        square = GeomLines(Geom.UH_static)

        for i in range(4):
            square.add_vertices(i, (i + 1) % 4)

        square_geom = Geom(vertex_data)
        square_geom.add_primitive(square)
        square_node = GeomNode(node_name)
        square_node.add_geom(square_geom)
        square_np = parent.attach_new_node(square_node)
        square_np.set_billboard_point_eye()
        square_np.set_bin("fixed", 100)
        square_np.set_depth_test(False)

        return square_np

    def hilite_handle(self, color_id):

        if color_id not in self._handle_names:
            return

        hilited_handles = []
        handle_name = self._handle_names[color_id]

        if handle_name == "screen":

            hilited_handles.append("screen")

        else:

            for axis in handle_name:
                hilited_handles.append(axis)

            if handle_name in self._handles["planes"]:
                hilited_handles.append(handle_name)
                self._handles["quads"][handle_name].show()

        if self._hilited_handles != hilited_handles:

            self.remove_hilite()
            self._hilited_handles = hilited_handles

            cyan = VBase4(0., 1., 1., 1.)
            cyan_alpha = VBase4(0., 1., 1., .25)

            for handle_name in hilited_handles:

                if handle_name in self._handles["planes"]:

                    handle = self._handles["planes"][handle_name]

                    if handle_name == "screen":
                        handle.set_color(cyan)
                    else:
                        handle[0].set_color(cyan)
                        handle[1].set_color(cyan)
                        self._handles["quads"][handle_name].set_color(cyan_alpha)

                else:

                    self._handles["axes"][handle_name].set_color(cyan)

    def remove_hilite(self):

        if self._hilited_handles:

            yellow = VBase4(1., 1., 0., 1.)
            yellow_alpha = VBase4(1., 1., 0., .25)

            for plane in self._handles["quads"]:
                if plane == self._selected_axes:
                    self._handles["quads"][plane].set_color(yellow_alpha)
                    self._handles["quads"][plane].show()
                else:
                    self._handles["quads"][plane].hide()

            for handle_name in self._hilited_handles:

                if handle_name == "screen":

                    if handle_name == self._selected_axes:
                        color = yellow
                    else:
                        color = self._axis_colors[handle_name]

                    self._handles["planes"][handle_name].set_color(color)

                elif handle_name in self._handles["planes"]:

                    if handle_name == self._selected_axes:
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
        Mgr.update_app("axis_constraints", "translate", axes)

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

        for plane in self._handles["planes"]:

            if plane == "screen":

                handle = self._handles["planes"][plane]
                handle.set_color(yellow if plane == axes else self._axis_colors[plane])

            else:

                quad = self._handles["quads"][plane]
                quad.set_color(yellow_alpha)

                if plane == axes:
                    handle = self._handles["planes"][plane]
                    handle[0].set_color(yellow)
                    handle[1].set_color(yellow)
                    quad.show()
                else:
                    handle = self._handles["planes"][plane]
                    handle[0].set_color(self._axis_colors[plane[0]])
                    handle[1].set_color(self._axis_colors[plane[1]])
                    quad.hide()

    def get_point_at_screen_pos(self, screen_pos):

        cam = self.cam()
        point1 = Mgr.get("transf_gizmo_world_pos")

        if self._selected_axes == "screen":

            normal = self.world.get_relative_vector(cam, Vec3.forward())
            plane = Plane(normal, point1)

        else:

            if len(self._selected_axes) == 2:

                axis_vec = Vec3()
                axis_vec["xyz".index(self._selected_axes[0])] = 1.
                axis_vec = V3D(self.world.get_relative_vector(self._handle_root, axis_vec))
                point2 = point1 + axis_vec
                axis_vec = Vec3()
                axis_vec["xyz".index(self._selected_axes[1])] = 1.
                axis_vec = V3D(self.world.get_relative_vector(self._handle_root, axis_vec))
                point3 = point1 + axis_vec

            else:

                axis_vec = Vec3()
                axis_vec["xyz".index(self._selected_axes)] = 1.
                axis_vec = V3D(self.world.get_relative_vector(self._handle_root, axis_vec))
                cam_vec = V3D(self.world.get_relative_vector(cam, Vec3.forward()))
                cross_vec = axis_vec ** cam_vec

                if not cross_vec.normalize():
                    return point1

                point2 = point1 + axis_vec
                point3 = point1 + cross_vec

            plane = Plane(point1, point2, point3)

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point
