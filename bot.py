import argparse
import asyncio
import functools
import logging
import time

import raftos

import telepot
import telepot.aio


class RelyBot(telepot.aio.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.alarms = raftos.ReplicatedDict(name='alarms')
        self.scheduled_alarms = {}

    async def init_alarms(self):
        now = int(time.time())
        for chat_id, alarm_time in await self.alarms.items():
            if alarm_time >= now:
                self.schedule_alarm(chat_id, alarm_time - now)

    async def start(self):
        await self.init_alarms()
        asyncio.ensure_future(self.message_loop())

    def stop(self):
        raise telepot.exception.StopListening

    async def idle(self):
        while True:
            await asyncio.sleep(1)

    async def on_chat_message(self, msg):
        if msg['text'].isdigit():
            timeout = int(msg['text'])
            update_time = int(msg['date'])
            chat_id = str(msg['chat']['id'])

            if chat_id in await self.alarms.get():
                future = self.scheduled_alarms[chat_id]
                if not future.done():
                    future.set_result(None)
                del self.scheduled_alarms[chat_id]

            await self.alarms.update({
                chat_id: update_time + timeout
            })
            self.schedule_alarm(chat_id, timeout)

    def schedule_alarm(self, chat_id, timeout):
        future = asyncio.Future()

        def alarm_for_chat_id(future):
            if not future.done():
                future.set_result(chat_id)

        self.loop.call_later(timeout, alarm_for_chat_id, future)
        self.scheduled_alarms[chat_id] = future
        asyncio.ensure_future(self.alarm(future))

    async def alarm(self, future):
        chat_id = await future
        if chat_id:
            await self.sendMessage(chat_id, 'Here you go!')
            await self.alarms.delete(chat_id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--node')
    parser.add_argument('--cluster')
    args = parser.parse_args()

    cluster = ['127.0.0.1:{}'.format(port) for port in args.cluster.split()]
    node_id = '127.0.0.1:{}'.format(args.node)

    bot = RelyBot(open('token').readline().strip())

    raftos.configure({
        'log_path': './',
        'serializer': raftos.serializers.JSONSerializer,

        'on_leader': bot.start,
        'on_follower': bot.stop
    })

    loop = asyncio.get_event_loop()
    loop.create_task(raftos.register(node_id, cluster=cluster))
    loop.run_until_complete(bot.idle())
