from .base import *
from direct.interval.IntervalGlobal import (LerpPosInterval, LerpQuatInterval,
    LerpScaleInterval, LerpQuatScaleInterval, Parallel)


class ViewManager:

    def __init__(self):

        GD.set_default("view", "persp")

        self._lerp_interval = None
        self._transition_done = True
        self._dest_view = ""
        self._pixel_under_mouse = None

        self._user_view_ids = []
        self._user_lens_types = {}
        self._user_view_index = 0
        self._is_front_custom = {}
        self._default_front_quats = {}
        self._default_home_default_transforms = {}
        self._default_home_custom_transforms = {}
        self._custom_home_default_transforms = {}
        self._custom_home_custom_transforms = {}

        self._view_names = {}
        self._grid_planes = {}
        self._grid_plane_defaults = {}
        self._render_modes = {}
        self._render_mode_defaults = {}

        self._backgrounds = backgrounds = {}
        root = GD.world.attach_new_node("view_background_root")
        root.set_transparency(TransparencyAttrib.M_alpha)
        root.set_depth_write(False)
        root.set_depth_test(False)
        root.hide(Mgr.get("picking_mask"))
        cm = CardMaker("view_background")
        cm.set_frame(0., 1., 0., 1.)
        cm.set_has_normals(False)
        data = {}
        view_ids = ("front", "back", "left", "right", "top", "bottom")
        hprs = ((0., 0., 0.), (180., 0., 0.), (-90., 0., 0.),
                (90., 0., 0.), (0., -90., 0.), (180., 90., 0.))

        for view_id, hpr in zip(view_ids, hprs):
            data[view_id] = {
                "filename": "",
                "show": True,
                "in_foreground": False,
                "alpha": 1.,
                "x": 0.,
                "y": 0.,
                "width": 1.,
                "height": 1.,
                "fixed_aspect_ratio": True,
                "bitmap_aspect_ratio": 1.,
                "flip_h": False,
                "flip_v": False
            }
            pivot = root.attach_new_node("view_background_pivot")
            pivot.set_hpr(hpr)
            card = pivot.attach_new_node(cm.generate())
            card.set_bin("background", -100)
            card.hide()
            backgrounds[view_id] = card

        copier = lambda data: {key: value.copy() for key, value in data.items()}
        GD.set_default("view_backgrounds", data, copier)

        Mgr.expose("is_front_view_custom", lambda view_id: self._is_front_custom[view_id])
        Mgr.expose("view_transition_done", lambda: self._transition_done)
        Mgr.expose("view_data", self.__get_view_data)
        Mgr.accept("set_view_data", self.__set_view_data)
        Mgr.accept("start_view_transition", self.__start_view_transition)
        Mgr.accept("center_view_on_objects", self.__center_view_on_objects)
        Mgr.add_app_updater("view", self.__update_view)
        Mgr.add_app_updater("active_grid_plane", self.__update_grid_plane)
        Mgr.add_app_updater("render_mode", self.__update_render_mode)

    def setup(self):

        view_ids = ("persp", "ortho", "front", "back", "left", "right", "top", "bottom")

        hprs = (VBase3(-45., -45., 0.), VBase3(-45., -45., 0.), VBase3(), VBase3(180., 0., 0.),
                VBase3(-90., 0., 0.), VBase3(90., 0., 0.), VBase3(0., -90., 0.), VBase3(180., 90., 0.))
        zooms = (-40.,) + (.1,) * 7

        def create_quat(hpr):

            quat = Quat()
            quat.set_hpr(hpr)

            return quat

        self._is_front_custom = {view_id: False for view_id in view_ids}
        self._default_front_quats = {view_id: Quat() for view_id in view_ids}
        self._default_home_default_transforms = default_default = {}
        self._default_home_custom_transforms = default_custom = {}
        self._custom_home_default_transforms = custom_default = {}
        self._custom_home_custom_transforms = custom_custom = {}
        initial_values = {"pos": None, "quat": None, "zoom": None}
        lens_types = ("persp",) + ("ortho",) * 7
        cam = GD.cam

        for view_id, hpr, zoom, lens_type in zip(view_ids, hprs, zooms, lens_types):
            default_default[view_id] = {"pos": Point3(), "quat": create_quat(hpr), "zoom": zoom}
            default_custom[view_id] = initial_values.copy()
            custom_default[view_id] = initial_values.copy()
            custom_custom[view_id] = initial_values.copy()
            cam.add_rig(view_id, VBase3(), Point3(), hpr, lens_type, zoom)

        names = ["Perspective", "Orthographic"] + [view_id.title() for view_id in view_ids[2:]]
        self._view_names = {view_id: name for view_id, name in zip(view_ids, names)}
        planes = ("xy", "xy", "xz", "xz", "yz", "yz", "xy", "xy")
        self._grid_planes = {view_id: plane for view_id, plane in zip(view_ids, planes)}
        self._grid_plane_defaults = self._grid_planes.copy()
        self._render_modes = {view_id: "shaded" for view_id in view_ids}
        self._render_mode_defaults = self._render_modes.copy()

        add_state = Mgr.add_state
        add_state("view_obj_picking_mode", -75, self.__enter_picking_mode,
                  self.__exit_picking_mode)

        def exit_view_obj_picking_mode():

            Mgr.exit_state("view_obj_picking_mode")

        bind = Mgr.bind_state
        bind("view_obj_picking_mode", "pick view obj -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("view_obj_picking_mode", "pick view obj", "mouse1", self.__pick)
        bind("view_obj_picking_mode", "exit view obj picking", "escape",
             exit_view_obj_picking_mode)
        bind("view_obj_picking_mode", "cancel view obj picking", "mouse3",
             exit_view_obj_picking_mode)
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("view_obj_picking_mode", "pick view obj ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))

        status_data = GD["status"]
        mode_text = "Pick object to align view to"
        info_text = "LMB to pick object; RMB to cancel"
        status_data["pick_view_obj"] = {"mode": mode_text, "info": info_text}

        return "views_ok"

    @property
    def is_front_custom(self):

        return self._is_front_custom[GD["view"]]

    @is_front_custom.setter
    def is_front_custom(self, is_front_custom):

        self._is_front_custom[GD["view"]] = is_front_custom

    @property
    def default_front_quat(self):

        return self._default_front_quats[GD["view"]]

    @default_front_quat.setter
    def default_front_quat(self, quat):

        self._default_front_quats[GD["view"]] = quat

    @property
    def default_home_default_pos(self):

        return self._default_home_default_transforms[GD["view"]]["pos"]

    @property
    def default_home_default_quat(self):

        return self._default_home_default_transforms[GD["view"]]["quat"]

    @property
    def default_home_default_zoom(self):

        return self._default_home_default_transforms[GD["view"]]["zoom"]

    @property
    def custom_home_default_pos(self):

        return self._custom_home_default_transforms[GD["view"]]["pos"]

    @custom_home_default_pos.setter
    def custom_home_default_pos(self, pos):

        self._custom_home_default_transforms[GD["view"]]["pos"] = pos

    @property
    def custom_home_default_quat(self):

        return self._custom_home_default_transforms[GD["view"]]["quat"]

    @custom_home_default_quat.setter
    def custom_home_default_quat(self, quat):

        self._custom_home_default_transforms[GD["view"]]["quat"] = quat

    @property
    def custom_home_default_zoom(self):

        return self._custom_home_default_transforms[GD["view"]]["zoom"]

    @custom_home_default_zoom.setter
    def custom_home_default_zoom(self, zoom):

        self._custom_home_default_transforms[GD["view"]]["zoom"] = zoom

    @property
    def custom_home_custom_pos(self):

        return self._custom_home_custom_transforms[GD["view"]]["pos"]

    @custom_home_custom_pos.setter
    def custom_home_custom_pos(self, pos):

        self._custom_home_custom_transforms[GD["view"]]["pos"] = pos

    @property
    def custom_home_custom_quat(self):

        return self._custom_home_custom_transforms[GD["view"]]["quat"]

    @custom_home_custom_quat.setter
    def custom_home_custom_quat(self, quat):

        self._custom_home_custom_transforms[GD["view"]]["quat"] = quat

    @property
    def custom_home_custom_zoom(self):

        return self._custom_home_custom_transforms[GD["view"]]["zoom"]

    @custom_home_custom_zoom.setter
    def custom_home_custom_zoom(self, zoom):

        self._custom_home_custom_transforms[GD["view"]]["zoom"] = zoom

    @property
    def default_home_custom_pos(self):

        pos = self._default_home_custom_transforms[GD["view"]]["pos"]

        return self.default_home_default_pos if pos is None else pos

    @default_home_custom_pos.setter
    def default_home_custom_pos(self, pos):

        self._default_home_custom_transforms[GD["view"]]["pos"] = pos

    @property
    def default_home_custom_quat(self):

        quat = self._default_home_custom_transforms[GD["view"]]["quat"]

        return self.default_home_default_quat if quat is None else quat

    @default_home_custom_quat.setter
    def default_home_custom_quat(self, quat):

        self._default_home_custom_transforms[GD["view"]]["quat"] = quat

    @property
    def default_home_custom_zoom(self):

        zoom = self._default_home_custom_transforms[GD["view"]]["zoom"]

        return self.default_home_default_zoom if zoom is None else zoom

    @default_home_custom_zoom.setter
    def default_home_custom_zoom(self, zoom):

        self._default_home_custom_transforms[GD["view"]]["zoom"] = zoom

    @property
    def home_default_pos(self):

        return self.custom_home_default_pos if self.is_front_custom else self.default_home_default_pos

    @property
    def home_default_quat(self):

        return self.custom_home_default_quat if self.is_front_custom else self.default_home_default_quat

    @property
    def home_default_zoom(self):

        return self.custom_home_default_zoom if self.is_front_custom else self.default_home_default_zoom

    @property
    def home_pos(self):

        return self.custom_home_custom_pos if self.is_front_custom else self.default_home_custom_pos

    @home_pos.setter
    def home_pos(self, pos):

        if self.is_front_custom:
            self.custom_home_custom_pos = pos
        else:
            self.default_home_custom_pos = pos

    @property
    def home_quat(self):

        return self.custom_home_custom_quat if self.is_front_custom else self.default_home_custom_quat

    @home_quat.setter
    def home_quat(self, quat):

        if self.is_front_custom:
            self.custom_home_custom_quat = quat
        else:
            self.default_home_custom_quat = quat

    @property
    def home_zoom(self):

        return self.custom_home_custom_zoom if self.is_front_custom else self.default_home_custom_zoom

    @home_zoom.setter
    def home_zoom(self, zoom):

        if self.is_front_custom:
            self.custom_home_custom_zoom = zoom
        else:
            self.default_home_custom_zoom = zoom

    @property
    def reset_interval(self):

        interval1 = LerpPosInterval(GD.cam.pivot, .5, self.home_pos,
                                    blendType="easeInOut")

        if GD.cam.lens_type == "persp":
            interval2 = LerpQuatInterval(GD.cam.target, .5, self.home_quat,
                                         blendType="easeInOut")
            interval3 = LerpPosInterval(GD.cam.origin, .5, Point3(0., self.home_zoom, 0.),
                                        blendType="easeInOut")
            lerp_interval = Parallel(interval1, interval2, interval3)
        else:
            interval2 = LerpQuatScaleInterval(GD.cam.target, .5, self.home_quat,
                                              self.home_zoom, blendType="easeInOut")
            lerp_interval = Parallel(interval1, interval2)

        return lerp_interval

    @property
    def default_grid_plane(self):

        return self._grid_plane_defaults[GD["view"]]

    @property
    def grid_plane(self):

        return self._grid_planes[GD["view"]]

    @grid_plane.setter
    def grid_plane(self, grid_plane):

        self._grid_planes[GD["view"]] = grid_plane

    @property
    def default_render_mode(self):

        return self._render_mode_defaults[GD["view"]]

    @property
    def render_mode(self):

        return self._render_modes[GD["view"]]

    @render_mode.setter
    def render_mode(self, render_mode):

        self._render_modes[GD["view"]] = render_mode

    def __enter_picking_mode(self, prev_state_id, active):

        Mgr.add_task(self.__update_cursor, "update_view_obj_picking_cursor")
        Mgr.update_app("status", ["pick_view_obj"])

        if not active:

            def handler(obj_ids):

                if obj_ids:
                    obj = Mgr.get("object", obj_ids[0])
                    self.__pick(picked_obj=obj)

            Mgr.update_remotely("selection_by_name", "", "Pick object to align view to",
                                None, False, "Pick", handler)
            Mgr.get("gizmo_picking_cam").node().active = False
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = False

    def __exit_picking_mode(self, next_state_id, active):

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self.__update_cursor()
                                        # is called
        Mgr.remove_task("update_view_obj_picking_cursor")
        Mgr.set_cursor("main")

        if not active:
            Mgr.get("gizmo_picking_cam").node().active = True
            Mgr.get("gizmo_picking_cam").node().get_display_region(0).active = True
            Mgr.update_remotely("selection_by_name", "default")

    def __pick(self, picked_obj=None):

        obj = picked_obj if picked_obj else Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if obj:
            self.__center_view_on_objects(obj_to_align_to=obj)
            Mgr.exit_state("view_obj_picking_mode")

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __get_view_data(self):

        cam = GD.cam
        data = {}
        data["custom"] = self._is_front_custom
        data["default_home_custom"] = self._default_home_custom_transforms
        data["custom_home_default"] = self._custom_home_default_transforms
        data["custom_home_custom"] = self._custom_home_custom_transforms
        data["user_ids"] = user_view_ids = self._user_view_ids
        data["user_lenses"] = self._user_lens_types
        data["user_index"] = self._user_view_index
        names = self._view_names
        data["user_names"] = {view_id: names[view_id] for view_id in user_view_ids}
        front_quats = self._default_front_quats
        data["user_front_quats"] = {view_id: front_quats[view_id] for view_id in user_view_ids}
        default_transforms = self._default_home_default_transforms
        data["user_defaults"] = {view_id: default_transforms[view_id] for view_id in user_view_ids}
        data["cam_pivot_pos"] = cam.pivot_positions
        data["cam_pivot_hpr"] = cam.pivot_hprs
        data["cam_target_hpr"] = cam.target_hprs
        data["cam_zoom"] = cam.zooms
        data["grid"] = self._grid_planes
        grid_defaults = self._grid_plane_defaults
        data["grid_user"] = {view_id: grid_defaults[view_id] for view_id in user_view_ids}
        data["render_mode"] = self._render_modes
        render_mode_defaults = self._render_mode_defaults
        data["render_mode_user"] = {view_id: render_mode_defaults[view_id] for view_id in user_view_ids}
        data["view"] = GD["view"]
        data["view_backgrounds"] = GD["view_backgrounds"]

        return data

    def __set_view_data(self, data):

        self._is_front_custom = data["custom"]
        self._default_home_custom_transforms = data["default_home_custom"]
        self._custom_home_default_transforms = data["custom_home_default"]
        self._custom_home_custom_transforms = data["custom_home_custom"]
        self._user_view_ids = user_view_ids = data["user_ids"]
        self._user_lens_types = lens_types = data["user_lenses"]
        self._user_view_index = data["user_index"]
        view_names = self._view_names
        user_names = data["user_names"]
        view_names.update(user_names)
        user_defaults = data["user_defaults"]
        self._default_home_default_transforms.update(user_defaults)
        front_quats = data["user_front_quats"]
        self._default_front_quats.update(front_quats)
        cam = GD.cam

        for view_id in user_view_ids:
            defaults = user_defaults[view_id]
            cam.add_rig(view_id, front_quats[view_id].get_hpr(), defaults["pos"],
                        defaults["quat"].get_hpr(), lens_types[view_id], defaults["zoom"])
            Mgr.update_remotely("view", "add", view_id, view_names[view_id])

        cam.pivot_positions = data["cam_pivot_pos"]
        cam.pivot_hprs = data["cam_pivot_hpr"]
        cam.target_hprs = data["cam_target_hpr"]
        cam.zooms = data["cam_zoom"]

        self._grid_planes = data["grid"]
        grid_defaults = self._grid_plane_defaults

        for view_id, plane in data["grid_user"].items():
            grid_defaults[view_id] = plane

        self._render_modes = data["render_mode"]
        render_mode_defaults = self._render_mode_defaults

        for view_id, render_mode in data["render_mode_user"].items():
            render_mode_defaults[view_id] = render_mode

        self.__set_view(data["view"], force=True)
        Mgr.update_remotely("view", "set", data["view"])

        if "view_backgrounds" in data:
            for view_id, bg_data in data["view_backgrounds"].items():
                bg_data["view"] = view_id
                self.__update_background(bg_data)

    def __clear_user_views(self):

        if GD["view"] in self._user_view_ids:
            self.__set_view("persp")

        cam = GD.cam
        view_names = self._view_names
        default_front = self._default_front_quats
        default_default = self._default_home_default_transforms
        default_custom = self._default_home_custom_transforms
        custom_default = self._custom_home_default_transforms
        custom_custom = self._custom_home_custom_transforms
        grid_plane_def =self._grid_plane_defaults
        grid_planes = self._grid_planes
        render_mode_def = self._render_mode_defaults
        render_modes = self._render_modes

        for view_id in reversed(self._user_view_ids):
            del view_names[view_id]
            del default_front[view_id]
            del default_default[view_id]
            del default_custom[view_id]
            del custom_default[view_id]
            del custom_custom[view_id]
            del grid_plane_def[view_id]
            del grid_planes[view_id]
            del render_mode_def[view_id]
            del render_modes[view_id]
            cam.remove_rig(view_id)

        self._user_view_ids = []
        self._user_lens_types = {}
        self._user_view_index = 0

    def __update_grid_plane(self, grid_plane):

        self.grid_plane = grid_plane

    def __update_render_mode(self, render_mode):

        self.render_mode = render_mode

    def __show_background(self, view_id):

        data = GD["view_backgrounds"][view_id]

        if data["filename"] and data["show"]:
            self._backgrounds[view_id].show()

    def __update_background(self, data):

        view_id = data["view"]

        if view_id == "all":
            for v_id in ("front", "back", "left", "right", "bottom", "top"):
                data["view"] = v_id
                self.__update_background(data)
            return

        background = self._backgrounds[view_id]
        background_data = GD["view_backgrounds"][view_id]

        filename = data["filename"]
        in_foreground = data["in_foreground"]
        alpha = data["alpha"]
        x = data["x"]
        y = data["y"]
        width = data["width"]
        height = data["height"]
        flip_h = data["flip_h"]
        flip_v = data["flip_v"]

        if filename != background_data["filename"]:

            if filename:

                path = Filename.from_os_specific(filename)

                if path.exists():
                    tex = Mgr.load_tex(path)
                    background.set_texture(tex)
                else:
                    data["filename"] = filename = ""

            if not filename:
                background.hide()
                background.clear_texture()

        if data["show"]:
            if filename and GD["view"] == view_id:
                background.show()
        else:
            background.hide()

        if in_foreground != background_data["in_foreground"]:
            bin_data = ("fixed", 100) if in_foreground else ("background", -100)
            background.set_bin(*bin_data)

        if alpha != background_data["alpha"]:
            background.set_alpha_scale(alpha)

        if x != background_data["x"]:
            background.set_x(x)

        if y != background_data["y"]:
            background.set_z(y)

        if width != background_data["width"]:
            background.set_sx(width)

        if height != background_data["height"]:
            background.set_sz(height)

        sx = -1. if background_data["flip_h"] else 1.
        sy = -1. if background_data["flip_v"] else 1.
        update_tex_scale = False

        if flip_h != background_data["flip_h"]:
            sx = -1. if flip_h else 1.
            update_tex_scale = True

        if flip_v != background_data["flip_v"]:
            sy = -1. if flip_v else 1.
            update_tex_scale = True

        if update_tex_scale:
            background.set_tex_scale(TextureStage.default, sx, sy)

        background_data.update(data)
        del background_data["view"]

    def __reset_backgrounds(self):

        for background in self._backgrounds.values():
            background.hide()
            background.set_bin("background", -100)
            background.set_pos(0., 0., 0.)
            background.set_scale(1.)
            background.clear_texture()
            background.clear_tex_transform()
            background.clear_color_scale()

    def __update_view(self, update_type, *args):

        view_id = GD["view"]

        if update_type == "set":
            self.__set_view(*args)
        elif update_type == "preview":
            self.__do_preview(*args)
        elif update_type == "center":
            self.__center_view_on_objects(*args)
        elif update_type == "reset":
            self.__reset_view(*args)
        elif update_type == "reset_all":
            self.__reset_all_views(*args)
        elif update_type == "set_as_home":
            self.__set_as_home_view()
        elif update_type == "reset_home":
            self.__reset_home_view()
        elif update_type == "set_as_front":
            self.__set_as_front_view()
        elif update_type == "reset_front":
            self.__reset_front_view()
        elif update_type == "init_copy":
            lens_type = args[0]
            Mgr.update_remotely("view", "request_copy_name", lens_type, self._view_names[view_id])
        elif update_type == "copy":
            self.__copy_view(*args)
        elif update_type == "take_snapshot":
            self.__take_snapshot(*args)
        elif update_type == "toggle_lens_type":
            self.__toggle_lens_type(*args)
        elif update_type == "init_remove":
            if view_id in self._user_view_ids:
                Mgr.update_remotely("view", "confirm_remove", view_id, self._view_names[view_id])
        elif update_type == "remove":
            self.__remove_user_view(*args)
        elif update_type == "init_clear":
            if self._user_view_ids:
                Mgr.update_remotely("view", "confirm_clear", len(self._user_view_ids))
        elif update_type == "clear":
            self.__clear_user_views()
        elif update_type == "init_rename":
            if view_id in self._user_view_ids:
                Mgr.update_remotely("view", "request_new_name", self._view_names[view_id])
        elif update_type == "rename":
            name = args[0]
            name = get_unique_name(name, iter(self._view_names.values()))
            self._view_names[view_id] = name
            lens_type = GD.cam.lens_type
            Mgr.update_remotely("view", "rename", lens_type, view_id, name)
        elif update_type == "obj_align":
            if GD["active_obj_level"] != "top":
                GD["active_obj_level"] = "top"
                Mgr.update_app("active_obj_level")
            Mgr.enter_state("view_obj_picking_mode")
        elif update_type == "background":
            self.__update_background(*args)
        elif update_type == "reset_backgrounds":
            self.__reset_backgrounds()

        if update_type in ("copy", "take_snapshot", "toggle_lens_type", "remove", "clear",
                           "rename", "background", "reset_backgrounds"):
            GD["unsaved_scene"] = True
            Mgr.update_app("unsaved_scene")
            Mgr.do("require_scene_save")

    def __toggle_lens_type(self):

        view_id = GD["view"]

        if view_id not in self._user_view_ids:
            return

        cam = GD.cam
        current_lens_type = cam.lens_type
        lens_type = "ortho" if current_lens_type == "persp" else "persp"

        self._user_lens_types[view_id] = lens_type
        default_default = self._default_home_default_transforms[view_id]
        default_default["zoom"] = cam.convert_zoom(lens_type, zoom=default_default["zoom"])
        default_custom = self._default_home_custom_transforms[view_id]
        custom_default = self._custom_home_default_transforms[view_id]
        custom_custom = self._custom_home_custom_transforms[view_id]

        for transforms in (default_custom, custom_default, custom_custom):

            zoom = transforms["zoom"]

            if zoom is not None:
                zoom = cam.convert_zoom(lens_type, zoom=zoom)
                transforms["zoom"] = zoom

        zoom = cam.convert_zoom(lens_type)
        cam.lens_type = lens_type
        cam.zoom = zoom
        cam.update()
        Mgr.get("grid").update(force=True)
        Mgr.get("picking_cam").adjust_to_lens()
        Mgr.get("transf_gizmo").adjust_to_lens(current_lens_type, lens_type)

    def __set_view(self, view_id, force=False):
        """ Switch to a different view """

        current_view_id = GD["view"]

        if not force and current_view_id == view_id:
            return

        cam = GD.cam
        current_lens_type = cam.lens_type
        GD["view"] = view_id
        cam.update()
        lens_type = cam.lens_type

        Mgr.update_app("active_grid_plane", self.grid_plane)
        Mgr.update_app("render_mode", self.render_mode)

        if current_lens_type != lens_type:
            Mgr.get("grid").update(force=True)
            Mgr.get("picking_cam").adjust_to_lens()
            Mgr.get("transf_gizmo").adjust_to_lens(current_lens_type, lens_type)

        Mgr.do("update_zoom_indicator")
        Mgr.do("update_view_gizmo", cube=False, hpr=True)
        Mgr.get("transf_gizmo").update()
        Mgr.do("update_coord_sys")

        if GD["coord_sys_type"] == "view":
            Mgr.get("selection").update_transform_values()

        backgrounds = self._backgrounds
        Mgr.update_remotely("view", "enable_obj_align", view_id not in backgrounds)

        if current_view_id in backgrounds:
            backgrounds[current_view_id].hide()

        if view_id in backgrounds:
            self.__show_background(view_id)

    def __copy_view(self, lens_type, name):
        """ Copy the current view using the given lens type and make it a user view """

        current_view_id = GD["view"]
        name = get_unique_name(name, iter(self._view_names.values()))
        view_id = str(self._user_view_index)
        self._view_names[view_id] = name

        cam = GD.cam

        pivot_pos = cam.pivot.get_pos()
        pivot_hpr = cam.pivot.get_hpr()
        target_hpr = cam.target.get_hpr()
        zoom = cam.convert_zoom(lens_type)

        self._is_front_custom[view_id] = self._is_front_custom[current_view_id]

        default_front = self._default_front_quats
        default_front[view_id] = default_front[current_view_id]
        default_default = self._default_home_default_transforms
        default_default[view_id] = default_default[current_view_id].copy()
        default_custom = self._default_home_custom_transforms
        default_custom[view_id] = default_custom[current_view_id].copy()
        custom_default = self._custom_home_default_transforms
        custom_default[view_id] = custom_default[current_view_id].copy()
        custom_custom = self._custom_home_custom_transforms
        custom_custom[view_id] = custom_custom[current_view_id].copy()

        self._grid_plane_defaults[view_id] = self._grid_plane_defaults[current_view_id]
        self._grid_planes[view_id] = self._grid_planes[current_view_id]
        self._render_mode_defaults[view_id] = self._render_mode_defaults[current_view_id]
        self._render_modes[view_id] = self._render_modes[current_view_id]

        self._user_view_ids.append(view_id)
        self._user_lens_types[view_id] = lens_type
        self._user_view_index += 1
        cam.add_rig(view_id, pivot_hpr, pivot_pos, target_hpr, lens_type, zoom)

        zoom = cam.convert_zoom(lens_type, zoom=default_default[current_view_id]["zoom"])
        default_default[view_id]["zoom"] = zoom

        for transforms in (default_custom, custom_default, custom_custom):

            zoom = transforms[current_view_id]["zoom"]

            if zoom is not None:
                zoom = cam.convert_zoom(lens_type, zoom=zoom)
                transforms[view_id]["zoom"] = zoom

        name = f"User {lens_type} - {name}"
        Mgr.update_remotely("view", "add", view_id, name)

        self.__set_view(view_id)

    def __take_snapshot(self, view_name):
        """ Take a snapshot of the current view and make it a user view """

        current_view_id = GD["view"]
        name = get_unique_name(view_name, iter(self._view_names.values()))
        view_id = str(self._user_view_index)
        self._view_names[view_id] = name

        self._is_front_custom[view_id] = False

        cam = GD.cam

        pivot = cam.pivot
        pivot_pos = pivot.get_pos()
        pivot_hpr = pivot.get_hpr()
        front_quat = pivot.get_quat()
        target = cam.target
        target_hpr = target.get_hpr()
        quat = target.get_quat()
        zoom = cam.zoom
        initial_values = {"pos": None, "quat": None, "zoom": None}
        default_front = self._default_front_quats
        default_front[view_id] = front_quat
        default_default = self._default_home_default_transforms
        default_default[view_id] = {"pos": pivot_pos, "quat": quat, "zoom": zoom}
        default_custom = self._default_home_custom_transforms
        default_custom[view_id] = initial_values.copy()
        custom_default = self._custom_home_default_transforms
        custom_default[view_id] = initial_values.copy()
        custom_custom = self._custom_home_custom_transforms
        custom_custom[view_id] = initial_values.copy()

        grid_plane = self._grid_planes[current_view_id]
        self._grid_plane_defaults[view_id] = grid_plane
        self._grid_planes[view_id] = grid_plane
        render_mode = self._render_modes[current_view_id]
        self._render_mode_defaults[view_id] = render_mode
        self._render_modes[view_id] = render_mode

        self._user_view_ids.append(view_id)
        lens_type = cam.lens_type
        self._user_lens_types[view_id] = lens_type
        self._user_view_index += 1
        cam.add_rig(view_id, pivot_hpr, pivot_pos, target_hpr, lens_type, zoom)

        name = f"User {lens_type} - {name}"
        Mgr.update_remotely("view", "add", view_id, name)

        self.__set_view(view_id)

    def __remove_user_view(self, view_id):

        if view_id not in self._user_view_ids:
            return

        if GD["view"] in self._user_view_ids:
            self.__set_view("persp")

        cam = GD.cam

        del self._view_names[view_id]
        del self._default_front_quats[view_id]
        del self._default_home_default_transforms[view_id]
        del self._default_home_custom_transforms[view_id]
        del self._custom_home_default_transforms[view_id]
        del self._custom_home_custom_transforms[view_id]
        del self._grid_plane_defaults[view_id]
        del self._grid_planes[view_id]
        del self._render_mode_defaults[view_id]
        del self._render_modes[view_id]
        cam.remove_rig(view_id)
        self._user_view_ids.remove(view_id)
        del self._user_lens_types[view_id]

    def __adjust_transition_hpr(self, task):

        cam_target = GD.cam.target
        quat = cam_target.get_quat()

        # prevent the bottom view from flipping 180 degrees when orbiting
        # the view later, due to a negative heading
        if self._dest_view == "-z":
            hpr = Vec3(180., 90., 0.)
        else:
            hpr = quat.get_hpr()

        cam_target.set_hpr(hpr)

        Mgr.get("transf_gizmo").update()
        Mgr.do("update_coord_sys")
        Mgr.do("update_zoom_indicator")

    def __transition_view(self, task):

        if self._lerp_interval.is_stopped():
            self._lerp_interval = None
            self._transition_done = True
            return

        Mgr.get("transf_gizmo").update()
        Mgr.do("update_coord_sys")
        Mgr.do("update_zoom_indicator")

        return task.cont

    def __start_view_transition(self, dest_view, quat):

        self._dest_view = dest_view
        lerp_interval = LerpQuatInterval(GD.cam.target, .5, quat,
                                         blendType="easeInOut")
        self._lerp_interval = lerp_interval
        lerp_interval.start()
        self._transition_done = False
        Mgr.add_task(self.__transition_view, "transition_view", sort=30,
                     uponDeath=self.__adjust_transition_hpr)
        Mgr.do("start_view_gizmo_transition")

    def __set_as_front_view(self, view_id=None):
        """ Set the given or current view as a custom Front view """

        if view_id:
            current_view_id = GD["view"]
            GD["view"] = view_id

        cam = GD.cam
        self.is_front_custom = True
        pos = cam.pivot.get_pos()
        quat = Quat()
        zoom = cam.zoom
        self.custom_home_default_pos = pos
        self.custom_home_default_quat = quat
        self.custom_home_default_zoom = zoom
        self.home_pos = pos
        self.home_quat = quat
        self.home_zoom = zoom
        hpr = cam.target.get_hpr(GD.world)
        cam.target.set_hpr(0., 0., 0.)
        cam.pivot.set_hpr(hpr)

        if not view_id or view_id == current_view_id:
            Mgr.do("update_view_gizmo", False, True)

        if view_id:
            GD["view"] = current_view_id

    def __reset_front_view(self, view_id=None, transition=True, reset_roll=True):
        """ Realigns the Front view to the world (or original user view space) """

        if view_id:
            current_view_id = GD["view"]
            GD["view"] = view_id

        if not self.is_front_custom:

            if view_id:
                GD["view"] = current_view_id

            return

        cam = GD.cam
        ref_node = NodePath("ref_node")
        def_front_quat = self.default_front_quat
        ref_node.set_quat(def_front_quat)
        hpr = cam.target.get_hpr(ref_node)
        quat = Quat()

        if reset_roll:
            forward_vec = ref_node.get_relative_vector(cam.target, Vec3.forward())
            look_at(quat, forward_vec, Vec3.up())
        else:
            quat.set_hpr(hpr)

        if transition and (not view_id or view_id == current_view_id):

            cam.target.set_hpr(hpr)
            cam.pivot.set_quat(def_front_quat)
            self._transition_done = False
            interval1 = LerpQuatInterval(cam.target, .5, quat, blendType="easeInOut")
            interval2 = LerpQuatInterval(Mgr.get("view_gizmo_root"), .5,
                                         def_front_quat, blendType="easeInOut")
            lerp_interval = Parallel(interval1, interval2)
            Mgr.do("start_view_gizmo_transition")
            self._lerp_interval = lerp_interval
            lerp_interval.start()
            Mgr.add_task(self.__transition_view, "transition_view", sort=30,
                         uponDeath=self.__adjust_transition_hpr)
            self._dest_view = ""

        else:

            cam.target.set_quat(quat)
            cam.pivot.set_quat(def_front_quat)

            if not view_id or view_id == current_view_id:
                Mgr.do("update_view_gizmo", False, True)

            if GD["coord_sys_type"] == "view":
                Mgr.get("selection").update_transform_values()

        self.is_front_custom = False

        if view_id:
            GD["view"] = current_view_id

    def __set_as_home_view(self):
        """ Set the current view as the Home view """

        cam = GD.cam
        self.home_pos = cam.pivot.get_pos()
        self.home_quat = cam.target.get_quat()
        self.home_zoom = cam.zoom

    def __reset_home_view(self):
        """ Reset the Home view """

        self.home_pos = self.home_default_pos
        self.home_quat = self.home_default_quat
        self.home_zoom = self.home_default_zoom

    def __reset_view(self, to_default=True, transition=False):
        """ Make the Home view the current view """

        cam = GD.cam
        lerp_view_gizmo = False

        if to_default:

            if transition and self.is_front_custom:
                lerp_view_gizmo = True
                gizmo_root = Mgr.get("view_gizmo_root")
                hpr = gizmo_root.get_hpr()

            self.__reset_front_view(transition=False, reset_roll=False)
            self.__reset_home_view()
            Mgr.update_app("active_grid_plane", self.default_grid_plane)
            Mgr.update_app("render_mode", self.default_render_mode)

            if lerp_view_gizmo:
                gizmo_root.set_hpr(hpr)

        current_quat = cam.target.get_quat()
        pos = self.home_pos
        quat = self.home_quat
        zoom = self.home_zoom
        almost_same_zoom = Vec3(0., zoom, 0.) == Vec3(0., cam.zoom, 0.)
        def_front_quat = self.default_front_quat

        if current_quat.almost_same_direction(quat, .000001) \
                and cam.pivot.get_pos() == pos and almost_same_zoom:

            if lerp_view_gizmo:
                gizmo_interval = LerpQuatInterval(gizmo_root, .5, def_front_quat, blendType="easeInOut")
                self._lerp_interval = gizmo_interval
                gizmo_interval.start()
                Mgr.add_task(self.__transition_view, "transition_view", sort=30,
                             uponDeath=self.__adjust_transition_hpr)
                Mgr.do("start_view_gizmo_transition")
                self._dest_view = "home"
                self._transition_done = False

            return

        if transition:

            lerp_interval = self.reset_interval

            if lerp_view_gizmo:
                gizmo_interval = LerpQuatInterval(gizmo_root, .5, def_front_quat, blendType="easeInOut")
                lerp_interval.append(gizmo_interval)

            self._lerp_interval = lerp_interval
            lerp_interval.start()
            Mgr.add_task(self.__transition_view, "transition_view", sort=30,
                         uponDeath=self.__adjust_transition_hpr)
            Mgr.do("start_view_gizmo_transition")
            self._dest_view = "home"
            self._transition_done = False

        else:

            cam.pivot.set_pos(pos)
            cam.target.set_quat(quat)
            cam.zoom = zoom
            Mgr.get("transf_gizmo").update()
            Mgr.do("update_coord_sys")
            Mgr.do("update_zoom_indicator")
            Mgr.do("update_view_gizmo")

            if GD["coord_sys_type"] == "view":
                Mgr.get("selection").update_transform_values()

    def __reset_all_views(self, to_default=True, transition=False):

        current_view_id = GD["view"]
        view_ids = ["persp", "ortho", "front", "back", "left", "right", "top", "bottom"]
        view_ids += self._user_view_ids

        for view_id in view_ids:
            GD["view"] = view_id
            self.__reset_view(to_default, transition)

        def task():

            GD["view"] = current_view_id
            Mgr.update_app("view", "set", "persp")

        PendingTasks.add(task, "set_persp_view", "ui")

    def __center_view_on_objects(self, transition=True, obj_to_align_to=None, obj_id=None):

        if self._lerp_interval:
            return

        from math import tan, radians

        if obj_to_align_to:

            objs = [obj_to_align_to]

        elif obj_id:

            obj = Mgr.get("object", obj_id)
            objs = [obj]

        else:

            pixel_color = Mgr.get("pixel_under_mouse")
            obj = Mgr.get("object", pixel_color=pixel_color)

            if obj:

                objs = [obj]

            else:

                selection = Mgr.get("selection_top")

                if selection:
                    objs = selection
                else:
                    objs = Mgr.get("objects")

        if not objs:
            return

        obj_root = Mgr.get("object_root")
        cam = GD.cam
        bounds_np = cam.origin.attach_new_node("cam_aligned_node")
        tmp_np = bounds_np.attach_new_node("tmp_node")

        if obj_to_align_to:
            bounds_np.set_hpr(obj_to_align_to.pivot, 0., 0., 0.)

        parents = {}
        parent_copies = {}

        bboxes = {obj: obj.bbox for obj in objs if obj.type == "model"
            and not obj.bbox.has_zero_size_owner}

        for bbox in bboxes.values():
            bbox.origin.detach_node()

        for obj in objs:

            orig = obj.origin
            parent = orig.parent
            parents[orig] = parent

            if parent in parent_copies:
                parent_copy = parent_copies[parent]
            else:
                parent_copy = NodePath("parent_copy")
                parent_copy.set_transform(parent.get_transform(GD.world))
                parent_copy.wrt_reparent_to(tmp_np)
                parent_copies[parent] = parent_copy

            orig.reparent_to(parent_copy)

        bounds = tmp_np.get_tight_bounds()

        for orig, parent in parents.items():
            orig.reparent_to(parent)

        for obj, bbox in bboxes.items():
            bbox.origin.reparent_to(obj.origin)

        centers = {}

        for obj in objs:

            center = obj.get_center_pos(tmp_np)

            if centers:
                centers["min"].x = min(centers["min"].x, center.x)
                centers["min"].y = min(centers["min"].y, center.y)
                centers["min"].z = min(centers["min"].z, center.z)
                centers["max"].x = max(centers["max"].x, center.x)
                centers["max"].y = max(centers["max"].y, center.y)
                centers["max"].z = max(centers["max"].z, center.z)
            else:
                centers = {"min": center, "max": VBase3(center)}

        if bounds:
            point_min, point_max = bounds
            point_min.x = min(point_min.x, centers["min"].x)
            point_min.y = min(point_min.y, centers["min"].y)
            point_min.z = min(point_min.z, centers["min"].z)
            point_max.x = max(point_max.x, centers["max"].x)
            point_max.y = max(point_max.y, centers["max"].y)
            point_max.z = max(point_max.z, centers["max"].z)
        else:
            point_min, point_max = centers["min"], centers["max"]

        if cam.lens.is_perspective():
            vec = (point_min - point_max) * .5
            center_pos = GD.world.get_relative_point(tmp_np, point_max + vec)
        else:
            vec = point_max - point_min
            center_pos = GD.world.get_relative_point(tmp_np, point_min + vec * .5)

        bounds_np.detach_node()

        if cam.lens.is_perspective():

            fov_h, fov_v = cam.lens.fov
            x, y, z = vec
            x = min(-.01, x)
            y = min(-.01, y)
            z = min(-.01, z)

            if vec.length_squared() < .000001:
                zoom = None
            else:
                zoom = y + ((x / tan(radians(fov_h * .5))) if x / z > fov_h / fov_v
                    else (z / tan(radians(fov_v * .5))))
                zoom = max(-1000000., min(-cam.lens.near, zoom))

            if transition:
                if zoom is None:
                    interval1 = None
                else:
                    interval1 = LerpPosInterval(cam.origin, .3, Point3(0., zoom, 0.),
                                                blendType="easeInOut")
            else:
                set_zoom = lambda: None if zoom is None else cam.origin.set_y(zoom)

        else:

            size_h, size_v = cam.lens.film_size
            x, y, z = vec
            x = max(.01, x)
            y = max(.01, y)
            z = max(.01, z)

            if vec.length_squared() < .000001:
                zoom = None
            else:
                zoom = (x / size_h) if x / z > size_h / size_v else (z / size_v)
                zoom *= cam.target.get_sx()
                zoom = min(100000., max(.0004, zoom))

            if transition:
                if zoom is None:
                    interval1 = None
                else:
                    interval1 = LerpScaleInterval(cam.target, .3, zoom, blendType="easeInOut")
            else:
                set_zoom = lambda: None if zoom is None else cam.target.set_scale(zoom)

        if transition:

            interval2 = LerpPosInterval(cam.pivot, .3, center_pos, blendType="easeInOut")
            lerp_interval = Parallel(interval2)

            if interval1 is not None:
                lerp_interval.append(interval1)

            if obj_to_align_to:
                quat = obj_to_align_to.pivot.get_quat(GD.world)
                interval3 = LerpQuatInterval(cam.pivot, .3, quat, blendType="easeInOut")
                interval4 = LerpQuatInterval(cam.target, .3, Quat(), blendType="easeInOut")
                interval5 = LerpQuatInterval(Mgr.get("view_gizmo_root"), .5,
                                             quat, blendType="easeInOut")
                lerp_interval.append(interval3)
                lerp_interval.append(interval4)
                lerp_interval.append(interval5)

            self._lerp_interval = lerp_interval
            lerp_interval.start()
            Mgr.add_task(self.__transition_view, "transition_view", sort=30)
            Mgr.do("start_view_gizmo_transition")
            self._dest_view = "obj_extents"
            self._transition_done = False

        else:

            cam.pivot.set_pos(center_pos)
            set_zoom()
            Mgr.get("transf_gizmo").update()
            Mgr.do("update_coord_sys")
            Mgr.do("update_zoom_indicator")

            if obj_to_align_to:
                Mgr.do("update_view_gizmo", False, True)

            if GD["coord_sys_type"] == "view":
                Mgr.get("selection").update_transform_values()

        if obj_to_align_to:
            self.is_front_custom = True
            quat = Quat()
            zoom = cam.zoom if zoom is None else zoom
            self.custom_home_default_pos = center_pos
            self.custom_home_default_quat = quat
            self.custom_home_default_zoom = zoom
            self.home_pos = center_pos
            self.home_quat = quat
            self.home_zoom = zoom

    def __do_preview(self, view_id):

        current_view_id = GD["view"]

        if view_id != current_view_id:

            current_lens_type = GD.cam.lens_type
            GD["view"] = view_id
            GD.cam.update()
            lens_type = GD.cam.lens_type
            Mgr.update_app("active_grid_plane", self.grid_plane)
            Mgr.update_app("render_mode", self.render_mode)

            if current_lens_type != lens_type:
                Mgr.get("grid").update(force=True)
                Mgr.get("picking_cam").adjust_to_lens()
                Mgr.get("transf_gizmo").adjust_to_lens(current_lens_type, lens_type)

            Mgr.do("update_zoom_indicator")
            Mgr.do("update_view_gizmo", cube=False, hpr=True)
            Mgr.get("transf_gizmo").update()
            Mgr.do("update_coord_sys")

            if GD["coord_sys_type"] == "view":
                Mgr.get("selection").update_transform_values()

            backgrounds = self._backgrounds
            Mgr.update_remotely("view", "enable_obj_align", view_id not in backgrounds)

            if current_view_id in backgrounds:
                backgrounds[current_view_id].hide()

            if view_id in backgrounds:
                self.__show_background(view_id)


MainObjects.add_class(ViewManager)
