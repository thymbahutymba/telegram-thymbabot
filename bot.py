import json, os, sqlite3, logging, tempfile
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler, RegexHandler, ConversationHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from sqlite3 import Error
from prettytable import PrettyTable

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO, filename='thymbabot.log')
CHOOSING, TAKE_DATA, TAKE_INFORMATION, LOOP_PAYMENT, SET_PAYMENT, TRANSICTION_STATE = range(6)

class core:
	cfg = None
	connect = None
	cursor = None
	
	action_keyboard = [['Expense', 'PaymentNotWork'], ['Cancel']]
	expense_keyboard = [['Price', 'Description'], ['Done']]
	#insert_handler = None
		
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
		
		#self.refresh_insert_handler()
				
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
			self.reply_message(bot, update, "You are already registered.")
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
		#self.refresh_insert_handler()

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
			last_id = self.add_expense(bot, update, price, desc)
			self.add_payment(update.message.chat_id, last_id, price)
	
	def reply_message(self, bot, update, text):
		c_id = update.message.chat_id
		to_mess = update.message.message_id
		bot.send_message(chat_id=c_id, text=text, reply_to_message_id=to_mess)

	def check_register(self, bot, update):
		query = "SELECT count(*) FROM user WHERE id={}".format(update.message.chat_id)
		self.cursor.execute(query)
		if self.cursor.fetchone()[0] == 0:
			text = "You are not registered yet, type /register to do so."
			self.reply_message(bot, update, text)
			return False
		return True
		
	def total_command(self, bot, update):
		if self.check_register(bot, update):
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
			
	def start(self):
		insert_handler = ConversationHandler(
			entry_points=[CommandHandler('insert', self.insert_command)],
			states={
				CHOOSING: [RegexHandler('^(Expense|PaymentNoWork)$', self.first_choice, pass_user_data=True)],
				TAKE_INFORMATION: [RegexHandler('^(Price|Description|Done)$', self.take_information, pass_user_data=True)],
				TAKE_DATA: [MessageHandler(Filters.text, self.take_data, pass_user_data=True)],
				LOOP_PAYMENT: [MessageHandler(Filters.text, self.loop_payment, pass_user_data=True)],
				SET_PAYMENT: [MessageHandler(Filters.text, self.set_payment, pass_user_data=True)],
				TRANSICTION_STATE: [RegexHandler('^(YES|NO)$', self.transiction_state, pass_user_data=True)]
				},
			fallbacks = [RegexHandler('^(Finish|Cancel)$', self.end_action, pass_user_data=True)],
		)
				
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
			#self.dispatcher.add_handler(CommandHandler('expense', self.expense_command, pass_args=True))
			self.dispatcher.add_handler(CommandHandler('print', self.print_command))
			self.dispatcher.add_handler(CallbackQueryHandler(self.button))
			self.dispatcher.add_handler(insert_handler)
			self.updater.idle()
		except Exception as ecc:
			logging.error('error: ' + str(ecc))
			pass
	
	def simple_2choice(self, user_data):
		if user_data['choice'] == 'Expense':
			markup = ReplyKeyboardMarkup(self.expense_keyboard, one_time_keyboard=True)
		#elif user_data == 'Payment':
			#markup...
		return markup
	
	def is_float(self, s):
		try:
			float(s)
			return True
		except Exception as ecc:
			logging.error("Error: " + str(ecc))
			return False
	
	def insert_command(self, bot, update):
		if not self.check_register(bot, update):
			return ConversationHandler.END
		else:
			markup = ReplyKeyboardMarkup(self.action_keyboard, one_time_keyboard=True)
			update.message.reply_text("Choice what you want to do.", reply_markup=markup)
			return CHOOSING
	
	def first_choice(self, bot, update, user_data):
		user_data['choice'] = update.message.text
		if user_data['choice'] == 'Expense':
			user_data['Price'] = None
			user_data['Description'] = None
		markup = self.simple_2choice(user_data)
		text = "Which information do you want to add?\nRemember that if you made a mistake, you can re-enter the data before clicking Done."
		update.message.reply_text(text, reply_markup=markup)
		return TAKE_INFORMATION	
	
	def take_information(self, bot, update, user_data):
		if update.message.text == 'Done':
			tmp_keyboard = [['YES', 'NO']]
			markup = ReplyKeyboardMarkup(tmp_keyboard, one_time_keyboard=True)
			update.message.reply_text("Do you want to confirm this data?", reply_markup=markup)
			return TRANSICTION_STATE
		
		user_data['adding'] = update.message.text
		msg = None
		if update.message.text == 'Price':
			msg = "Send me the price of the expanse."
		elif update.message.text == 'Description':
			msg = "Give me a little description."
		update.message.reply_text(msg)
		return TAKE_DATA
	
	def take_data(self, bot, update, user_data):
		if user_data['adding'] == 'Price' and not self.is_float(update.message.text):
			self.reply_message(bot, update, "This is not a valid price.")
		else:
			user_data[user_data['adding']]=update.message.text
			if 'adding' in user_data:
				del user_data['adding']
		
		markup = self.simple_2choice(user_data)
		text = "Which information do you want to add?\nRemember that if you made a mistake, you can re-enter the data before clicking Done."
		update.message.reply_text(text, reply_markup=markup)
		return TAKE_INFORMATION
	
	def transiction_state(self, bot, update, user_data):
		if update.message.text == 'YES':
			return LOOP_PAYMENT
		else:
			markup = self.simple_2choice(user_data)
			text = "Which information do you want to add?\nRemember that if you made a mistake, you can re-enter the data before clicking Done."
			update.message.reply_text(text, reply_markup=markup)
			return TAKE_INFORMATION
	
	def loop_payment(self, bot, update, user_data):
		query = "SELECT name FROM user"
		#WHERE id<>{}".format(update.message.chat_id)
		self.cursor.execute(query)
		user = []
		row = self.cursor.fetchone()[0]
		#while row is not None:
		print(row)
			#if not user_data[row]:
		user.append(row)
			#if row in self.cursor.fetchone()[0]:
			#	continue
		keyboard = [user, ['Cancel', 'Finish']]
		markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
		update.message.reply_text("Who should be charged these expenses?", reply_markup=markup)
		return SET_PAYMENT
	
	def set_payment(self, bot, update, user_data):
		print("SET_PAYMENT")
		user_data[update.message.text] = True
		return LOOP_PAYMENT		
	
	def end_action(self, bot, update, user_data):
		if update.message.text =='Cancel':
			update.message.reply_text("All information deleted", reply_markup=ReplyKeyboardRemove())
			del user_data
			return ConversationHandler.END
		"""
		elif update.message.text =='Done':
			if user_data['Price'] is None or user_data['Description'] is None:
				update.message.reply_text("You forgot to give me some information, I'm sorry!", reply_markup=ReplyKeyboardRemove())
				return ConversationHandler.END
			else:
				msg = "The information collected is:\nPrice - {} \nDescription - {}".format(user_data['Price'], user_data['Description'])
				msg += "\nWho should be charged these expenses?"
				#self.add_expense(bot, update, update.message.chat_id, userd_data['Price'], user_data['Description'])
				update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
				return LOOP_PAYMENT
	"""
	def add_expense(self, bot, update, c_id, price, desc):
		try:
			query = "INSERT INTO expense(price, description, data_reg, user_id)"
			query += "values({}, '{}', CURRENT_DATE, {});".format(price, desc, c_id)
			self.cursor.execute(query)
			self.connect.commit()
			logging.info("Insert into table expense from {}: {} {}.".format(c_id, price, desc))
			bot.send_message(chat_id=c_id, text="Insert completed.")
			query2 = "SELECT LAST_INSERT_ROWID()"
			self.cursor.execute(query2)
			e_id = self.cursor.fetchone()[0]
			self.add_payment(c_id, e_id, price)
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
