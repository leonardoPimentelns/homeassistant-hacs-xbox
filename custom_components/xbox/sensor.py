"""Platform for sensor integration."""
from __future__ import annotations
from os import truncate

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

from aiohttp import ClientSession,ClientResponseError
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
    try:
       add_entities([CustomXbox(config)])
    except FileNotFoundError:
          print('opa')



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
         """Start async_update."""
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
              session, config[CLIENT_ID], config[CLIENT_SECRET], "")

        try:
            with open(tokens_file, mode="r") as f:
                  tokens = f.read()
            auth_mgr.oauth = OAuth2TokenResponse.parse_raw(tokens)
        except FileNotFoundError:
            print(f'File {tokens_file} isn`t found or it doesn`t contain tokens!')

        try:
            await auth_mgr.refresh_tokens()
        except ClientResponseError:
              print("Could not refresh tokens")

        with open(tokens_file, mode="w") as f:
              f.write(auth_mgr.oauth.json())
        print(f'Refreshed tokens in {tokens_file}!')

        xbl_client = XboxLiveClient(auth_mgr)
        
        state_presence = None
        xuid = None
        console_id = None
        total_space = None
        free_space = None
        preferred_color= None
        title_id = None
        title_name = None
        title_box_art = None
        title_description= None
       
        
     
        
        get_xuid= await xbl_client.presence.get_presence_own()
        get_xuid = pd.DataFrame(get_xuid)
        xuid = get_xuid[1][0]
        state_presence = get_xuid[1][1]
        
        presence = await xbl_client.people.get_friends_own_batch([xuid])
        presence = pd.DataFrame(presence)
        
        preferred_color = presence[1][0][0].preferred_color
        
        
        get_console_id =  await xbl_client.smartglass.get_console_list()
        get_console_id = pd.DataFrame(get_console_id)
        console_id =  get_console_id[1][1][0].id
        
        get_storage_devices = await xbl_client.smartglass.get_storage_devices(console_id)
        get_storage_devices = pd.DataFrame(get_storage_devices)
        
        total_space = round(get_storage_devices[1][1][0].total_space_bytes/1024.0**3)
        free_space = round(get_storage_devices[1][1][0].free_space_bytes/1024.0**3)
        
        get_installed_apps = await xbl_client.smartglass.get_installed_apps()
        get_installed_apps = pd.DataFrame(get_installed_apps)
       
     



        if (state_presence != 'Offline'):
            for item in presence[1][0][0].presence_details:
                if (item.is_primary == True):
                    title_id =item.title_id 
                    
                    
            get_title_info = await xbl_client.titlehub.get_title_info(title_id)
            get_title_info = pd.DataFrame(get_title_info)
          
          
            for item in get_title_info[1][1][0].images:
                if (item.type == 'BoxArt'):
                    title_box_art =item.url
                if (item.type == 'Tile'):
                    title_box_art =item.url
              
            title_name = get_title_info[1][1][0].name
            title_description = get_title_info[1][1][0].detail.short_description




        attributes = {
        "state_presence": state_presence,
        "xuid": xuid,
        "console_id": console_id,
        "total_space": total_space,
        "free_space": free_space,
        "preferred_color": preferred_color,
        "title_id": title_id,
        "title_name": title_name,
        "title_box_art": title_box_art,
        "title_description": title_description,
       

        }
        return  attributes

