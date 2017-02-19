from ....base import *


class PolygonFlipBase(BaseObject):

    def flip_polygon_normals(self, selected_only=True):

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]
        ordered_polys = self._ordered_polys
        sel_data = self._poly_selection_data
        data_selected = sel_data["selected"]
        data_unselected = sel_data["unselected"]
        merged_verts = self._merged_verts
        merged_verts_to_resmooth = set()
        selected_poly_ids = self._selected_subobj_ids["poly"]
        poly_ids = iter(selected_poly_ids) if selected_only else polys.iterkeys()

        if not poly_ids:
            return

        vert_indices = {}
        vert_indices_selected = {}
        vert_indices_unselected = {}

        for poly_id in poly_ids:

            poly = polys[poly_id]
            rows = data_selected if poly_id in selected_poly_ids else data_unselected
            start = rows.index(poly[0])
            new_indices = []
            indices = vert_indices_selected if poly_id in selected_poly_ids else vert_indices_unselected
            indices[start] = new_indices
            vert_indices[ordered_polys.index(poly)] = new_indices

            new_tri_data = []

            for i, tri_verts in enumerate(poly):
                new_tri_verts = tri_verts[::-1]
                new_tri_data.append(new_tri_verts)
                rows[start + i] = new_tri_verts
                new_indices.append([verts[vert_id].get_row_index() for vert_id in new_tri_verts])

            poly.set_triangle_data(new_tri_data)
            poly.update_normal()
            merged_verts_to_resmooth.update(merged_verts[v_id] for v_id in poly.get_vertex_ids())

        progress_steps = len(merged_verts_to_resmooth) // 20

        yield True, progress_steps

        # Update geometry structures

        geoms = self._geoms
        poly_selected_geom = geoms["poly"]["selected"].node().modify_geom(0)
        prim_selected = GeomTriangles(Geom.UH_static)

        for i in sorted(vert_indices_selected):
            for indices in vert_indices_selected[i]:
                prim_selected.add_vertices(*indices)

        poly_selected_geom.set_primitive(0, prim_selected)

        toplvl_prim = GeomTriangles(Geom.UH_static)

        if selected_only:

            for i, poly in enumerate(ordered_polys):

                if i not in vert_indices:

                    old_indices = []
                    vert_indices[i] = old_indices

                    for tri_verts in poly:
                        old_indices.append([verts[vert_id].get_row_index() for vert_id in tri_verts])

        else:

            poly_unselected_geom = geoms["poly"]["unselected"].node().modify_geom(0)
            prim_unselected = GeomTriangles(Geom.UH_static)

            for i in sorted(vert_indices_unselected):
                for indices in vert_indices_unselected[i]:
                    prim_unselected.add_vertices(*indices)

            poly_unselected_geom.set_primitive(0, prim_unselected)

        for i in xrange(len(ordered_polys)):
            for indices in vert_indices[i]:
                toplvl_prim.add_vertices(*indices)

        toplvl_geom = self._toplvl_node.modify_geom(0)
        toplvl_geom.set_primitive(0, toplvl_prim)

        self._tri_change_all = not selected_only

        for step in self._update_vertex_normals(merged_verts_to_resmooth):
            yield


class PolygonFlipManager(BaseObject):

    def __init__(self):

        Mgr.add_app_updater("poly_flip", self.__do_flip_poly_normals)

    def __flip_poly_normals(self, selected_only=True):

        selection = Mgr.get("selection", "top")
        changed_objs = {}
        progress_steps = 0
        handlers = []

        for model in selection:

            geom_data_obj = model.get_geom_object().get_geom_data_object()
            handler = geom_data_obj.flip_polygon_normals(selected_only)
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
            obj_data[obj_id] = geom_data_obj.get_data_to_store("prop_change", "poly_tris")

        event_descr = "Flip polygon normals"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        yield False

    def __do_flip_poly_normals(self, selected_only=True):

        process = self.__flip_poly_normals(selected_only)

        if process.next():
            descr = "Updating geometry..."
            Mgr.do_gradually(process, "poly_normal_flip", descr)
