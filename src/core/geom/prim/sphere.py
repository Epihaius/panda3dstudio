from .base import *
from math import pi, sin, cos


class SphereManager(PrimitiveManager):

    def __init__(self):

        PrimitiveManager.__init__(self, "sphere", custom_creation=True)

        self._draw_plane = None

        self.set_property_default("radius", 1.)
        self.set_property_default("temp_segments", 8)  # minimum = 4
        self.set_property_default("segments", 12)  # minimum = 4
        self.set_property_default("smoothness", True)

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "sphere"
        status_text["phase1"] = "draw out the sphere"

        return PrimitiveManager.setup(self, creation_phases, status_text)

    def create_temp_primitive(self, color, pos):

        segs = self.get_property_defaults()["segments"]
        tmp_segs = self.get_property_defaults()["temp_segments"]
        segments = segs if segs < tmp_segs else tmp_segs
        is_smooth = self.get_property_defaults()["smoothness"]
        tmp_prim = TemporarySphere(segments, is_smooth, color, pos)

        return tmp_prim

    def create_primitive(self, model):

        prim = Sphere(model)
        segments = self.get_property_defaults()["segments"]
        poly_count, merged_vert_count = _get_mesh_density(segments)
        progress_steps = poly_count // 10 + poly_count // 50 + merged_vert_count // 20
        gradual = progress_steps > 100

        for step in prim.create(segments, self.get_property_defaults()["smoothness"]):
            if gradual:
                yield

        yield prim, gradual

    def init_primitive_size(self, prim, size=None):

        prop_defaults = self.get_property_defaults()
        radius = prop_defaults["radius"] if size is None else size
        prim.init_radius(radius)

    def __start_creation_phase1(self):
        """ Start drawing out sphere """

        # Create the plane parallel to the camera and going through the sphere
        # center, used to determine the radius drawn out by the user.

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
        self.get_temp_primitive().update_radius(radius)

    def create_custom_primitive(self, name, radius, segments, pos, rel_to_grid=False,
                                smooth=True, gradual=False):

        model_id = self.generate_object_id()
        model = Mgr.do("create_model", model_id, name, pos)

        if not rel_to_grid:
            pivot = model.get_pivot()
            pivot.clear_transform()
            pivot.set_pos(self.world, pos)

        next_color = self.get_next_object_color()
        model.set_color(next_color, update_app=False)
        prim = Sphere(model)

        for step in prim.create(segments, smooth):
            if gradual:
                yield

        prim.init_radius(radius)

        for step in prim.get_geom_data_object().finalize_geometry():
            if gradual:
                yield

        model.set_geom_object(prim)
        self.set_next_object_color()

        yield model


