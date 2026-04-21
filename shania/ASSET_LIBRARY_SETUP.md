# Asset Library Setup (Shania)

This adds a real image asset library on top of GCP Cloud Storage for templates and Canva workflows.

## Endpoints

- `GET /asset-library/list`
- `POST /asset-library/upload`
- `GET /asset-library/signed-url`

Existing generated-asset endpoint still works:
- `GET /assets/:id?path=...`

## Provider

Set provider (default is GCP):

- `ASSET_LIBRARY_PROVIDER=gcp`

If set to anything else (for example `drive`), the API currently returns `501` until a Drive adapter is added.

## Required Env

- `GCS_BUCKET` (example: `wihy-shania-graphics`)
- `GCP_PROJECT` (example: `wihy-ai`)

The service account running Shania needs GCS read/write permissions on that bucket.

## Upload Request Example

`POST /asset-library/upload`

```json
{
  "fileName": "broccoli-bowl.jpg",
  "contentType": "image/jpeg",
  "dataBase64": "<base64 or data-url>",
  "brand": "communitygroceries",
  "folder": "recipes",
  "tags": ["fresh", "meal-prep", "hero"]
}
```

## List Request Examples

- `GET /asset-library/list`
- `GET /asset-library/list?brand=wihy`
- `GET /asset-library/list?brand=communitygroceries&folder=recipes&limit=100`

## Signed URL Example

- `GET /asset-library/signed-url?path=asset-library/wihy/images/2026-04-20/abc-file.jpg&expires=120`

## Storage Path Pattern

Assets are stored under:

- `asset-library/{brand}/{folder}/{YYYY-MM-DD}/{uuid}-{safe-file-name}`

Defaults:
- `brand=shared`
- `folder=images`

## Google Drive Option

If you want Google Drive as provider, next step is to add a Drive adapter implementing:

- upload
- list
- signed/public URL generation

The API shape above is already provider-oriented and can be reused for Drive without changing callers.
