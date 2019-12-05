from ....base import *


class SmoothingGroup:

    def __init__(self, poly_ids=None):

        self._poly_ids = set([] if poly_ids is None else poly_ids)

    def __repr__(self):

        return f"SmoothingGroup({self._poly_ids})"

    def __hash__(self):

        return hash(tuple(sorted(self._poly_ids)))

    def __eq__(self, other):

        return False if other is None else self._poly_ids == other.get()

    def __ne__(self, other):

        return True if other is None else not self._poly_ids == other.get()

    def __getitem__(self, index):

        return list(self._poly_ids)[index]

    def __iter__(self):

        return iter(self._poly_ids)

    def __len__(self):

        return len(self._poly_ids)

    def copy(self):

        return SmoothingGroup(self._poly_ids)

    def add(self, poly_id):

        self._poly_ids.add(poly_id)

    def update(self, poly_ids):

        self._poly_ids.update(poly_ids)

    def difference_update(self, poly_ids):

        self._poly_ids.difference_update(poly_ids)

    def discard(self, poly_id):

        self._poly_ids.discard(poly_id)

    def get(self):

        return self._poly_ids

    def pop(self):

        return self._poly_ids.pop()

    def issubset(self, poly_ids):

        return self._poly_ids.issubset(poly_ids)


