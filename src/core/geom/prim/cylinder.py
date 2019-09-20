from .base import *
from math import pi, sin, cos


def _get_mesh_density(segments):

    poly_count = segments["circular"] * segments["height"]
    poly_count += 2 * segments["circular"] * segments["caps"]

    return poly_count


def _define_geom_data(segments, smooth, temp=False):

    geom_data = []
    positions_main = []

    if not temp:
        uvs_main = []
        smoothing_ids = [(0, smooth)]

    segs_c = segments["circular"]
    segs_h = segments["height"]
    segs_cap = segments["caps"]

    angle = 2 * pi / segs_c

    # Define vertex data

    vert_id = 0

    for i in range(segs_h + 1):

        z = 1. - i / segs_h

        for j in range(segs_c + 1):

            angle_h = angle * j
            x = cos(angle_h)
            y = sin(angle_h)

            if j < segs_c:
                pos = (x, y, z)
                pos_obj = PosObj(pos)
            else:
                pos_obj = positions_main[vert_id - segs_c]

            positions_main.append(pos_obj)

            if not temp:
                u = j / segs_c
                uvs_main.append((u, z))

            vert_id += 1

    if segs_cap:

        positions_cap_lower = positions_main[-segs_c - 1:]
        positions_cap_upper = positions_main[:segs_c + 1]
        positions_cap_upper.reverse()

        if not temp:
            uvs_cap_lower = []
            uvs_cap_upper = []

        def add_cap_data(cap):

            # Add data related to vertices along the cap segments

            if cap == "lower":

                positions = positions_cap_lower

                if not temp:
                    uvs = uvs_cap_lower

                z = 0.
                y_factor = 1.

            else:

                positions = positions_cap_upper

                if not temp:
                    uvs = uvs_cap_upper

                z = 1.
                y_factor = -1.

            vert_id = segs_c + 1

            if not temp:
                for j in range(segs_c + 1):
                    angle_h = angle * j
                    u = .5 + cos(angle_h) * .5
                    v = .5 - sin(angle_h) * .5
                    uvs.append((u, v))

            for i in range(1, segs_cap):

                r = 1. - i / segs_cap

                for j in range(segs_c + 1):

                    angle_h = angle * j
                    x = r * cos(angle_h)
                    y = r * sin(angle_h) * y_factor

                    if j < segs_c:
                        pos = (x, y, z)
                        pos_obj = PosObj(pos)
                    else:
                        pos_obj = positions[vert_id - segs_c]

                    positions.append(pos_obj)

                    if not temp:
                        uvs.append((.5 + x * .5, .5 - y * y_factor * .5))

                    vert_id += 1

            # Add data related to center vertex of cap

            pos = (0., 0., z)
            pos_obj = PosObj(pos)
            positions.append(pos_obj)

            if not temp:
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

    for i in range(segs_h):

        s = segs_c + 1
        k = i * s

        for j in range(segs_c):

            vi1 = k + j
            vi2 = vi1 + s
            vi3 = vi2 + 1
            vi4 = vi1 + 1
            vert_ids = (vi1, vi2, vi3)
            tri_data1 = []

            if not smooth:
                plane = Plane(*[Point3(*positions_main[vi]) for vi in vert_ids])
                poly_normal = plane.get_normal()

            get_normal = lambda i: convert_pos_to_normal(i) if smooth else poly_normal

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

    if segs_cap:

        def define_cap_faces(cap):

            if cap == "lower":

                positions = positions_cap_lower
                sign = 1.

                if not temp:
                    uvs = uvs_cap_lower
                    smoothing_grp = 1

            else:

                positions = positions_cap_upper
                sign = -1.

                if not temp:
                    uvs = uvs_cap_upper
                    smoothing_grp = 2

            # Define quadrangular faces of cap

            for i in range(segs_cap - 1):

                s = segs_c + 1
                k = i * s

                for j in range(segs_c):

                    vi1 = k + j
                    vi2 = vi1 + s
                    vi3 = vi2 + 1
                    vi4 = vi1 + 1
                    vert_ids = (vi1, vi2, vi3)
                    tri_data1 = []

                    for vi in vert_ids:

                        pos = positions[vi]
                        normal = Vec3(0., 0., -1. * sign)

                        if temp:
                            tri_data1.append({"pos": pos, "normal": normal})
                        else:
                            uv = uvs[vi]
                            tri_data1.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

                    vert_ids = (vi1, vi3, vi4)
                    tri_data2 = []

                    for vi in vert_ids:

                        pos = positions[vi]
                        normal = Vec3(0., 0., -1. * sign)

                        if temp:
                            tri_data2.append({"pos": pos, "normal": normal})
                        else:
                            uv = uvs[vi]
                            tri_data2.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

                    if temp:
                        poly_data = (tri_data1, tri_data2)  # quadrangular face
                    else:
                        tris = (tri_data1, tri_data2)  # quadrangular face
                        poly_data = {"tris": tris, "smoothing": [(smoothing_grp, smooth)]}

                    geom_data.append(poly_data)

            # Define triangular faces at center of cap

            s = segs_c + 1
            vi1 = segs_cap * s

            for j in range(segs_c):

                vi2 = vi1 - 1 - j
                vi3 = vi2 - 1
                vert_ids = (vi1, vi2, vi3)
                tri_data = []

                for vi in vert_ids:

                    pos = positions[vi]
                    normal = Vec3(0., 0., -1. * sign)

                    if temp:
                        tri_data.append({"pos": pos, "normal": normal})
                    else:
                        uv = uvs[vi]
                        tri_data.append({"pos": pos, "normal": normal, "uvs": {0: uv}})

                if temp:
                    poly_data = (tri_data,)  # triangular face
                else:
                    tris = (tri_data,)  # triangular face
                    poly_data = {"tris": tris, "smoothing": [(smoothing_grp, smooth)]}

                geom_data.append(poly_data)

        define_cap_faces("lower")
        define_cap_faces("upper")

    return geom_data


