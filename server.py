import math
import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="Gemini Tool Server",
    host="0.0.0.0",
    port=8050,
)

@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather in a specified city (mocked response)."""
    weather_data = {
        "london": "It's cloudy and 18°C in London.",
        "new york": "It's sunny and 25°C in New York.",
        "tokyo": "It's rainy and 20°C in Tokyo.",
        "paris": "It's 22°C with light showers in Paris.",
    }
    return weather_data.get(city.lower(), f"Sorry, I don't have weather data for {city}.")


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a basic math expression safely."""
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
    try:
        result = eval(expression, {"__builtins__": None}, allowed_names)
        return f"The result is: {result}"
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"

@mcp.tool()
def get_time(city: str) -> str:
    """Get the current time in a specified city."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        return "Timezone support requires Python 3.9+."

    city_timezones = {
        "new york": "America/New_York",
        "london": "Europe/London",
        "tokyo": "Asia/Tokyo",
        "paris": "Europe/Paris",
        "sydney": "Australia/Sydney",
    }

    tz_name = city_timezones.get(city.lower())
    if not tz_name:
        return f"Sorry, timezone info for '{city}' isn't available."

    now = datetime.datetime.now(ZoneInfo(tz_name))
    return f"The local time in {city.title()} is {now.strftime('%Y-%m-%d %H:%M:%S')}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
