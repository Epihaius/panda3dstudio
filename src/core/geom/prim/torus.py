from .base import *
from math import pi, sin, cos
import array


def _define_geom_data(segments, smooth, temp=False):

    geom_data = []
    pos_objs = []
    positions = []
    # keep track of row indices, one SparseArray per section;
    # compute the initial vertex positions the same for all sections, as if
    # they were all lying in the front plane, centered at the torus origin;
    # these will then be transformed with the following matrix:
    #     scale_mat (section_radius) * translate_mat (ring_radius)
    #     * rotate_mat (section angle)
    # for each section, using the corresponding SparseArray.
    section_arrays = []
    section_arrays_by_vert_id = {}
    section_rot_by_vert_id = {}

    if not temp:
        uvs = []

    segs_r = segments["ring"]
    segs_s = segments["section"]

    angle = 2. * pi / segs_s
    section_pos = [(sin(angle * i), 0., cos(angle * i)) for i in range(segs_s)]

    # Define vertex data

    vert_id = 0
    angle_h = 360. / segs_r
    up_vec = Vec3.up()
    translate_mat = Mat4.translate_mat(2., 0., 0.)

    for i in range(segs_r):

        if not temp:
            u = i / segs_r

        # two SparseArrays are needed; one for per-poly vertices (to shape the main geom)
        # and another for per-triangle vertices (to shape the auxiliary geom, used for
        # wireframe display and snapping)
        sparse_arrays = (SparseArray(), SparseArray())
        section_arrays.append(sparse_arrays)
        mat = translate_mat * Mat4.rotate_mat_normaxis(angle_h * i, up_vec)

        for j in range(segs_s + 1):

            if j < segs_s:
                pos_obj = PosObj(section_pos[j])
                pos_objs.append(pos_obj)
            else:
                pos_obj = positions[vert_id - segs_s]

            positions.append(pos_obj)

            if not temp:
                v = j / segs_s
                uvs.append((u, 1. - v))

            section_arrays_by_vert_id[vert_id] = sparse_arrays
            section_rot_by_vert_id[vert_id] = mat
            vert_id += 1

    positions.extend(positions[:segs_s + 1])
    sparse_arrays = section_arrays[0]
    section_arrays_by_vert_id.update({vi: sparse_arrays
        for vi in range(vert_id, vert_id + segs_s + 1)})
    section_rot_by_vert_id.update({vi: translate_mat
        for vi in range(vert_id, vert_id + segs_s + 1)})

    if not temp:
        for u, v in uvs[:segs_s + 1]:
            uvs.append((1., v))

    flat_normals = array.array("f", [])
    smooth_normals = array.array("f", [])
    normals = {"flat": flat_normals, "smooth": smooth_normals}

    # Define quadrangular faces

    row = 0
    row_alt = 0

    for i in range(segs_r):

        s = segs_s + 1
        k = i * s

        for j in range(segs_s):

            vi1 = k + j
            vi2 = vi1 + 1
            vi3 = vi2 + s
            vi4 = vi1 + s
            vert_data = {}
            vert_ids = (vi1, vi2, vi3, vi4)

            plane_points = [section_rot_by_vert_id[vi].xform_point(Point3(*positions[vi]))
                for vi in vert_ids[:3]]
            plane = Plane(*plane_points)
            poly_normal = plane.get_normal()

            for vi in vert_ids:

                pos = positions[vi]
                h_mat = section_rot_by_vert_id[vi]
                smooth_normal = h_mat.xform_vec(Vec3(*pos))
                normal = smooth_normal if smooth else poly_normal
                flat_normals.extend(poly_normal)
                smooth_normals.extend(smooth_normal)

                if temp:
                    vert_data[vi] = {"pos": pos, "normal": normal}
                else:
                    uv = uvs[vi]
                    vert_data[vi] = {"pos": pos, "normal": normal, "uvs": {0: uv},
                        "pos_ind": pos_objs.index(pos)}

                section_arrays_by_vert_id[vi][0].set_bit(row)
                row += 1

            poly_verts = [vert_data[vi] for vi in vert_ids]
            vert_ids = (vi1, vi2, vi3)
            tri_data1 = [vert_data[vi] for vi in vert_ids]

            for vi in vert_ids:
                section_arrays_by_vert_id[vi][1].set_bit(row_alt)
                row_alt += 1

            vert_ids = (vi1, vi3, vi4)
            tri_data2 = [vert_data[vi] for vi in vert_ids]
            tris = (tri_data1, tri_data2)  # quadrangular face

            for vi in vert_ids:
                section_arrays_by_vert_id[vi][1].set_bit(row_alt)
                row_alt += 1

            poly_data = {"verts": poly_verts, "tris": tris}
            geom_data.append(poly_data)

    return geom_data, normals, section_arrays


