from ..base import *
from .vert import MergedVertex
from .edge import MergedEdge


class PolygonEditBase(BaseObject):

    def detach_polygons(self):

        selection_ids = self._selected_subobj_ids
        selected_vert_ids = selection_ids["vert"]
        selected_edge_ids = selection_ids["edge"]
        selected_poly_ids = selection_ids["poly"]

        if not selected_poly_ids:
            return False

        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        polys = self._subobjs["poly"]
        border_verts = set()
        border_edges = []
        seam_edge_ids = []
        update_edges_to_transf = False
        update_verts_to_transf = False
        selected_polys = (polys[i] for i in selected_poly_ids)

        change = False

        for poly in selected_polys:

            for edge_id in poly.get_edge_ids():

                merged_edge = merged_edges[edge_id]

                if merged_edge in border_edges:
                    border_edges.remove(merged_edge)
                else:
                    border_edges.append(merged_edge)

        for merged_edge in border_edges:

            edge_ids = merged_edge[:]

            for edge_id in edge_ids:

                edge = edges[edge_id]

                for vert_id in edge:
                    border_verts.add(merged_verts[vert_id])

                if len(merged_edge) == 1:
                    continue

                if edge.get_polygon_id() in selected_poly_ids:
                    seam_edge_ids.extend(edge_ids)
                    merged_edge.remove(edge_id)
                    new_merged_edge = MergedEdge(self)
                    new_merged_edge.append(edge_id)
                    merged_edges[edge_id] = new_merged_edge
                    change = True

        for merged_vert in border_verts:

            remaining_vert_ids = [v_id for v_id in merged_vert
                                  if verts[v_id].get_polygon_id() not in selected_poly_ids]

            if not remaining_vert_ids:
                continue

            if merged_vert.get_id() in selected_vert_ids:
                update_verts_to_transf = True

            for vert_id in merged_vert:

                edge_ids = verts[vert_id].get_edge_ids()

                if edge_ids[0] in selected_edge_ids or edge_ids[1] in selected_edge_ids:
                    update_edges_to_transf = True

            new_merged_vert = MergedVertex(self)

            for vert_id in [v_id for v_id in merged_vert if v_id not in remaining_vert_ids]:
                merged_vert.remove(vert_id)
                new_merged_vert.append(vert_id)
                merged_verts[vert_id] = new_merged_vert

            change = True

        if change:

            if update_verts_to_transf:
                self._update_verts_to_transform("vert")

            if update_edges_to_transf:
                self._update_verts_to_transform("edge")

            self._update_verts_to_transform("poly")

            if seam_edge_ids:

                self.add_seam_edges(seam_edge_ids)

                seam_edges_to_select = set(seam_edge_ids) & set(selected_edge_ids)
                seam_edges_to_unselect = set(seam_edge_ids) - set(selected_edge_ids)

                if seam_edges_to_select:
                    color = UVMgr.get("uv_selection_colors")["seam"]["selected"]
                    self.update_seam_selection(seam_edges_to_select, color)
                    self._geom_data_obj.update_tex_seam_selection(seam_edges_to_select, color)

                if seam_edges_to_unselect:
                    color = UVMgr.get("uv_selection_colors")["seam"]["unselected"]
                    self.update_seam_selection(seam_edges_to_unselect, color)
                    self._geom_data_obj.update_tex_seam_selection(seam_edges_to_unselect, color)

        return change


class PolygonEditManager(BaseObject):

    def setup(self):

        Mgr.add_interface_updater("uv_window", "poly_detach", self.__detach_polygons)

    def __detach_polygons(self):

        selection = self._selections[self._uv_set_id]["poly"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.detach_polygons()
