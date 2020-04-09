from ...base import *
from .transform import TransformMixin


class SelectionMixin:
    """ GeomDataObject class mix-in """

    def __setstate__(self, state):

        self._poly_selection_data = {"selected": [], "unselected": []}
        self._selected_subobj_ids = {"vert": [], "edge": [], "poly": [], "normal": []}

    def _edit_state(self, state):

        del state["_poly_selection_data"]
        del state["_selected_subobj_ids"]

    def __init__(self):

        self._poly_selection_data = {"selected": [], "unselected": []}
        self._selected_subobj_ids = {"vert": [], "edge": [], "poly": [], "normal": []}
        self._sel_subobj_ids_backup = {}
        self._selection_backup = {}

    def update_selection(self, subobj_type, subobjs_to_select, subobjs_to_deselect,
                         update_verts_to_transf=True, selection_colors=None, geom=None):

        selected_subobj_ids = self._selected_subobj_ids[subobj_type]
        geoms = self._geoms[subobj_type]
        selected_subobjs = [subobj for subobj in subobjs_to_select
                            if subobj.id not in selected_subobj_ids]
        deselected_subobjs = [subobj for subobj in subobjs_to_deselect
                              if subobj.id in selected_subobj_ids]

        if not (selected_subobjs or deselected_subobjs):
            return False

        if subobj_type == "poly":

            geom_selected = geoms["selected"]
            geom_unselected = geoms["unselected"]
            sel_data = self._poly_selection_data
            data_selected = sel_data["selected"]
            data_unselected = sel_data["unselected"]
            prim = geom_selected.node().modify_geom(0).modify_primitive(0)
            array_sel = prim.modify_vertices()
            stride = array_sel.array_format.stride
            size_sel = array_sel.get_num_rows()
            row_count = sum([len(poly) for poly in selected_subobjs], size_sel)
            array_sel.set_num_rows(row_count)
            view_sel = memoryview(array_sel).cast("B")
            prim = geom_unselected.node().modify_geom(0).modify_primitive(0)
            array_unsel = prim.modify_vertices()
            size_unsel = array_unsel.get_num_rows()
            row_count = sum([len(poly) for poly in deselected_subobjs], size_unsel)
            array_unsel.set_num_rows(row_count)
            view_unsel = memoryview(array_unsel).cast("B")
            polys_sel = []
            polys_unsel = []
            row_ranges_sel_to_keep = SparseArray()
            row_ranges_sel_to_keep.set_range(0, array_sel.get_num_rows())
            row_ranges_unsel_to_keep = SparseArray()
            row_ranges_unsel_to_keep.set_range(0, size_unsel)
            row_ranges_sel_to_move = SparseArray()
            row_ranges_unsel_to_move = SparseArray()

            for poly in selected_subobjs:
                selected_subobj_ids.append(poly.id)
                start = data_unselected.index(poly[0]) * 3
                polys_sel.append((start, poly))
                row_ranges_unsel_to_keep.clear_range(start, len(poly))
                row_ranges_unsel_to_move.set_range(start, len(poly))

            for poly in deselected_subobjs:
                selected_subobj_ids.remove(poly.id)
                start = data_selected.index(poly[0]) * 3
                polys_unsel.append((start, poly))
                row_ranges_sel_to_keep.clear_range(start, len(poly))
                row_ranges_sel_to_move.set_range(start, len(poly))

            polys_sel.sort()
            polys_unsel.sort()

            for _, poly in polys_sel:
                data_selected.extend(poly)
                for vert_ids in poly:
                    data_unselected.remove(vert_ids)

            for _, poly in polys_unsel:
                data_unselected.extend(poly)
                for vert_ids in poly:
                    data_selected.remove(vert_ids)

            f = lambda values, stride: (v * stride for v in values)

            for i in range(row_ranges_unsel_to_move.get_num_subranges()):
                start = row_ranges_unsel_to_move.get_subrange_begin(i)
                size = row_ranges_unsel_to_move.get_subrange_end(i) - start
                offset_, start_, size_ = f((size_sel, start, size), stride)
                view_sel[offset_:offset_+size_] = view_unsel[start_:start_+size_]
                size_sel += size
                size_unsel -= size

            offset = 0

            for i in range(row_ranges_unsel_to_keep.get_num_subranges()):
                start = row_ranges_unsel_to_keep.get_subrange_begin(i)
                size = row_ranges_unsel_to_keep.get_subrange_end(i) - start
                offset_, start_, size_ = f((offset, start, size), stride)
                view_unsel[offset_:offset_+size_] = view_unsel[start_:start_+size_]
                offset += size

            for i in range(row_ranges_sel_to_move.get_num_subranges()):
                start = row_ranges_sel_to_move.get_subrange_begin(i)
                size = row_ranges_sel_to_move.get_subrange_end(i) - start
                offset_, start_, size_ = f((size_unsel, start, size), stride)
                view_unsel[offset_:offset_+size_] = view_sel[start_:start_+size_]
                size_unsel += size
                size_sel -= size

            offset = 0

            for i in range(row_ranges_sel_to_keep.get_num_subranges()):
                start = row_ranges_sel_to_keep.get_subrange_begin(i)
                size = row_ranges_sel_to_keep.get_subrange_end(i) - start
                offset_, start_, size_ = f((offset, start, size), stride)
                view_sel[offset_:offset_+size_] = view_sel[start_:start_+size_]
                offset += size

            array_sel.set_num_rows(size_sel)
            array_unsel.set_num_rows(size_unsel)

        else:

            if subobj_type == "vert":
                combined_subobjs = self.merged_verts
            elif subobj_type == "edge":
                combined_subobjs = self.merged_edges
            elif subobj_type == "normal":
                combined_subobjs = self.shared_normals

            selected_subobjs = set(combined_subobjs[subobj.id] for subobj in selected_subobjs)
            deselected_subobjs = set(combined_subobjs[subobj.id] for subobj in deselected_subobjs)

            sel_state_geom = geom if geom else geoms["sel_state"]
            vertex_data = sel_state_geom.node().modify_geom(0).modify_vertex_data()
            col_writer = GeomVertexWriter(vertex_data, "color")

            if selection_colors:
                sel_colors = selection_colors
            else:
                sel_colors = Mgr.get("subobj_selection_colors")[subobj_type]

            color_sel = sel_colors["selected"]
            color_unsel = sel_colors["unselected"]

            for combined_subobj in selected_subobjs:

                selected_subobj_ids.extend(combined_subobj)

                for row_index in combined_subobj.row_indices:
                    col_writer.set_row(row_index)
                    col_writer.set_data4(color_sel)

            for combined_subobj in deselected_subobjs:

                for subobj_id in combined_subobj:
                    selected_subobj_ids.remove(subobj_id)

                for row_index in combined_subobj.row_indices:
                    col_writer.set_row(row_index)
                    col_writer.set_data4(color_unsel)

            if subobj_type == "normal":

                selected_normal_ids = []
                deselected_normal_ids = []

                for combined_subobj in selected_subobjs:
                    selected_normal_ids.extend(combined_subobj)

                for combined_subobj in deselected_subobjs:
                    deselected_normal_ids.extend(combined_subobj)

                self.update_locked_normal_selection(selected_normal_ids, deselected_normal_ids)

        if update_verts_to_transf:
            self._update_verts_to_transform(subobj_type)

        return True

    def is_selected(self, subobj):

        return subobj.id in self._selected_subobj_ids[subobj.type]

    def get_selection(self, subobj_lvl):

        selected_subobj_ids = self._selected_subobj_ids[subobj_lvl]

        if subobj_lvl == "poly":
            polys = self._subobjs["poly"]
            return [polys[poly_id] for poly_id in selected_subobj_ids]

        if subobj_lvl == "vert":
            combined_subobjs = self.merged_verts
        elif subobj_lvl == "edge":
            combined_subobjs = self.merged_edges
        elif subobj_lvl == "normal":
            combined_subobjs = self.shared_normals

        return list(set(combined_subobjs[subobj_id] for subobj_id in selected_subobj_ids))

    def create_selection_backup(self, subobj_lvl):

        if subobj_lvl in self._selection_backup:
            return

        self._sel_subobj_ids_backup[subobj_lvl] = self._selected_subobj_ids[subobj_lvl][:]
        self._selection_backup[subobj_lvl] = self.get_selection(subobj_lvl)

    def restore_selection_backup(self, subobj_lvl):

        sel_backup = self._selection_backup

        if subobj_lvl not in sel_backup:
            return

        self.clear_selection(subobj_lvl, False)
        self.update_selection(subobj_lvl, sel_backup[subobj_lvl], [], False)
        del sel_backup[subobj_lvl]
        del self._sel_subobj_ids_backup[subobj_lvl]

    def remove_selection_backup(self, subobj_lvl):

        sel_backup = self._selection_backup

        if subobj_lvl in sel_backup:
            del sel_backup[subobj_lvl]
            del self._sel_subobj_ids_backup[subobj_lvl]

    def clear_selection(self, subobj_lvl, update_verts_to_transf=True, force=False):

        if not (force or self._selected_subobj_ids[subobj_lvl]):
            return

        geoms = self._geoms[subobj_lvl]

        if subobj_lvl == "poly":

            geom_selected = geoms["selected"]
            geom_unselected = geoms["unselected"]
            sel_data = self._poly_selection_data
            sel_data["unselected"].extend(sel_data["selected"])
            sel_data["selected"] = []

            from_array = geom_selected.node().modify_geom(0).modify_primitive(0).modify_vertices()
            from_size = from_array.data_size_bytes
            from_view = memoryview(from_array).cast("B")
            to_array = geom_unselected.node().modify_geom(0).modify_primitive(0).modify_vertices()
            to_size = to_array.data_size_bytes
            to_array.set_num_rows(to_array.get_num_rows() + from_array.get_num_rows())
            to_view = memoryview(to_array).cast("B")
            to_view[to_size:to_size+from_size] = from_view
            from_array.clear_rows()

        elif subobj_lvl == "normal":

            color = Mgr.get("subobj_selection_colors")["normal"]["unselected"]
            color_locked = Mgr.get("subobj_selection_colors")["normal"]["locked_unsel"]
            vertex_data = geoms["sel_state"].node().modify_geom(0).modify_vertex_data()
            col_writer = GeomVertexWriter(vertex_data, "color")
            verts = self._subobjs["vert"]

            for vert_id in self._selected_subobj_ids["normal"]:
                vert = verts[vert_id]
                row = vert.row_index
                col = color_locked if vert.has_locked_normal() else color
                col_writer.set_row(row)
                col_writer.set_data4(col)

        else:

            vertex_data = geoms["sel_state"].node().modify_geom(0).modify_vertex_data()
            color = Mgr.get("subobj_selection_colors")[subobj_lvl]["unselected"]
            new_data = vertex_data.set_color(color)
            vertex_data.set_array(1, new_data.get_array(1))

        self._selected_subobj_ids[subobj_lvl] = []

        if update_verts_to_transf:
            self._verts_to_transf[subobj_lvl] = {}

    def delete_selection(self, subobj_lvl, unregister_globally=True, unregister_locally=True):

        subobjs = self._subobjs
        verts = subobjs["vert"]
        edges = subobjs["edge"]
        polys = subobjs["poly"]

        selected_subobj_ids = self._selected_subobj_ids
        selected_vert_ids = selected_subobj_ids["vert"]
        selected_edge_ids = selected_subobj_ids["edge"]
        selected_poly_ids = selected_subobj_ids["poly"]

        if subobj_lvl == "vert":

            polys_to_delete = set()

            for vert in (verts[v_id] for v_id in selected_vert_ids):
                polys_to_delete.add(polys[vert.polygon_id])

        elif subobj_lvl == "edge":

            polys_to_delete = set()

            for edge in (edges[e_id] for e_id in selected_edge_ids):
                polys_to_delete.add(polys[edge.polygon_id])

        elif subobj_lvl == "poly":

            polys_to_delete = [polys[poly_id] for poly_id in selected_poly_ids]

        self.delete_polygons(polys_to_delete, unregister_globally, unregister_locally)

    def _restore_subobj_selection(self, time_id):

        obj_id = self.toplevel_obj.id
        prop_id = self._unique_prop_ids["subobj_selection"]
        data = Mgr.do("load_last_from_history", obj_id, prop_id, time_id)

        verts = self._subobjs["vert"]
        normal_ids = data["normal"]
        old_sel_normal_ids = set(self._selected_subobj_ids["normal"])
        new_sel_normal_ids = set(normal_ids)
        sel_normal_ids = new_sel_normal_ids - old_sel_normal_ids
        unsel_normal_ids = old_sel_normal_ids - new_sel_normal_ids
        unsel_normal_ids.intersection_update(verts)
        shared_normals = self.shared_normals
        original_shared_normals = {}

        if unsel_normal_ids:
            tmp_shared_normal = Mgr.do("create_shared_normal", self, unsel_normal_ids)
            unsel_id = tmp_shared_normal.id
            original_shared_normals[unsel_id] = shared_normals[unsel_id]
            shared_normals[unsel_id] = tmp_shared_normal
            unsel_normals = [tmp_shared_normal]
        else:
            unsel_normals = []

        if sel_normal_ids:
            tmp_shared_normal = Mgr.do("create_shared_normal", self, sel_normal_ids)
            sel_id = tmp_shared_normal.id
            original_shared_normals[sel_id] = shared_normals[sel_id]
            shared_normals[sel_id] = tmp_shared_normal
            sel_normals = [tmp_shared_normal]
        else:
            sel_normals = []

        self.update_selection("normal", sel_normals, unsel_normals, False)

        if unsel_normals:
            shared_normals[unsel_id] = original_shared_normals[unsel_id]
        if sel_normals:
            shared_normals[sel_id] = original_shared_normals[sel_id]

        self._update_verts_to_transform("normal")

        for subobj_type in ("vert", "edge", "poly"):

            subobjs = self._subobjs[subobj_type]

            subobj_ids = data[subobj_type]
            old_sel_subobj_ids = set(self._selected_subobj_ids[subobj_type])
            new_sel_subobj_ids = set(subobj_ids)
            sel_subobj_ids = new_sel_subobj_ids - old_sel_subobj_ids
            unsel_subobj_ids = old_sel_subobj_ids - new_sel_subobj_ids
            unsel_subobj_ids.intersection_update(subobjs)

            unsel_subobjs = [subobjs[i] for i in unsel_subobj_ids]
            sel_subobjs = [subobjs[i] for i in sel_subobj_ids]

            if subobj_type in ("vert", "edge"):

                merged_subobjs = self.merged_verts if subobj_type == "vert" else self.merged_edges
                original_merged_subobjs = {}

                if unsel_subobjs:

                    tmp_merged_subobj = Mgr.do(f"create_merged_{subobj_type}", self)

                    for subobj_id in unsel_subobj_ids:
                        tmp_merged_subobj.append(subobj_id)

                    unsel_id = tmp_merged_subobj.id
                    original_merged_subobjs[unsel_id] = merged_subobjs[unsel_id]
                    merged_subobjs[unsel_id] = tmp_merged_subobj
                    unsel_subobjs = [subobjs[unsel_id]]

                if sel_subobjs:

                    tmp_merged_subobj = Mgr.do(f"create_merged_{subobj_type}", self)

                    for subobj_id in sel_subobj_ids:
                        tmp_merged_subobj.append(subobj_id)

                    sel_id = tmp_merged_subobj.id
                    original_merged_subobjs[sel_id] = merged_subobjs[sel_id]
                    merged_subobjs[sel_id] = tmp_merged_subobj
                    sel_subobjs = [subobjs[sel_id]]

            self.update_selection(subobj_type, sel_subobjs, unsel_subobjs, False)

            if subobj_type in ("vert", "edge"):
                if unsel_subobjs:
                    merged_subobjs[unsel_id] = original_merged_subobjs[unsel_id]
                if sel_subobjs:
                    merged_subobjs[sel_id] = original_merged_subobjs[sel_id]

            self._update_verts_to_transform(subobj_type)


