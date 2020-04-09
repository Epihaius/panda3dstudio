from ....base import *


class EdgeBridgeMixin:
    """ EdgeEditMixin class mix-in """

    def __create_bridge_polygon(self, ordered_verts):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]
        ordered_polys = self.ordered_polys
        merged_verts = self.merged_verts
        merged_edges = self.merged_edges

        poly_verts = []
        poly_edges = []
        poly_tris = []

        merged_vert1, merged_vert2, merged_vert3, merged_vert4 = ordered_verts

        # Create the vertices

        def get_new_vertex(merged_vert):

            if len(merged_vert) == 1:

                vert_id = merged_vert.id
                vert = verts[vert_id]

                if not vert.edge_ids:
                    # this vertex was newly created to allow segmentation of bridge
                    # polygons; it can become part of the new bridge polygon
                    return vert, vert_id

            return None, None

        pos1 = merged_vert1.get_pos()
        vert1, vert1_id = get_new_vertex(merged_vert1)

        if not vert1:
            vert1 = Mgr.do("create_vert", self, pos1)
            vert1_id = vert1.id
            verts[vert1_id] = vert1
            merged_vert1.append(vert1_id)
            merged_verts[vert1_id] = merged_vert1

        poly_verts.append(vert1)

        if merged_vert2 is merged_vert1:

            pos2 = pos1
            vert2 = None

        else:

            pos2 = merged_vert2.get_pos()
            vert2, vert2_id = get_new_vertex(merged_vert2)

            if not vert2:
                vert2 = Mgr.do("create_vert", self, pos2)
                vert2_id = vert2.id
                verts[vert2_id] = vert2
                merged_vert2.append(vert2_id)
                merged_verts[vert2_id] = merged_vert2

            poly_verts.append(vert2)

        pos3 = merged_vert3.get_pos()
        vert3, vert3_id = get_new_vertex(merged_vert3)

        if not vert3:
            vert3 = Mgr.do("create_vert", self, pos3)
            vert3_id = vert3.id
            verts[vert3_id] = vert3
            merged_vert3.append(vert3_id)
            merged_verts[vert3_id] = merged_vert3

        poly_verts.append(vert3)

        if merged_vert4 is merged_vert3:

            pos4 = pos3
            vert4 = None

        else:

            pos4 = merged_vert4.get_pos()
            vert4, vert4_id = get_new_vertex(merged_vert4)

            if not vert4:
                vert4 = Mgr.do("create_vert", self, pos4)
                vert4_id = vert4.id
                verts[vert4_id] = vert4
                merged_vert4.append(vert4_id)
                merged_verts[vert4_id] = merged_vert4

            poly_verts.append(vert4)

        # Define triangulation

        poly_tris.append(tuple(vert.id for vert in poly_verts[:3]))

        if len(poly_verts) == 4:
            tri_verts = poly_verts[:]
            del tri_verts[1]
            poly_tris.append(tuple(vert.id for vert in tri_verts))

        # Create the edges

        if vert2:
            edge1 = Mgr.do("create_edge", self, (vert1_id, vert2_id))
            edge1_id = edge1.id
            vert2.add_edge_id(edge1_id)
            edges[edge1_id] = edge1
            poly_edges.append(edge1)

        edge2 = Mgr.do("create_edge", self, (vert2_id if vert2 else vert1_id, vert3_id))
        edge2_id = edge2.id

        if vert2:
            vert2.add_edge_id(edge2_id)

        vert3.add_edge_id(edge2_id)
        edges[edge2_id] = edge2
        poly_edges.append(edge2)

        if vert4:
            edge3 = Mgr.do("create_edge", self, (vert3_id, vert4_id))
            edge3_id = edge3.id
            vert3.add_edge_id(edge3_id)
            vert4.add_edge_id(edge3_id)
            edges[edge3_id] = edge3
            poly_edges.append(edge3)

        edge4 = Mgr.do("create_edge", self, (vert4_id if vert4 else vert3_id, vert1_id))
        edge4_id = edge4.id

        if vert4:
            vert4.add_edge_id(edge4_id)
        else:
            vert3.add_edge_id(edge4_id)

        vert1.add_edge_id(edge4_id)

        if vert2:
            vert1.add_edge_id(edge1_id)
        else:
            vert1.add_edge_id(edge2_id)

        edges[edge4_id] = edge4
        poly_edges.append(edge4)

        def merge_edge(edge):

            border_edge_id = edge.id
            merged_vert1, merged_vert2 = [merged_verts[v_id] for v_id in edge]

            for vert_id in merged_vert1:

                vert = verts[vert_id]

                for edge_id in vert.edge_ids:

                    if edge_id not in merged_edges:
                        continue

                    merged_edge = merged_edges[edge_id]

                    if len(merged_edge) > 1:
                        continue

                    vert1_id, vert2_id = edges[edge_id]
                    other_vert_id = vert1_id if merged_verts[vert2_id] is merged_vert1 else vert2_id

                    if merged_verts[other_vert_id] is merged_vert2:
                        merged_edge.append(border_edge_id)
                        merged_edges[border_edge_id] = merged_edge
                        break

                else:

                    continue

                break

            else:

                merged_edge = Mgr.do("create_merged_edge", self, border_edge_id)
                merged_edges[border_edge_id] = merged_edge

        for edge in poly_edges:
            merge_edge(edge)

        poly = Mgr.do("create_poly", self, poly_tris, poly_edges, poly_verts)
        ordered_polys.append(poly)
        polys[poly.id] = poly
        poly.update_center_pos()
        poly.update_normal()
        normal = poly.normal.normalized()

        for vert in poly_verts:
            vert.normal = normal

        return poly

    def bridge_edges(self, src_border_edge, dest_border_edge):

        merged_verts = self.merged_verts
        merged_edges = self.merged_edges
        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        selection_ids = self._selected_subobj_ids
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
                merged_edge = merged_edges[vert.edge_ids[index]]

                if len(merged_edge) == 1:
                    return merged_edge

        edge_id = src_border_edge.id

        if edge_id in selected_edge_ids:

            for index in (0, 1):

                src_edge = src_border_edge
                border_segment = border_segments[index]

                while True:

                    edge_id = src_edge[0]
                    src_edge = get_next_border_edge(edge_id, index)

                    if src_edge is src_border_edge:
                        segment_is_border = index

                    if src_edge is src_border_edge or src_edge.id not in selected_edge_ids:
                        break

                    if src_edge is dest_border_edge:
                        return False

                    border_segment.append(src_edge)

        verts_to_merge = {}
        edges_to_merge = {src_border_edge: dest_border_edge}
        src_end_edges = [src_border_edge, src_border_edge]
        dest_end_edges = [dest_border_edge, dest_border_edge]

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

                if not (dest_edge is src_edge or dest_edge in edges_to_merge):

                    edges_to_merge[src_edge] = dest_edge

                    if segment_is_border is None:
                        src_end_edges[index] = src_edge
                        dest_end_edges[index] = dest_edge

        new_polys = []

        update_polys_to_transf = False

        bridge_segments = GD["subobj_edit_options"]["edge_bridge_segments"]

        if bridge_segments > 1:

            seg_verts = {}

            def add_segment_vertices(src_vert, dest_vert):

                if src_vert is dest_vert:

                    seg_verts[src_vert] = [src_vert] * (bridge_segments + 1)

                else:

                    seg_verts[src_vert] = new_seg_verts = [src_vert]
                    src_pos = src_vert.get_pos()
                    seg_vec = (dest_vert.get_pos() - src_pos) / bridge_segments

                    for i in range(bridge_segments - 1):
                        pos = src_pos + seg_vec * (i + 1)
                        new_vert = Mgr.do("create_vert", self, pos)
                        vert_id = new_vert.id
                        verts[vert_id] = new_vert
                        new_merged_vert = Mgr.do("create_merged_vert", self, vert_id)
                        merged_verts[vert_id] = new_merged_vert
                        new_seg_verts.append(new_merged_vert)

                    new_seg_verts.append(dest_vert)

        def add_new_polys(vert1, vert2, vert3, vert4):

            # define the merged vertices of the bridging polygon(s) in winding order,
            # starting and ending with 2 vertices along the length of the bridge
            ordered_verts = (vert1, vert2, vert3, vert4)
            poly = self.__create_bridge_polygon(ordered_verts)
            new_polys.append(poly)

        for src_edge, dest_edge in edges_to_merge.items():

            src_vert1_id, src_vert2_id = edges[src_edge[0]]
            src_vert1 = merged_verts[src_vert1_id]
            src_vert2 = merged_verts[src_vert2_id]
            dest_vert2_id, dest_vert1_id = edges[dest_edge[0]]
            dest_vert1 = merged_verts[dest_vert1_id]
            dest_vert2 = merged_verts[dest_vert2_id]

            for merged_vert in set([src_vert1, src_vert2, dest_vert1, dest_vert2]):
                for vert_id in merged_vert:
                    if verts[vert_id].polygon_id in selected_poly_ids:
                        update_polys_to_transf = True

            if bridge_segments > 1:

                if src_vert1 not in seg_verts:
                    add_segment_vertices(src_vert1, dest_vert1)

                if src_vert2 not in seg_verts:
                    add_segment_vertices(src_vert2, dest_vert2)

                for i in range(bridge_segments):
                    vert1 = seg_verts[src_vert1][i]
                    vert2 = seg_verts[src_vert1][i + 1]
                    vert3 = seg_verts[src_vert2][i + 1]
                    vert4 = seg_verts[src_vert2][i]
                    add_new_polys(vert1, vert2, vert3, vert4)

            else:

                add_new_polys(src_vert1, dest_vert1, dest_vert2, src_vert2)

        if bridge_segments > 1:
            seg_verts.clear()

        self.create_new_geometry(new_polys)

        return True