def _get_mesh_density(segments):

    poly_count = segments * (segments // 2)
    merged_vert_count = (segments - 2) // 2 * segments + 2

    return poly_count, merged_vert_count


def _define_geom_data(segments, smooth, temp=False):

    geom_data = []
    positions_main = []

    if not temp:
        uvs_main = []
        smoothing_ids = [(0, smooth)]

    angle = 2 * pi / segments

    # Define vertex data

    vert_id = 0

    for i in xrange(1, segments // 2):

        z = cos(angle * i)

        r2 = sin(angle * i)

        if not temp:
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

            if not temp:
                u = 1. * j / segments
                uvs_main.append((u, 1. - v))

            vert_id += 1

    positions_lower = positions_main[-segments - 1:]
    positions_upper = positions_main[:segments + 1]
    positions_upper.reverse()

    if not temp:
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
            tri_data1 = []

            if not smooth:
                plane = Plane(*[Point3(*positions_main[vi]) for vi in vert_ids])
                poly_normal = plane.get_normal()

            get_normal = lambda vi: Vec3(*positions_main[vi]) if smooth else poly_normal

            for vi in vert_ids:

                pos = positions_main[vi]
                normal = get_normal(vi)

                if temp:
                    tri_data1.append({"pos": pos, "normal": normal})
                else:
                    uv = uvs_main[vi]
                    tri_data1.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

            vert_ids = (vi1, vi3, vi4)
            tri_data2 = []

            for vi in vert_ids:

                pos = positions_main[vi]
                normal = get_normal(vi)

                if temp:
                    tri_data2.append({"pos": pos, "normal": normal})
                else:
                    uv = uvs_main[vi]
                    tri_data2.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

            if temp:
                poly_data = (tri_data1, tri_data2)  # quadrangular face
            else:
                tris = (tri_data1, tri_data2)  # quadrangular face
                poly_data = {"tris": tris, "smoothing": smoothing_ids}

            geom_data.append(poly_data)

    # Define triangular faces at top pole

    pole_pos = PosObj((0., 0., 1.))
    pole_normal = Vec3(0., 0., 1.)

    if not temp:
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

        vert_props = {"pos": pole_pos, "normal": pole_normal if smooth else poly_normal}

        if not temp:
            u = 1. * j / segments
            vert_props["uvs"] = {0: (u, v)}

        tri_data = [vert_props]

        get_normal = lambda vi: Vec3(*positions_upper[vi]) if smooth else poly_normal

        if temp:

            for vi in vert_ids:
                tri_data.append({"pos": positions_upper[vi], "normal": get_normal(vi)})

            poly_data = (tri_data,)  # triangular face

        else:

            for vi in vert_ids:
                tri_data.append({"pos": positions_upper[vi], "normal": get_normal(vi),
                                  "uvs": {0: uvs_upper[vi]}})

            tris = (tri_data,)  # triangular face
            poly_data = {"tris": tris, "smoothing": smoothing_ids}

        geom_data.append(poly_data)

    # Define triangular faces at bottom pole

    pole_pos = PosObj((0., 0., -1.))
    pole_normal = Vec3(0., 0., -1.)

    if not temp:
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

        vert_props = {"pos": pole_pos, "normal": pole_normal if smooth else poly_normal}

        if not temp:
            u = 1. - 1. * j / segments
            vert_props["uvs"] = {0: (u, v)}

        tri_data = [vert_props]

        get_normal = lambda vi: Vec3(*positions_lower[vi]) if smooth else poly_normal

        if temp:

            for vi in vert_ids:
                tri_data.append({"pos": positions_lower[vi], "normal": get_normal(vi)})

            poly_data = (tri_data,)  # triangular face

        else:

            for vi in vert_ids:
                tri_data.append({"pos": positions_lower[vi], "normal": get_normal(vi),
                                  "uvs": {0: uvs_lower[vi]}})

            tris = (tri_data,)  # triangular face
            poly_data = {"tris": tris, "smoothing": smoothing_ids}

        geom_data.append(poly_data)

    return geom_data


class TemporarySphere(TemporaryPrimitive):

    def __init__(self, segments, is_smooth, color, pos):

        TemporaryPrimitive.__init__(self, "sphere", color, pos)

        self._radius = 0.
        geom_data = _define_geom_data(segments, is_smooth, True)
        self.create_geometry(geom_data)

    def update_radius(self, radius):

        r = max(radius, .001)

        if self._radius != r:
            self._radius = r
            self.get_origin().set_scale(r)

    def get_size(self):

        return self._radius

    def is_valid(self):

        return self._radius > .001


class Sphere(Primitive):

    def __init__(self, model):

        prop_ids = ["segments", "radius", "smoothness"]

        Primitive.__init__(self, "sphere", model, prop_ids)

        self._segments = 4
        self._segments_backup = 4
        self._radius = 0.
        self._is_smooth = True
        self._smoothing = {}

    def define_geom_data(self):

        return _define_geom_data(self._segments, self._is_smooth)

    def update(self, data):

        self._smoothing = data["smoothing"]

    def create(self, segments, is_smooth):

        self._segments = segments
        self._is_smooth = is_smooth

        for step in Primitive.create(self, *_get_mesh_density(segments)):
            yield

        self.update_initial_coords()

    def set_segments(self, segments):

        if self._segments == segments:
            return False

        self._segments_backup = self._segments
        self._segments = segments

        return True

    def __update_size(self):

        r = self._radius
        self.get_origin().set_scale(r)
        self.reset_initial_coords()
        self.get_geom_data_object().bake_transform()
        self.get_geom_data_object().update_poly_centers()
        self.get_model().get_bbox().update(*self.get_origin().get_tight_bounds())

    def init_radius(self, radius):

        r = max(radius, .001)
        self._radius = r
        self.__update_size()

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
                data.update(self.get_geom_data_backup().get_data_to_store("deletion"))
                data.update(self.get_geom_data_object().get_data_to_store("creation"))
                self.remove_geom_data_backup()
            elif prop_id == "smoothness":
                data.update(self.get_geom_data_object().get_data_to_store("prop_change", "smoothing"))
            elif prop_id == "radius":
                data.update(self.get_geom_data_object().get_property_to_store("subobj_transform",
                                                                              "prop_change", "all"))

            return data

        return Primitive.get_data_to_store(self, event_type, prop_id)

    def cancel_geometry_recreation(self, info):

        Primitive.cancel_geometry_recreation(self, info)

        if info == "creation":
            self._segments = self._segments_backup
            Mgr.update_remotely("selected_obj_prop", "sphere", "segments", self._segments)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "sphere", prop_id, self.get_property(prop_id, True))

        obj_id = self.get_toplevel_object().get_id()

        if prop_id == "segments":

            if restore:
                self.restore_initial_coords(value["pos_data"])

            change = self.set_segments(value["count"] if restore else value)

            if change:

                if not restore:
                    self.recreate_geometry(*_get_mesh_density(value))

                update_app()

            return change

        elif prop_id == "radius":

            change = self.set_radius(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("upd_vert_normals", "object") + 2
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.get_model().update_group_bbox()
                update_app()

            return change

        elif prop_id == "smoothness":

            change = self.set_smooth(value)

            if change and not restore:
                Mgr.schedule_screenshot_removal()
                descr = "Updating smoothness..."
                task = lambda: self.get_geom_data_object().set_smoothing(self._smoothing.itervalues()
                                                                         if value else None)
                PendingTasks.add(task, "smooth_polys", "object", id_prefix=obj_id,
                                 gradual=True, descr=descr)

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
        elif prop_id == "radius":
            return self._radius
        elif prop_id == "smoothness":
            return self._is_smooth

    def finalize(self):

        self.__update_size()

        for step in Primitive.finalize(self, update_poly_centers=False):
            yield


MainObjects.add_class(SphereManager)
