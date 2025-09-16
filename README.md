# Redis Models

This package provides a simple model structure for redis based storage.
It acts like an ORM and allows you to create models with validation.


## Installation

```bash
pip install redis_models
```

## Usage

First, you need to create your model. It's similar to Pydantic models, or built-in dataclass.

```python
from redis_models.models import RedisModel


class MyUserModel(RedisModel):
    name: str
    age: int

    class Meta:
        redis_url = "redis://localhost:6379/0"
        indexes = ("name", )

```

Let's create a User object


```python
user = User(name="John Doe", age=30)
```

Let's try creating an object that does not fit to the definition

```python
try:
    bad_user = User(name="John", eye_color="blue")
except ValidationError:
    pass
```

Let's write it to Redis
```python
user.save()
```

Let's see its `id`. `id`s are UUID4 hex strings

```python
print(user.id)
```

Fetch the record from Redis

```python
user_again = User.get(id=user.id)
```

See the object as dictionary

```python
print(user.asdict())
```

Let's delete the record

```python
user_again.delete()
```

Trying to find a non-existing record throws NotFound exception

```python

from redis_models.errors import NotFound

try:
    user_not_found = User.get(id=user_again.id)
except NotFound:
    print("User not found!")

```

Trying to filter with exact values. 
In this example, `name` field is noted as an index in the model.

```python

User.filter(name="nejdet")
```

## How it works

This package relies on `RedisModelMeta` and `RedisModel` classes.
`RedisModelMeta` is a type constructor and `RedisModel` is a class that contains required methods for derived models.


When you call `YourModel.save()` the method will


- Run `YourModel.asdict()` and get the whole data serialized to JSON (Therefore each field must be JSON-serializable!)

- Create a key like `YourModel-data-<SOME_UUID>` and puts the whole serialized data as value

- Create an index set for each field you put in `YourModel.Meta.indexes` using `YourModel-index-<INDEX_FIELD_NAME>-<INDEX_FIELD_VALUE>` format and UUID for each record as a value.


When you call `YourModel.get(id=id_value)` the method will search among `YourModel-data-<SOME_UUID>` keys and return the data.

When you call `YourModel.filter(index1=value1, index2=value2)` the method will 

- Use `SINTER` to have an intersection for UUIDs. 
- Then uses `MGET` to get multiple values at once. 
- Returns a generator that yields `YourModel` objects (for memory efficiency).