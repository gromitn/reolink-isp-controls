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
- Device-level custom actions **`reolink_isp.save_profile`** and **`reolink_isp.apply_profile`** for user-saved profile slots
- Fixed profile slots for **day**, **gloomy**, and **night**
- Diagnostic sensors for:
  - **Last Applied Profile**
  - **Saved Profile Slots**
- Read-back polling so Home Assistant reflects what the camera actually saved
- The proven staged workaround for locked shutter and gain changes on affected firmware

## Companion tool for Windows

There’s also a companion Windows app: [Reolink ISP Tool](https://github.com/gromitn/reolink-isp-tool).

That one is handy if you want a simple desktop UI for reading, tweaking, verifying, and backing up Reolink ISP settings directly from the camera. It’s a good fit for setup, experimentation, and backup/restore type jobs, whereas this Home Assistant integration is more about ongoing control and automation.

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
- **Saved profiles**
  - Save the current camera settings into one of three named slots: `day`, `gloomy`, or `night`
  - Apply a saved slot later using `reolink_isp.apply_profile`
  - If a profile slot has not been saved yet, the integration returns a clear error
- **Profile sensors**
  - **Last Applied Profile** shows the most recently applied profile slot
  - **Saved Profile Slots** shows which profile slots currently contain saved values  

When a setting is changed, the integration writes it to the camera and then reads the ISP settings back so Home Assistant shows the actual saved value.

## Firmware quirk handling

Some Reolink firmware appears not to reliably re-evaluate a locked shutter or locked gain value when changing directly from one locked pair to another.

This integration preserves the staged workaround proven in the desktop ISP tool:

- for locked shutter changes, it briefly opens the range before re-locking it
- for locked gain changes, it briefly opens the range before re-locking it

That helps the new value actually stick on the camera.

## Not included

Deliberately out of scope for this version:

- backup / restore - See [Reolink ISP Tool](https://github.com/gromitn/reolink-isp-tool).
- the wider ISP settings surface
- desktop UI features
- update checker logic from the desktop tool
- any direct coupling to the official Reolink integration

## Installation

### HACS
1. Add this repository as a custom repository in HACS under the Integration category
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

Use the device-level action `reolink_isp.apply_settings` when you want multiple ISP values applied in a single camera write.

This is especially useful when changing locked shutter or gain values, or when changing exposure mode and related values together.

Supported fields:

- `exposure`
- `shutter_min`
- `shutter_max`
- `gain_min`
- `gain_max`

Rules:

- `gain_min` and `gain_max` require `exposure: Manual`
- `shutter_min` and `shutter_max` require `exposure: Manual` or `Anti-Smearing`

Example action:

```yaml
action: reolink_isp.apply_settings
target:
  device_id: YOUR_DEVICE_ID
data:
  exposure: Manual
  shutter_min: 3
  shutter_max: 3
  gain_min: 30
  gain_max: 30
```

## User-saved profiles

The integration includes three fixed profile slots:

- `day`
- `gloomy`
- `night`

These are not hard-coded presets. Each slot stores the camera's current Exposure, Shutter Min/Max, and Gain Min/Max values when you save it.

This lets you tune the camera manually, save the current state as a named profile, and recall it later.

### Save a profile

```yaml
action: reolink_isp.save_profile
target:
  device_id: YOUR_DEVICE_ID
data:
  profile: night
```

### Apply a profile

```yaml
action: reolink_isp.apply_profile
target:
  device_id: YOUR_DEVICE_ID
data:
  profile: night
```

The `gloomy` slot is intended for in-between lighting conditions such as dawn, dusk, overcast weather, or storms.

## Notes

- This integration talks directly to the camera
- HTTPS certificate verification is optional because many Reolink cameras use self-signed certificates
- This is intended to complement the official Reolink integration, not replace it

## Status

Current release series: **v0.1.x**

This is an early MVP, but the core shutter/gain workflow is already working in Home Assistant
