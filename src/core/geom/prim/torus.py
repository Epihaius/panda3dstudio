from .base import *
from math import pi, sin, cos

VERT_SHADER = """
    #version 150 compatibility

    // Uniform inputs
    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat4 p3d_ModelViewMatrix;
    uniform float ring_radius;
    uniform float section_radius;

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
        vec3 pos_vec;
        vec3 section_center;
        float d;
        // original ring radius: 2.
        // original cross section radius: 1.
        pos_old = p3d_Vertex.xyz;
        // compute the horizontal distance to the vertex from the torus center
        d = sqrt(pos_old.x * pos_old.x + pos_old.y * pos_old.y);
        d = 2. / max(.0001, d);
        // compute the center of the cross section to which the vertex belongs
        section_center = vec3(pos_old.x * d, pos_old.y * d, 0.);
        pos_vec = pos_old - section_center;
        // the length of pos_vec should be 1. (the original cross section radius),
        // so it can be multiplied by the new cross section radius without prior
        // normalization
        pos_vec *= section_radius;
        // compute the new section center, keeping in mind that the original ring
        // radius equals 2.
        section_center *= .5 * ring_radius;
        // get the new vertex position by adding the updated pos_vec to the new
        // cross section center
        pos_new = section_center + pos_vec;
        flat_color = p3d_Color;

        gl_Position = p3d_ModelViewProjectionMatrix * vec4(pos_new, 1.);
        v = (p3d_ModelViewMatrix * vec4(pos_new, 1.)).xyz;
        texcoord = p3d_MultiTexCoord0;
        mynormal = normalize(gl_NormalMatrix * p3d_Normal);
    }
"""


class TorusManager(PrimitiveManager):

    def __init__(self):

        PrimitiveManager.__init__(self, "torus")

        self._dragged_point = Point3()
        self._section_radius_vec = V3D()
        self._draw_plane = None

        self.set_property_default("radius_ring", 2.)
        self.set_property_default("radius_section", 1.)
        self.set_property_default("smoothness", True)
        self.set_property_default("segments", {"ring": 24, "section": 12})  # minimum = 3

        Mgr.accept("inst_create_torus", self.create_instantly)

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1)
        creation_phases.append(creation_phase)
        creation_phase = (self.__start_creation_phase2, self.__creation_phase2)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "torus"
        status_text["phase1"] = "draw out the ring"
        status_text["phase2"] = "draw out the cross section"

        return PrimitiveManager.setup(self, creation_phases, status_text)

    def apply_default_size(self, prim):

        prop_defaults = self.get_property_defaults()
        prim.update_creation_size(prop_defaults["radius_ring"], prop_defaults["radius_section"],
                                  finalize=True)

    def init_primitive(self, model):

        prim = Torus(model)
        prop_defaults = self.get_property_defaults()
        prim.create(prop_defaults["segments"], prop_defaults["smoothness"])

        return prim

    def __start_creation_phase1(self):
        """ Start drawing out torus ring """

        cam_pos = self.cam().get_pos(self.world)
        lens_type = self.cam.lens_type

        # initialize the section radius, based on ...
        if lens_type == "persp":
            # ... the distance of the torus center to the camera
            section_radius = (self.get_origin_pos() - cam_pos).length() * .01
        else:
            # ... camera zoom
            section_radius = self.cam.zoom * 5.

        origin = self.get_primitive().get_origin()
        shader = Shader.make(Shader.SL_GLSL, VERT_SHADER, FRAG_SHADER)
        origin.set_shader(shader, 1)
        origin.set_shader_input("ring_radius", 2.)
        origin.set_shader_input("section_radius", section_radius)

    def __creation_phase1(self):
        """ Draw out torus ring """

        screen_pos = self.mouse_watcher.get_mouse()
        point = Mgr.get(("grid", "point_at_screen_pos"), screen_pos)

        if not point:
            return

        grid_origin = Mgr.get(("grid", "origin"))
        self._dragged_point = self.world.get_relative_point(grid_origin, point)
        ring_radius = (self.get_origin_pos() - point).length()
        self.get_primitive().update_creation_size(ring_radius)

    def __start_creation_phase2(self):
        """ Start drawing out torus cross section """

        cam = self.cam()
        origin_pos = self.get_primitive().get_model().get_origin().get_pos(self.world)
        ring_radius_vec = V3D(self._dragged_point - origin_pos)
        cam_forward_vec = V3D(self.world.get_relative_vector(cam, Vec3.forward()))
        plane = Plane(cam_forward_vec, Point3())
        self._section_radius_vec = plane.project(ring_radius_vec).normalized()
        self._draw_plane = Plane(cam_forward_vec, self._dragged_point)

    def __creation_phase2(self):
        """ Draw out torus cross section """

        if not self.mouse_watcher.has_mouse():
            return

        screen_pos = self.mouse_watcher.get_mouse()
        cam = self.cam()

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)
        near_point = rel_pt(near_point)
        far_point = rel_pt(far_point)
        point = Point3()

        if not self._draw_plane.intersects_line(point, near_point, far_point):
            return

        section_radius = (point - self._dragged_point).project(self._section_radius_vec).length()
        prim = self.get_primitive()
        prim.update_creation_size(section_radius=section_radius)


