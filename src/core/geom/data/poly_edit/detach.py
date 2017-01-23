from ....base import *


class PolygonDetachBase(BaseObject):

    def detach_polygons(self):

        selection_ids = self._selected_subobj_ids
        selected_vert_ids = selection_ids["vert"]
        selected_edge_ids = selection_ids["edge"]
        selected_poly_ids = selection_ids["poly"]

        if not selected_poly_ids:
            return

        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        polys = self._subobjs["poly"]
        border_verts = set()
        border_edges = []
        update_edges_to_transf = False
        update_verts_to_transf = False
        merged_verts_to_resmooth = set()
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
                    merged_edge.remove(edge_id)
                    new_merged_edge = Mgr.do("create_merged_edge", self, edge_id)
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

            new_merged_vert = Mgr.do("create_merged_vert", self)
            merged_verts_to_resmooth.add(merged_vert)
            merged_verts_to_resmooth.add(new_merged_vert)

            for vert_id in [v_id for v_id in merged_vert if v_id not in remaining_vert_ids]:
                merged_vert.remove(vert_id)
                new_merged_vert.append(vert_id)
                merged_verts[vert_id] = new_merged_vert

            change = True

        if not change:
            return

        progress_steps = len(merged_verts_to_resmooth) // 20

        yield True, progress_steps

        for step in self._update_vertex_normals(merged_verts_to_resmooth):
            yield

        if update_verts_to_transf:
            self._update_verts_to_transform("vert")

        if update_edges_to_transf:
            self._update_verts_to_transform("edge")

        self._update_verts_to_transform("poly")


class PolygonDetachManager(BaseObject):

    def __init__(self):

        Mgr.add_app_updater("poly_detach", self.__do_detach_polygons)

    def __detach_polygons(self):

        selection = Mgr.get("selection", "top")
        changed_objs = {}
        progress_steps = 0
        handlers = []

        for model in selection:

            geom_data_obj = model.get_geom_object().get_geom_data_object()
            handler = geom_data_obj.detach_polygons()
            change = False
            steps = 0

            for result in handler:
                if result:
                    change, steps = result
                    handlers.append(handler)
                    break

            if change:
                changed_objs[model.get_id()] = geom_data_obj
                progress_steps += steps

        if not changed_objs:
            yield False

        gradual = progress_steps > 20

        if gradual:
            Mgr.show_screenshot()
            GlobalData["progress_steps"] = progress_steps

        for handler in handlers:
            for step in handler:
                if gradual:
                    yield True

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.iteritems():
            obj_data[obj_id] = geom_data_obj.get_data_to_store("prop_change", "subobj_merge")

        event_descr = "Detach polygon selection"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        yield False

    def __do_detach_polygons(self):

        process = self.__detach_polygons()

        if process.next():
            descr = "Updating geometry..."
            Mgr.do_gradually(process, "poly_detach", descr)
