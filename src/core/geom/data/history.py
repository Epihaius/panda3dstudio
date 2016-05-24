from ...base import *


class GeomHistoryBase(BaseObject):

    def __init__(self):

        self._vert_normal_change = set()
        self._tri_change_all = False
        self._subobj_change = {"vert": {}, "edge": {}, "poly": {}}

    def get_data_to_store(self, event_type, prop_id="", info=""):

        data = {}

        obj_id = self.get_toplevel_object().get_id()
        cur_time_id = Mgr.do("get_history_time")

        if event_type == "creation":

            data["geom_data"] = {"main": self}

            for prop_id in self.get_property_ids():
                data.update(self.get_property_to_store(prop_id, event_type))

            prev_time_ids = (cur_time_id,)

            for subobj_type in ("vert", "edge", "poly"):

                subobjs = self._subobjs[subobj_type]

                for subobj in subobjs.itervalues():
                    subobj.set_creation_time(cur_time_id)

                pickled_objs = dict((s_id, cPickle.dumps(s, -1))
                                    for s_id, s in subobjs.iteritems())

                extra_data = {"%s_objs" % subobj_type: {"created": pickled_objs}}

                data["%ss" % subobj_type] = {"main": prev_time_ids, "extra": extra_data}

        elif event_type == "deletion":

            for prop_id in ("subobj_transform", "poly_tris", "uvs"):
                data.update(self.get_property_to_store(prop_id, event_type))

            for subobj_type in ("vert", "edge", "poly"):

                prev_time_ids = Mgr.do("load_last_from_history", obj_id, "%ss" % subobj_type)
                prev_time_ids += (cur_time_id,)

                subobjs = self._subobjs[subobj_type].iteritems()
                creation_times = dict((s_id, s.get_creation_time()) for s_id, s in subobjs)
                extra_data = {"%s_objs" % subobj_type: {"deleted": creation_times}}

                data["%ss" % subobj_type] = {"main": prev_time_ids, "extra": extra_data}

        elif event_type == "subobj_change":

            for prop_id in ("subobj_merge", "subobj_transform", "poly_tris", "uvs"):
                data.update(self.get_property_to_store(prop_id, event_type))

            subobj_change = self._subobj_change

            if "selection" in subobj_change:
                data.update(self.get_property_to_store("subobj_selection"))

            deleted_polys = subobj_change["poly"].get("deleted")

            if info == "rebuild":

                data.update(self.get_property_to_store("smoothing"))

            elif deleted_polys:

                poly_ids = [poly.get_id() for poly in deleted_polys]

                # check if the smoothing of this object has changed (by deleting
                # smoothed polys, which is equivalent to flattening them)
                if self.smooth_polygons(poly_ids, smooth=False, update_normals=False):
                    data.update(self.get_property_to_store("smoothing"))

            for subobj_type in ("vert", "edge", "poly"):

                prev_time_ids = Mgr.do("load_last_from_history", obj_id, "%ss" % subobj_type)
                prev_time_ids += (cur_time_id,)
                data_to_store = {}

                if "deleted" in subobj_change[subobj_type]:

                    deleted_subobjs = subobj_change[subobj_type]["deleted"]
                    # creation times of the deleted subobjects
                    creation_times = dict((s.get_id(), s.get_creation_time())
                                          for s in deleted_subobjs)
                    data_to_store["deleted"] = creation_times

                if "created" in subobj_change[subobj_type]:

                    created_subobjs = subobj_change[subobj_type]["created"]
                    pickled_objs = {}

                    for subobj in created_subobjs:
                        subobj.set_creation_time(cur_time_id)
                        pickled_objs[subobj.get_id()] = cPickle.dumps(subobj, -1)

                    data_to_store["created"] = pickled_objs

                extra_data = {"%s_objs" % subobj_type: data_to_store}
                data["%ss" % subobj_type] = {"main": prev_time_ids, "extra": extra_data}

            self._subobj_change = {"vert": {}, "edge": {}, "poly": {}}

        elif event_type == "prop_change":

            if prop_id in self._prop_ids:
                data = self.get_property_to_store(prop_id, event_type, info)

            self._uv_change = set()

        self._vert_normal_change = set()

        return data

    def get_property_to_store(self, prop_id, event_type="", info=""):

        data = {}

        if prop_id == "subobj_merge":

            data[prop_id] = {"main": (self._merged_verts, self._merged_edges)}

        if prop_id == "smoothing":

            data[prop_id] = {"main": self._poly_smoothing}

        elif prop_id == "subobj_selection":

            data[prop_id] = {"main": self._selected_subobj_ids}

        elif prop_id == "subobj_transform":

            obj_id = self.get_toplevel_object().get_id()
            subobj_lvl = GlobalData["active_obj_level"]
            pos_data = {"prev": {}, "pos": {}}
            extra_data = {"vert_pos_data": pos_data}
            cur_time_id = Mgr.do("get_history_time")
            prev_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id)
            verts = self._subobjs["vert"]

            if prev_time_ids:
                prev_time_ids += (cur_time_id,)
            else:
                prev_time_ids = (cur_time_id,)

            if event_type == "creation":

                for vert_id, vert in verts.iteritems():
                    pos = vert.get_pos()
                    pos_data["pos"][vert_id] = pos
                    vert.set_previous_property_time("transform", cur_time_id)

            elif event_type == "deletion":

                for vert_id, vert in verts.iteritems():
                    time_id = vert.get_previous_property_time("transform")
                    pos_data["prev"][vert_id] = time_id

            elif event_type == "subobj_change":

                deleted_verts = self._subobj_change["vert"].get("deleted", [])

                for vert in deleted_verts:
                    time_id = vert.get_previous_property_time("transform")
                    pos_data["prev"][vert.get_id()] = time_id

                created_verts = self._subobj_change["vert"].get("created", [])

                for vert in created_verts:
                    pos = vert.get_pos()
                    pos_data["pos"][vert.get_id()] = pos
                    vert.set_previous_property_time("transform", cur_time_id)

            elif event_type == "prop_change":

                if info == "all":
                    xformed_verts = set(self._merged_verts.itervalues())
                else:
                    xformed_verts = self._verts_to_transf[subobj_lvl]

                for merged_vert in xformed_verts:

                    pos = merged_vert.get_pos()

                    for vert_id in merged_vert:
                        # since it can happen that a MergedVertex references both previously
                        # transformed Vertex objects and newly created ones, the MergedVertex
                        # cannot be relied upon to get a single previous transform time for
                        # all the Vertex objects it references, so this has to be retrieved
                        # per Vertex object
                        time_id = verts[vert_id].get_previous_property_time("transform")
                        pos_data["pos"][vert_id] = pos
                        pos_data["prev"][vert_id] = time_id

                    merged_vert.set_previous_property_time("transform", cur_time_id)

            data[prop_id] = {"main": prev_time_ids, "extra": extra_data}

        elif prop_id == "poly_tris":

            obj_id = self.get_toplevel_object().get_id()
            subobj_lvl = GlobalData["active_obj_level"]
            tri_data = {"prev": {}, "tri_data": {}}
            extra_data = {"tri_data": tri_data}
            cur_time_id = Mgr.do("get_history_time")
            prev_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id)
            polys = self._subobjs["poly"]

            if prev_time_ids:
                prev_time_ids += (cur_time_id,)
            else:
                prev_time_ids = (cur_time_id,)

            if event_type == "creation":

                for poly_id, poly in polys.iteritems():
                    tris = poly[:]
                    tri_data["tri_data"][poly_id] = tris
                    poly.set_previous_property_time("tri_data", cur_time_id)

            elif event_type == "deletion":

                for poly_id, poly in polys.iteritems():
                    time_id = poly.get_previous_property_time("tri_data")
                    tri_data["prev"][poly_id] = time_id

            elif event_type == "subobj_change":

                deleted_polys = self._subobj_change["poly"].get("deleted", [])

                for poly in deleted_polys:
                    time_id = poly.get_previous_property_time("tri_data")
                    tri_data["prev"][poly.get_id()] = time_id

                created_polys = self._subobj_change["poly"].get("created", [])

                for poly in created_polys:
                    tris = poly[:]
                    tri_data["tri_data"][poly.get_id()] = tris
                    poly.set_previous_property_time("tri_data", cur_time_id)

            elif event_type == "prop_change":

                if self._tri_change_all:
                    poly_ids = polys.iterkeys()
                    self._tri_change_all = False
                else:
                    poly_ids = self._selected_subobj_ids["poly"]

                for poly_id in poly_ids:
                    poly = polys[poly_id]
                    tris = poly[:]
                    time_id = poly.get_previous_property_time("tri_data")
                    tri_data["tri_data"][poly_id] = tris
                    tri_data["prev"][poly_id] = time_id
                    poly.set_previous_property_time("tri_data", cur_time_id)

            data[prop_id] = {"main": prev_time_ids, "extra": extra_data}

        elif prop_id == "uvs":

            obj_id = self.get_toplevel_object().get_id()
            uv_data = {"prev": {}, "uvs": {}}
            extra_data = {"uv_data": uv_data}
            cur_time_id = Mgr.do("get_history_time")
            prev_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id)
            verts = self._subobjs["vert"]

            if prev_time_ids:
                prev_time_ids += (cur_time_id,)
            else:
                prev_time_ids = (cur_time_id,)

            if event_type == "creation":

                for vert_id, vert in verts.iteritems():
                    uvs = vert.get_uvs()
                    uv_data["uvs"][vert_id] = uvs
                    vert.set_previous_property_time("uvs", cur_time_id)

            elif event_type == "deletion":

                for vert_id, vert in verts.iteritems():
                    time_id = vert.get_previous_property_time("uvs")
                    uv_data["prev"][vert_id] = time_id

            elif event_type == "subobj_change":

                created_verts = self._subobj_change["vert"].get("created", [])

                for vert in created_verts:
                    uvs = vert.get_uvs()
                    uv_data["uvs"][vert.get_id()] = uvs
                    vert.set_previous_property_time("uvs", cur_time_id)

                deleted_verts = self._subobj_change["vert"].get("deleted", [])

                for vert in deleted_verts:
                    time_id = vert.get_previous_property_time("uvs")
                    uv_data["prev"][vert.get_id()] = time_id

            elif event_type == "prop_change":

                for vert_id in self._uv_change:
                    vert = verts[vert_id]
                    uvs = vert.get_uvs()
                    time_id = vert.get_previous_property_time("uvs")
                    uv_data["uvs"][vert_id] = uvs
                    uv_data["prev"][vert_id] = time_id
                    vert.set_previous_property_time("uvs", cur_time_id)

            data[prop_id] = {"main": prev_time_ids, "extra": extra_data}

        return data

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()

        if "self" in data_ids:

            self.update_selection_state(self.get_toplevel_object().is_selected())

            for prop_id in self.get_property_ids():
                self.__restore_property(prop_id, restore_type, old_time_id, new_time_id)

            task = lambda: self.__restore_subgeometry(old_time_id, new_time_id)
            task_id = "restore_subobjs"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = self.unregister_subobjects
            task_id = "unregister_subobjs"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = self.register_subobjects
            task_id = "register_subobjs"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        else:

            for prop_id in self.get_property_ids():
                if prop_id in data_ids:
                    self.__restore_property(prop_id, restore_type, old_time_id, new_time_id)

            if "polys" in data_ids:

                task = lambda: self.__restore_subgeometry(old_time_id, new_time_id)
                task_id = "restore_subobjs"
                PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

                task = self.unregister_subobjects
                task_id = "unregister_subobjs"
                PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

                task = self.register_subobjects
                task_id = "register_subobjs"
                PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

    def __restore_property(self, prop_id, restore_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()

        if prop_id == "subobj_merge":

            def update_verts_to_transform():

                for subobj_type in ("vert", "edge", "poly"):
                    self._update_verts_to_transform(subobj_type)

            task = lambda: self.__restore_subobj_merge(new_time_id)
            task_id = "merge_subobjs"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = lambda: Mgr.do("update_active_selection", restore=True)
            task_id = "upd_subobj_sel"
            PendingTasks.add(task, task_id, "object")

            task = update_verts_to_transform
            task_id = "upd_verts_to_transf"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = lambda: self._restore_poly_smoothing(new_time_id)
            task_id = "smooth_polys"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = self._restore_vertex_normals
            task_id = "upd_vert_normals"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        elif prop_id == "smoothing":

            task = lambda: self._restore_poly_smoothing(new_time_id)
            task_id = "smooth_polys"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = self._restore_vertex_normals
            task_id = "upd_vert_normals"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        elif prop_id == "subobj_selection":

            task = lambda: self._restore_subobj_selection(new_time_id)
            task_id = "set_subobj_sel"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = lambda: Mgr.do("update_active_selection", restore=True)
            task_id = "upd_subobj_sel"
            PendingTasks.add(task, task_id, "object")

        elif prop_id == "subobj_transform":

            task = lambda: self._restore_subobj_transforms(old_time_id, new_time_id)
            task_id = "set_subobj_transf"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = self._restore_vertex_normals
            task_id = "upd_vert_normals"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        elif prop_id == "poly_tris":

            task = lambda: self._restore_poly_triangle_data(old_time_id, new_time_id)
            task_id = "set_poly_triangles"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = self._restore_vertex_normals
            task_id = "upd_vert_normals"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        elif prop_id == "uvs":

            task = lambda: self._restore_uvs(old_time_id, new_time_id)
            task_id = "set_uvs"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

    def __restore_subgeometry(self, old_time_id, new_time_id):

        subobjs = self._subobjs
        selected_subobj_ids = self._selected_subobj_ids
        selected_vert_ids = selected_subobj_ids["vert"]
        selected_edge_ids = selected_subobj_ids["edge"]
        selected_poly_ids = selected_subobj_ids["poly"]

        subobjs_to_reg = self._subobjs_to_reg
        subobjs_to_unreg = self._subobjs_to_unreg
        verts_to_reg = subobjs_to_reg["vert"]
        verts_to_unreg = subobjs_to_unreg["vert"]
        edges_to_reg = subobjs_to_reg["edge"]
        edges_to_unreg = subobjs_to_unreg["edge"]
        polys_to_reg = subobjs_to_reg["poly"]
        polys_to_unreg = subobjs_to_unreg["poly"]

        vert_change = self.__restore_subobjects("vert", old_time_id, new_time_id)
        edge_change = self.__restore_subobjects("edge", old_time_id, new_time_id)
        poly_change = self.__restore_subobjects("poly", old_time_id, new_time_id)
        verts_to_remove, verts_to_restore = vert_change
        edges_to_remove, edges_to_restore = edge_change
        polys_to_remove, polys_to_restore = poly_change

        self.__init_subobj_restore()

        if polys_to_remove:
            self.__remove_polys(polys_to_remove)

        for vert in verts_to_remove:

            vert_id = vert.get_id()
            del subobjs["vert"][vert_id]
            verts_to_unreg[vert_id] = vert

            if vert_id in selected_vert_ids:
                selected_vert_ids.remove(vert_id)

        for vert in verts_to_restore:
            vert_id = vert.get_id()
            subobjs["vert"][vert_id] = vert
            verts_to_reg[vert_id] = vert
            vert.set_geom_data_object(self)
            self._vert_normal_change.add(vert_id)

        for edge in edges_to_remove:

            edge_id = edge.get_id()
            del subobjs["edge"][edge_id]
            edges_to_unreg[edge_id] = edge

            if edge_id in selected_edge_ids:
                selected_edge_ids.remove(edge_id)

        for edge in edges_to_restore:
            edge_id = edge.get_id()
            subobjs["edge"][edge_id] = edge
            edges_to_reg[edge_id] = edge
            edge.set_geom_data_object(self)

        for poly in polys_to_remove:

            poly_id = poly.get_id()
            del subobjs["poly"][poly_id]
            polys_to_unreg[poly_id] = poly

            if poly_id in selected_poly_ids:
                selected_poly_ids.remove(poly_id)

        for poly in polys_to_restore:
            poly_id = poly.get_id()
            subobjs["poly"][poly_id] = poly
            poly.set_geom_data_object(self)
            polys_to_reg[poly_id] = poly

        if polys_to_restore:
            self.__restore_polys(polys_to_restore)

        self.__finalize_subobj_restore()

        selected_subobj_ids["vert"] = []
        selected_subobj_ids["edge"] = []
        selected_subobj_ids["poly"] = []

        for vert_id in selected_vert_ids:
            self.set_selected(subobjs["vert"][vert_id], True, False)

        for edge_id in selected_edge_ids:
            self.set_selected(subobjs["edge"][edge_id], True, False)

        for poly_id in selected_poly_ids:
            self.set_selected(subobjs["poly"][poly_id], True, False)

        for subobj_type in ("vert", "edge", "poly"):
            self._update_verts_to_transform(subobj_type)

    def __restore_subobjects(self, subobj_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = "%ss" % subobj_type

        prev_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id, old_time_id)
        new_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)

        if prev_time_ids is None:

            # this is the case when the creation of the GeomDataObject is being redone;
            # as such, there are no subobjects defined before the time of creation
            # (given by old_time_id)

            prev_time_ids = ()

        else:

            i = 0

            for time_id in new_time_ids:

                if time_id not in prev_time_ids:
                    break

                i += 1

            common_time_ids = prev_time_ids[:i]
            prev_time_ids = prev_time_ids[i:]
            new_time_ids = new_time_ids[i:]

        subobjs_to_recreate = {}
        subobjs_to_delete = {}
        registered_subobjs = self._subobjs[subobj_type]

        data_id = "%s_objs" % subobj_type

        # undo current subobject creation/deletion state

        for time_id in prev_time_ids:

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            created_subobjs = subobj_data.get("created", {})
            deleted_subobjs = subobj_data.get("deleted", {})

            for subobj_id in created_subobjs:
                if subobj_id in registered_subobjs:
                    subobjs_to_delete[subobj_id] = registered_subobjs[subobj_id]

            data_to_load = {}

            for subobj_id, time_id2 in deleted_subobjs.iteritems():
                if time_id2 in common_time_ids:
                    data_to_load.setdefault(time_id2, []).append(subobj_id)

            for time_id2, subobj_ids in data_to_load.iteritems():

                subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id2)
                created_subobjs = subobj_data["created"]

                for subobj_id in subobj_ids:
                    subobjs_to_recreate[subobj_id] = created_subobjs[subobj_id]

        # redo target subobject creation/deletion state

        for time_id in new_time_ids:

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            created_subobjs = subobj_data.get("created", {})
            deleted_subobjs = subobj_data.get("deleted", {})

            for subobj_id in deleted_subobjs:
                if subobj_id in subobjs_to_recreate:
                    del subobjs_to_recreate[subobj_id]
                else:
                    subobjs_to_delete[subobj_id] = registered_subobjs[subobj_id]

            subobjs_to_recreate.update(created_subobjs)

        subobjs_to_create = []

        for subobj_id, pickled_subobj in subobjs_to_recreate.iteritems():
            created_subobj = cPickle.loads(pickled_subobj)
            subobjs_to_create.append(created_subobj)

        return subobjs_to_delete.values(), subobjs_to_create

    def __init_subobj_restore(self):

        sel_state = self._subobj_sel_state

        for subobj_type in ("vert", "edge", "poly"):
            for state in ("selected", "unselected"):
                sel_state[subobj_type][state] = []
                geom_node = self._geoms[subobj_type][state].node()
                geom_node.modify_geom(0).modify_primitive(0).modify_vertices().modify_handle().set_data("")
                # NOTE: do *NOT* call geom_node.modify_geom(0).modify_primitive(0).clearVertices(),
                # as this will explicitly remove all data from the primitive, and adding new
                # data thru ...modify_primitive(0).modify_vertices().modify_handle().set_data(data)
                # will not internally notify Panda3D that the primitive has now been
                # updated to contain new data! This will result in an assertion error
                # later on.

        self._verts_to_transf["vert"] = {}
        self._verts_to_transf["edge"] = {}
        self._verts_to_transf["poly"] = {}

    def __remove_polys(self, polys_to_remove):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        ordered_polys = self._ordered_polys

        poly_index = min(ordered_polys.index(poly) for poly in polys_to_remove)
        polys_to_offset = ordered_polys[poly_index:]

        row_ranges_to_delete = []
        vert_count = sum((poly.get_vertex_count() for poly in polys_to_remove))
        old_count = self._data_row_count
        count = old_count - vert_count

        for poly in polys_to_remove:
            poly_verts = poly.get_vertices()
            vert = poly_verts[0]
            row = vert.get_row_index()
            row_ranges_to_delete.append((row, len(poly_verts)))
            ordered_polys.remove(poly)

        row_index_offset = 0

        for poly in polys_to_offset:

            poly_verts = poly.get_vertices()

            if poly in polys_to_remove:
                row_index_offset -= len(poly_verts)
                continue

            for vert in poly_verts:
                vert.offset_row_index(row_index_offset)

        row_ranges_to_delete.sort(reverse=True)

        vertex_data_vert = self._vertex_data["vert"]
        vertex_data_edge = self._vertex_data["edge"]

        geom_node = self._toplvl_node
        vertex_data_top = geom_node.modify_geom(0).modify_vertex_data()

        vert_array = vertex_data_vert.modify_array(1)
        vert_handle = vert_array.modify_handle()
        vert_stride = vert_array.get_array_format().get_stride()
        edge_array = vertex_data_edge.modify_array(1)
        edge_handle = edge_array.modify_handle()
        edge_stride = edge_array.get_array_format().get_stride()

        poly_arrays = []
        poly_handles = []
        poly_strides = []

        for i in xrange(vertex_data_top.get_num_arrays()):
            poly_array = vertex_data_top.modify_array(i)
            poly_arrays.append(poly_array)
            poly_handles.append(poly_array.modify_handle())
            poly_strides.append(poly_array.get_array_format().get_stride())

        for start, size in row_ranges_to_delete:

            vert_handle.set_subdata(start * vert_stride, size * vert_stride, "")
            edge_handle.set_subdata((start + old_count) * edge_stride, size * edge_stride, "")
            edge_handle.set_subdata(start * edge_stride, size * edge_stride, "")

            for poly_handle, poly_stride in zip(poly_handles, poly_strides):
                poly_handle.set_subdata(start * poly_stride, size * poly_stride, "")

            old_count -= size

        self._data_row_count = count

    def __restore_polys(self, polys_to_restore):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        ordered_polys = self._ordered_polys
        vert_count = sum((poly.get_vertex_count() for poly in polys_to_restore))
        old_count = self._data_row_count
        count = old_count + vert_count

        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data_top.reserve_num_rows(count)
        row_index_offset = old_count

        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")
        pos_writer.set_row(row_index_offset)
        col_writer = GeomVertexWriter(vertex_data_top, "color")
        col_writer.set_row(row_index_offset)
        normal_writer = GeomVertexWriter(vertex_data_top, "normal")
        normal_writer.set_row(row_index_offset)
        tan_writer = GeomVertexWriter(vertex_data_top, "tangent")
        tan_writer.set_row(row_index_offset)
        bitan_writer = GeomVertexWriter(vertex_data_top, "binormal")
        bitan_writer.set_row(row_index_offset)

        pickable_type_id = PickableTypes.get_id("poly")

        for poly in polys_to_restore:

            ordered_polys.append(poly)
            picking_color = get_color_vec(poly.get_picking_color_id(), pickable_type_id)
            poly_verts = poly.get_vertices()

            for vert in poly_verts:
                vert.offset_row_index(row_index_offset)
                pos = vert.get_pos()
                pos_writer.add_data3f(pos)
                col_writer.add_data4f(picking_color)
                # TODO: move the next data updates to a later pending task (after
                # restoring the corresponding properties)
                normal = vert.get_normal()
                normal_writer.add_data3f(normal)
                tangent, bitangent = vert.get_tangent_space()
                tan_writer.add_data3f(tangent)
                bitan_writer.add_data3f(bitangent)

            row_index_offset += len(poly_verts)

        vertex_data_vert = self._vertex_data["vert"]
        vertex_data_vert.reserve_num_rows(count)
        vertex_data_vert.set_num_rows(count)
        vertex_data_tmp = GeomVertexData(vertex_data_vert)
        col_writer = GeomVertexWriter(vertex_data_tmp, "color")

        pickable_type_id = PickableTypes.get_id("vert")

        for poly in polys_to_restore:

            poly_verts = poly.get_vertices()
            row = poly_verts[0].get_row_index()
            col_writer.set_row(row)

            for vert in poly_verts:
                picking_color = get_color_vec(vert.get_picking_color_id(), pickable_type_id)
                col_writer.add_data4f(picking_color)

        vertex_data_vert.set_array(1, vertex_data_tmp.get_array(1))

        edges_to_restore = {}
        picking_colors1 = {}
        picking_colors2 = {}
        pickable_type_id = PickableTypes.get_id("edge")

        for poly in polys_to_restore:
            for edge in poly.get_edges():
                edges_to_restore[edge.get_picking_color_id()] = edge

        for picking_color_id, edge in edges_to_restore.iteritems():
            picking_color = get_color_vec(picking_color_id, pickable_type_id)
            row_index = verts[edge[0]].get_row_index()
            picking_colors1[row_index] = picking_color
            row_index = verts[edge[1]].get_row_index() + count
            picking_colors2[row_index] = picking_color

        vertex_data_edge = self._vertex_data["edge"]
        vertex_data_tmp = GeomVertexData(vertex_data_edge)
        vertex_data_tmp.set_num_rows(count)
        col_writer = GeomVertexWriter(vertex_data_tmp, "color")
        col_writer.set_row(old_count)

        for row_index in sorted(picking_colors1.iterkeys()):
            picking_color = picking_colors1[row_index]
            col_writer.add_data4f(picking_color)

        data = vertex_data_tmp.get_array(1).get_handle().get_data()

        vertex_data_tmp = GeomVertexData(vertex_data_edge)
        array = vertex_data_tmp.modify_array(1)
        stride = array.get_array_format().get_stride()
        array.modify_handle().set_subdata(0, old_count * stride, "")
        vertex_data_tmp.set_num_rows(count)
        col_writer = GeomVertexWriter(vertex_data_tmp, "color")
        col_writer.set_row(old_count)

        for row_index in sorted(picking_colors2.iterkeys()):
            picking_color = picking_colors2[row_index]
            col_writer.add_data4f(picking_color)

        data += vertex_data_tmp.get_array(1).get_handle().get_data()

        vertex_data_edge.set_num_rows(count * 2)
        vertex_data_edge.modify_array(1).modify_handle().set_data(data)

        self._data_row_count = count

        geom_node = self._toplvl_node

        # handle possible bug
        try:
            self._origin.node().set_bounds(geom_node.get_bounds())
        except:
            print "\n\n\n---------------------------------------------"
            print "---------- Could not set bounds! ------------"
            print "---------------------------------------------"

    def __finalize_subobj_restore(self):

        count = self._data_row_count
        ordered_polys = self._ordered_polys
        verts = self._subobjs["vert"]
        sel_state = self._subobj_sel_state
        sel_state["vert"]["unselected"] = range(count)
        sel_state_edge = sel_state["edge"]["unselected"]
        sel_state_poly = sel_state["poly"]["unselected"]

        vertex_data_vert = self._vertex_data["vert"]
        vertex_data_vert.set_num_rows(count)
        vertex_data_edge = self._vertex_data["edge"]
        vertex_data_edge.set_num_rows(count * 2)
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_num_rows(count)

        geoms = self._geoms

        geom_node = self._toplvl_node
        vertex_data_top = geom_node.get_geom(0).get_vertex_data()

        poly_arrays = []

        for i in xrange(vertex_data_top.get_num_arrays()):
            poly_arrays.append(vertex_data_top.get_array(i))

        pos_array = poly_arrays[0]
        vertex_data_vert.set_array(0, GeomVertexArrayData(pos_array))
        pos_data = pos_array.get_handle().get_data()
        array = GeomVertexArrayData(pos_array)
        array.modify_handle().set_data(pos_data * 2)
        vertex_data_edge.set_array(0, array)

        for i, poly_array in enumerate(poly_arrays):
            vertex_data_poly.set_array(i, GeomVertexArrayData(poly_array))

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(count * 2)
        tris_prim = GeomTriangles(Geom.UH_static)

        for poly in ordered_polys:

            for edge in poly.get_edges():
                row1, row2 = [verts[v_id].get_row_index() for v_id in edge]
                lines_prim.add_vertices(row1, row2 + count)
                sel_state_edge.append(row1)

            for vert_ids in poly:
                tris_prim.add_vertices(*[verts[v_id].get_row_index() for v_id in vert_ids])

            sel_state_poly.extend(poly[:])

        geom_node.modify_geom(0).set_primitive(0, tris_prim)

        geom_node = geoms["top"]["wire"].node()
        geom_node.modify_geom(0).set_primitive(0, lines_prim)

        geom_node = geoms["edge"]["unselected"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomLines(lines_prim))

        geom_node = geoms["poly"]["unselected"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomTriangles(tris_prim))

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.reserve_num_vertices(count)
        points_prim.add_next_vertices(count)
        geom_node = geoms["vert"]["unselected"].node()
        geom_node.modify_geom(0).set_primitive(0, GeomPoints(points_prim))

    def __restore_subobj_merge(self, time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = "subobj_merge"
        data = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)

        self._merged_verts, self._merged_edges = data
        merged_subobjs = set(self._merged_verts.values())
        merged_subobjs.update(self._merged_edges.values())

        for merged_subobj in merged_subobjs:
            merged_subobj.set_geom_data_object(self)
