from ..base import *
from ..dialog import *


class NameField(DialogInputField):

    _field_borders = ()
    _img_offset = (0, 0)
    _ref_node = NodePath("reference_node")

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset1"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def set_ref_node_pos(cls, pos):

        cls._ref_node.set_pos(pos)

    def __init__(self, parent, width, connection_index):

        if not self._field_borders:
            self.__set_field_borders()

        DialogInputField.__init__(self, parent, INSET1_BORDER_GFX_DATA, width)

        self.set_image_offset(self._img_offset)
        self.get_node().reparent_to(parent.get_widget_root_node())

        self._connection_index = connection_index

    def get_outer_borders(self):

        return self._field_borders

    def get_connection_index(self):

        return self._connection_index


class ObjectPane(DialogScrollPane):

    def __init__(self, dialog, hierarchy, new_obj_names):

        DialogScrollPane.__init__(self, dialog, "object_pane", "vertical", (700, 300), "both")

        self._hierarchy = hierarchy
        self._obj_names = new_obj_names
        self._old_name_texts = old_name_txts = []
        self._geom_type_texts = geom_type_txts = []
        self._fields = fields = []
        self._rect_sizers = rect_sizers = {}

        root_node = self.get_widget_root_node()
        sizer = self.get_sizer()
        get_name_parser = lambda index: lambda name: self.__parse_name(name, index)
        get_name_handler = lambda index: lambda val_id, value: self.__handle_name(value, index)
        margin = Skin["options"]["inputfield_margin"]
        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset1"]
        l += margin

        obj_indices = hierarchy[0]["child_indices"][:]
        type_descriptions = {"regular": "Geometry:", "collision": "Coll. geom.:", "none": "Node:"}

        while obj_indices:
            index = obj_indices.pop()
            data = hierarchy[index]
            geom_type = data["geom_type"]
            old_name = data["old_name"]
            new_name = data["new_name"]
            subsizer = Sizer("horizontal")
            borders = (10, 10, 10, 10)
            sizer.add(subsizer, expand=True, borders=borders)
            indent = 50 * (data["node_path"].get_num_nodes() - 2)
            subsizer.add((indent, 0))
            rect_sizer = Sizer("horizontal")
            rect_sizers[index] = rect_sizer
            subsizer.add(rect_sizer, proportion=1.)
            geom_type_txt = DialogText(self, type_descriptions[geom_type])
            geom_type_txt.get_node().reparent_to(root_node)
            geom_type_txts.append(geom_type_txt)
            borders = (10, 0, 0, 0)
            rect_sizer.add(geom_type_txt, alignment="center_v", borders=borders)
            name_sizer = Sizer("vertical")
            borders = (10, 10, 2, 10)
            rect_sizer.add(name_sizer, proportion=1., borders=borders)
            old_name_txt = DialogText(self, old_name)
            old_name_txt.get_node().reparent_to(root_node)
            old_name_txts.append(old_name_txt)
            borders = (l, 0, 0, 0)
            name_sizer.add(old_name_txt, borders=borders)
            name_field = NameField(self, 100, data["parent_index"])
            name_field.add_value("name", "string", handler=get_name_handler(index))
            name_field.set_input_parser("name", get_name_parser(index))
            name_field.show_value("name")
            name_field.set_value("name", new_name, handle_value=False)
            name_field.set_scissor_effect(self.get_scissor_effect())
            fields.append(name_field)
            borders = (0, 0, 0, 2)
            name_sizer.add(name_field, expand=True, borders=borders)
            obj_indices.extend(data["child_indices"])

    def _copy_widget_images(self, pane_image): 

        root_node = self.get_widget_root_node()

        for texts in (self._geom_type_texts, self._old_name_texts):
            for txt in texts:
                x, y = txt.get_pos(ref_node=root_node)
                pane_image.blend_sub_image(txt.get_image(), x, y, 0, 0)

        painter = PNMPainter(pane_image)
        pen = PNMBrush.make_pixel((0., 0., 0., 1.))
        fill = PNMBrush.make_transparent()
        painter.set_pen(pen)
        painter.set_fill(fill)

        for field in self._fields:

            x, y = field.get_pos(ref_node=root_node)
            offset_x, offset_y = field.get_image_offset()
            pane_image.copy_sub_image(field.get_image(), x + offset_x, y + offset_y, 0, 0)

            subsizer = field.get_sizer_item().get_sizer().get_owner()
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
        obj_names = GlobalData["obj_names"] + self._obj_names
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

        title = "Import options"
        choices = "okcancel"
        ok_alias = "Import"

        Dialog.__init__(self, None, title, choices, ok_alias, on_yes, None, on_cancel)

        client_sizer = self.get_client_sizer()

        info = 'Displayed below is the following object info, found in the chosen file:'
        info += u'\n    \u2022 the type of object (regular geometry, collision geometry or a node of some other kind);'
        info += u'\n    \u2022 the original name of the object ("<Unnamed>" if no name was found);'
        info += u'\n    \u2022 the unique name the object will have in the scene (editable);'
        info += u'\n    \u2022 the object hierarchy.'
        text = DialogText(self, info)
        borders = (50, 50, 20, 20)
        client_sizer.add(text, borders=borders)

        self._object_pane = pane = ObjectPane(self, hierarchy, new_obj_names)
        frame = pane.get_frame()
        borders = (50, 50, 20, 0)
        client_sizer.add(frame, proportion=1., expand=True, borders=borders)

        self.finalize()

    def update_widget_positions(self):

        self._object_pane.update_quad_pos()
        x, y = self._object_pane.get_pos(from_root=True)
        NameField.set_ref_node_pos((-x, 0, y))
