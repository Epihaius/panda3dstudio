from ..dialog import *


class NameField(DialogInputField):

    _ref_node = NodePath("reference_node")

    @classmethod
    def set_ref_node_pos(cls, pos):

        cls._ref_node.set_pos(pos)

    def __init__(self, parent, value_id, handler, connection_index):

        DialogInputField.__init__(self, parent, Skin.options["imp_dialog_field_min_width"])

        self.node.reparent_to(parent.widget_root_node)
        self.value_id = value_id
        self.value_type = "string"
        self.set_value_handler(handler)

        self._connection_index = connection_index

    def get_connection_index(self):

        return self._connection_index


class ObjectPane(DialogScrollPane):

    def __init__(self, parent, hierarchy, new_obj_names):

        options = Skin.options
        frame_client_size = (
            options["imp_dialog_scrollpane_width"],
            options["imp_dialog_scrollpane_height"]
        )

        DialogScrollPane.__init__(self, parent, "object_pane", "vertical", frame_client_size)

        self._hierarchy = hierarchy
        self._obj_names = new_obj_names
        self._old_name_texts = old_name_txts = []
        self._geom_type_texts = geom_type_txts = []
        self._fields = fields = []
        self._rect_sizers = rect_sizers = {}

        root_node = self.widget_root_node
        sizer = self.sizer
        get_name_parser = lambda index: lambda name: self.__parse_name(name, index)
        get_name_handler = lambda index: lambda *args: self.__handle_name(args[1], index)
        margin = options["inputfield_margin"]
        l, r, b, t = Skin.atlas.outer_borders["dialog_inset1"]
        l += margin

        obj_indices = hierarchy[0]["child_indices"][:]
        type_descriptions = {"regular": "Geometry:", "collision": "Coll. geom.:", "none": "Node:"}

        while obj_indices:
            index = obj_indices.pop()
            data = hierarchy[index]
            node_type = data["geom_type"]
            old_name = data["old_name"]
            new_name = data["new_name"]
            subsizer = Sizer("horizontal")
            borders = Skin.layout.borders["imp_dialog_hierarchy"]
            sizer.add(subsizer, proportions=(1., 0.), borders=borders)
            indent = options["imp_dialog_hierarchy_indent"] * (len(data["node_path"].nodes) - 2)
            subsizer.add((indent, 0))
            rect_sizer = Sizer("horizontal")
            rect_sizers[index] = rect_sizer
            subsizer.add(rect_sizer, proportions=(1., 0.))
            node_type_txt = DialogText(self, type_descriptions[node_type])
            node_type_txt.node.reparent_to(root_node)
            geom_type_txts.append(node_type_txt)
            borders = Skin.layout.borders["imp_dialog_node_type"]
            rect_sizer.add(node_type_txt, alignments=("min", "center"), borders=borders)
            name_sizer = Sizer("vertical")
            borders = Skin.layout.borders["imp_dialog_node_name"]
            rect_sizer.add(name_sizer, proportions=(1., 0.), borders=borders)
            old_name_txt = DialogText(self, old_name)
            old_name_txt.node.reparent_to(root_node)
            old_name_txts.append(old_name_txt)
            borders = (l, 0, 0, 0)
            name_sizer.add(old_name_txt, borders=borders)
            name_field = NameField(self, "name", get_name_handler(index), data["parent_index"])
            name_field.set_input_parser(get_name_parser(index))
            name_field.set_value(new_name)
            name_field.set_scissor_effect(self.scissor_effect)
            fields.append(name_field)
            borders = Skin.layout.borders["imp_dialog_node_field"]
            name_sizer.add(name_field, proportions=(1., 0.), borders=borders)
            obj_indices.extend(data["child_indices"])

    def _copy_widget_images(self, pane_image): 

        root_node = self.widget_root_node

        for texts in (self._geom_type_texts, self._old_name_texts):
            for txt in texts:
                x, y = txt.get_pos(ref_node=root_node)
                pane_image.blend_sub_image(txt.get_image(), x, y, 0, 0)

        painter = PNMPainter(pane_image)
        pen = PNMBrush.make_pixel(Skin.colors["import_dialog_lines"])
        fill = PNMBrush.make_transparent()
        painter.pen = pen
        painter.fill = fill

        for field in self._fields:

            x, y = field.get_pos(ref_node=root_node)
            offset_x, offset_y = field.image_offset
            pane_image.copy_sub_image(field.get_image(), x + offset_x, y + offset_y, 0, 0)

            subsizer = field.sizer_cell.sizer.owner
            x, y = subsizer.get_pos()
            w, h = subsizer.get_size()
            painter.draw_rectangle(x, y, x + w, y + h)

            index = field.get_connection_index()

            if index > 0:
                connected_rect_sizer = self._rect_sizers[index]
                x2, y2 = connected_rect_sizer.get_pos()
                w2, h2 = connected_rect_sizer.get_size()
                x1 = (x + x2) // 2
                y1 = y2 + h2
                y2 = y + h // 2
                painter.draw_line(x1, y1, x1, y2)
                painter.draw_line(x1, y2, x, y2)

    def destroy(self):

        DialogScrollPane.destroy(self)

        self._hierarchy = {}
        self._obj_names = []
        self._old_name_texts = []
        self._geom_type_texts = []
        self._fields = []
        self._rect_sizers = {}

    def __parse_name(self, new_name, index):

        name = self._hierarchy[index]["new_name"]
        obj_names = GD["obj_names"] + self._obj_names
        obj_names.remove(name)

        return get_unique_name(new_name.strip(), obj_names)

    def __handle_name(self, new_name, index):

        name = self._hierarchy[index]["new_name"]

        if new_name != name:
            self._hierarchy[index]["new_name"] = new_name
            self._obj_names.remove(name)
            self._obj_names.append(new_name)


class ImportDialog(Dialog):

    def __init__(self, hierarchy, new_obj_names):

        def on_yes():

            Mgr.update_remotely("import", "start")
            Mgr.update_app("unsaved_scene")

        def on_cancel():

            Mgr.update_remotely("import", "cancel")

        Dialog.__init__(self, "", "okcancel", "Import", on_yes, None, on_cancel)

        self._object_pane = pane = ObjectPane(self, hierarchy, new_obj_names)

        widgets = Skin.layout.create(self, "import")
        pane_cell = widgets["placeholders"]["pane"]
        checkbtn = widgets["checkbuttons"]["quadrangulate"]

        def handler(quadrangulate):

            hierarchy["quadrangulate"] = quadrangulate

        checkbtn.command = handler

        pane_cell.object = pane.frame

        self.finalize()

    def update_widget_positions(self):

        self._object_pane.update_quad_pos()
        x, y = self._object_pane.get_pos(net=True)
        NameField.set_ref_node_pos((-x, 0, y))
