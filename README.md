# Reolink ISP Controls

A lean Home Assistant custom integration for advanced Reolink ISP controls that are not exposed cleanly in the official integration, with a focus on shutter and gain control.

This integration talks directly to the camera over the Reolink CGI API and is intended as a small companion integration, not a replacement for the official Reolink integration.

## Current scope

This integration currently provides:

- UI config flow
- Direct camera connection over Reolink CGI
- `select` entity for **Exposure**
- `number` entities for:
  - **Gain Min**
  - **Gain Max**
  - **Shutter Min**
  - **Shutter Max**
- Device-level custom action **`reolink_isp.apply_settings`** for atomic multi-setting writes
- Read-back polling so Home Assistant reflects what the camera actually saved
- The proven staged workaround for locked shutter and gain changes on affected firmware

## Why this exists

Some Reolink cameras and firmware combinations support ISP settings such as shutter and gain through the CGI API, but do not expose them properly in the normal app or web UI.

This integration is designed to expose just those useful controls in Home Assistant, while leaving the broader camera feature set to the official Reolink integration.

## Current behavior

- **Exposure**
  - Available modes include the camera-supported exposure options returned by the API
- **Gain Min / Gain Max**
  - Available when **Exposure = Manual**
- **Shutter Min / Shutter Max**
  - Available when **Exposure = Manual** or **Exposure = Anti-Smearing**
- **Apply settings action**
  - Can apply any combination of exposure, shutter, and gain in a single camera write
  - Targets the device, not an individual entity

When a setting is changed, the integration writes it to the camera and then reads the ISP settings back so Home Assistant shows the actual saved value.

## Firmware quirk handling

Some Reolink firmware appears not to reliably re-evaluate a locked shutter or locked gain value when changing directly from one locked pair to another.

This integration preserves the staged workaround proven in the desktop ISP tool:

- for locked shutter changes, it briefly opens the range before re-locking it
- for locked gain changes, it briefly opens the range before re-locking it

That helps the new value actually stick on the camera.

## Not included

Deliberately out of scope for this version:

- backup / restore
- the wider ISP settings surface
- desktop UI features
- update checker logic from the desktop tool
- any direct coupling to the official Reolink integration

## Installation

### HACS
1. Add this repository as a custom repository in HACS, category **Integration**
2. Download **Reolink ISP Controls**
3. Restart Home Assistant
4. Add the integration from **Settings → Devices & Services**

### Manual
1. Copy `custom_components/reolink_isp` into your Home Assistant `custom_components` folder
2. Restart Home Assistant
3. Add the integration from **Settings → Devices & Services**

## Configuration

Add one camera at a time using:

- protocol (`http` or `https`)
- host / IP
- username
- password
- channel

For most direct-to-camera setups, `channel` should remain `0`.

## Atomic multi-setting action

Example automation/dev-tools action:

```yaml
service: reolink_isp.apply_settings
target:
  device_id: YOUR_DEVICE_ID
data:
  exposure: Manual
  shutter_min: 3
  shutter_max: 3
  gain_min: 30
  gain_max: 30
```

## Notes

- This integration talks directly to the camera
- HTTPS certificate verification is optional because many Reolink cameras use self-signed certificates
- This is intended to complement the official Reolink integration, not replace it

## Status

Current release series: **v0.1.x**

This is an early MVP, but the core shutter/gain workflow is already working in Home Assistant.
