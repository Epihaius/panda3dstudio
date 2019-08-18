from ..base import *


class Edge:

    __slots__ = ("type", "id", "picking_color_id", "_vert_ids",
                 "polygon_id", "uv_data_obj")

    def __init__(self, edge_id, picking_col_id, uv_data_obj=None,
                 poly_id=None, vert_ids=None, data_copy=None):

        self.type = "edge"
        self.id = edge_id
        self.picking_color_id = picking_col_id
        self.uv_data_obj = uv_data_obj

        if data_copy:
            poly_id = data_copy["poly_id"]
            vert_ids = data_copy["vert_ids"]

        self.polygon_id = poly_id
        self._vert_ids = vert_ids

    def copy(self):

        data_copy = {}
        data_copy["vert_ids"] = self._vert_ids[:]
        data_copy["poly_id"] = self.polygon_id
        edge = Edge(self.id, self.picking_color_id, data_copy=data_copy)

        return edge

    def __getitem__(self, index):

        try:
            return self._vert_ids[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    @property
    def merged_subobj(self):

        return self.uv_data_obj.get_merged_edge(self.id)

    @property
    def merged_edge(self):

        return self.uv_data_obj.get_merged_edge(self.id)

    @property
    def vertices(self):

        verts = self.uv_data_obj.get_subobjects("vert")

        return [verts[vert_id] for vert_id in self._vert_ids]

    @property
    def start_row_index(self):

        verts = self.uv_data_obj.get_subobjects("vert")

        return verts[self._vert_ids[0]].row_index

    @property
    def row_indices(self):

        verts = self.uv_data_obj.get_subobjects("vert")
        count = len(verts)
        r1, r2 = (verts[vert_id].row_index for vert_id in self._vert_ids)

        return [r1, r2 + count]

    def get_center_pos(self, ref_node=None):

        verts = self.uv_data_obj.get_subobjects("vert")

        return sum([verts[v_id].get_pos(ref_node) for v_id in self._vert_ids], Point3()) * .5


class MergedEdge:

    __slots__ = ("type", "full_type", "_ids", "uv_data_obj")

    def __init__(self, uv_data_obj, edge_ids=None):

        self.type = "edge"
        self.full_type = "merged_edge"
        self.uv_data_obj = uv_data_obj
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

    def extend(self, edge_ids):

        self._ids.extend(edge_ids)

    def remove(self, edge_id):

        self._ids.remove(edge_id)

    @property
    def id(self):

        edge = self.uv_data_obj.get_subobject("edge", self._ids[0])

        return edge.id if edge else None

    @property
    def picking_color_id(self):

        edge = self.uv_data_obj.get_subobject("edge", self._ids[0])

        return edge.picking_color_id if edge else None

    @property
    def picking_color_ids(self):

        edges = self.uv_data_obj.get_subobjects("edge")

        return [edges[e_id].picking_color_id for e_id in self._ids]

    @property
    def polygon_ids(self):

        edges = self.uv_data_obj.get_subobjects("edge")

        return [edges[e_id].polygon_id for e_id in self._ids]

    @property
    def special_selection(self):

        edges = [self]

        if GD["uv_edit_options"]["sel_edges_by_seam"] and len(self._ids) == 1:
            edges = self.uv_data_obj.get_seam_edges(self)

        return edges

    @property
    def start_row_indices(self):

        edges = self.uv_data_obj.get_subobjects("edge")

        return [edges[e_id].start_row_index for e_id in self._ids]

    @property
    def row_indices(self):

        edges = self.uv_data_obj.get_subobjects("edge")
        row_indices = []

        for e_id in self._ids:
            row_indices.extend(edges[e_id].row_indices)

        return row_indices

    def get_center_pos(self, ref_node=None):

        edge = self.uv_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_center_pos(ref_node)
