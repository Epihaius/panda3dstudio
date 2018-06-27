from .base import *


def _get_mesh_density(segments):

    poly_count = 2 * segments["x"] * segments["y"]
    poly_count += 2 * segments["x"] * segments["z"]
    poly_count += 2 * segments["y"] * segments["z"]

    return poly_count


def _define_geom_data(segments, temp=False):

    geom_data = []
    # store PosObjs referring to positions along the box edges, so they can be
    # shared by adjacent sides; this in turn will ensure that the corresponding
    # Vertex objects will be merged
    edge_positions = {}

    def get_side_data(i):

        d = {}

        for sign in (-1, 1):
            d[sign] = {
                "normal": tuple(sign * 1. if x == i else 0. for x in range(3)),
                "vert_data": {}
            }

        return "xyz"[i - 2] + "xyz"[i - 1], d

    sides = {k: v for k, v in (get_side_data(i) for i in range(3))}

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
        range1 = range(segs1 + 1)
        range2 = range(segs2 + 1)
        side_pair = sides[plane]

        for direction in side_pair:

            vert_id = 0
            side = side_pair[direction]
            vert_data = side["vert_data"]
            normal = side["normal"]
            coords[axis3] = (0. if direction == -1 else 1.) + offsets[axis3]
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

                    if temp:
                        vert_data[vert_id] = {"pos": pos_obj, "normal": normal}
                    else:
                        u = (-b if plane == "zx" else a) * direction
                        u += (1. if (direction > 0 if plane == "zx" else direction < 0) else 0.)
                        v = a if plane == "zx" else b
                        vert_data[vert_id] = {"pos": pos_obj, "normal": normal, "uvs": {0: (u, v)}}

                    vert_id += 1

    if not temp:
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

            for i in range(segs2):

                for j in range(segs1):

                    vi1 = i * (segs1 + 1) + j
                    vi2 = vi1 + 1
                    vi3 = vi2 + segs1
                    vi4 = vi3 + 1
                    vert_ids = (vi1, vi2, vi4) if direction == 1 else (vi1, vi4, vi2)
                    tri_data1 = [vert_data[vi] for vi in vert_ids]
                    vert_ids = (vi1, vi4, vi3) if direction == 1 else (vi1, vi3, vi4)
                    tri_data2 = [vert_data[vi] for vi in vert_ids]

                    if temp:
                        poly_data = (tri_data1, tri_data2)
                    else:
                        tris = (tri_data1, tri_data2)
                        poly_data = {"tris": tris, "smoothing": [(smoothing_id, True)]}

                    geom_data.append(poly_data)

            if not temp:
                smoothing_id += 1

    return geom_data


class TemporaryBox(TemporaryPrimitive):

    def __init__(self, segments, color, pos):

        TemporaryPrimitive.__init__(self, "box", color, pos)

        self._size = {"x": 0., "y": 0., "z": 0.}
        geom_data = _define_geom_data(segments, True)
        self.create_geometry(geom_data)
        self.get_origin().set_sz(.001)

    def update_size(self, x=None, y=None, z=None):

        origin = self.get_origin()
        size = self._size

        if x is not None:

            sx = max(abs(x), .001)
            sy = max(abs(y), .001)

            origin.set_x((-sx if x < 0. else sx) * .5)
            origin.set_y((-sy if y < 0. else sy) * .5)

            if size["x"] != sx:
                size["x"] = sx
                origin.set_sx(sx)

            if size["y"] != sy:
                size["y"] = sy
                origin.set_sy(sy)

        if z is not None:

            sz = max(abs(z), .001)
            s = -sz if z < 0. else sz

            if size["z"] != s:
                size["z"] = s
                origin.set_sz(sz)
                origin.set_z(s if s < 0. else 0.)

    def get_size(self):

        return self._size

    def is_valid(self):

        return max(self._size.values()) > .001

    def finalize(self):

        pos = self._pivot.get_pos()
        pivot = self.get_pivot()
        origin = self.get_origin()
        x, y, z = origin.get_pos()
        pos = self.world.get_relative_point(pivot, Point3(x, y, 0.))
        pivot.set_pos(self.world, pos)
        origin.set_x(0.)
        origin.set_y(0.)

        return TemporaryPrimitive.finalize(self)


