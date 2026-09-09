from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .models import Message
from asgiref.sync import sync_to_async
from datetime import datetime


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # 🔔 Notify join
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'system_message',
                'message': 'A user joined the chat'
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # 🔔 Notify leave
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'system_message',
                'message': 'A user left the chat'
            }
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        # ✍️ Typing indicator
        if data.get('type') == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing',
                    'username': data.get('username', 'Someone')
                }
            )
            return

        message = data.get('message', '').strip()
        username = data.get('username', 'Anonymous')

        if not message:
            return

        # 💾 Save message to DB
        await self.save_message(self.room_name, username, message)

        time = datetime.now().strftime("%H:%M")

        # 📤 Send to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
                'time': time
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'username': event['username'],
            'time': event['time']
        }))

    async def typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'username': event['username']
        }))

    async def system_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': event['message']
        }))

    @sync_to_async
    def save_message(self, room, username, message):
        Message.objects.create(
            room=room,
            username=username,
            content=message
        )