from .base import *


class TextureMap:

    _wrap_modes = {
        "repeat": SamplerState.WM_repeat,
        "clamp": SamplerState.WM_clamp,
        "border_color": SamplerState.WM_border_color,
        "mirror": SamplerState.WM_mirror,
        "mirror_once": SamplerState.WM_mirror_once
    }

    _filter_types = {
        "nearest": SamplerState.FT_nearest,
        "linear": SamplerState.FT_linear,
        "nearest_mipmap_nearest": SamplerState.FT_nearest_mipmap_nearest,
        "nearest_mipmap_linear": SamplerState.FT_nearest_mipmap_linear,
        "linear_mipmap_nearest": SamplerState.FT_linear_mipmap_nearest,
        "linear_mipmap_linear": SamplerState.FT_linear_mipmap_linear,
        "shadow": SamplerState.FT_shadow
    }

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_texture"] = None

        return state

    def __setstate__(self, state):

        self.__dict__ = state

        if self.type != "layer":
            self.tex_stage = Mgr.get("tex_stage", self.type)

        self.set_texture(self._rgb_filename, self._alpha_filename)

    def __init__(self, map_type, layer_name=None):

        self.type = map_type

        if map_type == "layer":
            self.tex_stage = TextureStage(layer_name)
        else:
            self.tex_stage = Mgr.get("tex_stage", map_type)

        self._uv_set_id = 0
        self.active = False
        self._texture = None
        self._rgb_filename = ""
        self._alpha_filename = ""
        self._border_color = (0., 0., 0., 1.)
        self._wrap_modes_locked = True
        self._wrap_mode_ids = {"u": "repeat", "v": "repeat"}
        self._filter_ids = {"min": "linear", "mag": "linear"}
        self._anisotropic_degree = 1
        self._transform = {"offset": [0., 0.], "rotate": [0.], "scale": [1., 1.]}

    def copy(self):

        tex_map = TextureMap(self.type)
        tex_map.border_color = self._border_color
        tex_map.wrap_u = self._wrap_mode_ids["u"]
        tex_map.wrap_v = self._wrap_mode_ids["v"]
        tex_map.lock_wrap_modes(self._wrap_modes_locked)
        tex_map.minfilter = self._filter_ids["min"]
        tex_map.magfilter = self._filter_ids["mag"]
        tex_map.anisotropic_degree = self._anisotropic_degree
        tex_map.copy_transform(self._transform)
        texture = self._texture.make_copy() if self._texture else None
        tex_map.set_texture(self._rgb_filename, self._alpha_filename, texture)
        tex_map.active = self.active

        return tex_map

    def equals(self, other):

        if self.active != other.active:
            return False

        if not self.active:
            return True

        if self.get_tex_filenames() != other.get_tex_filenames():
            return False

        if not self._texture:
            return True

        other_tex_stage = TextureStage(other.tex_stage)
        other_tex_stage.name = self.tex_stage.name

        if self.tex_stage != other_tex_stage:
            return False

        if self._border_color != other.border_color:
            return False

        if self._wrap_mode_ids["u"] != other.wrap_u:
            return False

        if self._wrap_mode_ids["v"] != other.wrap_v:
            return False

        if self._wrap_modes_locked != other.are_wrap_modes_locked():
            return False

        if self._filter_ids["min"] != other.minfilter:
            return False

        if self._filter_ids["mag"] != other.magfilter:
            return False

        if self._anisotropic_degree != other.anisotropic_degree:
            return False

        for transf_type in ("offset", "rotate", "scale"):
            if self._transform[transf_type] != other.get_transform(transf_type):
                return False

        return True

    @property
    def anisotropic_degree(self):

        return self._anisotropic_degree

    @anisotropic_degree.setter
    def anisotropic_degree(self, anisotropic_degree):

        self._anisotropic_degree = anisotropic_degree
        texture = self._texture

        if texture:
            texture.anisotropic_degree = anisotropic_degree

    @property
    def border_color(self):

        return self._border_color

    @border_color.setter
    def border_color(self, color_values):

        self._border_color = color_values
        texture = self._texture

        if texture:
            texture.border_color = VBase4(*color_values)

    @property
    def sort(self):

        return self.tex_stage.sort

    @sort.setter
    def sort(self, sort):

        self.tex_stage.sort = sort

    @property
    def priority(self):

        return self.tex_stage.priority

    @priority.setter
    def priority(self, priority):

        self.tex_stage.priority = priority

    def __set_wrap_mode(self, axis, wrap_mode_id):

        self._wrap_mode_ids[axis] = wrap_mode_id

        if self._wrap_modes_locked:
            self._wrap_mode_ids["v" if axis == "u" else "u"] = wrap_mode_id

        texture = self._texture

        if texture:

            wrap_mode = self._wrap_modes[wrap_mode_id]

            if axis == "u":
                texture.wrap_u = wrap_mode
                if self._wrap_modes_locked:
                    texture.wrap_v = wrap_mode
            else:
                texture.wrap_v = wrap_mode
                if self._wrap_modes_locked:
                    texture.wrap_u = wrap_mode

    @property
    def wrap_u(self):

        return self._wrap_mode_ids["u"]

    @wrap_u.setter
    def wrap_u(self, wrap_mode_id):

        self.__set_wrap_mode("u", wrap_mode_id)

    @property
    def wrap_v(self):

        return self._wrap_mode_ids["v"]

    @wrap_v.setter
    def wrap_v(self, wrap_mode_id):

        self.__set_wrap_mode("v", wrap_mode_id)

    def __set_filter_type(self, minmag, filter_id):

        self._filter_ids[minmag] = filter_id
        texture = self._texture

        if texture:
            if minmag == "min":
                texture.minfilter = self._filter_types[filter_id]
            else:
                texture.magfilter = self._filter_types[filter_id]

    @property
    def minfilter(self):

        return self._filter_ids["min"]

    @minfilter.setter
    def minfilter(self, filter_id):

        self.__set_filter_type("min", filter_id)

    @property
    def magfilter(self):

        return self._filter_ids["mag"]

    @magfilter.setter
    def magfilter(self, filter_id):

        self.__set_filter_type("mag", filter_id)

    @property
    def uv_set_name(self):

        return self.tex_stage.texcoord_name.name

    def set_uv_set_id(self, uv_set_id):

        if self._uv_set_id == uv_set_id:
            return False

        name = str(uv_set_id) if uv_set_id else InternalName.get_texcoord()
        self.tex_stage.set_texcoord_name(name)
        self._uv_set_id = uv_set_id

        return True

    @property
    def uv_set_id(self):

        return self._uv_set_id

    @uv_set_id.setter
    def uv_set_id(self, uv_set_id):

        self.set_uv_set_id(uv_set_id)

    def set_texture(self, rgb_filename="", alpha_filename="", texture=None):

        if texture is None:

            if rgb_filename:

                paths = ",".join(GD["config"]["texfile_paths"])
                rgb_fname = Filename.from_os_specific(rgb_filename)

                if rgb_fname.exists():
                    rgb_fullpath = rgb_filename
                else:
                    rgb_basename = rgb_fname.get_basename()
                    rgb_fname = Filename.from_os_specific(rgb_basename)
                    rgb_fname = DSearchPath.search_path(rgb_fname, paths, ",")
                    rgb_fullpath = rgb_fname.to_os_specific()

                if rgb_fname:

                    texture = Mgr.load_tex(rgb_fname)
                    alpha_fullpath = ""

                    if not texture.is_of_type(MovieTexture):

                        texture = Texture(self.type)

                        if alpha_filename:

                            a_fname = Filename.from_os_specific(alpha_filename)

                            if a_fname.exists():
                                alpha_fullpath = alpha_filename
                            else:
                                alpha_basename = a_fname.get_basename()
                                a_fname = Filename.from_os_specific(alpha_basename)
                                a_fname = DSearchPath.search_path(a_fname, paths, ",")
                                alpha_fullpath = a_fname.to_os_specific()

                            if a_fname:
                                texture.read(rgb_fname, a_fname, 0, 0)
                            else:
                                texture = None

                        else:

                            alpha_fullpath = ""
                            texture.read(rgb_fname)

                else:

                    texture = None

            else:

                texture = None

        else:

            rgb_fullpath = rgb_filename
            alpha_fullpath = alpha_filename

        if texture:
            texture.border_color = VBase4(*self._border_color)
            texture.wrap_u = self._wrap_modes[self._wrap_mode_ids["u"]]
            texture.wrap_v = self._wrap_modes[self._wrap_mode_ids["v"]]
            texture.minfilter = self._filter_types[self._filter_ids["min"]]
            texture.magfilter = self._filter_types[self._filter_ids["mag"]]
            texture.anisotropic_degree = self._anisotropic_degree
            self._rgb_filename = rgb_fullpath
            self._alpha_filename = alpha_fullpath
        else:
            self._rgb_filename = ""
            self._alpha_filename = ""

        self._texture = texture

        return texture

    def get_texture(self):

        return self._texture

    def get_tex_filenames(self):

        return self._rgb_filename, self._alpha_filename

    def has_texture(self, rgb_filename, alpha_filename):

        return self._rgb_filename == rgb_filename and self._alpha_filename == alpha_filename

    def lock_wrap_modes(self, lock):

        self._wrap_modes_locked = lock
        ids = self._wrap_mode_ids
        wrap_mode_id = ids["u"]

        if not lock or ids["v"] == wrap_mode_id:
            return

        ids["v"] = wrap_mode_id
        texture = self._texture

        if texture:
            texture.wrap_v = self._wrap_modes[wrap_mode_id]

    def are_wrap_modes_locked(self):

        return self._wrap_modes_locked

    def set_transform(self, transf_type, comp_index, value):

        self._transform[transf_type][comp_index] = value

    def get_transform(self, transf_type=None):

        return self._transform if transf_type is None else self._transform[transf_type]

    def copy_transform(self, transform):

        self._transform = {k: v[:] for k, v in transform.items()}


