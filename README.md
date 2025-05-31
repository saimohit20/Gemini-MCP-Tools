# gemini-mcp-tools

This repository contains a Python client that demonstrates how to integrate Google Gemini's Function Calling capabilities with a MCP server for external tool execution. This allows the Gemini LLM to intelligently decide when to use specific functions (tools) hosted on your MCP server to answer user queries or perform actions.

## Project Structure

**client.py**: The main client script that describes the interaction between user queries, Google Gemini, and the MCP server.
**server.py** : Your MCP server script which defines and hosts the actual tools (e.g., get_weather, calculate, get_time).
**README.md**: This file!

## Overall Architecture: How MCP Works

- User provides a query.
- Based on the query, Gemini selects a tool from the list of available tools provided by the MCP server.
- Gemini makes this selection based on the tool's name, its description, and the user's query intent.
- If a tool is selected, Gemini returns a response in a specific JSON format, indicating which tool to call and with what arguments.
- After your client executes the tool and gets the result, the entire conversation history (including your original query, Gemini's tool instruction, and the tool's output) is sent back to Gemini.
- Gemini then uses this complete history to provide the final response.
- If no tool is selected, Gemini directly provides a general answer to the query without involving any tools.

## How to Run

- Open client.py and replace the placeholder "" for GEMINI_API_KEY with your actual key : GEMINI_API_KEY = "YOUR_ACTUAL_GEMINI_API_KEY_HERE"
- Make sure your server.py is ready to be launched by the client. The client.py automatically starts the server.py process for you using StdioServerParameters.
- Run the client script:
**python client.py**

## How it Works: The Tool-Use Cycle

At its core, the client facilitates a multi-turn conversation between your query, Gemini, and your local tools.

1. **Tool Discovery and Declaration**
Your client.py starts. It establishes a connection to your local server.py (via MCP).

The client then asks the MCP server, "What tools do you have?" The server responds with details like tool names, descriptions, and their required input parameters (in JSON Schema format).

The client takes these details and formats them into a specific structure that Google Gemini understands (using "function_declarations"). This is how Gemini "learns" about your available tools and their capabilities.

-----------------------------------------------------------------------------------------------

2. **The LLM's Decision (process_query - First Turn)**

User Query: You ask a question (e.g., "What's the weather like in London?").
First Call to Gemini: Your client sends your query along with the list of available tools to Gemini. You instruct Gemini to AUTOmatically decide if a tool is needed.
Gemini's Reasoning:
Gemini analyzes your query and compares it with the description and parameters of the tools it "knows" about.
It internally determines if answering the query requires external information obtainable by a tool.
If it decides a tool is useful, it identifies the tool name and the arguments it needs to call that tool, based on your query.
Gemini's Response (Tool Call): Instead of a text answer, Gemini responds with a function_call instruction. This tells your client: "Hey, I need you to run get_weather with location='London'."

Your Client's Action: Your client.py detects this function_call within the response.candidates[0].content.parts. It then adds this function_call instruction to the ongoing conversation history (contents).

--------------------------------------------------------------------------------------------------------

3. **Tool Execution and Reporting (process_query - Your Code's Action)Execute Tool**:

Your client uses the extracted tool_call.name and tool_call.args to call the actual function on your MCP server (self.session.call_tool). Example: Your code executes get_weather("London") via MCP.
Get Result: The MCP server runs the function and returns the real-world result (e.g., "It's cloudy and 18°C in London.").
Report Result to Gemini: Crucially, your client then adds this tool's result back into the conversation history (contents). This time, it uses the special "role": "function" and "function_response" key to inform Gemini what happened.
---------------------------------------------

5. **Final Answer Generation (process_query - Second Turn)**
   
Second Call to Gemini: Your client sends the entire updated conversation history (original query + Gemini's tool call + tool's result) back to Gemini.
Gemini's Final Reasoning: With the context of the tool's result, Gemini can now synthesize a complete, human-readable answer to the original query.
Gemini's Response (Final Answer): Gemini provides a direct text response based on the data it received from the tool. Example of Gemini's final text response:
"The weather in London is currently cloudy with a temperature of 18°C."
Your Client's Action: Your client.py extracts this text and returns it as the final output.
------------------------------------------------------------------------------------------------

**Handling No Tool Call**

If, in the first turn, Gemini determines a tool is not needed (e.g., "Tell me a fun fact about giraffes."), it directly provides a text response. In this scenario, your code skips the tool execution and simply returns that direct text from Gemini.



