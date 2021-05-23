import os
import pickle

CITIES = ['Annaberg IZ', 'Belgern IZ', 'Borna IZ', 'Chemnitz IZ', 'Dresden IZ', 'Eich IZ', 'Grimma TIZ', 'Kamenz IZ', 'Leipzig Messe IZ', 'Löbau IZ', 'Mittweida IZ', 'Pirna IZ', 'Plauen TIZ', 'Riesa IZ', 'Zwickau IZ']
CITIES_AVL = []
CHATS = {}

with open('bot.data', 'rb') as bot_data:
	CITIES_AVL, CHATS, CHATS_WTG = pickle.load(bot_data)

print(f'Chats restored: {CHATS}. Waiting chats restored: {CHATS_WTG}. Available cities restored: {CITIES_AVL}')

CHATS_WTG = {city: [] for city in CITIES}

with open('bot.data', 'wb') as bot_data:
	pickle.dump([CITIES_AVL, NEW_CHATS, CHATS_WTG], bot_data)
