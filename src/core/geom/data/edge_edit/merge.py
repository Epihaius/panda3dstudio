from ....base import *


class EdgeMergeBase(BaseObject):

    def merge_edges(self, src_border_edge, dest_border_edge):

        merged_verts = self._merged_verts
        merged_edges = self._merged_edges
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        selection_ids = self._selected_subobj_ids
        selected_vert_ids = selection_ids["vert"]
        selected_edge_ids = selection_ids["edge"]

        # when edges are selected via polygon, the IDs of selected polys are
        # currently backed up
        if "poly" in self._sel_subobj_ids_backup:

            selected_poly_ids = self._sel_subobj_ids_backup["poly"][:]

            # the current selection (the picked helper poly) may not be made empty,
            # or the call to self.clear_selection() will have no effect and leave
            # the helper poly visible
            if selected_poly_ids:
                self._selected_subobj_ids["poly"] = selected_poly_ids

        else:

            selected_poly_ids = selection_ids["poly"]

        border_segments = ([], [])
        segment_is_border = None

        def get_next_border_edge(edge_id, index):

            vert_id = edges[edge_id][index]
            merged_vert = merged_verts[vert_id]

            for vert_id in merged_vert:

                vert = verts[vert_id]
                merged_edge = merged_edges[vert.get_edge_ids()[index]]

                if len(merged_edge) == 1:
                    return merged_edge

        edge_id = src_border_edge.get_id()

        if edge_id in selected_edge_ids:

            for index in (0, 1):

                src_edge = src_border_edge
                border_segment = border_segments[index]

                while True:

                    edge_id = src_edge[0]
                    src_edge = get_next_border_edge(edge_id, index)

                    if src_edge is src_border_edge:
                        segment_is_border = index

                    if (src_edge is src_border_edge
                            or src_edge.get_id() not in selected_edge_ids):
                        break

                    if src_edge is dest_border_edge:
                        return False, False

                    border_segment.append(src_edge)

        verts_to_merge = {}
        edges_to_merge = {src_border_edge: dest_border_edge}
        src_end_edges = [src_border_edge, src_border_edge]
        dest_end_edges = [dest_border_edge, dest_border_edge]
        src_end_edge = None

        for index in (0, 1):

            dest_edge = dest_border_edge
            border_segment = border_segments[1 - index]

            while border_segment:

                src_edge = border_segment.pop(0)
                edge_id = dest_edge[0]
                dest_edge = get_next_border_edge(edge_id, index)

                if dest_edge is dest_border_edge:
                    border_segments = ([], [])
                    src_end_edges = [src_border_edge, src_border_edge]
                    dest_end_edges = [dest_border_edge, dest_border_edge]
                    break

                if src_edge is src_end_edge:
                    del edges_to_merge[src_edge]
                    border_segments = ([], [])
                    break

                if not border_segment and segment_is_border == index:
                    src_end_edge = src_edge
                    border_segment.append(src_edge)

                if not (dest_edge is src_edge or dest_edge in edges_to_merge):

                    edges_to_merge[src_edge] = dest_edge

                    if segment_is_border is None:
                        src_end_edges[index] = src_edge
                        dest_end_edges[index] = dest_edge

        tmp_merged_vert = Mgr.do("create_merged_vert", self)
        tmp_merged_edge = Mgr.do("create_merged_edge", self)

        def validate_vertex_merge(src_vert, dest_vert):

            if src_vert is dest_vert:
                return True

            return set(src_vert.get_polygon_ids()).isdisjoint(dest_vert.get_polygon_ids())

        for src_edge, dest_edge in edges_to_merge.iteritems():

            src_vert1_id, src_vert2_id = edges[src_edge[0]]
            src_vert1 = merged_verts[src_vert1_id]
            src_vert2 = merged_verts[src_vert2_id]
            dest_vert2_id, dest_vert1_id = edges[dest_edge[0]]
            dest_vert1 = merged_verts[dest_vert1_id]
            dest_vert2 = merged_verts[dest_vert2_id]

            # if 2 merged verts to be combined are associated with the same polygon,
            # the currently processed src_edge and dest_edge will not be merged
            if not (validate_vertex_merge(src_vert1, dest_vert1)
                    and validate_vertex_merge(src_vert2, dest_vert2)):
                continue

            if src_vert1 is not dest_vert1 and src_vert1 not in verts_to_merge:
                verts_to_merge[src_vert1] = dest_vert1

            if src_vert2 is not dest_vert2 and src_vert2 not in verts_to_merge:
                verts_to_merge[src_vert2] = dest_vert2

            src_edge_id = src_edge.get_id()
            dest_edge_id = dest_edge.get_id()
            dest_edge.append(src_edge_id)
            merged_edges[src_edge_id] = dest_edge

            src_edge_selected = src_edge_id in selected_edge_ids
            dest_edge_selected = dest_edge_id in selected_edge_ids

            if src_edge_selected != dest_edge_selected:
                tmp_merged_edge.append(dest_edge_id if src_edge_selected else src_edge_id)

        if not verts_to_merge:
            return False, False

        xformed_verts = self._transformed_verts
        dest_verts = set()
        vert_ids = set()
        update_polys_to_transf = False

        for src_vert, dest_vert in verts_to_merge.iteritems():

            src_vert_selected = src_vert.get_id() in selected_vert_ids
            dest_vert_selected = dest_vert.get_id() in selected_vert_ids

            if src_vert_selected != dest_vert_selected:
                tmp_merged_vert.extend(dest_vert if src_vert_selected else src_vert)

            pos = dest_vert.get_pos()
            src_vert.set_pos(pos)
            dest_vert.extend(src_vert)
            dest_verts.add(dest_vert)
            xformed_verts.add(src_vert)
            vert_ids.update(src_vert)

            for vert_id in src_vert:
                merged_verts[vert_id] = dest_vert

            if not update_polys_to_transf:
                for vert_id in dest_vert:
                    if verts[vert_id].get_polygon_id() in selected_poly_ids:
                        update_polys_to_transf = True
                        break

        # If any border edges exist that are connected to the determined source and
        # destination segments and are themselves connected, they need to be merged also.
        for index in (0, 1):

            src_edge = src_end_edges[index]
            dest_edge = dest_end_edges[index]
            edge_id = src_edge[0]
            next_src_edge = get_next_border_edge(edge_id, 1 - index)

            if not next_src_edge or next_src_edge is dest_edge:
                continue

            next_src_edge_id = next_src_edge[0]
            vert_id = edges[next_src_edge_id][1 - index]
            merged_vert = merged_verts[vert_id]
            edge_id = dest_edge[0]
            next_dest_edge = get_next_border_edge(edge_id, index)

            if not next_dest_edge or next_src_edge is dest_edge:
                continue

            next_dest_edge_id = next_dest_edge[0]
            vert_id = edges[next_dest_edge_id][index]

            if merged_verts[vert_id] is merged_vert:

                next_dest_edge.append(next_src_edge_id)
                merged_edges[next_src_edge_id] = next_dest_edge

                src_edge_selected = next_src_edge_id in selected_edge_ids
                dest_edge_selected = next_dest_edge_id in selected_edge_ids

                if src_edge_selected != dest_edge_selected:
                    tmp_merged_edge.append(next_dest_edge_id if src_edge_selected else next_src_edge_id)

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

        if self.update_normal_sharing(dest_verts, from_smoothing_groups=True):
            selection_change = True

        self.update_vertex_positions(vert_ids)

        if update_polys_to_transf:
            self._update_verts_to_transform("poly")

        return True, selection_change


