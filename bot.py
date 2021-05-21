import os, signal
import json
import re
import pickle
from datetime import datetime, timedelta

import requests
from telegram.ext import Updater, CommandHandler, JobQueue, Filters
from telegram.error import ChatMigrated

LOGFILE = f'log_{datetime.now().strftime("%d%m%y_%H%M%S")}.txt'
TOKEN = os.getenv('BOT_TOKEN')
USER = os.getenv('TG_USER')
URL = 'https://countee-impfee.b-cdn.net/api/1.1/de/counters/getAll/_iz_sachsen'
INTERVAL = 180
STD_LIMIT = 5
all_cities = ['Annaberg IZ', 'Belgern IZ', 'Borna IZ', 'Chemnitz IZ', 'Dresden IZ', 'Eich IZ', 'Grimma TIZ', 'Kamenz IZ', 'Leipzig Messe IZ', 'Löbau IZ', 'Mittweida IZ', 'Pirna IZ', 'Plauen TIZ', 'Riesa IZ', 'Zwickau IZ']
CITIES = ['Dresden IZ', 'Pirna IZ']
CITIES_AVL = []
CHATS = {}
CHATS_WTG = {city: [] for city in CITIES}
COMMANDS = '/start - Start receiving notifications when appointments become available.\n'\
			'/stop - Stop receiving notifications.\n'\
			'/setlimit - Set minimum number of appointments required for you to be notified.\n'\
			'/help - Get a list of available commands.'


def commands(update, context):
	update.message.reply_text(COMMANDS)


def start(update, context):
	chat = update.message.chat.id

	if chat in CHATS:
		update.message.reply_text('Already started.')
	else:
		log(f'Adding chat {chat}.')
		CHATS[chat] = STD_LIMIT
		persist()
		update.message.reply_text(
			f'Tracking locations: {", ".join(CITIES)}. Interval: {INTERVAL} seconds.\n'\
			f'Notification limit: min. {STD_LIMIT} appointments. Use /setlimit to change.\n'\
			'Use /stop to stop receiving notifications.\n'
			'Send /help for more commands.')


def stop(update, context):
	chat = update.message.chat.id

	if chat not in CHATS:
		update.message.reply_text('Not running.')
	else:
		log(f'Removing chat {chat}.')
		del CHATS[chat]
		persist()
		update.message.reply_text('Stopped tracking.')


def set_limit(update, context):
	chat = update.message.chat.id

	if chat in CHATS:
		try:
			limit = int(context.args[0])
			if limit < 1:
				raise ValueError
			log(f'Setting limit of chat {chat} to {limit}.')
			CHATS[chat] = limit
			persist()
			update.message.reply_text(f'Set limit to {limit}.')
		except (IndexError, ValueError):
			update.message.reply_text('Invalid limit.')


def active_chats(update, context):
	update.message.reply_text(f'Active chats: {CHATS}')


def shutdown(update, context):
	log('Shutdown command issued.')
	update.message.reply_text('Shutting down...')
	os.kill(os.getpid(), signal.SIGINT)


def persist():
	with open('chat_ids', 'wb') as chat_ids:
		pickle.dump(CHATS, chat_ids)


def broadcast(context, message, city, count):
	log(f'Sending message "{message.splitlines()[0]}" to chats {CHATS}')
	for chat, limit in CHATS.copy().items():
		if count >= limit or count == 0 and chat in CHATS_WTG[city]:
			try:
				if count == 0:
					CHATS_WTG[city].remove(chat)
				context.bot.sendMessage(chat, message)
				if count != 0:
					CHATS_WTG[city].append(chat)
			except ChatMigrated as e:
				new_id = e.new_chat_id
				log(f'Chat {chat} migrated to supergroup. Updating id to {new_id} and sending again...')
				del CHATS[chat]
				CHATS[new_id] = limit
				persist()
				context.bot.sendMessage(new_id, message)
				if count != 0:
					CHATS_WTG[city].append(chat)
			except:
				log(f'Error sending message to chat {chat}, removing chat id...')
				del CHATS[chat]
				persist()


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
			broadcast(context, message, city, num)
		elif city in CITIES and num == 0 and city in CITIES_AVL:
			CITIES_AVL.remove(city)
			broadcast(context, f'No appointments left at {city}.', city, num)


def error(update, context):
	log(f'WARNING - Update {update} caused error: {context.error}')


def log(message):
	log_msg = f'{datetime.now().strftime("%b %d %H:%M:%S")} - {message}'
	print(log_msg)
	with open(LOGFILE, 'a') as f:
		f.write(log_msg + '\n')


def main():
	global CHATS

	log(f'Starting bot... Token: {TOKEN}')

	if os.path.exists('chat_ids'):
		with open('chat_ids', 'rb') as chat_ids:
			CHATS = pickle.load(chat_ids)
			log(f'Chats restored: {CHATS}')

	updater = Updater(TOKEN)

	dp = updater.dispatcher
	dp.add_handler(CommandHandler('help', commands, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('start', start, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('stop', stop, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('setlimit', set_limit, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('activechats', active_chats, Filters.user(username=USER)))
	dp.add_handler(CommandHandler('shutdown', shutdown, Filters.user(username=USER)))
	dp.add_error_handler(error)

	jq = updater.job_queue
	jq.run_repeating(check, interval=INTERVAL, first=10)

	updater.start_polling()
	updater.idle()


if __name__ == '__main__':
	main()