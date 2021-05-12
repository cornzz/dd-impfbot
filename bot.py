import os
import json
import re
from datetime import datetime, timedelta

import requests
from telegram.ext import Updater, CommandHandler, JobQueue

TOKEN = os.getenv('BOT_TOKEN')
URL = 'https://countee-impfee.b-cdn.net/api/1.1/de/counters/getAll/_iz_sachsen?cached=impfee'
INTERVAL = 180
CITIES = ['Dresden IZ', 'Pirna IZ']
CITIES_AVL = []
CHATS = []


def start(update, context):
	chat_id = update.message.chat.id

	if chat_id in CHATS:
		update.message.reply_text('Already started.')
	else:
		log(f'Adding chat {chat_id}.')
		CHATS.append(chat_id)
		update.message.reply_text(f'Tracking locations: {", ".join(CITIES)}. Interval: {INTERVAL} seconds.')


def stop(update, context):
	chat_id = update.message.chat.id

	if chat_id in CHATS:
		log(f'Removing chat {chat_id}.')
		CHATS.remove(chat_id)
		update.message.reply_text('Stopped.')
	else:
		update.message.reply_text('Not running.')


def send_message(context, message):
	log(f'Sending message "{message.splitlines()[0]}" to chats {CHATS}')
	for chat in CHATS:
		context.bot.sendMessage(chat, message)


def check(context):
	log('Checking locations...')
	content_raw = requests.get(URL).content
	content = json.loads(content_raw)

	for location in content['response']['data'].values():
		city = location['name']
		num = location['counteritems'][0]['val']
		if city in CITIES and num != 0 and city not in CITIES_AVL:
			CITIES_AVL.append(city)
			message = f'\U0001F6A8 New appointments at {city}: {num}\n'
			dates = re.findall(r'"c":(\d*),"d":(\d*)', location['counteritems'][0]['val_s'])
			for date in dates:
				if date[0] != '0':
					day = datetime.utcfromtimestamp(int(date[1])) + timedelta(hours=3)
					message += f'Appointments on {day.strftime("%d.%m.%Y")}: {date[0]}\n'
			send_message(context, message)
		elif city in CITIES and num == 0 and city in CITIES_AVL:
			CITIES_AVL.remove(city)
			send_message(context, f'No appointments left at {city}.')


def log(message):
	print(f'{datetime.now().strftime("%b %d %H:%M:%S")} - {message}')


def main():
	log('Starting bot...')

	updater = Updater(TOKEN)

	dp = updater.dispatcher
	dp.add_handler(CommandHandler('start', start))
	dp.add_handler(CommandHandler('stop', stop))
	
	jq = updater.job_queue
	jq.run_repeating(check, interval=INTERVAL, first=10)

	updater.start_polling()
	updater.idle()


if __name__ == '__main__':
	main()