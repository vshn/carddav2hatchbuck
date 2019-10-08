"""
Notification to pro-actively features for un
"""
import os
import logging

from rocketchat_API.rocketchat import RocketChat


# pylint: disable=too-few-public-methods
class NotificationService:
    """
    An alerting service for unresolvable import or merge issues.
    """

    def __init__(self):
        """A RocketChat channel"""
        self.user = os.environ.get("ROCKETCHAT_USER")
        self.password = os.environ.get("ROCKETCHAT_PASS")
        self.url = os.environ.get("ROCKETCHAT_URL")
        self.service = RocketChat(self.user, self.password, server_url=self.url)
        self.channel = os.environ.get("ROCKETCHAT_CHANNEL", "hatchbuck")
        self.alias = os.environ.get("ROCKETCHAT_ALIAS", "carddav2hatchbuck")

    def send_message(self, message):
        """Send a message to the RocketChat channel"""
        response = self.service.chat_post_message(
            message, channel=self.channel, alias=self.alias
        )
        logging.debug(response.json())
