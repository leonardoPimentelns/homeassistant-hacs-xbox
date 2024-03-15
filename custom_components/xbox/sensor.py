"""Platform for sensor integration."""
from __future__ import annotations
from os import truncate

import voluptuous as vol
from datetime import timedelta
import pandas as pd
from homeassistant.components.sensor import (
    SensorEntity
)
from xbox.webapi.api.provider.catalog.models import AlternateIdType, FieldsTemplate
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval

from aiohttp import ClientSession,ClientResponseError
from xbox.webapi.api.client import XboxLiveClient
from xbox.webapi.common.signed_session import SignedSession
from xbox.webapi.authentication.manager import AuthenticationManager
from xbox.webapi.authentication.models import OAuth2TokenResponse
from xbox.webapi.api.provider.catalog.models import (
    AlternateIdType,
    FieldsTemplate,
    PlatformType,
)

from xbox import *



CLIENT_ID = 'client_id'
CLIENT_SECRET = 'client_secret'
TOKENS = 'tokens'
UPDATE_FREQUENCY = timedelta(seconds=10)
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
        print('error')



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
    async with SignedSession() as session:
        auth_mgr = AuthenticationManager(session, config[CLIENT_ID], config[CLIENT_SECRET], "")

        try:
            with open(tokens_file) as f:
                tokens = f.read()
            # Assign gathered tokens
            auth_mgr.oauth = OAuth2TokenResponse.model_validate_json(tokens)
        except FileNotFoundError as e:
            print(
                f"File {tokens_file} isn`t found or it doesn`t contain tokens! err={e}"
            )
           

        try:
            await auth_mgr.refresh_tokens()
        except HTTPStatusError as e:
            print(
                f"""
                Could not refresh tokens from {tokens_file}, err={e}\n
                You might have to delete the tokens file and re-authenticate 
                if refresh token is expired  """
          
            )
           

        # Save the refreshed/updated tokens
        with open(tokens_file, mode="w") as f:
            f.write(auth_mgr.oauth.json())
        print(f"Refreshed tokens in {tokens_file}!")
        xbl_client = XboxLiveClient(auth_mgr)
        
        state_presence = None
        xuid = None
        gamertag = None
        display_pic_raw = None
        console_type = None
        console_id = None
        console_name = None
        total_space = None
        free_space = None
        primary_color= None
        secondary_color= None
        title_id = None
        title_name = 'Xbox'
        title_publisher_name= 'Microsoft'
        title_box_art = None
        title_description= 'Xbox Game Pass Play new games on day one. Plus, enjoy hundreds of high-quality games with friends on console, PC, or cloud. With games added all the time, there’s always something new to play.'
        min_age = None
        title_trailer= None
        big_id=[]
        array_screenshot=[]
        current_achievements = None
        total_achievements = None
        current_gamerscore = None
        total_gamerscore = None
        progress_percentage = None
        my_games =[]
        my_games_name = []
        my_games_box_art = []
       
        
     
        
        get_xuid= await xbl_client.presence.get_presence_own()
        xuid = get_xuid.xuid
        state_presence = get_xuid.state
        
        
        presence = await xbl_client.people.get_friends_own_batch([xuid])
        gamertag = presence.people[0].gamertag
        primary_color = presence.people[0].preferred_color.primary_color
        secondary_color = presence.people[0].preferred_color.secondary_color
        display_pic_raw = presence.people[0].display_pic_raw
        title_box_art = display_pic_raw
        
        get_console =  await xbl_client.smartglass.get_console_list()
        
        if get_console is not None and len(get_console.result) > 0:
            console_id = get_console.result[0].id
            console_name = get_console.result[0].name
            console_type = get_console.result[0].console_type
            get_storage_devices = await xbl_client.smartglass.get_storage_devices(console_id)
            total_space = round(get_storage_devices.result[0].total_space_bytes/1024.0**3)
            free_space = round(get_storage_devices.result[0].free_space_bytes/1024.0**3)
        else:
            print("Please, register your xbox console")
            
        
        
        
        get_installed_apps = await xbl_client.smartglass.get_installed_apps()
        
        
        apps = await xbl_client.smartglass.get_installed_apps()
        games = {
            game.one_store_product_id: game
            for game in apps.result
            if game.is_game and game.title_id
        }

        app_details = await xbl_client.catalog.get_products(
            games.keys(),
            FieldsTemplate.BROWSE,
        )

        images = {
            prod.product_id: prod.localized_properties[0].images
            for prod in app_details.products
        }
        
       
        for game_id, game in games.items():
            name = game.name
            my_games_name.append(name)
        
        for ima, image in images.items():
            for i in image:
                if i.image_purpose =='BoxArt':
                    box_art= i.uri
                    my_games_box_art.append(box_art)
                  
           
                    
        
        for i in range(len(my_games_name)):
            dados = {'name':my_games_name[i],'url':my_games_box_art[i]}
            my_games.append(dados)
          
        



        if (state_presence != 'Offline'):
            for item in presence.people[0].presence_details:
                if (item.is_primary == True):
                    title_id =item.title_id 
                    
                    
            get_title_info = await xbl_client.titlehub.get_title_info(title_id)
           
          
           
           
         
            
            current_achievements = get_title_info.titles[0].achievement.current_achievements
            total_achievements = get_title_info.titles[0].achievement.total_achievements
            current_gamerscore = get_title_info.titles[0].achievement.current_gamerscore
            total_gamerscore = get_title_info.titles[0].achievement.total_gamerscore
            progress_percentage = get_title_info.titles[0].achievement.progress_percentage
            
            
            for item in get_title_info.titles[0].images:
                
               
                if (item.type == 'BoxArt'):
                    url_string = item.url.replace("http://", "https://")
                    title_box_art =url_string
                        
                if (item.type == 'Tile'):
                    url_string = item.url.replace("http://", "https://")
                    title_box_art = url_string
                    
                if (item.type == 'Screenshot'):
                    url_string = item.url.replace("http://", "https://")
                    screenshot = {'url': url_string}
                   
                    array_screenshot.append(screenshot)
                    array_screenshot = list({d['url']: d for d in array_screenshot}.values())
                    
 
            title_name = get_title_info.titles[0].name
            title_publisher_name =  get_title_info.titles[0].detail.publisher_name
            min_age =  get_title_info.titles[0].detail.min_age
            
            title_description = get_title_info.titles[0].detail.short_description
            
            get_big_id = await xbl_client.catalog.product_search(title_name,PlatformType.XBOX)
            
            for item in get_big_id.results:
                if item.product_family_name == 'Games':
                    big_id.append(item.products[0].product_id)
                
            title_trailer = await xbl_client.catalog.get_products(big_id,FieldsTemplate.DETAILS)
            
            if len(title_trailer.products[0].localized_properties[0].videos) > 0:
                title_trailer = title_trailer.products[0].localized_properties[0].videos[0].uri
                title_trailer = title_trailer.replace("http:","")
            else:
                title_trailer = None



        attributes = {
        "state_presence": state_presence,
        "xuid": xuid,
        "gamertag":gamertag,
        "display_pic_raw": display_pic_raw,
        "console_type": console_type,
        "console_id": console_id,
        "console_name":console_name,
        "total_space": total_space,
        "free_space": free_space,
        "primary_color": primary_color,
        "secondary_color": secondary_color,
        "title_id": title_id,
        "title_name": title_name,
        "title_publisher_name": title_publisher_name,
        "title_description": title_description,
        "min_age": min_age,
        "title_box_art": title_box_art,
        "title_trailer": title_trailer,
        "screenshot": array_screenshot,
        "current_achievements": current_achievements,
        "total_achievements": total_achievements,
        "current_gamerscore": current_gamerscore,
        "total_gamerscore": total_gamerscore,
        "progress_percentage": progress_percentage,
        'my_games': my_games
            
            
            
        

        }
    
        return  attributes
