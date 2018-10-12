carddav2hatchbuck
=================

[![Build Status](https://img.shields.io/travis/vshn/carddav2hatchbuck/master.svg
)](https://travis-ci.org/vshn/carddav2hatchbuck)

A CLI tool to sync contacts from a CardDAV address book to Hatchbuck.

The `carddavsync` command searches the CardDAV address book for contacts and
compares it with contacts in a Hatchbuck. If the contact doesn't exist on
Hatchbuck yet it creates a new contact with the entire contact information
from the CardDAV address book. Otherwise, it updates the contact details on
Hatchbuck to match the one in the CardDAV address book.

The `sync` command calls `carddavsync` using username and password from `.env`

Usage
=====

See the help screen in the CLI, e.g.

```bash
python -m carddav2hatchbuck.sync --help
```

Required arguments can be provided as environment values, including writing
them into an `.env` file, or explicitly passed (takes precedence).
