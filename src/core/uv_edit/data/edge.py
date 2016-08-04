from ..base import *


class Edge(BaseObject):

    def __init__(self, edge_id, picking_col_id, uv_data_obj, verts, data_copy=None):

        self._type = "edge"
        self._id = edge_id
        self._picking_col_id = picking_col_id
        self._uv_data_obj = uv_data_obj

        if data_copy:

            poly_id = data_copy["poly_id"]
            vert_ids = data_copy["vert_ids"]

        else:

            poly_id = None
            vert_ids = [vert.get_id() for vert in verts]

            for vert in verts:
                vert.add_edge_id(edge_id)

        self._poly_id = poly_id
        self._vert_ids = vert_ids

    def copy(self):

        data_copy = {}
        data_copy["vert_ids"] = self._vert_ids[:]
        data_copy["poly_id"] = self._poly_id
        edge = Edge(self._id, self._picking_col_id, None, None, data_copy)

        return edge

    def __getitem__(self, index):

        try:
            return self._vert_ids[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def get_type(self):

        return self._type

    def get_id(self):

        return self._id

    def get_picking_color_id(self):

        return self._picking_col_id

    def set_uv_data_object(self, uv_data_obj):

        self._uv_data_obj = uv_data_obj

    def get_uv_data_object(self):

        return self._uv_data_obj

    def get_merged_object(self):

        return self._uv_data_obj.get_merged_edge(self._id)

    def get_merged_edge(self):

        return self._uv_data_obj.get_merged_edge(self._id)

    def set_polygon_id(self, polygon_id):

        self._poly_id = polygon_id

    def get_polygon_id(self):

        return self._poly_id

    def get_vertices(self):

        verts = self._uv_data_obj.get_subobjects("vert")

        return [verts[vert_id] for vert_id in self._vert_ids]

    def get_start_row_index(self):

        verts = self._uv_data_obj.get_subobjects("vert")

        return verts[self._vert_ids[0]].get_row_index()

    def get_row_indices(self):

        verts = self._uv_data_obj.get_subobjects("vert")
        count = len(verts)
        r1, r2 = (verts[vert_id].get_row_index() for vert_id in self._vert_ids)

        return [r1, r2 + count]

    def reverse_vertex_order(self):

        self._vert_ids = self._vert_ids[::-1]

    def get_center_pos(self, ref_node=None):

        verts = self._uv_data_obj.get_subobjects("vert")

        return sum([verts[v_id].get_pos(ref_node) for v_id in self._vert_ids], Point3()) * .5


class MergedEdge(object):

    def __init__(self, uv_data_obj, edge_ids=None):

        self._type = "edge"
        self._full_type = "merged_edge"
        self._uv_data_obj = uv_data_obj
        self._ids = [] if edge_ids is None else edge_ids

    def copy(self):

        return MergedEdge(None, self._ids)

    def __getitem__(self, index):

        try:
            return self._ids[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __len__(self):

        return len(self._ids)

    def append(self, edge_id):

        self._ids.append(edge_id)

    def remove(self, edge_id):

        self._ids.remove(edge_id)

    def get_type(self):

        return self._type

    def get_full_type(self):

        return self._full_type

    def get_id(self):

        edge = self._uv_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_id() if edge else None

    def get_picking_color_id(self):

        edge = self._uv_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_picking_color_id() if edge else None

    def get_picking_color_ids(self):

        edges = self._uv_data_obj.get_subobjects("edge")

        return [edges[e_id].get_picking_color_id() for e_id in self._ids]

    def get_polygon_ids(self):

        edges = self._uv_data_obj.get_subobjects("edge")

        return [edges[e_id].get_polygon_id() for e_id in self._ids]

    def get_start_row_indices(self):

        edges = self._uv_data_obj.get_subobjects("edge")

        return [edges[e_id].get_start_row_index() for e_id in self._ids]

    def get_row_indices(self):

        edges = self._uv_data_obj.get_subobjects("edge")
        row_indices = []

        for e_id in self._ids:
            row_indices.extend(edges[e_id].get_row_indices())

        return row_indices

    def set_uv_data_object(self, uv_data_obj):

        self._uv_data_obj = uv_data_obj

    def get_uv_data_object(self):

        return self._uv_data_obj

    def get_center_pos(self, ref_node=None):

        edge = self._uv_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_center_pos(ref_node)