class Layer(TextureMap):

    blend_modes = {
        "modulate": TextureStage.M_modulate,
        "combine": TextureStage.M_combine,
        "replace": TextureStage.M_replace,
        "decal": TextureStage.M_decal,
        "add": TextureStage.M_add,
        "blend": TextureStage.M_blend,
        "blend_color_scale": TextureStage.M_blend_color_scale,
        "selector": TextureStage.M_selector
    }
    combine_modes = {
        "modulate": TextureStage.CM_modulate,
        "interpolate": TextureStage.CM_interpolate,
        "replace": TextureStage.CM_replace,
        "subtract": TextureStage.CM_subtract,
        "add": TextureStage.CM_add,
        "add_signed": TextureStage.CM_add_signed,
        "dot3rgb": TextureStage.CM_dot3_rgb,
        "dot3rgba": TextureStage.CM_dot3_rgba
    }
    combine_mode_sources = {
        "texture": TextureStage.CS_texture,
        "previous_layer": TextureStage.CS_previous,
        "last_stored_layer": TextureStage.CS_last_saved_result,
        "primary_color": TextureStage.CS_primary_color,
        "constant_color": TextureStage.CS_constant,
        "const_color_scale": TextureStage.CS_constant_color_scale
    }
    combine_mode_src_channels = {
        "rgb": TextureStage.CO_src_color,
        "1-rgb": TextureStage.CO_one_minus_src_color,
        "alpha": TextureStage.CO_src_alpha,
        "1-alpha": TextureStage.CO_one_minus_src_alpha
    }

    def __init__(self, layer_id, name):

        TextureMap.__init__(self, "layer", name)

        self.id = layer_id
        self._name = name
        self._blend_mode = "modulate"
        self._uses_combine_mode = False

        cmbmode_data = {}
        cmbmode_data["channels"] = "rgb"
        mode_ids = list(self.combine_modes.keys())

        for channels in ("rgb", "alpha"):

            cmbmode_data[channels] = data = {}
            data["on"] = False
            data["mode"] = "modulate"
            data["source_index"] = 0
            data["sources"] = sources = {}

            for mode_id in mode_ids:
                sources[mode_id] = [["texture", channels]]

        mode_ids.remove("replace")

        for channels in ("rgb", "alpha"):

            sources = cmbmode_data[channels]["sources"]

            for mode_id in mode_ids:
                sources[mode_id].append(["previous_layer", channels])

            sources["interpolate"].append(["last_stored_layer", channels])

        self._combine_mode_data = cmbmode_data

        self.active = True

    def __copy_combine_mode_data(self):

        orig_data = self._combine_mode_data
        copy_data = orig_data.copy()
        copy_data["channels"]
        mode_ids = list(self.combine_modes.keys())

        for channels in ("rgb", "alpha"):

            copy_data[channels] = orig_data[channels].copy()
            old_sources = orig_data[channels]["sources"]
            copy_data[channels]["sources"] = new_sources = old_sources.copy()

            for mode_id, source_data in old_sources.items():
                new_sources[mode_id] = [source_ids[:] for source_ids in source_data]

        return copy_data

    def copy(self, copy_name=False):

        layer = Mgr.do("create_tex_layer")

        if copy_name:
            layer.name = self._name

        layer.border_color = self.border_color
        layer.wrap_u = self.wrap_u
        layer.wrap_v = self.wrap_v
        layer.lock_wrap_modes(self.are_wrap_modes_locked())
        layer.minfilter = self.minfilter
        layer.magfilter = self.magfilter
        layer.anisotropic_degree = self.anisotropic_degree
        layer.uv_set_id = self.uv_set_id
        layer.copy_transform(self.get_transform())
        rgb_filename, alpha_filename = self.get_tex_filenames()
        tex = self.get_texture()
        tex_copy = tex.make_copy() if tex else None
        layer.set_texture(rgb_filename, alpha_filename, tex_copy)
        layer.color = self.color
        layer.rgb_scale = self.rgb_scale
        layer.alpha_scale = self.alpha_scale
        layer.sort = self.sort
        layer.priority = self.priority
        layer.stored = self.stored
        layer.set_combine_mode_data(self.__copy_combine_mode_data())
        layer.blend_mode = self._blend_mode
        layer.active = self.active

        return layer

    @property
    def name(self):

        return self._name

    @name.setter
    def name(self, name):

        self.tex_stage.name = name
        self._name = name

    @property
    def color(self):

        r, g, b, a = self.tex_stage.color

        return r, g, b, a

    @color.setter
    def color(self, color):

        self.tex_stage.color = color

    @property
    def rgb_scale(self):

        return self.tex_stage.rgb_scale

    @rgb_scale.setter
    def rgb_scale(self, scale):

        self.tex_stage.rgb_scale = scale

    @property
    def alpha_scale(self):

        return self.tex_stage.alpha_scale

    @alpha_scale.setter
    def alpha_scale(self, scale):

        self.tex_stage.alpha_scale = scale

    @property
    def stored(self):

        return self.tex_stage.saved_result

    @stored.setter
    def stored(self, stored):

        self.tex_stage.saved_result = stored

    @property
    def blend_mode(self):

        return self._blend_mode

    @blend_mode.setter
    def blend_mode(self, mode_id):

        self._blend_mode = mode_id

        if not self._uses_combine_mode:
            self.tex_stage.set_mode(self.blend_modes[mode_id])

    def __apply_combine_mode(self, combine_channels=None):

        data = self._combine_mode_data
        channels = data["channels"] if combine_channels is None else combine_channels

        if not data[channels]["on"]:
            return

        mode_id = data[channels]["mode"]
        mode = self.combine_modes[mode_id]
        source_ids = data[channels]["sources"][mode_id]
        sources = (self.combine_mode_sources, self.combine_mode_src_channels)
        used_sources = [sources[j][source_ids[i][j]] for i in range(len(source_ids))
                        for j in range(2)]

        if channels == "rgb":
            self.tex_stage.set_combine_rgb(mode, *used_sources)
        else:
            self.tex_stage.set_combine_alpha(mode, *used_sources)

    def set_combine_mode_data(self, data):

        self._combine_mode_data = data
        self._uses_combine_mode = data["rgb"]["on"] or data["alpha"]["on"]

        if data["rgb"]["on"]:
            self.__apply_combine_mode("rgb")

        if data["alpha"]["on"]:
            self.__apply_combine_mode("alpha")

    def set_combine_channels(self, channels):

        data = self._combine_mode_data
        data["channels"] = channels
        on = data[channels]["on"]
        mode_id = data[channels]["mode"]
        source_ids = data[channels]["sources"][mode_id]
        count = len(source_ids)
        index = data[channels]["source_index"]
        source, src_channels = source_ids[index]
        layer_id = self.id
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_channels_use", on)
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_mode", mode_id)
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_source_count", count)
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_source_index", index)
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_source", source)
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_source_channels", src_channels)

    def get_selected_combine_channels(self):

        return self._combine_mode_data["channels"]

    def use_combine_channels(self, uses_channels):

        data = self._combine_mode_data
        channels = data["channels"]
        data[channels]["on"] = uses_channels
        self._uses_combine_mode = data["rgb"]["on"] or data["alpha"]["on"]

        if uses_channels:

            self.__apply_combine_mode()

        else:

            mode = self.combine_modes["modulate"]
            sources = self.combine_mode_sources
            tex = sources["texture"]
            prev = sources["previous_layer"]

            if channels == "rgb":
                rgb = self.combine_mode_src_channels["rgb"]
                self.tex_stage.set_combine_rgb(mode, tex, rgb, prev, rgb)
            else:
                alpha = self.combine_mode_src_channels["alpha"]
                self.tex_stage.set_combine_alpha(mode, tex, alpha, prev, alpha)

            other_channels = "alpha" if channels == "rgb" else "rgb"

            if not data[other_channels]["on"]:
                self.tex_stage.set_mode(self.blend_modes[self._blend_mode])

    def uses_combine_mode(self):

        return self._uses_combine_mode

    def set_combine_mode(self, mode_id):

        data = self._combine_mode_data
        channels = data["channels"]
        data[channels]["mode"] = mode_id

        if self._uses_combine_mode:
            self.__apply_combine_mode()

        source_ids = data[channels]["sources"][mode_id]
        count = len(source_ids)
        data[channels]["source_index"] = 0
        source, src_channels = source_ids[0]
        layer_id = self.id
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_source_count", count)
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_source_index", 0)
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_source", source)
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_source_channels", src_channels)

    def set_combine_source_index(self, index):

        data = self._combine_mode_data
        channels = data["channels"]
        data[channels]["source_index"] = index
        mode_id = data[channels]["mode"]
        source_ids = data[channels]["sources"][mode_id]
        source, src_channels = source_ids[index]
        layer_id = self.id
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_source", source)
        Mgr.update_remotely("tex_layer_prop", layer_id, "combine_source_channels", src_channels)

    def set_combine_source(self, source_id):

        data = self._combine_mode_data
        channels = data["channels"]
        index = data[channels]["source_index"]
        mode_id = data[channels]["mode"]
        source_ids = data[channels]["sources"][mode_id]
        source_ids[index][0] = source_id

        if self._uses_combine_mode:
            self.__apply_combine_mode()

    def set_combine_source_channels(self, src_channels):

        data = self._combine_mode_data
        channels = data["channels"]
        index = data[channels]["source_index"]
        mode_id = data[channels]["mode"]
        source_ids = data[channels]["sources"][mode_id]
        source_ids[index][1] = src_channels

        if self._uses_combine_mode:
            self.__apply_combine_mode()

    def set_property(self, prop_id, value):

        if prop_id == "name":
            self.name = value
        elif prop_id == "color":
            self.color = value
        elif prop_id == "rgb_scale":
            self.rgb_scale = value
        elif prop_id == "alpha_scale":
            self.alpha_scale = value
        elif prop_id == "uv_set_id":
            self.uv_set_id = value
        elif prop_id == "sort":
            self.sort = value
        elif prop_id == "priority":
            self.priority = value
        elif prop_id == "border_color":
            self.border_color = value
        elif prop_id == "wrap_lock":
            self.lock_wrap_modes(value)
        elif prop_id == "wrap_u":
            self.wrap_u = value
        elif prop_id == "wrap_v":
            self.wrap_v = value
        elif prop_id == "filter_min":
            self.minfilter = value
        elif prop_id == "filter_mag":
            self.magfilter = value
        elif prop_id == "anisotropic_degree":
            self.anisotropic_degree = value
        elif prop_id == "stored":
            self.stored = value
        elif prop_id == "blend_mode":
            self.blend_mode = value
        elif prop_id == "combine_mode":
            self.set_combine_mode(value)
        elif prop_id == "combine_channels":
            self.set_combine_channels(value)
        elif prop_id == "combine_channels_use":
            self.use_combine_channels(value)
        elif prop_id == "combine_source_index":
            self.set_combine_source_index(value)
        elif prop_id == "combine_source":
            self.set_combine_source(value)
        elif prop_id == "combine_source_channels":
            self.set_combine_source_channels(value)


