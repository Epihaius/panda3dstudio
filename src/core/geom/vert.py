from ..base import *


class Vertex(BaseObject):

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_geom_data_obj"] = None
        state["_data"] = data = self._data.copy()
        data["row_offset"] = 0

        return state

    def __init__(self, vert_id, picking_col_id, geom_data_obj, pos):

        self._type = "vert"
        self._full_type = "single_vert"
        self._id = vert_id
        self._picking_col_id = picking_col_id
        self._geom_data_obj = geom_data_obj
        self._creation_time = None
        self._prev_prop_time = {
            "transform": None,
            "uvs": None,
            "normal": None,
            "normal_lock": None
        }
        self._pos = Point3(*pos)  # in local space
        self._edge_ids = []
        self._poly_id = None
        self._data = {
            "row": 0,
            "row_offset": 0,
            "uvs": {},
            "normal": None,
            "normal_is_locked": False,
            "tangent_space": (Vec3(), Vec3())
        }

    def get_type(self):

        return self._type

    def get_full_type(self):

        return self._full_type

    def get_id(self):

        return self._id

    def get_picking_color_id(self):

        return self._picking_col_id

    def set_geom_data_object(self, geom_data_obj):

        self._geom_data_obj = geom_data_obj

    def get_geom_data_object(self):

        return self._geom_data_obj

    def get_toplevel_object(self, get_group=False):

        return self._geom_data_obj.get_toplevel_object(get_group)

    def get_merged_object(self):

        return self._geom_data_obj.get_merged_vertex(self._id)

    def get_merged_vertex(self):

        return self._geom_data_obj.get_merged_vertex(self._id)

    def set_creation_time(self, time_id):

        self._creation_time = time_id

    def get_creation_time(self):

        return self._creation_time

    def set_previous_property_time(self, prop_id, time_id):

        self._prev_prop_time[prop_id] = time_id

    def get_previous_property_time(self, prop_id):

        return self._prev_prop_time[prop_id]

    def set_pos(self, pos, ref_node=None):

        if ref_node:
            origin = self._geom_data_obj.get_origin()
            self._pos = origin.get_relative_point(ref_node, pos)
        else:
            self._pos = pos

    def get_pos(self, ref_node=None):

        if ref_node:
            origin = self._geom_data_obj.get_origin()
            return ref_node.get_relative_point(origin, self._pos)

        return self._pos

    def get_initial_pos(self):

        owner = self._geom_data_obj.get_owner()

        if owner.get_type() != "editable_geom":
            return owner.get_initial_pos(self._id)

        return self._pos

    def get_center_pos(self, ref_node=None):

        if ref_node:
            origin = self._geom_data_obj.get_origin()
            return ref_node.get_relative_point(origin, self._pos)

        return self._pos

    def add_edge_id(self, edge_id):

        self._edge_ids.append(edge_id)

    def get_edge_ids(self):

        return self._edge_ids

    def set_polygon_id(self, poly_id):

        self._poly_id = poly_id

    def get_polygon_id(self):

        return self._poly_id

    def get_special_selection(self):

        return [self]

    def set_row_index(self, index):

        self._data["row"] = index

    def offset_row_index(self, offset):

        self._data["row_offset"] += offset

    def get_row_index(self):

        data = self._data

        return data["row"] + data["row_offset"]

    def get_row_indices(self):

        return [self.get_row_index()]

    def set_uvs(self, uvs, uv_set_id=None):

        if uv_set_id is None:
            uv_data = dict((k, v) for k, v in uvs.items() if v != (0., 0.))
            self._data["uvs"] = uv_data
        elif uvs != (0., 0.):
            self._data["uvs"][uv_set_id] = uvs
        elif uv_set_id in self._data["uvs"]:
            del self._data["uvs"][uv_set_id]

    def get_uvs(self, uv_set_id=None):

        if uv_set_id is None:
            return self._data["uvs"]

        return self._data["uvs"].get(uv_set_id, (0., 0.))

    def set_color(self, color):

        if color == (1., 1., 1., 1.):
            if "color" in self._data:
                del self._data["color"]
        else:
            self._data["color"] = color

    def get_color(self):

        return self._data.get("color", (1., 1., 1., 1.))

    def set_normal(self, normal):

        self._data["normal"] = normal

    def get_normal(self):

        return self._data["normal"]

    def get_shared_normal(self):

        return self._geom_data_obj.get_shared_normal(self._id)

    def lock_normal(self, locked=True):

        if self._data["normal_is_locked"] == locked:
            return False

        self._data["normal_is_locked"] = locked

        return True

    def has_locked_normal(self):

        return self._data["normal_is_locked"]

    def get_polygon_normal(self):

        poly = Mgr.get("poly", self._poly_id)

        return poly.get_normal() if poly else None

    def set_tangent_space(self, tangent_space):

        self._data["tangent_space"] = tangent_space

    def get_tangent_space(self):

        return self._data["tangent_space"]

    def get_point_at_screen_pos(self, screen_pos):

        cam = self.cam()
        normal = self.world.get_relative_vector(cam, Vec3.forward())
        plane = Plane(normal, self.get_pos(self.world))

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)

        intersection_point = Point3()
        plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point))

        return intersection_point


