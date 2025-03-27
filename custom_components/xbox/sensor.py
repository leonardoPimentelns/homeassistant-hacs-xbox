from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiofiles
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

from xbox.webapi.api.provider.catalog.models import FieldsTemplate, PlatformType
from xbox.webapi.api.client import XboxLiveClient
from xbox.webapi.authentication.manager import AuthenticationManager
from xbox.webapi.authentication.models import OAuth2TokenResponse
from xbox.webapi.common.signed_session import SignedSession

_LOGGER = logging.getLogger(__name__)

CLIENT_ID = 'client_id'
CLIENT_SECRET = 'client_secret'
TOKENS_FILE = 'tokens'
UPDATE_INTERVAL = timedelta(seconds=300)

ICON = "mdi:microsoft-xbox"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CLIENT_ID): cv.string,
    vol.Required(CLIENT_SECRET): cv.string,
    vol.Required(TOKENS_FILE): cv.string
})

class XboxDataCoordinator:
    """Coordinator para gerenciar dados da Xbox API."""
    
    def __init__(self, hass, config):
        self.hass = hass
        self.config = config
        self.data = {}
        self.auth_mgr = None
        self.xbl_client = None
        self._session = None
        
    async def async_initialize(self):
        """Inicializar autenticação e cliente."""
        try:
            # Criar sessão SSL em thread separada
            self._session = await self.hass.async_add_executor_job(SignedSession)
            
            self.auth_mgr = AuthenticationManager(
                self._session,
                self.config[CLIENT_ID],
                self.config[CLIENT_SECRET],
                ""
            )
            await self.load_tokens()
            self.xbl_client = XboxLiveClient(self.auth_mgr)
            await self.async_update_data()
        except Exception as e:
            _LOGGER.error("Falha na inicialização: %s", str(e))
            raise

    async def load_tokens(self):
        """Carregar tokens de forma assíncrona."""
        try:
            async with aiofiles.open(self.config[TOKENS_FILE], mode='r') as f:
                tokens = await f.read()
            self.auth_mgr.oauth = OAuth2TokenResponse.parse_raw(tokens)
            await self.auth_mgr.refresh_tokens()
            await self.save_tokens()
        except FileNotFoundError:
            _LOGGER.error("Arquivo de tokens não encontrado: %s", self.config[TOKENS_FILE])
            raise
        except Exception as e:
            _LOGGER.error("Falha ao atualizar tokens: %s", str(e))
            raise

    async def save_tokens(self):
        """Salvar tokens de forma assíncrona."""
        try:
            async with aiofiles.open(self.config[TOKENS_FILE], mode='w') as f:
                await f.write(self.auth_mgr.oauth.json())
        except Exception as e:
            _LOGGER.error("Falha ao salvar tokens: %s", str(e))

    async def async_update_data(self):
        """Atualizar todos os dados da API."""
        try:
            self.data = await self.fetch_all_data()
        except Exception as e:
            _LOGGER.error("Falha na atualização de dados: %s", str(e))

    async def fetch_all_data(self) -> dict:
        """Buscar e combinar todos os dados."""
        data = {}
        
        # Dados do usuário
        data.update(await self.fetch_user_data())
        
        # Dados do console
        data.update(await self.fetch_console_data())
        
        # Dados de jogos
        data.update(await self.fetch_game_data())
        
        return data

    async def fetch_user_data(self) -> dict:
        """Buscar dados do usuário."""
        try:
            xuid = await self._get_xuid()
            presence = await self.xbl_client.people.get_friends_own_batch([xuid])
            return self.parse_user_data(presence)
        except Exception as e:
            _LOGGER.error("Falha ao buscar dados do usuário: %s", str(e))
            return {}

    async def _get_xuid(self) -> str:
        """Obter XUID do usuário atual."""
        presence = await self.xbl_client.presence.get_presence_own()
        return presence.xuid

    def parse_user_data(self, presence) -> dict:
        """Processar dados de presença do usuário."""
        if not presence.people:
            return {}
            
        user = presence.people[0]
        return {
            "state_presence": getattr(user, 'state', 'desconhecido'),
            "gamertag": user.gamertag,
            "display_pic_raw": user.display_pic_raw,
            "primary_color": user.preferred_color.primary_color,
            "secondary_color": user.preferred_color.secondary_color,
            "xuid": user.xuid
        }

    async def fetch_console_data(self) -> dict:
        """Buscar dados do console."""
        try:
            console_list = await self.xbl_client.smartglass.get_console_list()
            if not console_list.result:
                _LOGGER.warning("Nenhum console Xbox encontrado")
                return {}

            console = console_list.result[0]
            storage = await self.get_storage_data(console.id)
            
            return {
                "console_type": console.console_type,
                "console_power_state": console.power_state,
                "console_id": console.id,
                "console_name": console.name,
                "total_space": storage.get('total'),
                "free_space": storage.get('free')
            }
        except Exception as e:
            _LOGGER.error("Falha ao buscar dados do console: %s", str(e))
            return {}

    async def get_storage_data(self, console_id: str) -> dict:
        """Obter dados de armazenamento."""
        try:
            storage = await self.xbl_client.smartglass.get_storage_devices(console_id)
            if storage.result:
                return {
                    'total': round(storage.result[0].total_space_bytes / 1024**3, 1),
                    'free': round(storage.result[0].free_space_bytes / 1024**3, 1)
                }
            return {}
        except Exception as e:
            _LOGGER.error("Falha ao obter dados de armazenamento: %s", str(e))
            return {}

    async def fetch_game_data(self) -> dict:
        """Buscar dados relacionados a jogos."""
        game_data = {}
        
        try:
            # Jogo atual
            game_data.update(await self.get_current_game_info())
            
            # Biblioteca de jogos
            game_data['my_games'] = await self.get_game_library()
        except Exception as e:
            _LOGGER.error("Falha ao buscar dados de jogos: %s", str(e))

        return game_data

    async def get_current_game_info(self) -> dict:
        """Obter informações do jogo atual."""
        try:
            title_info = {}
            presence = await self.xbl_client.presence.get_presence_own()
            
            if presence.state != 'Offline' and presence.title_id:
                title_data = await self.xbl_client.titlehub.get_title_info(presence.title_id)
                title = title_data.titles[0]
                
                title_info = {
                    "title_id": presence.title_id,
                    "title_name": title.name,
                    "title_publisher_name": title.detail.publisher_name,
                    "title_description": title.detail.short_description,
                    "min_age": title.detail.min_age,
                    "current_achievements": title.achievement.current_achievements,
                    "total_achievements": title.achievement.total_achievements,
                    "current_gamerscore": title.achievement.current_gamerscore,
                    "total_gamerscore": title.achievement.total_gamerscore,
                    "progress_percentage": title.achievement.progress_percentage
                }
                
                # Processar imagens
                for img in title.images:
                    if img.type == 'BoxArt':
                        title_info["title_box_art"] = img.url.replace("http://", "https://")
                    elif img.type == 'Screenshot':
                        title_info.setdefault("screenshots", []).append(img.url.replace("http://", "https://"))

            return title_info
        except Exception as e:
            _LOGGER.error("Falha ao obter info do jogo atual: %s", str(e))
            return {}

    async def get_game_library(self) -> list:
        """Obter biblioteca de jogos."""
        try:
            apps = await self.xbl_client.smartglass.get_installed_apps()
            games = [app for app in apps.result if app.is_game]
            
            game_list = []
            for game in games:
                game_list.append({
                    "name": game.name,
                    "title_id": game.title_id,
                    "product_id": game.one_store_product_id
                })
                
            return game_list
        except Exception as e:
            _LOGGER.error("Falha ao obter biblioteca de jogos: %s", str(e))
            return []

