from __future__ import annotations

import asyncio
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

from xbox.webapi.api.provider.catalog.models import FieldsTemplate, PlatformType
from xbox.webapi.api.client import XboxLiveClient
from xbox.webapi.authentication.manager import AuthenticationManager
from xbox.webapi.authentication.models import OAuth2TokenResponse
from xbox.webapi.common.signed_session import SignedSession

CLIENT_ID = 'client_id'
CLIENT_SECRET = 'client_secret'
TOKENS_FILE = 'tokens'

ICON = "mdi:microsoft-xbox"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CLIENT_ID): cv.string,
    vol.Required(CLIENT_SECRET): cv.string,
    vol.Required(TOKENS_FILE): cv.string
})

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([
        XboxUserSensor(config),
        XboxCurrentGameSensor(config),
        XboxDeviceSensor(config),
        XboxGameLibrarySensor(config)
    ])

class XboxUserSensor(SensorEntity):
    def __init__(self, config):
        self._state = None
        self._attributes = None
        self._config = config

    @property
    def name(self):
        return 'Xbox User Info'

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        _, attributes = await async_main(self._config)
        self._state = attributes.get('gamertag')
        self._attributes = {
            "gamertag": attributes.get('gamertag'),
            "display_pic_raw": attributes.get('display_pic_raw'),
            "primary_color": attributes.get('primary_color'),
            "secondary_color": attributes.get('secondary_color'),
            "state_presence": attributes.get('state_presence')
        }
class XboxCurrentGameSensor(SensorEntity):
    def __init__(self, config):
        self._state = None
        self._attributes = None
        self._config = config

    @property
    def name(self):
        return 'Xbox Current Game'

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        _, attributes = await async_main(self._config)
        
        # Certifique-se de pegar o valor correto para o título
        title_name = attributes.get('title_name')  # Isso pode estar vazio se a API não retornar o título esperado
        if not title_name: 
            # Caso o título não tenha sido encontrado, defina um valor padrão ou tente buscar novamente
            title_name = "No game currently playing"  # ou qualquer outra lógica

        self._state = title_name
        
        self._attributes = {
            "title_id": attributes.get('title_id'),
            "title_publisher_name": attributes.get('title_publisher_name'),
            "title_description": attributes.get('title_description'),
            "title_box_art": attributes.get('title_box_art'),
            "title_trailer": attributes.get('title_trailer'),
            "screenshot": attributes.get('screenshot'),
            "min_age": attributes.get("min_age"),
            "current_achievements": attributes.get('current_achievements'),
            "total_achievements": attributes.get('total_achievements'),
            "current_gamerscore": attributes.get('current_gamerscore'),
            "total_gamerscore": attributes.get('total_gamerscore'),
            "progress_percentage": attributes.get('progress_percentage'),
            "user_gamertag": attributes.get('gamertag'),
            "user_xuid": attributes.get('xuid'),
            "user_display_pic": attributes.get('display_pic_raw')
        }

class XboxDeviceSensor(SensorEntity):
    def __init__(self, config):
        self._state = "Xbox Device"
        self._attributes = None
        self._config = config

    @property
    def name(self):
        return 'Xbox Device Info'

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        _, attributes = await async_main(self._config)
        self._attributes = {
            "console_type": attributes.get('console_type'),
            "console_power_state": attributes.get('console_power_state'),
            "console_id": attributes.get('console_id'),
            "console_name": attributes.get('console_name'),
            "total_space": attributes.get('total_space'),
            "free_space": attributes.get('free_space')
        }




class XboxGameLibrarySensor(SensorEntity):
    def __init__(self, config):
        self._state = "Game Library"
        self._attributes = None
        self._config = config

    @property
    def name(self):
        return 'Xbox Game Library'

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        _, attributes = await async_main(self._config)
        self._attributes = {
            "my_games": attributes.get('my_games')
        }