class TexMapManager:

    def __init__(self):

        self._layers = {}
        self._tex_stages = {}
        self._id_generator = id_generator()

    def setup(self):

        TS = TextureStage
        stages = self._tex_stages
        map_types = ("color", "normal", "height", "normal+height", "gloss",
                     "color+gloss", "normal+gloss", "glow", "color+glow")
        modes = (TS.M_modulate, TS.M_normal, TS.M_height, TS.M_normal_height, TS.M_gloss,
                 TS.M_modulate_gloss, TS.M_normal_gloss, TS.M_glow, TS.M_modulate_glow)

        for map_type, mode in zip(map_types, modes):
            stage = TS(f"tex_stage_{map_type}")
            stage.set_mode(mode)
            stages[map_type] = stage

        stages["vertex_colors"] = TS.default

        Mgr.accept("create_tex_map", self.__create_tex_map)
        Mgr.accept("create_tex_layer", self.__create_layer)
        Mgr.accept("register_tex_layer", self.__register_layer)
        Mgr.accept("unregister_tex_layer", self.__unregister_layer)
        Mgr.expose("tex_layer", lambda layer_id: self._layers.get(layer_id))
        Mgr.expose("tex_stage", lambda map_type: self._tex_stages.get(map_type))
        Mgr.expose("unique_tex_layer_name", self.__get_unique_layer_name)
        Mgr.expose("next_tex_layer_id", lambda: ("tex_layer",) + next(self._id_generator))
        Mgr.add_app_updater("new_tex_layer", self.__update_new_layer)
        Mgr.add_app_updater("tex_layer_selection", self.__select_layer)
        Mgr.add_app_updater("removed_tex_layer", self.__remove_layer)
        Mgr.add_app_updater("tex_layer_prop", self.__set_layer_property)

        return "texture_maps_ok"

    def __get_unique_layer_name(self, material, requested_name="", layer=None):

        layers = material.get_layers()

        if layer and layer in layers:
            layers.remove(layer)

        namelist = [l.name for l in layers]
        search_pattern = r"^Layer\s*(\d+)$"
        naming_pattern = "Layer {:02d}"

        return get_unique_name(requested_name, namelist, search_pattern, naming_pattern)

    def __create_tex_map(self, map_type):

        return TextureMap(map_type)

    def __create_layer(self, material=None):

        layer_id = ("tex_layer",) + next(self._id_generator)

        if material:
            name = self.__get_unique_layer_name(material)
        else:
            name = ""

        layer = Layer(layer_id, name)

        return layer

    def __register_layer(self, layer):

        self._layers[layer.id] = layer

    def __unregister_layer(self, layer):

        del self._layers[layer.id]

    def __update_new_layer(self, material_id, source_layer_id):

        material = Mgr.get("material", material_id)

        if source_layer_id is None:
            layer_id = ("tex_layer",) + next(self._id_generator)
            name = self.__get_unique_layer_name(material)
            layer = Layer(layer_id, name)
            material.add_layer(layer)
            self._layers[layer_id] = layer
            Mgr.update_remotely("new_tex_layer", layer_id, name)
            return

        source_layer = self._layers[source_layer_id]
        source_name = source_layer.name
        original_name = re.sub(r" - copy$| - copy \(\d+\)$", "", source_name, 1)
        copy_name = original_name + " - copy"
        copy_name = self.__get_unique_layer_name(material, copy_name)
        layer = source_layer.copy()
        layer.name = copy_name
        layer_id = layer.id
        self._layers[layer_id] = layer
        material.add_layer(layer)
        Mgr.update_remotely("new_tex_layer", layer_id, copy_name)

    def __remove_layer(self, material_id, layer_id):

        material = Mgr.get("material", material_id)
        layer = self._layers[layer_id]
        material.remove_layer(layer)
        del self._layers[layer_id]

        if not material.get_layers():
            layer_id = ("tex_layer",) + next(self._id_generator)
            name = self.__get_unique_layer_name(material)
            layer = Layer(layer_id, name)
            material.add_layer(layer)
            self._layers[layer_id] = layer
            Mgr.update_remotely("new_tex_layer", layer_id, name)

    def __select_layer(self, material_id, layer_id):

        material = Mgr.get("material", material_id)
        material.set_selected_layer_id(layer_id)
        layer = self._layers[layer_id]

        prop_id = "on"
        on = layer.active
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, on)
        rgb_filename, alpha_filename = layer.get_tex_filenames()
        prop_id = "color"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.color)
        prop_id = "rgb_scale"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.rgb_scale)
        prop_id = "alpha_scale"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.alpha_scale)
        prop_id = "file_main"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, rgb_filename)
        prop_id = "file_alpha"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, alpha_filename)
        prop_id = "sort"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.sort)
        prop_id = "priority"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.priority)
        prop_id = "border_color"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.border_color)
        prop_id = "wrap_u"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.wrap_u)
        prop_id = "wrap_v"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.wrap_v)
        prop_id = "wrap_lock"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.are_wrap_modes_locked())
        prop_id = "filter_min"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.minfilter)
        prop_id = "filter_mag"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.magfilter)
        prop_id = "anisotropic_degree"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.anisotropic_degree)
        prop_id = "transform"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.get_transform())
        prop_id = "uv_set"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.uv_set_id)
        prop_id = "stored"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.stored)
        prop_id = "blend_mode"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, layer.blend_mode)

        channels = layer.get_selected_combine_channels()
        prop_id = "combine_channels"
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, channels)
        layer.set_combine_channels(channels)

    def __set_layer_property(self, material_id, layer_id, prop_id, value):

        material = Mgr.get("material", material_id)
        layer = self._layers[layer_id]
        reapply_layer = False

        if prop_id == "name":
            value = self.__get_unique_layer_name(material, value, layer)
        elif prop_id == "on":
            material.set_map_active("layer", layer_id, value)
            Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, value)
            return
        elif prop_id == "sort":
            layers = material.get_layers()
            value = max(0, min(value, len(layers) - 1))
            layers.remove(layer)
            layers.insert(value, layer)
            for i, l in enumerate(layers):
                if l is not layer:
                    l.sort = i
            reapply_layer = True
        elif prop_id == "wrap_u":
            if layer.are_wrap_modes_locked():
                Mgr.update_remotely("tex_layer_prop", layer_id, "wrap_v", value)
        elif prop_id == "wrap_v":
            if layer.are_wrap_modes_locked():
                Mgr.update_remotely("tex_layer_prop", layer_id, "wrap_u", value)
        elif prop_id == "wrap_lock":
            if value:
                mode_id = layer.wrap_u
                Mgr.update_remotely("tex_layer_prop", layer_id, "wrap_v", mode_id)
        elif prop_id == "anisotropic_degree":
            value = max(1, min(value, 16))
        elif prop_id == "offset_u":
            material.set_map_transform("layer", layer_id, "offset", 0, value)
            Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, value)
            return
        elif prop_id == "offset_v":
            material.set_map_transform("layer", layer_id, "offset", 1, value)
            Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, value)
            return
        elif prop_id == "rotate":
            material.set_map_transform("layer", layer_id, "rotate", 0, value)
            Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, value)
            return
        elif prop_id == "scale_u":
            material.set_map_transform("layer", layer_id, "scale", 0, value)
            Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, value)
            return
        elif prop_id == "scale_v":
            material.set_map_transform("layer", layer_id, "scale", 1, value)
            Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, value)
            return
        elif prop_id == "uv_set":
            value = max(0, min(value, 7))
            material.set_layer_uv_set_id(layer, value)
            Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, value)
            return
        elif prop_id in ("color", "rgb_scale", "alpha_scale", "blend_mode",
                         "combine_mode", "combine_channels_use", "combine_source",
                         "combine_source_channels", "stored"):
            reapply_layer = True

        layer.set_property(prop_id, value)
        Mgr.update_remotely("tex_layer_prop", layer_id, prop_id, value)

        if reapply_layer:
            material.reapply_layer(layer)


MainObjects.add_class(TexMapManager)
