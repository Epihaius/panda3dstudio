from ..base import *


SS = SamplerState
WRAP_MODES = (SS.WM_repeat, SS.WM_clamp, SS.WM_border_color, SS.WM_mirror, SS.WM_mirror_once)
WRAP_MODE_IDS = ("repeat", "clamp", "border_color", "mirror", "mirror_once")
FILTER_TYPES = (SS.FT_nearest, SS.FT_linear, SS.FT_nearest_mipmap_nearest,
                SS.FT_nearest_mipmap_linear, SS.FT_linear_mipmap_nearest,
                SS.FT_linear_mipmap_linear, SS.FT_shadow, SS.FT_default)
FILTER_TYPE_IDS = ("nearest", "linear", "nearest_mipmap_nearest", "nearest_mipmap_linear",
                   "linear_mipmap_nearest", "linear_mipmap_linear", "shadow", "linear")

TS = TextureStage
FXMAP_TYPES = (TS.M_normal, TS.M_height, TS.M_normal_height, TS.M_gloss,
               TS.M_modulate_gloss, TS.M_glow, TS.M_modulate_glow)
FXMAP_IDS = ("normal", "height", "normal+height", "gloss",
             "color+gloss", "glow", "color+glow")
BLEND_MODES = (TS.M_modulate, TS.M_replace, TS.M_decal, TS.M_add,
               TS.M_blend, TS.M_blend_color_scale, TS.M_selector)
BLEND_MODE_IDS = ("modulate", "replace", "decal", "add",
                  "blend", "blend_color_scale", "selector")
COMBINE_MODES = (TS.CM_modulate, TS.CM_interpolate, TS.CM_replace, TS.CM_subtract,
                 TS.CM_add, TS.CM_add_signed, TS.CM_dot3_rgb, TS.CM_dot3_rgba)
COMBINE_MODE_IDS = ("modulate", "interpolate", "replace", "subtract",
                    "add", "add_signed", "dot3rgb", "dot3rgba")
COMBINE_MODE_SOURCES = (TS.CS_texture, TS.CS_previous, TS.CS_last_saved_result,
                        TS.CS_primary_color, TS.CS_constant, TS.CS_constant_color_scale)
COMBINE_MODE_SOURCE_IDS = ("texture", "previous_layer", "last_stored_layer",
                           "primary_color", "constant_color", "const_color_scale")
COMBINE_MODE_SRC_CHANNELS = (TS.CO_src_color, TS.CO_one_minus_src_color,
                             TS.CO_src_alpha, TS.CO_one_minus_src_alpha)
COMBINE_MODE_SRC_CHANNEL_IDS = ("rgb", "1-rgb", "alpha", "1-alpha")


def __set_texmap_properties(tex_map, texture, stage, tex_xforms):

    tex_map.set_border_color(tuple(texture.get_border_color()))
    wrap_ids = dict(zip(WRAP_MODES, WRAP_MODE_IDS))
    wrap_u_mode = texture.get_wrap_u()
    wrap_v_mode = texture.get_wrap_v()
    tex_map.lock_wrap_modes(False)
    tex_map.set_wrap_mode("u", wrap_ids[wrap_u_mode])
    tex_map.set_wrap_mode("v", wrap_ids[wrap_v_mode])
    tex_map.lock_wrap_modes(wrap_u_mode == wrap_v_mode)
    filter_ids = dict(zip(FILTER_TYPES, FILTER_TYPE_IDS))
    tex_map.set_filter_type("min", filter_ids[texture.get_minfilter()])
    tex_map.set_filter_type("mag", filter_ids[texture.get_magfilter()])
    tex_map.set_anisotropic_degree(texture.get_anisotropic_degree())

    if stage in tex_xforms:
        transform = tex_xforms[stage]
        tex_offset_u, tex_offset_v = transform.get_pos2d()
        tex_rotate = transform.get_rotate2d()
        tex_scale_u, tex_scale_v = transform.get_scale2d()
        tex_map.set_transform("offset", 0, tex_offset_u)
        tex_map.set_transform("offset", 1, tex_offset_v)
        tex_map.set_transform("rotate", 0, tex_rotate)
        tex_map.set_transform("scale", 0, tex_scale_u)
        tex_map.set_transform("scale", 1, tex_scale_v)


