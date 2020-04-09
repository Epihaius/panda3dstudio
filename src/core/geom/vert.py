from ..base import *


class Vertex:

    __slots__ = ("type", "full_type", "id", "picking_color_id", "edge_ids", "polygon_id",
                 "geom_data_obj", "creation_time", "_prev_prop_time", "_pos", "_data")

    def __getstate__(self):

        data = self._data.copy()
        data["row_offset"] = 0
        state = {
            "_id": self.id,
            "_picking_col_id": self.picking_color_id,
            "_creation_time": self.creation_time,
            "_prev_prop_time": self._prev_prop_time,
            "_edge_ids": self.edge_ids,
            "_poly_id": self.polygon_id,
            "_pos": self._pos,
            "_data": data
            # leave out the GeomDataObject, as it is pickled separately
        }

        return state

    def __setstate__(self, state):

        self.type = "vert"
        self.full_type = "single_vert"
        self.geom_data_obj = None
        self.id = state["_id"]
        self.picking_color_id = state["_picking_col_id"]
        self.creation_time = state["_creation_time"]
        self._prev_prop_time = state["_prev_prop_time"]
        self.edge_ids = state["_edge_ids"]
        self.polygon_id = state["_poly_id"]
        self._pos = state["_pos"]
        self._data = state["_data"]

    def __init__(self, vert_id, picking_col_id, geom_data_obj, pos):

        self.type = "vert"
        self.full_type = "single_vert"
        self.id = vert_id
        self.picking_color_id = picking_col_id
        self.geom_data_obj = geom_data_obj
        self.creation_time = None
        self._prev_prop_time = {
            "transform": None,
            "uvs": None,
            "normal": None,
            "normal_lock": None
        }
        self._pos = Point3(*pos)  # in local space
        self.edge_ids = []
        self.polygon_id = None
        self._data = {
            "row": 0,
            "row_offset": 0,
            "uvs": {},
            "normal": None,
            "normal_is_locked": False,
            "tangent_space": (Vec3(), Vec3())
        }

    @property
    def color(self):

        return self._data.get("color", (1., 1., 1., 1.))

    @color.setter
    def color(self, color):

        if color == (1., 1., 1., 1.):
            if "color" in self._data:
                del self._data["color"]
        else:
            self._data["color"] = color

    def get_toplevel_object(self, get_group=False):

        return self.geom_data_obj.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    @property
    def edges(self):

        edges = self.geom_data_obj.get_subobjects("edge")

        return [edges[edge_id] for edge_id in self.edge_ids]

    @property
    def polygon(self):

        return self.geom_data_obj.get_subobject("poly", self.polygon_id)

    @property
    def merged_subobj(self):

        return self.geom_data_obj.get_merged_vertex(self.id)

    @property
    def merged_vertex(self):

        return self.geom_data_obj.get_merged_vertex(self.id)

    def set_previous_property_time(self, prop_id, time_id):

        self._prev_prop_time[prop_id] = time_id

    def get_previous_property_time(self, prop_id):

        return self._prev_prop_time[prop_id]

    def set_pos(self, pos, ref_node=None):

        if ref_node:
            origin = self.geom_data_obj.origin
            self._pos = origin.get_relative_point(ref_node, pos)
        else:
            self._pos = pos

    def get_pos(self, ref_node=None):

        if ref_node:
            origin = self.geom_data_obj.origin
            return ref_node.get_relative_point(origin, self._pos)

        return self._pos

    def get_center_pos(self, ref_node=None):

        if ref_node:
            origin = self.geom_data_obj.origin
            return ref_node.get_relative_point(origin, self._pos)

        return self._pos

    def add_edge_id(self, edge_id):

        self.edge_ids.append(edge_id)

    @property
    def special_selection(self):

        return [self]

    @property
    def row_index(self):

        data = self._data

        return data["row"] + data["row_offset"]

    @row_index.setter
    def row_index(self, index):

        self._data["row"] = index

    def offset_row_index(self, offset):

        self._data["row_offset"] += offset

    @property
    def row_indices(self):

        return [self.row_index]

    def set_uvs(self, uvs, uv_set_id=None):

        if uv_set_id is None:
            uv_data = {k: v for k, v in uvs.items() if v != (0., 0.)}
            self._data["uvs"] = uv_data
        elif uvs != (0., 0.):
            self._data["uvs"][uv_set_id] = uvs
        elif uv_set_id in self._data["uvs"]:
            del self._data["uvs"][uv_set_id]

    def get_uvs(self, uv_set_id=None):

        if uv_set_id is None:
            return self._data["uvs"]

        return self._data["uvs"].get(uv_set_id, (0., 0.))

    @property
    def normal(self):

        return Vec3(self._data["normal"])

    @normal.setter
    def normal(self, normal):

        self._data["normal"] = normal

    @property
    def shared_normal(self):

        return self.geom_data_obj.get_shared_normal(self.id)

    def lock_normal(self, locked=True):

        if self._data["normal_is_locked"] == locked:
            return False

        self._data["normal_is_locked"] = locked

        return True

    def has_locked_normal(self):

        return self._data["normal_is_locked"]

    @property
    def tangent_space(self):

        return self._data["tangent_space"]

    @tangent_space.setter
    def tangent_space(self, tangent_space):

        self._data["tangent_space"] = tangent_space

    def get_point_at_screen_pos(self, screen_pos):

        cam = GD.cam()
        normal = GD.world.get_relative_vector(cam, Vec3.forward())
        plane = Plane(normal, self.get_pos(GD.world))

        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.world.get_relative_point(cam, point)

        intersection_point = Point3()
        plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point))

        return intersection_point


