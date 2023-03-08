from concurrent.futures import ProcessPoolExecutor
import asyncio
import DJ
import webServer 
import ServersHub
import DJDynamoDB

async def main():
    print("Starting gather")
    ServersHub.ServersHub.djdb = DJDynamoDB.DJDB()
    ServersHub.ServersHub.djdb.connect()
    ServersHub.ServersHub.loop = asyncio.get_event_loop()
    await asyncio.gather(
        asyncio.to_thread(webServer.runServer),
        DJ.startDJ()
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())