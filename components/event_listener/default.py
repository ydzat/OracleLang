"""
OracleLang Event Listener Component
Handles message events for divination commands
"""
from __future__ import annotations

from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import events, context
from langbot_plugin.api.entities.builtin.platform import message as platform_message


class DefaultEventListener(EventListener):
    """Default event listener for OracleLang plugin"""

    async def initialize(self):
        """Initialize event listener and register event handlers"""
        await super().initialize()
        
        # Register handler for person (private) messages
        @self.handler(events.PersonMessageReceived)
        async def on_person_message(event_context: context.EventContext):
            """Handle private messages"""
            await self._handle_message(event_context)
        
        # Register handler for group messages
        @self.handler(events.GroupMessageReceived)
        async def on_group_message(event_context: context.EventContext):
            """Handle group messages"""
            await self._handle_message(event_context)
    
    async def _handle_message(self, event_context: context.EventContext):
        """
        Handle incoming message event
        
        Args:
            event_context: The event context containing message information
        """
        try:
            # Get message text
            msg_text = ""
            for element in event_context.event.message_chain:
                if isinstance(element, platform_message.Plain):
                    msg_text += element.text
            
            # Skip if no text
            if not msg_text.strip():
                return
            
            # Get sender ID
            sender_id = event_context.event.sender_id
            
            # Process the divination message through the plugin
            response = await self.plugin.process_divination_message(msg_text, sender_id)
            
            # If we got a response, send it back
            if response:
                await event_context.reply(
                    platform_message.MessageChain([
                        platform_message.Plain(text=response)
                    ])
                )
                
                # Prevent default processing
                event_context.prevent_default()
                
        except Exception as e:
            self.ap.logger.error(f"Error handling message in OracleLang: {e}", exc_info=True)

