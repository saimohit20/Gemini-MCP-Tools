import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
import nest_asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import google.generativeai as genai


# Add your API key 
GEMINI_API_KEY = "" 

# Apply nest_asyncio to allow nested event loops (needed for Jupyter/IPython)
nest_asyncio.apply()


class MCPGeminiClient:
    """Client for interacting with Google Gemini models using MCP tools."""

    def __init__(self, model: str = "gemini-1.5-flash"): 
        """Initialize the Google Gemini MCP client.

        Args:
            model: The Google Gemini model to use.
        """
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        
        genai.configure(api_key=GEMINI_API_KEY)

        self.gemini_model = genai.GenerativeModel(model)
        self.model_name = model
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None

    async def connect_to_server(self, server_script_path: str = "server.py"):
        """Connect to an MCP server.

        Args:
            server_script_path: Path to the server script.
        """
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        tools_result = await self.session.list_tools()
        print("\nConnected to server with tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")

    def _clean_schema_for_gemini(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively cleans a JSON schema for Gemini compatibility.
        Removes 'title' and potentially other unsupported fields.
        """
        cleaned_schema = {}
        for key, value in schema.items():
            if key == "title": # Skip the 'title' field
                continue
            if isinstance(value, dict):
                cleaned_schema[key] = self._clean_schema_for_gemini(value)
            elif isinstance(value, list):
                cleaned_schema[key] = [
                    self._clean_schema_for_gemini(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned_schema[key] = value
        return cleaned_schema

    async def get_mcp_tools(self) -> List[Dict[str, Any]]: 
        """Get available tools from the MCP server in Google Gemini format.

        Returns:
            A list of tools in Google Gemini format.
        """
        tools_result = await self.session.list_tools()
        gemini_tools = []
        for tool in tools_result.tools:
            cleaned_parameters_schema = self._clean_schema_for_gemini(tool.inputSchema)
            print("cleaned parameter schema for {tool.name}", cleaned_parameters_schema)

            gemini_tools.append(
                {
                    "function_declarations": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": cleaned_parameters_schema,
                        }
                    ]
                }
            )
        return gemini_tools

    async def process_query(self, query: str) -> str:
        """Process a query using Google Gemini and available MCP tools.

        Args:
            query: The user query.

        Returns:
            The response from Google Gemini.
        """
        tools = await self.get_mcp_tools()

        contents = [{"role": "user", "parts": [query]}]

        response = await self.gemini_model.generate_content_async(
            contents,
            tools=tools,
            tool_config={"function_calling_config": "AUTO"}
        )

        function_calls = []
        # Ensure response and its content exist before accessing
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)

        if function_calls:
            # Append the model's tool call response (the functionCall part) to the contents
            # This is important for the model to understand the conversation flow.
            contents.append(response.candidates[0].content)

            for tool_call in function_calls:
                print(f"DEBUG: Calling MCP Tool: {tool_call.name} with args: {tool_call.args}")
                result = await self.session.call_tool(
                    tool_call.name,
                    arguments=tool_call.args,
                )
                print(f"DEBUG: MCP Tool Result: {result.content[0].text}")

                contents.append(
                    {
                        "role": "function",
                        "parts": [
                            {
                                "function_response": { # <-- THIS KEY WAS CHANGED
                                    "name": tool_call.name,
                                    "response": {"result": result.content[0].text} # The result payload
                                }
                            }
                        ]
                    }
                )
                
            # Send the updated contents (including tool call and its result) back to Gemini
            final_response = await self.gemini_model.generate_content_async(
                contents,
                tools=tools,
                tool_config={"function_calling_config": "AUTO"}
            )
            
            if final_response.candidates and final_response.candidates[0].content and final_response.candidates[0].content.parts:
                return "".join([part.text for part in final_response.candidates[0].content.parts if hasattr(part, 'text')])
            else:
                return "No discernable text response after tool execution."

        # If no tool calls were made in the first response, return the direct text response
        if response.text:
            return response.text
        
        return "No response or tool call from the model."

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    """Main entry point for the client."""
    client = MCPGeminiClient()
    await client.connect_to_server("server.py")

    queries = [
        "What's the weather like in London?",
        "What is 123 * 45 + 9?",
        "What time is it in Tokyo?",
        "Tell me a fun fact about giraffes."
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        response = await client.process_query(query)
        print(f"\nResponse: {response}")
        print("-" * 30)

    await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
