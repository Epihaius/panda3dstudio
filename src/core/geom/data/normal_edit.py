from ...base import *


class SharedNormal:

    __slots__ = ("type", "full_type", "_ids", "geom_data_obj")

    def __getstate__(self):

        state = {
            "_ids": self._ids
            # leave out the GeomDataObject, as it is pickled separately
        }

        return state

    def __setstate__(self, state):

        self.type = "normal"
        self.full_type = "shared_normal"
        self.geom_data_obj = None
        self._ids = state["_ids"]

    def __init__(self, geom_data_obj, vert_ids=None):

        self.type = "normal"
        self.full_type = "shared_normal"
        self.geom_data_obj = geom_data_obj
        # the IDs associated with this SharedNormal are actually Vertex IDs,
        # since there is one normal for every vertex
        self._ids = set() if vert_ids is None else set(vert_ids)

    def __deepcopy__(self, memo):

        return SharedNormal(self.geom_data_obj, self._ids)

    def __hash__(self):

        return hash(tuple(sorted(self._ids)))

    def __eq__(self, other):

        return self._ids == set(other)

    def __ne__(self, other):

        return not self._ids == set(other)

    def __getitem__(self, index):

        try:
            return list(self._ids)[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __iter__(self):

        return iter(self._ids)

    def __len__(self):

        return len(self._ids)

    @property
    def id(self):

        vert = self.geom_data_obj.get_subobject("vert", sorted(self._ids)[0])

        return vert.id if vert else None

    @property
    def picking_color_id(self):

        vert = self.geom_data_obj.get_subobject("vert", self[0])

        return vert.picking_color_id if vert else None

    def copy(self):

        return SharedNormal(self.geom_data_obj, self._ids)

    def add(self, vert_id):

        self._ids.add(vert_id)

    def discard(self, vert_id):

        self._ids.discard(vert_id)

    def update(self, vert_ids):

        self._ids.update(vert_ids)

    def extend(self, vert_ids):

        self._ids.update(vert_ids)

    def difference(self, vert_ids):

        return SharedNormal(self.geom_data_obj, self._ids.difference(vert_ids))

    def difference_update(self, vert_ids):

        self._ids.difference_update(vert_ids)

    def intersection(self, vert_ids):

        return SharedNormal(self.geom_data_obj, self._ids.intersection(vert_ids))

    def intersection_update(self, vert_ids):

        self._ids.intersection_update(vert_ids)

    def pop(self):

        return self._ids.pop()

    def issubset(self, vert_ids):

        return self._ids.issubset(vert_ids)

    @property
    def vertex_ids(self):

        return list(self._ids)

    @property
    def edge_ids(self):

        return [e_id for v in self.vertices for e_id in v.edge_ids]

    @property
    def polygon_ids(self):

        return [v.polygon_id for v in self.vertices]

    @property
    def vertices(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        return [verts[v_id] for v_id in self._ids]

    @property
    def edges(self):

        edges = self.geom_data_obj.get_subobjects("edge")

        return [edges[e_id] for e_id in self.edge_ids]

    @property
    def polygons(self):

        polys = self.geom_data_obj.get_subobjects("poly")

        return [polys[p_id] for p_id in self.polygon_ids]

    @property
    def connected_verts(self):

        verts = self.geom_data_obj.get_subobjects("vert")
        merged_verts = self.geom_data_obj.merged_verts

        return set(verts[v_id] for v_id in merged_verts[list(self._ids)[0]])

    @property
    def connected_edges(self):

        edges = self.geom_data_obj.get_subobjects("edge")

        return set(edges[e_id] for vert in self.connected_verts for e_id in vert.edge_ids)

    @property
    def connected_polys(self):

        polys = self.geom_data_obj.get_subobjects("poly")

        return set(polys[vert.polygon_id] for vert in self.connected_verts)

    def get_connected_subobjs(self, subobj_type):

        if subobj_type == "vert":
            return self.connected_verts
        elif subobj_type == "edge":
            return self.connected_edges
        elif subobj_type == "poly":
            return self.connected_polys

    @property
    def special_selection(self):

        return [self]

    @property
    def row_indices(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        return [verts[v_id].row_index for v_id in self._ids]

    def get_toplevel_object(self, get_group=False):

        return self.geom_data_obj.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def get_hpr(self, ref_node):

        geom_data_obj = self.geom_data_obj
        vert = geom_data_obj.get_subobject("vert", self[0])
        normal = vert.normal
        sign = -1. if geom_data_obj.owner.has_inverted_geometry() else 1.
        origin = geom_data_obj.origin
        normal = V3D(ref_node.get_relative_vector(origin, normal * sign))

        return normal.get_hpr()

    def get_center_pos(self, ref_node=None):

        vert = self.geom_data_obj.get_subobject("vert", self[0])

        return vert.get_pos(ref_node)

    def get_point_at_screen_pos(self, screen_pos):

        vert = self.geom_data_obj.get_subobject("vert", self[0])

        return vert.get_point_at_screen_pos(screen_pos)


class NormalEditMixin:
    """ GeomDataObject class mix-in """

    def __init__(self):

        self.shared_normals = {}
        self.locked_normals = set()
        self._normal_sharing_change = False
        self._normal_lock_change = set()
        self._normal_change = set()
        self._normal_length = 1.

    def _reset_normal_sharing(self, share=False):

        self.shared_normals = shared_normals = {}
        self._normal_sharing_change = True

        for merged_vert in set(self.merged_verts.values()):

            vert_ids = merged_vert[:]

            while vert_ids:

                vert_id = vert_ids.pop()
                shared_normal = SharedNormal(self, [vert_id])
                shared_normals[vert_id] = shared_normal

                if share:
                    for other_vert_id in vert_ids[:]:
                        shared_normal.add(other_vert_id)
                        shared_normals[other_vert_id] = shared_normal
                        vert_ids.remove(other_vert_id)

    def init_normal_sharing(self, share=True):
        """ Derive normal sharing from initial vertex normals """

        if not share:
            self._reset_normal_sharing()
            return

        verts = self._subobjs["vert"]
        shared_normals = self.shared_normals

        for merged_vert in set(self.merged_verts.values()):

            vert_ids = merged_vert[:]

            while vert_ids:

                vert_id = vert_ids.pop()
                shared_normal = SharedNormal(self, [vert_id])
                shared_normals[vert_id] = shared_normal
                vert = verts[vert_id]
                normal = vert.normal

                for other_vert_id in vert_ids[:]:

                    other_vert = verts[other_vert_id]

                    if other_vert.normal == normal:
                        shared_normal.add(other_vert_id)
                        shared_normals[other_vert_id] = shared_normal
                        vert_ids.remove(other_vert_id)

    def update_normal_sharing(self, merged_verts, from_smoothing_groups=False,
                              update_selection=True):
        """
        Call this method after splitting merged vertices to keep normal sharing
        limited to vertices that are merged together, or after merging vertices
        to derive normal sharing from smoothing groups.

        """

        verts = self._subobjs["vert"]
        shared_normals = self.shared_normals
        change = False

        if from_smoothing_groups:

            poly_smoothing = self._poly_smoothing
            selection_change = False

            if update_selection:
                selected_normal_ids = self._selected_subobj_ids["normal"]

            for merged_vert in merged_verts:

                vert_ids_by_smoothing = {}

                for vert_id in merged_vert:

                    vert = verts[vert_id]
                    poly_id = vert.polygon_id
                    smoothing = poly_smoothing.get(poly_id)

                    if smoothing:

                        smoothing_grp_orig = smoothing.pop()
                        smoothing_grp = smoothing_grp_orig.copy()

                        for other_smoothing_grp in smoothing:
                            smoothing_grp.update(other_smoothing_grp)

                        smoothing.append(smoothing_grp_orig)

                    else:

                        smoothing_grp = None

                    smoothing_grps = list(vert_ids_by_smoothing)

                    if smoothing_grp in smoothing_grps:
                        index = smoothing_grps.index(smoothing_grp)
                        smoothing_grp = smoothing_grps[index]
                        vert_ids_by_smoothing[smoothing_grp].append(vert_id)
                    else:
                        vert_ids_by_smoothing[smoothing_grp] = [vert_id]

                for smoothing_grp, vert_ids in vert_ids_by_smoothing.items():

                    if smoothing_grp:

                        if shared_normals[vert_ids[0]] != vert_ids:

                            if update_selection:

                                id_set = set(vert_ids)

                                if not (id_set.isdisjoint(selected_normal_ids)
                                        or id_set.issubset(selected_normal_ids)):
                                    id_set.difference_update(selected_normal_ids)
                                    tmp_shared_normal = SharedNormal(self, id_set)
                                    normal_id = tmp_shared_normal.id
                                    shared_normals[normal_id] = tmp_shared_normal
                                    self.update_selection("normal", [tmp_shared_normal], [])
                                    selection_change = True

                            shared_normal = SharedNormal(self, vert_ids)

                            for vert_id in vert_ids:
                                shared_normals[vert_id] = shared_normal

                            change = True

                    else:

                        for vert_id in vert_ids:
                            if shared_normals[vert_id] != [vert_id]:
                                shared_normals[vert_id] = SharedNormal(self, [vert_id])
                                change = True

            self._normal_sharing_change = change

            return selection_change

        for merged_vert in merged_verts:

            # Compare merged vert IDs with shared normal IDs.

            shared_normals_tmp = []
            vert_ids = set(merged_vert)

            for vert_id in merged_vert:

                shared_normal = shared_normals[vert_id]

                if shared_normal not in shared_normals_tmp:
                    shared_normals_tmp.append(shared_normal)

            for shared_normal in shared_normals_tmp:

                if not shared_normal.issubset(vert_ids):

                    change = True
                    new_shared_normal = shared_normal.difference(vert_ids)
                    shared_normal.intersection_update(vert_ids)

                    for vert_id in new_shared_normal.copy():
                        # if this method is called after deleting polygons, their
                        # vertex IDs have to be removed from normal sharing
                        if vert_id in verts:
                            shared_normals[vert_id] = new_shared_normal
                        else:
                            new_shared_normal.discard(vert_id)
                            del shared_normals[vert_id]

        # if this method is called after deleting polygons, their vertex IDs have
        # to be removed from normal sharing
        for vert_id in set(shared_normals).difference(verts):
            del shared_normals[vert_id]
            change = True

        self._normal_sharing_change = change

    def invert_geometry(self, invert=True, delay=True):

        def task():

            origin = self.origin

            if not origin:
                return

            if invert:
                state = origin.get_state()
                cull_attr = CullFaceAttrib.make_reverse()
                state = state.add_attrib(cull_attr)
                origin.set_state(state)
            else:
                origin.clear_two_sided()

            node = self._toplvl_node
            geom = node.modify_geom(0)
            vertex_data = geom.get_vertex_data().reverse_normals()
            geom.set_vertex_data(vertex_data)
            normal_array = GeomVertexArrayData(vertex_data.get_array(2))
            self._vertex_data["poly"].set_array(2, normal_array)
            self.owner.set_inverted_geometry(invert)

            for geom_type in ("pickable", "sel_state"):
                geom = self._geoms["normal"][geom_type].node().modify_geom(0)
                vertex_data = geom.modify_vertex_data()
                vertex_data.set_array(2, normal_array)

            if GD["active_obj_level"] == "normal":
                Mgr.get("selection").update_transform_values()

        if delay:
            task_id = "invert_geometry"
            obj_id = self.toplevel_obj.id
            PendingTasks.add(task, task_id, "object", id_prefix=obj_id)
        else:
            task()

    def has_inverted_geometry(self):

        return self.owner.has_inverted_geometry()

    def unify_normals(self, unify=True):

        sel_ids = set(self._selected_subobj_ids["normal"])

        if len(sel_ids) < 2:
            return False

        shared_normals = self.shared_normals
        merged_verts = self.merged_verts
        merged_verts_to_update = set()
        change = False

        if unify:

            while sel_ids:

                vert_id = sel_ids.pop()
                normal = shared_normals[vert_id]
                merged_vert = merged_verts[vert_id]

                for v_id in normal:
                    sel_ids.discard(v_id)

                for other_vert_id in sel_ids.copy():

                    if other_vert_id in merged_vert:

                        other_normal = shared_normals[other_vert_id]
                        normal.update(other_normal)

                        for v_id in other_normal:
                            sel_ids.discard(v_id)
                            shared_normals[v_id] = normal

                        merged_verts_to_update.add(merged_vert)
                        change = True

        else:

            while sel_ids:

                vert_id = sel_ids.pop()
                normal = shared_normals[vert_id]

                if len(normal) == 1:
                    continue

                merged_vert = merged_verts[vert_id]
                merged_verts_to_update.add(merged_vert)

                for v_id in normal:
                    sel_ids.discard(v_id)
                    shared_normals[v_id] = SharedNormal(self, [v_id])

                change = True

        if change:
            self.update_vertex_normals(merged_verts_to_update)
            self._normal_sharing_change = True

        return change

    def lock_normals(self, lock=True, normal_ids=None):

        if normal_ids is None:
            sel_ids = set(self._selected_subobj_ids["normal"])
        else:
            sel_ids = normal_ids

        if not sel_ids:
            return False

        verts = self._subobjs["vert"]
        shared_normals = self.shared_normals
        locked_normals = self.locked_normals
        merged_verts = self.merged_verts
        merged_verts_to_update = set()
        lock_change = self._normal_lock_change
        change = False

        while sel_ids:

            vert_id = sel_ids.pop()
            normal = shared_normals[vert_id]
            merged_vert = merged_verts[vert_id]

            for v_id in normal:

                sel_ids.discard(v_id)

                if verts[v_id].lock_normal(lock):

                    if lock:
                        locked_normals.add(v_id)
                    else:
                        locked_normals.discard(v_id)
                        merged_verts_to_update.add(merged_vert)

                    lock_change.add(v_id)
                    change = True

        if merged_verts_to_update:
            self.update_vertex_normals(merged_verts_to_update)

        locked_normal_ids = list(lock_change) if lock else []
        unlocked_normal_ids = [] if lock else list(lock_change)
        self.update_locked_normal_selection(None, None, locked_normal_ids, unlocked_normal_ids)

        return change

    def get_vertex_normals(self):

        verts = self._subobjs["vert"]
        normals = {}

        for vert_id, vert in verts.items():
            normals[vert_id] = vert.normal

        return normals

    def get_shared_normal(self, normal_id):

        return self.shared_normals.get(normal_id)

    def update_vertex_normals(self, merged_verts=None, update_tangent_space=True):
        """ Update the normals of the given merged vertices """

        if merged_verts is None:
            merged_verts = set(self.merged_verts.values())

        verts = self._subobjs["vert"]
        polys = self._subobjs["poly"]

        shared_normals = self.shared_normals
        verts_to_process = set(v_id for merged_vert in merged_verts for v_id in merged_vert)
        locked_normals = set(v_id for v_id in verts_to_process if verts[v_id].has_locked_normal())
        verts_to_process.difference_update(locked_normals)

        if not verts_to_process:
            return

        self._normal_change.update(verts_to_process)

        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        normal_writer = GeomVertexWriter(vertex_data_top, "normal")
        sign = -1. if self.owner.has_inverted_geometry() else 1.
        shared_normals_tmp = [s.difference(locked_normals) for s in
                              set(shared_normals[v_id] for v_id in verts_to_process)]

        for shared_normal in shared_normals_tmp:

            vert = verts[shared_normal.pop()]
            verts_to_update = [vert]
            poly = polys[vert.polygon_id]
            normal = Vec3(poly.normal)

            for vert_id in shared_normal:

                vert = verts[vert_id]
                verts_to_update.append(vert)
                poly = polys[vert.polygon_id]
                normal += poly.normal

            normal.normalize()

            for vert in verts_to_update:
                normal_writer.set_row(vert.row_index)
                normal_writer.set_data3(normal * sign)
                vert.normal = normal

        normal_array = vertex_data_top.get_array(2)
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_array(2, GeomVertexArrayData(normal_array))
        normal_geoms = self._geoms["normal"]

        for geom_type in ("pickable", "sel_state"):
            vertex_data = normal_geoms[geom_type].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(2, normal_array)

        if update_tangent_space:

            model = self.toplevel_obj

            if model.has_tangent_space():
                polys_to_update = set(verts[v_id].polygon_id for v_id in verts_to_process)
                tangent_flip, bitangent_flip = model.get_tangent_space_flip()
                self.update_tangent_space(tangent_flip, bitangent_flip, polys_to_update)
            else:
                self.is_tangent_space_initialized = False

    def clear_normal_change(self):

        self._normal_change.clear()

    def _restore_normal_length(self, time_id):

        obj_id = self.toplevel_obj.id
        prop_id = self._unique_prop_ids["normal_length"]
        normal_length = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)
        self._normal_length = normal_length
        self._geoms["normal"]["pickable"].set_shader_input("normal_length", normal_length)
        self._geoms["normal"]["sel_state"].set_shader_input("normal_length", normal_length)

    def _restore_normal_sharing(self, time_id):

        obj_id = self.toplevel_obj.id
        prop_id = self._unique_prop_ids["normal_sharing"]
        shared_normals = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)
        self.shared_normals = shared_normals

        for shared_normal in set(shared_normals.values()):
            shared_normal.geom_data_obj = self

    def _restore_vertex_normals(self, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id
        prop_id = self._unique_prop_ids["normals"]

        prev_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id, old_time_id)
        new_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)

        if prev_time_ids is None:
            prev_time_ids = ()

        if new_time_ids is None:
            new_time_ids = ()

        if not (prev_time_ids or new_time_ids):
            return

        if prev_time_ids and new_time_ids:

            i = 0

            for time_id in new_time_ids:

                if time_id not in prev_time_ids:
                    break

                i += 1

            common_time_ids = prev_time_ids[:i]
            prev_time_ids = prev_time_ids[i:]
            new_time_ids = new_time_ids[i:]

        verts = self._subobjs["vert"]

        data_id = self._unique_prop_ids["normal__extra__"]

        time_ids_to_restore = {}
        time_ids = {}
        normals = {}

        # to undo normal changes, determine the time IDs of the changes that
        # need to be restored by checking the data that was stored when changes
        # occurred, at times leading up to the time that is being replaced (the old
        # time)

        for time_id in reversed(prev_time_ids):
            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            time_ids_to_restore.update(subobj_data.get("prev", {}))

        vert_ids = {}

        for vert_id, time_id in time_ids_to_restore.items():
            if vert_id in verts:
                time_ids[vert_id] = time_id
                vert_ids.setdefault(time_id, []).append(vert_id)

        for time_id, ids in vert_ids.items():

            if time_id:

                normal_data = Mgr.do("load_from_history", obj_id, data_id, time_id)["normals"]

                for vert_id in ids:
                    if vert_id in normal_data:
                        normals[vert_id] = normal_data[vert_id]

        # to redo normal changes, retrieve the mappings that need to be restored
        # from the data that was stored when changes occurred, at times leading
        # up to the time that is being restored (the new time)

        for time_id in new_time_ids:

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            normals.update(subobj_data.get("normals", {}))

            for vert_id in subobj_data.get("prev", {}):
                if vert_id in verts:
                    time_ids[vert_id] = time_id

        # restore the verts' previous normal change time IDs
        for vert_id, time_id in time_ids.items():
            verts[vert_id].set_previous_property_time("normal", time_id)

        vertex_data_top = self._toplvl_node.modify_geom(0).modify_vertex_data()
        normal_writer = GeomVertexWriter(vertex_data_top, "normal")
        sign = -1. if self.owner.has_inverted_geometry() else 1.

        for vert_id, normal in normals.items():

            if vert_id not in verts:
                continue

            vert = verts[vert_id]
            normal_writer.set_row(vert.row_index)
            normal_writer.set_data3(normal * sign)
            vert.normal = normal

        normal_array = vertex_data_top.get_array(2)
        vertex_data_poly = self._vertex_data["poly"]
        vertex_data_poly.set_array(2, GeomVertexArrayData(normal_array))
        normal_geoms = self._geoms["normal"]

        for geom_type in ("pickable", "sel_state"):
            vertex_data = normal_geoms[geom_type].node().modify_geom(0).modify_vertex_data()
            vertex_data.set_array(2, normal_array)

    def _restore_normal_lock(self, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id
        prop_id = self._unique_prop_ids["normal_lock"]

        prev_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id, old_time_id)
        new_time_ids = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)

        if prev_time_ids is None:
            prev_time_ids = ()

        if new_time_ids is None:
            new_time_ids = ()

        if not (prev_time_ids or new_time_ids):
            return

        if prev_time_ids and new_time_ids:

            i = 0

            for time_id in new_time_ids:

                if time_id not in prev_time_ids:
                    break

                i += 1

            common_time_ids = prev_time_ids[:i]
            prev_time_ids = prev_time_ids[i:]
            new_time_ids = new_time_ids[i:]

        verts = self._subobjs["vert"]

        data_id = self._unique_prop_ids["normal_lock__extra__"]

        time_ids_to_restore = {}
        time_ids = {}
        normal_lock = {}

        # to undo normal lock changes, determine the time IDs of the changes that
        # need to be restored by checking the data that was stored when changes
        # occurred, at times leading up to the time that is being replaced (the old
        # time)

        for time_id in reversed(prev_time_ids):
            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            time_ids_to_restore.update(subobj_data.get("prev", {}))

        vert_ids = {}

        for vert_id, time_id in time_ids_to_restore.items():
            if vert_id in verts:
                time_ids[vert_id] = time_id
                vert_ids.setdefault(time_id, []).append(vert_id)

        for time_id, ids in vert_ids.items():

            if time_id:

                lock_data = Mgr.do("load_from_history", obj_id, data_id, time_id)["normal_lock"]

                for vert_id in ids:
                    if vert_id in lock_data:
                        normal_lock[vert_id] = lock_data[vert_id]

        # to redo normal lock changes, retrieve the mappings that need to be restored
        # from the data that was stored when changes occurred, at times leading
        # up to the time that is being restored (the new time)

        for time_id in new_time_ids:

            subobj_data = Mgr.do("load_from_history", obj_id, data_id, time_id)
            normal_lock.update(subobj_data.get("normal_lock", {}))

            for vert_id in subobj_data.get("prev", {}):
                if vert_id in verts:
                    time_ids[vert_id] = time_id

        # restore the verts' previous normal lock change time IDs
        for vert_id, time_id in time_ids.items():
            verts[vert_id].set_previous_property_time("normal_lock", time_id)

        locked_normal_ids = self.locked_normals
        unlocked_normal_ids = []

        for vert_id, locked in normal_lock.items():

            if vert_id not in verts:
                continue

            vert = verts[vert_id]
            vert.lock_normal(locked)

            if locked:
                locked_normal_ids.add(vert_id)
            else:
                unlocked_normal_ids.append(vert_id)
                locked_normal_ids.discard(vert_id)

        self.update_locked_normal_selection(None, None, locked_normal_ids, unlocked_normal_ids)

    def update_locked_normal_selection(self, selected_normal_ids=None, deselected_normal_ids=None,
                                       locked_normal_ids=None, unlocked_normal_ids=None):

        if not (selected_normal_ids or deselected_normal_ids
                or locked_normal_ids or unlocked_normal_ids):
            return

        verts = self._subobjs["vert"]
        sel_state_geom = self._geoms["normal"]["sel_state"]
        vertex_data = sel_state_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        sel_colors = Mgr.get("subobj_selection_colors")["normal"]

        if locked_normal_ids is not None:

            sel_ids = self._selected_subobj_ids["normal"]

            color_sel = sel_colors["locked_sel"]
            color_unsel = sel_colors["locked_unsel"]

            for vert_id in locked_normal_ids:
                vert = verts[vert_id]
                row = vert.row_index
                col_writer.set_row(row)
                col_writer.set_data4(color_sel if vert_id in sel_ids else color_unsel)

            color_sel = sel_colors["selected"]
            color_unsel = sel_colors["unselected"]

            for vert_id in unlocked_normal_ids:
                vert = verts[vert_id]
                row = vert.row_index
                col_writer.set_row(row)
                col_writer.set_data4(color_sel if vert_id in sel_ids else color_unsel)

            return

        color_sel = sel_colors["locked_sel"]
        color_unsel = sel_colors["locked_unsel"]

        for vert_id in selected_normal_ids:

            vert = verts[vert_id]

            if vert.has_locked_normal():
                row = vert.row_index
                col_writer.set_row(row)
                col_writer.set_data4(color_sel)

        for vert_id in deselected_normal_ids:

            vert = verts[vert_id]

            if vert.has_locked_normal():
                row = vert.row_index
                col_writer.set_row(row)
                col_writer.set_data4(color_unsel)

    def init_normal_length(self):

        geom = self._toplvl_node.get_geom(0)
        prim_count = geom.get_primitive(0).get_num_primitives()
        bounds = self.origin.get_tight_bounds()

        if bounds:
            p1, p2 = bounds
            x, y, z = p2 - p1
            a = (x + y + z) / 3.
            normal_length = min(a * .25, max(.001, 500. * a / prim_count))
        else:
            normal_length = .001

        self._geoms["normal"]["pickable"].set_shader_input("normal_length", normal_length)
        self._geoms["normal"]["sel_state"].set_shader_input("normal_length", normal_length)
        self._normal_length = normal_length

    def set_normal_length(self, normal_length, state="done"):

        if self._normal_length == normal_length and state == "done":
            return False

        polys = self._subobjs["poly"]
        self._geoms["normal"]["pickable"].set_shader_input("normal_length", normal_length)
        self._geoms["normal"]["sel_state"].set_shader_input("normal_length", normal_length)

        if state == "done":
            self._normal_length = normal_length
            return True

        return False

    def set_normal_shader(self, set_shader=True):

        if set_shader:
            shader = shaders.Shaders.normal
            self._geoms["normal"]["pickable"].set_shader(shader)
            self._geoms["normal"]["sel_state"].set_shader(shader)
        else:
            self._geoms["normal"]["pickable"].clear_shader()
            self._geoms["normal"]["sel_state"].clear_shader()

    def init_normal_picking_via_poly(self, poly, category=""):

        # Allow picking the vertex normals of the poly picked in the previous step
        # (see prepare_subobj_picking_via_poly) instead of other normals;
        # as soon as the mouse is released over a normal, it gets picked and
        # polys become pickable again.

        origin = self.origin
        verts = self._subobjs["vert"]
        edges = self._subobjs["edge"]
        count = poly.vertex_count

        # create pickable geometry, specifically for the normals of the
        # given polygon and belonging to the given category, if any
        vertex_format = Mgr.get("vertex_format_normal")
        vertex_data = GeomVertexData("vert_data", vertex_format, Geom.UH_static)
        vertex_data.reserve_num_rows(count)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")
        normal_writer = GeomVertexWriter(vertex_data, "normal")
        pickable_id = PickableTypes.get_id("vert")
        rows = self._tmp_row_indices
        sign = -1. if self.owner.has_inverted_geometry() else 1.
        by_aiming = GD["subobj_edit_options"]["pick_by_aiming"]

        if by_aiming:

            # To further assist with normal picking, create two quads for each
            # normal, with the picking color of that normal and perpendicular to
            # the view plane;
            # the border of each quad will pass through the vertex corresponding
            # to the normal itself, and through either of the centers of the 2 edges
            # connected by that vertex;
            # an auxiliary picking camera will be placed at the clicked point under
            # the mouse and follow the mouse cursor, rendering the picking color
            # of the quad it is pointed at.

            aux_picking_root = Mgr.get("aux_picking_root")
            aux_picking_cam = Mgr.get("aux_picking_cam")
            cam = GD.cam()
            cam_pos = cam.get_pos(GD.world)
            normal = GD.world.get_relative_vector(cam, Vec3.forward()).normalized()
            plane = Plane(normal, cam_pos + normal * 10.)
            aux_picking_cam.set_plane(plane)
            aux_picking_cam.update_pos()
            normal *= 5.
            vertex_data_poly = GeomVertexData("vert_data_poly", vertex_format, Geom.UH_static)
            vertex_data_poly.reserve_num_rows(count * 6)
            pos_writer_poly = GeomVertexWriter(vertex_data_poly, "vertex")
            col_writer_poly = GeomVertexWriter(vertex_data_poly, "color")
            tmp_poly_prim = GeomTriangles(Geom.UH_static)
            tmp_poly_prim.reserve_num_vertices(count * 12)
            rel_pt = lambda point: GD.world.get_relative_point(origin, point)
            lens_is_ortho = GD.cam.lens_type == "ortho"

        for i, vert_id in enumerate(poly.vertex_ids):

            vertex = verts[vert_id]
            pos = vertex.get_pos()
            pos_writer.add_data3(pos)
            color_id = vertex.picking_color_id
            picking_color = get_color_vec(color_id, pickable_id)
            col_writer.add_data4(picking_color)
            rows[color_id] = i
            vert_normal = vertex.normal
            normal_writer.add_data3(vert_normal * sign)

            if by_aiming:

                edge1_id, edge2_id = vertex.edge_ids
                edge1_center = edges[edge1_id].get_center_pos()
                edge2_center = edges[edge2_id].get_center_pos()
                p1 = Point3()
                point1 = rel_pt(edge1_center)
                point2 = point1 + normal if lens_is_ortho else cam_pos
                plane.intersects_line(p1, point1, point2)
                p2 = Point3()
                point1 = rel_pt(pos)
                point2 = point1 + normal if lens_is_ortho else cam_pos
                plane.intersects_line(p2, point1, point2)
                p3 = Point3()
                point1 = rel_pt(edge2_center)
                point2 = point1 + normal if lens_is_ortho else cam_pos
                plane.intersects_line(p3, point1, point2)
                pos_writer_poly.add_data3(p1 - normal)
                pos_writer_poly.add_data3(p1 + normal)
                pos_writer_poly.add_data3(p2 - normal)
                pos_writer_poly.add_data3(p2 + normal)
                pos_writer_poly.add_data3(p3 - normal)
                pos_writer_poly.add_data3(p3 + normal)

                for _ in range(6):
                    col_writer_poly.add_data4(picking_color)

                j = i * 6
                tmp_poly_prim.add_vertices(j, j + 1, j + 2)
                tmp_poly_prim.add_vertices(j + 1, j + 3, j + 2)
                tmp_poly_prim.add_vertices(j + 2, j + 3, j + 4)
                tmp_poly_prim.add_vertices(j + 3, j + 5, j + 4)

        tmp_prim = GeomPoints(Geom.UH_static)
        tmp_prim.reserve_num_vertices(count)
        tmp_prim.add_next_vertices(count)
        geom = Geom(vertex_data)
        geom.add_primitive(tmp_prim)
        node = GeomNode("tmp_geom_pickable")
        node.add_geom(geom)
        geom_pickable = origin.attach_new_node(node)
        geom_pickable.set_bin("fixed", 51)
        geom_pickable.set_depth_test(False)
        geom_pickable.set_depth_write(False)
        shader = shaders.Shaders.normal
        geom_pickable.set_shader(shader)
        normal_length = self._normal_length
        geom_pickable.set_shader_input("normal_length", normal_length)
        geom_sel_state = geom_pickable.copy_to(origin)
        geom_sel_state.name = "tmp_geom_sel_state"
        geom_sel_state.set_light_off()
        geom_sel_state.set_color_off()
        geom_sel_state.set_texture_off()
        geom_sel_state.set_material_off()
        geom_sel_state.set_transparency(TransparencyAttrib.M_alpha)
        geom_sel_state.set_render_mode_thickness(3)
        geom = geom_sel_state.node().modify_geom(0)
        vertex_data = geom.get_vertex_data().set_color((.3, .3, .3, .5))
        geom.set_vertex_data(vertex_data)
        self._tmp_geom_pickable = geom_pickable
        self._tmp_geom_sel_state = geom_sel_state

        if by_aiming:
            geom_poly = Geom(vertex_data_poly)
            geom_poly.add_primitive(tmp_poly_prim)
            node = GeomNode("tmp_geom_pickable")
            node.add_geom(geom_poly)
            geom_poly_pickable = aux_picking_root.attach_new_node(node)
            geom_poly_pickable.set_two_sided(True)

        # to determine whether the mouse is over the polygon or not, create a
        # duplicate with a white color to distinguish it from the black background
        # color (so it gets detected by the picking camera) and any other pickable
        # objects (so no attempt will be made to pick it)
        vertex_data_poly = GeomVertexData("vert_data_poly", vertex_format, Geom.UH_static)
        vertex_data_poly.reserve_num_rows(count)
        pos_writer_poly = GeomVertexWriter(vertex_data_poly, "vertex")
        col_writer_poly = GeomVertexWriter(vertex_data_poly, "color")
        tmp_poly_prim = GeomTriangles(Geom.UH_static)
        tmp_poly_prim.reserve_num_vertices(len(poly))
        vert_ids = poly.vertex_ids
        white = (1., 1., 1., 1.)

        for vert_id in vert_ids:
            vertex = verts[vert_id]
            pos = vertex.get_pos()
            pos_writer_poly.add_data3(pos)
            col_writer_poly.add_data4(white)

        for _ in range(count):
            col_writer_poly.add_data4(white)

        for tri_vert_ids in poly:
            for vert_id in tri_vert_ids:
                tmp_poly_prim.add_vertex(vert_ids.index(vert_id))

        geom_poly = Geom(vertex_data_poly)
        geom_poly.add_primitive(tmp_poly_prim)
        node = GeomNode("tmp_geom_poly_pickable")
        node.add_geom(geom_poly)
        geom_poly_pickable = geom_pickable.attach_new_node(node)
        geom_poly_pickable.set_bin("fixed", 50)
        geom_poly_pickable.set_shader_off()

        render_mask = Mgr.get("render_mask")
        picking_mask = Mgr.get("picking_mask")
        geom_pickable.hide(render_mask)
        geom_pickable.show_through(picking_mask)

        if by_aiming:
            aux_picking_cam.active = True
            Mgr.do("start_drawing_aux_picking_viz")

        geoms = self._geoms
        geoms["poly"]["pickable"].show(picking_mask)

    def get_normal_array(self):

        normals_geom = self._geoms["normal"]["pickable"].node().get_geom(0)
        normal_array = normals_geom.get_vertex_data().get_array(2)

        return GeomVertexArrayData(normal_array)

    def __update_geoms(self, normal_array):

        geom = self._geoms["normal"]["sel_state"].node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        vertex_data.set_array(2, normal_array)
        vertex_data = self._toplvl_node.modify_geom(0).modify_vertex_data()
        vertex_data.set_array(2, normal_array)
        vertex_data = self._vertex_data["poly"]
        vertex_data.set_array(2, normal_array)

    def prepare_normal_transform(self, normal_array, update_geoms=True):

        self._transf_start_data["pos_array"] = GeomVertexArrayData(normal_array)

        if update_geoms:
            geom = self._geoms["normal"]["pickable"].node().modify_geom(0)
            geom.modify_vertex_data().set_array(2, normal_array)
            self.__update_geoms(normal_array)

    def init_normal_transform(self):

        self.prepare_normal_transform(self.get_normal_array(), update_geoms=False)

    def set_normal_sel_angle(self, axis, angle):

        sel_ids = self._selected_subobj_ids["normal"]

        if not sel_ids:
            return

        origin = self.origin
        ref_node = self._get_ref_node()
        geom = self._geoms["normal"]["pickable"].node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        tmp_vertex_data = GeomVertexData(vertex_data)
        index = "zxy".index(axis)
        normal_rewriter = GeomVertexRewriter(tmp_vertex_data, "normal")
        verts = self._subobjs["vert"]

        for sel_id in sel_ids:
            vert = verts[sel_id]
            row = vert.row_index
            normal_rewriter.set_row(row)
            normal = normal_rewriter.get_data3()
            normal = V3D(ref_node.get_relative_vector(origin, normal))
            hpr = normal.get_hpr()
            hpr[index] = angle
            quat = Quat()
            quat.set_hpr(hpr)
            normal = quat.xform(Vec3.forward())
            normal = origin.get_relative_vector(ref_node, normal)
            normal_rewriter.set_data3(normal.normalized())

        normal_array = tmp_vertex_data.get_array(2)
        vertex_data.set_array(2, normal_array)
        self.__update_geoms(normal_array)

    def aim_selected_normals(self, point, ref_node, toward=True):

        sel_ids = self._selected_subobj_ids["normal"]

        if not sel_ids:
            return

        origin = self.origin
        target_pos = origin.get_relative_point(ref_node, point)
        geom = self._geoms["normal"]["pickable"].node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        tmp_vertex_data = GeomVertexData(vertex_data)
        normal_writer = GeomVertexWriter(tmp_vertex_data, "normal")
        verts = self._subobjs["vert"]

        for sel_id in sel_ids:
            vert = verts[sel_id]
            pos = vert.get_pos()
            normal = (target_pos - pos).normalized() * (1. if toward else -1.)
            row = vert.row_index
            normal_writer.set_row(row)
            normal_writer.set_data3(normal)

        normal_array = tmp_vertex_data.get_array(2)
        vertex_data.set_array(2, normal_array)
        self.__update_geoms(normal_array)

    def flip_normals(self):

        rows = self._rows_to_transf["normal"]

        if not rows:
            return

        scale_mat = Mat4.scale_mat(-1., -1., -1.)
        geom = self._geoms["normal"]["pickable"].node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        tmp_vertex_data = GeomVertexData(vertex_data)
        tmp_vertex_data.set_array(0, self.get_normal_array())
        tmp_vertex_data.transform_vertices(scale_mat, rows)
        normal_array = tmp_vertex_data.get_array(0)
        vertex_data.set_array(2, normal_array)
        self.__update_geoms(normal_array)

    def transform_normals(self, transf_type, value):

        rows = self._rows_to_transf["normal"]

        if not rows:
            return

        ref_node = self._get_ref_node()
        geom = self._geoms["normal"]["pickable"].node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        tmp_vertex_data = GeomVertexData(vertex_data)
        tmp_vertex_data.set_array(0, GeomVertexArrayData(self._transf_start_data["pos_array"]))
        origin = self.origin

        if transf_type == "custom":

            def get_custom_mat():

                final_mat = Mat4.ident_mat()
                mats = value["mats"]

                for mat, ref_type in mats:
                    if ref_type == "ref_node":
                        node = ref_node
                    elif ref_type == "pivot":
                        node = self.toplevel_obj.pivot
                    elif ref_type == "grid_origin":
                        node = Mgr.get("grid").origin
                    elif ref_type == "origin":
                        node = origin
                    elif ref_type == "world":
                        node = GD.world
                    elif ref_type == "custom":
                        node = value["ref_node"]
                    final_mat = final_mat * origin.get_mat(node) * mat * node.get_mat(origin)

                return final_mat

            mat = get_custom_mat()

        elif transf_type == "translate":

            vec = origin.get_relative_vector(ref_node, value)
            mat = Mat4.translate_mat(vec)

        elif transf_type == "rotate":

            quat = origin.get_quat(ref_node) * value * ref_node.get_quat(origin)
            mat = Mat4()
            quat.extract_to_matrix(mat)

        elif transf_type == "scale":

            scale_mat = Mat4.scale_mat(value)
            mat = origin.get_mat(ref_node) * scale_mat * ref_node.get_mat(origin)
            # remove translation component
            mat.set_row(3, VBase3())

        tmp_vertex_data.transform_vertices(mat, rows)
        pos_array = tmp_vertex_data.get_array(0)
        pos_reader = GeomVertexReader(pos_array, 0)
        normal_writer = GeomVertexWriter(vertex_data, "normal")
        verts = self._subobjs["vert"]
        sel_ids = self._selected_subobj_ids["normal"]

        for sel_id in sel_ids:
            vert = verts[sel_id]
            row = vert.row_index
            pos_reader.set_row(row)
            pos = pos_reader.get_data3()
            normal = Vec3(pos).normalized()
            normal_writer.set_row(row)
            normal_writer.set_data3(normal)

        normal_array = vertex_data.get_array(2)
        self.__update_geoms(normal_array)

    def finalize_normal_transform(self, cancelled=False, lock_normals=True):

        start_data = self._transf_start_data
        geom_node_top = self._toplvl_node
        vertex_data_top = geom_node_top.modify_geom(0).modify_vertex_data()

        if cancelled:

            normal_array = start_data["pos_array"]
            vertex_data_top.set_array(2, normal_array)
            self._vertex_data["poly"].set_array(2, normal_array)
            geom = self._geoms["normal"]["pickable"].node().modify_geom(0)
            geom.modify_vertex_data().set_array(2, normal_array)
            geom = self._geoms["normal"]["sel_state"].node().modify_geom(0)
            geom.modify_vertex_data().set_array(2, normal_array)

        else:

            verts = self._subobjs["vert"]
            polys_to_update = set()
            normal_reader = GeomVertexReader(vertex_data_top, "normal")
            sign = -1. if self.owner.has_inverted_geometry() else 1.
            sel_ids = self._selected_subobj_ids["normal"]

            for sel_id in sel_ids:
                vert = verts[sel_id]
                polys_to_update.add(vert.polygon_id)
                row = vert.row_index
                normal_reader.set_row(row)
                normal = Vec3(normal_reader.get_data3()) * sign
                vert.normal = normal

            if lock_normals:
                self._normal_change.update(sel_ids)

            model = self.toplevel_obj

            if model.has_tangent_space():
                tangent_flip, bitangent_flip = model.get_tangent_space_flip()
                self.update_tangent_space(tangent_flip, bitangent_flip, polys_to_update)
            else:
                self.is_tangent_space_initialized = False

            if lock_normals:
                self.lock_normals()

        start_data.clear()

    def copy_vertex_normal(self, normal):

        sel_ids = self._selected_subobj_ids["normal"]

        if not sel_ids:
            return False

        geom = self._geoms["normal"]["pickable"].node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        tmp_vertex_data = GeomVertexData(vertex_data)
        normal_writer = GeomVertexWriter(tmp_vertex_data, "normal")
        verts = self._subobjs["vert"]
        polys_to_update = set()
        sign = -1. if self.owner.has_inverted_geometry() else 1.

        for sel_id in sel_ids:
            vert = verts[sel_id]
            polys_to_update.add(vert.polygon_id)
            row = vert.row_index
            normal_writer.set_row(row)
            normal_writer.set_data3(normal * sign)
            vert.normal = Vec3(normal)

        normal_array = tmp_vertex_data.get_array(2)
        vertex_data.set_array(2, normal_array)
        self.__update_geoms(normal_array)

        self._normal_change.update(sel_ids)
        model = self.toplevel_obj

        if model.has_tangent_space():
            tangent_flip, bitangent_flip = model.get_tangent_space_flip()
            self.update_tangent_space(tangent_flip, bitangent_flip, polys_to_update)
        else:
            self.is_tangent_space_initialized = False

        self.lock_normals()

        return True


