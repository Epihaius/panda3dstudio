from .base import *


def _get_mesh_density(segments):

    poly_count = segments["x"] * segments["y"]

    return poly_count


def _define_geom_data(segments, temp=False):

    geom_data = []
    edge_positions = {}

    # Define vertex data

    segs1 = segments["x"]
    segs2 = segments["y"]
    i1 = 0
    i2 = 1
    range1 = range(segs1 + 1)
    range2 = range(segs2 + 1)

    vert_id = 0
    vert_data = {}
    normal = Vec3(0., 0., 1.)

    for i in range2:

        b = (1. / segs2) * i
        y = b - .5

        for j in range1:

            a = (1. / segs1) * j
            x = a - .5
            pos = (x, y, 0.)

            if temp:
                vert_data[vert_id] = {"pos": pos, "normal": normal}
            else:
                vert_data[vert_id] = {"pos": pos, "normal": normal, "uvs": {0: (a, b)}}

            vert_id += 1

    if not temp:
        smoothing_id = 0

    # Define faces

    for i in range(segs2):

        for j in range(segs1):

            vi1 = i * (segs1 + 1) + j
            vi2 = vi1 + 1
            vi3 = vi2 + segs1
            vi4 = vi3 + 1
            vert_ids = (vi1, vi2, vi4)
            tri_data1 = [vert_data[vi] for vi in vert_ids]
            vert_ids = (vi1, vi4, vi3)
            tri_data2 = [vert_data[vi] for vi in vert_ids]

            if temp:
                poly_data = (tri_data1, tri_data2)
            else:
                tris = (tri_data1, tri_data2)
                poly_data = {"tris": tris, "smoothing": [(smoothing_id, True)]}

            geom_data.append(poly_data)

    return geom_data


class TemporaryPlane(TemporaryPrimitive):

    def __init__(self, segments, color, pos):

        TemporaryPrimitive.__init__(self, "plane", color, pos)

        self._size = {"x": 0., "y": 0.}
        geom_data = _define_geom_data(segments, True)
        self.create_geometry(geom_data)

    def update_size(self, x=None, y=None):

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


class Plane(Primitive):

    def __init__(self, model):

        prop_ids = ["size_{}".format(axis) for axis in "xy"]
        prop_ids.append("segments")

        Primitive.__init__(self, "plane", model, prop_ids)

        self._segments = {"x": 1, "y": 1}
        self._segments_backup = {"x": 1, "y": 1}
        self._size = {"x": 0., "y": 0.}

    def define_geom_data(self):

        return _define_geom_data(self._segments)

    def create(self, segments, force_gradual=False):

        self._segments = segments
        poly_count = 0 if force_gradual else _get_mesh_density(segments)

        for step in Primitive.create(self, poly_count, force_gradual):
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
        origin = self.get_origin()
        origin.set_scale(sx, sy, 1.)
        self.reset_initial_coords()
        self.get_geom_data_object().bake_transform()

    def init_size(self, x, y):

        origin = self.get_origin()
        size = self._size
        size["x"] = max(abs(x), .001)
        size["y"] = max(abs(y), .001)

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
            Mgr.update_remotely("selected_obj_prop", "plane", "segments", self._segments)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "plane", prop_id,
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


class PlaneManager(PrimitiveManager):

    def __init__(self):

        PrimitiveManager.__init__(self, "plane", custom_creation=True)

        for axis in "xy":
            self.set_property_default("size_{}".format(axis), 1.)

        self.set_property_default("temp_segments", {"x": 1, "y": 1})
        self.set_property_default("segments", {"x": 1, "y": 1})

    def setup(self):

        creation_phases = []
        creation_phase = (lambda: None, self.__creation_phase1)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "plane"
        status_text["phase1"] = "draw out the plane"

        return PrimitiveManager.setup(self, creation_phases, status_text)

    def create_temp_primitive(self, color, pos):

        segs = self.get_property_defaults()["segments"]
        tmp_segs = self.get_property_defaults()["temp_segments"]
        segments = dict((axis, min(segs[axis], tmp_segs[axis])) for axis in "xy")
        tmp_prim = TemporaryPlane(segments, color, pos)

        return tmp_prim

    def create_primitive(self, model):

        prim = Plane(model)
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
            x, y = [prop_defaults["size_{}".format(axis)] for axis in "xy"]
        else:
            x, y = [size[axis] for axis in "xy"]

        prim.init_size(x, y)

    def __creation_phase1(self):
        """ Draw out plane """

        if not self.mouse_watcher.has_mouse():
            return

        screen_pos = self.mouse_watcher.get_mouse()
        point = Mgr.get(("grid", "point_at_screen_pos"), screen_pos)

        if not point:
            return

        grid_origin = Mgr.get(("grid", "origin"))
        tmp_prim = self.get_temp_primitive()
        pivot = tmp_prim.get_pivot()
        x, y, z = pivot.get_relative_point(grid_origin, point)
        tmp_prim.update_size(x, y)

    def create_custom_primitive(self, name, x, y, segments, pos, inverted=False,
                                rel_to_grid=False, gradual=False):

        model_id = self.generate_object_id()
        model = Mgr.do("create_model", model_id, name, pos)

        if gradual:
            id_str = str(model_id)
            handler = lambda info: model.cancel_creation()
            Mgr.add_notification_handler("long_process_cancelled", id_str, handler, once=True)

        if not rel_to_grid:
            pivot = model.get_pivot()
            pivot.clear_transform()
            pivot.set_pos(self.world, pos)

        next_color = self.get_next_object_color()
        model.set_color(next_color, update_app=False)
        prim = Plane(model)

        for step in prim.create(segments, force_gradual=gradual):
            if gradual:
                yield

        prim.init_size(x, y)
        prim.get_geom_data_object().finalize_geometry()
        model.set_geom_object(prim)
        self.set_next_object_color()

        if inverted:
            prim.set_property("normal_flip", True)

        if gradual:
            Mgr.remove_notification_handler("long_process_cancelled", id_str)

        yield model


MainObjects.add_class(PlaneManager)