class MergedVertex:

    __slots__ = ("type", "full_type", "_ids", "geom_data_obj")

    def __getstate__(self):

        state = {
            "_ids": self._ids
            # leave out the GeomDataObject, as it is pickled separately
        }

        return state

    def __setstate__(self, state):

        self.type = "vert"
        self.full_type = "merged_vert"
        self.geom_data_obj = None
        self._ids = state["_ids"]

    def __init__(self, geom_data_obj, vert_id=None):

        self.type = "vert"
        self.full_type = "merged_vert"
        self.geom_data_obj = geom_data_obj
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

    @property
    def id(self):

        vert = self.geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.id if vert else None

    @property
    def picking_color_id(self):

        vert = self.geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.picking_color_id if vert else None

    @property
    def picking_color_ids(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        return [verts[v_id].picking_color_id for v_id in self._ids]

    @property
    def edge_ids(self):

        return [e_id for v in self.vertices for e_id in v.edge_ids]

    @property
    def polygon_ids(self):

        return [v.polygon_id for v in self.vertices]

    @property
    def vertices(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        return [verts[v_id] for v_id in self._ids]

    @property
    def edges(self):

        edges = self.geom_data_obj.get_subobjects("edge")

        return [edges[e_id] for e_id in self.edge_ids]

    @property
    def polygons(self):

        polys = self.geom_data_obj.get_subobjects("poly")

        return [polys[p_id] for p_id in self.polygon_ids]

    def is_border_vertex(self):

        return any(len(e.merged_edge) == 1 for v in self.vertices for e in v.edges)

    @property
    def connected_verts(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        return set(verts[v_id] for v_id in self._ids)

    @property
    def connected_edges(self):

        verts = self.geom_data_obj.get_subobjects("vert")
        edges = self.geom_data_obj.get_subobjects("edge")

        return set(edges[e_id] for v_id in self._ids for e_id in verts[v_id].edge_ids)

    @property
    def connected_polys(self):

        verts = self.geom_data_obj.get_subobjects("vert")
        polys = self.geom_data_obj.get_subobjects("poly")

        return set(polys[verts[v_id].polygon_id] for v_id in self._ids)

    def get_connected_subobjs(self, subobj_type):

        if subobj_type == "vert":
            return self.connected_verts
        elif subobj_type == "edge":
            return self.connected_edges
        elif subobj_type == "poly":
            return self.connected_polys

    @property
    def special_selection(self):

        return [self]

    @property
    def row_indices(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        return [verts[v_id].row_index for v_id in self._ids]

    def get_toplevel_object(self, get_group=False):

        return self.geom_data_obj.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def set_previous_property_time(self, prop_id, time_id):

        verts = self.geom_data_obj.get_subobjects("vert")

        for vert_id in self._ids:
            verts[vert_id].set_previous_property_time(prop_id, time_id)

    def get_previous_property_time(self, prop_id):

        vert = self.geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_previous_property_time(prop_id)

    def set_pos(self, pos, ref_node=None):

        verts = self.geom_data_obj.get_subobjects("vert")

        for vert_id in self._ids:
            verts[vert_id].set_pos(pos, ref_node)

    def get_pos(self, ref_node=None):

        vert = self.geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_pos(ref_node)

    def get_center_pos(self, ref_node=None):

        vert = self.geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_center_pos(ref_node)

    def get_point_at_screen_pos(self, screen_pos):

        vert = self.geom_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_point_at_screen_pos(screen_pos)

    def is_facing_camera(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        for vert_id in self._ids:

            poly = self.geom_data_obj.get_subobject("poly", verts[vert_id].polygon_id)

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