class TemporaryCylinder(TemporaryPrimitive):

    def __init__(self, segments, is_smooth, color, pos):

        TemporaryPrimitive.__init__(self, "cylinder", color, pos)

        self._radius = 0.
        self._height = 0.
        geom_data = _define_geom_data(segments, is_smooth, True)
        self.create_geometry(geom_data)
        self.origin.set_sz(.001)

    def update_size(self, radius=None, height=None):

        origin = self.origin

        if radius is not None:

            r = max(radius, .001)

            if self._radius != r:
                self._radius = r
                origin.set_sx(r)
                origin.set_sy(r)

        if height is not None:

            sz = max(abs(height), .001)
            h = -sz if height < 0. else sz

            if self._height != h:
                self._height = h
                origin.set_sz(sz)
                origin.set_z(h if h < 0. else 0.)

    def get_size(self):

        return self._radius, self._height

    def is_valid(self):

        return min(self._radius, abs(self._height)) > .001


class Cylinder(Primitive):

    def __init__(self, model):

        prop_ids = ["segments", "radius", "height", "smoothness"]

        Primitive.__init__(self, "cylinder", model, prop_ids)

        self._segments = {"circular": 3, "height": 1, "caps": 0}
        self._segments_backup = {"circular": 3, "height": 1, "caps": 0}
        self._radius = 0.
        self._height = 0.
        self._is_smooth = True
        self._smoothing = {}

    def define_geom_data(self):

        return _define_geom_data(self._segments, self._is_smooth)

    def update(self, data):

        self._smoothing = data["smoothing"]

    def create(self, segments, is_smooth):

        self._segments = segments
        self._is_smooth = is_smooth

        for step in Primitive.create(self, _get_mesh_density(segments)):
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
        h = self._height
        origin = self.origin
        origin.set_scale(r, r, abs(h))
        origin.set_z(h if h < 0. else 0.)
        self.reset_initial_coords()
        self.geom_data_obj.bake_transform()

    def init_size(self, radius, height):

        origin = self.origin
        self._radius = max(radius, .001)
        self._height = max(abs(height), .001) * (-1. if height < 0. else 1.)

        self.__update_size()

    def set_radius(self, radius):

        if self._radius == radius:
            return False

        self._radius = radius

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
                data.update(self.get_geom_data_backup().get_data_to_store("deletion"))
                data.update(self.geom_data_obj.get_data_to_store("creation"))
                self.remove_geom_data_backup()
            elif prop_id == "smoothness":
                data.update(self.geom_data_obj.get_data_to_store())
            elif prop_id in ("radius", "height"):
                data.update(self.geom_data_obj.get_property_to_store("subobj_transform",
                                                                              "prop_change", "all"))

            return data

        return Primitive.get_data_to_store(self, event_type, prop_id)

    def cancel_geometry_recreation(self, info):

        Primitive.cancel_geometry_recreation(self, info)

        if info == "creation":
            self._segments = self._segments_backup
            Mgr.update_remotely("selected_obj_prop", "cylinder", "segments", self._segments)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "cylinder", prop_id,
                                self.get_property(prop_id, True))

        obj_id = self.toplevel_obj.id

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
                    self.recreate_geometry(_get_mesh_density(segments))

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

        elif prop_id == "height":

            change = self.set_height(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("set_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.model.update_group_bbox()
                update_app()

            return change

        elif prop_id == "smoothness":

            change = self.set_smooth(value)

            if change and not restore:
                task = lambda: self.geom_data_obj.set_smoothing(iter(self._smoothing.values())
                                                                         if value else None)
                PendingTasks.add(task, "set_poly_smoothing", "object", id_prefix=obj_id)

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
        elif prop_id == "height":
            return self._height
        elif prop_id == "smoothness":
            return self._is_smooth
        else:
            return Primitive.get_property(self, prop_id, for_remote_update)

    def finalize(self):

        self.__update_size()

        Primitive.finalize(self)


class CylinderManager(PrimitiveManager):

    def __init__(self):

        PrimitiveManager.__init__(self, "cylinder", custom_creation=True)

        self._height_axis = V3D(0., 0., 1.)
        self._draw_plane = None
        self._draw_plane_normal = V3D()
        self._dragged_point = Point3()

        self.set_property_default("radius", 1.)
        self.set_property_default("height", 1.)
        self.set_property_default("smoothness", True)
        self.set_property_default("temp_segments", {"circular": 8, "height": 1, "caps": 1})
        self.set_property_default("segments", {"circular": 12, "height": 4, "caps": 1})
        # minimum circular segments = 3
        # minimum height segments = 1
        # minimum cap segments = 0: no caps

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1,
                          self.__finish_creation_phase1)
        creation_phases.append(creation_phase)
        creation_phase = (self.__start_creation_phase2, self.__creation_phase2,
                          self.__finish_creation_phase2)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "cylinder"
        status_text["phase1"] = "draw out the base"
        status_text["phase2"] = "draw out the height"

        return PrimitiveManager.setup(self, creation_phases, status_text)

    def create_temp_primitive(self, color, pos):

        segs = self.get_property_defaults()["segments"]
        tmp_segs = self.get_property_defaults()["temp_segments"]
        segments = {k: min(segs[k], tmp_segs[k]) for k in ("circular", "height", "caps")}
        is_smooth = self.get_property_defaults()["smoothness"]
        tmp_prim = TemporaryCylinder(segments, is_smooth, color, pos)

        return tmp_prim

    def create_primitive(self, model):

        prim = Cylinder(model)
        prop_defaults = self.get_property_defaults()
        segments = prop_defaults["segments"]
        poly_count = _get_mesh_density(segments)
        progress_steps = (poly_count // 20) * 4
        gradual = progress_steps > 80

        for step in prim.create(segments, prop_defaults["smoothness"]):
            if gradual:
                yield

        yield prim, gradual

    def init_primitive_size(self, prim, size=None):

        if size is None:
            prop_defaults = self.get_property_defaults()
            prim.init_size(prop_defaults["radius"], prop_defaults["height"])
        else:
            prim.init_size(*size)

    def __start_creation_phase1(self):
        """ Start drawing out cylinder base """

        tmp_prim = self.get_temp_primitive()
        origin = tmp_prim.origin
        self._height_axis = GD.world.get_relative_vector(origin, V3D(0., 0., 1.))

    def __creation_phase1(self):
        """ Draw out cylinder base """

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
        radius = radius_vec.length()

        if snap_on and snap_tgt_type == "increment":
            offset_incr = snap_settings["increment"]["creation_phase_1"]
            radius = round(radius / offset_incr) * offset_incr
            point = origin_pos + radius_vec.normalized() * radius

        self._dragged_point = GD.world.get_relative_point(grid_origin, point)
        self.get_temp_primitive().update_size(radius)

    def __finish_creation_phase1(self):
        """ End creation phase 1 by setting default cylinder radius """

        prop_defaults = self.get_property_defaults()
        tmp_prim = self.get_temp_primitive()
        tmp_prim.update_size(prop_defaults["radius"])

    def __start_creation_phase2(self):
        """ Start drawing out cylinder height """

        cam = GD.cam()
        cam_forward_vec = V3D(GD.world.get_relative_vector(cam, Vec3.forward()))
        normal = V3D(cam_forward_vec - cam_forward_vec.project(self._height_axis))

        # If the plane normal is the null vector, the axis must be parallel to
        # the forward camera direction. In this case, a new normal can be chosen
        # arbitrarily, e.g. a horizontal vector perpendicular to the axis.

        if normal.length_squared() < .0001:

            x, y, z = self._height_axis

            # if the height axis is nearly vertical, any horizontal vector will
            # qualify as plane normal, e.g. a vector pointing in the the positive
            # X-direction; otherwise, the plane normal can be computed as
            # perpendicular to the axis
            normal = V3D(1., 0., 0.) if max(abs(x), abs(y)) < .0001 else V3D(y, -x, 0.)

        self._draw_plane = Plane(normal, self._dragged_point)

        if GD.cam.lens_type == "persp":

            cam_pos = cam.get_pos(GD.world)

            if normal * V3D(self._draw_plane.project(cam_pos) - cam_pos) < .0001:
                normal *= -1.

        self._draw_plane_normal = normal

        snap_settings = GD["snap"]
        snap_on = snap_settings["on"]["creation"] and snap_settings["on"]["creation_phase_2"]
        snap_tgt_type = snap_settings["tgt_type"]["creation_phase_2"]

        if snap_on and snap_tgt_type == "grid_point":

            # Snapping to any point on the active grid plane would just set the height
            # to zero, so a different grid plane needs to be set temporarily;
            # out of the two possible planes, choose the one that faces the camera most.

            grid_origin = Mgr.get("grid").origin
            active_plane_id = GD["active_grid_plane"]
            normal1 = Vec3()
            normal2 = Vec3()
            normal1["xyz".index(active_plane_id[0])] = 1.
            normal2["xyz".index(active_plane_id[1])] = 1.
            normal1 = GD.world.get_relative_vector(grid_origin, normal1)
            normal2 = GD.world.get_relative_vector(grid_origin, normal2)
            plane_id1 = "xyz".replace(active_plane_id[0], "")
            plane_id2 = "xyz".replace(active_plane_id[1], "")

            if abs(cam_forward_vec * normal1) > abs(cam_forward_vec * normal2):
                Mgr.update_app("active_grid_plane", plane_id1)
            else:
                Mgr.update_app("active_grid_plane", plane_id2)

            GD["active_grid_plane"] = active_plane_id

    def __creation_phase2(self):
        """ Draw out cylinder height """

        point = None
        snap_settings = GD["snap"]
        snap_on = snap_settings["on"]["creation"] and snap_settings["on"]["creation_phase_2"]
        snap_tgt_type = snap_settings["tgt_type"]["creation_phase_2"]

        if snap_on and snap_tgt_type != "increment":
            point = Mgr.get("snap_target_point")

        if point is None:

            if snap_on and snap_tgt_type != "increment":
                Mgr.do("set_projected_snap_marker_pos", None)

            if not GD.mouse_watcher.has_mouse():
                return

            screen_pos = GD.mouse_watcher.get_mouse()
            cam = GD.cam()
            lens_type = GD.cam.lens_type

            near_point = Point3()
            far_point = Point3()
            GD.cam.lens.extrude(screen_pos, near_point, far_point)
            rel_pt = lambda point: GD.world.get_relative_point(cam, point)
            near_point = rel_pt(near_point)
            far_point = rel_pt(far_point)

            if lens_type == "persp":
                # the height cannot be calculated if the cursor points away from the plane
                # in which it is drawn out
                if V3D(far_point - near_point) * self._draw_plane_normal < .0001:
                    return

            point = Point3()

            if not self._draw_plane.intersects_line(point, near_point, far_point):
                return

        else:

            point = GD.world.get_relative_point(Mgr.get("grid").origin, point)
            vec = point - self._dragged_point
            proj_point = self._dragged_point + vec.project(self._height_axis)
            Mgr.do("set_projected_snap_marker_pos", proj_point)

        tmp_prim = self.get_temp_primitive()
        pivot = tmp_prim.pivot
        z = pivot.get_relative_point(GD.world, point)[2]

        if snap_on and snap_tgt_type == "increment":
            offset_incr = snap_settings["increment"]["creation_phase_2"]
            z = round(z / offset_incr) * offset_incr

        tmp_prim.update_size(height=z)

    def __finish_creation_phase2(self):
        """ End creation phase 2 by setting default cylinder height """

        prop_defaults = self.get_property_defaults()
        tmp_prim = self.get_temp_primitive()
        tmp_prim.update_size(height=prop_defaults["height"])

    def create_custom_primitive(self, name, radius, height, segments, pos, rel_to_grid=False,
                                smooth=True, gradual=False):

        model_id = self.generate_object_id()
        model = Mgr.do("create_model", model_id, name, pos)

        if not rel_to_grid:
            pivot = model.pivot
            pivot.clear_transform()
            pivot.set_pos(GD.world, pos)

        next_color = self.get_next_object_color()
        model.set_color(next_color, update_app=False)
        prim = Cylinder(model)

        for step in prim.create(segments, smooth):
            if gradual:
                yield

        prim.init_size(radius, height)
        prim.geom_data_obj.finalize_geometry()
        model.geom_obj = prim
        self.set_next_object_color()

        yield model


MainObjects.add_class(CylinderManager)
