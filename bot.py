import json, logging, sqlite3
from telegram.ext import Updater, CommandHandler
from sqlite3 import Error

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, filename='thymbabot.log')
	
try:
	connessione = sqlite3.connect('casa.db', check_same_thread=False)
	cursor = connessione.cursor()
except Error as e:
	print(e)
	pass

class core:
	cfg = None
	log = None
	
	def __init__(self):
		with open('config.json') as config_file:
			self.log = None
			self.cfg = json.load(config_file)

		sql_create_table_users = "CREATE TABLE IF NOT EXISTS users(id integer PRIMARY KEY, name string NOT NULL);"
		
		sql_create_table_spese = "CREATE TABLE IF NOT EXISTS spese(id integer PRIMARY KEY AUTOINCREMENT,"
		sql_create_table_spese += "descrizione text NOT NULL,"
		sql_create_table_spese += "data_reg date NOT NULL,"
		sql_create_table_spese += "user_id NOT NULL,"
		sql_create_table_spese += "FOREIGN KEY (user_id) REFERENCES users(id));"
		
		if connessione is not None:
			connessione.execute(sql_create_table_users)
			connessione.execute(sql_create_table_spese)
		else:
			logging.error("Connection failed")
			
	def start(self):
		try:
			self.updater = Updater(token=self.cfg.get('token'), workers=10)
			self.dispatcher = self.updater.dispatcher
			self.updater.start_polling(clean=True)
			self.dispatcher.add_handler(CommandHandler('start', self.start_command))
			self.dispatcher.add_handler(CommandHandler('ping', self.ping_command))
			self.dispatcher.add_handler(CommandHandler('help', self.help_command))
			#updater.idle() #???
		except Exception as ecc:
			logging.error('error: ' + str(e))
			pass
		
	def start_command(self, bot, update):
		
		welcome = "I'm Heisenberg.\n"
		welcome += "Type /help to display the command list."
		c_id = update.message.chat_id
		c_username = update.message.from_user.username 
		bot.send_message(chat_id=c_id, text=welcome)
		
		try:
			if connessione is not None:
				insert_query = "SELECT count(*) FROM users WHERE id = {};".format(c_id)
				cursor.execute(insert_query)
				if cursor.fetchone()[0] == 0:
					query = "INSERT INTO users values({}, '{}');".format(c_id, c_username)
					cursor.execute(query)
					logging.info("Utente: {} con id: {} inserito".format(c_id, c_username))
					connessione.commit()
				else:
					logging.warning('Utente già inserito')
		except Exception as ecc:
			logging.error("Impossibile inserire utente")

			
	def ping_command(self, bot, update):
		#print(update.message.chat_id)
		bot.send_message(chat_id=update.message.chat_id, text="pong")

	def help_command(self, bot, update):
		message_help = "Command:\n"
		message_help += "/ping - ping the bot\n"
		message_help += "/help - help command\n"
		bot.send_message(chat_id=update.message.chat_id, text=message_help )


