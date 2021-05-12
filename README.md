Impfbot DD
===
Python based Telegram bot that sends notifications when there are available vaccination appointments in Dresden.

How to use
===
Requires python and virtualenv to be installed.
Rename `bot.env.default` to `bot.env`, add bot token and user name.

```
git clone https://github.com/cornzz/dd-impfbot.git
cd dd-impfbot
python -m venv venv
source venv/bin/activate
pip install -r reqs.txt
source bot.env
python bot.py
```