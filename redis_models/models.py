import json
from uuid import uuid4, UUID

from redis import Redis

from redis_models.errors import NotFound, ValidationError


class RedisModelMeta(type):
    def __new__(cls, name, bases, namespace):
        new_type = type(name, bases, namespace)
        breakpoint()
        return new_type


class RedisModel(metaclass=RedisModelMeta):
    def __init_subclass__(cls) -> None:
        validators = cls.__annotations__
        setattr(cls, "_validators_", validators)

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            if name not in self._validators_:
                raise ValidationError(f"Invalid parameter '{name}'") from None
            setattr(self, name, value)
        self.id = None
        self.validate()

    def asdict(self):
        return {name: getattr(self, name) for name in self._validators_}

    def save(self):
        client = Redis.from_url(self.__class__.Meta.redis_url)
        id_part = self.id or uuid4().hex
        obj_id = f"{self.__class__.__name__}-{id_part}"
        data = self.asdict()
        raw_data = json.dumps(data)
        client.set(obj_id, raw_data)
        self.id = id_part

    @classmethod
    def get(cls, id):
        client = Redis.from_url(cls.Meta.redis_url)
        obj_id = f"{cls.__name__}-{id}"
        raw_data = client.get(obj_id)
        if raw_data is None:
            raise NotFound("This record does not exist")
        data = json.loads(raw_data.decode())
        obj = cls(**data)
        obj.id = id
        return obj

    def delete(self):
        obj_id = f"{self.__class__.__name__}-{self.id}"
        client = Redis.from_url(self.__class__.Meta.redis_url)
        client.delete(obj_id)

    def validate(self):
        for field_name, field_type in self._validators_.items():
            if field_name == "id":
                continue
            try:
                value = getattr(self, field_name)
            except AttributeError:
                raise ValidationError(
                    f"'{field_name}' is expected at the initialization."
                ) from None
            if not isinstance(value, field_type):
                raise ValidationError(
                    f"'{field_name}' must be a '{field_type.name}' instance."
                ) from None
