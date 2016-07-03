from ....base import *


class PolygonDetachBase(BaseObject):

    def detach_polygons(self):

        selection_ids = self._selected_subobj_ids
        selected_poly_ids = selection_ids["poly"]

        if not selected_poly_ids:
            return False

        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        polys = self._subobjs["poly"]
        verts_to_separate = set()
        edges_to_split = []
        selected_polys = (polys[i] for i in selected_poly_ids)

        change = False

        for poly in selected_polys:

            for edge_id in poly.get_edge_ids():

                merged_edge = merged_edges[edge_id]

                if len(merged_edge) == 1:

                    # Even a border edge might still touch a non-selected poly in one of
                    # its vertices.

                    edge = edges[edge_id]

                    for edge_vert_id in edge:

                        merged_vert = merged_verts[edge_vert_id]

                        for vert_id in merged_vert:

                            vert = verts[vert_id]

                            if vert.get_polygon_id() not in selected_poly_ids:
                                verts_to_separate.add(merged_vert)
                                change = True
                                break

                    continue

                edge1_id, edge2_id = merged_edge
                other_edge_id = edge1_id if edge_id == edge2_id else edge2_id
                other_edge = edges[other_edge_id]

                if other_edge.get_polygon_id() in selected_poly_ids:
                    continue

                edges_to_split.append(edge_id)

                change = True

        if change:

            new_merged_verts = {}
            merged_verts_to_update = set()
            selected_vert_ids = selection_ids["vert"]
            selected_edge_ids = selection_ids["edge"]
            update_verts_to_transf = False
            update_edges_to_transf = False

            def split_merged_vertex(old_merged_vert, new_merged_vert):

                for vert_id in old_merged_vert[:]:

                    vert = verts[vert_id]

                    if vert.get_polygon_id() in selected_poly_ids:
                        old_merged_vert.remove(vert_id)
                        new_merged_vert.append(vert_id)
                        merged_verts[vert_id] = new_merged_vert

            for edge_id in edges_to_split:

                merged_edge = merged_edges[edge_id]
                new_merged_edge = Mgr.do("create_merged_edge", self, edge_id)
                merged_edge.remove(edge_id)
                merged_edges[edge_id] = new_merged_edge

                if edge_id in selected_edge_ids:
                    update_edges_to_transf = True

                edge = edges[edge_id]

                for vert_id in edge:

                    merged_vert = merged_verts[vert_id]

                    if merged_vert in new_merged_verts:
                        new_merged_vert = new_merged_verts[merged_vert]
                    else:
                        new_merged_vert = Mgr.do("create_merged_vert", self)
                        new_merged_verts[merged_vert] = new_merged_vert

                    merged_vert.remove(vert_id)
                    new_merged_vert.append(vert_id)
                    merged_verts[vert_id] = new_merged_vert
                    merged_verts_to_update.add(merged_vert)
                    merged_verts_to_update.add(new_merged_vert)
                    split_merged_vertex(merged_vert, new_merged_vert)

                    if vert_id in selected_vert_ids:
                        update_verts_to_transf = True

            for merged_vert in verts_to_separate:

                if merged_vert not in new_merged_verts:

                    new_merged_vert = Mgr.do("create_merged_vert", self)
                    new_merged_verts[merged_vert] = new_merged_vert
                    merged_verts_to_update.add(merged_vert)
                    merged_verts_to_update.add(new_merged_vert)
                    split_merged_vertex(merged_vert, new_merged_vert)

                    if merged_vert[0] in selected_vert_ids:
                        update_verts_to_transf = True

            self._update_vertex_normals(merged_verts_to_update)

            if update_verts_to_transf:
                self._update_verts_to_transform("vert")

            if update_edges_to_transf:
                self._update_verts_to_transform("edge")

            self._update_verts_to_transform("poly")

        return change


class PolygonDetachManager(BaseObject):

    def __init__(self):

        Mgr.add_app_updater("poly_detach", self.__detach_polygons)

    def __detach_polygons(self):

        selection = Mgr.get("selection", "top")
        changed_objs = {}

        for model in selection:

            geom_data_obj = model.get_geom_object().get_geom_data_object()

            if geom_data_obj.detach_polygons():
                changed_objs[model.get_id()] = geom_data_obj

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.iteritems():
            obj_data[obj_id] = geom_data_obj.get_data_to_store("prop_change", "subobj_merge")

        event_descr = "Detach polygon selection"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)
