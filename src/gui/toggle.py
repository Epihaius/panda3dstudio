from .base import *
from .button import Button, ButtonGroup


class ToggleButtonGroup(ButtonGroup):

    def __init__(self):

        ButtonGroup.__init__(self)

        self._default_toggle_id = None
        self._toggle_id = ""

        self._activators = {"": lambda: None}
        self._deactivators = {"": lambda: None}

    def _toggle(self, toggle_id):

        if toggle_id == self._toggle_id:
            if self._default_toggle_id is not None:
                self._deactivators[toggle_id]()
                self._activators[self._default_toggle_id]()
                self._toggle_id = self._default_toggle_id
        else:
            self._deactivators[self._toggle_id]()
            self._activators[toggle_id]()
            self._toggle_id = toggle_id

    def set_default_toggle(self, toggle_id, toggle):

        self._default_toggle_id = self._toggle_id = toggle_id
        self._activators[toggle_id], self._deactivators[toggle_id] = toggle

    def add_button(self, parent, toggle_id, toggle, bitmaps, tooltip_text, label="",
                   do_before=None, do_after=None, parent_type="toolbar",
                   focus_receiver=None, pos=None):

        if do_before and do_after:

            def command():

                do_before()
                self._toggle(toggle_id)
                do_after()

        elif do_before:

            def command():

                do_before()
                self._toggle(toggle_id)

        elif do_after:

            def command():

                self._toggle(toggle_id)
                do_after()

        if do_before or do_after:
            button = Button(parent, bitmaps, label, tooltip_text, command,
                            parent_type, focus_receiver, pos)
        else:
            button = Button(parent, bitmaps, label, tooltip_text, lambda: self._toggle(toggle_id),
                            parent_type, focus_receiver, pos)

        self._btns[toggle_id] = button

        self._activators[toggle_id], self._deactivators[toggle_id] = toggle

        return button

    def deactivate(self):

        if self._default_toggle_id is None:
            default_toggle_id = ""
        else:
            default_toggle_id = self._default_toggle_id

        if self._toggle_id != default_toggle_id:
            self._btns[self._toggle_id].set_active(False)
            self._toggle_id = default_toggle_id

    def set_active_button(self, toggle_id):

        self.deactivate()
        self._btns[toggle_id].set_active()
        self._toggle_id = toggle_id

    def get_active_button_id(self):

        return self._toggle_id
