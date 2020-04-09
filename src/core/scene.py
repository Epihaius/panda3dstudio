from .base import *


FILE_VERSION = "1.0.0"


class SceneManager:

    def __init__(self):

        GD.set_default("unsaved_scene", False)
        GD.set_default("loading_scene", False)

        self._handlers = {
            "reset": self.__reset,
            "load": self.__load,
            "save": self.__save
        }
        Mgr.add_app_updater("scene", lambda handler_id, *args, **kwargs:
                            self._handlers[handler_id](*args, **kwargs))
        Mgr.accept("make_backup", self.__make_backup)

    def __reset(self):

        Mgr.enter_state("selection_mode")
        obj_lvl = GD["active_obj_level"]

        if obj_lvl != "top":
            GD["active_obj_level"] = "top"
            Mgr.update_app("active_obj_level")

        for obj in Mgr.get("objects"):
            obj.destroy(unregister=False, add_to_hist=False)

        Mgr.do("reset_picking_col_id_ranges")
        Mgr.do("reset_registries")
        Mgr.do("reset_transf_to_restore")
        Mgr.do("reset_history")
        Mgr.get("selection_top").reset()
        PendingTasks.remove("update_selection", "ui")

        def task():

            selection = Mgr.get("selection_top")
            selection.update_ui()
            selection.update_center_pos()
            selection.update_obj_props(force=True)

        PendingTasks.add(task, "update_selection", "ui")
        PendingTasks.handle(["object", "ui"], True)

        if GD["object_links_shown"]:
            GD["object_links_shown"] = False
            Mgr.update_app("object_link_viz")

        if GD["transform_target_type"] != "all":
            GD["transform_target_type"] = "all"
            Mgr.update_app("transform_target_type")

        Mgr.update_remotely("material_library", "clear")
        Mgr.update_locally("material_library", "clear")
        Mgr.update_locally("object_selection", "reset_sets")

        for x in ("coord_sys", "transf_center"):
            Mgr.update_locally(f"custom_{x}_transform", "clear_stored")
            Mgr.do(f"set_custom_{x}_transform")

        Mgr.update_app("coord_sys", "world")
        Mgr.update_app("transf_center", "adaptive")
        Mgr.update_app("active_transform_type", "")
        Mgr.update_app("view", "clear")
        Mgr.update_app("view", "reset_all")
        Mgr.update_app("view", "reset_backgrounds")
        Mgr.update_app("status", ["select", ""])

        GD.reset()
        Mgr.update_remotely("two_sided")
        Mgr.update_remotely("object_snap", "reset")
        Mgr.update_remotely("auto_grid_align_reset")
        Mgr.update_app("group_options")
        Mgr.update_app("subobj_edit_options")

        for transf_type, axes in GD["axis_constraints"].items():
            Mgr.update_app("axis_constraints", transf_type, axes)

        for obj_type in Mgr.get("object_types"):
            Mgr.do(f"set_last_{obj_type}_obj_id", 0)

        Mgr.update_remotely("scene_label", "New")

    def __load_scene(self, scene_file):

        self.__reset()

        handler = lambda info: self.__reset()
        Mgr.add_notification_handler("long_process_cancelled", "scene_mgr", handler, once=True)
        task = lambda: Mgr.remove_notification_handler("long_process_cancelled", "scene_mgr")
        task_id = "remove_notification_handler"
        PendingTasks.add(task, task_id, "object", id_prefix="scene_mgr", sort=100)

        def finish():

            GD["loading_scene"] = False

        task_id = "finish_loading_scene"
        PendingTasks.add(finish, task_id, "ui", sort=100)

        GD["loading_scene"] = True
        Mgr.update_remotely("screenshot", "create")
        scene_data = pickle.loads(scene_file.read_subfile(scene_file.find_subfile("scene/data")))
        Mgr.do("set_material_library", scene_data["material_library"])
        Mgr.do("load_history", scene_file)
        scene_file.close()

        for obj_type in Mgr.get("object_types"):
            data_id = f"last_{obj_type}_obj_id"
            Mgr.do(f"set_last_{obj_type}_obj_id", scene_data[data_id])

        GD["axis_constraints"] = constraints = scene_data["axis_constraints"]

        for transf_type, axes in constraints.items():
            Mgr.update_app("axis_constraints", transf_type, axes)

        selection_sets = scene_data["selection_sets"]
        sets_loaded = selection_sets["sets"]
        names_loaded = selection_sets["names"]

        for obj_lvl in list(sets_loaded):

            lvl_sets_loaded = sets_loaded[obj_lvl]
            lvl_names_loaded = names_loaded[obj_lvl]
            sets_loaded[obj_lvl] = sets = {}
            names_loaded[obj_lvl] = names = {}

            for set_id_loaded, sel_set in lvl_sets_loaded.items():
                set_id = id(sel_set)
                sets[set_id] = sel_set
                names[set_id] = lvl_names_loaded[set_id_loaded]

        Mgr.do("set_selection_sets", selection_sets)

        if "snap_settings" in scene_data:
            GD["snap"] = scene_data["snap_settings"]

        if "transform_options" in scene_data:
            GD["transform_options"] = scene_data["transform_options"]

        GD["rel_transform_values"] = scene_data["rel_transform_values"]
        transf_type = scene_data["active_transform_type"]
        GD["active_transform_type"] = transf_type
        Mgr.update_app("active_transform_type", transf_type)

        if transf_type:
            if GD["snap"]["on"][transf_type]:
                Mgr.update_app("status", ["select", transf_type, "snap_idle"])
            else:
                Mgr.update_app("status", ["select", transf_type, "idle"])
        else:
            Mgr.update_app("status", ["select", ""])

        def task():

            for x in ("coord_sys", "transf_center"):
                x_type = scene_data[x]["type"]
                obj = Mgr.get("object", scene_data[x]["obj_id"])
                name_obj = obj.name_obj if obj else None
                transform = scene_data[x]["custom_transform"]
                Mgr.do(f"set_custom_{x}_transform", *transform)
                stored_transforms = scene_data[x]["stored_transforms"]
                Mgr.do(f"set_stored_{x}_transforms", stored_transforms)
                Mgr.update_locally(x, x_type, obj)
                Mgr.update_remotely(x, x_type, name_obj)

            Mgr.do("set_view_data", scene_data["view_data"])

        task_id = "scene_task"
        PendingTasks.add(task, task_id, "ui", sort=100)

        PendingTasks.handle(["object", "ui"], True)

    def __load(self, filename):

        path = Filename.from_os_specific(filename).get_fullpath()
        scene_file = Multifile()
        scene_file.open_read(Filename(path))

        def load():

            self.__load_scene(scene_file)
            GD["open_file"] = path
            Mgr.update_remotely("scene_label", filename)

        def cancel():

            scene_file.close()

        handlers = (load, cancel)
        valid_file = True
        prefixes = ("major", "minor", "patched")

        if not scene_file.is_read_valid():
            Mgr.update_remotely("scene_load_error", path, "read")
            valid_file = False
        elif scene_file.find_subfile("Panda3DStudio") == -1:
            Mgr.update_remotely("scene_load_error", path, "id")
            valid_file = False
        elif scene_file.find_subfile("version") == -1:
            Mgr.update_remotely("scene_load_error", path, "major_older_version")
            valid_file = False
        else:
            version = pickle.loads(scene_file.read_subfile(scene_file.find_subfile("version")))
            if version != FILE_VERSION:
                for i, (n1, n2) in enumerate(zip(version.split("."), FILE_VERSION.split("."))):
                    prefix = prefixes[i]
                    if int(n1) != int(n2):
                        valid_file = False
                    if int(n1) < int(n2):
                        Mgr.update_remotely("scene_load_error", path,
                            prefix + "_older_version", handlers)
                        break
                    elif int(n1) > int(n2):
                        Mgr.update_remotely("scene_load_error", path,
                            prefix + "_newer_version", handlers)
                        break

        if valid_file:
            load()

    def __save(self, filename, set_saved_state=True):

        scene_data = {}
        scene_data["material_library"] = Mgr.get("material_library")
        scene_data["selection_sets"] = Mgr.get("selection_sets")
        scene_data["view_data"] = Mgr.get("view_data")

        for x in ("coord_sys", "transf_center"):
            scene_data[x] = {}
            scene_data[x]["custom_transform"] = Mgr.get(f"custom_{x}_transform")
            scene_data[x]["stored_transforms"] = Mgr.get(f"stored_{x}_transforms")
            scene_data[x]["type"] = GD[f"{x}_type"]
            obj = Mgr.get(f"{x}_obj")
            scene_data[x]["obj_id"] = obj.id if obj else None

        scene_data["active_transform_type"] = GD["active_transform_type"]
        scene_data["rel_transform_values"] = GD["rel_transform_values"]
        scene_data["axis_constraints"] = GD["axis_constraints"]
        scene_data["transform_options"] = GD["transform_options"]
        scene_data["snap_settings"] = GD["snap"]

        for obj_type in Mgr.get("object_types"):
            data_id = f"last_{obj_type}_obj_id"
            scene_data[data_id] = Mgr.get(data_id)

        scene_file = Multifile()
        scene_file.open_write(Filename(filename))
        id_stream = StringStream()
        scene_file.add_subfile("Panda3DStudio", id_stream, 9)
        version_stream = StringStream(pickle.dumps(FILE_VERSION, -1))
        scene_file.add_subfile("version", version_stream, 9)
        scene_data_stream = StringStream(pickle.dumps(scene_data, -1))
        scene_file.add_subfile("scene/data", scene_data_stream, 9)
        Mgr.do("save_history", scene_file, set_saved_state)

        if scene_file.needs_repack():
            scene_file.repack()

        scene_file.flush()
        scene_file.close()

        if set_saved_state:
            GD["unsaved_scene"] = False
            GD["open_file"] = filename

    def __make_backup(self, index):

        open_file = GD["open_file"]
        filename = Filename(open_file if open_file else "autobackup")
        filename.set_extension(f"bak{index}")
        self.__save(filename.get_fullpath(), set_saved_state=False)


MainObjects.add_class(SceneManager)
