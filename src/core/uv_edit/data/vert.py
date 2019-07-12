from ..base import *


class Vertex(BaseObject):

    def __init__(self, vert_id, picking_col_id, pos, uv_data_obj=None,
                 poly_id=None, edge_ids=None, data_copy=None):

        self._type = "vert"
        self._full_type = "single_vert"
        self._id = vert_id
        self._picking_col_id = picking_col_id
        self._uv_data_obj = uv_data_obj
        self._prev_prop_time = {"transform": None}
        self._pos = Point3(*pos)  # in local space

        if data_copy:
            poly_id = data_copy["poly_id"]
            edge_ids = data_copy["edge_ids"]
            data = data_copy["data"]
        else:
            data = {"row": 0, "row_offset": 0}

        self._poly_id = poly_id
        self._edge_ids = edge_ids
        self._data = data

    def copy(self):

        data_copy = {}
        data_copy["poly_id"] = self._poly_id
        data_copy["edge_ids"] = self._edge_ids[:]
        data_copy["data"] = self._data.copy()
        vert = Vertex(self._id, self._picking_col_id, self._pos, data_copy=data_copy)

        return vert

    def get_type(self):

        return self._type

    def get_full_type(self):

        return self._full_type

    def get_id(self):

        return self._id

    def get_picking_color_id(self):

        return self._picking_col_id

    def set_uv_data_object(self, uv_data_obj):

        self._uv_data_obj = uv_data_obj

    def get_uv_data_object(self):

        return self._uv_data_obj

    def get_merged_object(self):

        return self._uv_data_obj.get_merged_vertex(self._id)

    def get_merged_vertex(self):

        return self._uv_data_obj.get_merged_vertex(self._id)

    def set_previous_property_time(self, prop_id, time_id):

        self._prev_prop_time[prop_id] = time_id

    def get_previous_property_time(self, prop_id):

        return self._prev_prop_time[prop_id]

    def set_pos(self, pos, ref_node=None):

        if ref_node:
            origin = self._uv_data_obj.get_origin()
            self._pos = origin.get_relative_point(ref_node, pos)
        else:
            self._pos = pos

    def get_pos(self, ref_node=None):

        if ref_node:
            origin = self._uv_data_obj.get_origin()
            return ref_node.get_relative_point(origin, self._pos)

        return self._pos

    def get_center_pos(self, ref_node=None):

        if ref_node:
            origin = self._uv_data_obj.get_origin()
            return ref_node.get_relative_point(origin, self._pos)

        return self._pos

    def get_polygon_id(self):

        return self._poly_id

    def get_edge_ids(self):

        return self._edge_ids

    def set_row_index(self, index):

        self._data["row"] = index

    def offset_row_index(self, offset):

        self._data["row_offset"] += offset

    def get_row_index(self):

        data = self._data

        return data["row"] + data["row_offset"]


class MergedVertex:

    def __init__(self, uv_data_obj, vert_ids=None):

        self._type = "vert"
        self._full_type = "merged_vert"
        self._uv_data_obj = uv_data_obj
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

    def get_type(self):

        return self._type

    def get_full_type(self):

        return self._full_type

    def get_id(self):

        vert = self._uv_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_id() if vert else None

    def get_picking_color_id(self):

        vert = self._uv_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_picking_color_id() if vert else None

    def get_picking_color_ids(self):

        verts = self._uv_data_obj.get_subobjects("vert")

        return [verts[v_id].get_picking_color_id() for v_id in self._ids]

    def get_polygon_ids(self):

        verts = self._uv_data_obj.get_subobjects("vert")

        return [verts[v_id].get_polygon_id() for v_id in self._ids]

    def get_special_selection(self):

        return [self]

    def get_row_indices(self):

        verts = self._uv_data_obj.get_subobjects("vert")

        return [verts[v_id].get_row_index() for v_id in self._ids]

    def set_uv_data_object(self, uv_data_obj):

        self._uv_data_obj = uv_data_obj

    def get_uv_data_object(self):

        return self._uv_data_obj

    def set_previous_property_time(self, prop_id, time_id):

        verts = self._uv_data_obj.get_subobjects("vert")

        for vert_id in self._ids:
            verts[vert_id].set_previous_property_time(prop_id, time_id)

    def get_previous_property_time(self, prop_id):

        vert = self._uv_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_previous_property_time(prop_id)

    def set_pos(self, pos, ref_node=None):

        verts = self._uv_data_obj.get_subobjects("vert")

        for vert_id in self._ids:
            verts[vert_id].set_pos(pos, ref_node)

    def get_pos(self, ref_node=None):

        vert = self._uv_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_pos(ref_node)

    def get_center_pos(self, ref_node=None):

        vert = self._uv_data_obj.get_subobject("vert", self._ids[0])

        return vert.get_center_pos(ref_node)
