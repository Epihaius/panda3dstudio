from .base import *
from math import pi, sin, cos

VERT_SHADER = """
    #version 150 compatibility

    // Uniform inputs
    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat4 p3d_ModelViewMatrix;
    uniform float bottom_radius;
    uniform float top_radius;
    uniform float height;

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec4 p3d_Color;
    in vec2 p3d_MultiTexCoord0;
    in vec3 p3d_Normal;

    // Output to fragment shader
    out vec2 texcoord;
    out vec3 mynormal;
    out vec3 v;
    out vec4 flat_color;

    void main(void)
    {
        vec3 pos_old;
        vec3 pos_new;
        vec3 normal_new;
        vec3 up_vec;
        float height_abs;
        float z;
        float delta_radius;
        float epsilon;
        float new_dist;
        float radius;
        float h;

        // original radii: 1.
        // original height: 1.
        pos_old = p3d_Vertex.xyz;
        height_abs = abs(height);
        z = pos_old.z * height_abs;

        if (height < 0.) {
            z -= height_abs;
            delta_radius = top_radius - bottom_radius;
        }
        else {
            delta_radius = bottom_radius - top_radius;
        }

        epsilon = 1.e-010;

        if (abs(delta_radius) < epsilon) {

            new_dist = bottom_radius;

        }
        else {

            if (abs(bottom_radius) >= epsilon) {
                radius = bottom_radius;
            }
            else {
                radius = top_radius;
            }

            h = height_abs * radius / delta_radius;
            new_dist = (h - z) * radius / h;

        }

        pos_new = p3d_Vertex.xyz;
        pos_new.z = 0.;
        pos_new *= new_dist;
        pos_new.z = z;
        flat_color = p3d_Color;

        gl_Position = p3d_ModelViewProjectionMatrix * vec4(pos_new, 1.);
        v = (p3d_ModelViewMatrix * vec4(pos_new, 1.)).xyz;
        texcoord = p3d_MultiTexCoord0;
        normal_new = p3d_Normal.xyz;

        if (abs(normal_new.z) < epsilon) {
            normal_new *= height_abs;
            up_vec = vec3(0., 0., 1.) * delta_radius;
            normal_new += up_vec;
            normal_new = normalize(normal_new);
        }

        mynormal = normalize(gl_NormalMatrix * normal_new);
    }
"""


