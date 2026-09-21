import json

from app.support_bus.datastream import parse_datastream_object


def test_parse_tickets_insert() -> None:
    record = {
        "read_method": "postgres-cdc-wal",
        "table": "tickets",
        "change_type": "INSERT",
        "payload": {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
    }
    raw = (json.dumps(record) + "\n").encode("utf-8")
    assert parse_datastream_object(raw) == {"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}


def test_parse_messages_update_skips_delete() -> None:
    insert = {
        "read_method": "postgres-cdc-wal",
        "table": "messages",
        "change_type": "INSERT",
        "payload": {
            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "ticket_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        },
    }
    delete = {
        "read_method": "postgres-cdc-wal",
        "table": "messages",
        "change_type": "DELETE",
        "payload": {"ticket_id": "cccccccc-cccc-cccc-cccc-cccccccccccc"},
    }
    backfill = {
        "read_method": "postgresql-backfill-foo",
        "table": "tickets",
        "change_type": "INSERT",
        "payload": {"id": "dddddddd-dddd-dddd-dddd-dddddddddddd"},
    }
    raw = "\n".join(json.dumps(row) for row in (insert, delete, backfill)).encode(
        "utf-8"
    )
    assert parse_datastream_object(raw) == {"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}


def test_parse_gcp_jsonl_source_metadata() -> None:
    record = {
        "read_method": "postgresql-cdc",
        "object": "public_tickets",
        "source_metadata": {
            "table": "tickets",
            "schema": "public",
            "change_type": "INSERT",
            "is_deleted": False,
        },
        "payload": {"id": "160a39fe-e7ca-4763-851f-1d3d31e504d2"},
    }
    raw = (json.dumps(record) + "\n").encode("utf-8")
    assert parse_datastream_object(raw) == {"160a39fe-e7ca-4763-851f-1d3d31e504d2"}
