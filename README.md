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

3. Create a new `Send Document` with the necessary fields and make sure the linked file will be public. At every half an hour the specified file gets sent to the corresponding chat. Otherwise, use ```send_to_telegram``` button to send the linked file. Currently, it supports gif, pdf, and zip files.

4. In `Send Document` if you enabled `delete_linked_file_after_sent` means, the linked file will be deleted in the system once it sent to the telegram chat.

## Dependencies

1. [Frappe](https://github.com/frappe/frappe)
2. Python
3. [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)

## License

MIT