def __set_layer_properties(layer, stage, tex_attrib, off_stages, tex_xforms):

    if stage in off_stages:
        layer.set_active(False)

    texture = tex_attrib.get_on_texture(stage)

    if texture:
        rgb_filename = texture.get_fullpath().to_os_specific()
        alpha_filename = texture.get_alpha_fullpath().to_os_specific()
        layer.set_texture(rgb_filename, alpha_filename)
        __set_texmap_properties(layer, texture, stage, tex_xforms)

    layer.set_sort(stage.get_sort())
    layer.set_priority(stage.get_priority())

    mode = stage.get_mode()

    if mode == TS.M_combine:

        layer.set_blend_mode("modulate")

        cmbmode_data = {}
        cmbmode_data["channels"] = "rgb"
        mode_ids = list(COMBINE_MODE_IDS)
        combine_ids = dict(zip(COMBINE_MODES, COMBINE_MODE_IDS))
        combine_ids[TS.CM_undefined] = "modulate"

        for channels in ("rgb", "alpha"):

            cmbmode_data[channels] = data = {}
            data["source_index"] = 0
            data["sources"] = sources = {}

            for mode_id in mode_ids:
                sources[mode_id] = [["texture", channels]]

        combine_rgb_mode = stage.get_combine_rgb_mode()
        combine_alpha_mode = stage.get_combine_alpha_mode()
        combine_rgb_mode_id = combine_ids[combine_rgb_mode]
        combine_alpha_mode_id = combine_ids[combine_alpha_mode]
        cmbmode_data["rgb"]["on"] = combine_rgb_mode != TS.CM_undefined
        cmbmode_data["alpha"]["on"] = combine_alpha_mode != TS.CM_undefined
        cmbmode_data["rgb"]["mode"] = combine_rgb_mode_id
        cmbmode_data["alpha"]["mode"] = combine_alpha_mode_id

        mode_ids.remove("replace")

        for channels in ("rgb", "alpha"):

            sources = cmbmode_data[channels]["sources"]

            for mode_id in mode_ids:
                sources[mode_id].append(["previous_layer", channels])

            sources["interpolate"].append(["last_stored_layer", channels])

        combine_src_ids = dict(zip(COMBINE_MODE_SOURCES, COMBINE_MODE_SOURCE_IDS))
        combine_src_chnl_ids = dict(zip(COMBINE_MODE_SRC_CHANNELS, COMBINE_MODE_SRC_CHANNEL_IDS))

        source_ids = cmbmode_data["rgb"]["sources"][combine_rgb_mode_id]
        src_count = len(source_ids)

        if combine_rgb_mode != TS.CM_undefined:

            source = stage.get_combine_rgb_source0()
            source_channel = stage.get_combine_rgb_operand0()
            source_ids[0][0] = combine_src_ids[source]
            source_ids[0][1] = combine_src_chnl_ids[source_channel]

            if src_count > 1:
                source = stage.get_combine_rgb_source1()
                source_channel = stage.get_combine_rgb_operand1()
                source_ids[1][0] = combine_src_ids[source]
                source_ids[1][1] = combine_src_chnl_ids[source_channel]

            if src_count > 2:
                source = stage.get_combine_rgb_source2()
                source_channel = stage.get_combine_rgb_operand2()
                source_ids[2][0] = combine_src_ids[source]
                source_ids[2][1] = combine_src_chnl_ids[source_channel]

        if combine_alpha_mode != TS.CM_undefined:

            source_ids = cmbmode_data["alpha"]["sources"][combine_alpha_mode_id]
            src_count = len(source_ids)

            source = stage.get_combine_alpha_source0()
            source_channel = stage.get_combine_alpha_operand0()
            source_ids[0][0] = combine_src_ids[source]
            source_ids[0][1] = combine_src_chnl_ids[source_channel]

            if src_count > 1:
                source = stage.get_combine_alpha_source1()
                source_channel = stage.get_combine_alpha_operand1()
                source_ids[1][0] = combine_src_ids[source]
                source_ids[1][1] = combine_src_chnl_ids[source_channel]

            if src_count > 2:
                source = stage.get_combine_alpha_source2()
                source_channel = stage.get_combine_alpha_operand2()
                source_ids[2][0] = combine_src_ids[source]
                source_ids[2][1] = combine_src_chnl_ids[source_channel]

        layer.set_combine_mode_data(cmbmode_data)
        layer.store(stage.get_saved_result())
        layer.set_rgb_scale(stage.get_rgb_scale())
        layer.set_alpha_scale(stage.get_alpha_scale())
        layer.set_color(tuple(stage.get_color()))

    elif mode in BLEND_MODES:

        layer.set_blend_mode(dict(zip(BLEND_MODES, BLEND_MODE_IDS))[mode])


