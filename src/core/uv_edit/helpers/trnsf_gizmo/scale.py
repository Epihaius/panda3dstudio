from ...base import *


class ScalingComponent(object):

    def __init__(self, gizmo):

        self._gizmo = gizmo
        self._type = "scale"
        self._origin = orig = gizmo.get_root().attach_new_node("uv_scaling_gizmo")
        orig.node().set_bounds(BoundingSphere(Point3(), .25))
        orig.node().set_final(True)
        self._render_mask = UVMgr.get("render_mask")
        self._picking_mask = UVMgr.get("picking_mask")
        self._handle_root = self._origin.attach_new_node("handle_root")
        self._handles = {"axes": {}, "planes": {}, "quads": {}}
        self._handle_names = {}
        self._hilited_handles = []
        self._axis_colors = {}
        self._active_axes = ""
        self._is_active = True

        self.__create_handles()

    def __create_handles(self):

        red = (.7, 0., 0., 1.)
        green = (0., .7, 0., 1.)

        self._axis_colors = {"u": red, "v": green}
        pickable_type_id = PickableTypes.get_id("transf_gizmo")

        # Create single-axis handles

        for i, axis in enumerate("uv"):

            color_id = self._gizmo.get_next_picking_color_id()
            color_vec = get_color_vec(color_id, pickable_type_id)
            self._handle_names[color_id] = axis
            pos1 = Point2()
            pos1[i] = -.04
            pos2 = Point2()
            pos2[i] = -.2
            handle, point = self.__create_axis_handle(self._origin, color_vec, pos1, pos2,
                                                      "{}_axis_handle".format(axis))
            color = self._axis_colors[axis]
            handle.set_color(color)
            point.set_color(color)
            self._handles["axes"][axis] = handle

        # Create double-axis handle

        plane = "uv"
        color_id = self._gizmo.get_next_picking_color_id()
        color_vec = get_color_vec(color_id, pickable_type_id)
        self._handle_names[color_id] = plane
        pos1 = Point2()
        pos2 = Point2()
        pos3 = Point2()
        pos4 = Point2()
        pos1[0] = pos3[1] = -.1
        pos2[0] = pos4[1] = -.14
        handle, quad = self.__create_plane_handle(self._origin, color_vec, pos1, pos2, pos3,
                                                  pos4, "{}_plane_handle".format(plane))
        self._handles["planes"][plane] = handle
        self._handles["quads"][plane] = quad
        handle[0].set_color(self._axis_colors[plane[0]])
        handle[1].set_color(self._axis_colors[plane[1]])

    def __create_axis_handle(self, parent, color, pos1, pos2, node_name):

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("axis_line_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        u, v = pos1
        pos_writer.add_data3(u, 0., v)
        u, v = pos2
        pos_writer.add_data3(u, 0., v)

        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.add_data4(color)
        col_writer.add_data4(color)

        lines = GeomLines(Geom.UH_static)
        lines.add_vertices(0, 1)
        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        lines_node = GeomNode(node_name)
        lines_node.add_geom(lines_geom)
        lines_np = parent.attach_new_node(lines_node)

        vertex_data = GeomVertexData("axis_point_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")
        pos_writer.add_data3(u, -.05, v)
        col_writer.add_data4(color)

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

        vertex_format = GeomVertexFormat.get_v3()

        def create_line(pos1, pos2):

            vertex_data = GeomVertexData("axes_plane_data", vertex_format, Geom.UH_static)

            pos_writer = GeomVertexWriter(vertex_data, "vertex")

            for pos in (pos1, pos2, pos5, pos6):
                u, v = pos
                pos_writer.add_data3(u, 0., v)

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

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("axes_quad_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        for pos in (pos2, pos1, pos3, pos4):
            u, v = pos
            pos_writer.add_data3(u, 0., v)
            col_writer.add_data4(color)

        tri = GeomTriangles(Geom.UH_static)
        tri.add_vertices(0, 1, 2)
        tri.add_vertices(2, 3, 0)
        quad_geom = Geom(vertex_data)
        quad_geom.add_primitive(tri)
        quad_node = GeomNode("plane_quad")
        quad_node.add_geom(quad_geom)
        quad_np = parent.attach_new_node(quad_node)
        quad_np.set_two_sided(True)
        quad_np.set_transparency(TransparencyAttrib.M_alpha)

        return (lines1_np, lines2_np), quad_np

    def get_transform_type(self):

        return self._type

    def hilite_handle(self, color_id):

        if color_id not in self._handle_names:
            return

        hilited_handles = []
        handle_name = self._handle_names[color_id]

        for axis in handle_name:
            hilited_handles.append(axis)

        if handle_name in self._handles["planes"]:
            hilited_handles.append(handle_name)
            self._handles["quads"][handle_name].show(self._render_mask)

        if self._hilited_handles != hilited_handles:

            self.remove_hilite()
            self._hilited_handles = hilited_handles

            cyan = (0., 1., 1., 1.)
            cyan_alpha = (0., 1., 1., .25)

            for handle_name in hilited_handles:
                if handle_name in self._handles["planes"]:
                    handle = self._handles["planes"][handle_name]
                    handle[0].set_color(cyan)
                    handle[1].set_color(cyan)
                    self._handles["quads"][handle_name].set_color(cyan_alpha)
                else:
                    self._handles["axes"][handle_name].set_color(cyan)

            GlobalData["uv_cursor"] = self._type

    def remove_hilite(self):

        if self._hilited_handles:

            if self._is_active:
                rgb = (1., 1., 0., 1.)
                rgba = (1., 1., 0., .25)
            else:
                rgb = (.5, .5, .5, 1.)
                rgba = (.5, .5, .5, .25)

            for plane in self._handles["quads"]:
                if plane == self._active_axes:
                    self._handles["quads"][plane].set_color(rgba)
                    self._handles["quads"][plane].show(self._render_mask)
                else:
                    self._handles["quads"][plane].hide(self._render_mask)

            for handle_name in self._hilited_handles:

                if handle_name in self._handles["planes"]:

                    if self._active_axes == handle_name or not self._is_active:
                        color1 = color2 = rgb
                    else:
                        color1 = self._axis_colors[handle_name[0]]
                        color2 = self._axis_colors[handle_name[1]]

                    handle = self._handles["planes"][handle_name]
                    handle[0].set_color(color1)
                    handle[1].set_color(color2)

                else:

                    if handle_name in self._active_axes or not self._is_active:
                        color = rgb
                    else:
                        color = self._axis_colors[handle_name]

                    self._handles["axes"][handle_name].set_color(color)

            self._hilited_handles = []
            GlobalData["uv_cursor"] = ""

    def select_handle(self, color_id):

        if color_id not in self._handle_names:
            return

        axes = self._handle_names[color_id]
        Mgr.update_interface("uv", "axis_constraints", self._type, axes)

        return axes

    def get_active_axes(self):

        return self._active_axes

    def set_active_axes(self, axes):

        self._active_axes = axes
        self.remove_hilite()
        yellow = (1., 1., 0., 1.)
        yellow_alpha = (1., 1., 0., .25)

        for axis in "uv":
            if axis in axes:
                self._handles["axes"][axis].set_color(yellow)
            else:
                self._handles["axes"][axis].set_color(self._axis_colors[axis])

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

    def set_active(self, is_active=True):

        if self._is_active == is_active:
            return

        if is_active:
            rgb = (1., 1., 0., 1.)
            rgba = (1., 1., 0., .25)
        else:
            rgb = (.5, .5, .5, 1.)
            rgba = (.5, .5, .5, .25)

        for handle in self._handles["planes"].values():
            handle[0].set_color(rgb)
            handle[1].set_color(rgb)

        for handle in self._handles["quads"].values():
            handle.set_color(rgba)

        for handle in self._handles["axes"].values():
            handle.set_color(rgb)

        self._is_active = is_active

    def show(self):

        self._origin.show()

    def hide(self):

        self._origin.hide()
