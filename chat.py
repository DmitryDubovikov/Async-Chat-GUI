import argparse
import asyncio
import logging
import os
import sys
from tkinter import messagebox

import aiofiles
from anyio import create_task_group
from dotenv import load_dotenv

import gui
from utils import connection, get_nickname


class InvalidToken(Exception):
    pass


async def send_messages(writer, sending_queue, watchdog_queue):
    while True:
        message = await sending_queue.get()
        message = message.replace("\n", "") + "\n"
        writer.write(message.encode() + b"\n")
        await writer.drain()
        await watchdog_queue.put("Message sent")


async def read_messages(reader, messages_queue, watchdog_queue, history_filename):
    while True:
        data = await reader.read(1024)
        if not data:
            # break
            raise ConnectionError

        message = data.decode().strip()
        await messages_queue.put(message)
        await watchdog_queue.put("New message in chat")

        async with aiofiles.open(history_filename, mode="a") as file:
            await file.write(message + "\n")


async def ping_pong(reader, writer, watchdog_queue):
    while True:
        writer.write("\n".encode())
        await writer.drain()
        await reader.readline()
        watchdog_queue.put_nowait("Ping successful")
        await asyncio.sleep(10)


async def authorise(reader, writer, account_hash):
    message = account_hash + "\n"
    writer.write(message.encode())
    await writer.drain()

    data = await reader.read(1024)
    response = data.decode()
    if "null" in response:
        messagebox.showerror(
            "Ошибка",
            "Неверный токен. Пожалуйста, проверьте ваш токен и попробуйте снова.",
        )
        raise InvalidToken("Неверный токен получен от сервера.")
    return get_nickname(response)


async def restore_messages(messages_queue, history_filename):
    async with aiofiles.open(history_filename, mode="r") as file:
        lines = await file.readlines()
        for line in lines:
            message = line.strip()
            await messages_queue.put(message)


async def watch_for_connection(watchdog_queue, watchdog_logger):
    while True:
        try:
            message = await asyncio.wait_for(watchdog_queue.get(), timeout=1)
            watchdog_logger.info(f"Connection is alive. {message}")
        except asyncio.TimeoutError:
            watchdog_logger.info("1s timeout is elapsed")


async def connect_and_write(
    host,
    port,
    sending_queue,
    status_updates_queue,
    watchdog_queue,
    account_hash,
):
    try:
        async with connection(host, port) as (reader, writer):
            message = gui.SendingConnectionStateChanged.ESTABLISHED
            await status_updates_queue.put(message)

            try:
                nickname = await authorise(reader, writer, account_hash)
                logging.info(f"Выполнена авторизация. Пользователь {nickname}.")
                await watchdog_queue.put("Connection is alive. Authorization done")

                message = gui.NicknameReceived(nickname)
                await status_updates_queue.put(message)

                async with create_task_group() as tg:
                    tg.start_soon(
                        send_messages,
                        writer,
                        sending_queue,
                        watchdog_queue,
                    )
                    tg.start_soon(ping_pong, reader, writer, watchdog_queue)

            except InvalidToken as e:
                logging.error(f"An error occurred: {e}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit()
    finally:
        if not reader.at_eof():
            reader.feed_eof()
        writer.close()
        await writer.wait_closed()


async def connect_and_read(
    host, port, messages_queue, status_updates_queue, watchdog_queue, history_filename
):
    while True:
        try:
            async with connection(host, port) as (reader, writer):
                message = gui.ReadConnectionStateChanged.ESTABLISHED
                await status_updates_queue.put(message)

                await read_messages(
                    reader, messages_queue, watchdog_queue, history_filename
                )
        except Exception as e:
            logging.error(f"An error occurred: {e}")

        # Sleep for some time before trying to reconnect
        await asyncio.sleep(5)


async def handle_connection(
    host,
    port_read,
    port_write,
    messages_queue,
    sending_queue,
    status_updates_queue,
    watchdog_queue,
    account_hash,
    watchdog_logger,
    history_filename,
):
    async with create_task_group() as tg:
        tg.start_soon(
            connect_and_read,
            host,
            port_read,
            messages_queue,
            status_updates_queue,
            watchdog_queue,
            history_filename,
        )
        tg.start_soon(
            connect_and_write,
            host,
            port_write,
            sending_queue,
            status_updates_queue,
            watchdog_queue,
            account_hash,
        )
        tg.start_soon(watch_for_connection, watchdog_queue, watchdog_logger),


async def main(host, port_read, port_write, history_filename):
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    load_dotenv()
    account_hash = os.getenv("ACCOUNT_HASH")

    await restore_messages(messages_queue, history_filename)

    async with create_task_group() as tg:
        tg.start_soon(
            handle_connection,
            host,
            port_read,
            port_write,
            messages_queue,
            sending_queue,
            status_updates_queue,
            watchdog_queue,
            account_hash,
            watchdog_logger,
            history_filename,
        )
        tg.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to a chat server.")
    parser.add_argument(
        "--host",
        type=str,
        default="minechat.dvmn.org",
        help="Host name of the chat server",
    )
    parser.add_argument(
        "--port_read",
        type=int,
        default=5000,
        help="Read port number of the chat server",
    )
    parser.add_argument(
        "--port_write",
        type=int,
        default=5050,
        help="Write port number of the chat server",
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

    watchdog_logger = logging.getLogger("watchdog_logger")
    watchdog_logger.setLevel(logging.INFO)

    try:
        asyncio.run(
            main(args.host, args.port_read, args.port_write, args.history_filename)
        )
    except (gui.TkAppClosed, KeyboardInterrupt):
        logging.info("gui was closed. exiting ..")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
