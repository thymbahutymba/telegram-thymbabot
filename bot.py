import json, logging, sqlite3
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, ConversationHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from sqlite3 import Error

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, filename='thymbabot.log')
	
try:
	connect = sqlite3.connect('casa.db', check_same_thread=False)
	cursor = connect.cursor()
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
		sql_create_table_spese += "price float NOT NULL,"
		sql_create_table_spese += "description text NOT NULL,"
		sql_create_table_spese += "data_reg date NOT NULL,"
		sql_create_table_spese += "user_id NOT NULL,"
		sql_create_table_spese += "FOREIGN KEY (user_id) REFERENCES users(id));"
		
		if connect is not None:
			connect.execute(sql_create_table_users)
			connect.execute(sql_create_table_spese)
		else:
			logging.error("Connection to database failed")
			
	def start(self):
		try:
			self.updater = Updater(token=self.cfg.get('token'), workers=10)
			self.dispatcher = self.updater.dispatcher
			self.updater.start_polling(clean=True)
			#self.updater.idle()
			self.dispatcher.add_handler(CommandHandler('start', self.start_command))
			self.dispatcher.add_handler(CommandHandler('ping', self.ping_command))
			self.dispatcher.add_handler(CommandHandler('help', self.help_command))
			self.dispatcher.add_handler(CommandHandler('register', self.register_command))
			self.dispatcher.add_handler(CommandHandler('shop', self.shop_command, pass_args=True))
		except Exception as ecc:
			logging.error('error: ' + str(ecc))
			pass
		
	def start_command(self, bot, update):
		welcome = "I'm Heisenberg.\n"
		welcome += "Type /help to display the command list."
		bot.send_message(chat_id=update.message.chat_id, text=welcome)
		
	def register_command(self, bot, update):
		c_id = update.message.chat_id
		c_username = update.message.from_user.username 
		try:
			if connect is not None:
				insert_query = "SELECT count(*) FROM users WHERE id = {};".format(c_id)
				cursor.execute(insert_query)
				if cursor.fetchone()[0] == 0:
					query = "INSERT INTO users values({}, '{}');".format(c_id, c_username)
					cursor.execute(query)
					connect.commit()
					bot.send_message(chat_id=c_id, text="Done.")
					msg = "New users registered: {} with id: {}".format(c_id, c_username)
					logging.info(msg)
					#self.report(bot,update,msg)
				else:
					logging.warning('User already registered.')
					bot.send_message(chat_id=c_id, text="You are already registered.")
		except Exception as ecc:
			bot.send_message(chat_id=c_id, text="Connection problem, report to admin.")
			logging.error("Unable to register user.")
			msg = "Connection problem, unable to register user"
			self.report(bot, update, msg)
			pass
			
	def report(self, bot,update,msg):
		bot.send_message(chat_id=self.cfg.get('admin_id'), text = msg)
	
	def ping_command(self, bot, update):
		bot.send_message(chat_id=update.message.chat_id, text="pong")

	def help_command(self, bot, update):
		message_help = "Command:\n"
		message_help += "/ping - ping the bot\n"
		message_help += "/help - help command\n"
		message_help += "/register - register your user\n"
		message_help += "/shop - add some buy."
		bot.send_message(chat_id=update.message.chat_id, text=message_help)
		
	def shop_command(self, bot, update, args):
		string = update.message.text.split(' ',2)
		price = float(args[0])
		desc = " ".join(args[1:])
		self.add_shop(bot, update, update.message.chat_id, price, desc)
	
	def add_shop(self, bot, update, c_id, price, desc):
		result = self.check_register(c_id)
		if result == False:
			bot.send_message(chat_id=c_id, text="You are not registered yet, type /register to do so.")
		else:
			try:
				query = "INSERT INTO spese(price, description, data_reg, user_id)"
				query += "values({}, '{}', CURRENT_DATE, {});".format(price, desc, c_id)
				print(query)
				cursor.execute(query)
				connect.commit()
				logging.info("Insert into table spese from {}: {} {}.".format(c_id, price, desc))
				bot.send_message(chat_id=c_id, text="Insert completed.")
			except Exception as e:
				logging.error("Insert into spese failed." + str(e))
				bot.send_message(chat_id=c_id, text="Insert into spese failed.")
				pass
			
	def check_register(self, c_id):
		query = "SELECT count(*) FROM users WHERE id={}".format(c_id)
		cursor.execute(query)
		if cursor.fetchone()[0] == 0:
			return False