def render_state_to_material(render_state):

    default_uv_set_name = InternalName.get_texcoord()
    uv_set_list = [default_uv_set_name]
    uv_set_list += [InternalName.get_texcoord_name(str(i))
                    for i in range(1, 8)]
    uv_set_names = {}

    if render_state.is_empty():

        material = None

    else:

        material = Mgr.do("create_material")
        color_attr_type = ColorAttrib.get_class_type()
        color_scale_attr_type = ColorScaleAttrib.get_class_type()
        material_attr_type = MaterialAttrib.get_class_type()
        transp_attr_type = TransparencyAttrib.get_class_type()
        tex_attr_type = TextureAttrib.get_class_type()
        tex_matrix_attr_type = TexMatrixAttrib.get_class_type()

        if render_state.has_attrib(color_attr_type):

            color_attrib = render_state.get_attrib(color_attr_type)

            if color_attrib.get_color_type() == ColorAttrib.T_vertex:
                material.set_property("show_vert_colors", True)
            elif color_attrib.get_color_type() == ColorAttrib.T_flat:
                color = color_attrib.get_color()
                material.set_property("flat_color", tuple(color))

        if render_state.has_attrib(material_attr_type):

            mat_attrib = render_state.get_attrib(material_attr_type)

            if not mat_attrib.is_off():

                m = mat_attrib.get_material()
                diffuse = {"value": tuple(m.get_diffuse()), "on": m.has_diffuse()}
                ambient = {"value": tuple(m.get_ambient()), "on": m.has_ambient()}
                emissive = {"value": tuple(m.get_emission()), "on": m.has_emission()}
                specular = {"value": tuple(m.get_specular()), "on": m.has_specular()}
                shininess = {"value": m.get_shininess(), "on": True}

                material.set_property("diffuse", diffuse, apply_base_mat=False)
                material.set_property("ambient", ambient, apply_base_mat=False)
                material.set_property("emissive", emissive, apply_base_mat=False)
                material.set_property("specular", specular, apply_base_mat=False)
                material.set_property("shininess", shininess, apply_base_mat=False)

        if render_state.has_attrib(transp_attr_type):

            transp_attrib = render_state.get_attrib(transp_attr_type)

            if render_state.has_attrib(color_scale_attr_type):
                color_scale_attrib = render_state.get_attrib(color_scale_attr_type)
                alpha_value = color_scale_attrib.get_scale()[3]
            else:
                alpha_value = 1.

            alpha_on = transp_attrib.get_mode() != TransparencyAttrib.M_none
            alpha = {"value": alpha_value, "on": alpha_on}
            material.set_property("alpha", alpha, apply_base_mat=False)

        if render_state.has_attrib(tex_attr_type):

            tex_attrib = render_state.get_attrib(tex_attr_type)
            colormap_stages = []
            layer_stages = []
            fxmap_stages = []
            off_stages = tex_attrib.get_off_stages()
            all_stages = off_stages + tex_attrib.get_on_stages()
            tex_xforms = {}

            if render_state.has_attrib(tex_matrix_attr_type):

                tex_matrix_attrib = render_state.get_attrib(tex_matrix_attr_type)

                for stage in tex_matrix_attrib.get_stages():
                    tex_xforms[stage] = tex_matrix_attrib.get_transform(stage)

            for stage in all_stages:

                mode = stage.get_mode()

                if mode == TS.M_modulate:
                    colormap_stages.append(stage)
                elif mode in FXMAP_TYPES:
                    fxmap_stages.append(stage)
                elif mode in BLEND_MODES:
                    layer_stages.append(stage)

                if mode == TS.M_combine and stage not in layer_stages:
                    layer_stages.append(stage)

            if not layer_stages and len(colormap_stages) == 1:

                stage = colormap_stages[0]
                uv_set_name = stage.get_texcoord_name()

                if uv_set_name != default_uv_set_name:
                    uv_set_names[uv_set_name] = default_uv_set_name

                texture = tex_attrib.get_on_texture(stage)

                if texture:
                    map_data = {}
                    map_data["map_type"] = "color"
                    rgb_filename = texture.get_fullpath().to_os_specific()
                    alpha_filename = texture.get_alpha_fullpath().to_os_specific()
                    map_data["rgb_filename"] = rgb_filename
                    map_data["alpha_filename"] = alpha_filename
                    material.set_texture(map_data)
                    tex_map = material.get_tex_map("color")
                    __set_texmap_properties(tex_map, texture, stage, tex_xforms)
                else:
                    material.set_map_active("color", is_active=False)

            elif colormap_stages:

                layer_stages.extend(colormap_stages)

            fxmap_ids = dict(zip(FXMAP_TYPES, FXMAP_IDS))

            for stage in fxmap_stages:

                texture = tex_attrib.get_on_texture(stage)

                if texture:
                    map_data = {}
                    map_type = fxmap_ids[stage.get_mode()]
                    map_data["map_type"] = map_type
                    rgb_filename = texture.get_fullpath().to_os_specific()
                    alpha_filename = texture.get_alpha_fullpath().to_os_specific()
                    map_data["rgb_filename"] = rgb_filename
                    map_data["alpha_filename"] = alpha_filename
                    material.set_texture(map_data)
                    material.set_map_active(map_type)
                    tex_map = material.get_tex_map(map_type)
                    __set_texmap_properties(tex_map, texture, stage, tex_xforms)

            if layer_stages:

                material.use_layers(True)
                stages_by_uv_set = {}

                for stage in layer_stages:
                    uv_set_name = stage.get_texcoord_name()
                    stages_by_uv_set.setdefault(uv_set_name, []).append(stage)

                # limit the number of texture coordinate sets to 8
                if len(stages_by_uv_set) > 8:

                    uv_sets_by_priority = []

                    for uv_set_name, stages in stages_by_uv_set.iteritems():
                        # check the highest priority of all texture stages
                        # that use a particular texture coordinate set
                        priority = max(stage.get_priority() for stage in stages)
                        uv_sets_by_priority.append((priority, uv_set_name))

                    uv_sets_by_priority.sort(reverse=True)
                    del uv_sets_by_priority[:8]

                    # low-priority texture stages that use the remaining texture
                    # coordinate sets will not be used
                    for priority, uv_set_name in uv_sets_by_priority:

                        for stage in stages_by_uv_set[uv_set_name]:
                            layer_stages.remove(stage)

                        del stages_by_uv_set[uv_set_name]

                # sort stages
                sorted_stages = sorted((stage.get_sort(), stage) for stage in layer_stages)
                layer_stages = [stage for sort, stage in sorted_stages]

                # give the stages consecutive sort values
                for i, stage in enumerate(layer_stages):
                    stage.set_sort(i)

                src_uv_set_names = set(stages_by_uv_set.iterkeys())
                dest_uv_set_names = set(uv_set_list[:len(stages_by_uv_set)])
                common = src_uv_set_names & dest_uv_set_names
                src_uv_set_names -= common
                dest_uv_set_names -= common
                uv_set_names = dict(zip(src_uv_set_names, dest_uv_set_names))

                stage = layer_stages.pop(0)
                layer = material.get_layer()
                name = stage.get_name()
                name = Mgr.get("unique_tex_layer_name", material, name, layer)
                layer.set_name(name)
                src_uv_name = stage.get_texcoord_name()
                uv_set_name = src_uv_name if src_uv_name in common else uv_set_names[src_uv_name]
                material.set_layer_uv_set_id(layer, uv_set_list.index(uv_set_name))
                __set_layer_properties(layer, stage, tex_attrib, off_stages, tex_xforms)

                for stage in layer_stages:
                    layer = Mgr.do("create_tex_layer", material)
                    name = stage.get_name()
                    name = Mgr.get("unique_tex_layer_name", material, name)
                    layer.set_name(name)
                    src_uv_name = stage.get_texcoord_name()
                    uv_set_name = src_uv_name if src_uv_name in common else uv_set_names[src_uv_name]
                    layer.set_uv_set_id(uv_set_list.index(uv_set_name))
                    __set_layer_properties(layer, stage, tex_attrib, off_stages, tex_xforms)
                    material.add_layer(layer)

        else:

            material.set_map_active("color", is_active=False)

    return material, uv_set_names
