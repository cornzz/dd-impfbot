import os
import pickle

CITIES = ['Dresden IZ', 'Pirna IZ']
CITIES_AVL = []
CHATS = {}
CHATS_WTG = {city: [] for city in CITIES}

with open('chat_ids', 'rb') as chat_ids:
	CHATS = pickle.load(chat_ids)
	print(f'Restored chats: {CHATS}.')

with open('bot.data', 'wb') as bot_data:
	pickle.dump([CITIES_AVL, CHATS, CHATS_WTG], bot_data)
