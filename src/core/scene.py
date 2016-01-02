from .base import *
from panda3d.egg import *


class SceneManager(BaseObject):

    def __init__(self):

        Mgr.set_global("unsaved_scene", False)

        self._handlers = {
            "reset": self.__reset,
            "load": self.__load,
            "save": self.__save,
            "export": self.__export,
            "import": self.__import,
        }
        Mgr.add_app_updater("scene", lambda handler_id, *args, **kwargs:
                            self._handlers[handler_id](*args, **kwargs))

    def __reset(self):
        # print "\n\n\n\n=============== Resetting scene
        # =================\n\n\n\n"

        Mgr.enter_state("selection_mode")

        for obj in Mgr.get("objects"):
            obj.destroy()

        Mgr.do("reset_history")
        PendingTasks.remove("update_selection", "ui")
        task = lambda: Mgr.get("selection", "top").update_ui(force=True)
        PendingTasks.add(task, "update_selection", "ui")
        PendingTasks.handle(["object", "ui"], True)

        if Mgr.get_global("active_obj_level") != "top":
            Mgr.set_global("active_obj_level", "top")
            Mgr.update_app("active_obj_level")

        if Mgr.get_global("render_mode") != "shaded":
            Mgr.set_global("render_mode", "shaded")
            Mgr.update_app("render_mode")

        Mgr.do("update_picking_col_id_ranges")
        Mgr.do("reset_cam_transform")
        Mgr.do("update_world_axes")
        Mgr.update_app("coord_sys", "world")
        Mgr.update_app("transf_center", "sel_center")
        Mgr.update_app("active_grid_plane", "XY")
        Mgr.update_app("active_transform_type", "")
        Mgr.update_app("status", "select", "")

        Mgr.reset_globals()

        for transf_type in ("translate", "rotate", "scale"):
            constraints = Mgr.get_global("axis_constraints_%s" % transf_type)
            Mgr.update_app("axis_constraints", transf_type, constraints)

        for obj_type in Mgr.get("object_types"):
            Mgr.do("set_last_%s_obj_id" % obj_type, 0)

    def __load(self, filename):

        self.__reset()
# print "\n\n\n\n=============== Loading scene =================\n\n\n\n"

        scene_file = Multifile()
        scene_file.open_read(Filename.from_os_specific(filename))
        scene_data_str = scene_file.read_subfile(
            scene_file.find_subfile("scene/data"))
        Mgr.do("load_history", scene_file)
        scene_file.close()
        scene_data = cPickle.loads(scene_data_str)

        for obj_type in Mgr.get("object_types"):
            data_id = "last_%s_obj_id" % obj_type
            Mgr.do("set_last_%s_obj_id" % obj_type, scene_data[data_id])

        for transf_type in ("translate", "rotate", "scale"):
            constraints = scene_data["axis_constraints"][transf_type]
            Mgr.set_global("axis_constraints_%s" % transf_type, constraints)
            Mgr.update_app("axis_constraints", transf_type, constraints)

        transf_type = scene_data["active_transform_type"]
        Mgr.set_global("active_transform_type", transf_type)
        Mgr.update_app("active_transform_type", transf_type)

        if transf_type:
            Mgr.update_app("status", "select", transf_type, "idle")
        else:
            Mgr.update_app("status", "select", "")

        for x in ("coord_sys", "transf_center"):
            x_type = scene_data[x]["type"]
            obj = Mgr.get("object", scene_data[x]["obj_id"])
            name = obj.get_name() if obj else None
            Mgr.update_locally(x, x_type, obj)
            Mgr.update_remotely(x, x_type, name)

        self.cam.set_y(scene_data["cam"])
        Mgr.get(("cam", "target")).set_mat(scene_data["cam_target"])
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_world_axes")
        active_grid_plane = scene_data["grid_plane"]
        Mgr.update_app("active_grid_plane", active_grid_plane)
        PendingTasks.handle(["object", "ui"], True)

    def __save(self, filename):

        scene_data = {}
        scene_data["cam"] = self.cam.get_y()
        scene_data["cam_target"] = Mgr.get(("cam", "target")).get_mat()
        scene_data["grid_plane"] = Mgr.get_global("active_grid_plane")

        for x in ("coord_sys", "transf_center"):
            scene_data[x] = {}
            scene_data[x]["type"] = Mgr.get_global("%s_type" % x)
            obj = Mgr.get("%s_obj" % x)
            scene_data[x]["obj_id"] = obj.get_id() if obj else None

        transf_type = Mgr.get_global("active_transform_type")
        scene_data["active_transform_type"] = transf_type
        scene_data["axis_constraints"] = {}

        for transf_type in ("translate", "rotate", "scale"):
            constraints = Mgr.get_global("axis_constraints_%s" % transf_type)
            scene_data["axis_constraints"][transf_type] = constraints

        for obj_type in Mgr.get("object_types"):
            data_id = "last_%s_obj_id" % obj_type
            scene_data[data_id] = Mgr.get(data_id)

        scene_file = Multifile()
        scene_file.open_write(Filename.from_os_specific(filename))
        scene_data_stream = StringStream(cPickle.dumps(scene_data, -1))
        scene_file.add_subfile("scene/data", scene_data_stream, 6)
        Mgr.do("save_history", scene_file)

        if scene_file.needs_repack():
            scene_file.repack()

        scene_file.flush()
        scene_file.close()

        Mgr.set_global("unsaved_scene", False)

    def __export(self, filename):

        root = NodePath("scene_root")
        tmp_node = NodePath("tmp_node")
        objs = [obj for obj in Mgr.get(
            "selection", "top") if obj.get_type() == "model"]

        for obj in objs:
            print "Exporting object:", obj.get_name()
            geom_data_obj = obj.get_geom_object().get_geom_data_object()
            origin = obj.get_origin()
            geom_top = geom_data_obj._geoms["top"]["shaded"].copy_to(tmp_node)
            geom_top.set_state(origin.get_state())
            geom_top.set_transform(origin.get_transform())
            geom_top.wrt_reparent_to(root)

            # TODO: retrieve texture filenames and make them relative
# texture.set_filename(rgb_fname.get_basename())
# texture.set_fullpath(rgb_fname.get_basename())

        root.write_bam_file(Filename.from_os_specific(filename))

    def __import(self, filename):
        pass


MainObjects.add_class(SceneManager)
