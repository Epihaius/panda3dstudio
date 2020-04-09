from .base import *
from math import pi, sin, cos
import array


def _define_geom_data(segments, smooth, temp=False):

    geom_data = []
    pos_objs = []
    positions_main = []

    if not temp:
        uvs_main = []

    angle = 2 * pi / segments

    # Define vertex data

    vert_id = 0

    for i in range(1, segments // 2):

        z = cos(angle * i)

        r2 = sin(angle * i)

        if not temp:
            v = 2. * i / segments

        for j in range(segments + 1):

            angle_h = angle * j
            x = r2 * cos(angle_h)
            y = r2 * sin(angle_h)

            if j < segments:
                pos = (x, y, z)
                pos_obj = PosObj(pos)
                pos_objs.append(pos_obj)
            else:
                pos_obj = positions_main[vert_id - segments]

            positions_main.append(pos_obj)

            if not temp:
                u = j / segments
                uvs_main.append((u, 1. - v))

            vert_id += 1

    positions_lower = positions_main[-segments - 1:]
    positions_upper = positions_main[:segments + 1]
    positions_upper.reverse()

    if not temp:
        uvs_lower = uvs_main[-segments - 1:]
        uvs_upper = uvs_main[:segments + 1]
        uvs_upper.reverse()
        flat_normals = array.array("f", [])
        smooth_normals = array.array("f", [])
        normals = {"flat": flat_normals, "smooth": smooth_normals}

    # Define quadrangular faces

    for i in range(1, segments // 2 - 1):

        s = segments + 1
        k = (i - 1) * s

        for j in range(segments):

            vi1 = k + j
            vi2 = vi1 + s
            vi3 = vi2 + 1
            vi4 = vi1 + 1
            vert_data = {}
            vert_ids = (vi1, vi2, vi3, vi4)

            plane = Plane(*[Point3(*positions_main[vi]) for vi in (vi1, vi2, vi3)])
            poly_normal = plane.get_normal()

            for vi in vert_ids:

                pos = positions_main[vi]
                smooth_normal = Vec3(*positions_main[vi])
                normal = smooth_normal if smooth else poly_normal

                if temp:
                    vert_data[vi] = {"pos": pos, "normal": normal}
                else:
                    flat_normals.extend(poly_normal)
                    smooth_normals.extend(smooth_normal)
                    uv = uvs_main[vi]
                    vert_data[vi] = {"pos": pos, "normal": normal, "uvs": {0: uv},
                        "pos_ind": pos_objs.index(pos)}

            poly_verts = [vert_data[vi] for vi in vert_ids]
            vert_ids = (vi1, vi2, vi3)
            tri_data1 = [vert_data[vi] for vi in vert_ids]
            vert_ids = (vi1, vi3, vi4)
            tri_data2 = [vert_data[vi] for vi in vert_ids]
            tris = (tri_data1, tri_data2)  # quadrangular face
            poly_data = {"verts": poly_verts, "tris": tris}
            geom_data.append(poly_data)

    # Define triangular faces at top pole

    pole_pos = PosObj((0., 0., 1.))
    pos_objs.append(pole_pos)
    pole_normal = Vec3(0., 0., 1.)

    if not temp:
        v = 1.

    for j in range(segments):

        vi2 = segments - j
        vi3 = vi2 - 1
        vert_ids = (vi2, vi3)

        cap_positions = [Point3(*positions_upper[vi]) for vi in vert_ids]
        cap_positions.append(Point3(*pole_pos))
        plane = Plane(*cap_positions)
        poly_normal = plane.get_normal()
        normal = pole_normal if smooth else poly_normal

        if temp:
            vert_data = {"pos": pole_pos, "normal": normal}
        else:
            flat_normals.extend(poly_normal)
            smooth_normals.extend(pole_normal)
            u = j / segments
            vert_data = {"pos": pole_pos, "normal": normal, "uvs": {0: (u, v)},
                "pos_ind": pos_objs.index(pole_pos)}

        tri_data = [vert_data]
        tris = (tri_data,)  # triangular face

        if temp:
            for vi in vert_ids:
                normal = Vec3(*positions_upper[vi]) if smooth else poly_normal
                tri_data.append({"pos": positions_upper[vi], "normal": normal})
        else:
            for vi in vert_ids:
                pos = positions_upper[vi]
                smooth_normal = Vec3(*positions_upper[vi])
                flat_normals.extend(poly_normal)
                smooth_normals.extend(smooth_normal)
                normal = smooth_normal if smooth else poly_normal
                uv = uvs_upper[vi]
                tri_data.append({"pos": pos, "normal": normal, "uvs": {0: uv},
                                 "pos_ind": pos_objs.index(pos)})

        poly_data = {"verts": tri_data, "tris": tris}
        geom_data.append(poly_data)

    # Define triangular faces at bottom pole

    pole_pos = PosObj((0., 0., -1.))
    pos_objs.append(pole_pos)
    pole_normal = Vec3(0., 0., -1.)

    if not temp:
        v = 0.

    for j in range(segments):

        vi2 = segments - j
        vi3 = vi2 - 1
        vert_ids = (vi2, vi3)

        cap_positions = [Point3(*positions_lower[vi])  for vi in vert_ids]
        cap_positions.append(Point3(*pole_pos))
        plane = Plane(*cap_positions)
        poly_normal = plane.get_normal()
        normal = pole_normal if smooth else poly_normal

        if temp:
            vert_data = {"pos": pole_pos, "normal": normal}
        else:
            flat_normals.extend(poly_normal)
            smooth_normals.extend(pole_normal)
            u = 1. - j / segments
            vert_data = {"pos": pole_pos, "normal": normal, "uvs": {0: (u, v)},
                "pos_ind": pos_objs.index(pole_pos)}

        tri_data = [vert_data]
        tris = (tri_data,)  # triangular face

        if temp:
            for vi in vert_ids:
                normal = Vec3(*positions_lower[vi]) if smooth else poly_normal
                tri_data.append({"pos": positions_lower[vi], "normal": normal})
        else:
            for vi in vert_ids:
                pos = positions_lower[vi]
                smooth_normal = Vec3(*positions_lower[vi])
                flat_normals.extend(poly_normal)
                smooth_normals.extend(smooth_normal)
                normal = smooth_normal if smooth else poly_normal
                uv = uvs_lower[vi]
                tri_data.append({"pos": pos, "normal": normal, "uvs": {0: uv},
                                 "pos_ind": pos_objs.index(pos)})

        poly_data = {"verts": tri_data, "tris": tris}
        geom_data.append(poly_data)

    return geom_data if temp else (geom_data, normals)


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
            self.origin.set_scale(r)

    def get_size(self):

        return self._radius

    def is_valid(self):

        return self._radius > .001


class Sphere(Primitive):

    def __getstate__(self):

        state = Primitive.__getstate__(self)
        del state["_normals"]

        return state

    def __init__(self, model, segments, is_smooth, picking_col_id, geom_data, normals):

        self._segments = segments
        self._radius = 0.
        self._is_smooth = is_smooth
        self._normals = normals

        prop_ids = ["segments", "radius", "smoothness"]

        Primitive.__init__(self, "sphere", model, prop_ids, picking_col_id, geom_data)

    def setup_geoms(self, restore=False):

        Primitive.setup_geoms(self)

        if restore:
            task = self.__update_normals
            PendingTasks.add(task, "set_normals", "object", id_prefix=self.toplevel_obj.id)

    def recreate(self):

        geom_data, normals = _define_geom_data(self._segments, self._is_smooth)
        self._normals = normals
        Primitive.recreate(self, geom_data)

    def set_segments(self, segments):

        if self._segments == segments:
            return False

        self._segments = segments

        return True

    def __update_size(self):

        mat = Mat4.scale_mat(self._radius)

        for i, geom in enumerate((self.geom, self.aux_geom)):
            vertex_data = geom.node().modify_geom(0).modify_vertex_data()
            pos_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
            pos_view[:] = self.initial_coords[i]
            vertex_data.transform_vertices(mat)

        self.update_poly_centers()

        self.model.bbox.update(self.geom.get_tight_bounds())

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

    def __update_normals(self):

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        normal_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("f")
        normal_view[:] = self._normals["smooth" if self._is_smooth else "flat"]

        if self.has_inverted_geometry():
            geom = self.geom.node().modify_geom(0)
            vertex_data = geom.get_vertex_data().reverse_normals()
            geom.set_vertex_data(vertex_data)

    def unlock_geometry(self, unlocked_geom):

        Primitive.unlock_geometry(self, unlocked_geom, update_normal_data=True)

    def get_data_to_store(self, event_type, prop_id=""):

        if event_type == "prop_change" and prop_id in self.get_type_property_ids():

            data = {}
            data[prop_id] = {"main": self.get_property(prop_id)}

            return data

        return Primitive.get_data_to_store(self, event_type, prop_id)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "segments":
            if for_remote_update:
                return self._segments
            else:
                return {"count": self._segments, "pos_data": self.initial_coords,
                        "normals": self._normals, "geom_data": self.geom_data,
                        "geom": self.geom_for_pickling, "aux_geom": self.aux_geom_for_pickling}
        elif prop_id == "radius":
            return self._radius
        elif prop_id == "smoothness":
            return self._is_smooth
        else:
            return Primitive.get_property(self, prop_id, for_remote_update)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "sphere", prop_id,
                                self.get_property(prop_id, True))

        obj_id = self.toplevel_obj.id

        if prop_id == "segments":

            if restore:
                self.initial_coords = value["pos_data"]
                self._normals = value["normals"]
                self.geom_data = value["geom_data"]
                self.geom = value["geom"]
                self.aux_geom = value["aux_geom"]
                self.model.bbox.update(self.geom.get_tight_bounds())
                self.setup_geoms(restore)

            task = self.__update_size
            sort = PendingTasks.get_sort("set_normals", "object") - 1
            PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
            self.model.update_group_bbox()

            change = self.set_segments(value["count"] if restore else value)

            if change:

                if not restore:
                    self.recreate()

                update_app()

            return change

        elif prop_id == "radius":

            change = self.set_radius(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("set_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.model.update_group_bbox()
                update_app()

            return change

        elif prop_id == "smoothness":

            change = self.set_smooth(value)

            if restore:
                task = self.__update_normals
                PendingTasks.add(task, "set_normals", "object", id_prefix=obj_id)
            elif change:
                self.__update_normals()

            if change:
                update_app()

            return change

        else:

            return Primitive.set_property(self, prop_id, value, restore)


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
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1,
                          self.__finish_creation_phase1)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "sphere"
        status_text["phase1"] = "draw out the sphere"

        return PrimitiveManager.setup(self, creation_phases, status_text)

    def define_geom_data(self):

        prop_defaults = self.get_property_defaults()
        segments = prop_defaults["segments"]
        is_smooth = prop_defaults["smoothness"]

        return _define_geom_data(segments, is_smooth)

    def create_temp_primitive(self, color, pos):

        segs = self.get_property_defaults()["segments"]
        tmp_segs = self.get_property_defaults()["temp_segments"]
        segments = segs if segs < tmp_segs else tmp_segs
        is_smooth = self.get_property_defaults()["smoothness"]
        tmp_prim = TemporarySphere(segments, is_smooth, color, pos)

        return tmp_prim

    def create_primitive(self, model, picking_col_id, geom_data):

        prop_defaults = self.get_property_defaults()
        segments = prop_defaults["segments"]
        is_smooth = prop_defaults["smoothness"]
        prim = Sphere(model, segments, is_smooth, picking_col_id, *geom_data)

        return prim

    def init_primitive_size(self, prim, size=None):

        prop_defaults = self.get_property_defaults()
        radius = prop_defaults["radius"] if size is None else size
        prim.init_radius(radius)

    def __start_creation_phase1(self):
        """ Start drawing out sphere """

        # Create the plane parallel to the camera and going through the sphere
        # center, used to determine the radius drawn out by the user.

        normal = GD.world.get_relative_vector(GD.cam(), Vec3.forward())
        self._draw_plane = Plane(normal, self.get_origin_pos())

    def __creation_phase1(self):
        """ Draw out sphere """

        end_point = None
        grid_origin = Mgr.get("grid").origin
        snap_settings = GD["snap"]
        snap_on = snap_settings["on"]["creation"] and snap_settings["on"]["creation_phase_1"]
        snap_tgt_type = snap_settings["tgt_type"]["creation_phase_1"]

        if snap_on and snap_tgt_type != "increment":
            end_point = Mgr.get("snap_target_point")

        if end_point is None:

            if not GD.mouse_watcher.has_mouse():
                return

            screen_pos = GD.mouse_watcher.get_mouse()
            near_point = Point3()
            far_point = Point3()
            GD.cam.lens.extrude(screen_pos, near_point, far_point)
            rel_pt = lambda point: GD.world.get_relative_point(GD.cam(), point)
            near_point = rel_pt(near_point)
            far_point = rel_pt(far_point)
            end_point = Point3()
            self._draw_plane.intersects_line(end_point, near_point, far_point)

        else:

            end_point = GD.world.get_relative_point(grid_origin, end_point)

        radius = (end_point - self.get_origin_pos()).length()

        if snap_on and snap_tgt_type == "increment":
            offset_incr = snap_settings["increment"]["creation_phase_1"]
            radius = round(radius / offset_incr) * offset_incr

        self.get_temp_primitive().update_radius(radius)

    def __finish_creation_phase1(self):
        """ End creation phase 1 by setting default sphere radius """

        prop_defaults = self.get_property_defaults()
        tmp_prim = self.get_temp_primitive()
        tmp_prim.update_radius(prop_defaults["radius"])

    def create_custom_primitive(self, name, radius, segments, pos, inverted=False,
                                rel_to_grid=False, smooth=True):

        model_id = self.generate_object_id()
        model = Mgr.do("create_model", model_id, name, pos)

        if not rel_to_grid:
            pivot = model.pivot
            pivot.clear_transform()
            pivot.set_pos(GD.world, pos)

        next_color = self.get_next_object_color()
        model.set_color(next_color, update_app=False)
        picking_col_id = self.get_next_picking_color_id()
        geom_data, normals = _define_geom_data(segments, smooth)
        prim = Sphere(model, segments, smooth, picking_col_id, geom_data, normals)
        prim.init_radius(radius)
        self.set_next_object_color()

        if inverted:
            prim.set_property("inverted_geom", True)

        return model


MainObjects.add_class(SphereManager)
