from django.conf import settings
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from terminal.terminal_tools import colorize
from MUD.ascii_art import ART

from MUD.models import Room, Player


class MudConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            # Accept the connection and store the Player object for current User
            await self.accept()

            try:
                self.player = await database_sync_to_async(Player.objects.get)(user=self.scope["user"])
            except Player.DoesNotExist:
                await self.send_message("Current User has no Player!")
                await self.close()
                return

            # If all is good, go online, send a welcome and joing the global an room chats
            self.isOnline = True
            await self.send_welcome()
            await self.join_room('dungeon')
            await self.join_room(await self.get_current_room_name())

    async def receive_json(self, content):
        """ Route client commands to internal functions. """
        command = content.get("command", None)
        try:
            if command == "leave":
                await self.leave_room()
                self.isOnline = False
            elif command == "send":
                await self.send_room(content["message"])
            elif command == "help":
                await self.send_help()
            elif command == "look":
                await self.send_room_description()
            elif command == "go":
                if content["message"]:
                    current_room = self.player.room.name
                    target_room_name = " ".join(content["message"])
                    new_room = await self.move_to_room(target_room_name)
                    if new_room:
                        await self.join_room(new_room)
                        await self.leave_room(current_room)
                        await self.send_room_description()
                    else:
                        await self.send_message("Invalid room.")
                else:
                    await self.send_message("No room specified.")
            else:
                await self.send_unknown(command)
        except Exception as e:
            await self.send_json({"error": e})

    async def disconnect(self, code):
        try:
            await self.leave_group()
        except Exception:
            pass

    async def send_message(self, message):
        await self.send_json({
            'message': message
        })

    async def send_welcome(self):
        await self.send_json( {'message': colorize('brightBlue', ART['BANNER'])} )

    async def send_unknown(self, command):
        await self.send_json({
            'message': f"I don't understand `{command}`, try " + colorize('brightYellow', "help") + "."
        })

    async def send_help(self):
        await self.send_json({
            'message': 'options: help, send, leave, look, go <room>' # we should have a set() of commands/options
        })

    async def send_room_description(self):
        message = await self.get_current_room_description()
        await self.send_json({
            'message': message
        })

    @database_sync_to_async
    def get_current_room_name(self):
        return self.player.room.name

    @database_sync_to_async
    def get_current_room_description(self):
        """ Returns a string with the description of the current room. """

        players = (
            Room.objects.get(name=self.player.room.name).player_set.all()
                        .exclude(name=self.player.name)
                        .values_list('name',flat=True)
        )
        if players:
            players_string= "Players here: " + colorize('brightBlue', ", ".join(players)) + "\r\n"
        else:
            players_string = ""

        exits = list(self.player.room.connections.all())

        message = (
                   "You are in " + colorize('brightGreen', self.player.room.name) + "\r\n\n" +
                    self.player.room.description + "\r\n\n" +
                   players_string +
                   "Exits: " + ", ".join([colorize('brightGreen', exit.name) for exit in exits])
                  )

        return message

    @database_sync_to_async
    def move_to_room(self, room_name):
        """ Move the current player to another room. Return room name on success. """

        try:
            self.player.room = self.player.room.connections.get(name__iexact=room_name.lower())
            self.player.save()
        except Room.DoesNotExist:
            return False
        return self.player.room.name

    async def join_room(self, room_name):
        await self.channel_layer.group_send(
            room_name,
            {
                'type': 'chat.join',
                'username': self.scope['user'].username,
            }
        )

        await self.channel_layer.group_add(
            room_name,
            self.channel_name,
        )

    async def leave_room(self, room_name):
        await self.channel_layer.group_send(
            room_name,
            {
                'type': 'chat.leave',
                'username': self.scope['user'].username,
            }
        )

        await self.channel_layer.group_discard(
            room_name,
            self.channel_name,
        )

    async def send_room(self, message):
        if not self.isOnline:
            raise Exception('Rejected')
        text = colorize('brightBlue', self.scope["user"].username) + " says, \"" + " ".join(message) + '"'
        await self.channel_layer.group_send(
            await self.get_current_room_name(),
            {
                "type": "chat.message",
                "username": self.scope["user"].username,
                "message": text,
            }
        )

    # These helper methods are named by the types we send - so chat.join becomes chat_join
    async def chat_join(self, event):
        if not (event["username"] == self.scope["user"].username):
            await self.send_json(
                {
                    "msg_type": 'ENTER',
                    "username": colorize('brightBlue', event["username"]),
                },
            )

    async def chat_leave(self, event):
        """
        Called when someone has left our chat.
        """
        # Send a message down to the client
        if not (event["username"] == self.scope["user"].username):
            await self.send_json(
                {
                    "msg_type": 'EXIT',
                    "username": colorize('brightBlue', event["username"]),
                },
            )

    async def chat_message(self, event):
        """
        Called when someone has messaged our chat.
        """
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": event['type'],
                "username": event["username"],
                "message": event["message"],
            },
        )
