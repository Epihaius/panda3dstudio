from ....base import *


class SmoothingGroup(object):

    def __init__(self, poly_ids=None):

        self._poly_ids = set([] if poly_ids is None else poly_ids)

    def __eq__(self, other):

        return self._poly_ids == other.get()

    def __ne__(self, other):

        return not self._poly_ids == other.get()

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


class SmoothingBase(BaseObject):

    def __init__(self):

        self._poly_smoothing = {}

    def set_smoothing(self, smoothing=None):

        if smoothing:

            self._poly_smoothing = poly_smoothing = {}

            for smoothing_grp in smoothing:
                for poly_id in smoothing_grp:
                    poly_smoothing.setdefault(
                        poly_id, set()).add(smoothing_grp)

            self._update_vertex_normals(set(self._merged_verts.itervalues()))

        else:

            self.set_smooth_shaded(False)

    def get_smoothed_polys(self, poly_id):

        polys = self._subobjs["poly"]

        if poly_id in self._poly_smoothing:

            poly_ids = set()

            for smoothing_grp in self._poly_smoothing[poly_id]:
                poly_ids.update(smoothing_grp)

            return [polys[p_id] for p_id in poly_ids]

        return [poly for p_id, poly in polys.iteritems() if p_id not in self._poly_smoothing]

    def get_vertex_normals(self):

        verts = self._subobjs["vert"]
        vertex_data_poly = self._vertex_data["poly"]
        normal_reader = GeomVertexReader(vertex_data_poly, "normal")
        normals = {}

        for vert_id, vert in verts.iteritems():
            normal_reader.set_row(vert.get_row_index())
            normals[vert_id] = normal_reader.get_data3f()

        return normals

    def set_smooth_shaded(self, smooth=True):

        polys = self._subobjs["poly"]

        if smooth:

            all_smoothing = set()

            for poly_id in polys:
                smoothing = self._poly_smoothing.get(poly_id, set([None]))
                all_smoothing.update(smoothing)

            if len(all_smoothing) == 1 and None not in all_smoothing:
                return False

            verts = self._subobjs["vert"]
            smoothing_grp = SmoothingGroup(polys.iterkeys())

            self._poly_smoothing = dict(
                (poly_id, set([smoothing_grp])) for poly_id in polys)

            vertex_data_poly = self._vertex_data["poly"]
            normal_writer = GeomVertexWriter(vertex_data_poly, "normal")

            merged_verts = self._merged_verts

            for merged_vert in set(merged_verts.itervalues()):

                verts_to_smooth = []
                normal = Vec3()

                for vert_id in merged_vert:
                    vert = verts[vert_id]
                    poly = polys[vert.get_polygon_id()]
                    normal += poly.get_normal()
                    verts_to_smooth.append(vert)

                normal.normalize()

                for vert in verts_to_smooth:
                    normal_writer.set_row(vert.get_row_index())
                    normal_writer.set_data3f(normal)

            array = vertex_data_poly.get_array(1)
            vertex_data_top = self._geoms["top"][
                "shaded"].node().modify_geom(0).modify_vertex_data()
            vertex_data_top.set_array(1, GeomVertexArrayData(array))

        else:

            if not self._poly_smoothing:
                return False

            self._poly_smoothing = {}

            vertex_data_poly = self._vertex_data["poly"]
            normal_writer = GeomVertexWriter(vertex_data_poly, "normal")

            for poly in polys.itervalues():

                normal = Vec3() + poly.get_normal()
                normal.normalize()

                for vert in poly.get_vertices():
                    normal_writer.set_row(vert.get_row_index())
                    normal_writer.set_data3f(normal)

            array = vertex_data_poly.get_array(1)
            vertex_data_top = self._geoms["top"][
                "shaded"].node().modify_geom(0).modify_vertex_data()
            vertex_data_top.set_array(1, GeomVertexArrayData(array))

        return True

    def smooth_selected_polygons(self, smooth=True, poly_id=None):

        selected_poly_ids = self._selected_subobj_ids["poly"]

        if not selected_poly_ids:
            return False

        return self.smooth_polygons(selected_poly_ids, smooth, poly_id)

    def smooth_polygons(self, poly_ids, smooth=True, src_poly_id=None, update_normals=True):

        polys = self._subobjs["poly"]
        poly_smoothing = self._poly_smoothing

        if src_poly_id is None:

            # Smooth or flatten the target polys.

            if smooth:

                # smoothing a single poly doesn't make much sense
                if len(poly_ids) == 1:
                    return False

                poly_id = poly_ids[0]

                # check if the target polys aren't already smoothed together
                if poly_id in poly_smoothing:
                    for smoothing_grp in poly_smoothing[poly_id]:
                        if set(poly_ids).issubset(smoothing_grp):
                            return False

                new_smoothing_grp = SmoothingGroup(poly_ids)

                for p_id in poly_ids:
                    poly_smoothing.setdefault(
                        p_id, set()).add(new_smoothing_grp)

                polys_to_smooth = poly_ids
                change = True

            else:

                # Remove all smoothing from the target polys.

                change = False
                polys_to_smooth = set()

                for p_id in poly_ids:

                    if p_id in poly_smoothing:

                        for smoothing_grp in poly_smoothing[p_id]:

                            smoothing_grp.discard(p_id)

                            if len(smoothing_grp) == 1:

                                last_id = smoothing_grp.pop()
                                poly_smoothing[last_id].discard(smoothing_grp)

                                if not poly_smoothing[last_id]:
                                    del poly_smoothing[last_id]

                        del poly_smoothing[p_id]
                        polys_to_smooth.add(p_id)
                        change = True

        else:

            # Update the smoothing of the target polys with the smoothing of the
            # source poly by adding or removing it.

            if src_poly_id not in polys:
                return False

            smoothing_change = poly_smoothing.get(src_poly_id)

            if smooth:

                # Add the smoothing of the source poly to the smoothing of the target
                # polys.

                if poly_ids == [src_poly_id]:
                    return False

                change = False
                polys_to_smooth = set()

                if not smoothing_change:
                    # if no smoothing was applied to the source poly, create a new
                    # smoothing group to be applied to both the source and
                    # target polys
                    new_smoothing_grp = SmoothingGroup([src_poly_id])
                    smoothing_change = set([new_smoothing_grp])
                    poly_smoothing[src_poly_id] = smoothing_change
                    polys_to_smooth.add(src_poly_id)

                for smoothing_grp in smoothing_change:

                    dif = set(poly_ids).difference(smoothing_grp)

                    if dif:

                        smoothing_grp.update(dif)
                        polys_to_smooth.update(dif)

                        for p_id in dif:
                            poly_smoothing.setdefault(
                                p_id, set()).add(smoothing_grp)
                        change = True

            else:

                # Remove the smoothing of the source poly from the smoothing of the
                # target polys.

                if not smoothing_change:
                    return False

                change = False
                polys_to_smooth = set()

                for p_id in poly_ids:

                    if p_id in poly_smoothing:

                        intersection = poly_smoothing[
                            p_id].intersection(smoothing_change)

                        if intersection:

                            poly_smoothing[p_id].difference_update(
                                intersection)
                            polys_to_smooth.add(p_id)

                            if not poly_smoothing[p_id]:
                                del poly_smoothing[p_id]

                            for smoothing_grp in intersection:

                                smoothing_grp.discard(p_id)

                                if len(smoothing_grp) == 1:

                                    last_id = smoothing_grp.pop()
                                    poly_smoothing[last_id].discard(
                                        smoothing_grp)
                                    polys_to_smooth.add(last_id)

                                    if not poly_smoothing[last_id]:
                                        del poly_smoothing[last_id]

                            change = True

        if not change:
            return False

        if update_normals:
            vert_ids = [vert_id for p_id in polys_to_smooth
                        for vert_id in polys[p_id].get_vertex_ids()]
            merged_verts = set(self._merged_verts[
                               vert_id] for vert_id in vert_ids)
            self._update_vertex_normals(merged_verts)

        return True

    def _update_vertex_normals(self, merged_verts):

        # Update the normals of the vertices associated with the given merged
        # verts.

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]

        vertex_data_copy = GeomVertexData(self._vertex_data["poly"])
        normal_writer = GeomVertexWriter(vertex_data_copy, "normal")

        poly_smoothing = self._poly_smoothing
        processed_verts = []

        for merged_vert in merged_verts:

            for vert_id in merged_vert:

                vert = verts[vert_id]

                if vert in processed_verts:
                    continue

                poly_id = vert.get_polygon_id()
                smoothing = poly_smoothing.get(poly_id)
                poly = polys[poly_id]

                if smoothing:

                    verts_to_smooth = []
                    normal = Vec3()
                    tmp_vert_ids = []
                    smoothing_to_check = set()

                    for vert2_id in merged_vert:

                        vert2 = verts[vert2_id]

                        if vert2 in processed_verts:
                            continue

                        poly2_id = vert2.get_polygon_id()

                        if poly2_id not in poly_smoothing:
                            continue

                        smoothing2 = poly_smoothing[poly2_id]

                        if smoothing2.intersection(smoothing):
                            smoothing_to_check.update(
                                smoothing2.difference(smoothing))
                            poly2 = polys[poly2_id]
                            normal += poly2.get_normal()
                            verts_to_smooth.append(vert2)
                        else:
                            tmp_vert_ids.append(vert2_id)

                    while tmp_vert_ids and smoothing_to_check:

                        next_smoothing_to_check = set()

                        for tmp_vert_id in tmp_vert_ids[:]:

                            vert2 = verts[tmp_vert_id]
                            poly2_id = vert2.get_polygon_id()
                            smoothing2 = poly_smoothing[poly2_id]

                            if smoothing2.intersection(smoothing_to_check):
                                next_smoothing_to_check.update(
                                    smoothing2.difference(smoothing_to_check))
                                poly2 = polys[poly2_id]
                                normal += poly2.get_normal()
                                verts_to_smooth.append(vert2)
                                tmp_vert_ids.remove(tmp_vert_id)

                        smoothing_to_check = next_smoothing_to_check

                    normal.normalize()

                    for vert in verts_to_smooth:
                        normal_writer.set_row(vert.get_row_index())
                        normal_writer.set_data3f(normal)

                    processed_verts.extend(verts_to_smooth)

                else:

                    normal = Vec3() + poly.get_normal()
                    normal.normalize()
                    normal_writer.set_row(vert.get_row_index())
                    normal_writer.set_data3f(normal)
                    processed_verts.append(vert)

        array = vertex_data_copy.get_array(1)
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_array(1, GeomVertexArrayData(array))
        vertex_data_top = self._geoms["top"][
            "shaded"].node().modify_geom(0).modify_vertex_data()
        vertex_data_top.set_array(1, GeomVertexArrayData(array))

    def _restore_poly_smoothing(self, time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = "smoothing"
        self._poly_smoothing, last_time_id = Mgr.do("load_last_from_history", obj_id,
                                                    prop_id, time_id, return_last_time_id=True)

        self._vert_normal_change.update(self._subobjs["vert"].iterkeys())

    def _restore_vertex_normals(self):

        merged_verts = set(self._merged_verts[vert_id]
                           for vert_id in self._vert_normal_change)
        self._vert_normal_change = set()
        self._update_vertex_normals(merged_verts)


class SmoothingManager(BaseObject):

    def __init__(self):

        Mgr.add_app_updater("model_smoothing", self.__set_smooth_shaded)
        Mgr.add_app_updater("poly_smoothing", self.__smooth_polygons)

    def setup(self):

        Mgr.set_global("sel_polys_by_smoothing", False)

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
        bind("smoothing_poly_picking_mode", "cancel smoothing with poly", "mouse3-up",
             lambda: Mgr.exit_state("smoothing_poly_picking_mode"))
        bind("smoothing_poly_picking_mode", "pick smoothing poly", "mouse1",
             self.__pick_smoothing_poly)
        bind("unsmoothing_poly_picking_mode", "unsmooth with poly -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("unsmoothing_poly_picking_mode", "quit unsmoothing with poly", "escape",
             lambda: Mgr.exit_state("unsmoothing_poly_picking_mode"))
        bind("unsmoothing_poly_picking_mode", "cancel unsmoothing with poly", "mouse3-up",
             lambda: Mgr.exit_state("unsmoothing_poly_picking_mode"))
        bind("unsmoothing_poly_picking_mode", "pick unsmoothing poly", "mouse1",
             self.__pick_smoothing_poly)

        status_data = Mgr.get_global("status_data")
        mode_text = "Pick poly for smoothing"
        info_text = "LMB to pick a polygon to smooth the selection with; RMB to cancel"
        status_data["smooth_with_poly"] = {
            "mode": mode_text, "info": info_text}
        mode_text = "Pick poly for unsmoothing"
        info_text = "LMB to pick a polygon to unsmooth the selection with; RMB to cancel"
        status_data["unsmooth_with_poly"] = {
            "mode": mode_text, "info": info_text}

        return True

    def __set_smooth_shaded(self, smooth=True):

        selection = Mgr.get("selection", "top")
        geom_data_objs = dict((obj.get_id(), obj.get_geom_object().get_geom_data_object())
                              for obj in selection)
        changed_objs = {}

        for obj_id, data_obj in geom_data_objs.iteritems():
            if data_obj.set_smooth_shaded(smooth):
                changed_objs[obj_id] = data_obj

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, data_obj in changed_objs.iteritems():
            obj_data[obj_id] = data_obj.get_data_to_store(
                "prop_change", "smoothing")

        event_descr = "Change model smoothing"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __smooth_polygons(self, smooth=True, poly_id=None):

        selection = Mgr.get("selection", "top")
        geom_data_objs = dict((obj.get_id(), obj.get_geom_object().get_geom_data_object())
                              for obj in selection)
        changed_objs = {}

        for obj_id, data_obj in geom_data_objs.iteritems():
            if data_obj.smooth_selected_polygons(smooth, poly_id):
                changed_objs[obj_id] = data_obj

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, data_obj in changed_objs.iteritems():
            obj_data[obj_id] = data_obj.get_data_to_store(
                "prop_change", "smoothing")

        event_descr = "Change polygon smoothing"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __enter_smoothing_poly_picking_mode(self, prev_state_id, is_active):

        Mgr.add_task(self._update_cursor, "update_poly_picking_cursor")
        Mgr.update_app("status", "smooth_with_poly")

    def __enter_unsmoothing_poly_picking_mode(self, prev_state_id, is_active):

        Mgr.add_task(self._update_cursor, "update_poly_picking_cursor")
        Mgr.update_app("status", "unsmooth_with_poly")

    def __exit_smoothing_poly_picking_mode(self, next_state_id, is_active):

        self._obj_is_under_mouse = None  # neither False nor True, to force an
        # update of the cursor next time
        # self._update_cursor() is called
        Mgr.remove_task("update_poly_picking_cursor")
        Mgr.set_cursor("main")

    def __pick_smoothing_poly(self):

        r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
        color_id = r << 16 | g << 8 | b  # credit to coppertop @ panda3d.org
        poly = Mgr.get("poly", color_id)
        state_id = Mgr.get_state_id()

        if poly:
            if state_id == "smoothing_poly_picking_mode":
                Mgr.update_locally("poly_smoothing", True, poly.get_id())
            else:
                Mgr.update_locally("poly_smoothing", False, poly.get_id())
