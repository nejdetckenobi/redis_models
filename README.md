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
print(user.asd)
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