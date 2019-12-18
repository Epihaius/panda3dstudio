from .base import *


class HierarchyManager:

    def __init__(self):

        self._obj_link_viz_nps = NodePathCollection()
        self._obj_link_viz = {}
        self._obj_to_link = None
        self._pixel_under_mouse = None

        status_data = GD["status"]
        mode_text = "Link selection"
        info_text = "LMB to pick parent object; RMB or <Escape> to end"
        status_data["sel_linking_mode"] = {"mode": mode_text, "info": info_text}
        mode_text = "Link object"
        info_text = "LMB-drag over first (child) object and release LMB over" \
                    " second (parent) object; RMB or <Escape> to end"
        status_data["obj_linking_mode"] = {"mode": mode_text, "info": info_text}
        mode_text = "Unlink object"
        info_text = "LMB to pick child object; RMB or <Escape> to end"
        status_data["obj_unlinking_mode"] = {"mode": mode_text, "info": info_text}

        GD.set_default("object_links_shown", False)
        GD.set_default("object_linking_mode", "")
        GD.set_default("transform_target_type", "all")
        Mgr.accept("add_obj_link_viz", self.__add_obj_link_viz)
        Mgr.accept("remove_obj_link_viz", self.__remove_obj_link_viz)
        Mgr.accept("update_obj_link_viz", self.__update_obj_link_viz)
        Mgr.accept("update_xform_target_type", self.__update_xform_target_type)
        Mgr.add_app_updater("object_link_viz", self.__show_object_links)
        Mgr.add_app_updater("selection_unlinking", self.__unlink_objects)
        Mgr.add_app_updater("transform_target_type", self.__update_pivot_viz)
        Mgr.add_app_updater("geom_reset", self.__reset_geoms)
        Mgr.add_app_updater("pivot_reset", self.__reset_pivots)

        add_state = Mgr.add_state
        add_state("object_linking_mode", -10, self.__enter_linking_mode,
                  self.__exit_linking_mode)
        add_state("object_link_creation", -11)

        cancel_link_creation = lambda: self.__finalize_object_linking(cancel=True)

        def exit_mode():

            Mgr.exit_state("object_linking_mode")
            GD["object_linking_mode"] = ""

        bind = Mgr.bind_state
        bind("object_linking_mode", "link objects -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("object_linking_mode", "link objects -> select", "escape", exit_mode)
        bind("object_linking_mode", "exit object linking mode", "mouse3", exit_mode)
        bind("object_linking_mode", "handle linking", "mouse1", self.__handle_linking)
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("object_linking_mode", "link objects ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))
        bind("object_link_creation", "quit link creation", "escape", cancel_link_creation)
        bind("object_link_creation", "cancel link creation", "mouse3", cancel_link_creation)
        bind("object_link_creation", "finalize link creation",
             "mouse1-up", self.__finalize_object_linking)

    def __enter_linking_mode(self, prev_state_id, active):

        if prev_state_id == "object_link_creation":
            return

        Mgr.add_task(self.__update_cursor, "update_linking_cursor")

        if GD["active_transform_type"]:
            GD["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")

        object_linking_mode = GD["object_linking_mode"]
        Mgr.update_app("status", [object_linking_mode])

        if not active:

            if object_linking_mode == "sel_linking_mode":

                def handler(obj_ids):

                    if obj_ids:
                        obj = Mgr.get("object", obj_ids[0])
                        self.__link_selection(picked_obj=obj)

                Mgr.update_remotely("selection_by_name", "", "Pick object to link to",
                                    None, False, "Pick", handler)

            elif object_linking_mode == "obj_unlinking_mode":

                def handler(obj_ids):

                    if obj_ids:
                        objs = [Mgr.get("object", obj_id) for obj_id in obj_ids]
                        self.__unlink_objects(picked_objs=objs)

                Mgr.update_remotely("selection_by_name", "", "Pick objects to unlink",
                                    None, True, "Pick", handler)

    def __exit_linking_mode(self, next_state_id, active):

        if next_state_id == "object_link_creation":
            return

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self.__update_cursor()
                                        # is called
        Mgr.remove_task("update_linking_cursor")
        Mgr.set_cursor("main")

        if not active:
            Mgr.update_remotely("selection_by_name", "default")

    def __show_object_links(self):

        show_links = GD["object_links_shown"]

        if show_links:
            self._obj_link_viz_nps.show()
        else:
            self._obj_link_viz_nps.hide()

    def __get_linkability(self, obj_to_link, target_obj):

        target_is_group = target_obj and target_obj.type == "group"
        objs = obj_to_link.descendants + [obj_to_link]
        member_linking = GD["group_options"]["member_linking"]

        if (target_is_group and member_linking["allowed"]
                and not member_linking["unlink_only"]
                and (target_obj.is_open() or not member_linking["open_groups_only"])):
            objs += [obj_to_link.group]
            linkable = target_obj.can_contain(obj_to_link) and target_obj not in objs
            link_type = "member"
        else:
            objs += [obj_to_link.parent]
            group = target_obj.group if target_obj else None
            linkable = not (group or target_obj in objs)
            link_type = "child"

        return linkable, link_type

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            self._pixel_under_mouse = pixel_under_mouse
            cursor_id = "main"

            if pixel_under_mouse != VBase4():

                obj_to_link = self._obj_to_link

                if obj_to_link:

                    target_obj = Mgr.get("object", pixel_color=pixel_under_mouse)
                    linkable, link_type = self.__get_linkability(obj_to_link, target_obj)

                    if target_obj and linkable:
                        cursor_id = "link"
                    else:
                        cursor_id = "no_link"

                else:

                    cursor_id = "select"

            Mgr.set_cursor(cursor_id)

        return task.cont

    def __add_obj_link_viz(self, child, parent):

        child_id = child.id
        parent_pivot = parent.pivot

        if child_id in self._obj_link_viz:
            link_geom = self._obj_link_viz[child_id]
            self._obj_link_viz_nps.remove_path(link_geom)
            link_geom.detach_node()

        vertex_format = GeomVertexFormat.get_v3c4()

        vertex_data = GeomVertexData("link_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        pos_writer.add_data3(0., 0., 0.)
        col_writer.add_data4(1., 1., 1., 1.)
        pos_writer.add_data3(child.pivot.get_pos(parent_pivot))
        col_writer.add_data4(.25, .25, .25, 1.)

        lines = GeomLines(Geom.UH_static)
        lines.add_next_vertices(2)

        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        node = GeomNode("object_link")
        node.add_geom(lines_geom)
        link_geom = parent_pivot.attach_new_node(node)
        link_geom.set_light_off()
        link_geom.set_shader_off()
        link_geom.set_bin("fixed", 100)
        link_geom.set_depth_test(False)
        link_geom.set_depth_write(False)
        link_geom.hide(Mgr.get("picking_mask"))
        self._obj_link_viz[child_id] = link_geom
        self._obj_link_viz_nps.add_path(link_geom)

        if not GD["object_links_shown"]:
            link_geom.hide()

    def __remove_obj_link_viz(self, child_id):

        if child_id not in self._obj_link_viz:
            return

        link_geom = self._obj_link_viz[child_id]
        self._obj_link_viz_nps.remove_path(link_geom)
        link_geom.detach_node()
        del self._obj_link_viz[child_id]

    def __update_obj_link_viz(self, obj_ids=None, force_update_children=False):

        def task():

            obj_transf_info = obj_ids if obj_ids else Mgr.get("obj_transf_info")
            obj_link_viz = self._obj_link_viz
            update_children = GD["transform_target_type"] in ("pivot",
                              "no_children") or force_update_children

            for obj_id in obj_transf_info:

                if obj_id in obj_link_viz:

                    link_viz = obj_link_viz[obj_id]
                    obj = Mgr.get("object", obj_id)
                    parent = obj.parent
                    vertex_data = link_viz.node().modify_geom(0).modify_vertex_data()
                    pos_writer = GeomVertexWriter(vertex_data, "vertex")
                    pos_writer.set_row(1)
                    pivot = obj.pivot
                    pos_writer.set_data3(pivot.get_pos(parent.pivot))

                    if update_children:
                        for child in obj.children:
                            child_link_viz = obj_link_viz[child.id]
                            vertex_data = child_link_viz.node().modify_geom(0).modify_vertex_data()
                            pos_writer = GeomVertexWriter(vertex_data, "vertex")
                            pos_writer.set_row(1)
                            pos_writer.set_data3(child.pivot.get_pos(pivot))

                elif update_children:

                    obj = Mgr.get("object", obj_id)
                    pivot = obj.pivot

                    for child in obj.children:
                        child_link_viz = obj_link_viz[child.id]
                        vertex_data = child_link_viz.node().modify_geom(0).modify_vertex_data()
                        pos_writer = GeomVertexWriter(vertex_data, "vertex")
                        pos_writer.set_row(1)
                        pos_writer.set_data3(child.pivot.get_pos(pivot))

        task_id = "obj_link_viz_update"
        PendingTasks.add(task, task_id, "object")

    def __handle_linking(self):

        linking_mode = GD["object_linking_mode"]

        if linking_mode == "sel_linking_mode":
            self.__link_selection()
        elif linking_mode == "obj_linking_mode":
            self.__init_object_linking()
        elif linking_mode == "obj_unlinking_mode":
            self.__unlink_object()

    def __init_object_linking(self):

        obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if not obj:
            return

        self._obj_to_link = obj
        pivot_pos = obj.pivot.get_pos(GD.world)
        Mgr.do("start_drawing_rubber_band", pivot_pos)
        Mgr.enter_state("object_link_creation")
        Mgr.set_cursor("no_link")

    def __finalize_object_linking(self, cancel=False):

        if not cancel:
            self.__link_picked_object()

        Mgr.do("end_drawing_rubber_band")
        Mgr.enter_state("object_linking_mode")
        Mgr.set_cursor("main" if self._pixel_under_mouse == VBase4() else "select")

        self._obj_to_link = None

    def __link_object(self, obj_to_link, new_target, link_type):

        old_target = obj_to_link.link_target
        old_target_is_group = old_target and old_target.type == "group"
        target_id = new_target.id

        if link_type == "child":

            obj_to_link.parent = target_id

        else:

            obj_to_link.group = target_id
            children = obj_to_link.children
            parent_id = new_target.outermost_group.id

            for child in children:
                child.parent = parent_id

        if link_type == "member" and not new_target.is_open():

            closed_groups = []
            deselected_members = []
            Mgr.do("close_groups", [obj_to_link], closed_groups, deselected_members)

            if closed_groups:

                # make undo/redoable

                obj_data = {}
                event_data = {"objects": obj_data}

                for group in closed_groups:
                    obj_data[group.id] = group.get_data_to_store("prop_change", "open")

                for member in deselected_members:
                    data = member.get_data_to_store("prop_change", "selection_state")
                    obj_data.setdefault(member.id, {}).update(data)

                Mgr.do("add_history", "", event_data, update_time_id=False)

            obj_to_link_deselected = obj_to_link.set_selected(False, add_to_hist=False)

            if obj_to_link_deselected or deselected_members:

                # make undo/redoable

                obj_data = {}
                event_data = {"objects": obj_data}

                if obj_to_link_deselected:
                    data = obj_to_link.get_data_to_store("prop_change", "selection_state")
                    obj_data.setdefault(obj_to_link.id, {}).update(data)

                if new_target.set_selected(add_to_hist=False):
                    data = new_target.get_data_to_store("prop_change", "selection_state")
                    obj_data[target_id] = data

                Mgr.do("add_history", "", event_data, update_time_id=False)

        if link_type == "member" and children:

            # make undo/redoable

            obj_data = {}
            event_data = {"objects": obj_data}

            for child in children:
                data = child.get_data_to_store("prop_change", "link")
                data.update(child.get_data_to_store("prop_change", "transform"))
                obj_data[child.id] = data

            Mgr.do("add_history", "", event_data, update_time_id=False)

        if old_target_is_group:

            obj_data = {}

            if Mgr.do("prune_empty_groups", [old_target], obj_data):
                # make undo/redoable
                event_data = {"objects": obj_data, "object_ids": set(Mgr.get("object_ids"))}
                Mgr.do("add_history", "", event_data, update_time_id=False)

    def __link_picked_object(self):

        obj_to_link = self._obj_to_link

        if not obj_to_link:
            return

        new_target = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if not new_target:
            return

        linkable, link_type = self.__get_linkability(obj_to_link, new_target)

        if not linkable:
            return

        Mgr.do("update_history_time")

        self.__link_object(obj_to_link, new_target, link_type)

        # make undo/redoable
        data = obj_to_link.get_data_to_store("prop_change", "link")
        data.update(obj_to_link.get_data_to_store("prop_change", "transform"))
        obj_data = {obj_to_link.id: data}

        if link_type == "child":
            event_descr = f'Link "{obj_to_link.name}"\nto "{new_target.name}"'
        else:
            event_descr = f'Add to group "{new_target.name}":\n    "{obj_to_link.name}"'

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        new_target_is_group = new_target.type == "group"

        if link_type == "child" and not (new_target_is_group and not new_target.get_members()):
            new_target.display_link_effect()

    def __link_selection(self, picked_obj=None):

        new_target = picked_obj if picked_obj else Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if not new_target:
            return

        selection = Mgr.get("selection_top")

        if not selection:
            return

        children = []
        members = []
        groups = []
        group_children = {}

        for obj in selection:

            linkable, link_type = self.__get_linkability(obj, new_target)

            if not linkable:
                continue

            if obj.type == "group":
                groups.append(obj)
                group_children[obj] = obj.children

            if link_type == "child":
                children.append(obj)
            else:
                members.append(obj)

        if not (children or members):
            return

        Mgr.do("update_history_time")

        for child in children:
            if child not in groups:
                self.__link_object(child, new_target, "child")

        for member in members:
            if member not in groups:
                self.__link_object(member, new_target, "member")

        for group in groups:
            if group in children:
                if group.get_members():
                    del group_children[group]
                    self.__link_object(group, new_target, "child")
                else:
                    children.remove(group)
            else:
                if group.get_members():
                    del group_children[group]
                    self.__link_object(group, new_target, "member")
                else:
                    members.remove(group)

        group_children = [child for group, c in group_children.items() for child in c]
        new_target_id = new_target.id

        for child in group_children:
            child.parent = new_target_id

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}

        for obj in children + members:
            data = obj.get_data_to_store("prop_change", "link")
            data.update(obj.get_data_to_store("prop_change", "transform"))
            obj_data[obj.id] = data

        for child in group_children:
            data = child.get_data_to_store("prop_change", "link")
            data.update(child.get_data_to_store("prop_change", "transform"))
            obj_data.setdefault(child.id, {}).update(data)

        if children:

            if len(children) == 1:

                event_descr = f'Link "{children[0].name}"\nto "{new_target.name}"'

            else:

                event_descr = f'Link objects to "{new_target.name}":\n'

                for child in children:
                    event_descr += f'\n    "{child.name}"'

        elif members:

            if len(members) == 1:

                event_descr = f'Add to group "{new_target.name}":\n    "{members[0].name}"'

            else:

                event_descr = f'Add to group "{new_target.name}":\n'

                for member in members:
                    event_descr += f'\n    "{member.name}"'

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        new_target_is_group = new_target.type == "group"

        if children and not (new_target_is_group and not new_target.get_members()):
            new_target.display_link_effect()

    def __unlink_object(self, picked_obj=None):

        obj = picked_obj if picked_obj else Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if not obj:
            return

        affect_group_members = GD["group_options"]["member_linking"]["allowed"]
        ungrouped = False
        unlinked = False

        group = obj.group
        groups = [group] if group else []

        if group:
            if affect_group_members and obj.set_group(None):
                ungrouped = True
        elif obj.set_parent(None):
            unlinked = True

        change = ungrouped or unlinked

        if not change:
            return

        # make undo/redoable

        Mgr.do("update_history_time")
        obj_data = {}
        event_data = {"objects": obj_data}

        if unlinked:
            event_descr = f'Unlink "{obj.name}"'
        elif ungrouped:
            event_descr = f'Ungroup "{obj.name}"'

        data = obj.get_data_to_store("prop_change", "link")
        data.update(obj.get_data_to_store("prop_change", "transform"))
        obj_data[obj.id] = data

        if Mgr.do("prune_empty_groups", groups, obj_data):
            event_data["object_ids"] = set(Mgr.get("object_ids"))

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __unlink_objects(self, picked_objs=None):

        if GD["active_obj_level"] != "top":
            return

        groups = set()
        affect_group_members = GD["group_options"]["member_linking"]["allowed"]
        ungrouped_members = []
        unlinked_children = []
        objs = picked_objs if picked_objs else Mgr.get("selection_top")

        for obj in objs:

            group = obj.group

            if group:

                groups.add(group)

                if affect_group_members and obj.set_group(None):
                    ungrouped_members.append(obj)

            elif obj.set_parent(None):

                unlinked_children.append(obj)

        changed_objs = ungrouped_members + unlinked_children

        if not changed_objs:
            return

        # make undo/redoable

        Mgr.do("update_history_time")
        obj_data = {}
        event_data = {"objects": obj_data}

        if len(unlinked_children) == 1:

            event_descr = f'Unlink "{unlinked_children[0].name}"'

        elif unlinked_children:

            event_descr = 'Unlink objects:\n'

            for obj in unlinked_children:
                event_descr += f'\n    "{obj.name}"'

        if ungrouped_members:

            if unlinked_children:
                event_descr += '\n\n'
            else:
                event_descr = ''

            if len(ungrouped_members) == 1:

                event_descr += f'Ungroup "{ungrouped_members[0].name}"'

            else:

                event_descr += 'Ungroup objects:\n'

                for obj in ungrouped_members:
                    event_descr += f'\n    "{obj.name}"'

        for obj in changed_objs:
            data = obj.get_data_to_store("prop_change", "link")
            data.update(obj.get_data_to_store("prop_change", "transform"))
            obj_data[obj.id] = data

        if Mgr.do("prune_empty_groups", groups, obj_data):
            event_data["object_ids"] = set(Mgr.get("object_ids"))

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __update_pivot_viz(self):

        target_type = GD["transform_target_type"]
        Mgr.do("show_pivot_gizmos", target_type in ("geom", "pivot"))

    def __update_xform_target_type(self, objs, reset=False):

        new_target_type = "all" if reset else GD["transform_target_type"]
        old_target_type = GD["transform_target_type"] if reset else "all"

        if new_target_type == old_target_type:
            return

        obj_root = Mgr.get("object_root")

        if new_target_type == "pivot":

            for obj in objs:

                obj.origin.wrt_reparent_to(obj_root)

                for child in obj.children:
                    child.pivot.wrt_reparent_to(obj_root)

                if obj.type == "group":
                    for member in obj.get_members():
                        member.pivot.wrt_reparent_to(obj_root)

        elif new_target_type == "no_children":

            for obj in objs:

                for child in obj.children:
                    child.pivot.wrt_reparent_to(obj_root)

                if obj.group in objs:
                    obj.pivot.wrt_reparent_to(obj_root)

        elif old_target_type == "pivot":

            for obj in objs:

                pivot = obj.pivot
                obj.origin.wrt_reparent_to(pivot)

                for child in obj.children:
                    child.pivot.wrt_reparent_to(pivot)

                if obj.type == "group":
                    for member in obj.get_members():
                        member.pivot.wrt_reparent_to(pivot)

        elif old_target_type == "no_children":

            for obj in objs:

                if obj.group in objs:
                    obj.pivot.wrt_reparent_to(obj.parent_pivot)

                pivot = obj.pivot

                for child in obj.children:
                    child.pivot.wrt_reparent_to(pivot)

    def __reset_geoms(self):

        sel = Mgr.get("selection_top")

        if not sel:
            return

        for obj in sel:

            obj.origin.clear_transform(obj.pivot)
            obj.update_group_bbox()

            if obj.type == "group":
                Mgr.do("update_group_bboxes", [obj.id])

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}
        Mgr.do("update_history_time")
        obj_count = len(sel)

        if obj_count > 1:

            event_descr = f"Reset {obj_count} objects' geometry:\n"

            for obj in sel:
                event_descr += f'\n    "{obj.name}"'

        else:

            event_descr = f'Reset "{sel[0].name}" geometry'

        for obj in sel:
            data = obj.get_data_to_store("prop_change", "origin_transform")
            obj_data[obj.id] = data

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __reset_pivots(self):

        sel = Mgr.get("selection_top")

        if not sel:
            return

        members = []

        for obj in sel:

            obj_root = Mgr.get("object_root")

            for child in obj.children:
                child.pivot.wrt_reparent_to(obj_root)

            if obj.type == "group":

                m = obj.get_members()
                members.extend(m)

                for member in m:
                    member.pivot.wrt_reparent_to(obj_root)

            pivot = obj.pivot
            origin = obj.origin
            pivot.clear_transform(origin)
            origin.clear_transform(pivot)

            for child in obj.children:
                child.pivot.wrt_reparent_to(pivot)

            if obj.type == "group":
                for member in m:
                    member.pivot.wrt_reparent_to(pivot)

        cs_type = GD["coord_sys_type"]
        cs_obj = Mgr.get("coord_sys_obj")
        tc_type = GD["transf_center_type"]
        tc_obj = Mgr.get("transf_center_obj")

        if cs_obj in sel:
            Mgr.do("notify_coord_sys_transformed")
            Mgr.do("update_coord_sys")

        if GD["active_obj_level"] == "top":

            if tc_type == "cs_origin":
                if cs_type == "object" and cs_obj in sel:
                    Mgr.get("transf_gizmo").pos = cs_obj.pivot.get_pos()
            elif tc_type == "object" and tc_obj in sel:
                Mgr.get("transf_gizmo").pos = tc_obj.pivot.get_pos()

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")
        self.__update_obj_link_viz([obj.id for obj in sel], True)

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}
        Mgr.do("update_history_time")
        obj_count = len(sel)

        if obj_count > 1:

            event_descr = f"Reset {obj_count} objects' pivots:\n"

            for obj in sel:
                event_descr += f'\n    "{obj.name}"'

        else:

            event_descr = f'Reset "{sel[0].name}" pivot'

        objs = set(sel)
        objs.update(members)

        for obj in sel:
            objs.update(obj.children)

        for obj in objs:
            data = obj.get_data_to_store("prop_change", "transform")
            obj_data[obj.id] = data

        for obj in sel:
            data = obj_data[obj.id]
            data.update(obj.get_data_to_store("prop_change", "origin_transform"))

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(HierarchyManager)