class Selection(TransformMixin):

    def __init__(self, obj_level, subobjs):

        TransformMixin.__init__(self)

        self._objs = subobjs
        self._obj_level = obj_level

        self._groups = {}

        for obj in subobjs:
            self._groups.setdefault(obj.geom_data_obj, []).append(obj)

    def __getitem__(self, index):

        try:
            return self._objs[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __len__(self):

        return len(self._objs)

    def get_geom_data_objects(self):

        return list(self._groups)

    def get_toplevel_objects(self, get_group=False):

        return [geom_data_obj.get_toplevel_object(get_group) for geom_data_obj in self._groups]

    def get_toplevel_object(self, get_group=False):
        """ Return a random top-level object """

        if self._groups:
            return list(self._groups.keys())[0].get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def get_subobjects(self, geom_data_obj):

        return self._groups.get(geom_data_obj, [])

    def update(self, hide_sets=False):

        self.update_center_pos()
        self.update_ui()

        if hide_sets:
            Mgr.update_remotely("selection_set", "hide_name")

    def add(self, subobjs, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_add = set(subobjs)
        common = old_sel & sel_to_add

        if common:
            sel_to_add -= common

        if not sel_to_add:
            return False

        geom_data_objs = {}
        groups = self._groups

        for obj in sel_to_add:
            geom_data_obj = obj.geom_data_obj
            geom_data_objs.setdefault(geom_data_obj, []).append(obj)
            groups.setdefault(geom_data_obj, []).append(obj)

        for geom_data_obj, objs in geom_data_objs.items():
            geom_data_obj.update_selection(self._obj_level, objs, [])

        sel.extend(sel_to_add)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon", "normal": "normal"}
            event_descr = f'Add to {subobj_descr[self._obj_level]} selection'
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.toplevel_obj
                obj_data[obj.id] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def remove(self, subobjs, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        sel_to_remove = set(subobjs)
        common = old_sel & sel_to_remove

        if not common:
            return False

        geom_data_objs = {}
        groups = self._groups

        for obj in common:

            sel.remove(obj)
            geom_data_obj = obj.geom_data_obj
            geom_data_objs.setdefault(geom_data_obj, []).append(obj)

            groups[geom_data_obj].remove(obj)

            if not groups[geom_data_obj]:
                del groups[geom_data_obj]

        for geom_data_obj, objs in geom_data_objs.items():
            geom_data_obj.update_selection(self._obj_level, [], objs)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon", "normal": "normal"}
            event_descr = f'Remove from {subobj_descr[self._obj_level]} selection'
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.toplevel_obj
                obj_data[obj.id] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def replace(self, subobjs, add_to_hist=True):

        sel = self._objs
        old_sel = set(sel)
        new_sel = set(subobjs)
        common = old_sel & new_sel

        if common:
            old_sel -= common
            new_sel -= common

        if not (old_sel or new_sel):
            return False

        geom_data_objs = {}

        for old_obj in old_sel:
            sel.remove(old_obj)
            geom_data_obj = old_obj.geom_data_obj
            geom_data_objs.setdefault(geom_data_obj, {"sel": [], "desel": []})["desel"].append(old_obj)

        for new_obj in new_sel:
            geom_data_obj = new_obj.geom_data_obj
            geom_data_objs.setdefault(geom_data_obj, {"sel": [], "desel": []})["sel"].append(new_obj)

        for geom_data_obj, objs in geom_data_objs.items():
            geom_data_obj.update_selection(self._obj_level, objs["sel"], objs["desel"])

        sel.extend(new_sel)

        self._groups = groups = {}

        for obj in common | new_sel:
            groups.setdefault(obj.geom_data_obj, []).append(obj)

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist and geom_data_objs:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon", "normal": "normal"}
            event_descr = f'Replace {subobj_descr[self._obj_level]} selection'
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.toplevel_obj
                obj_data[obj.id] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def clear(self, add_to_hist=True):

        if not self._objs:
            return False

        obj_lvl = self._obj_level
        geom_data_objs = []

        for geom_data_obj in self._groups:
            geom_data_obj.clear_selection(obj_lvl)
            geom_data_objs.append(geom_data_obj)

        self._groups = {}
        self._objs = []

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        if add_to_hist:

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon", "normal": "normal"}
            event_descr = f'Clear {subobj_descr[obj_lvl]} selection'
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.toplevel_obj
                obj_data[obj.id] = geom_data_obj.get_data_to_store("prop_change", "subobj_selection")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data)

        return True

    def delete(self, add_to_hist=True):

        obj_lvl = self._obj_level

        if obj_lvl == "normal":
            return False

        if not self._objs:
            return False

        geom_data_objs = list(self._groups.keys())

        self._groups = {}
        self._objs = []

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        for geom_data_obj in geom_data_objs:
            geom_data_obj.delete_selection(obj_lvl)

        if add_to_hist:

            Mgr.do("update_history_time")

            subobj_descr = {"vert": "vertex", "edge": "edge", "poly": "polygon", "normal": "normal"}
            event_descr = f'Delete {subobj_descr[obj_lvl]} selection'
            obj_data = {}
            event_data = {"objects": obj_data}

            for geom_data_obj in geom_data_objs:
                obj = geom_data_obj.toplevel_obj
                obj_data[obj.id] = geom_data_obj.get_data_to_store("subobj_change")

            # make undo/redoable
            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        return True


# subobject selection manager
class SelectionManager:

    def __init__(self):

        self._color_id = None
        self._selections = {}
        self._prev_obj_lvl = None
        self._next_selection = None
        self._selection_op = "replace"

        # the following variables are used to pick a subobject using its polygon
        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

        np = NodePath("poly_sel_state")
        poly_sel_state_off = np.get_state()
        tex_stage = TextureStage("poly_selection")
        tex_stage.sort = 100
        tex_stage.priority = -1
        tex_stage.mode = TextureStage.M_add
        np.set_transparency(TransparencyAttrib.M_none)
        projector = GD.cam.projector
        np.set_tex_gen(tex_stage, RenderAttrib.M_world_position)
        np.set_tex_projector(tex_stage, GD.world, projector)
        tex = Texture()
        tex.read(Filename(GFX_PATH + "sel_tex.png"))
        np.set_texture(tex_stage, tex)
        red = VBase4(1., 0., 0., 1.)
        material = Material("poly_selection")
        material.diffuse = red
        material.emission = red * .3
        np.set_material(material)
        poly_sel_state = np.get_state()
        poly_sel_effects = np.get_effects()
        color = VBase4(0., .7, .5, 1.)
        material = Material("temp_poly_selection")
        material.diffuse = color
        material.emission = color * .3
        np.set_material(material)
        tmp_poly_sel_state = np.get_state()
        Mgr.expose("poly_selection_state_off", lambda: poly_sel_state_off)
        Mgr.expose("poly_selection_state", lambda: poly_sel_state)
        Mgr.expose("poly_selection_effects", lambda: poly_sel_effects)
        Mgr.expose("temp_poly_selection_state", lambda: tmp_poly_sel_state)

        vert_colors = {"selected": (1., 0., 0., 1.), "unselected": (.5, .5, 1., 1.)}
        edge_colors = {"selected": (1., 0., 0., 1.), "unselected": (1., 1., 1., 1.)}
        normal_colors = {"selected": (1., 0.3, 0.3, 1.), "unselected": (.75, .75, 0., 1.),
                         "locked_sel": (0.75, 0.3, 1., 1.), "locked_unsel": (0.3, 0.5, 1., 1.)}
        subobj_sel_colors = {"vert": vert_colors, "edge": edge_colors, "normal": normal_colors}

        Mgr.expose("subobj_selection_colors", lambda: subobj_sel_colors)

        Mgr.expose("selection_vert", lambda: self._selections["vert"])
        Mgr.expose("selection_edge", lambda: self._selections["edge"])
        Mgr.expose("selection_poly", lambda: self._selections["poly"])
        Mgr.expose("selection_normal", lambda: self._selections["normal"])
        Mgr.expose("subobj_selection_set", self.__get_selection_set)
        Mgr.accept("update_selection_vert", lambda: self.__update_selection("vert"))
        Mgr.accept("update_selection_edge", lambda: self.__update_selection("edge"))
        Mgr.accept("update_selection_poly", lambda: self.__update_selection("poly"))
        Mgr.accept("update_selection_normal", lambda: self.__update_selection("normal"))
        Mgr.accept("select_vert", lambda *args: self.__init_select("vert", *args))
        Mgr.accept("select_edge", lambda *args: self.__init_select("edge", *args))
        Mgr.accept("select_poly", lambda *args: self.__init_select("poly", *args))
        Mgr.accept("select_normal", lambda *args: self.__init_select("normal", *args))
        Mgr.accept("select_single_vert", lambda: self.__select_single("vert"))
        Mgr.accept("select_single_edge", lambda: self.__select_single("edge"))
        Mgr.accept("select_single_poly", lambda: self.__select_single("poly"))
        Mgr.accept("select_single_normal", lambda: self.__select_single("normal"))
        Mgr.accept("inverse_select_subobjs", self.__inverse_select)
        Mgr.accept("select_all_subobjs", self.__select_all)
        Mgr.accept("clear_subobj_selection", self.__select_none)
        Mgr.accept("apply_subobj_selection_set", self.__apply_selection_set)
        Mgr.accept("region_select_subobjs", self.__region_select)
        Mgr.accept("init_selection_via_poly", self.__init_selection_via_poly)
        Mgr.add_app_updater("active_obj_level", lambda: self.__clear_prev_selection(True))
        Mgr.add_app_updater("picking_via_poly", self.__set_subobj_picking_via_poly)
        Mgr.add_app_updater("subobj_sel_conversion", self.__convert_subobj_selection)
        Mgr.add_app_updater("viewport", self.__handle_viewport_resize)

        add_state = Mgr.add_state
        add_state("picking_via_poly", -1, self.__init_subobj_picking_via_poly)

        bind = Mgr.bind_state
        bind("picking_via_poly", "select subobj via poly",
             "mouse1-up", self.__select_subobj_via_poly)
        bind("picking_via_poly", "cancel subobj select via poly",
             "mouse3", self.__cancel_select_via_poly)

        status_data = GD["status"]
        info = "LMB-drag over subobject to pick it; RMB to cancel"
        status_data["picking_via_poly"] = {"mode": "Pick subobject", "info": info}

    def __handle_viewport_resize(self):

        # Maintain the size and aspect ratio of the polygon selection texture.

        w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
        lenses = GD.cam.projector_lenses
        lens_persp = lenses["persp"]
        lens_persp.fov = 2. * math.degrees(math.atan(2.5 / max(w, h)))
        lens_ortho = lenses["ortho"]
        lens_ortho.film_size = 2000. / max(w, h)

    def __clear_prev_selection(self, check_top=False):

        obj_lvl = GD["active_obj_level"]

        if check_top and obj_lvl != "top":
            return

        if self._prev_obj_lvl:
            self._selections[self._prev_obj_lvl] = None
            self._prev_obj_lvl = None

        selection = Mgr.get("selection_top")
        sel_count = len(selection)
        obj = selection[0]
        geom_data_obj = obj.geom_obj.geom_data_obj

        for prop_id in geom_data_obj.get_type_property_ids(obj_lvl):
            value = geom_data_obj.get_property(prop_id, for_remote_update=True, obj_lvl=obj_lvl)
            value = (value, sel_count)
            Mgr.update_remotely("selected_obj_prop", "unlocked_geom", prop_id, value)

    def __update_selection(self, obj_lvl):

        self.__clear_prev_selection()
        subobjs = []

        for obj in Mgr.get("selection_top"):
            subobjs.extend(obj.get_subobj_selection(obj_lvl))

        self._selections[obj_lvl] = sel = Selection(obj_lvl, subobjs)

        if self._next_selection is not None:
            sel.replace(self._next_selection)
            self._next_selection = None

        sel.update()
        self._prev_obj_lvl = obj_lvl
        Mgr.update_remotely("selection_set", "hide_name")

    def __get_all_combined_subobjs(self, obj_lvl):

        subobjs = []
        geom_data_objs = [m.geom_obj.geom_data_obj for m in Mgr.get("selection_top")]

        if obj_lvl == "vert":
            for geom_data_obj in geom_data_objs:
                subobjs.extend(geom_data_obj.merged_verts.values())
        elif obj_lvl == "edge":
            for geom_data_obj in geom_data_objs:
                subobjs.extend(geom_data_obj.merged_edges.values())
        elif obj_lvl == "normal":
            for geom_data_obj in geom_data_objs:
                subobjs.extend(geom_data_obj.shared_normals.values())
        elif obj_lvl == "poly":
            for geom_data_obj in geom_data_objs:
                subobjs.extend(geom_data_obj.get_subobjects("poly").values())

        return subobjs

    def __inverse_select(self):

        obj_lvl = GD["active_obj_level"]
        selection = self._selections[obj_lvl]
        old_sel = set(selection)
        new_sel = set(self.__get_all_combined_subobjs(obj_lvl))
        selection.replace(new_sel - old_sel)
        Mgr.update_remotely("selection_set", "hide_name")

    def __select_all(self):

        obj_lvl = GD["active_obj_level"]
        selection = self._selections[obj_lvl]
        selection.replace(self.__get_all_combined_subobjs(obj_lvl))
        Mgr.update_remotely("selection_set", "hide_name")

    def __select_none(self):

        obj_lvl = GD["active_obj_level"]
        selection = self._selections[obj_lvl]
        selection.clear()
        Mgr.update_remotely("selection_set", "hide_name")

    def __get_selection_set(self):

        obj_lvl = GD["active_obj_level"]
        selection = self._selections[obj_lvl]

        if obj_lvl == "poly":
            return set(obj.id for obj in selection)
        else:
            return set(obj_id for obj in selection for obj_id in obj)

    def __apply_selection_set(self, sel_set):

        obj_lvl = GD["active_obj_level"]
        selection = self._selections[obj_lvl]
        geom_data_objs = [m.geom_obj.geom_data_obj for m in Mgr.get("selection_top")]
        combined_subobjs = {}

        if obj_lvl == "vert":
            for geom_data_obj in geom_data_objs:
                combined_subobjs.update(geom_data_obj.merged_verts)
        elif obj_lvl == "edge":
            for geom_data_obj in geom_data_objs:
                combined_subobjs.update(geom_data_obj.merged_edges)
        elif obj_lvl == "normal":
            for geom_data_obj in geom_data_objs:
                combined_subobjs.update(geom_data_obj.shared_normals)
        elif obj_lvl == "poly":
            for geom_data_obj in geom_data_objs:
                combined_subobjs.update(geom_data_obj.get_subobjects("poly"))

        new_sel = set(combined_subobjs.get(obj_id) for obj_id in sel_set)
        new_sel.discard(None)
        selection.replace(new_sel)

    def __init_select(self, obj_lvl, picked_obj, op):

        self._selection_op = op

        if obj_lvl == "vert":

            if GD["subobj_edit_options"]["pick_via_poly"]:
                obj = picked_obj if picked_obj and picked_obj.type == "poly" else None
                self._picked_poly = obj
            else:
                obj = picked_obj.merged_vertex if picked_obj else None

        elif obj_lvl == "edge":

            if GD["subobj_edit_options"]["pick_via_poly"]:

                obj = picked_obj if picked_obj and picked_obj.type == "poly" else None

                if obj and GD["subobj_edit_options"]["sel_edges_by_border"]:

                    merged_edges = obj.geom_data_obj.merged_edges

                    for edge_id in obj.edge_ids:
                        if len(merged_edges[edge_id]) == 1:
                            break
                    else:
                        obj = None

                self._picked_poly = obj

            else:

                obj = picked_obj.merged_edge if picked_obj else None

                if obj and GD["subobj_edit_options"]["sel_edges_by_border"] and len(obj) > 1:
                    obj = None

        elif obj_lvl == "normal":

            if GD["subobj_edit_options"]["pick_via_poly"]:
                obj = picked_obj if picked_obj and picked_obj.type == "poly" else None
                self._picked_poly = obj
            else:
                obj = picked_obj.shared_normal if picked_obj else None

        elif obj_lvl == "poly":

            obj = picked_obj

        if self._picked_poly:
            Mgr.enter_state("picking_via_poly")
            return False, False

        self._color_id = obj.picking_color_id if obj else None
        r = self.__select(obj_lvl)
        selection = self._selections[obj_lvl]

        if not (obj and obj in selection):
            obj = selection[0] if selection else None

        if obj:

            cs_type = GD["coord_sys_type"]
            tc_type = GD["transf_center_type"]
            toplvl_obj = obj.toplevel_obj

            if cs_type == "local":
                Mgr.update_locally("coord_sys", cs_type, toplvl_obj)

            if tc_type == "pivot":
                Mgr.update_locally("transf_center", tc_type, toplvl_obj)

        return r

    def __select(self, obj_lvl, ignore_transform=False):

        if obj_lvl == "normal":
            obj = Mgr.get("vert", self._color_id)
        else:
            obj = Mgr.get(obj_lvl, self._color_id)

        if obj_lvl == "vert":
            obj = obj.merged_vertex if obj else None
        elif obj_lvl == "edge":
            obj = obj.merged_edge if obj else None
        elif obj_lvl == "normal":
            obj = obj.shared_normal if obj else None

        selection = self._selections[obj_lvl]
        can_select_single = False
        start_mouse_checking = False
        op = self._selection_op

        if obj:

            if op == "replace":

                if GD["active_transform_type"] and not ignore_transform:

                    if obj in selection and len(selection) > 1:

                        # When the user clicks one of multiple selected objects, updating the
                        # selection must be delayed until it is clear whether he wants to
                        # transform the entire selection or simply have only this object
                        # selected (this is determined by checking if the mouse has moved at
                        # least a certain number of pixels by the time the left mouse button
                        # is released).

                        can_select_single = True

                    else:

                        selection.replace(obj.special_selection)

                    start_mouse_checking = True

                else:

                    selection.replace(obj.special_selection)

            elif op == "add":

                selection.add(obj.special_selection)
                transform_allowed = GD["active_transform_type"]

                if transform_allowed:
                    start_mouse_checking = True

            elif op == "remove":

                selection.remove(obj.special_selection)

            elif op == "toggle":

                old_sel = set(selection)
                new_sel = set(obj.special_selection)
                selection.replace(old_sel ^ new_sel)

                if obj in selection:
                    transform_allowed = GD["active_transform_type"]
                else:
                    transform_allowed = False

                if transform_allowed:
                    start_mouse_checking = True

        elif op == "replace":

            selection.clear()

        Mgr.update_remotely("selection_set", "hide_name")

        return can_select_single, start_mouse_checking

    def __select_single(self, obj_lvl):

        # If multiple objects were selected and no transformation occurred, a single
        # object has been selected out of that previous selection.

        if obj_lvl == "normal":
            obj = Mgr.get("vert", self._color_id)
        else:
            obj = Mgr.get(obj_lvl, self._color_id)

        if obj_lvl == "vert":
            obj = obj.merged_vertex if obj else None
        elif obj_lvl == "edge":
            obj = obj.merged_edge if obj else None
        elif obj_lvl == "normal":
            obj = obj.shared_normal if obj else None

        self._selections[obj_lvl].replace(obj.special_selection)

    def __region_select(self, cam, lens_exp, tex_buffer, ellipse_data, mask_tex, op):

        obj_lvl = GD["active_obj_level"]

        subobjs = {}
        index_offset = 0

        for obj in Mgr.get("selection_top"):

            geom_data_obj = obj.geom_obj.geom_data_obj
            obj_type = "vert" if obj_lvl == "normal" else obj_lvl
            indexed_subobjs = geom_data_obj.get_indexed_subobjects(obj_type)

            for index, subobj in indexed_subobjs.items():
                subobjs[index + index_offset] = subobj

            geom_data_obj.origin.set_shader_input("index_offset", index_offset)
            index_offset += len(indexed_subobjs)

        ge = GD.graphics_engine
        obj_count = len(subobjs)
        region_type = GD["region_select"]["type"]
        subobj_edit_options = GD["subobj_edit_options"]
        pick_via_poly = subobj_edit_options["pick_via_poly"]

        if pick_via_poly:
            Mgr.update_locally("picking_via_poly", False)

        def region_select_objects(sel, enclose=False):

            tex = Texture()
            tex.setup_1d_texture(obj_count, Texture.T_int, Texture.F_r32i)
            tex.clear_color = (0., 0., 0., 0.)
            sh = shaders.region_sel

            if "rect" in region_type or "square" in region_type:
                fs = sh.FRAG_SHADER_INV if enclose else sh.FRAG_SHADER
            elif "ellipse" in region_type or "circle" in region_type:
                fs = sh.FRAG_SHADER_ELLIPSE_INV if enclose else sh.FRAG_SHADER_ELLIPSE
            else:
                fs = sh.FRAG_SHADER_FREE_INV if enclose else sh.FRAG_SHADER_FREE

            if obj_lvl == "normal":
                sh = shaders.region_sel_normal
                vs = sh.VERT_SHADER
                gs = sh.GEOM_SHADER
                shader = Shader.make(Shader.SL_GLSL, vs, fs, gs)
            else:
                vs = shaders.region_sel_subobj.VERT_SHADER
                shader = Shader.make(Shader.SL_GLSL, vs, fs)

            state_np = NodePath("state_np")
            state_np.set_shader(shader, 1)
            state_np.set_shader_input("selections", tex, read=False, write=True)

            if "ellipse" in region_type or "circle" in region_type:
                state_np.set_shader_input("ellipse_data", Vec4(*ellipse_data))
            elif region_type in ("fence", "lasso", "paint"):
                if enclose:
                    img = PNMImage()
                    mask_tex.store(img)
                    img.expand_border(2, 2, 2, 2, (0., 0., 0., 0.))
                    mask_tex.load(img)
                state_np.set_shader_input("mask_tex", mask_tex)
            elif enclose:
                w_b, h_b = tex_buffer.get_size()
                state_np.set_shader_input("buffer_size", Vec2(w_b + 2, h_b + 2))

            state = state_np.get_state()
            cam.node().initial_state = state

            ge.render_frame()

            if ge.extract_texture_data(tex, GD.window.get_gsg()):

                texels = memoryview(tex.get_ram_image()).cast("I")

                if obj_lvl == "edge":

                    sel_edges_by_border = subobj_edit_options["sel_edges_by_border"]

                    for i, mask in enumerate(texels):
                        for j in range(32):
                            if mask & (1 << j):
                                index = 32 * i + j
                                subobj = subobjs[index].merged_subobj
                                if not sel_edges_by_border or len(subobj) == 1:
                                    sel.update(subobj.special_selection)

                elif obj_lvl == "normal":

                    for i, mask in enumerate(texels):
                        for j in range(32):
                            if mask & (1 << j):
                                index = 32 * i + j
                                subobj = subobjs[index].shared_normal
                                sel.update(subobj.special_selection)

                else:

                    for i, mask in enumerate(texels):
                        for j in range(32):
                            if mask & (1 << j):
                                index = 32 * i + j
                                subobj = subobjs[index].merged_subobj
                                sel.update(subobj.special_selection)

            state_np.clear_attrib(ShaderAttrib)

        new_sel = set()
        region_select_objects(new_sel)
        ge.remove_window(tex_buffer)

        if GD["region_select"]["enclose"]:
            w_b, h_b = tex_buffer.get_size()
            bfr_exp = GD.window.make_texture_buffer("tex_buffer_exp", w_b + 4, h_b + 4)
            GD.showbase.make_camera(bfr_exp, useCamera=cam)
            cam.node().set_lens(lens_exp)
            inverse_sel = set()
            region_select_objects(inverse_sel, True)
            new_sel -= inverse_sel
            ge.remove_window(bfr_exp)

        if pick_via_poly:
            Mgr.update_locally("picking_via_poly", True)

        selection = self._selections[obj_lvl]

        if op == "replace":
            selection.replace(new_sel)
        elif op == "add":
            selection.add(new_sel)
        elif op == "remove":
            selection.remove(new_sel)
        elif op == "toggle":
            old_sel = set(selection)
            selection.replace(old_sel ^ new_sel)

    def __set_subobj_picking_via_poly(self, via_poly=False):

        GD["subobj_edit_options"]["pick_via_poly"] = via_poly

        if not via_poly:

            models = Mgr.get("model_objs")

            for model in models:
                if model.geom_type == "unlocked_geom":
                    geom_data_obj = model.geom_obj.geom_data_obj
                    geom_data_obj.restore_selection_backup("poly")

        obj_lvl = GD["active_obj_level"]

        if obj_lvl not in ("vert", "edge", "normal"):
            return

        for obj in Mgr.get("selection_top"):
            obj.geom_obj.geom_data_obj.init_subobj_picking(obj_lvl)

    def __init_selection_via_poly(self, picked_poly, op):

        if picked_poly:
            Mgr.get("transf_gizmo").set_pickable(False)
            self._picked_poly = picked_poly
            self._selection_op = op
            Mgr.enter_state("picking_via_poly")

    def __init_subobj_picking_via_poly(self, prev_state_id, active):

        Mgr.add_task(self.__hilite_subobj, "hilite_subobj")
        Mgr.remove_task("update_cursor")
        subobj_lvl = GD["active_obj_level"]

        if subobj_lvl == "edge" and GD["subobj_edit_options"]["sel_edges_by_border"]:
            category = "border"
        else:
            category = ""

        geom_data_obj = self._picked_poly.geom_data_obj
        geom_data_obj.init_subobj_picking_via_poly(subobj_lvl, self._picked_poly, category)
        # temporarily select picked poly
        geom_data_obj.update_selection("poly", [self._picked_poly], [], False)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.geom_obj.geom_data_obj

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable(False)

        Mgr.update_app("status", ["picking_via_poly"])

        cs_type = GD["coord_sys_type"]
        tc_type = GD["transf_center_type"]
        toplvl_obj = self._picked_poly.toplevel_obj

        if cs_type == "local":
            Mgr.update_locally("coord_sys", cs_type, toplvl_obj)

        if tc_type == "pivot":
            Mgr.update_locally("transf_center", tc_type, toplvl_obj)

    def __hilite_subobj(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")
        active_transform_type = GD["active_transform_type"]

        if self._pixel_under_mouse != pixel_under_mouse:

            if pixel_under_mouse == VBase4():

                if active_transform_type and self._tmp_color_id is not None:
                    self.__select_subobj_via_poly(transform=True)
                    return

            else:

                r, g, b, a = [int(round(c * 255.)) for c in pixel_under_mouse]
                color_id = r << 16 | g << 8 | b
                geom_data_obj = self._picked_poly.geom_data_obj
                subobj_lvl = GD["active_obj_level"]

                # highlight temporary subobject
                if geom_data_obj.hilite_temp_subobject(subobj_lvl, color_id):
                    self._tmp_color_id = color_id

            self._pixel_under_mouse = pixel_under_mouse

        not_hilited = pixel_under_mouse in (VBase4(), VBase4(1., 1., 1., 1.))
        cursor_id = "main" if not_hilited else ("select" if not active_transform_type
                                                else active_transform_type)

        if GD["subobj_edit_options"]["pick_by_aiming"]:

            aux_pixel_under_mouse = Mgr.get("aux_pixel_under_mouse")

            if not_hilited or self._aux_pixel_under_mouse != aux_pixel_under_mouse:

                if not_hilited and aux_pixel_under_mouse != VBase4():

                    r, g, b, a = [int(round(c * 255.)) for c in aux_pixel_under_mouse]
                    color_id = r << 16 | g << 8 | b
                    geom_data_obj = self._picked_poly.geom_data_obj
                    subobj_lvl = GD["active_obj_level"]

                    # highlight temporary subobject
                    if geom_data_obj.hilite_temp_subobject(subobj_lvl, color_id):
                        self._tmp_color_id = color_id
                        cursor_id = "select" if not active_transform_type else active_transform_type

                self._aux_pixel_under_mouse = aux_pixel_under_mouse

        if self._cursor_id != cursor_id:
            Mgr.set_cursor(cursor_id)
            self._cursor_id = cursor_id

        return task.cont

    def __select_subobj_via_poly(self, transform=False):

        Mgr.remove_task("hilite_subobj")
        Mgr.enter_state("selection_mode")
        subobj_lvl = GD["active_obj_level"]
        geom_data_obj = self._picked_poly.geom_data_obj

        if self._tmp_color_id is None:

            obj = None

        else:

            if subobj_lvl == "vert":
                vert_id = Mgr.get("vert", self._tmp_color_id).id
                obj = geom_data_obj.get_merged_vertex(vert_id)
            elif subobj_lvl == "edge":
                edge_id = Mgr.get("edge", self._tmp_color_id).id
                obj = geom_data_obj.get_merged_edge(edge_id)
                obj = (None if GD["subobj_edit_options"]["sel_edges_by_border"]
                       and len(obj) > 1 else obj)
            elif subobj_lvl == "normal":
                vert_id = Mgr.get("vert", self._tmp_color_id).id
                obj = geom_data_obj.get_shared_normal(vert_id)

        self._color_id = obj.picking_color_id if obj else None

        ignore_transform = not transform
        self.__select(subobj_lvl, ignore_transform)

        geom_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.geom_obj.geom_data_obj

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None
        active_transform_type = GD["active_transform_type"]

        if transform and obj and obj.geom_data_obj.is_selected(obj):

            if active_transform_type == "translate":
                picked_point = obj.get_center_pos(GD.world)
            elif GD.mouse_watcher.has_mouse():
                screen_pos = Point2(GD.mouse_watcher.get_mouse())
                picked_point = obj.get_point_at_screen_pos(screen_pos)
            else:
                picked_point = None

            if picked_point:
                selection = self._selections[subobj_lvl]
                selection.update(hide_sets=True)
                Mgr.do("init_transform", picked_point)

            Mgr.set_cursor(active_transform_type)

        if active_transform_type:
            Mgr.get("transf_gizmo").set_pickable()

    def __cancel_select_via_poly(self):

        Mgr.remove_task("hilite_subobj")
        Mgr.enter_state("selection_mode")
        subobj_lvl = GD["active_obj_level"]

        geom_data_obj = self._picked_poly.geom_data_obj
        geom_data_obj.prepare_subobj_picking_via_poly(subobj_lvl)

        for model in Mgr.get("selection_top"):

            other_geom_data_obj = model.geom_obj.geom_data_obj

            if other_geom_data_obj is not geom_data_obj:
                other_geom_data_obj.set_pickable()

        self._picked_poly = None
        self._tmp_color_id = None
        self._cursor_id = ""
        self._pixel_under_mouse = None
        self._aux_pixel_under_mouse = None

        if GD["active_transform_type"]:
            Mgr.get("transf_gizmo").set_pickable()

    def __convert_subobj_selection_touching(self, next_subobj_lvl):

        subobj_lvl = GD["active_obj_level"]
        self._next_selection = next_sel = set()
        selection = self._selections[subobj_lvl]

        if not selection:
            return

        if next_subobj_lvl == "normal":
            for subobj in selection:
                next_sel.update(v.shared_normal for v in subobj.connected_verts)
        else:
            for subobj in selection:
                next_sel.update(s.merged_subobj for s in
                    subobj.get_connected_subobjs(next_subobj_lvl))

    def __convert_subobj_selection_containing(self, next_subobj_lvl):

        lvls = {"vert": 0, "normal": 0, "edge": 1, "poly": 2}
        subobj_lvl = GD["active_obj_level"]
        self._next_selection = next_sel = set()
        selection = self._selections[subobj_lvl]

        if not selection:
            return

        if subobj_lvl == "edge" and next_subobj_lvl == "normal":
            for merged_edge in selection:
                next_sel.update(v.shared_normal for v in merged_edge.vertices)
        elif subobj_lvl == "poly" and next_subobj_lvl == "normal":
            for poly in selection:
                next_sel.update(v.shared_normal for v in poly.vertices)
        elif subobj_lvl == "poly" and next_subobj_lvl == "edge":
            for poly in selection:
                next_sel.update(e.merged_edge for e in poly.edges)
        elif lvls[next_subobj_lvl] > lvls[subobj_lvl]:
            if next_subobj_lvl == "edge":
                for subobj in selection:
                    if subobj_lvl == "vert":
                        next_sel.update(e.merged_edge for e in subobj.connected_edges
                            if all(v.merged_vertex in selection for v in e.vertices))
                    else:  # subobj_lvl == "normal"
                        next_sel.update(e.merged_edge for e in subobj.connected_edges
                            if all(v.shared_normal in selection for v in e.vertices))
            else:  # next_subobj_lvl == "poly"
                for subobj in selection:
                    if subobj_lvl == "vert":
                        next_sel.update(p for p in subobj.connected_polys
                            if all(v.merged_vertex in selection for v in p.vertices))
                    elif subobj_lvl == "normal":
                        next_sel.update(p for p in subobj.connected_polys
                            if all(v.shared_normal in selection for v in p.vertices))
                    else:  # subobj_lvl == "edge"
                        next_sel.update(p for p in subobj.connected_polys
                            if all(e.merged_edge in selection for e in p.edges))
        else:
            self.__convert_subobj_selection_touching(next_subobj_lvl)

    def __convert_subobj_selection_bordering(self, next_subobj_lvl):

        lvls = {"vert": 0, "normal": 0, "edge": 1, "poly": 2}
        subobj_lvl = GD["active_obj_level"]
        selection = self._selections[subobj_lvl]

        if not selection:
            return

        if subobj_lvl == "poly":
            poly_set = set(selection)
        else:
            self.__convert_subobj_selection_containing("poly")
            poly_set = self._next_selection

        def is_border_edge(edge):

            polys = edge.geom_data_obj.get_subobjects("poly")

            return len(set(polys[p_id] for p_id in edge.merged_edge.polygon_ids)
                    & poly_set) == 1

        border_edges = (e for p in poly_set for e in p.edges if is_border_edge(e))

        if next_subobj_lvl == "normal":
            self._next_selection = set(v.shared_normal for e in border_edges
                for v in e.vertices)
        elif next_subobj_lvl == "vert":
            self._next_selection = set(v.merged_vertex for e in border_edges
                for v in e.vertices)
        elif next_subobj_lvl == "edge":
            self._next_selection = set(e.merged_edge for e in border_edges)
        else:  # next_subobj_lvl == "poly"
            self._next_selection = set(e.polygon for e in border_edges)

    def __convert_subobj_selection(self, next_subobj_lvl, conversion_type):

        if conversion_type == "touching":
            self.__convert_subobj_selection_touching(next_subobj_lvl)
        elif conversion_type == "containing":
            self.__convert_subobj_selection_containing(next_subobj_lvl)
        elif conversion_type == "bordering":
            self.__convert_subobj_selection_bordering(next_subobj_lvl)


MainObjects.add_class(SelectionManager)
