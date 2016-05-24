from ..base import *
from .vert import MergedVertex
from .edge import MergedEdge


class VertexEditBase(BaseObject):

    def break_vertices(self):

        selected_vert_ids = self._selected_subobj_ids["vert"]

        if not selected_vert_ids:
            return False

        verts = self._subobjs["vert"]
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts_to_break = set([merged_verts[v_id] for v_id in selected_vert_ids])
        edges_to_split = set()

        change = False
        update_edges_to_transf = False
        update_polys_to_transf = False
        edge_verts_to_transf = self._verts_to_transf["edge"]
        poly_verts_to_transf = self._verts_to_transf["poly"]

        for merged_vert in verts_to_break:

            if len(merged_vert) == 1:
                continue

            for vert_id in merged_vert[1:]:

                merged_vert.remove(vert_id)
                new_merged_vert = MergedVertex(self)
                new_merged_vert.append(vert_id)
                merged_verts[vert_id] = new_merged_vert

                for edge_id in verts[vert_id].get_edge_ids():
                    edges_to_split.add(merged_edges[edge_id])

            change = True

            if merged_vert in edge_verts_to_transf:
                update_edges_to_transf = True
            if merged_vert in poly_verts_to_transf:
                update_polys_to_transf = True

        for merged_edge in edges_to_split:

            if len(merged_edge) == 1:
                continue

            for edge_id in merged_edge[1:]:
                merged_edge.remove(edge_id)
                new_merged_edge = MergedEdge(self)
                new_merged_edge.append(edge_id)
                merged_edges[edge_id] = new_merged_edge

        if change:

            self._update_verts_to_transform("vert")

            if update_edges_to_transf:
                self._update_verts_to_transform("edge")
            if update_polys_to_transf:
                self._update_verts_to_transform("poly")

        return change


class VertexEditManager(BaseObject):

    def setup(self):

        Mgr.add_interface_updater("uv_window", "vert_break", self.__break_vertices)

    def __break_vertices(self):

        selection = self._selections[self._uv_set_id]["vert"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.break_vertices()
