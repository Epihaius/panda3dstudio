from ..base import *


class Polygon(BaseObject):

    def __init__(self, poly_id, picking_col_id, uv_data_obj=None, triangle_data=None,
                 vert_ids=None, edge_ids=None, data_copy=None):

        self._type = "poly"
        self._id = poly_id
        self._picking_col_id = picking_col_id
        self._uv_data_obj = uv_data_obj

        if data_copy:
            center_pos = data_copy["center_pos"]
            triangle_data = data_copy["tri_data"]
            vert_ids = data_copy["vert_ids"]
            edge_ids = data_copy["edge_ids"]
        else:
            center_pos = Point3()

        self._center_pos = center_pos
        self._tri_data = triangle_data
        self._vert_ids = vert_ids
        self._edge_ids = edge_ids

    def copy(self):

        data_copy = {}
        data_copy["center_pos"] = self._center_pos
        data_copy["tri_data"] = self._tri_data[:]
        data_copy["vert_ids"] = self._vert_ids[:]
        data_copy["edge_ids"] = self._edge_ids[:]
        poly = Polygon(self._id, self._picking_col_id, data_copy=data_copy)

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

        return self

    def get_neighbor_ids(self):

        merged_verts = self._uv_data_obj.get_merged_vertices()
        neighbor_ids = set()

        for vert_id in self._vert_ids:
            neighbor_ids.update(merged_verts[vert_id].get_polygon_ids())

        neighbor_ids.remove(self._id)

        return neighbor_ids

    def get_vertex_ids(self):

        return self._vert_ids

    def get_edge_ids(self):

        return self._edge_ids

    def get_vertices(self):

        verts = self._uv_data_obj.get_subobjects("vert")

        return [verts[vert_id] for vert_id in self._vert_ids]

    def get_edges(self):

        edges = self._uv_data_obj.get_subobjects("edge")

        return [edges[edge_id] for edge_id in self._edge_ids]

    def get_vertex_count(self):

        return len(self._vert_ids)

    def get_row_indices(self):

        verts = self._uv_data_obj.get_subobjects("vert")

        return [verts[vert_id].get_row_index() for vert_id in self._vert_ids]

    def get_special_selection(self):

        polys = [self]

        if GlobalData["uv_edit_options"]["sel_polys_by_cluster"]:
            polys = self._uv_data_obj.get_polygon_cluster(self._id)

        return polys

    def update_center_pos(self):

        verts = self.get_vertices()
        positions = [vert.get_pos() for vert in verts]
        self._center_pos = sum(positions, Point3()) / len(positions)

    def set_center_pos(self, center_pos):

        self._center_pos = center_pos

    def get_center_pos(self, ref_node):

        origin = self._uv_data_obj.get_origin()
        pos = ref_node.get_relative_point(origin, self._center_pos)

        return pos