class NormalManager:

    def __init__(self):

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

        Mgr.accept("create_shared_normal", lambda *args, **kwargs: SharedNormal(*args, **kwargs))
        Mgr.add_app_updater("normal_length", self.__set_normal_length)
        Mgr.add_app_updater("inverted_geom", self.__invert_geometry)
        Mgr.add_app_updater("normal_unification", self.__unify_normals)
        Mgr.add_app_updater("normal_lock", self.__lock_normals)

        add_state = Mgr.add_state
        add_state("normal_dir_copy_mode", -10, self.__enter_picking_mode,
                  self.__exit_picking_mode)
        add_state("normal_picking_via_poly", -11, self.__start_normal_picking_via_poly)

        exit_mode = lambda: Mgr.exit_state("normal_dir_copy_mode")

        bind = Mgr.bind_state
        bind("normal_dir_copy_mode", "normal dir copy -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("normal_dir_copy_mode", "normal dir copy -> select", "escape", exit_mode)
        bind("normal_dir_copy_mode", "exit normal dir copy mode", "mouse3", exit_mode)
        bind("normal_dir_copy_mode", "copy normal dir", "mouse1", self.__pick)
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("normal_dir_copy_mode", "normal dir ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))
        bind("normal_picking_via_poly", "pick hilited normal",
             "mouse1-up", self.__pick_hilited_normal)
        bind("normal_picking_via_poly", "cancel normal picking",
             "mouse3", self.__cancel_normal_picking_via_poly)

        status_data = GD["status"]
        mode_text = "Copy normal direction"
        info_text = "Pick normal to copy direction to selected normals;" \
                    " RMB or <Escape> to end"
        status_data["normal_dir_copy_mode"] = {"mode": mode_text, "info": info_text}
        info_text = "LMB-drag over normal to pick it; RMB to cancel"
        status_data["normal_picking_via_poly"] = {"mode": "Pick normal", "info": info_text}

    def __set_normal_length(self, normal_length, state="done"):

        selection = Mgr.get("selection_top")
        changed_objs = []

        for obj in selection:
            if obj.geom_obj.set_normal_length(normal_length, state):
                changed_objs.append(obj)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in changed_objs:
            if obj.geom_type == "locked_geom":
                obj_data[obj.id] = obj.geom_obj.get_data_to_store("prop_change", "normal_length")
            elif obj.geom_type == "unlocked_geom":
                geom_data_obj = obj.geom_obj.geom_data_obj
                obj_data[obj.id] = geom_data_obj.get_property_to_store("normal_length")

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'Change normal length of "{obj.name}"\nto {normal_length :.6f}'
        else:
            event_descr = 'Change normal length of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])
            event_descr += f'\n\nto {normal_length :.6f}'

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __invert_geometry(self, invert=True):

        Mgr.exit_states(min_persistence=-99)
        selection = Mgr.get("selection_top")
        changed_objs = []

        for obj in selection:
            if obj.geom_obj.invert_geometry(invert):
                changed_objs.append(obj)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in changed_objs:
            obj_data[obj.id] = obj.get_data_to_store("prop_change", "inverted_geom")

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'{"Invert" if invert else "Uninvert"} geometry of "{obj.name}"'
        else:
            event_descr = f'{"Invert" if invert else "Uninvert"} geometry of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __unify_normals(self, unify=True):

        selection = Mgr.get("selection_top")
        changed_objs = {}

        for model in selection:

            geom_data_obj = model.geom_obj.geom_data_obj

            if geom_data_obj.unify_normals(unify):
                changed_objs[model.id] = geom_data_obj

        if not changed_objs:
            return

        Mgr.do("update_active_selection")
        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.items():
            obj_data[obj_id] = geom_data_obj.get_data_to_store()

        event_descr = f'{"Unify" if unify else "Separate"} normals'
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __lock_normals(self, lock=True):

        selection = Mgr.get("selection_top")
        changed_objs = {}

        for model in selection:

            geom_data_obj = model.geom_obj.geom_data_obj

            if geom_data_obj.lock_normals(lock):
                changed_objs[model.id] = geom_data_obj

        if not changed_objs:
            return

        Mgr.do("update_active_selection")
        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.items():
            obj_data[obj_id] = geom_data_obj.get_data_to_store()

        event_descr = f'{"Lock" if lock else "Unlock"} normals'
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __enter_picking_mode(self, prev_state_id, active):

        if GD["active_transform_type"]:
            GD["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")

        Mgr.add_task(self.__update_cursor, "update_mode_cursor")
        Mgr.update_app("status", ["normal_dir_copy_mode"])

    def __exit_picking_mode(self, next_state_id, active):

        Mgr.remove_task("update_mode_cursor")
        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self.__update_cursor()
                                        # is called
        Mgr.set_cursor("main")

    def __pick(self, picked_vert=None):

        if picked_vert:

            vert = picked_vert

        else:

            if not self._pixel_under_mouse:
                return

            r, g, b, a = [int(round(c * 255.)) for c in self._pixel_under_mouse]
            color_id = r << 16 | g << 8 | b
            pickable_type = PickableTypes.get(a)

            if pickable_type == "poly":
                self._picked_poly = Mgr.get("poly", color_id)
                Mgr.enter_state("normal_picking_via_poly")
                return

            if pickable_type != "vert":
                return

            vert = Mgr.get("vert", color_id)

            if not vert:
                return

        normal = vert.normal
        changed_objs = {}

        for obj in Mgr.get("selection_top"):

            geom_data_obj = obj.geom_obj.geom_data_obj

            if geom_data_obj.copy_vertex_normal(normal):
                changed_objs[obj.id] = geom_data_obj

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}

        for obj_id, geom_data_obj in changed_objs.items():
            obj_data[obj_id] = geom_data_obj.get_data_to_store()

        event_descr = "Copy normal direction"
        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __start_normal_picking_via_poly(self, prev_state_id, active):

        Mgr.remove_task("update_mode_cursor")

        geom_data_obj = self._picked_poly.geom_data_obj
        geom_data_obj.init_subobj_picking_via_poly("normal", self._picked_poly)
        # temporarily select picked poly
        geom_data_obj.update_selection("poly", [self._picked_poly], [], False)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.geom_obj.geom_data_obj

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable(False)

        Mgr.add_task(self.__hilite_normal, "hilite_normal")
        Mgr.update_app("status", ["normal_picking_via_poly"])

        cs_type = GD["coord_sys_type"]
        tc_type = GD["transf_center_type"]
        toplvl_obj = self._picked_poly.toplevel_obj

        if cs_type == "local":
            Mgr.update_locally("coord_sys", cs_type, toplvl_obj)

        if tc_type == "pivot":
            Mgr.update_locally("transf_center", tc_type, toplvl_obj)

    def __hilite_normal(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            if pixel_under_mouse != VBase4():

                r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                color_id = r << 16 | g << 8 | b
                geom_data_obj = self._picked_poly.geom_data_obj

                # highlight temporary normal
                if geom_data_obj.hilite_temp_subobject("normal", color_id):
                    self._tmp_color_id = color_id

            self._pixel_under_mouse = pixel_under_mouse

        color = tuple(round(c * 255.) for c in pixel_under_mouse)
        not_hilited = color in ((0., 0., 0., 0.), (255., 255., 255., 255.))
        cursor_id = "main" if not_hilited else "select"

        if GD["subobj_edit_options"]["pick_by_aiming"]:

            aux_pixel_under_mouse = Mgr.get("aux_pixel_under_mouse")

            if not_hilited or self._aux_pixel_under_mouse != aux_pixel_under_mouse:

                if not_hilited and aux_pixel_under_mouse != VBase4():

                    r, g, b, a = [int(round(c * 255.)) for c in aux_pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    geom_data_obj = self._picked_poly.geom_data_obj

                    # highlight temporary normal
                    if geom_data_obj.hilite_temp_subobject("normal", color_id):
                        self._tmp_color_id = color_id
                        cursor_id = "select"

                self._aux_pixel_under_mouse = aux_pixel_under_mouse

        if self._cursor_id != cursor_id:
            Mgr.set_cursor(cursor_id)
            self._cursor_id = cursor_id

        return task.cont

    def __pick_hilited_normal(self):

        Mgr.remove_task("hilite_normal")

        if self._tmp_color_id is not None:
            picked_vert = Mgr.get("vert", self._tmp_color_id)
            self.__pick(picked_vert)

        Mgr.enter_state("normal_dir_copy_mode")

        geom_data_obj = self._picked_poly.geom_data_obj
        geom_data_obj.prepare_subobj_picking_via_poly("normal")

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.geom_obj.geom_data_obj

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

    def __cancel_normal_picking_via_poly(self):

        Mgr.remove_task("hilite_normal")
        Mgr.exit_state("normal_picking_via_poly")

        geom_data_obj = self._picked_poly.geom_data_obj
        geom_data_obj.prepare_subobj_picking_via_poly("normal")

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.geom_obj.geom_data_obj

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont


MainObjects.add_class(NormalManager)
