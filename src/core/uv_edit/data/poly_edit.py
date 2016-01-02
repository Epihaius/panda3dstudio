from ..base import *
from .vert import MergedVertex
from .edge import MergedEdge


class PolygonEditBase(BaseObject):

    def detach_polygons(self):

        selection_ids = self._selected_subobj_ids
        selected_poly_ids = selection_ids["poly"]

        if not selected_poly_ids:
            return False

        selected_vert_ids = selection_ids["vert"]
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        edges_to_split = []
        new_merged_verts = {}
        polys = self._subobjs["poly"]
        selected_polys = (polys[i] for i in selected_poly_ids)

        change = False
        update_verts_to_transf = False

        for poly in selected_polys:

            for vert_id in poly.get_vertex_ids():

                merged_vert = merged_verts[vert_id]

                if merged_vert in new_merged_verts:
                    new_merged_vert = new_merged_verts[merged_vert]
                elif len(merged_vert) == 1:
                    continue
                else:
                    new_merged_vert = MergedVertex(self)
                    new_merged_verts[merged_vert] = new_merged_vert

                merged_vert.remove(vert_id)
                new_merged_vert.append(vert_id)
                merged_verts[vert_id] = new_merged_vert

                change = True

                if vert_id in selected_vert_ids:
                    update_verts_to_transf = True

            for edge_id in poly.get_edge_ids():

                merged_edge = merged_edges[edge_id]

                if merged_edge in edges_to_split:
                    edges_to_split.remove(merged_edge)
                else:
                    edges_to_split.append(merged_edge)

        if change:

            selected_edge_ids = selection_ids["edge"]
            update_edges_to_transf = False

            for merged_edge in edges_to_split:

                edge_id = merged_edge[0]
                new_merged_edge = MergedEdge(self)
                new_merged_edge.append(edge_id)
                merged_edge.remove(edge_id)
                merged_edges[edge_id] = new_merged_edge

                if edge_id in selected_edge_ids:
                    update_edges_to_transf = True

            if update_verts_to_transf:
                self._update_verts_to_transform("vert")

            if update_edges_to_transf:
                self._update_verts_to_transform("edge")

            self._update_verts_to_transform("poly")

        return change


class PolygonEditManager(BaseObject):

    def setup(self):

        Mgr.add_interface_updater(
            "uv_window", "poly_detach", self.__detach_polygons)

    def __detach_polygons(self):

        selection = self._selections[self._uv_set_id]["poly"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.detach_polygons()
