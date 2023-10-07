import asyncio
import gui


async def send_test_messages(messages_queue):
    # Отправить тестовые сообщения в очередь messages_queue
    test_messages = ["Привет, мир!", "Это тестовое сообщение.", "Asyncio работает!"]
    for message in test_messages:
        await messages_queue.put(message)
        await asyncio.sleep(1)  # Подождать 1 секунду между отправкой сообщений


async def main():
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    asyncio.create_task(send_test_messages(messages_queue))

    await gui.draw(messages_queue, sending_queue, status_updates_queue)


if __name__ == "__main__":
    asyncio.run(main())