class MergedVertex:

    def __getstate__(self):

        # When pickling a MergedVertex, it should not have a GeomDataObject, since
        # this will be pickled separately.

        state = self.__dict__.copy()
        state["_geom_data_obj"] = None

        return state

    def __init__(self, geom_data_obj, vert_id=None):

        self._type = "vert"
        self._full_type = "merged_vert"
        self._geom_data_obj = geom_data_obj
        self._ids = [] if vert_id is None else [vert_id]

    def __lt__(self, other):

        return id(self) < id(other)

    def __le__(self, other):

        return id(self) <= id(other)

    def __gt__(self, other):

        return id(self) < id(other)

    def __ge__(self, other):

        return id(self) <= id(other)

    def __getitem__(self, index):

        try:
            return self._ids[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __len__(self):

        return len(self._ids)

    def append(self, vert_id):

        self._ids.append(vert_id)

    def extend(self, vert_ids):

        self._ids.extend(vert_ids)

    def remove(self, vert_id):

        self._ids.remove(vert_id)

    def get_type(self):

        return self._type

    def get_full_type(self):

        return self._full_type

    def get_id(self):

        vert = self._geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_id() if vert else None

    def get_picking_color_id(self):

        vert = self._geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_picking_color_id() if vert else None

    def get_picking_color_ids(self):

        verts = self._geom_data_obj.get_subobjects("vert")

        return [verts[v_id].get_picking_color_id() for v_id in self._ids]

    def is_border_vertex(self):

        geom_data_obj = self._geom_data_obj
        verts = geom_data_obj.get_subobjects("vert")

        for vert_id in self._ids:
            for edge_id in verts[vert_id].get_edge_ids():
                if len(geom_data_obj.get_merged_edge(edge_id)) == 1:
                    return True

        return False

    def get_edge_ids(self):

        verts = self._geom_data_obj.get_subobjects("vert")
        edge_ids = []

        for vert_id in self._ids:
            edge_ids.extend(verts[vert_id].get_edge_ids())

        return edge_ids

    def get_polygon_ids(self):

        verts = self._geom_data_obj.get_subobjects("vert")

        return [verts[v_id].get_polygon_id() for v_id in self._ids]

    def get_connected_verts(self):

        verts = self._geom_data_obj.get_subobjects("vert")

        return set(verts[v_id] for v_id in self._ids)

    def get_connected_edges(self):

        verts = self._geom_data_obj.get_subobjects("vert")
        edges = self._geom_data_obj.get_subobjects("edge")

        return set(edges[e_id] for v_id in self._ids for e_id in verts[v_id].get_edge_ids())

    def get_connected_polys(self):

        verts = self._geom_data_obj.get_subobjects("vert")
        polys = self._geom_data_obj.get_subobjects("poly")

        return set(polys[verts[v_id].get_polygon_id()] for v_id in self._ids)

    def get_connected_subobjs(self, subobj_type):

        if subobj_type == "vert":
            return self.get_connected_verts()
        elif subobj_type == "edge":
            return self.get_connected_edges()
        elif subobj_type == "poly":
            return self.get_connected_polys()

    def get_special_selection(self):

        return [self]

    def get_row_indices(self):

        verts = self._geom_data_obj.get_subobjects("vert")

        return [verts[v_id].get_row_index() for v_id in self._ids]

    def set_geom_data_object(self, geom_data_obj):

        self._geom_data_obj = geom_data_obj

    def get_geom_data_object(self):

        return self._geom_data_obj

    def get_toplevel_object(self, get_group=False):

        return self._geom_data_obj.get_toplevel_object(get_group)

    def set_previous_property_time(self, prop_id, time_id):

        verts = self._geom_data_obj.get_subobjects("vert")

        for vert_id in self._ids:
            verts[vert_id].set_previous_property_time(prop_id, time_id)

    def get_previous_property_time(self, prop_id):

        vert = self._geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_previous_property_time(prop_id)

    def set_pos(self, pos, ref_node=None):

        verts = self._geom_data_obj.get_subobjects("vert")

        for vert_id in self._ids:
            verts[vert_id].set_pos(pos, ref_node)

    def get_pos(self, ref_node=None):

        vert = self._geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_pos(ref_node)

    def get_center_pos(self, ref_node=None):

        vert = self._geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_center_pos(ref_node)

    def get_point_at_screen_pos(self, screen_pos):

        vert = self._geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_point_at_screen_pos(screen_pos)

    def is_facing_camera(self):

        verts = self._geom_data_obj.get_subobjects("vert")

        for vert_id in self._ids:

            poly = self._geom_data_obj.get_subobject("poly", verts[vert_id].get_polygon_id())

            if poly.is_facing_camera():
                return True

        return False


class VertexManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "vert", self.__create_vertex, "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("vert")
        Mgr.accept("create_merged_vert", self.__create_merged_vertex)

    def __create_vertex(self, geom_data_obj, pos):

        vert_id = self.get_next_id()
        picking_col_id = self.get_next_picking_color_id()
        vertex = Vertex(vert_id, picking_col_id, geom_data_obj, pos)

        return vertex

    def __create_merged_vertex(self, geom_data_obj, vert_id=None):

        vertex = MergedVertex(geom_data_obj, vert_id)

        return vertex


MainObjects.add_class(VertexManager)
