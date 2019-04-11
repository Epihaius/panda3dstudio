from direct.showbase.DirectObject import DirectObject
import logging
import re
import pickle

logging.basicConfig(filename='p3ds.log', filemode='w',
                    format='%(asctime)s - %(levelname)s: %(message)s',
                    datefmt='%Y/%m/%d %H:%M:%S', level=logging.DEBUG)


class GlobalMeta(type):

    def __init__(cls, name, bases, dic):

        type.__init__(cls, name, bases, dic)

        cls._defaults = {}
        cls._copiers = {}
        cls._data = {}

    def __getitem__(cls, data_id):
        """
        Get the current value of a certain global.
        This value is accessible from both the Core and the GUI.

        """

        if data_id in cls._data:
            return cls._data[data_id]

        raise KeyError('Global data ID "{}" not defined.'.format(data_id))

    def __setitem__(cls, data_id, value):
        """
        Set a certain global value.
        This can be done from *any* object in the Core or the GUI, while a value
        obtained through manager.get() can only be set by the object that initially
        exposed it.

        """

        cls._data[data_id] = value

        if data_id not in cls._defaults:
            cls._defaults[data_id] = value

    def __contains__(cls, data_id):

        return data_id in cls._data

    def set_default(cls, data_id, default_value, copier=None):

        cls._defaults[data_id] = default_value

        if copier:
            cls._copiers[data_id] = copier

        if data_id not in cls._data:
            cls._data[data_id] = copier(default_value) if copier else default_value

    def reset(cls, data_id=None):

        data = cls._data

        if data_id is None:
            for data_id, value in cls._defaults.items():
                copier = cls._copiers.get(data_id)
                data[data_id] = copier(value) if copier else value
        else:
            value = cls._defaults[data_id]
            copier = cls._copiers.get(data_id)
            data[data_id] = copier(value) if copier else value


# Global data - accessible from both the Core and the GUI - can be set and
# retrieved through the following class.
class GlobalData(object, metaclass=GlobalMeta):

    pass


# Using the following class to set the name of an object allows updating the
# application to pick up any changes made to the name wherever this name is used.
class ObjectName(object):

    def __init__(self, name):

        self._value = name
        self._updaters = {}

    def add_updater(self, update_id, updater):

        self._updaters[update_id] = updater

    def remove_updater(self, update_id, final_update=False):

        if update_id not in self._updaters:
            return

        if final_update:
            self._updaters[update_id](None)

        del self._updaters[update_id]

    def clear_updaters(self, final_update=False):

        updaters = self._updaters

        if final_update:
            for updater in updaters.values():
                updater(None)

        updaters.clear()

    def update(self, update_id=None):

        value = self._value
        updaters = self._updaters

        if update_id is None:
            for updater in updaters.values():
                updater(value)
        elif update_id in updaters:
            updaters[update_id](value)

    def get_value(self):

        return self._value

    def set_value(self, name, update=True, update_id=None):

        self._value = name

        if update:
            self.update(update_id)


def get_unique_name(requested_name, namelist, default_search_pattern="",
                    default_naming_pattern="", default_min_index=1):

    namestring = "\n".join(namelist)
    search_pattern = default_search_pattern
    naming_pattern = default_naming_pattern
    min_index = default_min_index

    if requested_name:

        pattern = r"(.*?)(\s*)(\d*)$"
        basename, space, index_str = re.search(pattern, requested_name).groups()

        if index_str:

            min_index = int(index_str)
            search_pattern = r"^{}\s*(\d+)$".format(re.escape(basename))
            zero_padding = len(index_str) if index_str.startswith("0") else 0
            naming_pattern = basename + space + "{:0" + str(zero_padding) + "d}"

        else:

            # also search for "(<index>)" at the end
            pattern = r"(.*?)(\s*)(?:\((\d*)\))*$"
            basename, space, index_str = re.search(pattern, requested_name).groups()

            if index_str:

                min_index = int(index_str)
                search_pattern = r"^{}\s*\((\d+)\)$".format(re.escape(basename))
                zero_padding = len(index_str) if index_str.startswith("0") else 0
                naming_pattern = basename + space + "({:0" + str(zero_padding) + "d})"

            else:

                search_pattern = r"^{}$".format(re.escape(basename))

                if re.findall(search_pattern, namestring, re.M):
                    min_index = 2
                    search_pattern = r"^{}\s*\((\d+)\)$".format(re.escape(basename))
                    naming_pattern = basename + " ({:d})"
                else:
                    return basename

    names = re.finditer(search_pattern, namestring, re.M)
    inds = [int(name.group(1)) for name in names]
    max_index = min_index + len(inds)

    for i in range(min_index, max_index):
        if i not in inds:
            return naming_pattern.format(i)

    return naming_pattern.format(max_index)