class EdgeBridgeManager:

    def __init__(self):

        add_state = Mgr.add_state
        add_state("edge_bridge_mode", -10, self.__enter_bridge_mode,
                  self.__exit_bridge_mode)
        add_state("edge_bridge", -11)

        cancel_bridge = lambda: self._finalize_bridge(cancel=True)
        exit_mode = lambda: Mgr.exit_state("edge_bridge_mode")

        bind = Mgr.bind_state
        bind("edge_bridge_mode", "bridge edges -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("edge_bridge_mode", "bridge edges -> select", "escape", exit_mode)
        bind("edge_bridge_mode", "exit edge bridge mode", "mouse3", exit_mode)
        bind("edge_bridge_mode", "bridge edges", "mouse1", self._init_bridge)
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("edge_bridge_mode", "bridge edges ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))
        bind("edge_bridge", "quit edge bridge", "escape", cancel_bridge)
        bind("edge_bridge", "cancel edge bridge", "mouse3", cancel_bridge)
        bind("edge_bridge", "abort edge bridge", "focus_loss", cancel_bridge)
        bind("edge_bridge", "finalize edge bridge", "mouse1-up", self._finalize_bridge)
        bind("edge_bridge", "bridge edges -> pick edge via poly",
             "mouse1", self._start_dest_edge_picking_via_poly)

        status_data = GD["status"]
        mode_text = "Bridge edges"
        info_text = "LMB-drag over a border edge and release LMB over" \
                    " other border edge to create bridge; RMB or <Escape> to end"
        status_data["edge_bridge_mode"] = {"mode": mode_text, "info": info_text}

    def __enter_bridge_mode(self, prev_state_id, active):

        if prev_state_id == "edge_bridge":
            return

        if GD["active_transform_type"]:
            GD["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")

        self._mode_id = "bridge"
        Mgr.add_task(self._update_cursor, "update_mode_cursor")
        Mgr.update_app("status", ["edge_bridge_mode"])

    def __exit_bridge_mode(self, next_state_id, active):

        if next_state_id == "edge_bridge":
            return

        Mgr.remove_task("update_mode_cursor")
        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self._update_cursor()
                                        # is called
        Mgr.set_cursor("main")

        if next_state_id != "edge_picking_via_poly":
            self._mode_id = ""

    def _init_bridge(self, picked_edge=None):

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
                merged_edges = self._picked_poly.geom_data_obj.merged_edges

                for edge_id in self._picked_poly.edge_ids:
                    if len(merged_edges[edge_id]) == 1:
                        break
                else:
                    return

                Mgr.enter_state("edge_picking_via_poly")

                return

            picked_obj = Mgr.get("edge", color_id)
            edge = picked_obj.merged_edge if picked_obj else None

        if not edge or len(edge) > 1:
            return

        model = edge.toplevel_obj

        for obj in Mgr.get("selection_top"):
            if obj is not model:
                obj.geom_obj.geom_data_obj.set_pickable(False)

        self._src_border_edge = edge
        self._picking_dest_edge = True
        pos = edge.get_center_pos(GD.world)
        Mgr.do("start_drawing_rubber_band", pos)
        Mgr.do("enable_view_gizmo", False)
        Mgr.enter_state("edge_bridge")
        Mgr.set_cursor("main")

    def _finalize_bridge(self, cancel=False, picked_edge=None):

        if not cancel:
            self.__bridge_edges(picked_edge)

        src_border_edge = self._src_border_edge

        if src_border_edge:

            model = src_border_edge.toplevel_obj

            for obj in Mgr.get("selection_top"):
                if obj is not model:
                    obj.geom_obj.geom_data_obj.set_pickable()

        Mgr.do("end_drawing_rubber_band")
        self._picking_dest_edge = False
        Mgr.enter_state("edge_bridge_mode")
        Mgr.set_cursor("main" if self._pixel_under_mouse == VBase4() else "select")
        Mgr.do("enable_view_gizmo")

        self._src_border_edge = None

    def __bridge_edges(self, picked_edge=None):

        src_border_edge = self._src_border_edge

        if not src_border_edge:
            return

        model = src_border_edge.toplevel_obj

        if picked_edge:
            dest_border_edge = picked_edge
        else:
            r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
            color_id = r << 16 | g << 8 | b
            picked_obj = Mgr.get("edge", color_id)
            dest_border_edge = picked_obj.merged_edge if picked_obj else None

        if not dest_border_edge or dest_border_edge is src_border_edge or len(dest_border_edge) > 1:
            return

        geom_data_obj = model.geom_obj.geom_data_obj

        if not geom_data_obj.bridge_edges(src_border_edge, dest_border_edge):
            return

        Mgr.do("update_active_selection")
        Mgr.do("update_history_time")

        event_descr = f'Bridge edges of "{model.name}"'
        obj_data = {model.id: geom_data_obj.get_data_to_store("subobj_change")}
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)
