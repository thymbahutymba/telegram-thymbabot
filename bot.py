import json, os, sqlite3, logging
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from sqlite3 import Error
from prettytable import PrettyTable

#level=logging.INFO,

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='thymbabot.log')

class core:
	cfg = None
	connect = None
	cursor = None
	
	def __init__(self):
		
		try:
			self.connect = sqlite3.connect('casa.sqlite3', check_same_thread=False)
			self.cursor = self.connect.cursor()
		except Error as e:
			logging.error("Error to connect database: " + str(e))
			pass
		
		with open('config.json') as config_file:
			self.log = None
			self.cfg = json.load(config_file)
			
		for tab_file in os.listdir('tables'):
			with open('tables/'+tab_file) as tab:
				if self.connect is not None:
					t = tab.read()
					self.cursor.execute(t)
				else:
					logging.error("Connection to database failed")
					break
				
	def start(self):
		try:
			self.updater = Updater(token=self.cfg.get('token'), workers=10)
			self.dispatcher = self.updater.dispatcher
			self.updater.start_polling(clean=True)
			self.dispatcher.add_error_handler(self.error_callback)
			self.dispatcher.add_handler(CommandHandler('start', self.start_command))
			self.dispatcher.add_handler(CommandHandler('ping', self.ping_command))
			self.dispatcher.add_handler(CommandHandler('help', self.help_command))
			self.dispatcher.add_handler(CommandHandler('register', self.register_command))
			self.dispatcher.add_handler(CommandHandler('total', self.total_command))
			self.dispatcher.add_handler(CommandHandler('expense', self.expense_command, pass_args=True))
			self.dispatcher.add_handler(CommandHandler('print', self.print_command))
			self.dispatcher.add_handler(CallbackQueryHandler(self.button))
		except Exception as ecc:
			logging.error('error: ' + str(ecc))
			pass
		
	def error_callback(self, bot, update, error):
		logging.error("Update {} caused error {}.".format(update,error))
				
	def start_command(self, bot, update):
		welcome = "I'm Heisenberg.\n"
		welcome += "Type /help to display the command list."
		bot.send_message(chat_id=update.message.chat_id, text=welcome)
		
	def register_command(self, bot, update):
		c_id = update.message.chat_id
		c_username = update.message.from_user.username 
#		try:
#			if connect is not None:
		insert_query = "SELECT count(*) FROM user WHERE id = {};".format(c_id)
		self.cursor.execute(insert_query)
		if self.cursor.fetchone()[0] == 0:
			query = "INSERT INTO user values({}, '{}');".format(c_id, c_username)
			self.cursor.execute(query)
			self.connect.commit()
			self.reply_message(bot, update, "Done.")
			logging.info("New users registered: {} with id: {}".format(c_id, c_username))
		else:
			logging.warning('User {} already registered.'.format(c_id))
			bot.send_message(chat_id=c_id, text="You are already registered.")
#		except Exception as ecc:
#			bot.send_message(chat_id=c_id, text="Connection problem, report to admin.")
#			logging.error("Unable to register user.")
#			msg = "Connection problem, unable to register user"
#			self.report(bot, update, msg)
#			pass
			
	def report(self, bot,update,msg):
		bot.send_message(chat_id=self.cfg.get('admin_id'), text = msg)
	
	def ping_command(self, bot, update):
		bot.send_message(chat_id=update.message.chat_id, text="pong")

	def help_command(self, bot, update):
		message_help = "Command:\n"
		message_help += "/ping - ping the bot\n"
		message_help += "/help - help command\n"
		message_help += "/register - register your user\n"
		message_help += "/expense - add some purchase. <price> <description>\n"
		message_help += "/total - total of your expense\n"
		message_help += "/print - show something."
		bot.send_message(chat_id=update.message.chat_id, text=message_help)
		
	def expense_command(self, bot, update, args):
		string = update.message.text.split(' ',2)
		if not args or len(args)<2:
			text = "You forgot price and/or description."
			self.reply_message(bot, update, text)
		else:
#			price = float(args[0])
#			desc = " ".join(args[1:])
#			print(price)
#			print(desc)
#			if price is None or desc is None:
#				update.reply_message("You have not set price or description.")
#			else:
			last_id = self.add_expense(bot, update, price, desc)
			self.add_payment(update.message.chat_id, last_id, price)
			
	def reply_message(self, bot, update, text):
		c_id = update.message.chat_id
		to_mess = update.message.message_id
		bot.send_message(chat_id=c_id, text=text, reply_to_message_id=to_mess)
	
	def add_expense(self, bot, update, c_id, price, desc):
		if self.check_register(c_id) == False:
			text = "You are not registered yet, type /register to do so."
			self.reply_message(bot, update, text)
		else:
			try:
				query = "INSERT INTO expense(price, description, data_reg, user_id)"
				query += "values({}, '{}', CURRENT_DATE, {});".format(price, desc, c_id)
				self.cursor.execute(query)
				self.connect.commit()
				logging.info("Insert into table expense from {}: {} {}.".format(c_id, price, desc))
				bot.send_message(chat_id=c_id, text="Insert completed.")
				query2 = "SELECT LAST_INSERT_ROWID()"
				self.cursor.execute(query2)
				return self.cursor.fetchone()[0]
			except Exception as e:
				logging.error("Insert into expense failed. Error: "+ str(e))
				bot.send_message(chat_id=c_id, text="Insert into expense failed.")
				pass
	
	def add_payment(self, c_id, e_id, price):
		try:
			query = "SELECT count(*) FROM user"
			self.cursor.execute(query)
			own_price = float(price/(cursor.fetchone()[0]))
			query2 = "INSERT INTO payment(expense_id, user_id, import) values({}, {}, {})".format(e_id, c_id, own_price)
			self.cursor.execute(query2)
			self.connect.commit()
			logging.info("Insert into table payment.")
		except Exception as e:
			logging.error("Insert into payment failed. Error: " + str(e))
			pass
	
	def check_register(self, c_id):
		query = "SELECT count(*) FROM user WHERE id={}".format(c_id)
		self.cursor.execute(query)
		if self.cursor.fetchone()[0] == 0:
			return False
		
	def total_command(self, bot, update):
		if self.check_register(update.message.chat_id) == False:
			msg = "You are not in my database, you have not bought anything."
			self.reply_message(bot, update, msg)
		else:
			query = "SELECT sum(price) FROM expense WHERE user_id = {}".format(update.message.chat_id)
			self.cursor.execute(query)
			total = cursor.fetchone()[0]
			user = update.message.from_user.username
			msg = "Total amount of expense for {} is: {}€".format(user,total)
			self.reply_message(bot, update, msg)

	def print_command(self, bot, update):
		keyboard = [[InlineKeyboardButton("Expense", callback_data='1'),
			   InlineKeyboardButton("Payments", callback_data='2'),
			   InlineKeyboardButton("Users", callback_data='3')]]
		
		reply_markup = InlineKeyboardMarkup(keyboard)

		update.message.reply_text('Choose what you want to print:', reply_markup=reply_markup)
		
		
	def button(self, bot, update):
		update.callback_query.message.delete()
		try:
			c_id = update.callback_query.message.chat_id
			if int(update.callback_query.data) == 1:
				query = "SELECT * FROM expense WHERE user_id={}".format(c_id)
				table = PrettyTable(["ID", "Price", "Description", "Data Reg", "User"])
				tmp = "expense"
			elif int(update.callback_query.data) == 2:
				query = "SELECT * FROM payment WHERE user_id={}".format(c_id)
				table = PrettyTable(["Expense", "User", "Payment Date", "Import", "Paid?"])
				tmp = "payment"
			elif int(update.callback_query.data) == 3:
				query = "SELECT * FROM user"
				table = PrettyTable(["ID", "Name"])
				tmp = "user"
			
			self.cursor.execute(query)
			if self.cursor.fetchone() is None:
				text = "There are not results for {}.".format(tmp)
				bot.send_message(chat_id=c_id, text = text)
			else:
				self.cursor.execute(query) #refresh result set
				for res in self.cursor.fetchall():
					table.add_row(res)
				s = "```\n"
				s += table.get_string()
				s += "```"
				bot.send_message(chat_id=c_id, text = s, parse_mode='MARKDOWN')
		except Exception as ecc:
			logging.error("Error: " + str(ecc))
