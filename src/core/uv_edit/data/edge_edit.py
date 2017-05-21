from ..base import *
from .vert import MergedVertex
from .edge import MergedEdge


class EdgeEditBase(BaseObject):

    def split_edges(self, edge_ids=None):

        selection_ids = self._selected_subobj_ids
        selected_edge_ids = selection_ids["edge"] if edge_ids is None else edge_ids

        if not selected_edge_ids:
            return False

        selected_vert_ids = selection_ids["vert"]
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        selected_edges = set(merged_edges[i] for i in selected_edge_ids)
        verts_to_split = {}

        change = False
        seam_edge_ids = []
        update_verts_to_transf = False
        update_edges_to_transf = not set(selection_ids["edge"]).isdisjoint(edge_ids) if edge_ids else True
        update_polys_to_transf = False
        poly_verts_to_transf = self._verts_to_transf["poly"]

        # for each selected edge vertex, check the connected edges (in ordered fashion,
        # starting at the selected edge) until either the starting selected edge is
        # encountered (in this case, the vertex cannot be split), or a different
        # selected edge or border edge is encountered (if so, the vertex can be split);
        # if at least one of the vertices of an edge can be split, the edge itself
        # can be split (unless it is a border edge)
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
                    next_edge_ids = next_vert.get_edge_ids()

                    if next_edge_ids[0] == edge_id:
                        next_edge_id = next_edge_ids[1]
                    else:
                        next_edge_id = next_edge_ids[0]

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

                # it is possible that only vertices are split, without splitting any edges,
                # e.g. when trying to split two border edges that meet at a vertex that is
                # shared with other border edges
                if len(merged_edge) > 1:
                    seam_edge_ids.extend([edge1_id, edge2_id])
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

            UVMgr.do("update_active_selection")

            if update_verts_to_transf:
                self._update_verts_to_transform("vert")

            if update_edges_to_transf:
                self._update_verts_to_transform("edge")

            if update_polys_to_transf:
                self._update_verts_to_transform("poly")

            if seam_edge_ids:

                self.add_seam_edges(seam_edge_ids)

                seam_edges_to_select = set(seam_edge_ids) & set(selection_ids["edge"])
                seam_edges_to_unselect = set(seam_edge_ids) - set(selection_ids["edge"])

                if seam_edges_to_select:
                    color = UVMgr.get("uv_selection_colors")["seam"]["selected"]
                    self.update_seam_selection(seam_edges_to_select, color)
                    self._geom_data_obj.update_tex_seam_selection(seam_edges_to_select, color)

                if seam_edges_to_unselect:
                    color = UVMgr.get("uv_selection_colors")["seam"]["unselected"]
                    self.update_seam_selection(seam_edges_to_unselect, color)
                    self._geom_data_obj.update_tex_seam_selection(seam_edges_to_unselect, color)

        return change

    def stitch_edges(self, edge_ids=None):

        selection_ids = self._selected_subobj_ids
        selected_edge_ids = selection_ids["edge"]
        seam_edge_ids = set(selected_edge_ids if edge_ids is None else edge_ids)

        if not seam_edge_ids:
            return False, False

        selected_vert_ids = selection_ids["vert"]
        selected_poly_ids = selection_ids["poly"]
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        geom_data_obj = self._geom_data_obj
        merged_geom_verts = geom_data_obj.get_merged_vertices()

        seam_edges_to_remove = set()
        uv_by_geom_vert = {}
        tmp_merged_vert = MergedVertex(self)
        tmp_merged_edge = MergedEdge(self)

        for edge1_id in seam_edge_ids:

            if len(merged_edges[edge1_id]) > 1:
                continue

            merged_geom_edge = geom_data_obj.get_merged_edge(edge1_id)

            if len(merged_geom_edge) == 1:
                continue

            seam_edges_to_remove.update(merged_geom_edge)
            edge_id1, edge_id2 = merged_geom_edge
            edge2_id = edge_id1 if edge_id2 == edge1_id else edge_id2
            vert_ids = edges[edge1_id]
            src_verts = [merged_verts[vert_id] for vert_id in vert_ids]

            for vert_id in vert_ids:
                d = uv_by_geom_vert.setdefault(merged_geom_verts[vert_id],
                                               {"src": set(), "dest": set()})
                merged_vert = merged_verts[vert_id]
                d["src"].add(merged_vert)

            vert_ids = edges[edge2_id]

            for vert_id in vert_ids:

                d = uv_by_geom_vert.setdefault(merged_geom_verts[vert_id],
                                               {"src": set(), "dest": set()})
                merged_vert = merged_verts[vert_id]

                if merged_vert in src_verts:
                    d["src"].remove(merged_vert)
                else:
                    d["dest"].add(merged_vert)

        if not seam_edges_to_remove:
            return False, False

        verts_to_move = set()
        new_merged_verts = []

        for merged_geom_vert, d in uv_by_geom_vert.iteritems():

            src_verts = d["src"]
            dest_verts = d["dest"]
            dest_vert_count = len(dest_verts)
            pos = sum([v.get_pos() for v in dest_verts], Point3()) / dest_vert_count

            id_set = set()

            for merged_vert in src_verts:
                id_set.update(merged_vert)
                merged_vert.set_pos(pos)

            for merged_vert in dest_verts:
                id_set.update(merged_vert)
                merged_vert.set_pos(pos)

            verts_to_move.update(id_set)

            new_merged_vert = MergedVertex(self)
            new_merged_vert.extend(id_set)
            new_merged_verts.append(new_merged_vert)

            for vert_id in id_set:
                merged_verts[vert_id] = new_merged_vert

            if not (id_set.isdisjoint(selected_vert_ids) or id_set.issubset(selected_vert_ids)):
                tmp_merged_vert.extend(id_set.difference(selected_vert_ids))

        update_polys_to_transf = False

        for merged_vert in new_merged_verts:

            edges_by_merged_vert = {}

            for vert_id in merged_vert:

                vert = verts[vert_id]

                if vert.get_polygon_id() in selected_poly_ids:
                    update_polys_to_transf = True

                for edge1_id in vert.get_edge_ids():

                    merged_edge = merged_edges[edge1_id]

                    if len(merged_edge) > 1:
                        continue

                    vert1_id, vert2_id = edges[edge1_id]
                    other_vert_id = vert1_id if merged_verts[vert2_id] is merged_vert else vert2_id
                    other_merged_vert = merged_verts[other_vert_id]

                    if other_merged_vert in edges_by_merged_vert:

                        edge2_id = edges_by_merged_vert.pop(other_merged_vert)
                        merged_edge.append(edge2_id)
                        merged_edges[edge2_id] = merged_edge
                        seam_edges_to_remove.update(merged_edge)
                        edge1_selected = edge1_id in selected_edge_ids
                        edge2_selected = edge2_id in selected_edge_ids

                        if edge1_selected != edge2_selected:
                            tmp_merged_edge.append(edge1_id if edge2_selected else edge2_id)

                    else:

                        edges_by_merged_vert[other_merged_vert] = edge1_id

        self.remove_seam_edges(seam_edges_to_remove)
        selection_change = False

        if tmp_merged_vert[:]:
            vert_id = tmp_merged_vert.get_id()
            orig_merged_vert = merged_verts[vert_id]
            merged_verts[vert_id] = tmp_merged_vert
            self.update_selection("vert", [tmp_merged_vert], [], False)
            merged_verts[vert_id] = orig_merged_vert
            self._update_verts_to_transform("vert")
            selection_change = True

        if tmp_merged_edge[:]:
            edge_id = tmp_merged_edge.get_id()
            orig_merged_edge = merged_edges[edge_id]
            merged_edges[edge_id] = tmp_merged_edge
            self.update_selection("edge", [tmp_merged_edge], [], False)
            merged_edges[edge_id] = orig_merged_edge
            self._update_verts_to_transform("edge")
            selection_change = True

        self.update_vertex_positions(verts_to_move)
        UVMgr.do("update_active_selection")

        if update_polys_to_transf:
            self._update_verts_to_transform("poly")

        return True, selection_change


class EdgeEditManager(BaseObject):

    def setup(self):

        Mgr.add_interface_updater("uv_window", "edge_split", self.__split_edges)
        Mgr.add_interface_updater("uv_window", "edge_stitch", self.__stitch_edges)

    def __split_edges(self):

        selection = self._selections[self._uv_set_id]["edge"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.split_edges()

    def __stitch_edges(self):

        selection = self._selections[self._uv_set_id]["edge"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.stitch_edges()
