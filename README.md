# My MCP Servers

A collection of custom MCP (Model Context Protocol) servers providing various services including calendar management and weather information.

## Features

- **Calendar Service**: Integration with Google Calendar API for event management
- **Weather Service**: Weather information and forecasting capabilities

## System Requirements

- Python 3.10 or higher
- MCP SDK 1.2.0 or higher
- Google Calendar API credentials (`credentials.json`)

## Environment Setup

1. Install uv (MacOS/Linux):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Note: Restart your terminal after installing uv to ensure the command is available.

2. Clone the repository:
```bash
git clone <your-repository-url>
cd my-mcp-servers
```

3. Create and activate virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
```

4. Install dependencies:
```bash
uv add "mcp[cli]" google-api-core google-api-python-client google-auth google-auth-oauthlib httpx python-dateutil pytz tzlocal
```

## Configuration

1. Place your Google Calendar API credentials in `credentials.json`
   Note: The authentication token will be automatically generated on first use of the calendar service.

## Services

### Calendar Service
The calendar service provides integration with Google Calendar, allowing you to:
- Create and manage calendar events
- List upcoming events
- Set up recurring meetings

### Weather Service
The weather service offers:
- Weather forecasts
- Weather alerts
- Location-based weather information

## Dependencies

- google-api-core
- google-api-python-client
- google-auth
- google-auth-oauthlib
- httpx
- mcp[cli]
- python-dateutil
- pytz
- tzlocal

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
