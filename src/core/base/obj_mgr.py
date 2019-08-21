from .base import *
from .mgr import CoreManager as Mgr


class GeneralObjectManager:

    def __init__(self):

        self._obj_root = GD.world.attach_new_node("object_root")
        self._obj_types = {"top": [], "sub": []}
        self._obj_id = None

        self._showing_object_name = False
        self._checking_object_name = False
        self._clock = ClockObject()
        self._mouse_prev = Point2()

        self._obj_lvl_before_hist_change = "top"
        self._sel_before_hist_change = set()

        self._registry_backups_created = False

        GD.set_default("active_obj_level", "top")
        GD.set_default("temp_toplevel", False)
        GD.set_default("render_mode", "shaded")
        GD.set_default("next_obj_color", None)
        GD.set_default("obj_names", [], lambda l: l[:])

        Mgr.expose("object_root", lambda: self._obj_root)
        Mgr.expose("object_type_data", lambda: self._obj_types)
        Mgr.expose("object", self.__get_object)
        Mgr.expose("objects", lambda level="top": sum([Mgr.get(f"{obj_type}_objs")
                                                       for obj_type in self._obj_types[level]], []))
        Mgr.expose("object_ids", lambda level="top": sum([Mgr.get(f"{obj_type}_obj_ids")
                                                          for obj_type in self._obj_types[level]], []))
        Mgr.expose("object_types", lambda level="all": self._obj_types["top"] + self._obj_types["sub"]
                   if level == "all" else self._obj_types[level])
        Mgr.expose("next_obj_name", self.__get_next_object_name)
        Mgr.accept("reset_registries", self.__reset_registries)
        Mgr.accept("create_registry_backups", self.__create_registry_backups)
        Mgr.add_app_updater("custom_obj_name", self.__set_custom_object_name)
        Mgr.add_app_updater("selected_obj_name", self.__set_object_name)
        Mgr.add_app_updater("selected_obj_color", self.__set_object_color)
        Mgr.add_app_updater("selected_obj_prop", self.__set_object_property)
        Mgr.add_app_updater("obj_tags", self.__update_object_tags)
        Mgr.add_app_updater("render_mode", self.__update_render_mode)
        Mgr.add_app_updater("two_sided", self.__toggle_two_sided)
        Mgr.add_app_updater("active_obj_level", self.__update_object_level)
        Mgr.add_app_updater("history_change", self.__start_selection_check)
        Mgr.add_app_updater("transform_target_type", self.__update_xform_values)
        Mgr.add_notification_handler("long_process_cancelled", "obj_mgr",
                                     self.__restore_registry_backups)

        def enable_obj_name_checking():

            Mgr.remove_task("check_object_name")
            Mgr.add_task(self.__check_object_name, "check_object_name", sort=3)

        def disable_obj_name_checking():

            Mgr.remove_task("check_object_name")
            Mgr.update_remotely("object_name_tag", False)

        Mgr.accept("enable_object_name_checking", enable_obj_name_checking)
        Mgr.accept("disable_object_name_checking", disable_obj_name_checking)

        def set_obj_id(obj_id):

            self._obj_id = obj_id

        Mgr.accept("set_object_id", set_obj_id)

    def setup(self):

        self._obj_root.set_light(Mgr.get("default_light"))

        Mgr.add_task(self.__check_object_name, "check_object_name", sort=3)

        return True

    def __get_object(self, obj_id=None, pixel_color=None, obj_type=None, obj_lvl=None):

        if obj_id:

            if obj_type:

                return Mgr.get(obj_type, obj_id)

            for obj_type in self._obj_types[obj_lvl if obj_lvl else "top"]:

                obj = Mgr.get(obj_type, obj_id)

                if obj:
                    return obj

        elif pixel_color:

            r, g, b, pickable_type_id = [int(round(c * 255.)) for c in pixel_color]
            color_id = r << 16 | g << 8 | b

            pickable_type = PickableTypes.get(pickable_type_id)

            if not pickable_type:
                return None

            if pickable_type in ("transf_gizmo", ):
                return None

            obj = Mgr.get(pickable_type, color_id)

            if obj_lvl and obj_lvl != "top":
                return obj

            return obj.get_toplevel_object(get_group=True) if obj else None

    def __show_object_name(self, selection):

        pixel_color = Mgr.get("pixel_under_mouse")
        obj = self.__get_object(pixel_color=pixel_color)

        if not obj:
            return

        name = obj.name
        group = obj.group

        if group:
            name = f'{group.name} [{name}]'

        self._showing_object_name = True
        is_selected = obj in selection
        Mgr.update_remotely("object_name_tag", self._showing_object_name, name, is_selected)

        if is_selected and len(selection) > 1 and GD["active_transform_type"]:
            Mgr.update_remotely("transform_values", obj.transform_values)

        if is_selected:

            state_id = Mgr.get_state_id()
            cs_type = GD["coord_sys_type"]
            tc_type = GD["transf_center_type"]

            if state_id == "selection_mode":

                if cs_type == "local":
                    Mgr.update_locally("coord_sys", cs_type, obj)

                if tc_type == "pivot":
                    Mgr.update_locally("transf_center", tc_type, obj)

    def __check_object_name(self, task):

        if Mgr.get_state_id() == "suppressed":
            return task.cont

        if not GD.mouse_watcher.has_mouse():
            return task.cont

        mouse_pos = GD.mouse_watcher.get_mouse()

        selection = Mgr.get("selection_top")

        if mouse_pos == self._mouse_prev:

            if not self._checking_object_name:
                self._checking_object_name = True
                self._clock.reset()
            elif not self._showing_object_name and self._clock.real_time >= .5:
                self.__show_object_name(selection)
                self._clock.reset()

        else:

            self._mouse_prev = Point2(mouse_pos)
            self._checking_object_name = False

            if self._showing_object_name:

                self._showing_object_name = False
                Mgr.update_remotely("object_name_tag", self._showing_object_name)

                if len(selection) > 1 and GD["active_transform_type"]:
                    Mgr.update_remotely("transform_values")

        return task.cont

    def __set_custom_object_name(self, obj_type, custom_name):

        Mgr.do(f"set_custom_{obj_type}_name", custom_name)
        Mgr.update_remotely("next_obj_name", self.__get_next_object_name(obj_type))

    @staticmethod
    def __get_next_object_name(obj_type):

        custom_name = Mgr.get(f"custom_{obj_type}_name")
        namelist = GD["obj_names"]
        search_pattern = fr"^{obj_type}\s*(\d+)$"
        naming_pattern = obj_type + " {:04d}"

        return get_unique_name(custom_name, namelist, search_pattern, naming_pattern)

    @staticmethod
    def __set_object_name(name):

        selection = Mgr.get("selection_top")

        if not selection:
            return

        namelist = [obj.name for obj in Mgr.get("objects") if obj not in selection]
        old_names = [obj.name for obj in selection]
        new_names = []
        objs_by_name = {k: v for k, v in zip(old_names, selection)}
        objs_to_rename = [obj for obj in selection]
        sel_count = len(selection)

        for i in range(sel_count):

            new_name = get_unique_name(name, namelist)
            namelist.append(new_name)

            if new_name in old_names:
                objs_to_rename.remove(objs_by_name[new_name])
                old_names.remove(new_name)
            else:
                new_names.append(new_name)

        if objs_to_rename:

            obj_data = {}

            for obj, new_name in zip(objs_to_rename, new_names):
                obj.name = new_name
                obj_data[obj.id] = {"name": {"main": new_name}}

            if len(new_names) == 1:
                event_descr = f'Rename "{old_names[0]}"\nto "{new_names[0]}"'
            else:
                event_descr = 'Rename objects:\n'
                event_descr += ";\n".join([f'\n    "{old}"\n    to "{new}"'
                                           for old, new in zip(old_names, new_names)])

            event_data = {"objects": obj_data}
            Mgr.do("add_history", event_descr, event_data)

        names = {obj.id: obj.name for obj in selection}
        Mgr.update_remotely("selected_obj_names", names)

    def __set_object_color(self, color_values):

        objects = [obj for obj in Mgr.get("selection_top") if obj.has_color()]

        if not objects:
            return

        r, g, b = color_values
        color = VBase4(r, g, b, 1.)

        changed_objs = [obj for obj in objects if obj.set_color(color, update_app=False)]

        if not changed_objs:
            return

        obj_data = {obj.id: {"color": {"main": color}} for obj in changed_objs}

        if len(changed_objs) == 1:

            name = changed_objs[0].name
            event_descr = f'Change color of "{name}"\nto R:{r :.3f} | G:{g :.3f} | B:{b :.3f}'

        else:

            event_descr = 'Change color of objects:\n'

            for obj in changed_objs:
                event_descr += f'\n    "{obj.name}"'

            event_descr += f'\n\nto R:{r :.3f} | G:{g :.3f} | B:{b :.3f}'

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data)

        Mgr.update_remotely("selected_obj_color", color_values)
        GD["sel_color_count"] = 1
        Mgr.update_app("sel_color_count")

    def __update_object_tags(self, tags=None):

        obj = self.__get_object(self._obj_id)

        if tags is None:
            Mgr.update_remotely("obj_tags", obj.tags)
        else:
            obj.tags = tags
            Mgr.do("update_history_time")
            obj_data = {self._obj_id: obj.get_data_to_store("prop_change", "tags")}
            event_descr = f'Change tags of "{obj.name}"'
            event_data = {"objects": obj_data}
            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __update_xform_values(self):

        selection = Mgr.get("selection_top")

        if GD["active_obj_level"] == "top" and len(selection) == 1:
            Mgr.update_remotely("transform_values", selection[0].transform_values)

    def __add_to_history(self, changed_objs, prop_id, value):

        Mgr.do("update_history_time")

        obj_data = {}

        for obj in changed_objs:
            obj_data[obj.id] = obj.get_data_to_store("prop_change", prop_id)

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'Change {prop_id} of "{obj.name}"\nto {value}'
        else:
            event_descr = f'Change {prop_id} of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])
            event_descr += f'\n\nto {value}'

        event_data = {"objects": obj_data}

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __set_object_property(self, prop_id, value):
        """ Set the *type-specific* property given by prop_id to the given value """

        selection = Mgr.get("selection_top")

        if not selection:
            return

        changed_objs = [obj for obj in selection if obj.set_property(prop_id, value)]

        if not changed_objs:
            return

        get_task = lambda objs: lambda: self.__add_to_history(objs, prop_id, value)
        task = get_task(changed_objs)
        PendingTasks.add(task, "add_history", "object", 100)

    def __update_render_mode(self, new_mode):

        old_mode = GD["render_mode"]
        GD["render_mode"] = new_mode

        for model in Mgr.get("model_objs"):
            model.update_render_mode()

        Mgr.notify("render_mode_changed", old_mode, new_mode)

    def __toggle_two_sided(self):

        two_sided = not GD["two_sided"]
        GD["two_sided"] = two_sided

        for model in Mgr.get("model_objs"):
            model.set_two_sided(two_sided)

        Mgr.update_remotely("two_sided")

    def __update_object_level(self):

        obj_lvl = GD["active_obj_level"]
        obj_root = Mgr.get("object_root")
        picking_mask = Mgr.get("picking_mask")

        models = set(obj for obj in Mgr.get("selection_top") if obj.type == "model"
                     and obj.geom_type == "editable_geom")

        for model_id in self._sel_before_hist_change:

            model = Mgr.get("model", model_id)

            if model and model.geom_type == "editable_geom":
                models.add(model)

        if obj_lvl == "top":

            obj_root.show(picking_mask)

            for model in models:
                model.geom_obj.show_top_level()

        else:

            obj_root.hide(picking_mask)

            for model in models:
                model.geom_obj.show_subobj_level(obj_lvl)

        Mgr.update_remotely("selection_set", "replace", obj_lvl)

    def __check_selection(self):

        obj_lvl = self._obj_lvl_before_hist_change

        if obj_lvl == "top":
            return

        sel_after_hist_change = set(obj.id for obj in Mgr.get("selection_top"))
        set_sublvl = False

        if sel_after_hist_change == self._sel_before_hist_change:

            set_sublvl = True

            for model_id in sel_after_hist_change:

                model = Mgr.get("model", model_id)

                if model.geom_type != "editable_geom":
                    set_sublvl = False
                    break

        if set_sublvl:
            GD["active_obj_level"] = obj_lvl
            Mgr.update_locally("active_obj_level", restore=True)

        GD["temp_toplevel"] = False
        Mgr.update_remotely("active_obj_level")

        self._obj_lvl_before_hist_change = "top"
        self._sel_before_hist_change = set()

    def __start_selection_check(self):

        # This is called before undo/redo, to determine whether or not to stay at
        # the current subobject level, depending on the change in toplevel object
        # selection.

        obj_lvl = GD["active_obj_level"]

        if obj_lvl == "top":
            return

        self._obj_lvl_before_hist_change = obj_lvl
        self._sel_before_hist_change = set(obj.id for obj in Mgr.get("selection_top"))
        task = self.__check_selection
        task_id = "set_obj_level"
        PendingTasks.add(task, task_id, "object")
        GD["active_obj_level"] = "top"
        GD["temp_toplevel"] = True
        Mgr.update_locally("active_obj_level", restore=True)
        Mgr.exit_states(min_persistence=-99)

    def __reset_registries(self):

        for obj_type in self._obj_types["top"] + self._obj_types["sub"]:
            Mgr.do(f"reset_{obj_type}_registry")

        Notifiers.reg.info('Registries reset.')

    def __create_registry_backups(self):

        if self._registry_backups_created:
            return

        for obj_type in self._obj_types["top"] + self._obj_types["sub"]:
            Mgr.do(f"create_{obj_type}_registry_backup")

        task = self.__remove_registry_backups
        task_id = "remove_registry_backups"
        PendingTasks.add(task, task_id, "object", sort=100)
        self._registry_backups_created = True
        Notifiers.reg.info('Registry backups created.')

    def __restore_registry_backups(self, info=""):

        if not self._registry_backups_created:
            return

        for obj_type in self._obj_types["top"] + self._obj_types["sub"]:
            Mgr.do(f"restore_{obj_type}_registry_backup")

        Notifiers.reg.info(f'Registry backups restored;\ninfo: {info}')
        self.__remove_registry_backups()

    def __remove_registry_backups(self):

        if not self._registry_backups_created:
            return

        for obj_type in self._obj_types["top"] + self._obj_types["sub"]:
            Mgr.do(f"remove_{obj_type}_registry_backup")

        self._registry_backups_created = False
        Notifiers.reg.info('Registry backups removed.')