class ConeManager(PrimitiveManager):

    def __init__(self):

        PrimitiveManager.__init__(self, "cone")

        self._height_axis = V3D(0., 0., 1.)
        self._draw_plane = None
        self._draw_plane_normal = V3D()
        self._dragged_point = Point3()
        self._top = Point3()
        self._top_radius_vec = V3D()

        self.set_property_default("radius_bottom", 1.)
        self.set_property_default("radius_top", 0.)
        self.set_property_default("height", 1.)
        self.set_property_default("smoothness", True)
        self.set_property_default("segments", {"circular": 12, "height": 1, "caps": 1})
        # minimum circular segments = 3
        # minimum height segments = 1
        # minimum cap segments = 0: no caps

        Mgr.accept("inst_create_cone", self.create_instantly)

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1)
        creation_phases.append(creation_phase)
        creation_phase = (self.__start_creation_phase2, self.__creation_phase2)
        creation_phases.append(creation_phase)
        creation_phase = (self.__start_creation_phase3, self.__creation_phase3)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "cone"
        status_text["phase1"] = "draw out the base"
        status_text["phase2"] = "draw out the height"
        status_text["phase3"] = "draw out the top"

        return PrimitiveManager.setup(self, creation_phases, status_text)

    def apply_default_size(self, prim):

        prop_defaults = self.get_property_defaults()
        prim.update_creation_size(prop_defaults["radius_bottom"], prop_defaults["radius_top"],
                                  prop_defaults["height"], finalize=True)

    def init_primitive(self, model):

        prim = Cone(model)
        prop_defaults = self.get_property_defaults()
        prim.create(prop_defaults["segments"], prop_defaults["smoothness"])

        return prim

    def __start_creation_phase1(self):
        """ Start drawing out cone base """

        prim = self.get_primitive()
        origin = prim.get_model().get_origin()
        self._height_axis = self.world.get_relative_vector(origin, V3D(0., 0., 1.))
        origin = prim.get_origin()
        shader = Shader.make(Shader.SL_GLSL, VERT_SHADER, FRAG_SHADER)
        origin.set_shader(shader, 1)
        origin.set_shader_input("bottom_radius", 1.)
        origin.set_shader_input("top_radius", 1.)
        origin.set_shader_input("height", .001)

    def __creation_phase1(self):
        """ Draw out cone base """

        screen_pos = self.mouse_watcher.get_mouse()
        point = Mgr.get(("grid", "point_at_screen_pos"), screen_pos)

        if not point:
            return

        grid_origin = Mgr.get(("grid", "origin"))
        self._dragged_point = self.world.get_relative_point(grid_origin, point)
        radius = (self.get_origin_pos() - point).length()
        self.get_primitive().update_creation_size(radius, radius)

    def __start_creation_phase2(self):
        """ Start drawing out cone height """

        cam = self.cam()
        cam_forward_vec = self.world.get_relative_vector(cam, Vec3.forward())
        normal = V3D(cam_forward_vec - cam_forward_vec.project(self._height_axis))

        # If the plane normal is the null vector, the axis must be parallel to
        # the forward camera direction. In this case, a new normal can be chosen
        # arbitrarily, e.g. a horizontal vector perpendicular to the axis.

        if normal.length_squared() < .0001:

            x, y, z = self._height_axis

            # if the height axis is nearly vertical, any horizontal vector will
            # qualify as plane normal, e.g. a vector pointing in the positive
            # X-direction; otherwise, the plane normal can be computed as
            # perpendicular to the axis
            normal = V3D(1., 0., 0.) if max(abs(x), abs(y)) < .0001 else V3D(y, -x, 0.)

        self._draw_plane = Plane(normal, self._dragged_point)

        if self.cam.lens_type == "persp":

            cam_pos = cam.get_pos(self.world)

            if normal * V3D(self._draw_plane.project(cam_pos) - cam_pos) < .0001:
                normal *= -1.

        self._draw_plane_normal = normal

    def __creation_phase2(self):
        """ Draw out cone height """

        if not self.mouse_watcher.has_mouse():
            return

        screen_pos = self.mouse_watcher.get_mouse()
        cam = self.cam()
        lens_type = self.cam.lens_type

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)
        near_point = rel_pt(near_point)
        far_point = rel_pt(far_point)

        if lens_type == "persp":
            # the height cannot be calculated if the cursor points away from the plane
            # in which it is drawn out
            if V3D(far_point - near_point) * self._draw_plane_normal < .0001:
                return

        if not self._draw_plane.intersects_line(self._dragged_point, near_point, far_point):
            return

        prim = self.get_primitive()
        origin = prim.get_model().get_origin()
        height = origin.get_relative_point(self.world, self._dragged_point)[2]
        prim.update_creation_size(height=height)

    def __start_creation_phase3(self):
        """ Start drawing out cone top """

        prim = self.get_primitive()
        origin = prim.get_model().get_origin()
        height = prim.get_property("height")
        self._top = origin.get_pos(self.world) + self._height_axis * height
        cam = self.cam()
        cam_pos = cam.get_pos(self.world)
        cam_forward_vec = V3D(self.world.get_relative_vector(cam, Vec3.forward()))
        self._draw_plane = Plane(cam_forward_vec, self._top)
        point = Point3()
        self._draw_plane.intersects_line(point, cam_pos, self._dragged_point)
        self._top_radius_vec = V3D((point - self._top).normalized())

    def __creation_phase3(self):
        """ Draw out cone top """

        if not self.mouse_watcher.has_mouse():
            return

        screen_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        cam = self.cam()
        rel_pt = lambda point: self.world.get_relative_point(cam, point)
        near_point = rel_pt(near_point)
        far_point = rel_pt(far_point)

        if not self._draw_plane.intersects_line(point, near_point, far_point):
            return

        vec = V3D(point - self._top)

        if vec * self._top_radius_vec <= 0.:
            top_radius = 0.
        else:
            top_radius = (vec.project(self._top_radius_vec)).length()

        self.get_primitive().update_creation_size(top_radius=top_radius)


