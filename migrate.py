import os
import pickle

CITIES = ['Annaberg IZ', 'Belgern IZ', 'Borna IZ', 'Chemnitz IZ', 'Dresden IZ', 'Eich IZ', 'Grimma TIZ', 'Kamenz IZ', 'Leipzig Messe IZ', 'Löbau IZ', 'Mittweida IZ', 'Pirna IZ', 'Plauen TIZ', 'Riesa IZ', 'Zwickau IZ']
CITIES_AVL = []
CHATS = {}
CHATS_WTG = {city: [] for city in CITIES}

with open('chat_ids', 'rb') as chat_ids:
	CHATS = pickle.load(chat_ids)

NEW_CHATS = {x: [5, set(['Dresden IZ', 'Pirna IZ'])] for x in CHATS}
print(f'Restored chats: {NEW_CHATS}.')

with open('bot.data', 'wb') as bot_data:
	pickle.dump([CITIES_AVL, NEW_CHATS, CHATS_WTG], bot_data)
