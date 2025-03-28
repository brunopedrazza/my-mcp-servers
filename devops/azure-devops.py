from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from typing import Optional, Dict, Any
import os
from mcp.server.fastmcp import FastMCP

# Initialize Azure DevOps client
organization_url = os.getenv('AZURE_DEVOPS_ORG_URL')
personal_access_token = os.getenv('AZURE_DEVOPS_PAT')

# Create a connection object
credentials = BasicAuthentication('', personal_access_token)
connection = Connection(base_url=organization_url, creds=credentials)

mcp = FastMCP("azure-devops")

@mcp.tool()
async def get_status(name: str) -> str:
    return f"Azure DevOps {name} is running"

@mcp.tool()
async def create_work_item(
    project: str,
    title: str,
    work_item_type: str = "Task",
    description: Optional[str] = None,
    assigned_to: Optional[str] = None,
    priority: int = 2,
    tags: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a work item in Azure DevOps.
    
    Args:
        project: The name of the Azure DevOps project
        title: Title of the work item
        work_item_type: Type of work item (Task, Bug, User Story, etc.)
        description: Description of the work item
        assigned_to: Email of the person to assign the work item to
        priority: Priority of the work item (1-4)
        tags: Comma-separated list of tags
    
    Returns:
        Dict containing the created work item details
    """
    if not organization_url or not personal_access_token:
        raise ValueError("Azure DevOps credentials not configured. Please set AZURE_DEVOPS_ORG_URL and AZURE_DEVOPS_PAT environment variables.")

    # Get a client for the work item tracking area
    wit_client = connection.clients.get_work_item_tracking_client()
    
    # Create the work item
    document = [
        {
            "op": "add",
            "path": "/fields/System.Title",
            "value": title
        }
    ]
    
    if description:
        document.append({
            "op": "add",
            "path": "/fields/System.Description",
            "value": description
        })
    
    if assigned_to:
        document.append({
            "op": "add",
            "path": "/fields/System.AssignedTo",
            "value": assigned_to
        })
    
    if priority:
        document.append({
            "op": "add",
            "path": "/fields/Microsoft.VSTS.Common.Priority",
            "value": priority
        })
    
    if tags:
        document.append({
            "op": "add",
            "path": "/fields/System.Tags",
            "value": tags
        })
    
    created_item = wit_client.create_work_item(
        document=document,
        project=project,
        type=work_item_type
    )
    
    return {
        "id": created_item.id,
        "url": created_item.url,
        "title": created_item.fields["System.Title"],
        "state": created_item.fields["System.State"]
    }

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')