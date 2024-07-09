class CaseInsensitiveDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._convert_keys()

    def __getitem__(self, key):
        return super().__getitem__(self._convert_key(key))

    def __setitem__(self, key, value):
        super().__setitem__(self._convert_key(key), value)

    def __delitem__(self, key):
        return super().__delitem__(self._convert_key(key))

    def __contains__(self, key):
        return super().__contains__(self._convert_key(key))

    def pop(self, key, default=None):
        return super().pop(self._convert_key(key), default)

    def get(self, key, default=None):
        return super().get(self._convert_key(key), default)

    def _convert_keys(self):
        for key in list(self.keys()):
            super().__setitem__(self._convert_key(key), super().pop(key))

    def _convert_key(self, key):
        return key.lower() if isinstance(key, str) else key

class ActionInput:
    def __init__(self, action_name, parameters=None):
        self._action_name = action_name
        if parameters is not None and not isinstance(parameters, dict):
            raise TypeError('parameters must be a dictionary')
        self._parameters = CaseInsensitiveDict(parameters) if parameters is not None else {}

    def to_dict(self):
        return {
            'action_name': self._action_name,
            'parameters': self._parameters
        }

    @property
    def action_name(self):
        return self._action_name

    @property
    def parameters(self):
        return self._parameters

    def action_input_to_dict(self):
        return {
            'action_name': self.action_name,
            'parameters': self.parameters
        }