class SmoothingMixin:
    """ PolygonEditMixin class mix-in """

    def __init__(self):

        self._poly_smoothing = {}
        self._poly_smoothing_change = False

    def update_smoothing(self):
        """ Derive smoothing groups from shared vertex normals """

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]
        merged_verts = self.merged_verts
        shared_normals = self.shared_normals
        poly_smoothing = {}
        creases = {}

        for merged_vert in set(merged_verts.values()):

            if len(merged_vert) < 2:
                continue

            vert_ids = merged_vert[:]

            while vert_ids:

                vert_id = vert_ids.pop()
                vert = verts[vert_id]
                poly_id = vert.polygon_id

                for other_vert_id in vert_ids:
                    if other_vert_id not in shared_normals[vert_id]:
                        other_poly_id = verts[other_vert_id].polygon_id
                        creases.setdefault(poly_id, set()).add(other_poly_id)
                        creases.setdefault(other_poly_id, set()).add(poly_id)

        polys_to_process = set(polys)
        smoothing = []

        while polys_to_process:

            poly_id = polys_to_process.pop()
            polys_to_smooth = set([poly_id])
            neighbor_ids = set([poly_id])

            while neighbor_ids:

                neighbor_id = neighbor_ids.pop()
                polys_to_process.discard(neighbor_id)

                for vert_id in polys[neighbor_id].vertex_ids:

                    other_vert_ids = merged_verts[vert_id][:]
                    other_vert_ids.remove(vert_id)

                    for other_vert_id in other_vert_ids:

                        other_poly_id = verts[other_vert_id].polygon_id

                        for poly_id in creases.get(other_poly_id, set()):

                            if poly_id in polys_to_smooth:
                                break

                        else:

                            polys_to_smooth.add(other_poly_id)

                            if other_poly_id in polys_to_process:
                                neighbor_ids.add(other_poly_id)

            if len(polys_to_smooth) > 1:
                smoothing.append(polys_to_smooth)

        for polys_to_smooth in smoothing:

            smoothing_group = SmoothingGroup(polys_to_smooth)

            for poly_id in polys_to_smooth:
                poly_smoothing.setdefault(poly_id, set()).add(smoothing_group)

        # check if anything has changed
        if set(poly_smoothing) == set(self._poly_smoothing):

            old_smoothing = set()
            new_smoothing = set()

            for smoothing in self._poly_smoothing.values():
                old_smoothing.update(smoothing)

            for smoothing in poly_smoothing.values():
                new_smoothing.update(smoothing)

            old_smoothing = list(old_smoothing)

            for smoothing_grp in new_smoothing:
                if smoothing_grp not in old_smoothing:
                    break
            else:
                return False

        self._poly_smoothing = poly_smoothing
        self._poly_smoothing_change = True

        return True

    def set_smoothing(self, smoothing=None):

        if smoothing:

            self._reset_normal_sharing()
            shared_normals = self.shared_normals
            self._poly_smoothing = poly_smoothing = {}
            polys = self._subobjs["poly"]
            merged_verts = self.merged_verts

            for smoothing_grp in smoothing:

                # Update vertex normal sharing

                poly_ids = smoothing_grp[:]

                while poly_ids:

                    poly_id = poly_ids.pop()
                    poly = polys[poly_id]
                    vert_ids = poly.vertex_ids[:]

                    for other_poly_id in poly_ids:

                        other_poly = polys[other_poly_id]
                        other_vert_ids = other_poly.vertex_ids[:]

                        for vert_id in vert_ids:

                            for other_vert_id in other_vert_ids[:]:

                                if merged_verts[vert_id] is merged_verts[other_vert_id]:

                                    shared_normal = shared_normals[vert_id]
                                    other_shared_normal = shared_normals[other_vert_id]
                                    shared_normal.update(other_shared_normal)

                                    for v_id in other_shared_normal:
                                        shared_normals[v_id] = shared_normal

                                    other_vert_ids.remove(other_vert_id)

                self._normal_sharing_change = True

                # Update smoothing groups

                for poly_id in smoothing_grp:
                    poly_smoothing.setdefault(poly_id, set()).add(smoothing_grp)

                self._poly_smoothing_change = True

            merged_verts = set(self.merged_verts.values())
            self.update_vertex_normals(merged_verts, update_tangent_space=False)

            model = self.toplevel_obj

            if model.has_tangent_space():
                model.update_tangent_space()
            else:
                self._is_tangent_space_initialized = False

        else:

            self.set_smooth_shaded(False)

    def get_smoothed_polys(self, poly_id):

        polys = self._subobjs["poly"]

        if poly_id in self._poly_smoothing:

            poly_ids = set()

            for smoothing_grp in self._poly_smoothing[poly_id]:
                poly_ids.update(smoothing_grp)

            return [polys[p_id] for p_id in poly_ids]

        return [poly for p_id, poly in polys.items() if p_id not in self._poly_smoothing]

    def set_smooth_shaded(self, smooth=True):

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]
        sign = -1. if self.owner.has_flipped_normals() else 1.
        normals_to_sel = False

        if smooth:

            self._reset_normal_sharing(share=True)
            shared_normals = self.shared_normals
            all_smoothing = set()

            for poly_id in polys:
                smoothing = self._poly_smoothing.get(poly_id, set([None]))
                all_smoothing.update(smoothing)

            if len(all_smoothing) == 1 and None not in all_smoothing:
                return False, False

            smoothing_grp = SmoothingGroup(polys)

            self._poly_smoothing = {poly_id: set([smoothing_grp]) for poly_id in polys}

            vertex_data_poly = self._vertex_data["poly"]
            normal_writer = GeomVertexWriter(vertex_data_poly, "normal")

            merged_verts = self.merged_verts
            selected_normal_ids = set(self._selected_subobj_ids["normal"])

            for merged_vert in set(merged_verts.values()):

                verts_to_smooth = []
                normal = Vec3()

                for vert_id in merged_vert:

                    vert = verts[vert_id]

                    if vert.has_locked_normal():
                        continue

                    verts_to_smooth.append(vert)
                    poly = polys[vert.polygon_id]
                    normal += poly.normal

                normal.normalize()

                for vert in verts_to_smooth:
                    normal_writer.set_row(vert.row_index)
                    normal_writer.set_data3(normal * sign)
                    vert.normal = normal

                # Make sure that all normals in the same merged vertex become
                # selected if at least one of them is already selected.

                ids = set(merged_vert)
                sel_ids = selected_normal_ids.intersection(ids)

                if not sel_ids or len(sel_ids) == len(ids):
                    continue

                tmp_normal = Mgr.do("create_shared_normal", self, ids.difference(sel_ids))
                tmp_id = tmp_normal.id
                orig_normal = shared_normals[tmp_id]
                shared_normals[tmp_id] = tmp_normal
                self.update_selection("normal", [tmp_normal], [])
                shared_normals[tmp_id] = orig_normal
                normals_to_sel = True

            normal_array = vertex_data_poly.get_array(2)
            vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
            vertex_data_top.set_array(2, GeomVertexArrayData(normal_array))
            normal_geoms = self._geoms["normal"]
            vertex_data_normal = normal_geoms["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data_normal.set_array(2, normal_array)
            vertex_data_normal = normal_geoms["sel_state"].node().modify_geom(0).modify_vertex_data()
            vertex_data_normal.set_array(2, normal_array)

        else:

            if not self._poly_smoothing:
                return False, False

            self._reset_normal_sharing()
            self._poly_smoothing = {}

            vertex_data_poly = self._vertex_data["poly"]
            normal_writer = GeomVertexWriter(vertex_data_poly, "normal")

            for poly in polys.values():

                normal = poly.normal.normalized()

                for vert in poly.vertices:
                    if not vert.has_locked_normal():
                        normal_writer.set_row(vert.row_index)
                        normal_writer.set_data3(normal * sign)
                        vert.normal = Vec3(normal)

            normal_array = vertex_data_poly.get_array(2)
            vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
            vertex_data_top.set_array(2, GeomVertexArrayData(normal_array))
            normal_geoms = self._geoms["normal"]
            vertex_data_normal = normal_geoms["pickable"].node().modify_geom(0).modify_vertex_data()
            vertex_data_normal.set_array(2, normal_array)
            vertex_data_normal = normal_geoms["sel_state"].node().modify_geom(0).modify_vertex_data()
            vertex_data_normal.set_array(2, normal_array)

        self._normal_change = set(verts)
        self._poly_smoothing_change = True

        model = self.toplevel_obj

        if model.has_tangent_space():
            model.update_tangent_space()
        else:
            self._is_tangent_space_initialized = False

        return True, normals_to_sel

    def smooth_selected_polygons(self, smooth=True, poly_id=None):

        selected_poly_ids = self._selected_subobj_ids["poly"]

        if not selected_poly_ids:
            return False, False

        return self.smooth_polygons(selected_poly_ids, smooth, poly_id)

    def __smooth_polygons(self, poly_ids, smooth=True, src_poly_id=None, update_normals=True):

        polys = self._subobjs["poly"]
        verts = self._subobjs["vert"]
        shared_normals = self.shared_normals
        poly_smoothing = self._poly_smoothing
        normals_to_sel = False

        if src_poly_id is None:

            # Smooth or flatten the target polys.

            if smooth:

                # smoothing a single poly doesn't make much sense
                if len(poly_ids) == 1:
                    return False, None, False

                poly_id = poly_ids[0]

                # check if the target polys aren't already smoothed together
                if poly_id in poly_smoothing:
                    for smoothing_grp in poly_smoothing[poly_id]:
                        if set(poly_ids).issubset(smoothing_grp):
                            return False, None, False

                new_smoothing_grp = SmoothingGroup(poly_ids)

                for poly_id in poly_ids:
                    poly_smoothing.setdefault(poly_id, set()).add(new_smoothing_grp)

                polys_to_update = poly_ids

            else:

                # Remove all smoothing from the target polys.

                polys_to_update = set(poly_smoothing).intersection(poly_ids)

                for poly_id in polys_to_update:

                    if poly_id in poly_smoothing:

                        for smoothing_grp in poly_smoothing[poly_id]:

                            smoothing_grp.discard(poly_id)

                            # A smoothing group consisting of just a single poly serves no
                            # real purpose, so it can be removed

                            if len(smoothing_grp) == 1:

                                last_id = smoothing_grp.pop()
                                poly_smoothing[last_id].discard(smoothing_grp)

                                if not poly_smoothing[last_id]:
                                    del poly_smoothing[last_id]

                        del poly_smoothing[poly_id]

        else:

            # Update the smoothing of the target polys with the smoothing of the
            # source poly by adding or removing it.

            if src_poly_id not in polys:
                return False, None, False

            smoothing_change = set(poly_smoothing.get(src_poly_id, []))

            if smooth:

                # Add the smoothing of the source poly to the smoothing of the target
                # polys.

                if poly_ids == [src_poly_id]:
                    return False, None, False

                polys_to_update = set()

                if not smoothing_change:
                    # if no smoothing was applied to the source poly, create a new
                    # smoothing group to be applied to both the source and
                    # target polys
                    new_smoothing_grp = SmoothingGroup([src_poly_id])
                    smoothing_change = set([new_smoothing_grp])
                    poly_smoothing[src_poly_id] = smoothing_change
                    polys_to_update.add(src_poly_id)

                for smoothing_grp in smoothing_change:

                    dif = set(poly_ids).difference(smoothing_grp)

                    if dif:

                        smoothing_grp.update(dif)
                        polys_to_update.update(dif)

                        for poly_id in dif:
                            poly_smoothing.setdefault(poly_id, set()).add(smoothing_grp)

            else:

                # Remove the smoothing of the source poly from the smoothing of the
                # target polys.

                if not smoothing_change:
                    return False, None, False

                polys_to_update = set()

                for poly_id in poly_ids:

                    if poly_smoothing.get(poly_id, set()).intersection(smoothing_change):

                        poly_smoothing[poly_id].difference_update(smoothing_change)
                        polys_to_update.add(poly_id)

                        if not poly_smoothing[poly_id]:
                            del poly_smoothing[poly_id]

                if polys_to_update:

                    for smoothing_grp in smoothing_change:

                        smoothing_grp.difference_update(poly_ids)

                        # A smoothing group consisting of just a single poly serves no
                        # real purpose, so it can be removed

                        if len(smoothing_grp) == 1:

                            last_id = smoothing_grp.pop()
                            poly_smoothing[last_id].discard(smoothing_grp)

                            if not poly_smoothing[last_id]:
                                del poly_smoothing[last_id]

        if not polys_to_update:
            return False, None, False

        if update_normals:

            merged_verts = set(self.merged_verts[v_id] for p_id in polys_to_update
                               for v_id in polys[p_id].vertex_ids)

            # Update vertex normal sharing

            for merged_vert in merged_verts:

                vert_ids = merged_vert[:]

                for vert_id in vert_ids:
                    shared_normals[vert_id] = Mgr.do("create_shared_normal", self, [vert_id])

                while vert_ids:

                    vert_id = vert_ids.pop()
                    shared_normal = shared_normals[vert_id]
                    vert = verts[vert_id]
                    poly_id = vert.polygon_id

                    for other_vert_id in vert_ids[:]:

                        other_vert = verts[other_vert_id]
                        other_poly_id = other_vert.polygon_id

                        for smoothing_grp in poly_smoothing.get(poly_id, []):
                            if other_poly_id in smoothing_grp:
                                shared_normal.add(other_vert_id)
                                shared_normals[other_vert_id] = shared_normal
                                vert_ids.remove(other_vert_id)
                                vert_ids.append(other_vert_id)
                                break

                if not smooth:
                    continue

                # Make sure that all shared normals in the same merged vertex become
                # selected if at least one of them is already selected.

                selected_normal_ids = set(self._selected_subobj_ids["normal"])

                for shared_normal in set(shared_normals[v_id] for v_id in merged_vert):

                    ids = shared_normal
                    sel_ids = selected_normal_ids.intersection(ids)

                    if not sel_ids or len(sel_ids) == len(ids):
                        continue

                    tmp_normal = Mgr.do("create_shared_normal", self, ids.difference(sel_ids))
                    tmp_id = tmp_normal.id
                    orig_normal = shared_normals[tmp_id]
                    shared_normals[tmp_id] = tmp_normal
                    self.update_selection("normal", [tmp_normal], [])
                    shared_normals[tmp_id] = orig_normal
                    normals_to_sel = True

            self._normal_sharing_change = True

        else:

            merged_verts = None

        self._poly_smoothing_change = True

        return True, merged_verts, normals_to_sel

    def smooth_polygons(self, poly_ids, smooth=True, src_poly_id=None, update_normals=True):

        change, merged_verts, normals_to_sel = self.__smooth_polygons(poly_ids, smooth, src_poly_id,
                                                                      update_normals)

        if merged_verts:
            self.update_vertex_normals(merged_verts)

        return change, normals_to_sel

    def _restore_poly_smoothing(self, time_id):

        obj_id = self.toplevel_obj.id
        prop_id = self._unique_prop_ids["smoothing"]
        self._poly_smoothing = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)


