import os, signal
import json
import re
import pickle
from datetime import datetime, timedelta

import requests
from telegram.ext import Updater, CommandHandler, JobQueue, Filters
from telegram.error import ChatMigrated

LOGFILE = f'log_{datetime.now().strftime("%d%m%y_%H%M%S")}.txt'
PERSIST_LOG = bool(os.getenv('PERSIST_LOG'))
TOKEN = os.getenv('BOT_TOKEN')
USER = os.getenv('TG_USER')
URL = 'https://countee-impfee.b-cdn.net/api/1.1/de/counters/getAll/_iz_sachsen'
INTERVAL = 180
STD_LIMIT = 5
CITIES = ['Annaberg IZ', 'Belgern IZ', 'Borna IZ', 'Chemnitz IZ', 'Dresden IZ', 'Eich IZ', 'Grimma TIZ', 'Kamenz IZ', 'Leipzig Messe IZ', 'Löbau IZ', 'Mittweida IZ', 'Pirna IZ', 'Plauen TIZ', 'Riesa IZ', 'Zwickau IZ']
STD_CITIES = set(['Dresden IZ', 'Pirna IZ'])
CITIES_AVL = []
CHATS = {}
CHATS_WTG = {city: [] for city in CITIES}
COMMANDS = '/start - Start receiving notifications when appointments become available.\n'\
			'/stop - Stop receiving notifications.\n'\
			'/setlimit <limit> - Set minimum number of appointments required for you to be notified.\n'\
			'/locations - See currently tracked locations.\n'\
			'/addlocation <city> - Add location to tracking.\n'\
			'/removelocation <city> - Remove location from tracking.\n'\
			'/help - Get a list of available commands.'


def commands(update, context):
	update.message.reply_text(COMMANDS)


def start(update, context):
	chat = update.message.chat.id

	if chat in CHATS:
		update.message.reply_text('Already started.')
	else:
		log(f'Adding chat {chat}.')
		CHATS[chat] = [STD_LIMIT, STD_CITIES.copy()]
		persist()
		update.message.reply_text(
			f'Tracking locations: {", ".join(STD_CITIES)}. Interval: {INTERVAL} seconds.\n'\
			f'Notification limit: min. {STD_LIMIT} appointments. Use /setlimit to change.\n'\
			'Send /stop to stop receiving notifications.\n'
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
			CHATS[chat][0] = limit
			persist()
			update.message.reply_text(f'Set limit to {limit}.')
		except (IndexError, ValueError):
			update.message.reply_text('Invalid limit.')


def locations(update, context):
	chat = update.message.chat.id

	if chat in CHATS:
		update.message.reply_text(f'Tracking locations {", ".join(CHATS[chat][1])}.')


def add_location(update, context):
	chat = update.message.chat.id

	if chat in CHATS:
		try:
			city = [x for x in CITIES if x.lower().startswith(context.args[0].lower())]
			log(f'Adding location {city[0]} to chat {chat}.')
			CHATS[chat][1].add(city[0])
			persist()
			update.message.reply_text(f'Tracking locations {", ".join(CHATS[chat][1])}.')
		except IndexError:
			update.message.reply_text('Invalid location.')


def remove_location(update, context):
	chat = update.message.chat.id

	if chat in CHATS:
		try:
			city = [x for x in CITIES if x.lower().startswith(context.args[0].lower())]
			if city[0] in CHATS[chat][1]:
				log(f'Removing location {city[0]} from chat {chat}.')
				CHATS[chat][1].remove(city[0])
				persist()
				update.message.reply_text(f'Tracking locations {", ".join(CHATS[chat][1])}.')
		except IndexError:
			update.message.reply_text('Invalid location.')



def active_chats(update, context):
	update.message.reply_text(f'Active chats: {list(CHATS)}')


def shutdown(update, context):
	log('Shutdown command issued.')
	update.message.reply_text('Shutting down...')
	persist()
	os.kill(os.getpid(), signal.SIGINT)


def persist():
	with open('bot.data', 'wb') as bot_data:
		pickle.dump([CITIES_AVL, CHATS, CHATS_WTG], bot_data)


def broadcast(context, message, city, count):
	for chat, settings in CHATS.copy().items():
		if count >= settings[0] and city in settings[1] or chat in CHATS_WTG[city] and count == 0:
			try:
				if count == 0:
					CHATS_WTG[city].remove(chat)
				log(f'Sending message "{message.splitlines()[0]}" to chat {chat}')
				context.bot.sendMessage(chat, message)
				if count != 0:
					CHATS_WTG[city].append(chat)
			except ChatMigrated as e:
				new_id = e.new_chat_id
				log(f'Chat {chat} migrated to supergroup. Updating id to {new_id} and sending again...')
				del CHATS[chat]
				CHATS[new_id] = settings
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
		if num != 0 and city not in CITIES_AVL:
			CITIES_AVL.append(city)
			message = f'\U0001F6A8 New appointments at {city}: {num}\n'
			dates = re.findall(r'"c":(\d*),"d":(\d*)', location['counteritems'][0]['val_s'])
			for date in dates:
				if date[0] != '0':
					day = datetime.utcfromtimestamp(int(date[1])) + timedelta(hours=3)
					message += f'Appointments on {day.strftime("%d.%m.%Y")}: {date[0]}\n'
			broadcast(context, message, city, num)
		elif num == 0 and city in CITIES_AVL:
			CITIES_AVL.remove(city)
			broadcast(context, f'No appointments left at {city}.', city, num)


def error(update, context):
	log(f'WARNING - Update {update} caused error: {context.error}')


def log(message):
	log_msg = f'{datetime.now().strftime("%b %d %H:%M:%S")} - {message}'
	print(log_msg)
	if PERSIST_LOG:
		with open(LOGFILE, 'a') as f:
			f.write(log_msg + '\n')


def main():
	global CITIES_AVL, CHATS, CHATS_WTG

	log(f'Starting bot... Token: {TOKEN}')

	if os.path.exists('bot.data'):
		with open('bot.data', 'rb') as bot_data:
			CITIES_AVL, CHATS, CHATS_WTG = pickle.load(bot_data)
			log(f'Chats restored: {CHATS}. Waiting chats restored: {CHATS_WTG}. Available cities restored: {CITIES_AVL}')

	updater = Updater(TOKEN)

	dp = updater.dispatcher
	dp.add_handler(CommandHandler('help', commands, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('start', start, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('stop', stop, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('setlimit', set_limit, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('locations', locations, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('addlocation', add_location, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('removelocation', remove_location, ~Filters.update.edited_message))
	dp.add_handler(CommandHandler('activechats', active_chats, Filters.user(username=USER)))
	dp.add_handler(CommandHandler('shutdown', shutdown, Filters.user(username=USER)))
	dp.add_error_handler(error)

	jq = updater.job_queue
	jq.run_repeating(check, interval=INTERVAL, first=10)

	updater.start_polling()
	updater.idle()


if __name__ == '__main__':
	main()