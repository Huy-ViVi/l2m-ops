# Package notes (sample plugin)

Owner: your_account

## What it does
Notes per top-up package (Product Key), shown together with the package name from the team's master file. This is the
sample plugin showing how to use `core.sdk`.

## Pages
- **Package notes** (`page.py`): add, view and delete notes; see the edit / delete history; log a summary to the
  Activity history.

## Saved data
| Collection | Key | Fields | Shared IDs used |
|---|---|---|---|
| `notes` | `id` = `<product_key>-<YYYYMMDDHHMMSS>` | `product_key`, `note`, `date` | `product_key`, `date` |

Data belongs to the selected game.

## Data used from the platform / other plugins
- `sdk.master()`: package name by Product Key.

## Needs from the platform
None (no scheduled runs, VPN, extra libraries or secrets).

## Changes
- 0.1.0 (2026-10-29): first version.
