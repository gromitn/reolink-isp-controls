# Reolink ISP custom integration starter

This is a lean Home Assistant custom integration starter extracted from the desktop Reolink ISP Tool logic.

## Scope of this starter

- UI config flow
- Direct camera connection over Reolink CGI
- `select` entity for **Exposure**
- `number` entities for:
  - Gain Min
  - Gain Max
  - Shutter Min
  - Shutter Max
- Preserves the proven staging workaround for locked shutter/gain writes
- Polls current ISP back from the camera so Home Assistant reflects what the camera actually saved

## Intentionally left out for v1

- backup / restore
- the wider ISP surface area
- update checker
- desktop UI concepts
- official Reolink integration coupling

## Install

1. Copy `custom_components/reolink_isp` into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Add **Reolink ISP** from Settings -> Devices & Services.
4. Enter the camera host, protocol, username and password.

## Notes

- This starter talks to the camera directly.
- HTTPS certificate verification is optional because many Reolink cameras use self-signed certs.
- `channel` is included but defaults to `0`.
- The number entities are only available when the current exposure mode supports them:
  - Gain: `Manual`
  - Shutter: `Manual` or `Anti-Smearing`
