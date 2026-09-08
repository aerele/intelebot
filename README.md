# Intelebot

Intelebot integrates [Telegram](https://telegram.org/) with Frappe, ERPNext, Custom frappe applications to yield more productivity via [Telegram Bot API](https://core.telegram.org/bots/api). 


### Table of Contents
* [Installation](#installation)
* [Setup and Use](#setup-and-use)
* [Dependencies](#dependencies)
* [License](#license)

## Installation
Navigate to your bench folder
```
cd frappe-bench
```
Install Intelebot App
```
bench get-app intelebot https://github.com/aerele/intelebot.git
bench --site [site-name] install-app intelebot
```

## Setup and Use:

 - Create a new [Telegram bot](https://core.telegram.org/bots) in `BotFather`

 - Get Telegram Bot Token from `BotFather`

### Once you created your bot.

In Intelebot,

1. Go to → `Telegram Bot` -> Enter Telegram Bot Username and Bot API Token.

2. Once the new `Telegram Bot` document created. At every half an hour,  ``telegram channel``, ``groups``, ``supergroups``, and ``private`` chats associated with the corresponding bots are created automatically via `Bot API` under ``Telegram Chat``.

3. Create a new `Send Document` with the necessary fields and a public file stored on the site. The file is sent immediately on creation. The scheduler checks queued documents and eligible failed sends every half hour. You can also use the `Send To Telegram` button. GIF, PDF, and ZIP files continue to be sent as documents.

4. In `Send Document` if you enabled `delete_linked_file_after_sent` means, the linked file will be deleted in the system once it sent to the telegram chat.

## Dependencies

1. [Frappe](https://github.com/frappe/frappe) v15 or v16, managed by Bench.
2. Python 3.10+ for Intelebot; use the Python version required by your Frappe release. Current Frappe v16 requires Python 3.14.
3. [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 22.8, the latest stable release verified on 8 September 2026.

### Upgrading an existing installation

After updating the Intelebot checkout to this revision, run from the bench:

```sh
bench setup requirements --python
bench --site [site-name] migrate
bench restart
```

Upgrade Python/Frappe using the normal Bench migration procedure before installing on v16. This app does not upgrade the framework or Python for you. The existing DocTypes, button methods and half-hour scheduler paths are retained; bot tokens and chat links do not need to be recreated.

### How the asynchronous Telegram API is used

Frappe hooks, whitelisted methods and scheduler jobs remain synchronous. A small adapter awaits python-telegram-bot operations inside a separate event-loop lifetime, then returns the result to Frappe. Bot HTTP connections and upload file handles are closed after each operation. Frappe database operations stay in the original calling thread/context, including when the caller already has an event loop.

Chat discovery handles private chats, groups, supergroups and channels, including absent optional names/usernames. It resumes after the last saved update ID. An empty poll is successful. Telegram polling requires that this bot is not already using a webhook or a competing update consumer.

Sends are marked `Completed` only after Telegram confirms delivery. Failed sends retain their file and error details. The scheduler retains the existing retry policy: queued records and timeout failures, with the existing retry-count cutoff. Other errors can be retried manually after correcting the cause. Completed records are not resent, and a file-cleanup failure leaves the record Completed with an error log rather than scheduling another upload.

Telegram does not provide an idempotency key for document sends. A timeout after Telegram accepts an upload, or a process failure before the database saves the result, can still produce a duplicate on retry. This upgrade does not promise exactly-once delivery.

### Tests

From the Intelebot checkout, with the bench environment and updated dependencies active:

```sh
python -m unittest discover -s tests -v
```

The suite uses actual Frappe imports/controllers and PTB 22.8 with a mocked HTTP transport. It checks polling, uploads, resource cleanup, synchronous calls inside/outside an event loop, chat updates, retry handling and file deletion. It does not contact Telegram or modify a site database. Before deployment, verify Fetch Now, a test-file upload, and a scheduled retry on a staging site with a dedicated test bot.

## License

MIT
