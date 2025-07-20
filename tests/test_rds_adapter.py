from unittest.mock import patch, MagicMock
from app.adapters.rds_adapter import RDSAdapter
import pytest


@pytest.fixture
def rds_adapter():
    adapter = RDSAdapter.__new__(RDSAdapter)
    adapter.connection_string = "host=test dbname=test user=test password=test"
    adapter.connection = MagicMock()
    return adapter


def test_when_adapter_repr_or_str_then_contains_connection_info(rds_adapter):
    assert "host=test" in repr(rds_adapter)
    assert "dbname=test" in repr(rds_adapter)
    assert "test" in str(rds_adapter)


@patch("app.adapters.rds_adapter.ps.connect")
def test_when_connect_success_then_connection_created(mock_connect):
    mock_connect.return_value = MagicMock()
    adapter = RDSAdapter("host", "db", "user", "pass")
    assert adapter.connection is not None


@patch("app.adapters.rds_adapter.ps.connect", return_value=None)
def test_when_connect_failure_then_raises_connection_error(mock_connect):
    adapter = RDSAdapter.__new__(RDSAdapter)
    adapter.connection_string = "host=test dbname=test user=test password=test"
    with pytest.raises(ConnectionError):
        adapter.connect()


def test_when_close_called_then_connection_closed(rds_adapter):
    rds_adapter.connection.close = MagicMock()
    rds_adapter.close()
    assert rds_adapter.connection is None


def test_when_execute_success_then_returns_data_and_columns(rds_adapter):
    mock_cursor = MagicMock()
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [(1,)]
    mock_cursor.description = [("col1",)]
    rds_adapter.connection.cursor.return_value = mock_cursor
    rds_adapter.connection.commit = MagicMock()
    data, columns = rds_adapter.execute("SELECT 1")
    assert data == [(1,)]
    assert columns == ["col1"]


def test_when_execute_undefined_column_then_raises_value_error(rds_adapter):
    mock_cursor = MagicMock()
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.execute.side_effect = Exception("UndefinedColumn")
    rds_adapter.connection.cursor.return_value = mock_cursor
    rds_adapter.connection.rollback = MagicMock()
    with patch("app.adapters.rds_adapter.ps.errors.UndefinedColumn", Exception):
        with pytest.raises(ValueError):
            rds_adapter.execute("SELECT badcol")


def test_when_insert_called_then_returns_lastrowid(rds_adapter):
    rds_adapter.execute = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.lastrowid = 42
    rds_adapter.connection.cursor.return_value = mock_cursor
    result = rds_adapter.insert("table", (1, 2))
    rds_adapter.execute.assert_called_once()
    assert result == 42


def test_when_list_tables_called_then_returns_table_list(rds_adapter):
    rds_adapter.execute = MagicMock(return_value=([("table1",), ("table2",)], ["table_name"]))
    tables = rds_adapter.list_tables()
    rds_adapter.execute.assert_called_once()
    assert tables == [("table1",), ("table2",)]


def test_when_list_table_fields_called_then_returns_field_list(rds_adapter):
    rds_adapter.execute = MagicMock(return_value=([("col1", "int")], ["column_name", "data_type"]))
    fields = rds_adapter.list_table_fields("table1")
    rds_adapter.execute.assert_called_once()
    assert fields == [("col1", "int")]


def test_when_select_valid_table_and_fields_then_returns_data_and_query(rds_adapter):
    rds_adapter.list_tables = MagicMock(return_value=[["table1"]])
    rds_adapter.list_table_fields = MagicMock(return_value=[["col1"]])
    rds_adapter.execute = MagicMock(return_value=([("row",)], ["col1"]))
    data, columns, query = rds_adapter.select("table1", fields="col1")
    assert data == [("row",)]
    assert "SELECT col1 FROM table1" in query


def test_when_select_invalid_table_then_raises_value_error(rds_adapter):
    rds_adapter.list_tables = MagicMock(return_value=[["table1"]])
    with pytest.raises(ValueError):
        rds_adapter.select("badtable")


def test_when_select_invalid_field_then_raises_value_error(rds_adapter):
    rds_adapter.list_tables = MagicMock(return_value=[["table1"]])
    rds_adapter.list_table_fields = MagicMock(return_value=[["col1"]])
    with pytest.raises(ValueError):
        rds_adapter.select("table1", fields="badcol")


def test_when_select_count_then_query_contains_count(rds_adapter):
    rds_adapter.list_tables = MagicMock(return_value=[["table1"]])
    rds_adapter.execute = MagicMock(return_value=([("row",)], ["count"]))
    data, columns, query = rds_adapter.select("table1", count=True)
    assert "COUNT(*)" in query


def test_when_build_from_join_clause_then_returns_join_string(rds_adapter):
    clause = rds_adapter.build_from_join_clause("t1", "t2", "f1", "f2")
    assert clause == "FROM t1 INNER JOIN t2 ON t1.f1 = t2.f2"
