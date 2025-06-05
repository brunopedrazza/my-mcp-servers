from typing import Any, Optional

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.cosmos import CosmosClient
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cosmos")

_client: Optional[CosmosClient] = None
_container = None


@mcp.init
async def initialize(
    keyvault_name: str,
    secret_name: str,
    database_name: str,
    container_name: str,
) -> str:
    """Initialize connection to Cosmos DB using Key Vault secret."""
    global _client, _container
    try:
        credential = DefaultAzureCredential()
        vault_url = f"https://{keyvault_name}.vault.azure.net"
        secret_client = SecretClient(vault_url=vault_url, credential=credential)
        connection_string = secret_client.get_secret(secret_name).value

        _client = CosmosClient.from_connection_string(connection_string)
        database = _client.get_database_client(database_name)
        _container = database.get_container_client(container_name)
        return "Initialization successful"
    except Exception as e:
        _client = None
        _container = None
        return f"Initialization failed: {e}"


@mcp.tool()
async def get_document_by_id(doc_id: str) -> dict[str, Any] | None:
    """Fetch a document by id from the configured Cosmos DB container."""
    if _container is None:
        return {"error": "Cosmos DB container not initialized"}
    try:
        items = list(
            _container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": doc_id}],
                enable_cross_partition_query=True,
            )
        )
        if items:
            return items[0]
    except Exception as e:
        return {"error": f"Failed to query document: {str(e)}"}
    return None


if __name__ == "__main__":
    mcp.run(transport="stdio")
