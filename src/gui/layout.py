from .base import *
from .toolbar import *
from .panel import *
from .dialog import *
import os
import sys


class Layout:

    path = os.path.join("skins", "default", "layout")
    count = 0
    ids = {"toolbar": {}, "panel": {}, "dialog": {}}
    data = {}
    sizers = {}
    toolbars = {}  # the arrangement of the toolbars themselves
    control_panels = {}
    borders = {}

    @classmethod
    def load_data(cls, container_type, container_id):

        layout_data = []
        container_data = {"type": container_type, "id": container_id}
        layout_data.append(container_data)
        default_size = (0, 0)
        radiobtngrp_data = None
        read_borders = False
        read_options = False
        skin_options = {}

        def typecast(string, data_type):

            if data_type == "string":
                return string
            if data_type == "float":
                return float(string)
            if data_type == "int":
                return int(string)
            if data_type == "bool":
                return bool(int(string))

        with open(os.path.join(cls.path, f"{container_type}__{container_id}.txt")) as data_file:

            for line in data_file:

                if line.startswith("#"):
                    continue
                elif line.startswith("BORDERS"):
                    read_borders = True
                    read_options = False
                    continue
                elif line.startswith("OPTIONS"):
                    read_borders = False
                    read_options = True
                    continue
                elif line.startswith("name"):
                    name = [x.strip() for x in line.split("=")][1]
                    container_data["name"] = name
                    continue
                elif line.startswith("title"):
                    title = [x.strip() for x in line.split("=")][1]
                    container_data["title"] = title
                    continue
                elif line.startswith("default_size"):
                    default_size = [x.strip() for x in line.split("=")][1]
                    default_size = tuple(int(x) for x in default_size.split())
                    continue
                elif not (read_borders or read_options or line.startswith(" ")):
                    obj_data = {}
                    layout_data.append(obj_data)
                    obj_data["type"], obj_data["id"] = [x.strip() for x in line.split()]
                    if obj_data["type"] == "radiobuttongroup":
                        obj_data["btns"] = []
                        radiobtngrp_data = obj_data
                    elif obj_data["type"] == "radiobutton":
                        radiobtngrp_data["btns"].append(obj_data)
                    continue

                if read_borders:
                    obj_id, l, r, b, t = line.split()
                    cls.borders[obj_id] = (int(l), int(r), int(b), int(t))
                elif read_options:
                    option, data_type, value = line.split()
                    skin_options[option] = typecast(value, data_type)
                else:
                    key, value = [x.strip() for x in line.split("=", 1)]
                    obj_data[key] = value

        container_layout_id = cls.count
        cls.count += 1
        cls.ids[container_type][container_id] = container_layout_id
        data = cls.data
        data[container_layout_id] = container_data

        layout_id = cls.count
        cls.count += 1
        container_data["sizer_layout_id"] = layout_id
        data[layout_id] = {
            "container": container_layout_id,
            "type": "sizer",
            "id": layout_id,
            "layout_id": layout_id,
            "prim_dir": "vertical",
            "prim_limit": 0,
            "gaps": (0, 0),
            "row_proportions": {},
            "column_proportions": {},
            "default_size": default_size,
            "obj_ids": []
        }

        def parse_text(text):

            text = text.replace("\\|", chr(13))
            text = text.replace("|", "\n")
            text = text.replace(chr(13), "|")

            text = text.replace("\\*", chr(13))
            text = text.replace("*", "\u2022")
            text = text.replace(chr(13), "*")

            return text

        def parse_placement_data(obj_data):

            obj_data["proportions"] = tuple(float(x) for x in obj_data["proportions"].split())
            obj_data["alignments"] = tuple(obj_data["alignments"].split())
            obj_data["borders"] = tuple(int(x) for x in obj_data["borders"].split())

        new_sizer_ids = {container_type: container_layout_id}

        for obj_data in layout_data[1:]:

            layout_id = cls.count
            cls.count += 1
            data[layout_id] = obj_data
            obj_data["layout_id"] = layout_id
            obj_type = obj_data["type"]

            if obj_type in ("panel_container", "panel_section", "group"):

                layout_id = cls.count
                cls.count += 1
                default_size = tuple(int(x) for x in obj_data["default_size"].split())
                del obj_data["default_size"]
                data[layout_id] = {
                    "container": obj_data["layout_id"],
                    "type": "sizer",
                    "id": layout_id,
                    "layout_id": layout_id,
                    "prim_dir": "vertical",
                    "prim_limit": 0,
                    "gaps": (0, 0),
                    "row_proportions": {},
                    "column_proportions": {},
                    "default_size": default_size,
                    "obj_ids": []
                }
                obj_data["sizer_layout_id"] = layout_id

                if obj_type == "panel_section":
                    obj_data["hidden"] = bool(int(obj_data["hidden"]))

            if obj_type in ("sizer", "group"):
                obj_id = obj_data["id"]
                layout_id = obj_data["layout_id"]
                obj_data["id"] = layout_id
                old_sizer_id = f"{obj_type} {obj_id}"
                new_sizer_ids[old_sizer_id] = layout_id

            obj_id = obj_data["id"]

            if obj_type == "sizer":
                obj_data["obj_ids"] = []
                obj_data["prim_limit"] = int(obj_data["prim_limit"])
                obj_data["gaps"] = tuple(int(g) for g in obj_data["gaps"].split())
                obj_data["row_proportions"] = {int(i): float(p) for i, p in
                    (ip.split(":") for ip in obj_data["row_proportions"].split())}
                obj_data["column_proportions"] = {int(i): float(p) for i, p in
                    (ip.split(":") for ip in obj_data["column_proportions"].split())}
                obj_data["default_size"] = tuple(int(x) for x in obj_data["default_size"].split())
            elif obj_type == "space":
                obj_data["size"] = tuple(int(x) for x in obj_data["size"].split())
            elif obj_type == "text":
                obj_data["text"] = parse_text(obj_data["text"])
            elif obj_type == "checkbutton":
                obj_data["text_offset"] = int(obj_data["text_offset"])
                obj_data["text"] = parse_text(obj_data["text"])
            elif obj_type == "combobox":
                obj_data["field_width"] = int(obj_data["field_width"])
            elif obj_type == "radiobuttongroup":
                obj_data["prim_limit"] = int(obj_data["prim_limit"])
                obj_data["gaps"] = tuple(int(g) for g in obj_data["gaps"].split())
                obj_data["text_offset"] = int(obj_data["text_offset"])
                obj_data["expand"] = bool(int(obj_data["expand"]))
            elif obj_type == "field":
                obj_data["width"] = int(obj_data["width"])
            elif obj_type == "placeholder":
                obj_data["size"] = tuple(int(x) for x in obj_data["size"].split())

            if obj_type == "panel_container":
                old_sizer_id = f"panel_container {obj_id}"
                new_sizer_ids[old_sizer_id] = obj_data["layout_id"]
                sizer_data = data[container_data["sizer_layout_id"]]
                sizer_data["obj_ids"].append(obj_data["layout_id"])
            elif obj_type == "panel_section":
                old_sizer_id = f"panel_section {obj_id}"
                new_sizer_ids[old_sizer_id] = obj_data["layout_id"]
                sizer_data = data[container_data["sizer_layout_id"]]
                sizer_data["obj_ids"].append(obj_data["layout_id"])
            elif obj_type != "radiobutton":
                parse_placement_data(obj_data)
                if obj_data["container"] in new_sizer_ids:
                    obj_data["container"] = new_sizer_ids[obj_data["container"]]
                sizer_data = cls.__get_containing_sizer_data(obj_data["container"])
                sizer_data["obj_ids"].append(obj_data["layout_id"])

        return skin_options

    @classmethod
    def __get_containing_sizer_data(cls, layout_id):

        obj_data = cls.data[layout_id]

        if obj_data["type"] == "sizer":
            return obj_data
        else:
            return cls.data[obj_data["sizer_layout_id"]]

    @classmethod
    def __add_layout_data(cls, layout_data, obj_ids):

        data = cls.data

        for layout_id in obj_ids:

            obj_data = data[layout_id]
            layout_data.append(obj_data)

            if "obj_ids" in obj_data:
                cls.__add_layout_data(layout_data, obj_data["obj_ids"])
            elif "sizer_layout_id" in obj_data:
                sizer_data = data[obj_data["sizer_layout_id"]]
                cls.__add_layout_data(layout_data, sizer_data["obj_ids"])

    @classmethod
    def create(cls, container_widget, container_id, text_vars=None, component_ids=None):

        def parse_text(text, text_vars):

            if "{" in text:
                for key, value in text_vars.items():
                    s = f"{{{key}}}"
                    if s in text:
                        text = text.replace(s, value)

            return text

        def add_to_sizer(sizer, obj, obj_data):

            proportions = obj_data["proportions"]
            alignments = obj_data["alignments"]
            borders = obj_data["borders"]

            return sizer.add(obj, proportions, alignments, borders)

        btns = {}
        checkbtns = {}
        radiobtn_grps = {}
        comboboxes = {}
        colorboxes = {}
        fields = {}
        placeholders = {}
        simple_widgets = {}
        widgets = {
            "buttons": btns,
            "checkbuttons": checkbtns,
            "radiobutton_groups": radiobtn_grps,
            "comboboxes": comboboxes,
            "colorboxes": colorboxes,
            "fields": fields,
            "placeholders": placeholders,
            "simple_widgets": simple_widgets
        }

        container_type = container_widget.widget_type
        layout_id = cls.ids[container_type][container_id]
        data = cls.data
        container_data = data[layout_id]

        txt_vars = {} if text_vars is None else text_vars

        if container_type == "toolbar":
            container_widget.name = parse_text(container_data["title"], txt_vars)
        elif container_type == "panel":
            container_widget.set_title(parse_text(container_data["title"], txt_vars))
        elif container_type == "dialog":
            if container_data["title"] != "-":
                container_widget.set_title(parse_text(container_data["title"], txt_vars))

        if container_type == "toolbar":
            container_widget.update_grip_tooltip_label()

        client_sizer = container_widget.client_sizer
        sizer_layout_id = container_data["sizer_layout_id"]
        sizer_data = data[sizer_layout_id]
        client_sizer.default_size = sizer_data["default_size"]
        sizers = cls.sizers
        sizers[layout_id] = client_sizer
        layout_data = []
        cls.__add_layout_data(layout_data, sizer_data["obj_ids"])
        txt_classes = {
            "toolbar": ToolbarText,
            "panel": PanelText,
            "dialog": DialogText
        }
        colorbox_classes = {
            "toolbar": ToolbarColorBox,
            "panel": PanelColorBox,
        }
        btn_classes = {
            "toolbar": ToolbarButton,
            "panel": PanelButton,
            "dialog": DialogButton
        }
        checkbtn_classes = {
            "toolbar": ToolbarCheckButton,
            "panel": PanelCheckButton,
            "dialog": DialogCheckButton
        }
        combobox_classes = {
            "toolbar": ToolbarComboBox,
            "panel": PanelComboBox,
            "dialog": DialogComboBox
        }
        fld_classes = {
            "toolbar": {
                "input" : ToolbarInputField,
                "multival" : ToolbarMultiValField,
                "spinner" : ToolbarSpinnerField,
                "slider" : ToolbarSliderField
            },
            "panel": {
                "input" : PanelInputField,
                "spinner" : PanelSpinnerField,
                "slider" : PanelSliderField
            },
            "dialog": {
                "input" : DialogInputField,
                "spinner" : DialogSpinnerField,
                "slider" : DialogSliderField
            }
        }
        simple_widget_classes = {
            "toolbar_separator": ToolbarSeparator,
            "gridspacing_box": GridSpacingBox,
            "basic_color_swatches": BasicColorGroup,
            "custom_color_swatches": CustomColorGroup,
            "hue_sat_control": HueSatControl,
            "lum_control": LuminanceControl,
            "new_swatch": NewColorSwatch,
            "current_swatch": CurrentColorSwatch
        }

        comp_ids = [None] if component_ids is None else component_ids + [None]

        for obj_data in layout_data:

            if obj_data.get("component_id") not in comp_ids:
                continue

            if "container" in obj_data and obj_data["container"] not in sizers:
                continue

            obj_type = obj_data["type"]
            obj_id = obj_data["id"]

            if obj_type == "panel_container":
                widget = container_widget.create_container(obj_id)
                sizer_layout_id = obj_data["sizer_layout_id"]
                w_d, h_d = data[sizer_layout_id]["default_size"]
                w_gfx, h_gfx = widget.gfx_size
                widget.sizer.default_size = (max(w_gfx, w_d), max(h_gfx, h_d))
                sizers[obj_data["layout_id"]] = widget.sizer
            elif obj_type == "panel_section":
                title = parse_text(obj_data["title"], txt_vars)
                widget = container_widget.add_section(obj_id, title, obj_data["hidden"])
                sizer_layout_id = obj_data["sizer_layout_id"]
                widget.client_sizer.default_size = data[sizer_layout_id]["default_size"]
                sizers[obj_data["layout_id"]] = widget.client_sizer
            elif obj_type == "group":
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                widget_class = PanelWidgetGroup if container_type == "panel" else DialogWidgetGroup
                title = parse_text(obj_data["title"], txt_vars)
                widget = widget_class(parent, title)
                sizer_layout_id = obj_data["sizer_layout_id"]
                widget.client_sizer.default_size = data[sizer_layout_id]["default_size"]
                sizers[obj_data["layout_id"]] = widget.client_sizer
                add_to_sizer(sizer, widget, obj_data)
            elif obj_type == "sizer":
                prim_dir = obj_data["prim_dir"]
                prim_limit = obj_data["prim_limit"]
                sizer = Sizer(prim_dir, prim_limit, obj_data["gaps"])
                for i, p in obj_data["row_proportions"].items():
                    sizer.set_row_proportion(i, p)
                for i, p in obj_data["column_proportions"].items():
                    sizer.set_column_proportion(i, p)
                sizer.default_size = obj_data["default_size"]
                sizers[obj_data["layout_id"]] = sizer
                owner = sizers[obj_data["container"]]
                add_to_sizer(owner, sizer, obj_data)
            elif obj_type == "space":
                sizer = sizers[obj_data["container"]]
                add_to_sizer(sizer, obj_data["size"], obj_data)
            elif obj_type in simple_widget_classes:
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                widget = simple_widget_classes[obj_type](parent)
                add_to_sizer(sizer, widget, obj_data)
                simple_widgets[obj_type] = widget
            elif obj_type == "text":
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                text = parse_text(obj_data["text"], txt_vars)
                widget_class = txt_classes[container_type]
                if container_type == "dialog":
                    text_type = obj_data.get("text_type", "dialog")
                    widget = widget_class(parent, text, text_type)
                else:
                    widget = widget_class(parent, text)
                add_to_sizer(sizer, widget, obj_data)
            elif obj_type == "colorbox":
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                widget_class = colorbox_classes[container_type]
                widget = widget_class(parent)
                add_to_sizer(sizer, widget, obj_data)
                colorboxes[obj_id] = widget
            elif obj_type == "button":
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                widget_class = btn_classes[container_type]
                text = parse_text(obj_data["text"], txt_vars)
                tooltip_text = parse_text(obj_data["tooltip_text"], txt_vars)
                widget = widget_class(parent, text, obj_data["icon_id"], tooltip_text)
                add_to_sizer(sizer, widget, obj_data)
                btns[obj_id] = widget
            elif obj_type == "toolbutton":
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                text = parse_text(obj_data["text"], txt_vars)
                tooltip_text = parse_text(obj_data["tooltip_text"], txt_vars)
                widget = DialogToolButton(parent, text, obj_data["icon_id"], tooltip_text)
                add_to_sizer(sizer, widget, obj_data)
                btns[obj_id] = widget
            elif obj_type == "dropdown_button":
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                text = parse_text(obj_data["text"], txt_vars)
                tooltip_text = parse_text(obj_data["tooltip_text"], txt_vars)
                widget = DialogDropdownButton(parent, text, obj_data["icon_id"], tooltip_text)
                add_to_sizer(sizer, widget, obj_data)
                btns[obj_id] = widget
            elif obj_type == "checkbutton":
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                widget_class = checkbtn_classes[container_type]
                text = parse_text(obj_data["text"], txt_vars)
                widget = widget_class(parent, text, obj_data["text_offset"])
                add_to_sizer(sizer, widget, obj_data)
                checkbtns[obj_id] = widget
            elif obj_type == "radiobuttongroup":
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                widget_class = (PanelRadioButtonGroup if container_type == "panel"
                    else DialogRadioButtonGroup)
                grp = widget_class(parent, obj_data["prim_dir"], obj_data["prim_limit"],
                    obj_data["gaps"], obj_data["expand"], obj_data["text_offset"])
                add_to_sizer(sizer, grp.sizer, obj_data)
                for btn_data in obj_data["btns"]:
                    if btn_data.get("component_id") not in comp_ids:
                        continue
                    text = parse_text(btn_data["text"], txt_vars)
                    btn = grp.add_button(btn_data["id"], text)
                radiobtn_grps[obj_id] = grp
            elif obj_type == "combobox":
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                widget_class = combobox_classes[container_type]
                text = parse_text(obj_data["text"], txt_vars)
                widget = widget_class(parent, obj_data["field_width"], text,
                    obj_data["icon_id"], obj_data["tooltip_text"])
                add_to_sizer(sizer, widget, obj_data)
                comboboxes[obj_id] = widget
            elif obj_type == "field":
                sizer = sizers[obj_data["container"]]
                parent = sizer.owner_widget
                is_multival = "multival" in obj_data["field_type"]
                has_spinner = "spinner" in obj_data["field_type"]
                has_slider = "slider" in obj_data["field_type"]
                field_type = "multival" if is_multival else ("spinner" if has_spinner
                    else ("slider" if has_slider else "input"))
                widget_class = fld_classes[container_type][field_type]
                if has_spinner:
                    widget = widget_class(parent, obj_data["width"], has_slider=has_slider)
                else:
                    widget = widget_class(parent, obj_data["width"])
                add_to_sizer(sizer, widget, obj_data)
                fields[obj_id] = widget
            elif obj_type == "placeholder":
                sizer = sizers[obj_data["container"]]
                space = obj_data["size"]
                placeholders[obj_id] = add_to_sizer(sizer, space, obj_data)

        sizers.clear()

        return widgets

    @classmethod
    def __load_toolbar_layout(cls, interface_id):

        path = os.path.join(cls.path, f"toolbars__{interface_id}.txt")

        if not os.path.exists(path):
            Notifiers.gui.info(f'(error): "{interface_id}" toolbar layout not found!')
            raise RuntimeError(f'Failed to load "{interface_id}" toolbar layout!')

        cls.toolbars[interface_id] = toolbar_layout = {}
        toolbar_layout["top"] = [None]
        toolbar_layout["bottom"] = []

        with open(path) as data_file:

            for line in data_file:

                if line.startswith("#"):
                    continue
                elif line.startswith("    bundle"):
                    bundle = []
                    toolbars.append(bundle)
                    continue
                elif not line.startswith(" "):
                    alignment = line.strip()
                    toolbars = toolbar_layout[alignment]
                    continue

                row = [x.strip() for x in line.split()]
                bundle.append(row)

        toolbar_layout["bottom"].append(None)

    @classmethod
    def __load_control_pane_layout(cls, interface_id):

        path = os.path.join(cls.path, f"control_pane__{interface_id}.txt")

        if not os.path.exists(path):
            Notifiers.gui.info(f'(error): "{interface_id}" control pane layout not found!')
            raise RuntimeError(f'Failed to load "{interface_id}" control pane layout!')

        with open(path) as data_file:

            cls.control_panels[interface_id] = panel_ids = []

            for line in data_file:

                if line.startswith("#"):
                    continue

                panel_ids.append(line.strip())

    @classmethod
    def load(cls):

        config_data = GD["config"]
        skin_id = config_data["skin"]
        path = os.path.join("skins", skin_id, "layout")

        if not os.path.exists(path):
            if skin_id == "default":
                Notifiers.gui.info('(error): default layout directory not found!')
                raise RuntimeError('Failed to load default layout!')
            else:
                path = os.path.join("skins", "default", "layout")
                if not os.path.exists(path):
                    Notifiers.gui.info('(error): default layout directory not found!')
                    raise RuntimeError('Failed to load default layout!')
                else:
                    Notifiers.gui.warning(f'Skin "{skin_id}" layout not found!'
                        ' Loading default skin layout.')

        cls.path = path
        skin_options = {}

        for interface_id in ("main", "uv"):
            cls.__load_toolbar_layout(interface_id)
            cls.__load_control_pane_layout(interface_id)

        for toolbar_layout in cls.toolbars.values():

            for alignment, toolbar_id_lists in toolbar_layout.items():

                for toolbar_id_list in toolbar_id_lists:

                    if toolbar_id_list is None:
                        continue

                    for toolbar_ids in toolbar_id_list:
                        for toolbar_id in toolbar_ids:
                            cls.load_data("toolbar", toolbar_id)

        panel_ids = set(p_id for p_ids in cls.control_panels.values() for p_id in p_ids)

        for panel_id in panel_ids:
            skin_options.update(cls.load_data("panel", panel_id))

        for name in (os.path.splitext(name)[0] for name in os.listdir(path)):
            if name.startswith("dialog__"):
                container_id = name.replace("dialog__", "")
                skin_options.update(cls.load_data("dialog", container_id))

        return skin_options
