from browser_use import Agent, ChatOpenAI
import asyncio

async def main():
    llm = ChatOpenAI(
        base_url="http://localhost:8080/v1",
        api_key="none",
        model="llama3.2:3b",
        temperature=0.0
    )
    task = "Navigate to DuckDuckGo.com and search for 'browser-use"
    agent = Agent(task=task, llm=llm)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())