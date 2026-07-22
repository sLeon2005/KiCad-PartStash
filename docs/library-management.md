# Library Management

Kicad-PartStash keeps bundled defaults separate from the user's personal library.

## Bundled defaults

Bundled defaults live in `data/default_parts.json` and are intended to be versioned with the project.

When a bundled default is edited in the app, the original default is not changed. Instead, the app saves a user override with the same `id` in the local user library.

## User library

The user library is stored outside the repo in the app data folder. On Windows, that is usually:

```txt
%APPDATA%/Kicad-PartStash/user_parts.json
```

It can contain:

- custom user parts
- user overrides for bundled defaults

## Import and export

Export writes the current user library to JSON. It does not export bundled defaults unless they have user overrides.

Import merges a JSON library into the current user library. If an imported part has the same `id` as an existing user part, the imported version replaces it.

## Restore defaults

Restore removes user overrides for bundled defaults. Custom user parts are kept.
