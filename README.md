carddav2hatchbuck
=================

The carddavsync.py script searches the address book for contacts and compares it with contacts in a hatchback.
If the contact is in a hatchback, do not create a contact, or if it does not exist,
create a new contact with the same contact information in the address book.

The sync.py calls the carddavsync.py script and uses the user and pass from .env

Usage
=====