class Cone(Primitive):

    def __init__(self, model):

        prop_ids = ["segments", "radius_bottom", "radius_top", "height", "smoothness"]

        Primitive.__init__(self, "cone", model, prop_ids)

        self._segments = {"circular": 3, "height": 1, "caps": 0}
        self._bottom_radius = 0.
        self._top_radius = 0.
        self._height = 0.
        self._is_smooth = True
        self._smoothing = {}

    def define_geom_data(self):

        geom_data = []
        positions_main = []
        uvs_main = []

        segments = self._segments
        segs_c = segments["circular"]
        segs_h = segments["height"]
        segs_cap = segments["caps"]
        smooth = self._is_smooth
        smoothing_ids = [(0, smooth)]

        angle = 2 * pi / segs_c

        # Define vertex data

        vert_id = 0

        for i in xrange(segs_h + 1):

            z = 1. - 1. * i / segs_h

            for j in xrange(segs_c + 1):

                angle_h = angle * j
                x = cos(angle_h)
                y = sin(angle_h)

                if j < segs_c:
                    pos = (x, y, z)
                    pos_obj = PosObj(pos)
                else:
                    pos_obj = positions_main[vert_id - segs_c]

                positions_main.append(pos_obj)

                u = 1. * j / segs_c
                uvs_main.append((u, z))

                vert_id += 1

        if segs_cap:

            positions_cap_lower = positions_main[-segs_c - 1:]
            positions_cap_upper = positions_main[:segs_c + 1]
            positions_cap_upper.reverse()
            uvs_cap_lower = []
            uvs_cap_upper = []

            def add_cap_data(cap):

                # Add data related to vertices along the cap segments

                if cap == "lower":
                    positions = positions_cap_lower
                    uvs = uvs_cap_lower
                    z = 0.
                    y_factor = 1.
                else:
                    positions = positions_cap_upper
                    uvs = uvs_cap_upper
                    z = 1.
                    y_factor = -1.

                vert_id = segs_c + 1

                for j in xrange(segs_c + 1):
                    angle_h = angle * j
                    u = .5 + cos(angle_h) * .5
                    v = .5 - sin(angle_h) * .5
                    uvs.append((u, v))

                for i in xrange(1, segs_cap):

                    r = 1. - 1. * i / segs_cap

                    for j in xrange(segs_c + 1):

                        angle_h = angle * j
                        x = r * cos(angle_h)
                        y = r * sin(angle_h) * y_factor

                        if j < segs_c:
                            pos = (x, y, z)
                            pos_obj = PosObj(pos)
                        else:
                            pos_obj = positions[vert_id - segs_c]

                        positions.append(pos_obj)

                        uvs.append((.5 + x * .5, .5 - y * y_factor * .5))

                        vert_id += 1

                # Add data related to center vertex of cap

                pos = (0., 0., z)
                pos_obj = PosObj(pos)
                positions.append(pos_obj)
                uvs.append((.5, .5))

            add_cap_data("lower")
            add_cap_data("upper")

        # Define faces

        z_vec = V3D(0., 0., 1.)

        def convert_pos_to_normal(vert_index):

            normal = Vec3(*positions_main[vert_index])
            normal[2] = 0.
            normal.normalize()

            return normal

        for i in xrange(segs_h):

            s = segs_c + 1
            k = i * s

            for j in xrange(segs_c):

                vi1 = k + j
                vi2 = vi1 + s
                vi3 = vi2 + 1
                vi4 = vi1 + 1
                vert_ids = (vi1, vi2, vi3)
                vert_data = []

                if not smooth:
                    plane = Plane(*[Point3(*positions_main[vi]) for vi in vert_ids])
                    poly_normal = plane.get_normal()

                get_normal = lambda i: convert_pos_to_normal(i) if smooth else poly_normal

                for vi in vert_ids:
                    pos = positions_main[vi]
                    normal = get_normal(vi)
                    uv = uvs_main[vi]
                    vert_data.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

                tri_data1 = {"verts": vert_data}

                vert_ids = (vi1, vi3, vi4)
                vert_data = []

                for vi in vert_ids:
                    pos = positions_main[vi]
                    normal = get_normal(vi)
                    uv = uvs_main[vi]
                    vert_data.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

                tri_data2 = {"verts": vert_data}

                tris = (tri_data1, tri_data2)  # quadrangular face
                poly_data = {"tris": tris, "smoothing": smoothing_ids}
                geom_data.append(poly_data)

        if segs_cap:

            def define_cap_faces(cap):

                if cap == "lower":
                    positions = positions_cap_lower
                    uvs = uvs_cap_lower
                    sign = 1.
                    smoothing_grp = 1
                else:
                    positions = positions_cap_upper
                    uvs = uvs_cap_upper
                    sign = -1.
                    smoothing_grp = 2

                # Define quadrangular faces of cap

                for i in xrange(segs_cap - 1):

                    s = segs_c + 1
                    k = i * s

                    for j in xrange(segs_c):

                        vi1 = k + j
                        vi2 = vi1 + s
                        vi3 = vi2 + 1
                        vi4 = vi1 + 1
                        vert_ids = (vi1, vi2, vi3)
                        vert_data = []

                        for vi in vert_ids:
                            pos = positions[vi]
                            normal = Vec3(0., 0., -1. * sign)
                            uv = uvs[vi]
                            vert_data.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

                        tri_data1 = {"verts": vert_data}

                        vert_ids = (vi1, vi3, vi4)
                        vert_data = []

                        for vi in vert_ids:
                            pos = positions[vi]
                            normal = Vec3(0., 0., -1. * sign)
                            uv = uvs[vi]
                            vert_data.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

                        tri_data2 = {"verts": vert_data}

                        tris = (tri_data1, tri_data2)  # quadrangular face
                        poly_data = {"tris": tris, "smoothing": [(smoothing_grp, smooth)]}
                        geom_data.append(poly_data)

                # Define triangular faces at center of cap

                s = segs_c + 1
                vi1 = segs_cap * s

                for j in xrange(segs_c):

                    vi2 = vi1 - 1 - j
                    vi3 = vi2 - 1
                    vert_ids = (vi1, vi2, vi3)
                    vert_data = []

                    for vi in vert_ids:
                        pos = positions[vi]
                        normal = Vec3(0., 0., -1. * sign)
                        uv = uvs[vi]
                        vert_data.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

                    tri_data = {"verts": vert_data}

                    tris = (tri_data,)  # triangular face
                    poly_data = {"tris": tris, "smoothing": [(smoothing_grp, smooth)]}
                    geom_data.append(poly_data)

            define_cap_faces("lower")
            define_cap_faces("upper")

        return geom_data

    def update(self, data):

        self._smoothing = data["smoothing"]

    def create(self, segments, is_smooth):

        self._segments = segments
        self._is_smooth = is_smooth

        Primitive.create(self)

        self.update_initial_coords()

    def set_segments(self, segments):

        if self._segments == segments:
            return False

        self._segments = segments

        return True

    def __set_new_vertex_position(self, pos_old):

        # original radii: 1.
        # original height: 1.
        height = abs(self._height)
        z = pos_old.z * height

        if self._height < 0.:
            z -= height
            delta_radius = self._top_radius - self._bottom_radius
        else:
            delta_radius = self._bottom_radius - self._top_radius

        epsilon = 1.e-010

        if abs(delta_radius) < epsilon:

            new_dist = self._bottom_radius

        else:

            if abs(self._bottom_radius) >= epsilon:
                radius = self._bottom_radius
            else:
                radius = self._top_radius

            h = height * radius / delta_radius
            new_dist = (h - z) * radius / h

        pos_new = Point3(pos_old)
        pos_new.z = 0.
        pos_new *= new_dist
        pos_new.z = z

        return pos_new

    def __update_size(self):

        self.reset_initial_coords()
        self.get_geom_data_object().reposition_vertices(self.__set_new_vertex_position)
        self.get_geom_data_object().update_poly_centers()
        self.get_model().get_bbox().update(*self.get_origin().get_tight_bounds())

    def update_creation_size(self, bottom_radius=None, top_radius=None, height=None, finalize=False):

        origin = self.get_origin()

        if bottom_radius is not None:

            r = max(bottom_radius, .001)

            if self._bottom_radius != r:

                self._bottom_radius = r

                if not finalize:
                    origin.set_shader_input("bottom_radius", r)

        if top_radius is not None:

            r = max(top_radius, 0.)

            if self._top_radius != r:

                self._top_radius = r

                if not finalize:
                    origin.set_shader_input("top_radius", r)

        if height is not None:

            abs_h = max(abs(height), .001)
            h = -abs_h if height < 0. else abs_h

            if self._height != h:

                self._height = h

                if not finalize:
                    origin.set_shader_input("height", h)

        if finalize:
            self.__update_size()

    def set_bottom_radius(self, radius):

        if self._bottom_radius == radius:
            return False

        self._bottom_radius = radius

        return True

    def set_top_radius(self, radius):

        if self._top_radius == radius:
            return False

        self._top_radius = radius

        return True

    def set_height(self, height):

        if self._height == height:
            return False

        self._height = height

        return True

    def set_smooth(self, is_smooth=True):

        if self._is_smooth == is_smooth:
            return False

        self._is_smooth = is_smooth

        return True

    def get_data_to_store(self, event_type, prop_id=""):

        if event_type == "prop_change" and prop_id in self.get_type_property_ids():

            data = {}
            data[prop_id] = {"main": self.get_property(prop_id)}

            if prop_id == "segments":
                data.update(self.get_geom_data_object().get_data_to_store("subobj_change",
                                                                          info="rebuild"))
            elif prop_id == "smoothness":
                data.update(self.get_geom_data_object().get_data_to_store("prop_change",
                                                                          "smoothing"))
            elif prop_id in ("radius_bottom", "radius_top", "height"):
                data.update(self.get_geom_data_object().get_property_to_store("subobj_transform",
                                                                              "prop_change", "all"))

            return data

        return Primitive.get_data_to_store(self, event_type, prop_id)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "cone", prop_id,
                                self.get_property(prop_id, True))

        obj_id = self.get_toplevel_object().get_id()

        if prop_id == "segments":

            if restore:
                segments = value["count"]
                self.restore_initial_coords(value["pos_data"])
            else:
                segments = self._segments.copy()
                segments.update(value)

            change = self.set_segments(segments)

            if change:

                if not restore:
                    self.recreate_geometry()

                update_app()

            return change

        elif prop_id == "radius_bottom":

            change = self.set_bottom_radius(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("upd_vert_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.get_model().update_group_bbox()
                update_app()

                if not restore:
                    task = self.get_geom_data_object().init_poly_normals
                    PendingTasks.add(task, "upd_vert_normals", "object", id_prefix=obj_id)

            return change

        elif prop_id == "radius_top":

            change = self.set_top_radius(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("upd_vert_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.get_model().update_group_bbox()
                update_app()

                if not restore:
                    task = self.get_geom_data_object().init_poly_normals
                    PendingTasks.add(task, "upd_vert_normals", "object", id_prefix=obj_id)

            return change

        elif prop_id == "height":

            change = self.set_height(value)

            if change:

                task = self.__update_size
                sort = PendingTasks.get_sort("upd_vert_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.get_model().update_group_bbox()
                update_app()

                if not restore:
                    task = self.get_geom_data_object().init_poly_normals
                    PendingTasks.add(task, "upd_vert_normals", "object", id_prefix=obj_id)

            return change

        elif prop_id == "smoothness":

            change = self.set_smooth(value)

            if change and not restore:
                task = lambda: self.get_geom_data_object().set_smoothing(self._smoothing.itervalues()
                                                                         if value else None)
                PendingTasks.add(task, "smooth_polys", "object", id_prefix=obj_id)

            if change:
                update_app()

            return change

        else:

            return Primitive.set_property(self, prop_id, value, restore)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "segments":
            if for_remote_update:
                return self._segments
            else:
                return {"count": self._segments, "pos_data": self.get_initial_coords()}
        elif prop_id == "radius_bottom":
            return self._bottom_radius
        elif prop_id == "radius_top":
            return self._top_radius
        elif prop_id == "height":
            return self._height
        elif prop_id == "smoothness":
            return self._is_smooth

    def is_valid(self):

        return min(max(self._bottom_radius, self._top_radius), abs(self._height)) > .001

    def finalize(self):

        origin = self.get_origin()
        render_state = origin.get_state()
        render_state = render_state.remove_attrib(ShaderAttrib.get_class_type())
        origin.set_state(render_state)
        origin.clear_shader_input("bottom_radius")
        origin.clear_shader_input("top_radius")
        origin.clear_shader_input("height")

        self.__update_size()

        Primitive.finalize(self, update_poly_centers=False)


MainObjects.add_class(ConeManager)
