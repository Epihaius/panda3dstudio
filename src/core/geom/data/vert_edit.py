from ...base import *


class VertexEditBase(BaseObject):

    def break_vertices(self):

        selected_vert_ids = self._selected_subobj_ids["vert"]

        if not selected_vert_ids:
            return

        verts = self._subobjs["vert"]
        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts_to_break = set(merged_verts[v_id] for v_id in selected_vert_ids)
        edges_to_split = set()

        change = False
        update_edges_to_transf = False
        update_polys_to_transf = False
        edge_verts_to_transf = self._verts_to_transf["edge"]
        poly_verts_to_transf = self._verts_to_transf["poly"]
        merged_verts_to_resmooth = set()

        for merged_vert in verts_to_break:

            if len(merged_vert) == 1:
                continue

            for vert_id in merged_vert[1:]:

                merged_vert.remove(vert_id)
                new_merged_vert = Mgr.do("create_merged_vert", self, vert_id)
                merged_verts[vert_id] = new_merged_vert
                merged_verts_to_resmooth.add(new_merged_vert)

                for edge_id in verts[vert_id].get_edge_ids():
                    edges_to_split.add(merged_edges[edge_id])

            change = True
            merged_verts_to_resmooth.add(merged_vert)

            if merged_vert in edge_verts_to_transf:
                update_edges_to_transf = True
            if merged_vert in poly_verts_to_transf:
                update_polys_to_transf = True

        for merged_edge in edges_to_split:

            if len(merged_edge) == 1:
                continue

            for edge_id in merged_edge[1:]:
                merged_edge.remove(edge_id)
                new_merged_edge = Mgr.do("create_merged_edge", self, edge_id)
                merged_edges[edge_id] = new_merged_edge

        if not change:
            return

        progress_steps = len(merged_verts_to_resmooth) // 20

        yield True, progress_steps

        Mgr.do("update_active_selection")

        for step in self._update_vertex_normals(merged_verts_to_resmooth):
            yield

        self._update_verts_to_transform("vert")

        if update_edges_to_transf:
            self._update_verts_to_transform("edge")
        if update_polys_to_transf:
            self._update_verts_to_transform("poly")


class VertexEditManager(BaseObject):

    def __init__(self):

        Mgr.add_app_updater("vert_break", self.__do_break_vertices)

    def __break_vertices(self):

        selection = Mgr.get("selection", "top")
        changed_objs = {}
        progress_steps = 0
        handlers = []

        for model in selection:

            geom_data_obj = model.get_geom_object().get_geom_data_object()
            handler = geom_data_obj.break_vertices()
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

        event_descr = "Break vertex selection"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        yield False

    def __do_break_vertices(self):

        process = self.__break_vertices()

        if process.next():
            descr = "Updating geometry..."
            Mgr.do_gradually(process, "vert_break", descr)


MainObjects.add_class(VertexEditManager)
