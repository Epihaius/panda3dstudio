from ..base import *


class Vertex:

    __slots__ = ("type", "full_type", "id", "picking_color_id", "edge_ids", "polygon_id",
                 "uv_data_obj", "_prev_prop_time", "_pos", "_data")

    def __init__(self, vert_id, picking_col_id, pos, uv_data_obj=None,
                 poly_id=None, edge_ids=None, data_copy=None):

        self.type = "vert"
        self.full_type = "single_vert"
        self.id = vert_id
        self.picking_color_id = picking_col_id
        self.uv_data_obj = uv_data_obj
        self._prev_prop_time = {"transform": None}
        self._pos = Point3(*pos)  # in local space

        if data_copy:
            poly_id = data_copy["poly_id"]
            edge_ids = data_copy["edge_ids"]
            data = data_copy["data"]
        else:
            data = {"row": 0, "row_offset": 0}

        self.polygon_id = poly_id
        self.edge_ids = edge_ids
        self._data = data

    def copy(self):

        data_copy = {}
        data_copy["poly_id"] = self.polygon_id
        data_copy["edge_ids"] = self.edge_ids[:]
        data_copy["data"] = self._data.copy()
        vert = Vertex(self.id, self.picking_color_id, self._pos, data_copy=data_copy)

        return vert

    @property
    def merged_subobj(self):

        return self.uv_data_obj.get_merged_vertex(self.id)

    @property
    def merged_vertex(self):

        return self.uv_data_obj.get_merged_vertex(self.id)

    def set_previous_property_time(self, prop_id, time_id):

        self._prev_prop_time[prop_id] = time_id

    def get_previous_property_time(self, prop_id):

        return self._prev_prop_time[prop_id]

    def set_pos(self, pos, ref_node=None):

        if ref_node:
            origin = self.uv_data_obj.origin
            self._pos = origin.get_relative_point(ref_node, pos)
        else:
            self._pos = pos

    def get_pos(self, ref_node=None):

        if ref_node:
            origin = self.uv_data_obj.origin
            return ref_node.get_relative_point(origin, self._pos)

        return self._pos

    def get_center_pos(self, ref_node=None):

        if ref_node:
            origin = self.uv_data_obj.origin
            return ref_node.get_relative_point(origin, self._pos)

        return self._pos

    @property
    def row_index(self):

        data = self._data

        return data["row"] + data["row_offset"]

    @row_index.setter
    def row_index(self, index):

        self._data["row"] = index

    def offset_row_index(self, offset):

        self._data["row_offset"] += offset


class MergedVertex:

    __slots__ = ("type", "full_type", "_ids", "uv_data_obj")

    def __init__(self, uv_data_obj, vert_ids=None):

        self.type = "vert"
        self.full_type = "merged_vert"
        self.uv_data_obj = uv_data_obj
        self._ids = [] if vert_ids is None else vert_ids

    def copy(self):

        return MergedVertex(None, self._ids)

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

        vert = self.uv_data_obj.get_subobject("vert", self._ids[0])

        return vert.id if vert else None

    @property
    def picking_color_id(self):

        vert = self.uv_data_obj.get_subobject("vert", self._ids[0])

        return vert.picking_color_id if vert else None

    @property
    def picking_color_ids(self):

        verts = self.uv_data_obj.get_subobjects("vert")

        return [verts[v_id].picking_color_id for v_id in self._ids]

    @property
    def edge_ids(self):

        verts = self.uv_data_obj.get_subobjects("vert")
        edge_ids = []

        for vert_id in self._ids:
            edge_ids.extend(verts[vert_id].edge_ids)

        return edge_ids

    @property
    def polygon_ids(self):

        verts = self.uv_data_obj.get_subobjects("vert")

        return [verts[v_id].polygon_id for v_id in self._ids]

    @property
    def special_selection(self):

        return [self]

    @property
    def row_indices(self):

        verts = self.uv_data_obj.get_subobjects("vert")

        return [verts[v_id].row_index for v_id in self._ids]

    def set_previous_property_time(self, prop_id, time_id):

        verts = self.uv_data_obj.get_subobjects("vert")

        for vert_id in self._ids:
            verts[vert_id].set_previous_property_time(prop_id, time_id)

    def get_previous_property_time(self, prop_id):

        vert = self.uv_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_previous_property_time(prop_id)

    def set_pos(self, pos, ref_node=None):

        verts = self.uv_data_obj.get_subobjects("vert")

        for vert_id in self._ids:
            verts[vert_id].set_pos(pos, ref_node)

    def get_pos(self, ref_node=None):

        vert = self.uv_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_pos(ref_node)

    def get_center_pos(self, ref_node=None):

        vert = self.uv_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_center_pos(ref_node)