class TemporaryTorus(TemporaryPrimitive):

    def __init__(self, segments, is_smooth, color, pos):

        TemporaryPrimitive.__init__(self, "torus", color, pos)

        self._ring_radius = 0.
        self._section_radius = 0.
        geom_data, normals, section_arrays = _define_geom_data(segments, is_smooth, True)
        self.create_geometry(geom_data)
        origin = self.origin
        origin.set_shader_input("ring_radius", 2.)
        origin.set_shader_input("section_radius", 1.)
        torus_shaded = shaders.Shaders.torus_shaded
        torus_wire = shaders.Shaders.torus_wire

        for child in origin.get_children():

            vertex_data = child.node().modify_geom(0).modify_vertex_data()
            mat = Mat4.translate_mat(2., 0., 0.)
            vertex_data.transform_vertices(mat)
            angle = 360. / segments["ring"]
            axis_vec = Vec3.up()
            index = 0 if child.name == "shaded" else 1

            for i, rows in enumerate(section_arrays):
                mat = Mat4.rotate_mat_normaxis(angle * i, axis_vec)
                vertex_data.transform_vertices(mat, rows[index])

            if child.name == "shaded":
                normal_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("f")
                normal_view[:] = normals["smooth" if is_smooth else "flat"]
                child.set_shader(torus_shaded)
            else:
                child.set_shader(torus_wire)

    def update_size(self, ring_radius=None, section_radius=None):

        origin = self.origin

        if ring_radius is not None:

            r = max(ring_radius, .001)

            if self._ring_radius != r:
                self._ring_radius = r
                origin.set_shader_input("ring_radius", r)

        if section_radius is not None:

            r = max(section_radius, .001)

            if self._section_radius != r:
                self._section_radius = r
                origin.set_shader_input("section_radius", r)

    def get_size(self):

        return self._ring_radius, self._section_radius

    def is_valid(self):

        return min(self._ring_radius, self._section_radius) > .001


