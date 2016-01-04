from .base import *


class BoxManager(PrimitiveManager):

    def __init__(self):

        PrimitiveManager.__init__(self, "box")

        self._height_axis = V3D(0., 0., 1.)
        self._draw_plane = None
        self._draw_plane_normal = V3D()
        self._base_center = V3D()
        self._dragged_point = Point3()

        axes = "xyz"
        prop_types = ("size", "segments")
        defaults = (1., 1)

        for prop_type, value in zip(prop_types, defaults):
            for axis in axes:
                prop_id = "%s_%s" % (prop_type, axis)
                self.set_property_default(prop_id, value)

        Mgr.accept("inst_create_box", self.create_instantly)

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1)
        creation_phases.append(creation_phase)
        creation_phase = (self.__start_creation_phase2, self.__creation_phase2)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "box"
        status_text["phase1"] = "draw out the base"
        status_text["phase2"] = "draw out the height"

        return PrimitiveManager.setup(self, creation_phases, status_text)

    def apply_default_size(self, prim):

        prop_defaults = self.get_property_defaults()
        x, y, z = [prop_defaults["size_%s" % axis] for axis in "xyz"]
        prim.update_creation_size(x, y, z, finalize=True)

    def init_primitive(self, model):

        prim = Box(model)
        prop_defaults = self.get_property_defaults()
        segments = {}

        for axis in "xyz":
            segments[axis] = prop_defaults["segments_%s" % axis]

        prim.create(segments)

        return prim

    def __start_creation_phase1(self):
        """ Start drawing out box base """

        prim = self.get_primitive()
        origin = prim.get_model().get_origin()
        self._height_axis = self.world.get_relative_vector(
            origin, V3D(0., 0., 1.))

    def __creation_phase1(self):
        """ Draw out box base """

        mpos = self.mouse_watcher.get_mouse()
        point = Mgr.get(("grid", "point_at_screen_pos"), mpos)

        if not point:
            return

        grid_origin = Mgr.get(("grid", "origin"))
        self._dragged_point = self.world.get_relative_point(grid_origin, point)
        prim = self.get_primitive()
        origin = prim.get_model().get_origin()
        x, y, z = origin.get_relative_point(grid_origin, point)
        prim.update_creation_size(x, y)

        self._base_center = Point3((self.get_origin_pos() + point) * .5)

    def __start_creation_phase2(self):
        """ Start drawing out box height """

        cam_forward_vec = self.world.get_relative_vector(
            self.cam, Vec3(0., 1., 0.))
        normal = V3D(cam_forward_vec -
                     cam_forward_vec.project(self._height_axis))

        # If the plane normal is the null vector, the axis must be parallel to
        # the forward camera direction. In this case, a new normal can be chosen
        # arbitrarily, e.g. a horizontal vector perpendicular to the axis.

        if normal.length_squared() < .0001:

            x, y, z = self._height_axis

            # if the height axis is nearly vertical, any horizontal vector will
            # qualify as plane normal, e.g. a vector pointing in the the positive
            # X-direction; otherwise, the plane normal can be computed as
            # perpendicular to the axis
            if max(abs(x), abs(y)) < .0001:
                normal = V3D(1., 0., 0.)
            else:
                normal = V3D(y, -x, 0.)

        self._draw_plane = Plane(normal, self._dragged_point)
        cam_pos = self.cam.get_pos(self.world)

        if normal * V3D(self._draw_plane.project(cam_pos) - cam_pos) < .0001:
            normal *= -1.

        self._draw_plane_normal = normal

    def __creation_phase2(self):
        """ Draw out box height """

        if not self.mouse_watcher.has_mouse():
            return

        mpos = self.mouse_watcher.get_mouse()
        far_point_local = Point3()
        self.cam_lens.extrude(mpos, Point3(), far_point_local)
        far_point = self.world.get_relative_point(self.cam, far_point_local)
        cam_pos = self.cam.get_pos(self.world)

        # the height cannot be calculated if the cursor points away from the plane
        # in which it is drawn out
        if V3D(far_point - cam_pos) * self._draw_plane_normal < .0001:
            return

        point = Point3()

        if not self._draw_plane.intersects_line(point, cam_pos, far_point):
            return

        prim = self.get_primitive()
        origin = prim.get_model().get_origin()
        z = origin.get_relative_point(self.world, point)[2]
        prim.update_creation_size(z=z)


