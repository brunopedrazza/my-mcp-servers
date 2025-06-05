# My MCP Servers

A collection of custom MCP (Model Context Protocol) servers providing various services including calendar management and weather information.

For more information about building MCP servers, see the [official MCP documentation](https://modelcontextprotocol.io/quickstart/server).

## Features

- **Calendar Service**: Integration with Google Calendar API for event management
- **Weather Service**: Weather information and forecasting capabilities
- **Sound Control Service**: Basic playback controls for the Music app on macOS
- **Cosmos DB Service**: Retrieve documents from Azure Cosmos DB containers

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

3. Sync your environment:
```bash
uv sync
```

4. Test if it's working:
```bash
uv run weather/weather.py
```

## Configuration

1. Place your Google Calendar API credentials in `credentials.json`
   - To obtain your credentials, follow the [Google Calendar API Python Quickstart Guide](https://developers.google.com/calendar/api/quickstart/python)
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

### Sound Control Service
This service exposes simple playback controls for macOS. It can:
- Play or pause the current track
- Skip to the next track
- Return to the previous track

### Cosmos DB Service
The Cosmos DB service connects to Azure Cosmos DB and allows retrieval of
documents by their `id`. Connection information is securely loaded from an Azure
Key Vault secret during initialization.

#### Usage
Initialize the service with your Azure resources:
- `keyvault_name`: Your Azure Key Vault name (e.g., "my-keyvault")
- `secret_name`: Name of the secret containing your Cosmos DB connection string
- `database_name`: Target Cosmos DB database name
- `container_name`: Target container name within the database

Example initialization:
```python
# The service will automatically connect using DefaultAzureCredential
# Ensure your environment has proper Azure authentication configured
await initialize(
    keyvault_name="my-company-keyvault",
    secret_name="cosmos-connection-string", 
    database_name="production-db",
    container_name="documents"
)
```

Once initialized, you can retrieve documents by ID:
```python
# Retrieve a document by its ID
document = await get_document_by_id("user-123")
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