# The following class allows predefining specific bindings of events to their
# handlers.
# Multiple bindings can be set active at once, with the option to stop listening
# for all other events.
class EventBinder(object):

    def __init__(self, listener):

        self._listener = listener
        self._bindings = {}
        self._active_bindings = {}

    def bind(self, binding_id, event_props, handler, arg_list=None, once=False):
        """
        Predefine a specific binding of an event to a handler by id.
        The event in this binding can be set to be listened for later on by simply
        using this id instead of having to set the details of the binding every
        single time.

        """

        args = (arg_list,) if arg_list else ()
        self._bindings[binding_id] = (once, event_props, handler) + args

    def unbind(self, binding_id):
        """
        Remove the given binding.
        Note that, if the binding is currently active, this also stops the event in
        that binding being listened for!

        Returns True if successful or False if binding_id was not found.

        """

        if binding_id not in self._bindings:
            return False

        event_props = self._bindings[binding_id][1]
        del self._bindings[binding_id]

        if event_props in self._active_bindings:
            self.ignore(event_props)

        return True

    def accept(self, binding_ids, exclusive=False):
        """
        Listen for the events in the bindings whose ids are given.

        If "exclusive" is True, the events in all of the predefined bindings other
        than the ones given will be ignored.

        Returns True if successful or False if not all binding_ids were found.

        """

        if exclusive:
            self.ignore_all()

        binding_ids_found = True

        for binding_id in binding_ids:

            if binding_id not in self._bindings:
                binding_ids_found = False
                continue

            binding = self._bindings[binding_id]
            event_props = binding[1]
            self._active_bindings[event_props] = binding_id
            method = self._listener.accept_once if binding[0] else self._listener.accept
            method(*binding[1:])

        return binding_ids_found

    def ignore(self, *event_data):
        """
        Stop listening for the events whose ids are given.

        """

        for event_props in event_data:

            self._listener.ignore(event_props)

            if event_props in self._active_bindings:
                del self._active_bindings[event_props]

    def ignore_all(self):
        """
        Stop listening for all events.

        """

        self._listener.ignore_all()
        self._active_bindings = {}

    def get_active_bindings(self):
        """
        Return a list of the ids of the bindings of the events currently being
        listened for.

        """

        return list(self._active_bindings.values())


class StateObject(object):

    def __init__(self, state_id, persistence, on_enter=None, on_exit=None):

        self._id = state_id
        self._persistence = persistence
        self._enter_command = on_enter if on_enter else lambda prev_state_id, is_active: None
        self._exit_command = on_exit if on_exit else lambda next_state_id, is_active: None
        self._is_active = False
        self._prev_state = None

    def get_id(self):

        return self._id

    def get_persistence(self):

        return self._persistence

    def set_active(self, is_active=True):

        self._is_active = is_active

    def is_active(self):

        return self._is_active

    def set_enter_command(self, on_enter):

        self._enter_command = on_enter

    def set_exit_command(self, on_exit):

        self._exit_command = on_exit

    def set_previous_state(self, prev_state):

        while prev_state and prev_state.get_persistence() <= self._persistence:
            prev_state = prev_state.get_previous_state()

        self._prev_state = prev_state

    def get_previous_state(self):

        prev_state = self._prev_state

        while prev_state and not prev_state.is_active():
            prev_state = prev_state.get_previous_state()

        return prev_state

    def enter(self, prev_state_id):

        self._enter_command(prev_state_id, self._is_active)
        self._is_active = True

    def exit(self, next_state_id):

        self._exit_command(next_state_id, self._is_active)


