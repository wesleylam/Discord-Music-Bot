from concurrent.futures import ProcessPoolExecutor
import asyncio
from DJ import startDJ
from webServer import runServer
from VcControlManager import VcControlManager

async def main():
    print("Starting gather")
    await asyncio.gather(
        asyncio.to_thread(lambda : runServer(vcManager)),
        startDJ(vcManager)
    )


if __name__ == "__main__":
    global vcManager
    vcManager = VcControlManager()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())