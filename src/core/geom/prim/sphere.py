from .base import *
from math import pi, sin, cos


class SphereManager(PrimitiveManager):

    def __init__(self):

        PrimitiveManager.__init__(self, "sphere")

        self._draw_plane = None

        self.set_property_default("radius", 1.)
        self.set_property_default("segments", 12)  # minimum = 4
        self.set_property_default("smoothness", True)

        Mgr.accept("inst_create_sphere", self.create_instantly)

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "sphere"
        status_text["phase1"] = "draw out the sphere"

        return PrimitiveManager.setup(self, creation_phases, status_text)

    def apply_default_size(self, prim):

        prop_defaults = self.get_property_defaults()
        prim.update_creation_radius(prop_defaults["radius"], finalize=True)

    def init_primitive(self, model):

        prim = Sphere(model)
        prim.create(self.get_property_defaults()["segments"],
                    self.get_property_defaults()["smoothness"])

        return prim

    def __start_creation_phase1(self):
        """ Start drawing out sphere """

        # Create the plane parallel to the camera and going through the sphere
        # center, used to determine the radius drawn out by the user.

        prim = self.get_primitive()
        normal = self.world.get_relative_vector(self.cam(), Vec3.forward())
        grid_origin = Mgr.get(("grid", "origin"))
        point = self.world.get_relative_point(grid_origin, self.get_origin_pos())
        self._draw_plane = Plane(normal, point)

    def __creation_phase1(self):
        """ Draw out sphere """

        screen_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(self.cam(), point)
        near_point = rel_pt(near_point)
        far_point = rel_pt(far_point)
        intersection_point = Point3()
        self._draw_plane.intersects_line(intersection_point, near_point, far_point)
        grid_origin = Mgr.get(("grid", "origin"))
        point = self.world.get_relative_point(grid_origin, self.get_origin_pos())
        radius = max(.001, (intersection_point - point).length())
        self.get_primitive().update_creation_radius(radius)


