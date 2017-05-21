from ..base import *
from .vert import MergedVertex
from .edge import MergedEdge


class PolygonEditBase(BaseObject):

    def get_polygon_selection_border(self):

        selected_poly_ids = self._selected_subobj_ids["poly"]

        if not selected_poly_ids:
            return set()

        merged_edges = self._merged_edges
        polys = self._subobjs["poly"]
        selected_polys = (polys[i] for i in selected_poly_ids)
        border_edges = []

        for poly in selected_polys:

            for edge_id in poly.get_edge_ids():

                merged_edge = merged_edges[edge_id]

                if merged_edge in border_edges:
                    border_edges.remove(merged_edge)
                else:
                    border_edges.append(merged_edge)

        return set(e_id for merged_edge in border_edges for e_id in merged_edge)

    def detach_polygons(self):

        edge_ids = self.get_polygon_selection_border()

        if not edge_ids:
            return False

        return self.split_edges(edge_ids)

    def stitch_polygons(self):

        edge_ids = self.get_polygon_selection_border()

        if not edge_ids:
            return False

        return self.stitch_edges(edge_ids)


class PolygonEditManager(BaseObject):

    def setup(self):

        Mgr.add_interface_updater("uv_window", "poly_detach", self.__detach_polygons)
        Mgr.add_interface_updater("uv_window", "poly_stitch", self.__stitch_polygons)

    def __detach_polygons(self):

        selection = self._selections[self._uv_set_id]["poly"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.detach_polygons()

    def __stitch_polygons(self):

        selection = self._selections[self._uv_set_id]["poly"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.stitch_polygons()
