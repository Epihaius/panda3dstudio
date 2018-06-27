from ...base import *


class GeomHistoryBase(BaseObject):

    def __init__(self):

        self._subobj_change = {"vert": {}, "edge": {}, "poly": {}}

    def get_data_to_store(self, event_type="", prop_id="", info="", unique_id=False):

        data = {}
        unique_prop_ids = self._unique_prop_ids
        obj_id = self.get_toplevel_object().get_id()
        cur_time_id = Mgr.do("get_history_time")
        extra_normal_data = None
        extra_normal_lock_data = None

        if event_type == "creation":

            data["geom_data"] = {"main": self}

            for prop_id in self._prop_ids:
                data.update(self.get_property_to_store(prop_id, event_type))

            self._normal_change = set()

            prev_time_ids = (cur_time_id,)

            for subobj_type in ("vert", "edge", "poly"):

                subobjs = self._subobjs[subobj_type]

                for subobj in subobjs.values():
                    subobj.set_creation_time(cur_time_id)

                pickled_objs = dict((s_id, pickle.dumps(s, -1))
                                    for s_id, s in subobjs.items())

                extra_data = {unique_prop_ids["{}__extra__".format(subobj_type)]: {"created": pickled_objs}}

                data[unique_prop_ids["{}s".format(subobj_type)]] = {"main": prev_time_ids, "extra": extra_data}

        elif event_type == "deletion":

            for prop_id in ("subobj_transform", "poly_tris", "uvs", "normals", "normal_lock"):
                data.update(self.get_property_to_store(prop_id, event_type))

            for subobj_type in ("vert", "edge", "poly"):

                prev_time_ids = Mgr.do("load_last_from_history", obj_id, unique_prop_ids["{}s".format(subobj_type)])
                prev_time_ids += (cur_time_id,)

                subobjs = iter(self._subobjs[subobj_type].items())
                creation_times = dict((s_id, s.get_creation_time()) for s_id, s in subobjs)
                extra_data = {unique_prop_ids["{}__extra__".format(subobj_type)]: {"deleted": creation_times}}

                data[unique_prop_ids["{}s".format(subobj_type)]] = {"main": prev_time_ids, "extra": extra_data}

            toplvl_obj = self.get_toplevel_object()
            data["tangent space"] = {"main": toplvl_obj.get_property("tangent space")}

        elif event_type == "subobj_change":

            for prop_id in ("subobj_merge", "subobj_transform", "subobj_selection", "poly_tris", "uvs"):
                data.update(self.get_property_to_store(prop_id, event_type))

            subobj_change = self._subobj_change
            deleted_verts = subobj_change["vert"].get("deleted")

            if deleted_verts:
                normal_data = self.get_property_to_store("normals", event_type)
                data.update(normal_data)
                extra_normal_data = list(normal_data.values())[0]["extra"][unique_prop_ids["normal__extra__"]]
                normal_lock_data = self.get_property_to_store("normal_lock", event_type)
                data.update(normal_lock_data)
                extra_normal_lock_data = list(normal_lock_data.values())[0]["extra"][unique_prop_ids["normal_lock__extra__"]]

            # TODO: check if all polys have been deleted; if so, this GeomDataObject
            # needs to be deleted itself also

            for subobj_type in ("vert", "edge", "poly"):

                prev_time_ids = Mgr.do("load_last_from_history", obj_id, unique_prop_ids["{}s".format(subobj_type)])
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
                        pickled_objs[subobj.get_id()] = pickle.dumps(subobj, -1)

                    data_to_store["created"] = pickled_objs

                extra_data = {unique_prop_ids["{}__extra__".format(subobj_type)]: data_to_store}
                data[unique_prop_ids["{}s".format(subobj_type)]] = {"main": prev_time_ids, "extra": extra_data}

            self._subobj_change = {"vert": {}, "edge": {}, "poly": {}}

        elif event_type == "prop_change":

            unique_prop_id = prop_id if unique_id else (unique_prop_ids[prop_id]
                                                        if prop_id in unique_prop_ids else None)

            if unique_prop_id in self.get_property_ids(unique=True):
                data = self.get_property_to_store(unique_prop_id, event_type, info, unique_id=True)

        if self._normal_change:

            normal_data = self.get_property_to_store("normals", "prop_change")

            if extra_normal_data:
                extra_data = list(normal_data.values())[0]["extra"][unique_prop_ids["normal__extra__"]]
                extra_normal_data["prev"].update(extra_data["prev"])
                extra_normal_data["normals"].update(extra_data["normals"])
            else:
                data.update(normal_data)

        if self._normal_lock_change:

            normal_lock_data = self.get_property_to_store("normal_lock", "prop_change")

            if extra_normal_lock_data:
                extra_data = list(normal_lock_data.values())[0]["extra"][unique_prop_ids["normal_lock__extra__"]]
                extra_normal_lock_data["prev"].update(extra_data["prev"])
                extra_normal_lock_data["normals"].update(extra_data["normal_lock"])
            else:
                data.update(normal_lock_data)

        if self._normal_sharing_change:
            data.update(self.get_property_to_store("normal_sharing"))

        if self._poly_smoothing_change:
            data.update(self.get_property_to_store("smoothing"))

        return data

    def get_property_to_store(self, prop_id, event_type="", info="", unique_id=False):

        data = {}
        unique_prop_ids = self._unique_prop_ids
        unique_prop_id = prop_id if unique_id else (unique_prop_ids[prop_id]
                                                    if prop_id in unique_prop_ids else None)

        if unique_prop_id == unique_prop_ids["subobj_merge"]:

            data[unique_prop_id] = {"main": (self._merged_verts, self._merged_edges)}

        elif unique_prop_id == unique_prop_ids["uv_set_names"]:

            data[unique_prop_id] = {"main": self._uv_set_names}

        elif unique_prop_id == unique_prop_ids["normal_length"]:

            data[unique_prop_id] = {"main": self._normal_length}

        elif unique_prop_id == unique_prop_ids["normal_sharing"]:

            data[unique_prop_id] = {"main": self._shared_normals}
            self._normal_sharing_change = False

        elif unique_prop_id == unique_prop_ids["smoothing"]:

            data[unique_prop_id] = {"main": self._poly_smoothing}
            self._poly_smoothing_change = False

        elif unique_prop_id == unique_prop_ids["subobj_selection"]:

            sel_subobj_ids = copy.deepcopy(self._selected_subobj_ids)
            sel_subobj_ids.update(self._sel_subobj_ids_backup)
            data[unique_prop_id] = {"main": sel_subobj_ids}

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

                for vert_id, vert in verts.items():
                    pos = vert.get_pos()
                    pos_data["pos"][vert_id] = pos
                    vert.set_previous_property_time("transform", cur_time_id)

            elif event_type == "deletion":

                for vert_id, vert in verts.items():
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
                    xformed_verts = set(self._merged_verts.values())
                elif info == "check":
                    xformed_verts = set(self._transformed_verts)
                    self._transformed_verts = set()
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

                for poly_id, poly in polys.items():
                    tris = poly[:]
                    tri_data["tri_data"][poly_id] = tris
                    poly.set_previous_property_time("tri_data", cur_time_id)

            elif event_type == "deletion":

                for poly_id, poly in polys.items():
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

                for poly_id in self._tri_change:
                    poly = polys[poly_id]
                    tris = poly[:]
                    time_id = poly.get_previous_property_time("tri_data")
                    tri_data["tri_data"][poly_id] = tris
                    tri_data["prev"][poly_id] = time_id
                    poly.set_previous_property_time("tri_data", cur_time_id)

                self._tri_change = set()

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

                for vert_id, vert in verts.items():
                    uvs = vert.get_uvs()
                    uv_data["uvs"][vert_id] = uvs
                    vert.set_previous_property_time("uvs", cur_time_id)

            elif event_type == "deletion":

                for vert_id, vert in verts.items():
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

                self._uv_change = set()

            data[unique_prop_id] = {"main": prev_time_ids, "extra": extra_data}

        elif unique_prop_id == unique_prop_ids["normals"]:

            obj_id = self.get_toplevel_object().get_id()
            normal_data = {"prev": {}, "normals": {}}
            extra_data = {unique_prop_ids["normal__extra__"]: normal_data}
            cur_time_id = Mgr.do("get_history_time")
            prev_time_ids = Mgr.do("load_last_from_history", obj_id, unique_prop_id)
            verts = self._subobjs["vert"]

            if prev_time_ids:
                prev_time_ids += (cur_time_id,)
            else:
                prev_time_ids = (cur_time_id,)

            if event_type == "creation":

                for vert_id, vert in verts.items():
                    normal = vert.get_normal()
                    normal_data["normals"][vert_id] = normal
                    vert.set_previous_property_time("normal", cur_time_id)

            elif event_type == "deletion":

                for vert_id, vert in verts.items():
                    time_id = vert.get_previous_property_time("normal")
                    normal_data["prev"][vert_id] = time_id

            elif event_type == "subobj_change":

                created_verts = self._subobj_change["vert"].get("created", [])

                for vert in created_verts:
                    normal = vert.get_normal()
                    normal_data["normals"][vert.get_id()] = normal
                    vert.set_previous_property_time("normal", cur_time_id)

                deleted_verts = self._subobj_change["vert"].get("deleted", [])

                for vert in deleted_verts:
                    time_id = vert.get_previous_property_time("normal")
                    normal_data["prev"][vert.get_id()] = time_id

            elif event_type == "prop_change":

                if info == "all":
                    normal_change = verts
                else:
                    normal_change = self._normal_change

                for vert_id in normal_change:
                    vert = verts[vert_id]
                    normal = vert.get_normal()
                    time_id = vert.get_previous_property_time("normal")
                    normal_data["normals"][vert_id] = normal
                    normal_data["prev"][vert_id] = time_id
                    vert.set_previous_property_time("normal", cur_time_id)

                self._normal_change = set()

            data[unique_prop_id] = {"main": prev_time_ids, "extra": extra_data}

        elif unique_prop_id == unique_prop_ids["normal_lock"]:

            obj_id = self.get_toplevel_object().get_id()
            lock_data = {"prev": {}, "normal_lock": {}}
            extra_data = {unique_prop_ids["normal_lock__extra__"]: lock_data}
            cur_time_id = Mgr.do("get_history_time")
            prev_time_ids = Mgr.do("load_last_from_history", obj_id, unique_prop_id)
            verts = self._subobjs["vert"]

            if prev_time_ids:
                prev_time_ids += (cur_time_id,)
            else:
                prev_time_ids = (cur_time_id,)

            if event_type == "creation":

                for vert_id, vert in verts.items():
                    locked = vert.has_locked_normal()
                    lock_data["normal_lock"][vert_id] = locked
                    vert.set_previous_property_time("normal_lock", cur_time_id)

            elif event_type == "deletion":

                for vert_id, vert in verts.items():
                    time_id = vert.get_previous_property_time("normal_lock")
                    lock_data["prev"][vert_id] = time_id

            elif event_type == "subobj_change":

                created_verts = self._subobj_change["vert"].get("created", [])

                for vert in created_verts:
                    locked = vert.has_locked_normal()
                    lock_data["normal_lock"][vert.get_id()] = locked
                    vert.set_previous_property_time("normal_lock", cur_time_id)

                deleted_verts = self._subobj_change["vert"].get("deleted", [])

                for vert in deleted_verts:
                    time_id = vert.get_previous_property_time("normal_lock")
                    lock_data["prev"][vert.get_id()] = time_id

            elif event_type == "prop_change":

                if info == "all":
                    lock_change = verts
                else:
                    lock_change = self._normal_lock_change

                for vert_id in lock_change:
                    vert = verts[vert_id]
                    locked = vert.has_locked_normal()
                    time_id = vert.get_previous_property_time("normal_lock")
                    lock_data["normal_lock"][vert_id] = locked
                    lock_data["prev"][vert_id] = time_id
                    vert.set_previous_property_time("normal_lock", cur_time_id)

                self._normal_lock_change = set()

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

            self.__restore_tangent_space()

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

        elif prop_id == unique_prop_ids["uv_set_names"]:

            task = lambda: self._restore_uv_set_names(new_time_id)
            task_id = "set_uv_set_names"
            PendingTasks.add(task, task_id, "object", 0, id_prefix=obj_id)

        elif prop_id == unique_prop_ids["normal_length"]:

            task = lambda: self._restore_normal_length(new_time_id)
            task_id = "set_normal_length"
            sort = PendingTasks.get_sort("set_normals", "object") + 1
            PendingTasks.add(task, task_id, "object", sort, id_prefix=obj_id)

        elif prop_id == unique_prop_ids["normal_sharing"]:

            task = lambda: self._restore_normal_sharing(new_time_id)
            task_id = "share_normals"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        elif prop_id == unique_prop_ids["smoothing"]:

            task = lambda: self._restore_poly_smoothing(new_time_id)
            task_id = "set_poly_smoothing"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

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

            self.get_toplevel_object().update_group_bbox()

        elif prop_id == unique_prop_ids["poly_tris"]:

            task = lambda: self._restore_poly_triangle_data(old_time_id, new_time_id)
            task_id = "set_poly_triangles"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        elif prop_id == unique_prop_ids["uvs"]:

            task = lambda: self._restore_uvs(old_time_id, new_time_id)
            task_id = "set_uvs"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)
            self.__restore_tangent_space()

        elif prop_id == unique_prop_ids["normals"]:

            task = lambda: self._restore_vertex_normals(old_time_id, new_time_id)
            task_id = "set_normals"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)
            self.__restore_tangent_space()

        elif prop_id == unique_prop_ids["normal_lock"]:

            task = lambda: self._restore_normal_lock(old_time_id, new_time_id)
            task_id = "set_normal_lock"
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

    def __recreate_geometry(self, old_time_id, new_time_id):

        subobjs = self._subobjs

        for subobj_type in ("vert", "edge", "poly"):

            subobjs[subobj_type] = self.__load_subobjects(subobj_type, old_time_id, new_time_id)[1]

            for subobj in subobjs[subobj_type].values():
                subobj.set_geom_data_object(self)

        self._ordered_polys = list(subobjs["poly"].values())
        poly_count = len(subobjs["poly"])
        progress_steps = poly_count // 20
        gradual = progress_steps > 20

        if gradual:
            GlobalData["progress_steps"] = progress_steps

        for step in self.create_geometry(gradual=gradual, restore=True):
            if gradual:
                yield True

        self.init_picking_colors()

        if self._owner.has_vertex_colors():
            self.set_initial_vertex_colors()

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

        progress_steps = 3 + 2 * len(polys_to_remove) // 20 + 3 * len(polys_to_restore) // 20
        progress_steps += (len(self._ordered_polys) - len(polys_to_remove) + len(polys_to_restore)) // 20
        gradual = progress_steps > 50

        if gradual:
            GlobalData["progress_steps"] = progress_steps

        self.__init_geometry_restore()

        if polys_to_remove:
            for step in self.__remove_polys(list(polys_to_remove.values())):
                if gradual:
                    yield True

        for subobj_type in ("vert", "edge", "poly"):

            subobjs_to_remove, subobjs_to_restore = subobj_change[subobj_type]
            objs = subobjs[subobj_type]
            objs_to_unreg = subobjs_to_unreg[subobj_type]
            objs_to_reg = subobjs_to_reg[subobj_type]

            for subobj_id, subobj in subobjs_to_remove.items():
                del objs[subobj_id]
                objs_to_unreg[subobj_id] = subobj

            if gradual:
                yield True

            for subobj_id, subobj in subobjs_to_restore.items():
                objs[subobj_id] = subobj
                objs_to_reg[subobj_id] = subobj
                subobj.set_geom_data_object(self)

            if gradual:
                yield True

        if polys_to_restore:
            for step in self.__restore_polys(list(polys_to_restore.values())):
                if gradual:
                    yield True

        for step in self.__finalize_geometry_restore():
            if gradual:
                yield True

        for subobj_type in ("vert", "edge", "poly", "normal"):
            selected_subobj_ids[subobj_type] = []

        yield False

    def __load_subobjects(self, subobj_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = self._unique_prop_ids["{}s".format(subobj_type)]

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

        data_id = self._unique_prop_ids["{}__extra__".format(subobj_type)]

        # undo current subobject creation/deletion state

        for time_id in prev_time_ids:

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            created_subobjs = subobj_data.get("created", {})
            deleted_subobjs = subobj_data.get("deleted", {})

            for subobj_id in created_subobjs:
                if subobj_id in registered_subobjs:
                    subobjs_to_remove[subobj_id] = registered_subobjs[subobj_id]

            data_to_load = {}

            for subobj_id, time_id2 in deleted_subobjs.items():
                if time_id2 in common_time_ids:
                    data_to_load.setdefault(time_id2, []).append(subobj_id)

            for time_id2, subobj_ids in data_to_load.items():

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

        for subobj_id, pickled_subobj in subobjs_to_recreate.items():
            subobj = pickle.loads(pickled_subobj)
            subobjs_to_restore[subobj_id] = subobj

        return subobjs_to_remove, subobjs_to_restore

    def __init_geometry_restore(self):

        sel_data = self._poly_selection_data
        geoms = self._geoms
        geoms["top"].node().modify_geom(0).clear_primitives()
        geoms["poly"]["pickable"].node().modify_geom(0).clear_primitives()
        geoms["poly"]["unselected"].node().modify_geom(0).clear_primitives()

        for subobj_type in ("vert", "edge", "normal"):
            geoms[subobj_type]["pickable"].node().modify_geom(0).clear_primitives()
            geoms[subobj_type]["sel_state"].node().modify_geom(0).clear_primitives()

        for state in ("selected", "unselected"):
            sel_data[state] = []

        prim = geoms["poly"]["selected"].node().modify_geom(0).modify_primitive(0)
        prim.modify_vertices().modify_handle().set_num_rows(0)
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

            if poly_count == 20:
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

            if poly_count == 20:
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
        vert_stride = vert_array.array_format.get_stride()
        edge_array = vertex_data_edge.modify_array(1)
        edge_handle = edge_array.modify_handle()
        edge_stride = edge_array.array_format.get_stride()
        picking_array = vertex_data_poly_picking.modify_array(1)
        picking_handle = picking_array.modify_handle()
        picking_stride = picking_array.array_format.get_stride()

        poly_handles = []
        poly_strides = []

        for i in range(vertex_data_top.get_num_arrays()):
            poly_array = vertex_data_top.modify_array(i)
            poly_handles.append(poly_array.modify_handle())
            poly_strides.append(poly_array.array_format.get_stride())

        for start, size in row_ranges_to_delete:

            vert_handle.set_subdata(start * vert_stride, size * vert_stride, bytes())
            edge_handle.set_subdata((start + old_count) * edge_stride, size * edge_stride, bytes())
            edge_handle.set_subdata(start * edge_stride, size * edge_stride, bytes())
            picking_handle.set_subdata(start * picking_stride, size * picking_stride, bytes())

            for poly_handle, poly_stride in zip(poly_handles, poly_strides):
                poly_handle.set_subdata(start * poly_stride, size * poly_stride, bytes())

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

            if poly_count == 20:
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

            if poly_count == 20:
                yield
                poly_count = 0

        col_array = vertex_data_tmp.get_array(1)
        vertex_data_vert.set_array(1, col_array)

        vertex_data_normal = geoms["normal"]["pickable"].node().modify_geom(0).modify_vertex_data()
        vertex_data_normal.reserve_num_rows(count)
        vertex_data_normal.set_num_rows(count)
        vertex_data_normal.set_array(1, GeomVertexArrayData(col_array))

        edges_to_restore = {}
        picking_colors1 = {}
        picking_colors2 = {}
        pickable_type_id = PickableTypes.get_id("edge")
        poly_count = 0

        for poly in polys_to_restore:

            for edge in poly.get_edges():
                edges_to_restore[edge.get_picking_color_id()] = edge

            poly_count += 1

            if poly_count == 20:
                yield
                poly_count = 0

        for picking_color_id, edge in edges_to_restore.items():
            picking_color = get_color_vec(picking_color_id, pickable_type_id)
            row_index = verts[edge[0]].get_row_index()
            picking_colors1[row_index] = picking_color
            row_index = verts[edge[1]].get_row_index() + count
            picking_colors2[row_index] = picking_color

        yield

        vertex_data_edge = geoms["edge"]["pickable"].node().modify_geom(0).modify_vertex_data()
        col_array = vertex_data_edge.get_array(1)
        col_array_tmp1 = GeomVertexArrayData(col_array)
        col_array_tmp1.set_num_rows(count)
        col_writer = GeomVertexWriter(col_array_tmp1, 0)
        col_writer.set_row(old_count)

        for row_index in sorted(picking_colors1):
            picking_color = picking_colors1[row_index]
            col_writer.add_data4f(picking_color)

        yield

        col_array_tmp2 = GeomVertexArrayData(col_array.array_format, col_array.usage_hint)
        col_array_tmp2.unclean_set_num_rows(count)
        stride = col_array_tmp2.array_format.get_stride()
        # the second temporary array contains only the second half of the original vertex data
        # (to be extended with [count - old_count] rows)
        size = old_count * stride
        from_handle = col_array.get_handle()
        to_handle = col_array_tmp2.modify_handle()
        to_handle.copy_subdata_from(0, size, from_handle, size, size)
        col_writer = GeomVertexWriter(col_array_tmp2, 0)
        col_writer.set_row(old_count)

        for row_index in sorted(picking_colors2):
            picking_color = picking_colors2[row_index]
            col_writer.add_data4f(picking_color)

        yield

        vertex_data_edge.set_num_rows(count * 2)
        col_array = vertex_data_edge.modify_array(1)
        size = col_array_tmp1.data_size_bytes
        to_handle = col_array.modify_handle()
        from_handle = col_array_tmp1.get_handle()
        to_handle.copy_subdata_from(0, size, from_handle, 0, size)
        from_handle = col_array_tmp2.get_handle()
        to_handle.copy_subdata_from(size, size, from_handle, 0, size)

        self._data_row_count = count

        self.__restore_tangent_space()

    def __finalize_geometry_restore(self):

        count = self._data_row_count
        ordered_polys = self._ordered_polys
        verts = self._subobjs["vert"]
        sel_data = self._poly_selection_data["unselected"]

        geoms = self._geoms
        sel_colors = Mgr.get("subobj_selection_colors")

        vert_picking_geom = geoms["vert"]["pickable"].node().modify_geom(0)
        edge_picking_geom = geoms["edge"]["pickable"].node().modify_geom(0)
        poly_picking_geom = geoms["poly"]["pickable"].node().modify_geom(0)
        normal_picking_geom = geoms["normal"]["pickable"].node().modify_geom(0)
        vert_sel_state_geom = geoms["vert"]["sel_state"].node().modify_geom(0)
        edge_sel_state_geom = geoms["edge"]["sel_state"].node().modify_geom(0)
        normal_sel_state_geom = geoms["normal"]["sel_state"].node().modify_geom(0)
        poly_unselected_geom = geoms["poly"]["unselected"].node().modify_geom(0)
        vertex_data_vert = vert_picking_geom.modify_vertex_data()
        vertex_data_vert.set_num_rows(count)
        vertex_data_normal = normal_picking_geom.modify_vertex_data()
        vertex_data_normal.set_num_rows(count)
        vertex_data_edge = edge_picking_geom.modify_vertex_data()
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
        vertex_data_normal.set_array(0, GeomVertexArrayData(pos_array))
        vertex_data_normal.set_array(2, GeomVertexArrayData(poly_arrays[2]))

        vertex_data_vert = vert_sel_state_geom.modify_vertex_data()
        vertex_data_vert.set_num_rows(count)
        vertex_data_vert.set_array(0, GeomVertexArrayData(pos_array))
        new_data = vertex_data_vert.set_color(sel_colors["vert"]["unselected"])
        vertex_data_vert.set_array(1, new_data.get_array(1))

        vertex_data_normal = normal_sel_state_geom.modify_vertex_data()
        vertex_data_normal.set_num_rows(count)
        vertex_data_normal.set_array(0, GeomVertexArrayData(pos_array))
        new_data = vertex_data_normal.set_color(sel_colors["normal"]["unselected"])
        vertex_data_normal.set_array(1, new_data.get_array(1))
        vertex_data_normal.set_array(2, GeomVertexArrayData(poly_arrays[2]))

        size = pos_array.data_size_bytes
        pos_array_edge = GeomVertexArrayData(pos_array.array_format, pos_array.usage_hint)
        pos_array_edge.unclean_set_num_rows(pos_array.get_num_rows() * 2)

        from_handle = pos_array.get_handle()
        to_handle = pos_array_edge.modify_handle()
        to_handle.copy_subdata_from(0, size, from_handle, 0, size)
        to_handle.copy_subdata_from(size, size, from_handle, 0, size)
        vertex_data_edge.set_array(0, pos_array_edge)

        vertex_data_edge = edge_sel_state_geom.modify_vertex_data()
        vertex_data_edge.set_num_rows(count * 2)
        vertex_data_edge.set_array(0, GeomVertexArrayData(pos_array_edge))
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

            sel_data.extend(poly)
            poly_count += 1

            if poly_count == 20:
                yield
                poly_count = 0

        geom_node.modify_geom(0).add_primitive(tris_prim)

        points_prim = GeomPoints(Geom.UH_static)
        points_prim.reserve_num_vertices(count)
        points_prim.add_next_vertices(count)
        vert_picking_geom.add_primitive(GeomPoints(points_prim))
        vert_sel_state_geom.add_primitive(GeomPoints(points_prim))
        normal_picking_geom.add_primitive(GeomPoints(points_prim))
        normal_sel_state_geom.add_primitive(GeomPoints(points_prim))

        edge_picking_geom.add_primitive(lines_prim)
        edge_sel_state_geom.add_primitive(GeomLines(lines_prim))

        poly_picking_geom.add_primitive(GeomTriangles(tris_prim))
        poly_unselected_geom.add_primitive(GeomTriangles(tris_prim))

        self._origin.node().set_bounds(self._toplvl_node.get_bounds())

    def __restore_subobj_merge(self, time_id):

        obj_id = self.get_toplevel_object().get_id()
        prop_id = self._unique_prop_ids["subobj_merge"]
        data = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)

        self._merged_verts, self._merged_edges = data
        merged_subobjs = set(self._merged_verts.values())
        merged_subobjs.update(iter(self._merged_edges.values()))

        for merged_subobj in merged_subobjs:
            merged_subobj.set_geom_data_object(self)

    def __restore_tangent_space(self):

        def task():

            model = self.get_toplevel_object()

            if model.has_tangent_space():
                model.update_tangent_space()

        model = self.get_toplevel_object()
        task_id = "update_tangent_space"
        PendingTasks.add(task, task_id, "object", id_prefix=model.get_id())
