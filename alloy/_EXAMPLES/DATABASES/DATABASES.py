
from ARIS_Migration_Tool_SCB_Nov2026.alloy._EXAMPLES.DATABASES.MY_MODELS import MyCustomDBTable
from ARIS_Migration_Tool_SCB_Nov2026.alloy.databases.database_utility_factory import DatabaseUtilityFactory


def EXAMPLE_DATABASES():

    dbu = DatabaseUtilityFactory.get_database_utility(
        db_engine="sqlite",
        db_name="alloy",
    )

    my_custom_db_record: MyCustomDBTable = MyCustomDBTable(
        name="John",
        last_name="Doe",
    )

    another_custom_db_record: MyCustomDBTable = MyCustomDBTable(
        name="Jane",
        last_name="Doe",
    )

    dbu.create(my_custom_db_record)
    dbu.create(another_custom_db_record)

    retrieved_record = dbu.read(MyCustomDBTable, multiple=False, filters={"last_name": "Doe"}, negative_filters={"name": "Jane"})

    print(str(retrieved_record))


EXAMPLE_DATABASES()
