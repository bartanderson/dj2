import asyncio
from browser_use import Agent
from langchain_ollama import ChatOllama

async def main():
    # Use a model you already have (adjust the name if needed)
    llm = ChatOllama(
        model="llama3.2:3b",   # or your preferred model (e.g., deepseek-r1:32b)
        num_ctx=128000,            # your full context window
        temperature=0.0
    )

    agent = Agent(
        task="Go to chat.deepseek.com and tell me what the page title is",
        llm=llm,
        use_vision=False,          # set to True if your model supports vision
    )

    result = await agent.run()
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())