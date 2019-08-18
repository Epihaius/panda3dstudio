from ..base import *


class Polygon:

    __slots__ = ("type", "id", "picking_color_id", "vertex_ids", "edge_ids",
                 "uv_data_obj", "_tri_data", "_center_pos")

    def __init__(self, poly_id, picking_col_id, uv_data_obj=None, triangle_data=None,
                 vert_ids=None, edge_ids=None, data_copy=None):

        self.type = "poly"
        self.id = poly_id
        self.picking_color_id = picking_col_id
        self.uv_data_obj = uv_data_obj

        if data_copy:
            center_pos = data_copy["center_pos"]
            triangle_data = data_copy["tri_data"]
            vert_ids = data_copy["vert_ids"]
            edge_ids = data_copy["edge_ids"]
        else:
            center_pos = Point3()

        self._center_pos = center_pos
        self._tri_data = triangle_data
        self.vertex_ids = vert_ids
        self.edge_ids = edge_ids

    def copy(self):

        data_copy = {}
        data_copy["center_pos"] = self._center_pos
        data_copy["tri_data"] = self._tri_data[:]
        data_copy["vert_ids"] = self.vertex_ids[:]
        data_copy["edge_ids"] = self.edge_ids[:]
        poly = Polygon(self.id, self.picking_color_id, data_copy=data_copy)

        return poly

    def __getitem__(self, index):

        try:
            return self._tri_data[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __len__(self):
        """
        Return the size of the polygon corresponding to the number of data rows of
        the associated GeomTriangles object.

        """

        return len(self._tri_data) * 3

    @property
    def merged_subobj(self):

        return self

    @property
    def neighbor_ids(self):

        merged_verts = self.uv_data_obj.merged_verts
        neighbor_ids = set()

        for vert_id in self.vertex_ids:
            neighbor_ids.update(merged_verts[vert_id].polygon_ids)

        neighbor_ids.remove(self.id)

        return neighbor_ids

    @property
    def vertices(self):

        verts = self.uv_data_obj.get_subobjects("vert")

        return [verts[vert_id] for vert_id in self.vertex_ids]

    @property
    def edges(self):

        edges = self.uv_data_obj.get_subobjects("edge")

        return [edges[edge_id] for edge_id in self.edge_ids]

    @property
    def vertex_count(self):

        return len(self.vertex_ids)

    @property
    def row_indices(self):

        verts = self.uv_data_obj.get_subobjects("vert")

        return [verts[vert_id].row_index for vert_id in self.vertex_ids]

    @property
    def special_selection(self):

        polys = [self]

        if GD["uv_edit_options"]["sel_polys_by_cluster"]:
            polys = self.uv_data_obj.get_polygon_cluster(self.id)

        return polys

    def update_center_pos(self):

        verts = self.vertices
        positions = [vert.get_pos() for vert in verts]
        self._center_pos = sum(positions, Point3()) / len(positions)

    def set_center_pos(self, center_pos):

        self._center_pos = center_pos

    def get_center_pos(self, ref_node):

        origin = self.uv_data_obj.origin
        pos = ref_node.get_relative_point(origin, self._center_pos)

        return pos
