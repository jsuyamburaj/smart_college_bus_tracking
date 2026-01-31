import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser
from buses.models import Bus
from accounts.models import StudentProfile

class BusTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.bus_id = self.scope['url_route']['kwargs']['bus_id']
        self.bus_group_name = f'bus_{self.bus_id}'
        
        # Join bus group
        await self.channel_layer.group_add(
            self.bus_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current bus location
        bus_data = await self.get_bus_data()
        if bus_data:
            await self.send(text_data=json.dumps({
                'type': 'location_update',
                'data': bus_data
            }))

    async def disconnect(self, close_code):
        # Leave bus group
        await self.channel_layer.group_discard(
            self.bus_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'location_update':
            # Driver is sending location update
            location_data = data.get('data', {})
            
            # Broadcast to all connected clients
            await self.channel_layer.group_send(
                self.bus_group_name,
                {
                    'type': 'location_message',
                    'data': location_data
                }
            )
        
        elif message_type == 'status_update':
            # Update bus status
            status_data = data.get('data', {})
            await self.channel_layer.group_send(
                self.bus_group_name,
                {
                    'type': 'status_message',
                    'data': status_data
                }
            )

    async def location_message(self, event):
        # Send location update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'data': event['data']
        }))

    async def status_message(self, event):
        # Send status update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'data': event['data']
        }))

    @database_sync_to_async
    def get_bus_data(self):
        try:
            bus = Bus.objects.get(id=self.bus_id)
            if bus.current_location:
                return {
                    'bus_id': bus.id,
                    'bus_number': bus.bus_number,
                    'latitude': bus.latitude,
                    'longitude': bus.longitude,
                    'speed': bus.current_speed,
                    'status': bus.status,
                    'timestamp': bus.last_updated.isoformat()
                }
        except Bus.DoesNotExist:
            pass
        return None

class StudentTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.student_id = self.scope['url_route']['kwargs']['student_id']
        self.student_group_name = f'student_{self.student_id}'
        
        # Verify student exists
        student = await self.get_student()
        if not student:
            await self.close()
            return
        
        # Get assigned bus
        bus = await self.get_student_bus(student)
        if not bus:
            await self.close()
            return
        
        self.bus_id = bus.id
        self.bus_group_name = f'bus_{self.bus_id}'
        
        # Join both student and bus groups
        await self.channel_layer.group_add(
            self.student_group_name,
            self.channel_name
        )
        
        await self.channel_layer.group_add(
            self.bus_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current bus location
        bus_data = await self.get_bus_data()
        if bus_data:
            await self.send(text_data=json.dumps({
                'type': 'location_update',
                'data': bus_data
            }))

    async def disconnect(self, close_code):
        # Leave groups
        await self.channel_layer.group_discard(
            self.student_group_name,
            self.channel_name
        )
        await self.channel_layer.group_discard(
            self.bus_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Students typically don't send data, just receive
        pass

    async def location_message(self, event):
        # Forward bus location updates to student
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'data': event['data']
        }))

    async def notification_message(self, event):
        # Send notifications to student
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))

    @database_sync_to_async
    def get_student(self):
        try:
            return StudentProfile.objects.get(id=self.student_id)
        except StudentProfile.DoesNotExist:
            return None

    @database_sync_to_async
    def get_student_bus(self, student):
        return student.assigned_bus

    @database_sync_to_async
    def get_bus_data(self):
        try:
            bus = Bus.objects.get(id=self.bus_id)
            if bus.current_location:
                return {
                    'bus_id': bus.id,
                    'bus_number': bus.bus_number,
                    'latitude': bus.latitude,
                    'longitude': bus.longitude,
                    'speed': bus.current_speed,
                    'status': bus.status,
                    'timestamp': bus.last_updated.isoformat()
                }
        except Bus.DoesNotExist:
            pass
        return None