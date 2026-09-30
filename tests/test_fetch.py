import unittest
from unittest.mock import Mock, patch

import requests

from src.config import ScraperSettings
from src.fetch import FetchError, get_if_exists, get_with_retries


def response(status_code: int = 200) -> Mock:
    result = Mock(spec=requests.Response)
    result.status_code = status_code
    result.raise_for_status.side_effect = (
        requests.HTTPError(response=result) if status_code >= 400 else None
    )
    return result


class FetchTests(unittest.TestCase):
    def test_missing_resource_returns_none(self) -> None:
        with patch("src.fetch.requests.get", return_value=response(404)):
            self.assertIsNone(get_if_exists("https://example.invalid", timeout=1))

    def test_other_http_errors_are_raised(self) -> None:
        with patch("src.fetch.requests.get", return_value=response(500)):
            with self.assertRaises(requests.HTTPError):
                get_if_exists("https://example.invalid", timeout=1)

    def test_retries_until_a_request_succeeds(self) -> None:
        ok = response()
        with patch(
            "src.fetch.requests.get",
            side_effect=[requests.ConnectionError("offline"), ok],
        ) as get:
            result = get_with_retries(
                "https://example.invalid", ScraperSettings(retries=2, delay=0)
            )

        self.assertIs(result, ok)
        self.assertEqual(get.call_count, 2)

    def test_raises_after_exhausting_retries(self) -> None:
        with patch(
            "src.fetch.requests.get", side_effect=requests.ConnectionError("offline")
        ):
            with self.assertRaises(FetchError):
                get_with_retries(
                    "https://example.invalid", ScraperSettings(retries=2, delay=0)
                )


if __name__ == "__main__":
    unittest.main()