# The following class manages the different states that the application
# can be in for a specific interface.
class StateManager(object):

    def __init__(self):

        self._states = {}
        self._default_state_id = ""
        self._current_state_id = ""
        self._is_state_binder = False
        self._changing_state = False

    def add_state(self, state_id, persistence, on_enter=None, on_exit=None):
        """
        Define a new state, optionally with commands to be called on entering and/or
        exiting that state.

        """

        self._states[state_id] = StateObject(state_id, persistence, on_enter, on_exit)

    def set_state_enter_command(self, state_id, on_enter):

        self._states[state_id].set_enter_command(on_enter)

    def set_state_exit_command(self, state_id, on_exit):

        self._states[state_id].set_exit_command(on_exit)

    def has_state(self, state_id):
        """ Check if the state with the given id has been previously defined """

        return state_id in self._states

    def is_state_binder(self):
        """ Check if this object is a StateBinder instance """

        return self._is_state_binder

    def set_default_state(self, state_id):
        """
        Set the default state for the interface this StateManager is associated with.

        Returns True if successful or False if the state with the given id has not
        been previously defined or is already the current state.
        Also returns False if a state change is already in progress.

        """

        if self._changing_state:
            return False

        if state_id not in self._states:
            return False

        current_state_id = self._current_state_id

        if state_id == current_state_id:
            return False

        self._changing_state = True
        state = self._states[state_id]
        state.enter(current_state_id)

        if self._is_state_binder:
            self._set_state_bindings(state_id)

        self._default_state_id = state_id
        self._current_state_id = state_id
        self._changing_state = False

        return True

    def enter_state(self, state_id):
        """
        Change from the current state to the one with the given id.

        Returns True if successful or False if the state with the given id has not
        been previously defined or is already the current state.
        Also returns False if a state change is already in progress.

        """

        if self._changing_state:
            return False

        if state_id not in self._states:
            return False

        current_state_id = self._current_state_id

        if state_id == current_state_id:
            return False

        self._changing_state = True
        current_state = self._states[current_state_id]
        state = self._states[state_id]
        state.set_previous_state(current_state)
        persistence = state.get_persistence()

        if current_state.get_persistence() <= persistence:
            current_state.set_active(False)

        current_state.exit(state_id)
        prev_state = current_state.get_previous_state()

        while prev_state and prev_state is not state and prev_state.get_persistence() <= persistence:
            prev_state.set_active(False)
            prev_state.exit(state_id)
            prev_state = prev_state.get_previous_state()

        state.enter(self._current_state_id)

        if self._is_state_binder:
            self._set_state_bindings(state_id)

        self._current_state_id = state_id
        self._changing_state = False

        return True

    def exit_state(self, state_id):
        """
        Exit the state with the given id. If it is not the current state, it will
        merely get deactivated (its exit command will still be called and it will
        be marked as inactive, but its previous state will not be restored).

        Returns True if successful or False if the state with the given id has not
        been previously defined, is inactive or is the default state.
        Also returns False if a state change is already in progress.

        """

        if self._changing_state:
            return False

        if state_id not in self._states:
            return False

        state = self._states[state_id]

        if not state.is_active():
            return False

        prev_state = state.get_previous_state()

        if not prev_state:
            # the default state has no previous state and thus cannot be exited
            return False

        self._changing_state = True
        current_state_id = self._current_state_id
        state.set_active(False)

        if state_id == current_state_id:

            prev_state_id = prev_state.get_id()
            state.exit(prev_state_id)
            prev_state.enter(state_id)

            if self._is_state_binder:
                self._set_state_bindings(prev_state_id)

            self._current_state_id = prev_state_id

        else:

            state.exit(current_state_id)

        self._changing_state = False

        return True

    def exit_states(self, min_persistence=None):
        """
        Exit all states with a persistence lower than or equal to min_persistence.
        If no persistence is specified, start by exiting the current state.
        Returns False if a state change is already in progress, True otherwise.

        """

        if self._changing_state:
            return False

        self._changing_state = True
        current_state_id = self._current_state_id
        default_state_id = self._default_state_id
        current_state = self._states[current_state_id]
        default_state = self._states[default_state_id]
        persistence = current_state.get_persistence() if min_persistence is None else min_persistence
        prev_state = current_state

        while prev_state and prev_state is not default_state:

            if prev_state.get_persistence() >= persistence:
                prev_state.set_active(False)
                prev_state.exit(default_state_id)

            prev_state = prev_state.get_previous_state()

        if current_state.get_persistence() >= persistence:

            default_state.enter(current_state_id)

            if self._is_state_binder:
                self._set_state_bindings(default_state_id)

            self._current_state_id = default_state_id

        self._changing_state = False

        return True

    def get_current_state_id(self):
        """ Return the id of the current state """

        return self._current_state_id

    def get_state_persistence(self, state_id):

        return self._states[state_id].get_persistence()

    def is_state_active(self, state_id):

        return self._states[state_id].is_active()


# The following class associates a particular state with a selection of event
# bindings.
class StateBinder(StateManager):

    def __init__(self, event_binder):

        StateManager.__init__(self)

        self._state_bindings = {}
        self._evt_binder = event_binder
        self._is_state_binder = True

    def add_state(self, state_id, persistence, on_enter=None, on_exit=None):
        """
        Define a new state, optionally with commands to be called on entering and/or
        exiting that state.

        """

        StateManager.add_state(self, state_id, persistence, on_enter, on_exit)

        self._state_bindings[state_id] = []

    def bind(self, state_id, binding_id, event_props, event_handler):
        """
        Define an event binding and associate it with a state.

        """

        self._evt_binder.bind(binding_id, event_props, event_handler)
        self._state_bindings[state_id].append(binding_id)

    def accept(self, binding_ids, exclusive=False):
        """
        Listen for the events in the bindings whose ids are given.

        If "exclusive" is True, the events in all of the predefined bindings other
        than the ones given will be ignored.

        Returns True if successful or False if not all binding_ids were found.

        """

        return self._evt_binder.accept(binding_ids, exclusive)

    def _set_state_bindings(self, state_id):
        """
        Change from the current state to the one with the given id.

        """

        self._evt_binder.accept(self._state_bindings[state_id], exclusive=True)

    def get_event_binder(self):
        """ Get the event binder used by this StateBinder """

        return self._evt_binder
