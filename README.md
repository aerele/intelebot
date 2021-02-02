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

3. Use the `send_document` function to send documents like gif, pdf, and zip. In two ways,
    1. Passing `File URL`
    2. Pass `file_name` of the frappe's File doctype.

## Dependencies

1. [Frappe](https://github.com/frappe/frappe)
2. Python
3. [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)

## License

MIT