class ObjectManager:

    def __init__(self, obj_type, create_func, obj_level="top", pickable=False):

        self._obj_type = obj_type
        obj_types = Mgr.get("object_type_data")
        obj_types[obj_level].append(obj_type)
        self._pickable = pickable

        self._objects = {}
        self._object_id = 0
        self._objects_backup = None
        self._object_id_backup = None

        Mgr.accept(f"create_{obj_type}", create_func)
        Mgr.accept(f"register_{obj_type}", self.__register_object)
        Mgr.accept(f"unregister_{obj_type}", self.__unregister_object)
        Mgr.accept(f"register_{obj_type}_objs", self.__register_objects)
        Mgr.accept(f"unregister_{obj_type}_objs", self.__unregister_objects)
        Mgr.expose(obj_type, lambda obj_id: self._objects.get(obj_id))
        Mgr.expose(f"{obj_type}_objs", lambda: list(self._objects.values()))
        Mgr.expose(f"{obj_type}_obj_ids", lambda: list(self._objects.keys()))
        Mgr.expose(f"last_{obj_type}_obj_id", lambda: self._object_id)
        Mgr.accept(f"set_last_{obj_type}_obj_id", self.__set_last_id)
        Mgr.accept(f"reset_{obj_type}_registry", self.__reset_registry)
        Mgr.accept(f"create_{obj_type}_registry_backup", self.__create_registry_backup)
        Mgr.accept(f"restore_{obj_type}_registry_backup", self.__restore_registry_backup)
        Mgr.accept(f"remove_{obj_type}_registry_backup", self.__remove_registry_backup)

    def get_managed_object_type(self):

        return self._obj_type

    def get_next_id(self):

        self._object_id += 1

        return self._object_id

    def __set_last_id(self, obj_id):

        self._object_id = obj_id

    def __register_object(self, obj, restore=True):

        if self._pickable:
            key = obj.picking_color_id
        else:
            key = obj.id

        self._objects[key] = obj

        if self._pickable and restore:
            self.discard_picking_color_id(key)

    def __register_objects(self, objects, restore=True):

        if self._pickable:
            d = {obj.picking_color_id: obj for obj in objects}
        else:
            d = {obj.id: obj for obj in objects}

        self._objects.update(d)

        if self._pickable and restore:
            self.discard_picking_color_ids(d)

    def __unregister_object(self, obj):

        if self._pickable:
            key = obj.picking_color_id
        else:
            key = obj.id

        del self._objects[key]

        if self._pickable:
            self.recover_picking_color_id(key)

    def __unregister_objects(self, objects):

        if self._pickable:
            ids = [obj.picking_color_id for obj in objects]
        else:
            ids = [obj.id for obj in objects]

        for i in ids:
            del self._objects[i]

        if self._pickable:
            self.recover_picking_color_ids(ids)

    def __reset_registry(self):

        self._objects = {}
        self._object_id = 0
        self._objects_backup = None
        self._object_id_backup = None

    def __create_registry_backup(self):

        self._objects_backup = self._objects.copy()
        self._object_id_backup = self._object_id

    def __restore_registry_backup(self):

        self._objects = self._objects_backup
        self._object_id = self._object_id_backup

    def __remove_registry_backup(self):

        self._objects_backup = None
        self._object_id_backup = None


MainObjects.add_class(GeneralObjectManager)
