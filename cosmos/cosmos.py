from dataclasses import dataclass
import os
from typing import Any
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.cosmos import CosmosClient, ContainerProxy
from mcp.server.fastmcp import FastMCP

@dataclass
class AppContext:
    container: ContainerProxy

@asynccontextmanager
async def cosmos_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage Cosmos DB connection lifecycle."""
    # Get configuration from environment variables
    keyvault_name = os.getenv("AZURE_KEYVAULT_NAME")
    secret_name = os.getenv("COSMOS_SECRET_NAME")
    database_name = os.getenv("COSMOS_DATABASE_NAME") 
    container_name = os.getenv("COSMOS_CONTAINER_NAME")
    
    if not all([keyvault_name, secret_name, database_name, container_name]):
        raise ValueError(
            "Missing required environment variables: "
            "AZURE_KEYVAULT_NAME, COSMOS_SECRET_NAME, COSMOS_DATABASE_NAME, COSMOS_CONTAINER_NAME"
        )
    
    # Initialize Cosmos DB connection
    credential = DefaultAzureCredential()
    vault_url = f"https://{keyvault_name}.vault.azure.net"
    secret_client = SecretClient(vault_url=vault_url, credential=credential)
    connection_string = secret_client.get_secret(secret_name).value

    _client = CosmosClient.from_connection_string(connection_string)
    database = _client.get_database_client(database_name)
    _container = database.get_container_client(container_name)
    
    # Yield the initialized resources
    yield AppContext(container=_container)


# Initialize FastMCP server with lifespan
mcp = FastMCP("cosmos", lifespan=cosmos_lifespan)


@mcp.tool()
async def get_document_by_id(doc_id: str) -> dict[str, Any]:
    """Fetch a document by id from the configured Cosmos DB container."""
    ctx = mcp.get_context()
    container: ContainerProxy = ctx.request_context.lifespan_context.container
    
    if container is None:
        return {"error": "Cosmos DB container not available. Server may not be properly initialized."}
    
    try:
        items = list(
            container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": doc_id}],
                enable_cross_partition_query=True,
            )
        )
        if items:
            return {"success": True, "data": items[0]}
        return {"success": False, "error": f"Document with id '{doc_id}' not found"}
    except Exception as e:
        return {"success": False, "error": f"Failed to fetch document: {str(e)}"}


@mcp.tool() 
async def get_container_info() -> dict[str, Any]:
    """Get information about the Cosmos DB container."""
    ctx = mcp.get_context()
    container: ContainerProxy = ctx.request_context.lifespan_context.container
    
    if container is None:
        return {"error": "Cosmos DB container not available. Server may not be properly initialized."}
    
    try:
        # Get container properties
        container_props = container.read()
        return {
            "success": True,
            "container_id": container_props["id"],
            "partition_key": container_props.get("partitionKey", {}),
            "indexing_policy": container_props.get("indexingPolicy", {}),
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to get container info: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