# Função principal para buscar os dados da API
async def async_main(config):
    client_id = config.get(CLIENT_ID)
    client_secret = config.get(CLIENT_SECRET)
    tokens_file = config.get(TOKENS_FILE)

    async with SignedSession() as session:
        auth_mgr = AuthenticationManager(session, client_id, client_secret, "")
        try:
            with open(tokens_file) as f:
                tokens = f.read()
            auth_mgr.oauth = OAuth2TokenResponse.parse_raw(tokens)
        except FileNotFoundError as e:
            _LOGGER.error("File %s isn't found or it doesn't contain tokens! err=%s", tokens_file, e)
            return

        await auth_mgr.refresh_tokens()

        with open(tokens_file, mode="w") as f:
            f.write(auth_mgr.oauth.json())
        _LOGGER.info("Refreshed tokens in %s!", tokens_file)

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
        primary_color = None
        secondary_color = None
        title_id = None
        title_name = "Xbox"
        title_publisher_name = "Microsoft"
        title_box_art = None
        title_description = (
            "Xbox Game Pass Play new games on day one. Plus, enjoy hundreds of high-quality games with friends on console, PC, or cloud. With games added all the time, there’s always something new to play."
        )
        min_age = None
        title_trailer = None
        big_id = []
        array_screenshot = []
        current_achievements = None
        total_achievements = None
        current_gamerscore = None
        total_gamerscore = None
        progress_percentage = None
        my_games = []
        my_games_name = []
        my_games_box_art = []

        get_xuid = await xbl_client.presence.get_presence_own()
        xuid = get_xuid.xuid
        state_presence = get_xuid.state

        presence = await xbl_client.people.get_friends_own_batch([xuid])
        gamertag = presence.people[0].gamertag
        primary_color = presence.people[0].preferred_color.primary_color
        secondary_color = presence.people[0].preferred_color.secondary_color
        display_pic_raw = presence.people[0].display_pic_raw
        title_box_art = display_pic_raw

        get_console = await xbl_client.smartglass.get_console_list()

        if get_console and len(get_console.result) > 0:
            console_id = get_console.result[0].id
            console_power_state = get_console.result[0].power_state

            console_name = get_console.result[0].name
            console_type = get_console.result[0].console_type
            get_storage_devices = await xbl_client.smartglass.get_storage_devices(console_id)
            total_space = round(get_storage_devices.result[0].total_space_bytes / 1024.0 ** 3)
            free_space = round(get_storage_devices.result[0].free_space_bytes / 1024.0 ** 3)
        else:
            print("Please, register your Xbox console")
            return

        get_installed_apps = await xbl_client.smartglass.get_installed_apps()

        apps = await xbl_client.smartglass.get_installed_apps()
        games = {
            game.one_store_product_id: game
            for game in apps.result
            if game.is_game and game.title_id
        }

        app_details = None
        if games:
            app_details = await xbl_client.catalog.get_products(
                list(games.keys()),
                FieldsTemplate.BROWSE,
            )

        if app_details:
            images = {
                prod.product_id: prod.localized_properties[0].images
                for prod in app_details.products
            }

            for game_id, game in games.items():
                name = game.name
                my_games_name.append(name)

            for ima, image in images.items():
                for i in image:
                    if i.image_purpose == 'BoxArt':
                        box_art = i.uri
                        my_games_box_art.append(box_art)

            for i in range(len(my_games_name)):
                data = {'name': my_games_name[i], 'url': my_games_box_art[i]}
                my_games.append(data)

        if state_presence != 'Offline':
            for item in presence.people[0].presence_details:
                if item.is_primary:
                    title_id = item.title_id

            if title_id:
                get_title_info = await xbl_client.titlehub.get_title_info(title_id)

                current_achievements = get_title_info.titles[0].achievement.current_achievements
                total_achievements = get_title_info.titles[0].achievement.total_achievements
                current_gamerscore = get_title_info.titles[0].achievement.current_gamerscore
                total_gamerscore = get_title_info.titles[0].achievement.total_gamerscore
                progress_percentage = get_title_info.titles[0].achievement.progress_percentage

                for item in get_title_info.titles[0].images:
                    if item.type == 'BoxArt':
                        url_string = item.url.replace("http://", "https://")
                        title_box_art = url_string
                    if item.type == 'Tile':
                        url_string = item.url.replace("http://", "https://")
                        title_box_art = url_string
                    if item.type == 'Screenshot':
                        url_string = item.url.replace("http://", "https://")
                        screenshot = {'url': url_string}
                        array_screenshot.append(screenshot)
                        array_screenshot = list({d['url']: d for d in array_screenshot}.values())

                title_name = get_title_info.titles[0].name
                title_publisher_name = get_title_info.titles[0].detail.publisher_name
                min_age = get_title_info.titles[0].detail.min_age
                title_description = get_title_info.titles[0].detail.short_description

                get_big_id = await xbl_client.catalog.product_search(title_name, PlatformType.XBOX)

                for item in get_big_id.results:
                    if item.product_family_name == 'Games':
                        big_id.append(item.products[0].product_id)

                if big_id:
                    title_trailer = await xbl_client.catalog.get_products(big_id, FieldsTemplate.DETAILS)

                    if len(title_trailer.products[0].localized_properties[0].videos) > 0:
                        title_trailer = title_trailer.products[0].localized_properties[0].videos[0].uri
                        title_trailer = title_trailer.replace("http:", "")
                    else:
                        title_trailer = None

        attributes = {
            "state_presence": state_presence,
            "xuid": xuid,
            "gamertag": gamertag,
            "display_pic_raw": display_pic_raw,
            "console_type": console_type,
            "console_power_state" : console_power_state,
            "console_id": console_id,
            "console_name": console_name,
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

        return console_power_state, attributes