class Box(Primitive):

    def __init__(self, model):

        prop_ids = ["size_{}".format(axis) for axis in "xyz"]
        prop_ids.append("segments")

        Primitive.__init__(self, "box", model, prop_ids)

        self._segments = {"x": 1, "y": 1, "z": 1}
        self._segments_backup = {"x": 1, "y": 1, "z": 1}
        self._size = {"x": 0., "y": 0., "z": 0.}

    def define_geom_data(self):

        return _define_geom_data(self._segments)

    def create(self, segments):

        self._segments = segments

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

        size = self._size
        sx = size["x"]
        sy = size["y"]
        sz = size["z"]
        origin = self.get_origin()
        origin.set_scale(sx, sy, abs(sz))
        origin.set_z(sz if sz < 0. else 0.)
        self.reset_initial_coords()
        self.get_geom_data_object().bake_transform()

    def init_size(self, x, y, z):

        origin = self.get_origin()
        size = self._size
        size["x"] = max(abs(x), .001)
        size["y"] = max(abs(y), .001)
        size["z"] = max(abs(z), .001) * (-1. if z < 0. else 1.)

        self.__update_size()

    def set_dimension(self, axis, value):

        if self._size[axis] == value:
            return False

        self._size[axis] = value

        return True

    def get_side_data(self):

        side_data = {}
        side_ids = ("left", "right", "back", "front", "bottom", "top")
        side_axes = ("x", "x", "y", "y", "z", "z")
        side_vecs = (Vec3.left(), Vec3.right(), Vec3.back(), Vec3.forward(), Vec3.down(), Vec3.up())
        size = self._size.copy()
        height = size["z"]
        size["z"] = abs(height)
        segs = self._segments
        center = Point3() + Vec3.up() * height * .5

        for side_id, side_axis, side_vec in zip(side_ids, side_axes, side_vecs):
            pos = center + side_vec * size[side_axis] * .5
            x, y = [size[axis] for axis in "xyz".replace(side_axis, "")]
            segs_x, segs_y = [segs[axis] for axis in "xyz".replace(side_axis, "")]
            side_segs = {"x": segs_x, "y": segs_y}
            side_data[side_id] = {"pos": pos, "size": (x, y), "segs": side_segs}

        return side_data

    def get_data_to_store(self, event_type, prop_id=""):

        if event_type == "prop_change" and prop_id in self.get_type_property_ids():

            data = {}
            data[prop_id] = {"main": self.get_property(prop_id)}

            if prop_id == "segments":
                data.update(self.get_geom_data_backup().get_data_to_store("deletion"))
                data.update(self.get_geom_data_object().get_data_to_store("creation"))
                self.remove_geom_data_backup()
            elif "size" in prop_id:
                data.update(self.get_geom_data_object().get_property_to_store("subobj_transform",
                                                                              "prop_change", "all"))

            return data

        return Primitive.get_data_to_store(self, event_type, prop_id)

    def cancel_geometry_recreation(self, info):

        Primitive.cancel_geometry_recreation(self, info)

        if info == "creation":
            self._segments = self._segments_backup
            Mgr.update_remotely("selected_obj_prop", "box", "segments", self._segments)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "box", prop_id,
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
                    self.recreate_geometry(_get_mesh_density(segments))

                update_app()

            return change

        elif "size" in prop_id:

            axis = prop_id.split("_")[1]
            change = self.set_dimension(axis, value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("set_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.get_model().update_group_bbox()
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
        elif "size" in prop_id:
            axis = prop_id.split("_")[1]
            return self._size[axis]
        else:
            return Primitive.get_property(self, prop_id, for_remote_update)

    def __center_origin(self, adjust_pivot=True):

        model = self.get_model()
        origin = self.get_origin()
        x, y, z = origin.get_pos()
        pivot = model.get_pivot()

        if adjust_pivot:
            pos = self.world.get_relative_point(pivot, Point3(x, y, 0.))
            pivot.set_pos(self.world, pos)

        origin.set_x(0.)
        origin.set_y(0.)

    def finalize(self):

        self.__center_origin()
        self.__update_size()

        Primitive.finalize(self)


class BoxManager(PrimitiveManager):

    def __init__(self):

        PrimitiveManager.__init__(self, "box", custom_creation=True)

        self._height_axis = V3D(0., 0., 1.)
        self._draw_plane = None
        self._draw_plane_normal = V3D()
        self._dragged_point = Point3()
        self._tmp_box_origin = None
        self._created_planes = []

        for axis in "xyz":
            self.set_property_default("size_{}".format(axis), 1.)

        self.set_property_default("temp_segments", {"x": 1, "y": 1, "z": 1})
        self.set_property_default("segments", {"x": 1, "y": 1, "z": 1})

        Mgr.add_app_updater("box_to_planes", self.__convert_boxes_to_planes)

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

    def create_temp_primitive(self, color, pos):

        segs = self.get_property_defaults()["segments"]
        tmp_segs = self.get_property_defaults()["temp_segments"]
        segments = dict((axis, min(segs[axis], tmp_segs[axis])) for axis in "xyz")
        tmp_prim = TemporaryBox(segments, color, pos)

        return tmp_prim

    def create_primitive(self, model):

        prim = Box(model)
        segments = self.get_property_defaults()["segments"]
        poly_count = _get_mesh_density(segments)
        progress_steps = (poly_count // 20) * 4
        gradual = progress_steps > 80

        for step in prim.create(segments):
            if gradual:
                yield

        yield prim, gradual

    def init_primitive_size(self, prim, size=None):

        if size is None:
            prop_defaults = self.get_property_defaults()
            x, y, z = [prop_defaults["size_{}".format(axis)] for axis in "xyz"]
        else:
            x, y, z = [size[axis] for axis in "xyz"]

        prim.init_size(x, y, z)

    def __start_creation_phase1(self):
        """ Start drawing out box base """

        tmp_prim = self.get_temp_primitive()
        origin = tmp_prim.get_origin()
        self._height_axis = self.world.get_relative_vector(origin, V3D(0., 0., 1.))

    def __creation_phase1(self):
        """ Draw out box base """

        screen_pos = self.mouse_watcher.get_mouse()
        point = Mgr.get(("grid", "point_at_screen_pos"), screen_pos)

        if not point:
            return

        grid_origin = Mgr.get(("grid", "origin"))
        self._dragged_point = self.world.get_relative_point(grid_origin, point)
        tmp_prim = self.get_temp_primitive()
        pivot = tmp_prim.get_pivot()
        x, y, z = pivot.get_relative_point(grid_origin, point)
        tmp_prim.update_size(x, y)

    def __start_creation_phase2(self):
        """ Start drawing out box height """

        cam = self.cam()
        cam_forward_vec = self.world.get_relative_vector(cam, Vec3.forward())
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

        if self.cam.lens_type == "persp":

            cam_pos = cam.get_pos(self.world)

            if normal * V3D(self._draw_plane.project(cam_pos) - cam_pos) < .0001:
                normal *= -1.

        self._draw_plane_normal = normal

    def __creation_phase2(self):
        """ Draw out box height """

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

        point = Point3()

        if not self._draw_plane.intersects_line(point, near_point, far_point):
            return

        tmp_prim = self.get_temp_primitive()
        pivot = tmp_prim.get_pivot()
        z = pivot.get_relative_point(self.world, point)[2]
        tmp_prim.update_size(z=z)

    def create_custom_primitive(self, name, x, y, z, segments, pos, inverted=False,
                                rel_to_grid=False, gradual=False):

        model_id = self.generate_object_id()
        model = Mgr.do("create_model", model_id, name, pos)

        if not rel_to_grid:
            pivot = model.get_pivot()
            pivot.clear_transform()
            pivot.set_pos(self.world, pos)

        next_color = self.get_next_object_color()
        model.set_color(next_color, update_app=False)
        prim = Box(model)

        for step in prim.create(segments):
            if gradual:
                yield

        prim.init_size(x, y, z)
        prim.get_geom_data_object().finalize_geometry()
        model.set_geom_object(prim)
        self.set_next_object_color()

        if inverted:
            prim.set_property("normal_flip", True)

        yield model

    def __boxes_to_planes_conversion(self):

        selection = Mgr.get("selection_top")
        objs = selection[:]
        obj_names = GlobalData["obj_names"]
        box_names = []

        poly_count = 0

        for obj in objs:
            geom_data_obj = obj.get_geom_object().get_geom_data_object()
            poly_count += len(geom_data_obj.get_subobjects("poly"))

        progress_steps = (poly_count // 20) * 4
        gradual = progress_steps > 80

        if gradual:
            Mgr.update_remotely("screenshot", "create")
            GlobalData["progress_steps"] = progress_steps

        planes = self._created_planes
        side_hprs = {"left": VBase3(0., 90., -90.), "right": VBase3(0., 90., 90.),
                     "back": VBase3(0., 90., 0.), "front": VBase3(180., 90., 0.),
                     "bottom": VBase3(180., 180., 0.), "top": VBase3(0., 0., 0.)}

        for obj in objs:

            group = obj.get_group()
            parent = obj.get_parent()
            material = obj.get_material()
            box_name = obj.get_name()
            box_names.append(box_name)
            box_origin = NodePath(obj.get_origin().node().make_copy())
            box_origin.set_transform(obj.get_origin().get_net_transform())
            self._tmp_box_origin = box_origin
            box = obj.get_geom_object()
            side_data = box.get_side_data()

            for side_id, data in side_data.items():

                name = box_name + " " + side_id
                name = get_unique_name(name, obj_names)
                obj_names.append(name)
                pos = data["pos"]
                x, y = data["size"]
                segments = data["segs"]
                inverted = box.has_flipped_normals()
                creator = Mgr.do("create_custom_plane", name, x, y, segments, pos,
                                 inverted, gradual=gradual)

                for plane in creator:
                    if gradual:
                        yield True

                plane.register(restore=False)
                planes.append(plane)
                plane_pivot = plane.get_pivot()
                plane_pivot.set_hpr(side_hprs[side_id])
                plane_pivot.reparent_to(box_origin)
                plane_pivot.wrt_reparent_to(Mgr.get("object_root"))

                if group:
                    plane.set_group(group.get_id())
                elif parent:
                    plane.set_parent(parent.get_id())

                if material:
                    plane.set_material(material)

            box_origin.remove_node()

        Mgr.exit_state("processing")
        self._tmp_box_origin = None

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in objs:
            obj_data[obj.get_id()] = obj.get_data_to_store("deletion")
            obj.destroy(add_to_hist=False)

        for plane in planes:
            hist_data = plane.get_data_to_store("creation")
            hist_data["selection_state"] = {"main": True}
            obj_data[plane.get_id()] = hist_data

        selection.add(planes, add_to_hist=False, update=False)
        self._created_planes = []

        if len(objs) == 1:
            event_descr = 'Make planes from box "{}"'.format(box_names[0])
        else:
            event_descr = 'Make planes from boxes:\n'
            event_descr += "".join(['\n    "{}"'.format(name) for name in box_names])

        event_data = {"objects": obj_data}
        event_data["object_ids"] = set(Mgr.get("object_ids"))
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        yield False

    def __cancel_conversion_process(self, info):

        if info == "convert_boxes_to_planes":

            for obj in self._created_planes:
                obj.destroy(unregister=False, add_to_hist=False)

            self._created_planes = []

            if self._tmp_box_origin:
                self._tmp_box_origin.remove_node()
                self._tmp_box_origin = None

    def __convert_boxes_to_planes(self):

        Mgr.do("create_registry_backups")
        Mgr.do("create_id_range_backups")
        process = self.__boxes_to_planes_conversion()

        if next(process):
            handler = self.__cancel_conversion_process
            Mgr.add_notification_handler("long_process_cancelled", "box_mgr", handler, once=True)
            task = lambda: Mgr.remove_notification_handler("long_process_cancelled", "box_mgr")
            task_id = "remove_notification_handler"
            PendingTasks.add(task, task_id, "object", id_prefix="box_mgr", sort=100)
            descr = "Converting..."
            Mgr.do_gradually(process, "convert_boxes_to_planes", descr, cancellable=True)


MainObjects.add_class(BoxManager)
