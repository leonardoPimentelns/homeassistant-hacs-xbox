"""Platform for sensor integration."""
from __future__ import annotations

import voluptuous as vol
from datetime import timedelta
import pandas as pd
from homeassistant.components.sensor import (
    SensorEntity
)

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval

import sys
from aiohttp import ClientSession
from xbox.webapi.api.client import XboxLiveClient
from xbox.webapi.authentication.manager import AuthenticationManager
from xbox.webapi.authentication.models import OAuth2TokenResponse
from xbox import *

CLIENT_ID = 'client_id'
CLIENT_SECRET = 'client_secret'
TOKENS = 'tokens'
UPDATE_FREQUENCY = timedelta(seconds=5)
ICON = "mdi:microsoft-xbox"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CLIENT_ID): cv.string,
        vol.Required(CLIENT_SECRET): cv.string,
        vol.Required(TOKENS): cv.string
    }
)
def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    add_entities([CustomXbox(config)])


class CustomXbox(SensorEntity):
    """Representation of a Sensor."""
    def __init__(self,config):
        self._attr_name = "Xbox"
        self.results = None
        self.config = config
    @property
    def should_poll(self):
        """Return False as this entity has custom polling."""
        return False
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON
    async def async_added_to_hass(self):
            """Start custom polling."""


            @callback
            def async_update(event_time=None):
                """Update the entity."""
                self.async_schedule_update_ha_state(True)


            async_track_time_interval(self.hass, async_update, UPDATE_FREQUENCY)

    async def async_update(self):
         self.results =  await async_main(self.config )
         self._attr_native_value =  None


    @property
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        self._attributes = {
            "results": self.results
        }
        return  self._attributes



async def async_main(config):
    tokens_file = config[TOKENS] # replace with path in auth scrip or just paste file with tokens here
    async with ClientSession() as session:
        auth_mgr = AuthenticationManager(
              session, CLIENT_ID, CLIENT_SECRET, "")

        try:
            with open(tokens_file, mode="r") as f:
                  tokens = f.read()
            auth_mgr.oauth = OAuth2TokenResponse.parse_raw(tokens)
        except FileNotFoundError:
            print(f'File {tokens_file} isn`t found or it doesn`t contain tokens!')
            exit(-1)

        try:
              await auth_mgr.refresh_tokens()
        except ClientResponseError:
              print("Could not refresh tokens")
              sys.exit(-1)

        with open(tokens_file, mode="w") as f:
              f.write(auth_mgr.oauth.json())
        print(f'Refreshed tokens in {tokens_file}!')
        xbl_client = XboxLiveClient(auth_mgr)





        boxArt = None
        title_name = None
        title_id = None
        xuid = None
        console_id = None

        get_xuid= await xbl_client.presence.get_presence_own()
        get_xuid = pd.DataFrame(get_xuid)
        xuid = get_xuid[1][0]

        get_console_id =  await xbl_client.smartglass.get_console_list()
        get_console_id = pd.DataFrame(get_console_id)
        console_id =  get_console_id[1][1][0].id

        presence = await xbl_client.people.get_friends_own_batch([xuid])
        presence = pd.DataFrame(presence)
        for item in presence[1][0][0].presence_details:
            if (item.is_primary == True):
                title_id =item.title_id
                title_name =item.presence_text

        get_title_info = await xbl_client.titlehub.get_title_info(title_id)
        get_title_info = pd.DataFrame(get_title_info)

        for item in get_title_info[1][1][0].images:
            if (item.type == 'BoxArt'):
                boxArt =item.url
            if (item.type == 'Tile'):
                  boxArt =item.url

        description = get_title_info[1][1][0].detail.short_description



        get_storage_devices = await xbl_client.smartglass.get_storage_devices(console_id)
        get_storage_devices = pd.DataFrame(get_storage_devices)

        get_installed_apps = await xbl_client.smartglass.get_installed_apps()
        get_installed_apps = pd.DataFrame(get_installed_apps)


        total_space_bytes = round(get_storage_devices[1][1][0].total_space_bytes/1024.0**3)
        free_space_bytes = round(get_storage_devices[1][1][0].free_space_bytes/1024.0**3)




        attributes = {
        "title_name": title_name,
        "title_id": title_id,
        "description": description,
        "boxArt": boxArt,
        "free_space_bytes": free_space_bytes,
        "total_space_bytes": total_space_bytes,

        }
        return  attributes
