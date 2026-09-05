import pytest
from unittest.mock import MagicMock, patch
from src.tools.system_info import SystemInfoTool
from src.tools.web_search import WebSearchTool

def test_system_info_summary():
    tool = SystemInfoTool()
    summary = tool.get_summary()
    assert "cpu_percent" in summary
    assert "ram_percent" in summary
    assert "ram_available_gb" in summary
    assert "os" in summary
    assert isinstance(summary["cpu_percent"], (int, float))
    assert isinstance(summary["ram_percent"], (int, float))
    assert isinstance(summary["ram_available_gb"], (int, float))
    assert isinstance(summary["os"], str)

def test_web_search_success():
    tool = WebSearchTool()
    with patch("duckduckgo_search.DDGS") as mock_ddgs_cls:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.text.return_value = [
            {"title": "Test Title", "body": "Test Snippet", "href": "https://example.com"}
        ]
        mock_ddgs_cls.return_value = mock_instance

        results = tool.search("python", max_results=1)
        assert len(results) == 1
        assert results[0] == {
            "title": "Test Title",
            "snippet": "Test Snippet",
            "url": "https://example.com"
        }

def test_web_search_error_handling():
    tool = WebSearchTool()
    with patch("duckduckgo_search.DDGS", side_effect=Exception("Network error")):
        results = tool.search("python")
        assert len(results) == 1
        assert results[0]["title"] == "Search Error"
        assert "Network error" in results[0]["snippet"]
