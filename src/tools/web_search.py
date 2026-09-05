from typing import List, Dict, Any


class WebSearchTool:
    def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", "")
                    })
            return results
        except Exception as e:
            return [{"title": "Search Error", "snippet": str(e), "url": ""}]
