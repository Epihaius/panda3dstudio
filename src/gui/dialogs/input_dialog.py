from ..dialog import *


class InputDialog(Dialog):

    def __init__(self, title="", message="", default_input="", choices="okcancel",
                 ok_alias="OK", on_yes=None, on_no=None, on_cancel=None):

        def command():

            if on_yes:
                on_yes(self._input)

        Dialog.__init__(self, title, choices, ok_alias, command, on_no, on_cancel)

        widgets = Skin.layout.create(self, "input")
        text_cell = widgets["placeholders"]["text"]
        field = widgets["fields"]["input"]

        self._input = default_input

        text_cell.object = DialogText(self, message, text_type="dialog_message")

        field.value_id = "input"
        field.value_type = "string"
        field.set_on_key_enter(lambda: self.close(answer="yes"))
        field.set_on_key_escape(self.close)
        field.set_input_parser(self.__parse_input)

        self.finalize()

        field.set_text(default_input)
        field.on_left_down()
        field._on_left_up()

    def __parse_input(self, input_text):

        self._input = input_text.strip()

        return self._input
