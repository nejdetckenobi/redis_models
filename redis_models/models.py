import json
from uuid import uuid4, UUID

from redis import Redis

from redis_models.errors import NotFound, ValidationError


class RedisModelMeta(type):
    def __new__(cls, name, bases, namespace):
        new_type = type(name, bases, namespace)
        return new_type


class RedisModel(metaclass=RedisModelMeta):
    DATA_KEY_FORMAT = "{model_name}-data-{id}"
    INDEX_KEY_FORMAT = "{model_name}-index-{field_name}-{field_value}"

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
        index_fields = getattr(self.__class__.Meta, "indexes", ())
        id_part = self.id or uuid4().hex
        obj_id = self.DATA_KEY_FORMAT.format(
            model_name=self.__class__.__name__, id=id_part
        )
        data = self.asdict()
        raw_data = json.dumps(data)
        client.set(obj_id, raw_data)

        for index_name in index_fields:
            index_key = self.INDEX_KEY_FORMAT.format(
                model_name=self.__class__.__name__,
                field_name=index_name,
                field_value=data[index_name],
            )
            client.sadd(index_key, id_part)
        self.id = id_part

    @classmethod
    def get(cls, id):
        client = Redis.from_url(cls.Meta.redis_url)
        obj_id = cls.DATA_KEY_FORMAT.format(model_name=cls.__name__, id=id)
        raw_data = client.get(obj_id)
        if raw_data is None:
            raise NotFound("This record does not exist")
        data = json.loads(raw_data.decode())
        obj = cls(**data)
        obj.id = id
        return obj

    @classmethod
    def filter(cls, **filter_dict):
        client = Redis.from_url(cls.Meta.redis_url)
        filters = [
            cls.INDEX_KEY_FORMAT.format(
                model_name=cls.__name__,
                field_name=filter_name,
                field_value=filter_value,
            )
            for filter_name, filter_value in filter_dict.items()
        ]
        obj_id_parts = client.sinter(*filters)

        obj_ids = [
            cls.DATA_KEY_FORMAT.format(model_name=cls.__name__, id=obj_id_part.decode())
            for obj_id_part in obj_id_parts
        ]

        values = client.mget(obj_ids)
        for obj_id_part, raw_obj_data in zip(obj_id_parts, values):
            obj_data = json.loads(raw_obj_data)
            obj = cls(**obj_data)
            obj.id = obj_id_part.decode()
            yield obj

    def delete(self):
        obj_id = self.DATA_KEY_FORMAT.format(
            model_name=self.__class__.__name__, id=self.id
        )
        client = Redis.from_url(self.__class__.Meta.redis_url)
        client.delete(obj_id)
        index_fields = getattr(self.__class__.Meta, "indexes", ())
        index_keys = []
        for index in index_fields:
            index_key = self.INDEX_KEY_FORMAT.format(
                model_name=self.__class__.__name__,
                field_name=index,
                field_value=getattr(self, index),
            )
            index_keys.append(index_key)
        client.delete(*index_keys)

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