class Torus(Primitive):

    def __init__(self, model):

        prop_ids = ["segments", "radius_ring", "radius_section", "smoothness"]

        Primitive.__init__(self, "torus", model, prop_ids)

        self._segments = {"ring": 3, "section": 3}
        self._ring_radius = 0.
        self._section_radius = 0.
        self._is_smooth = True
        self._smoothing = {}

    def define_geom_data(self):

        geom_data = []
        positions = []
        uvs = []

        segments = self._segments
        segs_r = segments["ring"]
        segs_s = segments["section"]
        smooth = self._is_smooth
        smoothing_ids = [(0, smooth)]

        angle_h = 2. * pi / segs_r
        angle_v = 2. * pi / segs_s

        # Define vertex data

        vert_id = 0

        for i in xrange(segs_s):

            z = cos(angle_v * i)

            r2 = 2. + sin(angle_v * i)
            v = 1. * i / segs_s

            for j in xrange(segs_r + 1):

                if j < segs_r:
                    x = r2 * cos(angle_h * j)
                    y = r2 * sin(angle_h * j)
                    pos = (x, y, z)
                    pos_obj = PosObj(pos)
                else:
                    pos_obj = positions[vert_id - segs_r]

                positions.append(pos_obj)

                u = 1. * j / segs_r
                uvs.append((u, 1. - v))

                vert_id += 1

        positions.extend(positions[:segs_r + 1])

        for u, v in uvs[:segs_r + 1]:
            uvs.append((u, 0.))

        # Define quadrangular faces

        for i in xrange(segs_s):

            s = segs_r + 1
            k = i * s

            for j in xrange(segs_r):

                vi1 = k + j
                vi2 = vi1 + s
                vi3 = vi2 + 1
                vi4 = vi1 + 1
                vert_ids = (vi1, vi2, vi3)
                vert_data = []

                def get_normal(vi):

                    x, y, z = positions[vi]
                    pos = Point3(x, y, z)
                    vec = Vec3(x, y, 0.)
                    section_center_pos = Point3(vec.normalized() * 2.)
                    normal = pos - section_center_pos

                    return normal

                if not smooth:
                    plane = Plane(*[Point3(*positions[vi]) for vi in vert_ids])
                    poly_normal = plane.get_normal()

                for vi in vert_ids:
                    pos = positions[vi]
                    normal = get_normal(vi) if smooth else poly_normal
                    uv = uvs[vi]
                    vert_data.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

                tri_data1 = {"verts": vert_data}

                vert_ids = (vi1, vi3, vi4)
                vert_data = []

                for vi in vert_ids:
                    pos = positions[vi]
                    normal = get_normal(vi) if smooth else poly_normal
                    uv = uvs[vi]
                    vert_data.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

                tri_data2 = {"verts": vert_data}

                tris = (tri_data1, tri_data2)  # quadrangular face
                poly_data = {"tris": tris, "smoothing": smoothing_ids}
                geom_data.append(poly_data)

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

        # original ring radius: 2.
        # original cross section radius: 1.
        pos_tmp = Point3(pos_old)
        pos_tmp.z = 0.
        # compute the horizontal distance to the vertex from the torus center
        d = pos_tmp.length()
        d = 2. / max(.0001, d)
        # compute the center of the cross section to which the vertex belongs
        section_center = Vec3(pos_old.x * d, pos_old.y * d, 0.)
        # compute the vector pointing from the center of the cross section to
        # the vertex
        pos_vec = pos_old - section_center
        # the length of pos_vec should be 1. (the original cross section radius),
        # so it can be multiplied by the new cross section radius without prior
        # normalization
        pos_vec *= self._section_radius
        # compute the new section center, keeping in mind that the original ring
        # radius equals 2.
        section_center *= .5 * self._ring_radius
        # get the new vertex position by adding the updated pos_vec to the new
        # cross section center
        pos_new = Point3(section_center + pos_vec)

        return pos_new

    def __update_size(self):

        self.reset_initial_coords()
        self.get_geom_data_object().reposition_vertices(self.__set_new_vertex_position)
        self.get_geom_data_object().update_poly_centers()
        self.get_model().get_bbox().update(*self.get_origin().get_tight_bounds())

    def update_creation_size(self, ring_radius=None, section_radius=None, finalize=False):

        origin = self.get_origin()

        if ring_radius is not None:

            r = max(ring_radius, .001)

            if self._ring_radius != r:

                self._ring_radius = r

                if not finalize:
                    origin.set_shader_input("ring_radius", r)

        if section_radius is not None:

            r = max(section_radius, .001)

            if self._section_radius != r:

                self._section_radius = r

                if not finalize:
                    origin.set_shader_input("section_radius", r)

        if finalize:
            self.__update_size()

    def set_ring_radius(self, radius):

        if self._ring_radius == radius:
            return False

        self._ring_radius = radius

        return True

    def set_section_radius(self, radius):

        if self._section_radius == radius:
            return False

        self._section_radius = radius

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
                data.update(self.get_geom_data_object().get_data_to_store("subobj_change", info="rebuild"))
            elif prop_id == "smoothness":
                data.update(self.get_geom_data_object().get_data_to_store("prop_change", "smoothing"))
            elif prop_id in ("radius_ring", "radius_section"):
                data.update(self.get_geom_data_object().get_property_to_store("subobj_transform",
                                                                              "prop_change", "all"))

            return data

        return Primitive.get_data_to_store(self, event_type, prop_id)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "torus", prop_id,
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

        elif prop_id == "radius_ring":

            change = self.set_ring_radius(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("upd_vert_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.get_model().update_group_bbox()
                update_app()

            return change

        elif prop_id == "radius_section":

            change = self.set_section_radius(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("upd_vert_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.get_model().update_group_bbox()
                update_app()

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
        elif prop_id == "radius_ring":
            return self._ring_radius
        elif prop_id == "radius_section":
            return self._section_radius
        elif prop_id == "smoothness":
            return self._is_smooth

    def finalize(self):

        origin = self.get_origin()
        render_state = origin.get_state()
        render_state = render_state.remove_attrib(ShaderAttrib.get_class_type())
        origin.set_state(render_state)
        origin.clear_shader_input("ring_radius")
        origin.clear_shader_input("section_radius")

        self.__update_size()

        Primitive.finalize(self, update_poly_centers=False)

    def is_valid(self):

        return min(self._ring_radius, self._section_radius) > .001


MainObjects.add_class(TorusManager)