class Torus(Primitive):

    def __getstate__(self):

        state = Primitive.__getstate__(self)
        del state["_normals"]
        del state["_section_arrays"]

        return state

    def __init__(self, model, segments, is_smooth, picking_col_id, geom_data,
                 normals, arrays):

        self._segments = segments
        self._is_smooth = is_smooth
        self._ring_radius = 0.
        self._section_radius = 0.
        self._normals = normals
        self._section_arrays = arrays

        prop_ids = ["segments", "radius_ring", "radius_section", "smoothness"]

        Primitive.__init__(self, "torus", model, prop_ids, picking_col_id, geom_data)

    def recreate(self):

        geom_data, normals, arrays = _define_geom_data(self._segments, self._is_smooth)
        self._normals = normals
        self._section_arrays = arrays
        Primitive.recreate(self, geom_data)

    def set_segments(self, segments):

        if self._segments == segments:
            return False

        self._segments = segments

        return True

    def __update_size(self):

        ring_radius = self._ring_radius
        section_radius = self._section_radius
        tmp_mat = Mat4.scale_mat(section_radius) * Mat4.translate_mat(ring_radius, 0., 0.)
        angle = 360. / self._segments["ring"]
        axis_vec = Vec3.up()
        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        tan_space_array = vertex_data.modify_array(3)

        for i, geom in enumerate((self.geom, self.aux_geom)):

            vertex_data = geom.node().modify_geom(0).modify_vertex_data()
            pos_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
            pos_view[:] = self.initial_coords[i]
            vertex_data.transform_vertices(tmp_mat)

            for j, rows in enumerate(self._section_arrays):
                mat = Mat4.rotate_mat_normaxis(angle * j, axis_vec)
                vertex_data.transform_vertices(mat, rows[i])

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(3, tan_space_array)
        self.__update_normals()
        self.update_poly_centers()

        self.model.bbox.update(self.geom.get_tight_bounds())

    def init_size(self, ring_radius, section_radius):

        self._ring_radius = max(ring_radius, .001)
        self._section_radius = max(section_radius, .001)
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
                        "normals": self._normals, "section_arrays": self._section_arrays,
                        "geom_data": self.geom_data, "geom": self.geom_for_pickling,
                        "aux_geom": self.aux_geom_for_pickling}
        elif prop_id == "radius_ring":
            return self._ring_radius
        elif prop_id == "radius_section":
            return self._section_radius
        elif prop_id == "smoothness":
            return self._is_smooth
        else:
            return Primitive.get_property(self, prop_id, for_remote_update)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "torus", prop_id,
                                self.get_property(prop_id, True))

        obj_id = self.toplevel_obj.id

        if prop_id == "segments":

            if restore:
                segments = value["count"]
                self.initial_coords = value["pos_data"]
                self._normals = value["normals"]
                self._section_arrays = value["section_arrays"]
                self.geom_data = value["geom_data"]
                self.geom = value["geom"]
                self.aux_geom = value["aux_geom"]
                self.model.bbox.update(self.geom.get_tight_bounds())
                self.setup_geoms()
            else:
                segments = self._segments.copy()
                segments.update(value)

            task = self.__update_size
            sort = PendingTasks.get_sort("set_normals", "object") - 1
            PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
            self.model.update_group_bbox()

            change = self.set_segments(segments)

            if change:

                if not restore:
                    self.recreate()

                update_app()

            return change

        elif prop_id == "radius_ring":

            change = self.set_ring_radius(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("set_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.model.update_group_bbox()
                update_app()

            return change

        elif prop_id == "radius_section":

            change = self.set_section_radius(value)

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


class TorusManager(PrimitiveManager):

    def __init__(self):

        PrimitiveManager.__init__(self, "torus")

        self._dragged_point = Point3()
        self._section_radius_vec = V3D()
        self._draw_plane = None

        self.set_property_default("radius_ring", 2.)
        self.set_property_default("radius_section", 1.)
        self.set_property_default("smoothness", True)
        self.set_property_default("temp_segments", {"ring": 12, "section": 6})  # minimum = 3
        self.set_property_default("segments", {"ring": 24, "section": 12})  # minimum = 3

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1,
                          self.__finish_creation_phase1)
        creation_phases.append(creation_phase)
        creation_phase = (self.__start_creation_phase2, self.__creation_phase2,
                          self.__finish_creation_phase2)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "torus"
        status_text["phase1"] = "draw out the ring"
        status_text["phase2"] = "draw out the cross section"

        return PrimitiveManager.setup(self, creation_phases, status_text)

    def define_geom_data(self):

        prop_defaults = self.get_property_defaults()
        segments = prop_defaults["segments"]
        is_smooth = prop_defaults["smoothness"]

        return _define_geom_data(segments, is_smooth)

    def create_temp_primitive(self, color, pos):

        segs = self.get_property_defaults()["segments"]
        tmp_segs = self.get_property_defaults()["temp_segments"]
        segments = {k: min(segs[k], tmp_segs[k]) for k in ("ring", "section")}
        is_smooth = self.get_property_defaults()["smoothness"]
        tmp_prim = TemporaryTorus(segments, is_smooth, color, pos)

        return tmp_prim

    def create_primitive(self, model, picking_col_id, geom_data):

        prop_defaults = self.get_property_defaults()
        segments = prop_defaults["segments"]
        is_smooth = prop_defaults["smoothness"]
        prim = Torus(model, segments, is_smooth, picking_col_id, *geom_data)

        return prim

    def init_primitive_size(self, prim, size=None):

        prop_defaults = self.get_property_defaults()

        if size is None:
            prim.init_size(prop_defaults["radius_ring"], prop_defaults["radius_section"])
        else:
            prim.init_size(*size)

    def __start_creation_phase1(self):
        """ Start drawing out torus ring """

        cam_pos = GD.cam().get_pos(GD.world)
        lens_type = GD.cam.lens_type

        # initialize the section radius, based on ...
        if lens_type == "persp":
            # ... the distance of the torus center to the camera
            section_radius = (self.get_origin_pos() - cam_pos).length() * .01
        else:
            # ... camera zoom
            section_radius = GD.cam.zoom * 5.

        origin = self.get_temp_primitive().origin
        origin.set_shader_input("section_radius", section_radius)

    def __creation_phase1(self):
        """ Draw out torus ring """

        point = None
        grid = Mgr.get("grid")
        grid_origin = grid.origin
        origin_pos = grid_origin.get_relative_point(GD.world, self.get_origin_pos())
        snap_settings = GD["snap"]
        snap_on = snap_settings["on"]["creation"] and snap_settings["on"]["creation_phase_1"]
        snap_tgt_type = snap_settings["tgt_type"]["creation_phase_1"]

        if snap_on and snap_tgt_type != "increment":
            point = Mgr.get("snap_target_point")

        if point is None:

            if snap_on and snap_tgt_type != "increment":
                Mgr.do("set_projected_snap_marker_pos", None)

            if not GD.mouse_watcher.has_mouse():
                return

            screen_pos = GD.mouse_watcher.get_mouse()
            point = grid.get_point_at_screen_pos(screen_pos, origin_pos)

        else:

            point = grid.get_projected_point(point, origin_pos)
            proj_point = GD.world.get_relative_point(grid_origin, point)
            Mgr.do("set_projected_snap_marker_pos", proj_point)

        if not point:
            return

        radius_vec = point - origin_pos
        ring_radius = radius_vec.length()

        if snap_on and snap_tgt_type == "increment":
            offset_incr = snap_settings["increment"]["creation_phase_1"]
            ring_radius = round(ring_radius / offset_incr) * offset_incr
            point = origin_pos + radius_vec.normalized() * ring_radius

        self._dragged_point = GD.world.get_relative_point(grid_origin, point)
        self.get_temp_primitive().update_size(ring_radius)

    def __finish_creation_phase1(self):
        """ End creation phase 1 by setting default torus ring radius """

        prop_defaults = self.get_property_defaults()
        tmp_prim = self.get_temp_primitive()
        tmp_prim.update_size(prop_defaults["radius_ring"])

    def __start_creation_phase2(self):
        """ Start drawing out torus cross section """

        cam = GD.cam()
        ring_radius_vec = V3D(self._dragged_point - self.get_origin_pos())
        cam_forward_vec = V3D(GD.world.get_relative_vector(cam, Vec3.forward()))
        plane = Plane(cam_forward_vec, Point3())
        self._section_radius_vec = plane.project(ring_radius_vec).normalized()
        self._draw_plane = Plane(cam_forward_vec, self._dragged_point)

    def __creation_phase2(self):
        """ Draw out torus cross section """

        tmp_prim = self.get_temp_primitive()
        point = None
        snap_settings = GD["snap"]
        snap_on = snap_settings["on"]["creation"] and snap_settings["on"]["creation_phase_2"]
        snap_tgt_type = snap_settings["tgt_type"]["creation_phase_2"]

        if snap_on and snap_tgt_type != "increment":
            point = Mgr.get("snap_target_point")

        if point is None:

            if not GD.mouse_watcher.has_mouse():
                return

            screen_pos = GD.mouse_watcher.get_mouse()
            cam = GD.cam()

            near_point = Point3()
            far_point = Point3()
            GD.cam.lens.extrude(screen_pos, near_point, far_point)
            rel_pt = lambda point: GD.world.get_relative_point(cam, point)
            near_point = rel_pt(near_point)
            far_point = rel_pt(far_point)
            point = Point3()

            if not self._draw_plane.intersects_line(point, near_point, far_point):
                return

            radius_vec = (point - self._dragged_point).project(self._section_radius_vec)

        else:

            grid = Mgr.get("grid")
            origin_pos = grid.origin.get_relative_point(GD.world, self.get_origin_pos())
            proj_point = grid.get_projected_point(point, origin_pos)
            vec = proj_point - origin_pos
            ring_point = origin_pos + vec.normalized() * tmp_prim.get_size()[0]
            radius_vec = point - ring_point

        section_radius = radius_vec.length()

        if snap_on and snap_tgt_type == "increment":
            offset_incr = snap_settings["increment"]["creation_phase_2"]
            section_radius = round(section_radius / offset_incr) * offset_incr

        tmp_prim.update_size(section_radius=section_radius)

    def __finish_creation_phase2(self):
        """ End creation phase 2 by setting default torus cross section radius """

        prop_defaults = self.get_property_defaults()
        tmp_prim = self.get_temp_primitive()
        tmp_prim.update_size(section_radius=prop_defaults["radius_section"])


MainObjects.add_class(TorusManager)
