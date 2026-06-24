"""
Adri — Web search tool.
Uses the Tavily API to search the web and return summarized results.
"""

from tavily import TavilyClient, MissingAPIKeyError, InvalidAPIKeyError, UsageLimitExceededError
from config import TAVILY_API_KEY, logger


def web_search(query: str) -> str:
    """Search the web for the given query and return a summary of the top results.

    Uses the Tavily search API to find relevant web pages. Returns a formatted
    string containing the title, snippet, and URL for the top 3-5 results.

    Args:
        query: The search query string to look up on the web.

    Returns:
        A formatted string with the top search results, or an error message
        if the search fails.
    """
    logger.info("Web search: '%s'", query)

    if not TAVILY_API_KEY:
        logger.error("Tavily API key is not set")
        return "Error: Tavily API key is not configured. Please set TAVILY_API_KEY in your .env file."

    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(query=query, max_results=5)
    except MissingAPIKeyError:
        logger.error("Tavily API key is missing")
        return "Error: Tavily API key is missing. Please set TAVILY_API_KEY in your .env file."
    except InvalidAPIKeyError:
        logger.error("Tavily API key is invalid")
        return "Error: The Tavily API key is invalid. Please check your TAVILY_API_KEY in the .env file."
    except UsageLimitExceededError:
        logger.warning("Tavily API rate limit exceeded")
        return "Error: Tavily API rate limit exceeded. Please try again later."
    except ConnectionError:
        logger.error("Network error during web search")
        return "Error: Could not connect to the search service. Please check your internet connection."
    except Exception as e:
        logger.error("Unexpected error during web search: %s", e)
        return f"Error: An unexpected error occurred while searching — {e}"

    results = response.get("results", [])
    if not results:
        logger.info("No results found for: '%s'", query)
        return f"No results found for '{query}'."

    # Format top results into a readable string
    lines = [f"Search results for '{query}':\n"]
    for i, result in enumerate(results, start=1):
        title = result.get("title", "No title")
        snippet = result.get("content", "No snippet available.")
        url = result.get("url", "")
        lines.append(f"{i}. {title}")
        lines.append(f"   {snippet}")
        if url:
            lines.append(f"   URL: {url}")
        lines.append("")

    formatted = "\n".join(lines).strip()
    logger.info("Web search returned %d results", len(results))
    return formatted


if __name__ == "__main__":
    print(web_search("latest Python 3.13 features"))