class Box(Primitive):

    def __init__(self, model):

        prop_types = ("size", "segments")
        axes = "xyz"
        prop_ids = ["%s_%s" % (prop_type, axis)
                    for prop_type in prop_types for axis in axes]

        Primitive.__init__(self, "box", model, prop_ids)

        self._segments = {"x": 1, "y": 1, "z": 1}
        self._size = {"x": 1., "y": 1., "z": 1.}

    def define_geom_data(self):

        geom_data = []
        # store PosObjs referring to positions along the box edges, so they can be
        # shared by adjacent sides; this in turn will ensure that the corresponding
        # Vertex objects will be merged
        edge_positions = {}

        def get_side_data(i):

            d = {}

            for sign in (-1, 1):
                d[sign] = {
                    "normal": tuple(map(lambda x: sign * 1. if x == i else 0., range(3))),
                    "vert_data": {}
                }

            return "xyz"[i - 2] + "xyz"[i - 1], d

        sides = dict(map(get_side_data, range(3)))
        segments = self._segments

        offsets = {"x": -.5, "y": -.5, "z": 0.}

        # Define vertex data

        for plane in sides:

            axis1, axis2 = plane
            axis3 = "xyz".replace(axis1, "").replace(axis2, "")
            coords = {"x": 0., "y": 0., "z": 0.}
            segs1 = segments[axis1]
            segs2 = segments[axis2]
            segs3 = segments[axis3]
            i1 = "xyz".index(axis1)
            i2 = "xyz".index(axis2)
            range1 = xrange(segs1 + 1)
            range2 = xrange(segs2 + 1)
            side_pair = sides[plane]

            for direction in side_pair:

                vert_id = 0
                side = side_pair[direction]
                vert_data = side["vert_data"]
                normal = side["normal"]
                coords[axis3] = (0. if direction == -
                                 1 else 1.) + offsets[axis3]
                offset1 = offsets[axis1]
                offset2 = offsets[axis2]

                for i in range2:

                    b = (1. / segs2) * i
                    coords[axis2] = b + offset2

                    for j in range1:

                        a = (1. / segs1) * j
                        coords[axis1] = a + offset1
                        pos = tuple(coords[axis] for axis in "xyz")

                        if i in (0, segs2) or j in (0, segs1):

                            k = 0 if direction == -1 else segs3
                            key_components = {axis1: j, axis2: i, axis3: k}
                            key = tuple(key_components[axis] for axis in "xyz")

                            if key in edge_positions:
                                pos_obj = edge_positions[key]
                            else:
                                pos_obj = PosObj(pos)
                                edge_positions[key] = pos_obj

                        else:

                            pos_obj = PosObj(pos)

                        u = (-b if plane == "zx" else a) * direction
                        u += (1. if (direction > 0 if plane ==
                                     "zx" else direction < 0) else 0.)
                        v = a if plane == "zx" else b
                        vert_data[vert_id] = {
                            "pos": pos_obj, "normal": normal, "uvs": {0: (u, v)}}
                        vert_id += 1

        smoothing_id = 0

        # Define faces

        for plane in sides:

            axis1, axis2 = plane
            segs1 = segments[axis1]
            segs2 = segments[axis2]
            side_pair = sides[plane]

            for direction in side_pair:

                side = side_pair[direction]
                vert_data = side["vert_data"]

                for i in xrange(segs2):

                    for j in xrange(segs1):

                        vi1 = i * (segs1 + 1) + j
                        vi2 = vi1 + 1
                        vi3 = vi2 + segs1
                        vi4 = vi3 + 1
                        vert_ids = (vi1, vi2, vi4) if direction == 1 else (
                            vi1, vi4, vi2)
                        tri_data1 = {"verts": [vert_data[vi]
                                               for vi in vert_ids]}
                        tri_data1["tangent_space"] = None
                        vert_ids = (vi1, vi4, vi3) if direction == 1 else (
                            vi1, vi3, vi4)
                        tri_data2 = {"verts": [vert_data[vi]
                                               for vi in vert_ids]}
                        tri_data2["tangent_space"] = None
                        tris = (tri_data1, tri_data2)
                        poly_data = {"tris": tris,
                                     "smoothing": [(smoothing_id, True)]}
                        geom_data.append(poly_data)

                smoothing_id += 1

        return geom_data

    def create(self, segments):

        self._segments = segments

        Primitive.create(self)

        self.get_origin().set_sz(.001)
        self.update_init_pos_data()

    def set_segments(self, axis, segments):

        if self._segments[axis] == segments:
            return False

        self._segments[axis] = segments

        return True

    def __update_size(self):

        size = self._size
        sx = size["x"]
        sy = size["y"]
        sz = size["z"]
        origin = self.get_origin()
        origin.set_scale(sx, sy, abs(sz))
        origin.set_z(sz if sz < 0. else 0.)
        self.reset_init_pos_data()
        self.get_geom_data_object().bake_transform()
        self.get_geom_data_object().update_poly_centers()
        self.get_model().get_bbox().update(*origin.get_tight_bounds())

    def update_creation_size(self, x=None, y=None, z=None, finalize=False):

        origin = self.get_origin()
        size = self._size

        if x is not None:

            sx = max(abs(x), .001)
            sy = max(abs(y), .001)

            origin.set_x((-sx if x < 0. else sx) * .5)
            origin.set_y((-sy if y < 0. else sy) * .5)

            if size["x"] != sx:

                size["x"] = sx

                if not finalize:
                    origin.set_sx(sx)

            if size["y"] != sy:

                size["y"] = sy

                if not finalize:
                    origin.set_sy(sy)

        if z is not None:

            sz = max(abs(z), .001)
            s = -sz if z < 0. else sz

            if size["z"] != s:

                size["z"] = s

                if not finalize:
                    origin.set_sz(sz)
                    origin.set_z(s if s < 0. else 0.)

        if finalize:
            self.__center_origin(adjust_model_origin=False)
            self.__update_size()

    def set_dimension(self, axis, value):

        if self._size[axis] == value:
            return False

        self._size[axis] = value

        return True

    def get_data_to_store(self, event_type, prop_id=""):

        if event_type == "prop_change" and prop_id in self.get_type_property_ids():

            data = {}
            data[prop_id] = {"main": self.get_property(prop_id)}

            if "segments" in prop_id:
                data.update(self.get_geom_data_object().get_data_to_store(
                    "subobj_change", info="rebuild"))
            elif "size" in prop_id:
                data.update(self.get_geom_data_object().get_property_to_store(
                    "subobj_transform", "prop_change", "all"))

            return data

        return Primitive.get_data_to_store(self, event_type, prop_id)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "box", prop_id,
                                self.get_property(prop_id, True))

        obj_id = self.get_toplevel_object().get_id()

        if "segments" in prop_id:

            axis = prop_id.split("_")[1]
            change = self.set_segments(
                axis, value["count"] if restore else value)

            if change:

                if restore:
                    task = lambda: self.restore_init_pos_data(
                        value["pos_data"])
                    sort = PendingTasks.get_sort(
                        "upd_vert_normals", "object") + 1
                    PendingTasks.add(task, "restore_pos_data",
                                     "object", sort, id_prefix=obj_id)
                else:
                    task = self.clear_geometry
                    task_id = "clear_geom_data"
                    PendingTasks.add(task, task_id, "object", id_prefix=obj_id)
                    task = self.recreate_geometry
                    task_id = "set_geom_data"
                    PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

                update_app()

            return change

        elif "size" in prop_id:

            axis = prop_id.split("_")[1]
            change = self.set_dimension(axis, value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("upd_vert_normals", "object") + 2
                PendingTasks.add(task, "upd_size", "object",
                                 sort, id_prefix=obj_id)
                update_app()

            return change

        else:

            return Primitive.set_property(self, prop_id, value, restore)

    def get_property(self, prop_id, for_remote_update=False):

        if "segments" in prop_id:
            axis = prop_id.split("_")[1]
            if for_remote_update:
                return self._segments[axis]
            else:
                return {"count": self._segments[axis], "pos_data": self.get_init_pos_data()}
        elif "size" in prop_id:
            axis = prop_id.split("_")[1]
            return self._size[axis]

    def __center_origin(self, adjust_model_origin=True):

        model = self.get_model()
        origin = self.get_origin()
        x, y, z = origin.get_pos()
        model_origin = model.get_origin()

        if adjust_model_origin:
            pos = self.world.get_relative_point(model_origin, Point3(x, y, 0.))
            model_origin.set_pos(self.world, pos)

        origin.set_x(0.)
        origin.set_y(0.)

    def finalize(self):

        self.__center_origin()
        self.__update_size()

        Primitive.finalize(self, update_poly_centers=False)

    def is_valid(self):

        return max(self._size.itervalues()) > .001


MainObjects.add_class(BoxManager)
