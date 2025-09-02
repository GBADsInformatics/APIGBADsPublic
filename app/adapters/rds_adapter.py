import logging
from typing import Tuple
import psycopg as ps


logging.basicConfig(level=logging.INFO, format='%(levelname)s:\t%(name)s: %(message)s')
logger = logging.getLogger(__name__)


class RDSAdapter:
    """
    A class to interact with an RDS database using psycopg.
    This class provides methods to connect to the database and execute queries.
    """
    connection: ps.Connection = None

    def __init__(self, host: str, database: str, user: str, password: str):
        self.connection_string = f"host={host} dbname={database} user={user} password={password}"
        self.connect()

    def __enter__(self):
        if not self.connection:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def __repr__(self) -> str:
        return f"RDSAdapter({self.connection_string.split()[0]}, {self.connection_string.split()[1]})"

    def __str__(self) -> str:
        return f"RDSAdapter connected to {self.connection_string.split()[1]} at {self.connection_string.split()[0]}"

    def connect(self) -> None:
        """
        Establish a connection to the RDS database.
        """
        self.connection = ps.connect(self.connection_string)
        if not self.connection:
            raise ConnectionError("Failed to connect to the RDS database")
        logger.info("Connected to the RDS database successfully")

    def close(self) -> None:
        """
        Close the database connection.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

    def execute(self, query: str, params: tuple = ()) -> Tuple[list, list]:
        """
        Execute a SQL query and return the results.
        :param query: SQL query to execute
        :param params: Tuple of parameters for the query
        :return: List of results and column names
        """
        with self.connection.cursor() as cursor:
            try:
                cursor.execute(query, params)
            except ps.errors.UndefinedColumn as exc:
                self.connection.rollback()
                raise ValueError(f"Invalid field name: {exc}") from exc
            except ps.errors.UndefinedTable as exc:
                self.connection.rollback()
                raise ValueError(f"Invalid table name: {exc}") from exc
            except ps.errors.SyntaxError as exc:
                self.connection.rollback()
                raise ValueError(f"Syntax error in query: {exc}") from exc
            self.connection.commit()
            # Only fetch results if there is a result set
            if cursor.description is not None:
                data = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
            else:
                data = []
                column_names = []
            return data, column_names

    def insert(self, table: str, values: tuple) -> list:
        """
        Insert a row into the specified table.
        :param table: Name of the table to insert into
        :param values: Tuple of values to insert
        """
        placeholders = ', '.join(['%s'] * len(values))
        query = f"INSERT INTO {table} VALUES ({placeholders}) RETURNING *"
        data, _ = self.execute(query, values)
        logger.info("Inserted values %s into table %s", values, table)
        return data

    def list_tables(self) -> list:
        """
        List all tables in the connected database.
        :return: List of table names
        """
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"
        tables, _ = self.execute(query)
        logger.info("Listed %d tables.", len(tables))
        return tables

    def list_table_fields(self, table_name: str) -> list:
        """
        List all fields in the specified table.
        :param table_name: Name of the table to list fields from
        :return: List of field names and their data types
        """
        query = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s"
        fields, _ = self.execute(query, (table_name,))
        logger.info("Listed %d fields for table %s.", len(fields), table_name)
        return fields

    def select(
        self,
        table_name: str,
        fields: str = "*",
        where: str = "",
        join: str = "",
        order_by: str = "",
        count: bool = False,
        where_params: tuple = ()
    ) -> Tuple[list, list, str]:
        """
        Query the specified table with optional filtering, joining, and ordering.
        :param table_name: Name of the table to query (validated)
        :param fields: Comma-separated list of fields to select (validated)
        :param where: Optional WHERE clause (use %s for parameters)
        :param join: Optional JOIN clause (validated or whitelisted)
        :param order_by: Optional ORDER BY clause (validated or whitelisted)
        :param where_params: Tuple of parameters for the WHERE clause
        :return: List of query results, and the executed query string
        """
        allowed_tables = [t[0] for t in self.list_tables()]
        if table_name not in allowed_tables:
            raise ValueError("Invalid table name")

        if count:
            fields = "COUNT(*)"
        elif fields != "*" and not join:
            allowed_fields = [f[0] for f in self.list_table_fields(table_name)]
            for field in fields.split(","):
                if field.strip() not in allowed_fields:
                    raise ValueError(f"Invalid field name: {field}")

        query = f"SELECT {fields}"
        if not join.startswith("FROM "):
            query += f" FROM {table_name}"
        if join:
            query += f" {join}"
        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDER BY {order_by}"

        data, column_names = self.execute(query, where_params)
        return data, column_names, query

    def build_from_join_clause(self, table1: str, table2: str, field1: str, field2: str) -> str:
        """
        Build a FROM table JOIN clause for the query.
        :param table1: First table name
        :param table2: Second table name
        :param field1: Field from the first table to join on
        :param field2: Field from the second table to join on
        :return: JOIN clause string
        """
        return f"FROM {table1} INNER JOIN {table2} ON {table1}.{field1} = {table2}.{field2}"

    def delete(self, table: str, where: str, params: tuple = ()) -> int:
        """
        Delete rows from the specified table with a WHERE clause.
        :param table: Name of the table to delete from
        :param where: WHERE clause (e.g., "user_id = %s")
        :param params: Tuple of parameters for the WHERE clause
        :return: Number of rows deleted
        """
        query = f"DELETE FROM {table} WHERE {where}"
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            self.connection.commit()
            deleted_count = cursor.rowcount
        logger.info("Deleted %d rows from table %s where %s", deleted_count, table, where)
        return deleted_count