class SmoothingManager:
    """ PolygonEditManager class mix-in """

    def __init__(self):

        Mgr.add_app_updater("model_smoothing", self.__set_smooth_shaded)
        Mgr.add_app_updater("poly_smoothing", self.__smooth_polygons)
        Mgr.add_app_updater("poly_smoothing_update", self.__update_polygon_smoothing)

        GD.set_default("sel_polys_by_smoothing", False)

        add_state = Mgr.add_state
        add_state("smoothing_poly_picking_mode", -10, self.__enter_smoothing_poly_picking_mode,
                  self.__exit_smoothing_poly_picking_mode)
        add_state("unsmoothing_poly_picking_mode", -10, self.__enter_unsmoothing_poly_picking_mode,
                  self.__exit_smoothing_poly_picking_mode)

        bind = Mgr.bind_state
        bind("smoothing_poly_picking_mode", "smooth with poly -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("smoothing_poly_picking_mode", "quit smoothing with poly", "escape",
             lambda: Mgr.exit_state("smoothing_poly_picking_mode"))
        bind("smoothing_poly_picking_mode", "cancel smoothing with poly", "mouse3",
             lambda: Mgr.exit_state("smoothing_poly_picking_mode"))
        bind("smoothing_poly_picking_mode", "pick smoothing poly", "mouse1",
             self.__pick_smoothing_poly)
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("smoothing_poly_picking_mode", "smooth ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))
        bind("unsmoothing_poly_picking_mode", "unsmooth with poly -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("unsmoothing_poly_picking_mode", "quit unsmoothing with poly", "escape",
             lambda: Mgr.exit_state("unsmoothing_poly_picking_mode"))
        bind("unsmoothing_poly_picking_mode", "cancel unsmoothing with poly", "mouse3",
             lambda: Mgr.exit_state("unsmoothing_poly_picking_mode"))
        bind("unsmoothing_poly_picking_mode", "pick unsmoothing poly", "mouse1",
             self.__pick_smoothing_poly)
        bind("unsmoothing_poly_picking_mode", "unsmooth ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))

        status_data = GD["status"]
        mode_text = "Pick poly for smoothing"
        info_text = "LMB to pick a polygon to smooth the selection with; RMB to cancel"
        status_data["smooth_with_poly"] = {"mode": mode_text, "info": info_text}
        mode_text = "Pick poly for unsmoothing"
        info_text = "LMB to pick a polygon to unsmooth the selection with; RMB to cancel"
        status_data["unsmooth_with_poly"] = {"mode": mode_text, "info": info_text}

    def __set_smooth_shaded(self, smooth=True):

        # exit any subobject modes
        Mgr.exit_states(min_persistence=-99)
        selection = Mgr.get("selection_top")
        geom_data_objs = {obj.id: obj.geom_obj.geom_data_obj for obj in selection}
        changed_objs = {}
        changed_selections = []

        for obj_id, geom_data_obj in geom_data_objs.items():

            change, normals_to_sel = geom_data_obj.set_smooth_shaded(smooth)

            if change:

                changed_objs[obj_id] = geom_data_obj

                if normals_to_sel:
                    changed_selections.append(obj_id)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.items():

            obj_data[obj_id] = geom_data_obj.get_data_to_store()

            if obj_id in changed_selections:
                obj_data[obj_id].update(geom_data_obj.get_property_to_store("subobj_selection"))

        event_descr = "Change model smoothing"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __smooth_polygons(self, smooth=True, poly_id=None):

        # exit any subobject modes
        Mgr.exit_states(min_persistence=-99)
        selection = Mgr.get("selection_top")
        changed_objs = {}
        changed_selections = []

        for model in selection:

            geom_data_obj = model.geom_obj.geom_data_obj
            change, normals_to_sel = geom_data_obj.smooth_selected_polygons(smooth, poly_id)

            if change:

                changed_objs[model.id] = geom_data_obj

                if normals_to_sel:
                    changed_selections.append(model.id)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.items():

            obj_data[obj_id] = geom_data_obj.get_data_to_store()

            if obj_id in changed_selections:
                obj_data[obj_id].update(geom_data_obj.get_property_to_store("subobj_selection"))

        event_descr = "Change polygon smoothing"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __update_polygon_smoothing(self):

        # exit any subobject modes
        Mgr.exit_states(min_persistence=-99)
        selection = Mgr.get("selection_top")
        changed_objs = {}

        for model in selection:

            geom_data_obj = model.geom_obj.geom_data_obj

            if geom_data_obj.update_smoothing():
                changed_objs[model.id] = geom_data_obj

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.items():
            obj_data[obj_id] = geom_data_obj.get_data_to_store()

        event_descr = "Update polygon smoothing"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __enter_smoothing_poly_picking_mode(self, prev_state_id, active):

        GD["active_transform_type"] = ""
        Mgr.update_app("active_transform_type", "")
        Mgr.add_task(self._update_cursor, "update_poly_picking_cursor")
        Mgr.update_app("status", ["smooth_with_poly"])

    def __enter_unsmoothing_poly_picking_mode(self, prev_state_id, active):

        GD["active_transform_type"] = ""
        Mgr.update_app("active_transform_type", "")
        Mgr.add_task(self._update_cursor, "update_poly_picking_cursor")
        Mgr.update_app("status", ["unsmooth_with_poly"])

    def __exit_smoothing_poly_picking_mode(self, next_state_id, active):

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self._update_cursor()
                                        # is called
        Mgr.remove_task("update_poly_picking_cursor")
        Mgr.set_cursor("main")

    def __pick_smoothing_poly(self):

        if not self._pixel_under_mouse:
            return

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b
        poly = Mgr.get("poly", color_id)
        state_id = Mgr.get_state_id()

        if poly:
            if state_id == "smoothing_poly_picking_mode":
                Mgr.update_locally("poly_smoothing", True, poly.id)
            else:
                Mgr.update_locally("poly_smoothing", False, poly.id)