class Sphere(Primitive):

    def __init__(self, model):

        prop_ids = ["segments", "radius", "smoothness"]

        Primitive.__init__(self, "sphere", model, prop_ids)

        self._segments = 4
        self._radius = 0.
        self._is_smooth = True
        self._smoothing = {}

    def define_geom_data(self):

        geom_data = []
        positions_main = []
        uvs_main = []

        segments = self._segments
        smooth = self._is_smooth
        smoothing_ids = [(0, smooth)]

        angle = 2 * pi / segments

        # Define vertex data

        vert_id = 0

        for i in xrange(1, segments // 2):

            z = cos(angle * i)

            r2 = sin(angle * i)
            v = 2. * i / segments

            for j in xrange(segments + 1):

                angle_h = angle * j
                x = r2 * cos(angle_h)
                y = r2 * sin(angle_h)

                if j < segments:
                    pos = (x, y, z)
                    pos_obj = PosObj(pos)
                else:
                    pos_obj = positions_main[vert_id - segments]

                positions_main.append(pos_obj)

                u = 1. * j / segments
                uvs_main.append((u, 1. - v))

                vert_id += 1

        positions_lower = positions_main[-segments - 1:]
        positions_upper = positions_main[:segments + 1]
        positions_upper.reverse()
        uvs_lower = uvs_main[-segments - 1:]
        uvs_upper = uvs_main[:segments + 1]
        uvs_upper.reverse()

        # Define quadrangular faces

        z_vec = V3D(0., 0., 1.)

        for i in xrange(1, segments // 2 - 1):

            s = segments + 1
            k = (i - 1) * s

            for j in xrange(segments):

                vi1 = k + j
                vi2 = vi1 + s
                vi3 = vi2 + 1
                vi4 = vi1 + 1
                vert_ids = (vi1, vi2, vi3)
                vert_data = []

                if not smooth:
                    plane = Plane(*[Point3(*positions_main[vi]) for vi in vert_ids])
                    poly_normal = plane.get_normal()

                get_normal = lambda vi: Vec3(*positions_main[vi]) if smooth else poly_normal

                for vi in vert_ids:
                    pos = positions_main[vi]
                    uv = uvs_main[vi]
                    normal = get_normal(vi)
                    normalV3D = V3D(normal)
                    tangent = z_vec ** normalV3D
                    bitangent = normalV3D ** tangent
                    tangent.normalize()
                    bitangent.normalize()
                    tangent_space = (tangent, bitangent)
                    vert_data.append({"pos": pos, "normal": normal, "uvs": {0: uv},
                                      "tangent_space": tangent_space})

                tri_data1 = {"verts": vert_data, "tangent_space": None}

                vert_ids = (vi1, vi3, vi4)
                vert_data = []

                for vi in vert_ids:
                    pos = positions_main[vi]
                    uv = uvs_main[vi]
                    normal = get_normal(vi)
                    normalV3D = V3D(normal)
                    tangent = z_vec ** normalV3D
                    bitangent = normalV3D ** tangent
                    tangent.normalize()
                    bitangent.normalize()
                    tangent_space = (tangent, bitangent)
                    vert_data.append({"pos": pos, "normal": normal, "uvs": {0: uv},
                                      "tangent_space": tangent_space})

                tri_data2 = {"verts": vert_data, "tangent_space": None}

                tris = (tri_data1, tri_data2)  # quadrangular face
                poly_data = {"tris": tris, "smoothing": smoothing_ids}
                geom_data.append(poly_data)

        # Define triangular faces at top pole

        pole_pos = PosObj((0., 0., 1.))
        pole_normal = Vec3(0., 0., 1.)
        tangent = Vec3(1., 0., 0.)
        bitangent = Vec3(0., -1., 0.)
        pole_tangent_space = (tangent, bitangent)
        v = 1.

        for j in xrange(segments):

            vi2 = segments - j
            vi3 = vi2 - 1
            vert_ids = (vi2, vi3)

            if not smooth:
                cap_positions = [Point3(*positions_upper[vi]) for vi in vert_ids]
                cap_positions.append(Point3(*pole_pos))
                plane = Plane(*cap_positions)
                poly_normal = plane.get_normal()

            u = 1. * j / segments
            vert_props = {"pos": pole_pos, "normal": pole_normal if smooth else poly_normal,
                          "uvs": {0: (u, v)}, "tangent_space": pole_tangent_space}
            vert_data = [vert_props]

            get_normal = lambda vi: Vec3(*positions_upper[vi]) if smooth else poly_normal

            for vi in vert_ids:
                vert_data.append({"pos": positions_upper[vi], "normal": get_normal(vi),
                                  "uvs": {0: uvs_upper[vi]}})

            tri_data = {"verts": vert_data, "tangent_space": None}
            tris = (tri_data,)  # triangular face
            poly_data = {"tris": tris, "smoothing": smoothing_ids}
            geom_data.append(poly_data)

        # Define triangular faces at bottom pole

        pole_pos = PosObj((0., 0., -1.))
        pole_normal = Vec3(0., 0., -1.)
        tangent = Vec3(1., 0., 0.)
        bitangent = Vec3(0., 1., 0.)
        pole_tangent_space = (tangent, bitangent)
        v = 0.

        for j in xrange(segments):

            vi2 = segments - j
            vi3 = vi2 - 1
            vert_ids = (vi2, vi3)

            if not smooth:
                cap_positions = [Point3(*positions_lower[vi])  for vi in vert_ids]
                cap_positions.append(Point3(*pole_pos))
                plane = Plane(*cap_positions)
                poly_normal = plane.get_normal()

            u = 1. - 1. * j / segments
            vert_props = {"pos": pole_pos, "normal": pole_normal if smooth else poly_normal,
                          "uvs": {0: (u, v)}, "tangent_space": pole_tangent_space}
            vert_data = [vert_props]

            get_normal = lambda vi: Vec3(*positions_lower[vi]) if smooth else poly_normal

            for vi in vert_ids:
                vert_data.append({"pos": positions_lower[vi], "normal": get_normal(vi),
                                  "uvs": {0: uvs_lower[vi]}})

            tri_data = {"verts": vert_data, "tangent_space": None}
            tris = (tri_data,)  # triangular face
            poly_data = {"tris": tris, "smoothing": smoothing_ids}
            geom_data.append(poly_data)

        return geom_data

    def update(self, data):

        self._smoothing = data["smoothing"]

    def create(self, segments, is_smooth):

        self._segments = segments
        self._is_smooth = is_smooth

        Primitive.create(self)

        self.update_init_pos_data()

    def set_segments(self, segments):

        if self._segments == segments:
            return False

        self._segments = segments

        return True

    def __update_size(self):

        r = self._radius
        self.get_origin().set_scale(r)
        self.reset_init_pos_data()
        self.get_geom_data_object().bake_transform()
        self.get_geom_data_object().update_poly_centers()
        self.get_model().get_bbox().update(*self.get_origin().get_tight_bounds())

    def update_creation_radius(self, radius, finalize=False):

        r = max(radius, .001)

        if self._radius != r:
            self._radius = r
            self.__update_size() if finalize else self.get_origin().set_scale(r)

    def set_radius(self, radius):

        if self._radius == radius:
            return False

        self._radius = radius

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
            elif prop_id == "radius":
                data.update(self.get_geom_data_object().get_property_to_store("subobj_transform",
                                                                              "prop_change", "all"))

            return data

        return Primitive.get_data_to_store(self, event_type, prop_id)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "sphere", prop_id, self.get_property(prop_id, True))

        obj_id = self.get_toplevel_object().get_id()

        if prop_id == "segments":

            change = self.set_segments(value["count"] if restore else value)

            if change:
                if restore:
                    task = lambda: self.restore_init_pos_data(value["pos_data"])
                    sort = PendingTasks.get_sort("upd_vert_normals", "object") + 1
                    PendingTasks.add(task, "restore_pos_data", "object", sort, id_prefix=obj_id)
                else:
                    task = self.clear_geometry
                    task_id = "clear_geom_data"
                    PendingTasks.add(task, task_id, "object", id_prefix=obj_id)
                    task = self.recreate_geometry
                    task_id = "set_geom_data"
                    PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            if change:
                update_app()

            return change

        elif prop_id == "radius":

            change = self.set_radius(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("upd_vert_normals", "object") + 2
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
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
                return {"count": self._segments, "pos_data": self.get_init_pos_data()}
        elif prop_id == "radius":
            return self._radius
        elif prop_id == "smoothness":
            return self._is_smooth

    def is_valid(self):

        return self._radius > .001

    def finalize(self):

        self.__update_size()

        Primitive.finalize(self, update_poly_centers=False)


MainObjects.add_class(SphereManager)
