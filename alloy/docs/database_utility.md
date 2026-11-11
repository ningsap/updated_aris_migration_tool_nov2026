# Database utility ([module link](/alloy/databases/))

This module connects to a given database and allows you to perform CRUD operations without worrying about what happens under the hood.
It's using [SQLAlchemy](https://www.sqlalchemy.org/) to manage database operations in an ORM manner. In case you are not familiar with general ORM-style database operations within Python please consider getting a basic understanding of it before using this module.

> See the [databases examples](/alloy/_EXAMPLES/DATABASES/DATABASES.py).

# Initialization  

> ⚠️ Before using the database, you will have to initialize the database schema. See the [Edit Schema](#edit-schema) section for more information.

1. First, you will have to import the factory class - the import statement is at the top of this file.
2. To create and/or connected to your database, initialize the factory class like this:

```python
from alloy.databases.database_utility_factory import DatabaseUtilityFactory

dbu = DatabaseUtilityFactory.get_database_utility(
    engine_type="sqlite",
    db_name="name_of_my_database"
)
```
There area few parameters that can make your life easier:

- `append_from_base: bool = False` Setting this to true, will try and append newly added tables and columns from the base class in SQLAlchemy. In other words, if you added something new to the database, setting this to true will update the schema of the connected database. ATTENTION: This does not work the other way around or for things that you deleted from the base models, i.e. deleting a column/table in the database itself or in the models is not considered here.
- `recreate_on_schema_change: bool = False` Rather for testing - Creates a new database and archives the old one if the schema changes between connections (works for SQLite since the database is a local file)
- `recreate_on_rerun: bool = False` Rather for testing - Creates a new database and archives the old one if the script is run again

3. This returns a DatabaseUtility object based on the engine type you provided. You can now use this object to perform CRUD operations on your database.

# Using CRUD Operations 

The DatabaseUtility object has the following methods: `create`, `read`, `update`, `delete` and they function as one would expect. Aside from the `read` function, all of them take a model object as an argument, i.e. an instance of the model class that you have defined. 

The `read` function takes a model class as an argument and returns a list of all objects of that class in the database. See the in-code documentation for more information about filters. Here are some basic examples:

### Create
```python
my_test_user = UserModel(name="John Doe", age=25)
    
dbu.create(my_test_user)
```
### Read
```python
10_users_male_age25_outside_berlin = dbu.read(
    UserModel,
    multiple=True,
    limit=10,
    filters={
        "age": 25,
        "sex": "male"
    },
    negative_filters={
        "city": "Berlin"
    }
)
```

### Update
```python
my_test_user.age = 26

dbu.update(my_test_user)
```

### Delete
```python
dbu.delete(my_test_user)
```

# Edit Schema

This is mostly native to SQLAlchemy, but here is a quick example of how you can add a new table/column:

1. Ensure that you import the declarative base from this module since there are some tables that are created by default

```python
from alloy.databases.models import Base
```
> ⚠️ The models you create MUST inherit from this base class ⚠️ 


2. It is advised to create a separate folder/file to create your model classes. This is to ensure that you can easily extend the module without having to change the base files. And it's a mess having model definitions in between your code. 

3. Create a new model class that inherits from the Base class following the SQLAlchemy ORM style. Here is an example:
```python
from sqlalchemy.orm import Mapped, mapped_column

from alloy.databases.models import Base

class Address(Base):
     __tablename__ = "address"

     id: Mapped[int] = mapped_column(primary_key=True)
     email_address: Mapped[str]
     ...
```


# Architecture

The module is built in a way that you can easily extend it to support other database engines. To do so, you will have to create a new class that inherits from the `DatabaseUtilityBase` class and implement the necessary mechanism to ensure the functionality of all arguments. 

The `DatabaseUtilityFactory` class will then have to be extended to support the new engine type.

Let's take the existing SQLite implementation as an example:

The setup is quite straight forward - the `DatabaseUtilityBase` class has everything that IS NOT specific to the database engine. It has all the CRUD operations as well as all supportive methods that are not specific to the database dialect. 
> For instance, we can check whether the schema is up to date or not with `schema_is_current`. However, we cannot append new tables or columns to the database schema, as this is specific to the SQLite engine and is done in `SQLiteUtility.append_missing_from_base`.

 The `SQLiteUtility` class inherits from `DatabaseUtilityBase` and implements the specific methods for SQLite. If you would like to extend this module to support another database engine, you would have to create a new class that inherits from `DatabaseUtilityBase` and implement the necessary methods.