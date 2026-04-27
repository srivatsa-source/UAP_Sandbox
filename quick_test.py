import asyncio
from mcp.client.stdio import stdio_client, get_default_environment, StdioServerParameters
from mcp.client.session import ClientSession

async def main():
    server_params = StdioServerParameters(
        command="uap.exe",
        args=["start"],
        env=get_default_environment()
    )
    
    print("Connecting to UAP MCP Server via stdio...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Successfully securely negotiated MCP Initialization!")
            
            tools = await session.list_tools()
            print("\nAvailable UAP Tools exposed over MCP:")
            for tool in tools.tools:
                print(f" 🔌 {tool.name}: {tool.description}")

if __name__ == "__main__":
    asyncio.run(main())