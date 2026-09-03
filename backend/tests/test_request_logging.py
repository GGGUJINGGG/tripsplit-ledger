import json
import logging

from tests.base import DatabaseTestCase


class RequestLoggingTests(DatabaseTestCase):
    def test_logs_a_structured_json_line_for_each_request(self) -> None:
        logger = logging.getLogger("app.requests")

        records: list[logging.LogRecord] = []

        class _CapturingHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = _CapturingHandler()
        logger.addHandler(handler)
        try:
            response = self.client.get("/api/health")
        finally:
            logger.removeHandler(handler)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(records), 1)

        record = records[0]
        extra_fields = record.extra_fields
        self.assertEqual(extra_fields["http_method"], "GET")
        self.assertEqual(extra_fields["path"], "/api/health")
        self.assertEqual(extra_fields["status_code"], 200)
        self.assertIsInstance(extra_fields["duration_ms"], float)
        self.assertGreaterEqual(extra_fields["duration_ms"], 0)

    def test_json_formatter_produces_valid_parseable_json(self) -> None:
        from app.logging_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="app.requests",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="GET /api/health 200",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {
            "http_method": "GET",
            "path": "/api/health",
            "status_code": 200,
            "duration_ms": 1.23,
            "client_ip": "127.0.0.1",
        }

        formatted = formatter.format(record)
        payload = json.loads(formatted)

        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "app.requests")
        self.assertEqual(payload["http_method"], "GET")
        self.assertEqual(payload["status_code"], 200)
