"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant import util
import sys
import pandas as pd
from datetime import timedelta
from aiohttp import ClientSession
from xbox.webapi.api.client import XboxLiveClient
from xbox.webapi.authentication.manager import AuthenticationManager
from xbox.webapi.authentication.models import OAuth2TokenResponse
from xbox import *

client_id = '590c180c-ec11-451b-b2b5-1d785d77403a'
client_secret = 'mYt8Q~B2PGEUn.k.xuvftMUG_HmX6R-sqs3HwaAY'
UPDATE_FREQUENCY = timedelta(seconds=1)
TITLE_ID = None


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    add_entities([CustomXbox()])


class CustomXbox(SensorEntity):
    """Representation of a Sensor."""
    def __init__(self):
        self._attr_name = "Xbox"
        self.results = None

    @util.Throttle(UPDATE_FREQUENCY)
    async def async_update(self):
        """Retrieve latest state."""
        self.results =  await async_main()

        self._attr_native_value =  None

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        self._attributes = {
            "results": self.results
        }
        return  self._attributes



async def async_main():
    tokens_file = "/workspaces/core/homeassistant/components/custom_xbox/tokens.json" # replace with path in auth scrip or just paste file with tokens here
    async with ClientSession() as session:
        auth_mgr = AuthenticationManager(
              session, client_id, client_secret, "")

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
        presence = await xbl_client.people.get_friends_own_batch(['2533274927773646'])
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

        description = get_title_info[1][1][0].detail.short_description



        get_storage_devices = await xbl_client.smartglass.get_storage_devices('F4001F112BC1D01F')
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
        "total_space_bytes": total_space_bytes

        }
        return  attributes