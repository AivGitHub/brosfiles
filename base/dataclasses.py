from dataclasses import dataclass


@dataclass
class DataClassBase:
    """Base dataclass.

    All custom dataclasses should be inherited from this class.
    This class contains simple type validation.
    """
    def _validate(self):
        wrong_type_fields = []

        for name, field in self.__dataclass_fields__.items():
            actual_type = type(getattr(self, name))

            try:
                _types = field.type.__args__
            except AttributeError:
                _types = (field.type, )

            if actual_type not in _types:
                wrong_type_fields.append(name)

        if wrong_type_fields:
            raise ValueError('Wrong type; fields=%s' % ', '.join(wrong_type_fields))

        return True

    def __post_init__(self):
        self._validate()
