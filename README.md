# homeassistant-hacs-xbox
- Follow this tutorial https://github.com/OpenXbox/xbox-webapi-python

# HACS - Recommended
- Have HACS installed, this will allow you to easily update.
- Add https://github.com/leonardoPimentelns/homeassistant-hacs-xbox as a custom repository with Type: Integration
- Click Install under "Custom xbox" integration.
- Restart Home-Assistant.

Example configuration.yaml:
```yaml
sensor:
  - platform: custom_xbox
    client_id: 'YOUR CLIENT ID HERE'
    client_secret: 'YOUR CLIENT SECRET HERE'
    tokens: 'PATH TOKEN HERE'
 ```
