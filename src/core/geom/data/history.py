from ...base import *


class GeomHistoryBase(BaseObject):

    def __init__(self):

        self._vert_normal_change = set()
        self._tri_change_all = False
        self._subobj_change = {"vert": {}, "edge": {}, "poly": {}}

    def get_data_to_store(self, event_type, prop_id="", info="", unique_id=False):

        data = {}
        unique_prop_ids = self._unique_prop_ids
        obj_id = self.get_toplevel_object().get_id()
        cur_time_id = Mgr.do("get_history_time")

        if event_type == "creation":

            data["geom_data"] = {"main": self}

            for prop_id in self._prop_ids:
                data.update(self.get_property_to_store(prop_id, event_type))

            prev_time_ids = (cur_time_id,)

            for subobj_type in ("vert", "edge", "poly"):

                subobjs = self._subobjs[subobj_type]

                for subobj in subobjs.itervalues():
                    subobj.set_creation_time(cur_time_id)

                pickled_objs = dict((s_id, cPickle.dumps(s, -1))
                                    for s_id, s in subobjs.iteritems())

                extra_data = {unique_prop_ids["%s__extra__" % subobj_type]: {"created": pickled_objs}}

                data[unique_prop_ids["%ss" % subobj_type]] = {"main": prev_time_ids, "extra": extra_data}

        elif event_type == "deletion":

            for prop_id in ("subobj_transform", "poly_tris", "uvs"):
                data.update(self.get_property_to_store(prop_id, event_type))

            for subobj_type in ("vert", "edge", "poly"):

                prev_time_ids = Mgr.do("load_last_from_history", obj_id, unique_prop_ids["%ss" % subobj_type])
                prev_time_ids += (cur_time_id,)

                subobjs = self._subobjs[subobj_type].iteritems()
                creation_times = dict((s_id, s.get_creation_time()) for s_id, s in subobjs)
                extra_data = {unique_prop_ids["%s__extra__" % subobj_type]: {"deleted": creation_times}}

                data[unique_prop_ids["%ss" % subobj_type]] = {"main": prev_time_ids, "extra": extra_data}

            toplvl_obj = self.get_toplevel_object()
            data["tangent space"] = {"main": toplvl_obj.get_property("tangent space")}

        elif event_type == "subobj_change":

            for prop_id in ("subobj_merge", "subobj_transform", "poly_tris", "uvs"):
                data.update(self.get_property_to_store(prop_id, event_type))

            subobj_change = self._subobj_change

            if "selection" in subobj_change:
                data.update(self.get_property_to_store("subobj_selection"))

            deleted_polys = subobj_change["poly"].get("deleted")

            if deleted_polys:

                poly_ids = [poly.get_id() for poly in deleted_polys]

                # check if the smoothing of this object has changed (by deleting
                # smoothed polys, which is equivalent to flattening them)
                if self.smooth_polygons(poly_ids, smooth=False, update_normals=False):
                    data.update(self.get_property_to_store("smoothing"))

                # TODO: check if all polys have been deleted; if so, this GeomDataObject
                # needs to be deleted itself also

            for subobj_type in ("vert", "edge", "poly"):

                prev_time_ids = Mgr.do("load_last_from_history", obj_id, unique_prop_ids["%ss" % subobj_type])
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

                extra_data = {unique_prop_ids["%s__extra__" % subobj_type]: data_to_store}
                data[unique_prop_ids["%ss" % subobj_type]] = {"main": prev_time_ids, "extra": extra_data}

            self._subobj_change = {"vert": {}, "edge": {}, "poly": {}}

        elif event_type == "prop_change":

            unique_prop_id = prop_id if unique_id else (unique_prop_ids[prop_id]
                                                        if prop_id in unique_prop_ids else None)

            if unique_prop_id in self.get_property_ids(unique=True):
                data = self.get_property_to_store(unique_prop_id, event_type, info, unique_id=True)

            self._uv_change = set()

        self._vert_normal_change = set()

        return data

    def get_property_to_store(self, prop_id, event_type="", info="", unique_id=False):

        data = {}
        unique_prop_ids = self._unique_prop_ids
        unique_prop_id = prop_id if unique_id else (unique_prop_ids[prop_id]
                                                    if prop_id in unique_prop_ids else None)

        if unique_prop_id == unique_prop_ids["subobj_merge"]:

            data[unique_prop_id] = {"main": (self._merged_verts, self._merged_edges)}

        elif unique_prop_id == unique_prop_ids["smoothing"]:

            data[unique_prop_id] = {"main": self._poly_smoothing}

        elif unique_prop_id == unique_prop_ids["subobj_selection"]:

            data[unique_prop_id] = {"main": self._selected_subobj_ids}

        elif unique_prop_id == unique_prop_ids["subobj_transform"]:

            obj_id = self.get_toplevel_object().get_id()
            subobj_lvl = GlobalData["active_obj_level"]
            pos_data = {"prev": {}, "pos": {}}
            extra_data = {unique_prop_ids["vert_pos__extra__"]: pos_data}
            cur_time_id = Mgr.do("get_history_time")
            prev_time_ids = Mgr.do("load_last_from_history", obj_id, unique_prop_id)
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

            data[unique_prop_id] = {"main": prev_time_ids, "extra": extra_data}

        elif unique_prop_id == unique_prop_ids["poly_tris"]:

            obj_id = self.get_toplevel_object().get_id()
            subobj_lvl = GlobalData["active_obj_level"]
            tri_data = {"prev": {}, "tri_data": {}}
            extra_data = {unique_prop_ids["tri__extra__"]: tri_data}
            cur_time_id = Mgr.do("get_history_time")
            prev_time_ids = Mgr.do("load_last_from_history", obj_id, unique_prop_id)
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

            data[unique_prop_id] = {"main": prev_time_ids, "extra": extra_data}

        elif unique_prop_id == unique_prop_ids["uvs"]:

            obj_id = self.get_toplevel_object().get_id()
            uv_data = {"prev": {}, "uvs": {}}
            extra_data = {unique_prop_ids["uv__extra__"]: uv_data}
            cur_time_id = Mgr.do("get_history_time")
            prev_time_ids = Mgr.do("load_last_from_history", obj_id, unique_prop_id)
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

            data[unique_prop_id] = {"main": prev_time_ids, "extra": extra_data}

        return data

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()

        if "self" in data_ids:

            cancellable = True if GlobalData["loading_scene"] else False

            for prop_id in self.get_property_ids(unique=True):
                self.__restore_property(prop_id, restore_type, old_time_id, new_time_id,
                                        cancellable)

            task = lambda: self.__recreate_geometry(old_time_id, new_time_id)
            task_id = "restore_geometry"
            descr = "Creating geometry..."
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id, gradual=True,
                             descr=descr, cancellable=cancellable)

            task = self.register
            task_id = "register_subobjs"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        else:

            for prop_id in self.get_property_ids(unique=True):
                if prop_id in data_ids:
                    self.__restore_property(prop_id, restore_type, old_time_id, new_time_id)

            if self._unique_prop_ids["polys"] in data_ids:

                task = lambda: self.__restore_geometry(old_time_id, new_time_id)
                task_id = "restore_geometry"
                descr = "Creating geometry..."
                PendingTasks.add(task, task_id, "object", id_prefix=obj_id, gradual=True,
                                 descr=descr)

                task = self.unregister
                task_id = "unregister_subobjs"
                PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

                task = self.register
                task_id = "register_subobjs"
                PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        task = self._origin.show
        task_id = "show_origin"
        PendingTasks.add(task, task_id, "object", id_prefix=obj_id, sort=100)

    def __restore_property(self, prop_id, restore_type, old_time_id, new_time_id,
                           cancellable=False):

        obj_id = self.get_toplevel_object().get_id()
        unique_prop_ids = self._unique_prop_ids

        if prop_id == unique_prop_ids["subobj_merge"]:

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
            descr = "Updating vertex normals..."
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id, gradual=True,
                             descr=descr, cancellable=cancellable)

        elif prop_id == unique_prop_ids["smoothing"]:

            task = lambda: self._restore_poly_smoothing(new_time_id)
            task_id = "smooth_polys"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = self._restore_vertex_normals
            task_id = "upd_vert_normals"
            descr = "Updating vertex normals..."
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id, gradual=True,
                             descr=descr, cancellable=cancellable)

        elif prop_id == unique_prop_ids["subobj_selection"]:

            task = lambda: self._restore_subobj_selection(new_time_id)
            task_id = "set_subobj_sel"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = lambda: Mgr.do("update_active_selection", restore=True)
            task_id = "upd_subobj_sel"
            PendingTasks.add(task, task_id, "object")

        elif prop_id == unique_prop_ids["subobj_transform"]:

            task = lambda: self._restore_subobj_transforms(old_time_id, new_time_id)
            task_id = "set_subobj_transf"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = self._restore_vertex_normals
            task_id = "upd_vert_normals"
            descr = "Updating vertex normals..."
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id, gradual=True,
                             descr=descr, cancellable=cancellable)

            self.get_toplevel_object().update_group_bbox()

        elif prop_id == unique_prop_ids["poly_tris"]:

            task = lambda: self._restore_poly_triangle_data(old_time_id, new_time_id)
            task_id = "set_poly_triangles"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

            task = self._restore_vertex_normals
            task_id = "upd_vert_normals"
            descr = "Updating vertex normals..."
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id, gradual=True,
                             descr=descr, cancellable=cancellable)

        elif prop_id == unique_prop_ids["uvs"]:

            task = lambda: self._restore_uvs(old_time_id, new_time_id)
            task_id = "set_uvs"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

    def __recreate_geometry(self, old_time_id, new_time_id):

        subobjs = self._subobjs

        for subobj_type in ("vert", "edge", "poly"):

            subobjs[subobj_type] = self.__load_subobjects(subobj_type, old_time_id, new_time_id)[1]

            for subobj in subobjs[subobj_type].itervalues():
                subobj.set_geom_data_object(self)

        self._ordered_polys = subobjs["poly"].values()
        poly_count = len(subobjs["poly"])
        merged_vert_count = len(self._merged_verts)
        progress_steps = poly_count // 50
        gradual = progress_steps > 50

        if gradual:
            GlobalData["progress_steps"] = progress_steps

        for step in self.create_geometry(gradual=gradual, restore=True):
            if gradual:
                yield True

        self.init_vertex_colors()

        yield False

    def __restore_geometry(self, old_time_id, new_time_id):

        subobjs = self._subobjs
        selected_subobj_ids = self._selected_subobj_ids

        subobjs_to_reg = self._subobjs_to_reg = {"vert": {}, "edge": {}, "poly": {}}
        subobjs_to_unreg = self._subobjs_to_unreg = {"vert": {}, "edge": {}, "poly": {}}
        subobj_change = {}

        for subobj_type in ("vert", "edge", "poly"):
            subobj_change[subobj_type] = self.__load_subobjects(subobj_type, old_time_id, new_time_id)

        polys_to_remove, polys_to_restore = subobj_change["poly"]
        verts_to_restore = subobj_change["vert"][1]

        progress_steps = 3 + len(polys_to_remove) // 50 + 3 * len(polys_to_restore) // 50
        progress_steps += (len(self._ordered_polys) - len(polys_to_remove) + len(polys_to_restore)) // 50
        gradual = progress_steps > 50

        if gradual:
            GlobalData["progress_steps"] = progress_steps

        self.__init_geometry_restore()

        if polys_to_remove:
            for step in self.__remove_polys(polys_to_remove.values()):
                if gradual:
                    yield True

        for vert_id in verts_to_restore:
            self._vert_normal_change.add(vert_id)

        for subobj_type in ("vert", "edge", "poly"):

            subobjs_to_remove, subobjs_to_restore = subobj_change[subobj_type]
            objs = subobjs[subobj_type]
            objs_to_unreg = subobjs_to_unreg[subobj_type]
            objs_to_reg = subobjs_to_reg[subobj_type]
            ids = selected_subobj_ids[subobj_type]

            for subobj_id, subobj in subobjs_to_remove.iteritems():

                del objs[subobj_id]
                objs_to_unreg[subobj_id] = subobj

                if subobj_id in ids:
                    ids.remove(subobj_id)

            if gradual:
                yield True

            for subobj_id, subobj in subobjs_to_restore.iteritems():
                objs[subobj_id] = subobj
                objs_to_reg[subobj_id] = subobj
                subobj.set_geom_data_object(self)

            if gradual:
                yield True

        if polys_to_restore:
            for step in self.__restore_polys(polys_to_restore.values()):
                if gradual:
                    yield True

        for step in self.__finalize_geometry_restore():
            if gradual:
                yield True

        for subobj_type in ("vert", "edge", "poly"):

            ids = selected_subobj_ids[subobj_type]
            objs = subobjs[subobj_type]

            if ids:

                selected_subobjs = (objs[subobj_id] for subobj_id in ids)
                self.update_selection(subobj_type, selected_subobjs, [], False)

                if gradual:
                    yield True

            selected_subobj_ids[subobj_type] = []

        yield False

    def __load_subobjects(self, subobj_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = self._unique_prop_ids["%ss" % subobj_type]

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
        subobjs_to_remove = {}
        registered_subobjs = self._subobjs[subobj_type]

        data_id = self._unique_prop_ids["%s__extra__" % subobj_type]

        # undo current subobject creation/deletion state

        for time_id in prev_time_ids:

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            created_subobjs = subobj_data.get("created", {})
            deleted_subobjs = subobj_data.get("deleted", {})

            for subobj_id in created_subobjs:
                if subobj_id in registered_subobjs:
                    subobjs_to_remove[subobj_id] = registered_subobjs[subobj_id]

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
                    subobjs_to_remove[subobj_id] = registered_subobjs[subobj_id]

            subobjs_to_recreate.update(created_subobjs)

        subobjs_to_restore = {}

        for subobj_id, pickled_subobj in subobjs_to_recreate.iteritems():
            subobj = cPickle.loads(pickled_subobj)
            subobjs_to_restore[subobj_id] = subobj

        return subobjs_to_remove, subobjs_to_restore

    def __init_geometry_restore(self):

        sel_data = self._poly_selection_data
        geoms = self._geoms
        geoms["top"].node().modify_geom(0).clear_primitives()
        geoms["poly"]["pickable"].node().modify_geom(0).clear_primitives()
        geoms["poly"]["unselected"].node().modify_geom(0).clear_primitives()

        for subobj_type in ("vert", "edge"):
            geoms[subobj_type]["pickable"].node().modify_geom(0).clear_primitives()
            geoms[subobj_type]["sel_state"].node().modify_geom(0).clear_primitives()

        for state in ("selected", "unselected"):
            sel_data[state] = []

        prim = geoms["poly"]["selected"].node().modify_geom(0).modify_primitive(0)
        prim.modify_vertices().modify_handle().set_data("")
        # NOTE: do *NOT* call prim.clearVertices(), as this will explicitly
        # remove all data from the primitive, and adding new data through
        # prim.modify_vertices().modify_handle().set_data(data) will not
        # internally notify Panda3D that the primitive has now been updated
        # to contain new data. This will result in an assertion error later on.

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
        poly_count = 0

        for poly in polys_to_remove:

            poly_verts = poly.get_vertices()
            vert = poly_verts[0]
            row = vert.get_row_index()
            row_ranges_to_delete.append((row, len(poly_verts)))
            ordered_polys.remove(poly)
            poly_count += 1

            if poly_count == 50:
                yield
                poly_count = 0

        row_index_offset = 0
        poly_count = 0

        for poly in polys_to_offset:

            poly_verts = poly.get_vertices()

            if poly in polys_to_remove:
                row_index_offset -= len(poly_verts)
                continue

            for vert in poly_verts:
                vert.offset_row_index(row_index_offset)

            poly_count += 1

            if poly_count == 50:
                yield
                poly_count = 0

        row_ranges_to_delete.sort(reverse=True)

        geoms = self._geoms
        vertex_data_vert = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_edge = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_poly_picking = self._vertex_data["poly_picking"]

        geom_node = self._toplvl_node
        vertex_data_top = geom_node.modify_geom(0).modify_vertex_data()

        vert_array = vertex_data_vert.modify_array(1)
        vert_handle = vert_array.modify_handle()
        vert_stride = vert_array.get_array_format().get_stride()
        edge_array = vertex_data_edge.modify_array(1)
        edge_handle = edge_array.modify_handle()
        edge_stride = edge_array.get_array_format().get_stride()
        picking_array = vertex_data_poly_picking.modify_array(1)
        picking_handle = picking_array.modify_handle()
        picking_stride = picking_array.get_array_format().get_stride()

        poly_arrays = []
        poly_handles = []
        poly_strides = []

        for i in range(vertex_data_top.get_num_arrays()):
            poly_array = vertex_data_top.modify_array(i)
            poly_arrays.append(poly_array)
            poly_handles.append(poly_array.modify_handle())
            poly_strides.append(poly_array.get_array_format().get_stride())

        for start, size in row_ranges_to_delete:

            vert_handle.set_subdata(start * vert_stride, size * vert_stride, "")
            edge_handle.set_subdata((start + old_count) * edge_stride, size * edge_stride, "")
            edge_handle.set_subdata(start * edge_stride, size * edge_stride, "")
            picking_handle.set_subdata(start * picking_stride, size * picking_stride, "")

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

        geoms = self._geoms

        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data_top.reserve_num_rows(count)
        vertex_data_poly_picking = self._vertex_data["poly_picking"]
        vertex_data_poly_picking.reserve_num_rows(count)
        row_index_offset = old_count

        pos_writer = GeomVertexWriter(vertex_data_top, "vertex")
        pos_writer.set_row(row_index_offset)
        col_writer = GeomVertexWriter(vertex_data_poly_picking, "color")
        col_writer.set_row(row_index_offset)

        pickable_type_id = PickableTypes.get_id("poly")
        poly_count = 0

        for poly in polys_to_restore:

            ordered_polys.append(poly)
            picking_color = get_color_vec(poly.get_picking_color_id(), pickable_type_id)
            poly_verts = poly.get_vertices()

            for vert in poly_verts:
                vert.offset_row_index(row_index_offset)
                pos = vert.get_initial_pos()
                pos_writer.add_data3f(pos)
                col_writer.add_data4f(picking_color)

            row_index_offset += len(poly_verts)
            poly_count += 1

            if poly_count == 50:
                yield
                poly_count = 0

        vertex_data_vert = geoms["vert"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_vert.reserve_num_rows(count)
        vertex_data_vert.set_num_rows(count)
        vertex_data_tmp = GeomVertexData(vertex_data_vert)
        col_writer = GeomVertexWriter(vertex_data_tmp, "color")

        pickable_type_id = PickableTypes.get_id("vert")
        poly_count = 0

        for poly in polys_to_restore:

            poly_verts = poly.get_vertices()
            row = poly_verts[0].get_row_index()
            col_writer.set_row(row)

            for vert in poly_verts:
                picking_color = get_color_vec(vert.get_picking_color_id(), pickable_type_id)
                col_writer.add_data4f(picking_color)

            poly_count += 1

            if poly_count == 50:
                yield
                poly_count = 0

        vertex_data_vert.set_array(1, vertex_data_tmp.get_array(1))

        edges_to_restore = {}
        picking_colors1 = {}
        picking_colors2 = {}
        pickable_type_id = PickableTypes.get_id("edge")
        poly_count = 0

        for poly in polys_to_restore:

            for edge in poly.get_edges():
                edges_to_restore[edge.get_picking_color_id()] = edge

            poly_count += 1

            if poly_count == 50:
                yield
                poly_count = 0

        for picking_color_id, edge in edges_to_restore.iteritems():
            picking_color = get_color_vec(picking_color_id, pickable_type_id)
            row_index = verts[edge[0]].get_row_index()
            picking_colors1[row_index] = picking_color
            row_index = verts[edge[1]].get_row_index() + count
            picking_colors2[row_index] = picking_color

        yield

        vertex_data_edge = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_tmp = GeomVertexData(vertex_data_edge)
        vertex_data_tmp.set_num_rows(count)
        col_writer = GeomVertexWriter(vertex_data_tmp, "color")
        col_writer.set_row(old_count)

        for row_index in sorted(picking_colors1.iterkeys()):
            picking_color = picking_colors1[row_index]
            col_writer.add_data4f(picking_color)

        yield

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

        yield

        data += vertex_data_tmp.get_array(1).get_handle().get_data()

        vertex_data_edge.set_num_rows(count * 2)
        vertex_data_edge.modify_array(1).modify_handle().set_data(data)

        self._data_row_count = count

    def __finalize_geometry_restore(self):

        count = self._data_row_count
        ordered_polys = self._ordered_polys
        verts = self._subobjs["vert"]
        sel_data = self._poly_selection_data["unselected"]

        geoms = self._geoms
        sel_colors = Mgr.get("subobj_selection_colors")

        pickable_vert_geom = geoms["vert"]["pickable"].node().modify_geom(0)
        pickable_edge_geom = geoms["edge"]["pickable"].node().modify_geom(0)
        pickable_poly_geom = geoms["poly"]["pickable"].node().modify_geom(0)
        vert_sel_state_geom = geoms["vert"]["sel_state"].node().modify_geom(0)
        edge_sel_state_geom = geoms["edge"]["sel_state"].node().modify_geom(0)
        poly_unselected_geom = geoms["poly"]["unselected"].node().modify_geom(0)
        vertex_data_vert = pickable_vert_geom.modify_vertex_data()
        vertex_data_vert.set_num_rows(count)
        vertex_data_edge = pickable_edge_geom.modify_vertex_data()
        vertex_data_edge.set_num_rows(count * 2)
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_num_rows(count)
        vertex_data_poly_picking = self._vertex_data["poly_picking"]

        geom_node = self._toplvl_node
        vertex_data_top = geom_node.get_geom(0).get_vertex_data()

        poly_arrays = []

        for i in range(vertex_data_top.get_num_arrays()):
            poly_arrays.append(vertex_data_top.get_array(i))

        pos_array = poly_arrays[0]
        vertex_data_vert.set_array(0, GeomVertexArrayData(pos_array))

        vertex_data_vert = vert_sel_state_geom.modify_vertex_data()
        vertex_data_vert.set_num_rows(count)
        vertex_data_vert.set_array(0, GeomVertexArrayData(pos_array))
        new_data = vertex_data_vert.set_color(sel_colors["vert"]["unselected"])
        vertex_data_vert.set_array(1, new_data.get_array(1))

        pos_data = pos_array.get_handle().get_data()
        array = GeomVertexArrayData(pos_array)
        array.modify_handle().set_data(pos_data * 2)
        vertex_data_edge.set_array(0, array)

        vertex_data_edge = edge_sel_state_geom.modify_vertex_data()
        vertex_data_edge.set_num_rows(count * 2)
        vertex_data_edge.set_array(0, GeomVertexArrayData(array))
        new_data = vertex_data_edge.set_color(sel_colors["edge"]["unselected"])
        vertex_data_edge.set_array(1, new_data.get_array(1))

        vertex_data_poly_picking.set_array(0, GeomVertexArrayData(pos_array))

        for i, poly_array in enumerate(poly_arrays):
            vertex_data_poly.set_array(i, GeomVertexArrayData(poly_array))

        lines_prim = GeomLines(Geom.UH_static)
        lines_prim.reserve_num_vertices(count * 2)
        tris_prim = GeomTriangles(Geom.UH_static)
        poly_count = 0

        for poly in ordered_polys:

            for edge in poly.get_edges():
                row1, row2 = [verts[v_id].get_row_index() for v_id in edge]
                lines_prim.add_vertices(row1, row2 + count)

            for vert_ids in poly:
                tris_prim.add_vertices(*[verts[v_id].get_row_index() for v_id in vert_ids])

            sel_data.extend(poly[:])
            poly_count += 1

            if poly_count == 50:
                yield
                poly_count = 0

        geom_node.modify_geom(0).add_primitive(tris_prim)

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.reserve_num_vertices(count)
        points_prim.add_next_vertices(count)
        pickable_vert_geom.add_primitive(GeomPoints(points_prim))
        vert_sel_state_geom.add_primitive(GeomPoints(points_prim))

        pickable_edge_geom.add_primitive(lines_prim)
        edge_sel_state_geom.add_primitive(GeomLines(lines_prim))

        pickable_poly_geom.add_primitive(GeomTriangles(tris_prim))
        poly_unselected_geom.add_primitive(GeomTriangles(tris_prim))

        self._origin.node().set_bounds(self._toplvl_node.get_bounds())

    def __restore_subobj_merge(self, time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = self._unique_prop_ids["subobj_merge"]
        data = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)

        self._merged_verts, self._merged_edges = data
        merged_subobjs = set(self._merged_verts.values())
        merged_subobjs.update(self._merged_edges.values())

        for merged_subobj in merged_subobjs:
            merged_subobj.set_geom_data_object(self)
