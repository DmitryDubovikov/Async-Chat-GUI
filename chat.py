import argparse
import asyncio
import logging
from datetime import datetime
from contextlib import aclosing

import gui


async def send_test_messages(messages_queue):
    while True:
        await messages_queue.put(datetime.timestamp(datetime.now()))
        await asyncio.sleep(10)


async def read_messages(reader, messages_queue=None):
    while True:
        data = await reader.read(1024)
        if not data:
            break

        message = data.decode().strip()
        await messages_queue.put(message)
        logging.info(f"Message read: {message}")


async def open_connection_and_read(host, port, messages_queue):
    while True:
        try:
            async with aclosing(await asyncio.open_connection(host, port)) as (
                reader,
                writer,
            ):
                await read_messages(reader, messages_queue)
        except Exception as e:
            logging.error(f"An error occurred: {e}")
        finally:
            if not reader.at_eof():
                reader.feed_eof()
            writer.close()
            await writer.wait_closed()

        # Sleep for some time before trying to reconnect
        await asyncio.sleep(5)


async def main(host, port):
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await asyncio.gather(
        # asyncio.create_task(send_test_messages(messages_queue)),
        send_test_messages(messages_queue),
        open_connection_and_read(host, port, messages_queue),
        gui.draw(messages_queue, sending_queue, status_updates_queue),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to a chat server.")
    parser.add_argument(
        "--host",
        type=str,
        default="minechat.dvmn.org",
        help="Host name of the chat server",
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Port number of the chat server"
    )
    parser.add_argument(
        "--history",
        type=str,
        default="minechat.history",
        dest="history_filename",
        help="History filename to read messages from",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    asyncio.run(main(args.host, args.port))