class XboxBaseSensor(SensorEntity):
    """Classe base para sensores Xbox."""
    
    def __init__(self, coordinator, sensor_type):
        self._coordinator = coordinator
        self._sensor_type = sensor_type
        self._attr_unique_id = f"xbox_{sensor_type}"
        self._attr_icon = ICON
        self._attr_entity_registry_enabled_default = True

    @property
    def name(self):
        return f'Xbox {self._sensor_type.replace("_", " ").title()}'

    async def async_update(self):
        await self._coordinator.async_update_data()

    @property
    def extra_state_attributes(self):
        return self._coordinator.data

class XboxUserSensor(XboxBaseSensor):
    """Sensor para informações do usuário Xbox."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "user_info")

    @property
    def state(self):
        return self._coordinator.data.get('gamertag', 'Desconhecido')

    @property
    def extra_state_attributes(self):
        return {
            k: self._coordinator.data.get(k)
            for k in [
                'gamertag', 'display_pic_raw', 'primary_color',
                'secondary_color', 'state_presence', 'xuid'
            ]
        }

class XboxCurrentGameSensor(XboxBaseSensor):
    """Sensor para jogo atual do Xbox."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "current_game")

    @property
    def state(self):
        return self._coordinator.data.get('title_name', 'Nenhum jogo em execução')

    @property
    def extra_state_attributes(self):
        return {
            k: self._coordinator.data.get(k)
            for k in [
                'title_id', 'title_name', 'title_publisher_name',
                'title_description', 'min_age', 'title_box_art',
                'current_achievements', 'total_achievements',
                'current_gamerscore', 'total_gamerscore',
                'progress_percentage', 'screenshots'
            ]
        }

class XboxDeviceSensor(XboxBaseSensor):
    """Sensor para informações do dispositivo Xbox."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "device_info")

    @property
    def state(self):
        return self._coordinator.data.get('console_name', 'Console não encontrado')

    @property
    def extra_state_attributes(self):
        return {
            k: self._coordinator.data.get(k)
            for k in [
                'console_type', 'console_power_state',
                'console_id', 'console_name',
                'total_space', 'free_space'
            ]
        }

class XboxGameLibrarySensor(XboxBaseSensor):
    """Sensor para biblioteca de jogos do Xbox."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "game_library")

    @property
    def state(self):
        games = self._coordinator.data.get('my_games', [])
        return f"{len(games)} jogos na biblioteca"

    @property
    def extra_state_attributes(self):
        return {
            'games': self._coordinator.data.get('my_games', [])
        }

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Configurar a plataforma de sensores."""
    coordinator = XboxDataCoordinator(hass, config)
    
    try:
        await coordinator.async_initialize()
    except Exception as e:
        _LOGGER.error("Falha na inicialização do coordenador Xbox: %s", str(e))
        return

    async_track_time_interval(
        hass,
        coordinator.async_update_data,
        UPDATE_INTERVAL
    )

    sensors = [
        XboxUserSensor(coordinator),
        XboxCurrentGameSensor(coordinator),
        XboxDeviceSensor(coordinator),
        XboxGameLibrarySensor(coordinator)
    ]
    
    async_add_entities(sensors)
