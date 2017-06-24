from .base import *


class SceneManager(BaseObject):

    def __init__(self):

        GlobalData.set_default("unsaved_scene", False)
        GlobalData.set_default("loading_scene", False)

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
        obj_lvl = GlobalData["active_obj_level"]

        if obj_lvl != "top":
            GlobalData["active_obj_level"] = "top"
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
            selection.update_obj_props(force=True)

        PendingTasks.add(task, "update_selection", "ui")
        PendingTasks.handle(["object", "ui"], True)

        if GlobalData["object_links_shown"]:
            GlobalData["object_links_shown"] = False
            Mgr.update_app("object_link_viz")

        if GlobalData["transform_target_type"] != "all":
            GlobalData["transform_target_type"] = "all"
            Mgr.update_app("transform_target_type")

        Mgr.do("clear_user_views")
        Mgr.update_remotely("material_library", "clear")
        Mgr.update_locally("material_library", "clear")
        Mgr.update_app("view", "reset_all")
        Mgr.update_app("coord_sys", "world")
        Mgr.update_app("transf_center", "adaptive")
        Mgr.update_app("active_transform_type", "")
        Mgr.update_app("status", "select", "")

        GlobalData.reset()
        Mgr.update_remotely("two_sided")
        Mgr.update_app("group_options")
        Mgr.update_app("subobj_edit_options")

        for transf_type, axes in GlobalData["axis_constraints"].iteritems():
            Mgr.update_app("axis_constraints", transf_type, axes)

        for obj_type in Mgr.get("object_types"):
            Mgr.do("set_last_%s_obj_id" % obj_type, 0)

        Mgr.update_remotely("scene_label", "New")

    def __load(self, filename):

        self.__reset()

        handler = lambda info: self.__reset()
        Mgr.add_notification_handler("long_process_cancelled", "scene_mgr", handler, once=True)
        task = lambda: Mgr.remove_notification_handler("long_process_cancelled", "scene_mgr")
        task_id = "remove_notification_handler"
        PendingTasks.add(task, task_id, "object", id_prefix="scene_mgr", sort=100)

        def finish():

            GlobalData["loading_scene"] = False

        task_id = "finish_loading_scene"
        PendingTasks.add(finish, task_id, "ui", sort=100)

        GlobalData["loading_scene"] = True
        Mgr.show_screenshot()
        scene_file = Multifile()
        scene_file.open_read(Filename.from_os_specific(filename))
        scene_data_str = scene_file.read_subfile(scene_file.find_subfile("scene/data"))
        scene_data = cPickle.loads(scene_data_str)
        Mgr.do("set_material_library", scene_data["material_library"])
        Mgr.do("load_history", scene_file)
        scene_file.close()

        for obj_type in Mgr.get("object_types"):
            data_id = "last_%s_obj_id" % obj_type
            Mgr.do("set_last_%s_obj_id" % obj_type, scene_data[data_id])

        GlobalData["axis_constraints"] = constraints = scene_data["axis_constraints"]

        for transf_type, axes in constraints.iteritems():
            Mgr.update_app("axis_constraints", transf_type, axes)

        GlobalData["rel_transform_values"] = scene_data["rel_transform_values"]
        transf_type = scene_data["active_transform_type"]
        GlobalData["active_transform_type"] = transf_type
        Mgr.update_app("active_transform_type", transf_type)

        if transf_type:
            Mgr.update_app("status", "select", transf_type, "idle")
        else:
            Mgr.update_app("status", "select", "")

        def task():

            for x in ("coord_sys", "transf_center"):
                x_type = scene_data[x]["type"]
                obj = Mgr.get("object", scene_data[x]["obj_id"])
                name = obj.get_name(as_object=True) if obj else None
                Mgr.update_locally(x, x_type, obj)
                Mgr.update_remotely(x, x_type, name)

            Mgr.do("set_view_data", scene_data["view_data"])

        task_id = "scene_task"
        PendingTasks.add(task, task_id, "ui", sort=100)

        PendingTasks.handle(["object", "ui"], True)
        GlobalData["open_file"] = filename

    def __save(self, filename, set_saved_state=True):

        scene_data = {}
        scene_data["material_library"] = Mgr.get("material_library")
        scene_data["view_data"] = Mgr.get("view_data")

        for x in ("coord_sys", "transf_center"):
            scene_data[x] = {}
            scene_data[x]["type"] = GlobalData["%s_type" % x]
            obj = Mgr.get("%s_obj" % x)
            scene_data[x]["obj_id"] = obj.get_id() if obj else None

        scene_data["active_transform_type"] = GlobalData["active_transform_type"]
        scene_data["rel_transform_values"] = GlobalData["rel_transform_values"]
        scene_data["axis_constraints"] = GlobalData["axis_constraints"]

        for obj_type in Mgr.get("object_types"):
            data_id = "last_%s_obj_id" % obj_type
            scene_data[data_id] = Mgr.get(data_id)

        scene_file = Multifile()
        scene_file.open_write(Filename.from_os_specific(filename))
        scene_data_stream = StringStream(cPickle.dumps(scene_data, -1))
        scene_file.add_subfile("scene/data", scene_data_stream, 9)
        Mgr.do("save_history", scene_file, set_saved_state)

        if scene_file.needs_repack():
            scene_file.repack()

        scene_file.flush()
        scene_file.close()

        if set_saved_state:
            GlobalData["unsaved_scene"] = False
            GlobalData["open_file"] = filename

    def __make_backup(self, index):

        open_file = GlobalData["open_file"]

        if open_file:
            root, ext = os.path.splitext(open_file)
        else:
            root = "autobackup"

        filename = root + ".bak%d" % index
        self.__save(filename, set_saved_state=False)


MainObjects.add_class(SceneManager)
