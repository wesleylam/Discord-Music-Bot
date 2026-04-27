import asyncio
import DJ
import webServer
import ServersHub
import DJDB
import Chatbot

async def main():
    print("Starting gather")
    ServersHub.ServersHub.djdb = DJDB.DJDB()
    ServersHub.ServersHub.djdb.connect()
    # Capture the running loop for thread-safe operations in other modules
    ServersHub.ServersHub.loop = asyncio.get_running_loop()

    try:
        await asyncio.gather(
            DJ.startDJ(),
            asyncio.to_thread(webServer.runServer),
            asyncio.to_thread(Chatbot.Chatbot.parserLoop),
        )
    except asyncio.CancelledError:
        print("System shutting down...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass