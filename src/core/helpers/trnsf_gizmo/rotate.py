from .base import *


class RotationGizmo(TransformationGizmo):

    def _create_handles(self):

        self._origin = Mgr.get("transf_gizmo").root.attach_new_node("rotation_gizmo")

        self._radius = .15
        self._screen_handle_radius = 1.3
        self._origin.set_scale(self._radius)

        self._screen_plane = None

        cam = GD.cam()
        bb_fx_persp = {}
        vec_x = Vec3(1., 0., 0.)
        vec_z = Vec3(0., 0., 1.)
        effect = BillboardEffect.make(vec_z, False, True, 0., cam, Point3())
        bb_fx_persp["xy"] = effect
        bb_fx_persp["xz"] = effect
        effect = BillboardEffect.make(vec_x, False, True, 0., cam, Point3())
        bb_fx_persp["yz"] = effect
        bb_fx_ortho = {}
        point = Point3(0., -100000., 0.)
        effect = BillboardEffect.make(vec_z, False, True, 0., cam, point)
        bb_fx_ortho["xy"] = effect
        bb_fx_ortho["xz"] = effect
        effect = BillboardEffect.make(vec_x, False, True, 0., cam, point)
        bb_fx_ortho["yz"] = effect
        self._billboard_fx = {"persp": bb_fx_persp, "ortho": bb_fx_ortho}

        self._center_axis_root = self._origin.attach_new_node("center_axis_root")
        self._center_axes = {}

        red = VBase4(.7, 0., 0., 1.)
        green = VBase4(0., .7, 0., 1.)
        blue = VBase4(0., 0., .7, 1.)
        grey = VBase4(.5, .5, .5, 1.)
        dark_grey = VBase4(.3, .3, .3, 1.)

        self._axis_colors = {"yz": red, "xz": green, "xy": blue, "view": grey}
        pickable_type_id = PickableTypes.get_id("transf_gizmo")

        for plane in ("xy", "xz", "yz"):

            color_id = self.get_next_picking_color_id()
            color_vec = get_color_vec(color_id, pickable_type_id)
            self._handle_names[color_id] = plane
            axis = "".join(a for a in "xyz" if a not in plane)

            if axis == "y":
                pivot = self._origin.attach_new_node("y_handle_pivot")
                pivot.set_p(90.)
                handle = self.__create_axis_handle(pivot, color_vec, "z")
            else:
                handle = self.__create_axis_handle(self._origin, color_vec, axis)

            handle.set_effect(bb_fx_persp[plane])
            handle.set_color(self._axis_colors[plane])
            self._handles["planes"][plane] = handle

        color_id = self.get_next_picking_color_id()
        color_vec = get_color_vec(color_id, pickable_type_id)
        self._handle_names[color_id] = "view"
        handle = self.__create_screen_aligned_circle(self._origin, color_vec,
                                                     self._screen_handle_radius,
                                                     "screen_axis_handle")
        handle.set_color(grey)
        self._handles["planes"]["view"] = handle

        handle = self.__create_screen_aligned_circle(self._origin, dark_grey, 1., "trackball_edge")
        handle.hide(self._picking_mask)

        color_id = self.get_next_picking_color_id()
        color_vec = get_color_vec(color_id, pickable_type_id)
        self._handle_names[color_id] = "trackball"
        handle = self.__create_trackball(self._origin, color_vec)
        handle.set_transparency(TransparencyAttrib.M_alpha)
        handle.set_color(.25, .25, .25, .5)
        handle.hide(self._render_mask)
        self._handles["planes"]["trackball"] = handle

        self._angle_disc_pivot = self._origin.attach_new_node("angle_disc_pivot")
        self._angle_disc_root = self._angle_disc_pivot.attach_new_node("angle_disc_root")
        self._angle_disc_root.set_p(-90.)
        self._angle_disc_root.hide(self._picking_mask)
        self._angle_disc = self._angle_disc_root.attach_new_node("angle_disc")
        self._angle_disc.set_two_sided(True)
        self._angle_disc.set_transparency(TransparencyAttrib.M_alpha)
        self._angle_disc.set_color(.2, .1, .3, .25)
        self._angle_disc.hide()
        angle_disc_half1 = self.__create_angle_disc_half(self._angle_disc)
        angle_disc_half2 = self.__create_angle_disc_half(self._angle_disc, mirror=True)

        clip_plane = PlaneNode("clip_plane_neg_angle", Plane(Vec3(-1., 0., 0.), Point3()))
        clip_plane.set_clip_effect(1)
        clip_plane.set_priority(100)
        self._angle_clip_root = self._angle_disc_root.attach_new_node("angle_clip_root")
        self._clip_plane_neg_angle = self._angle_clip_root.attach_new_node(clip_plane)
        clip_plane = PlaneNode("clip_plane_pos_angle", Plane(Vec3(1., 0., 0.), Point3()))
        clip_plane.set_clip_effect(1)
        clip_plane.set_priority(100)
        self._clip_plane_pos_angle = self._angle_clip_root.attach_new_node(clip_plane)

        angle_disc_half1.set_clip_plane(self._clip_plane_neg_angle)
        angle_disc_half2.set_clip_plane(self._clip_plane_pos_angle)

        for axis in "xyz":
            self._center_axes[axis] = self.__create_center_axis(self._center_axis_root, axis)

        self._angle_arrow = self.__create_angle_arrow(self._angle_disc, .5)
        self._angle_arrow.set_color(1., 1., 1., 1.)

        self._angle = 0.
        self._rotation_started = False

        Mgr.accept("init_rotation_gizmo_angle", self.__init_rotation_angle)
        Mgr.accept("reset_rotation_gizmo_angle", self.__reset_rotation_angle)
        Mgr.accept("set_rotation_gizmo_angle", self.__set_rotation_angle)
        Mgr.expose("trackball_data", self.__get_trackball_data)

    def __create_axis_handle(self, parent, color, axis):

        segments = 50
        angle = math.pi / segments

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("axis_circle_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        circle = GeomLines(Geom.UH_static)

        for i in range(segments + 1):
            x = math.cos(angle * i)
            y = -math.sin(angle * i)
            pos_writer.add_data3(x, y, 0.)
            col_writer.add_data4(color)

        for i in range(segments):
            circle.add_vertices(i, i + 1)

        circle_geom = Geom(vertex_data)
        circle_geom.add_primitive(circle)
        circle_node = GeomNode(f"{axis}_axis_handle")
        circle_node.add_geom(circle_geom)
        circle_np = parent.attach_new_node(circle_node)

        return circle_np

    def __create_angle_disc_half(self, parent, mirror=False):

        segments = 50
        angle = math.pi / segments

        if mirror:
            angle *= -1.

        offset = math.pi * .5

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("angle_disc_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        disc = GeomTriangles(Geom.UH_static)

        for i in range(segments + 1):
            x = math.cos(angle * i - offset)
            y = math.sin(angle * i - offset)
            pos_writer.add_data3(x, y, 0.)

        for i in range(1, segments):
            disc.add_vertices(0, i, i + 1)

        disc_geom = Geom(vertex_data)
        disc_geom.add_primitive(disc)
        disc_node = GeomNode("angle_disc_node")
        disc_node.add_geom(disc_geom)

        return parent.attach_new_node(disc_node)

    def __create_screen_aligned_circle(self, parent, color, radius, node_name):

        segments = 100
        angle = 2. * math.pi / segments

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("axis_circle_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        circle = GeomLines(Geom.UH_static)

        for i in range(segments):
            x = math.cos(angle * i) * radius
            z = math.sin(angle * i) * radius
            pos_writer.add_data3(x, 0., z)
            col_writer.add_data4(color)

        for i in range(segments):
            circle.add_vertices(i, (i + 1) % segments)

        circle_geom = Geom(vertex_data)
        circle_geom.add_primitive(circle)
        circle_node = GeomNode(node_name)
        circle_node.add_geom(circle_geom)
        circle_np = parent.attach_new_node(circle_node)
        circle_np.set_billboard_point_eye()

        return circle_np

    def __create_center_axis(self, parent, axis):

        index = "xyz".index(axis)
        pos = VBase3()
        pos[index] = .5
        color = VBase4(0., 0., 0., 1.)
        color[index] = .3

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("center_axis_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        pos_writer.add_data3(0., 0., 0.)
        col_writer.add_data4(color)
        pos_writer.add_data3(pos)
        col_writer.add_data4(color)

        lines = GeomLines(Geom.UH_static)
        lines.add_vertices(0, 1)
        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        lines_node = GeomNode(f"center_axis_{axis}")
        lines_node.add_geom(lines_geom)
        lines_np = parent.attach_new_node(lines_node)
        lines_np.hide(self._picking_mask)

        return lines_np

    def __create_angle_arrow(self, parent, length):

        vertex_format = GeomVertexFormat.get_v3()
        vertex_data = GeomVertexData("angle_arrow_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        pos_writer.add_data3(0., 1., 0.)
        pos_writer.add_data3(length, 1., 0.)
        pos_writer.add_data3(length * .9, 1.075, 0.)
        pos_writer.add_data3(length * .9, .925, 0.)

        lines = GeomLines(Geom.UH_static)
        lines.add_vertices(0, 1)
        lines.add_vertices(1, 2)
        lines.add_vertices(1, 3)
        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        lines_node = GeomNode("angle_arrow")
        lines_node.add_geom(lines_geom)
        lines_np = parent.attach_new_node(lines_node)

        return lines_np

    def __create_trackball(self, parent, color):

        segments = 100
        angle = 2. * math.pi / segments

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("disc_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        disc = GeomTriangles(Geom.UH_static)

        for i in range(segments):
            x = math.cos(angle * i)
            z = math.sin(angle * i)
            pos_writer.add_data3(x, 0., z)
            col_writer.add_data4(color)

        for i in range(2, segments):
            disc.add_vertices(0, i - 1, i)

        disc_geom = Geom(vertex_data)
        disc_geom.add_primitive(disc)
        disc_node = GeomNode("trackball_disc_node")
        disc_node.add_geom(disc_geom)

        disc_np = parent.attach_new_node(disc_node)
        disc_np.set_billboard_point_eye()

        return disc_np

    def hilite_handle(self, color_id):

        if color_id not in self._handle_names:
            return

        hilited_handles = []
        handle_name = self._handle_names[color_id]

        if handle_name in self._handles["planes"]:
            hilited_handles.append(handle_name)

        if self._hilited_handles != hilited_handles:

            self.remove_hilite()
            self._hilited_handles = hilited_handles

            cyan = VBase4(0., 1., 1., 1.)

            for handle_name in hilited_handles:
                if handle_name == "trackball":
                    self._handles["planes"][handle_name].show(self._render_mask)
                else:
                    self._handles["planes"][handle_name].set_color(cyan)

    def remove_hilite(self):

        if self._hilited_handles:

            yellow = VBase4(1., 1., 0., 1.)
            yellow_alpha = VBase4(1., 1., 0., .25)

            for handle_name in self._hilited_handles:
                if handle_name == "trackball":
                    if handle_name != self._selected_axes:
                        self._handles["planes"][handle_name].hide(self._render_mask)
                else:
                    color = yellow if handle_name == self._selected_axes else self._axis_colors[handle_name]
                    self._handles["planes"][handle_name].set_color(color)

            if self._selected_axes == "trackball":
                self._hilited_handles = ["trackball"]
            else:
                self._hilited_handles = []

    def select_handle(self, color_id):

        if color_id not in self._handle_names:
            return

        axes = self._handle_names[color_id]

        if axes == "trackball":

            prev_constraints = GD["axis_constraints"]["rotate"]

            if prev_constraints != "trackball":
                GD["prev_axis_constraints_rotate"] = prev_constraints

        if axes in ("view", "trackball"):
            constraints = axes
        else:
            axis = "".join(a for a in "xyz" if a not in axes) if len(axes) == 2 else axes
            constraints = axis

        Mgr.update_app("axis_constraints", "rotate", constraints)

    def set_active_axes(self, axes):

        if len(axes) == 1:
            self._selected_axes = "xyz".replace(axes, "")
        else:
            self._selected_axes = axes

        self.remove_hilite()

        for plane in self._handles["planes"]:
            if plane == "trackball":
                if plane == self._selected_axes:
                    self._handles["planes"][plane].show(self._render_mask)
            elif plane == self._selected_axes:
                self._handles["planes"][plane].set_color(VBase4(1., 1., 0., 1.))
            else:
                self._handles["planes"][plane].set_color(self._axis_colors[plane])

        for axis_np in self._center_axes.values():
            axis_np.clear_color_scale()

        if self._selected_axes == "view":
            self._angle_disc_pivot.set_hpr(0., 0., 0.)
            self._angle_disc_pivot.set_billboard_point_eye(GD.cam(), 0.)
            self._angle_disc.set_hpr(0., 0., 0.)
            self._angle_clip_root.set_hpr(0., 0., 0.)
        else:
            self._angle_disc_pivot.clear_billboard()

        self.__update_angle_disc()

    def __update_angle_disc(self):

        if self._selected_axes in ("view", "trackball"):
            return

        axis1, axis2 = self._selected_axes
        axis = "xyz".replace(axis1, "").replace(axis2, "")
        axis_index = "xyz".index(axis)
        axis1_index = axis_index - 2
        axis2_index = axis_index - 1
        col_scale = VBase4(1., 1., 1., 1.)
        col_scale[axis_index] = 4.
        self._center_axes[axis].set_color_scale(col_scale)
        axis1_vec = V3D()
        axis1_vec[axis1_index] = 1.
        axis2_vec = V3D()
        axis2_vec[axis2_index] = 1.
        axis1_vec = V3D(self._origin.get_relative_vector(self._center_axis_root, axis1_vec))
        axis2_vec = V3D(self._origin.get_relative_vector(self._center_axis_root, axis2_vec))
        axis_vec = axis1_vec ** axis2_vec
        self._angle_disc_pivot.look_at(Point3(axis_vec))

    def __get_trackball_data(self, screen_pos):

        cam = GD.cam()
        lens_type = GD.cam.lens_type
        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.world.get_relative_point(cam, point)
        cam_pos = cam.get_pos(GD.world)

        intersection_point = Point3()

        if not self._screen_plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        if lens_type == "persp":
            # due to the billboard effect applied to the transf_gizmo_root, the correct
            # position of the origin cannot be retrieved from self._origin, so it needs
            # to be computed explicitly
            vec = Mgr.get("transf_gizmo").pos - cam_pos
            vec.normalize()
            origin_pos = cam_pos + vec * 2.
        else:
            origin_pos = Mgr.get("transf_gizmo").pos

        vec = intersection_point - origin_pos
        vec = V3D(cam.get_relative_vector(GD.world, vec))

        vec_length = vec.length()
        radians = 0.
        radius = self._radius * (1. if lens_type == "persp" else 200.)

        if vec_length > radius:
            radians = (vec_length - radius) / radius
            vec.normalize()
            vec *= radius

        # The vector pointing from the center of the trackball to the mouse is an
        # orthogonal projection of the vector needed; the y-component needs to be
        # computed such that the vector length equals the trackball radius.

        length_squared = min(radius ** 2., vec.length_squared())
        vec[1] = - (radius ** 2. - length_squared) ** .5
        vec.normalize()

        return vec, radians

    def get_point_at_screen_pos(self, screen_pos):

        cam = GD.cam()
        lens_type = GD.cam.lens_type
        point1 = Mgr.get("transf_gizmo").pos

        if self._selected_axes == "trackball":

            normal = GD.world.get_relative_vector(cam, Vec3.forward())

            if lens_type == "persp":
                cam_pos = cam.get_pos(GD.world)
                vec = point1 - cam_pos
                vec.normalize()
                point = cam_pos + vec * 2. # the world position of self._origin
            else:
                point = point1

            self._screen_plane = Plane(normal, point)

            return Point3()

        if self._selected_axes == "view":

            normal = GD.world.get_relative_vector(cam, Vec3.forward())
            plane = Plane(normal, point1)

        else:

            target = Mgr.get("transf_gizmo").target
            vec_coords = [0., 0., 0.]
            vec_coords["xyz".index(self._selected_axes[0])] = 1.
            axis_vec = GD.world.get_relative_vector(target, Vec3(*vec_coords))
            point2 = point1 + axis_vec
            vec_coords = [0., 0., 0.]
            vec_coords["xyz".index(self._selected_axes[1])] = 1.
            axis_vec = GD.world.get_relative_vector(target, Vec3(*vec_coords))
            point3 = point1 + axis_vec

            plane = Plane(point1, point2, point3)

        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.world.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point

    def __init_rotation_angle(self, point):

        gizmo_pos = self._angle_disc_root.get_pos(GD.world)
        offset_vec = gizmo_pos - Mgr.get("transf_gizmo").pos
        p = self._angle_disc_root.get_relative_point(GD.world, point + offset_vec)
        self._angle_clip_root.look_at(p)
        self._angle_disc.look_at(p)

        if self._selected_axes == "view":
            self._angle_disc.set_scale(self._screen_handle_radius)

        self._angle_disc.show()
        self._rotation_started = True

    def __reset_rotation_angle(self):

        self._clip_plane_neg_angle.set_h(0.)
        self._clip_plane_pos_angle.set_h(0.)
        self._angle_disc.hide()

        if self._selected_axes == "view":
            self._angle_disc.set_scale(1.)

        self._angle = 0.
        self._rotation_started = False

    def __set_rotation_angle(self, angle):

        if self._rotation_started:

            self._rotation_started = False

            if angle > 180.:
                self._angle = angle - 360.
                self._angle_arrow.set_r(0.)
            else:
                self._angle = angle
                self._angle_arrow.set_r(180.)

        else:

            if angle > 180.:
                if 90. < self._angle <= 360.:
                    self._angle = angle
                else:
                    self._angle = angle - 360.
                    self._angle_arrow.set_r(0.)
            else:
                if -90. > self._angle >= -360.:
                    self._angle = angle - 360.
                else:
                    self._angle = angle
                    self._angle_arrow.set_r(180.)

        if self._angle < 0.:
            if abs(self._angle) > 180.:
                self._clip_plane_pos_angle.set_h(self._angle + 180.)
                self._clip_plane_neg_angle.set_h(180.)
            else:
                self._clip_plane_pos_angle.set_h(0.)
                self._clip_plane_neg_angle.set_h(self._angle)
        else:
            if abs(self._angle) > 180.:
                self._clip_plane_neg_angle.set_h(self._angle + 180.)
                self._clip_plane_pos_angle.set_h(180.)
            else:
                self._clip_plane_neg_angle.set_h(0.)
                self._clip_plane_pos_angle.set_h(self._angle)

    def adjust_to_lens(self, lens_type):

        bb_fx = self._billboard_fx[lens_type]

        for plane in ("xy", "xz", "yz"):
            self._handles["planes"][plane].set_effect(bb_fx[plane])
