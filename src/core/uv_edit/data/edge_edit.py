from ..base import *
from .vert import MergedVertex
from .edge import MergedEdge


class EdgeEditBase(BaseObject):

    def split_edges(self):

        selection_ids = self._selected_subobj_ids
        selected_edge_ids = selection_ids["edge"]

        if not selected_edge_ids:
            return False

        selected_vert_ids = selection_ids["vert"]
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        selected_edges = set([merged_edges[i] for i in selected_edge_ids])
        verts_to_split = {}

        change = False
        update_verts_to_transf = False
        update_polys_to_transf = False
        poly_verts_to_transf = self._verts_to_transf["poly"]

        # for each selected edge vertex, check the connected edges (in ordered fashion,
        # starting at the selected edge) until either the starting selected edge is
        # encountered (in this case, the vertex cannot be split), or a different
        # selected edge or border edge is encountered (if so, the vertex can be split);
        # if at least one of the vertices of an edge can be split, the edge itself
        # can be split;
        # border edges cannot be split
        for merged_edge in selected_edges:

            if len(merged_edge) == 1:
                edge1_id = merged_edge[0]
                edge2_id = None
            else:
                edge1_id, edge2_id = merged_edge

            edge1 = edges[edge1_id]
            vert_split = False

            for vert_id in edge1:

                merged_vert = merged_verts[vert_id]
                vert_ids_to_separate = []
                next_vert_id = vert_id
                edge_id = edge1_id

                while True:

                    next_vert = verts[next_vert_id]
                    vert_ids_to_separate.append(next_vert_id)
                    edge_ids = next_vert.get_edge_ids()

                    if edge_ids[0] == edge_id:
                        next_edge_id = edge_ids[1]
                    else:
                        next_edge_id = edge_ids[0]

                    if next_edge_id == edge2_id:
                        break

                    next_merged_edge = merged_edges[next_edge_id]

                    if next_merged_edge in selected_edges or len(next_merged_edge) == 1:

                        if len(merged_vert) > len(vert_ids_to_separate):

                            vert_ids = set(vert_ids_to_separate)

                            if vert_ids not in verts_to_split.setdefault(merged_vert, []):
                                verts_to_split[merged_vert].append(vert_ids)

                            vert_split = True

                        break

                    if next_merged_edge[0] == next_edge_id:
                        edge_id = next_merged_edge[1]
                    else:
                        edge_id = next_merged_edge[0]

                    edge = edges[edge_id]

                    if merged_verts[edge[0]] == merged_vert:
                        next_vert_id = edge[0]
                    else:
                        next_vert_id = edge[1]

            if vert_split:

                if len(merged_edge) > 1:
                    new_merged_edge = MergedEdge(self)
                    new_merged_edge.append(edge1_id)
                    merged_edge.remove(edge1_id)
                    merged_edges[edge1_id] = new_merged_edge

                change = True

        if change:

            for merged_vert in verts_to_split:

                for vert_ids_to_separate in verts_to_split[merged_vert]:

                    new_merged_vert = MergedVertex(self)

                    for id_to_separate in vert_ids_to_separate:

                        merged_vert.remove(id_to_separate)
                        new_merged_vert.append(id_to_separate)
                        merged_verts[id_to_separate] = new_merged_vert

                        if id_to_separate in selected_vert_ids:
                            update_verts_to_transf = True

                        if merged_vert in poly_verts_to_transf:
                            update_polys_to_transf = True

            if update_verts_to_transf:
                self._update_verts_to_transform("vert")

            self._update_verts_to_transform("edge")

            if update_polys_to_transf:
                self._update_verts_to_transform("poly")

        return change


class EdgeEditManager(BaseObject):

    def setup(self):

        Mgr.add_interface_updater(
            "uv_window", "edge_split", self.__split_edges)

    def __split_edges(self):

        selection = self._selections[self._uv_set_id]["edge"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.split_edges()