class EdgeMergeManager(BaseObject):

    def __init__(self):

        add_state = Mgr.add_state
        add_state("edge_merge_mode", -10, self.__enter_merge_mode, self.__exit_merge_mode)
        add_state("edge_merge", -11)

        cancel_merge = lambda: self._finalize_merge(cancel=True)
        exit_mode = lambda: Mgr.exit_state("edge_merge_mode")

        bind = Mgr.bind_state
        bind("edge_merge_mode", "merge edges -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("edge_merge_mode", "merge edges -> select", "escape", exit_mode)
        bind("edge_merge_mode", "exit edge merge mode", "mouse3-up", exit_mode)
        bind("edge_merge_mode", "merge edges", "mouse1", self._init_merge)
        bind("edge_merge", "quit edge merge", "escape", cancel_merge)
        bind("edge_merge", "cancel edge merge", "mouse3-up", cancel_merge)
        bind("edge_merge", "abort edge merge", "focus_loss", cancel_merge)
        bind("edge_merge", "finalize edge merge", "mouse1-up", self._finalize_merge)
        bind("edge_merge", "merge edges -> pick edge via poly",
             "mouse1", self._start_dest_edge_picking_via_poly)

        status_data = GlobalData["status_data"]
        mode_text = "Merge edges"
        info_text = "LMB-drag over a border edge and release LMB over" \
                    " other border edge to merge; RMB or <Escape> to end"
        status_data["edge_merge_mode"] = {"mode": mode_text, "info": info_text}

    def __enter_merge_mode(self, prev_state_id, is_active):

        if prev_state_id == "edge_merge":
            return

        if GlobalData["active_transform_type"]:
            GlobalData["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")

        self._mode_id = "merge"
        Mgr.add_task(self._update_cursor, "update_mode_cursor")
        Mgr.update_app("status", ["edge_merge_mode"])

    def __exit_merge_mode(self, next_state_id, is_active):

        if next_state_id == "edge_merge":
            return

        Mgr.remove_task("update_mode_cursor")
        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self._update_cursor()
                                        # is called
        Mgr.set_cursor("main")

        if next_state_id != "edge_picking_via_poly":
            self._mode_id = ""

    def _init_merge(self, picked_edge=None):

        if picked_edge:

            edge = picked_edge

        else:

            if not self._pixel_under_mouse:
                return

            r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
            color_id = r << 16 | g << 8 | b
            pickable_type = PickableTypes.get(a)

            if pickable_type == "poly":

                self._picked_poly = Mgr.get("poly", color_id)
                merged_edges = self._picked_poly.get_geom_data_object().get_merged_edges()

                for edge_id in self._picked_poly.get_edge_ids():
                    if len(merged_edges[edge_id]) == 1:
                        break
                else:
                    return

                Mgr.enter_state("edge_picking_via_poly")

                return

            picked_obj = Mgr.get("edge", color_id)
            edge = picked_obj.get_merged_edge() if picked_obj else None

        if not edge or len(edge) > 1:
            return

        model = edge.get_toplevel_object()

        for obj in Mgr.get("selection_top"):
            if obj is not model:
                obj.get_geom_object().get_geom_data_object().set_pickable(False)

        self._src_border_edge = edge
        self._picking_dest_edge = True
        pos = edge.get_center_pos(self.world)
        Mgr.do("start_drawing_rubber_band", pos)
        Mgr.do("enable_view_gizmo", False)
        Mgr.enter_state("edge_merge")
        Mgr.set_cursor("main")

    def _finalize_merge(self, cancel=False, picked_edge=None):

        if not cancel:
            self.__merge_edges(picked_edge)

        src_border_edge = self._src_border_edge

        if src_border_edge:

            model = src_border_edge.get_toplevel_object()

            for obj in Mgr.get("selection_top"):
                if obj is not model:
                    obj.get_geom_object().get_geom_data_object().set_pickable()

        Mgr.do("end_drawing_rubber_band")
        self._picking_dest_edge = False
        Mgr.enter_state("edge_merge_mode")
        Mgr.set_cursor("main" if self._pixel_under_mouse == VBase4() else "select")
        Mgr.do("enable_view_gizmo")

        self._src_border_edge = None

    def __merge_edges(self, picked_edge=None):

        src_border_edge = self._src_border_edge

        if not src_border_edge:
            return

        model = src_border_edge.get_toplevel_object()

        if picked_edge:
            dest_border_edge = picked_edge
        else:
            r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
            color_id = r << 16 | g << 8 | b
            picked_obj = Mgr.get("edge", color_id)
            dest_border_edge = picked_obj.get_merged_edge() if picked_obj else None

        if not dest_border_edge or dest_border_edge is src_border_edge or len(dest_border_edge) > 1:
            return

        geom_data_obj = model.get_geom_object().get_geom_data_object()
        change, selection_change = geom_data_obj.merge_edges(src_border_edge, dest_border_edge)

        if not change:
            return

        Mgr.do("update_active_selection")
        Mgr.do("update_history_time")

        data = geom_data_obj.get_data_to_store("prop_change", "subobj_merge")
        data.update(geom_data_obj.get_data_to_store("prop_change", "subobj_transform", "check"))

        if selection_change:
            data.update(geom_data_obj.get_property_to_store("subobj_selection"))

        obj_data = {model.get_id(): data}

        event_descr = "Merge edges"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)
