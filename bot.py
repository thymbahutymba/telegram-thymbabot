import json, os, sqlite3, logging, tempfile
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler, RegexHandler, ConversationHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from sqlite3 import Error
from prettytable import PrettyTable

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO, filename='thymbabot.log')
CHOOSING, TAKE_DATA, TAKE_INFORMATION, SET_PAYMENT, USER_PAYMENT, REGISTER_PAYMENT = range(6)

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

	def error_callback(self, bot, update, error):
		logging.error("Update {} caused error {}.".format(update,error))

	def start_command(self, bot, update):
		welcome = "I'm Heisenberg.\n"
		welcome += "Type /help to display the command list."
		bot.send_message(chat_id=update.message.chat_id, text=welcome)

	def register_command(self, bot, update):
		c_id = update.message.chat_id
		c_username = update.message.from_user.username
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

	def report(self, bot,update,msg):
		bot.send_message(chat_id=self.cfg.get('admin_id'), text = msg)

	def ping_command(self, bot, update):
		bot.send_message(chat_id=update.message.chat_id, text="pong")

	def help_command(self, bot, update):
		message_help = "Command:\n"
		message_help += "/ping - ping the bot\n"
		message_help += "/help - help command\n"
		message_help += "/register - register your user\n"
		message_help += "/action - perform some action.\n"
		message_help += "/total - total of your expense"
		#message_help += "/print - show something."
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
			total = self.cursor.fetchone()[0]
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
			entry_points=[CommandHandler('action', self.action_command)],
			states={
				CHOOSING: [RegexHandler('^(Expense|Payment)$', self.first_choice, pass_user_data=True)],
				TAKE_INFORMATION: [RegexHandler('^(Price|Description|Debtor)$', self.take_information, pass_user_data=True)],
				TAKE_DATA: [MessageHandler(Filters.text, self.take_data, pass_user_data=True)],
				SET_PAYMENT: [MessageHandler(Filters.text, self.set_payment, pass_user_data=True)],
				USER_PAYMENT: [MessageHandler(Filters.text, self.user_payment, pass_user_data=True)],
				REGISTER_PAYMENT: [CallbackQueryHandler(self.register_payment, pass_user_data=True)]
				},
			fallbacks = [RegexHandler('^(Submit|Cancel)$', self.end_action, pass_user_data=True)],
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
			#self.dispatcher.add_handler(CommandHandler('print', self.print_command))
			#self.dispatcher.add_handler(CallbackQueryHandler(self.button))
			self.dispatcher.add_handler(insert_handler)
			self.updater.idle()
		except Exception as ecc:
			logging.error('error: ' + str(ecc))
			pass

	def simple_2choice(self, user_data):
		expense_keyboard = [['Price', 'Description'], ['Debtor', 'Cancel', 'Submit']]
		markup = ReplyKeyboardMarkup(expense_keyboard, one_time_keyboard=True)
		return markup

	def is_float(self, s):
		try:
			float(s)
			return True
		except Exception as ecc:
			logging.error("Error: " + str(ecc))
			return False

	def action_command(self, bot, update):
		if not self.check_register(bot, update):
			return ConversationHandler.END
		else:
			action_keyboard = [['Expense', 'Payment'], ['Pending\nComingSoon', 'Cancel']]
			markup = ReplyKeyboardMarkup(action_keyboard, one_time_keyboard=True)
			update.message.reply_text("Choice what you want to do.", reply_markup=markup)
			return CHOOSING

	def first_choice(self, bot, update, user_data):
		user_data['choice'] = update.message.text
		if user_data['choice'] == 'Expense':
			user_data['Price'] = None
			user_data['Description'] = None
			markup = self.simple_2choice(user_data)
			text = "Which information do you want to add?\nRemember that if you made a mistake, you can re-enter the data before clicking Submit."
			update.message.reply_text(text, reply_markup=markup)
			return TAKE_INFORMATION
		else:
			markup = self.payment_keyboard(update.message.chat_id)
			text = "Who did you pay?"
			update.message.reply_text(text, reply_markup=markup)
			return USER_PAYMENT

	def payment_keyboard(self, c_id):
		query = "SELECT DISTINCT U.name "
		query += "FROM payment P INNER JOIN expense E on P.expense_id=E.id "
		query += "INNER JOIN user U on E.user_id=U.id "
		query += "WHERE P.user_id=:chat_id"
		self.cursor.execute(query, {"chat_id": c_id})
		user = []
		for row in self.cursor:
			user.append(row[0])

		#TODO back button

		keyboard = [user, ['Cancel']]
		markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
		return markup

	def user_keyboard(self, update, user_data):
		query = "SELECT name FROM user WHERE id<>:id"
		user = []
		self.cursor.execute(query, {"id": update.message.chat_id})
		for row in self.cursor:
			if row[0] not in user_data:
				user.append(row[0])

		keyboard = [user, ['Back']]
		markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
		return markup

	def take_information(self, bot, update, user_data):
		if update.message.text == 'Debtor':
			markup = self.user_keyboard(update, user_data)
			update.message.reply_text("Who should be charged these expenses?", reply_markup=markup)
			return SET_PAYMENT

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
			del user_data['adding']

		markup = self.simple_2choice(user_data)
		text = "Which information do you want to add?\nRemember that if you made a mistake, you can re-enter the data before clicking Done."
		update.message.reply_text(text, reply_markup=markup)
		return TAKE_INFORMATION

	def set_payment(self, bot, update, user_data):
		if update.message.text == 'Back':
			markup = self.simple_2choice(user_data)
			text = "Which information do you want to add?\nRemember that if you made a mistake, you can re-enter the data before clicking Done."
			update.message.reply_text(text, reply_markup=markup)
			return TAKE_INFORMATION

		user_data[update.message.text] = True
		markup = self.user_keyboard(update, user_data)
		update.message.reply_text("Who should be charged these expenses?", reply_markup=markup)
		return SET_PAYMENT

	def end_action(self, bot, update, user_data):
		if update.message.text =='Cancel':
			update.message.reply_text("All information deleted.", reply_markup=ReplyKeyboardRemove())
			user_data.clear()
			return ConversationHandler.END
		elif user_data['Price'] is None or user_data['Description'] is None:
			update.message.reply_text("You forgot to give me some information, I'm sorry!", reply_markup=ReplyKeyboardRemove())
			user_data.clear()
			return ConversationHandler.END
		else:
			msg = "The added information are:\nPrice - {}€ \nDescription - {}\n".format(user_data['Price'], user_data['Description'])
			user = []
			query = "SELECT name FROM user"
			self.cursor.execute(query)
			for row in self.cursor:
				if row[0] in user_data:
					user.append(row)
			msg += "The user who will be charge the expese are:\n"
			for row in user:
				msg += "- " + str(row[0]) + "\n"
			self.add_expense(bot, update, round(user_data['Price'], 2), user_data['Description'], user)
			update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
			user_data.clear()
			return ConversationHandler.END

	def add_expense(self, bot, update, price, desc, user):
		try:
			query = "INSERT INTO expense(price, description, data_reg, user_id)"
			query += "values(:price, ':desc', CURRENT_DATE, :c_id);"#.format(price, desc, update.message.chat_id)
			self.cursor.execute(query, {"price": price, "desc": desc, "c_id": update.message.chat_id})
			self.connect.commit()
			logging.info("Insert into table expense from {}: {} {}.".format(update.message.chat_id, price, desc))
			query2 = "SELECT LAST_INSERT_ROWID()"
			self.cursor.execute(query2)
			e_id = self.cursor.fetchone()[0]
			self.add_payment(e_id, price, user)
		except Exception as e:
			logging.error("Insert into expense failed. Error: "+ str(e))
			update.message.reply_text("Insert into expense failed.")
			pass

	def add_payment(self, e_id, price, user):
		try:
			own_price = round(float(float(price)/(len(user)+1)),2)
			for row in user:
				query = "SELECT id FROM user WHERE name=':name'"
				self.cursor.execute(query, {"name": str(row[0])})
				c_id = int(self.cursor.fetchone()[0])
				query2 = "INSERT INTO payment(expense_id, user_id, import) values(:e_id, :c_id, :price)"
				self.cursor.execute(query2, {"e_id": e_id,"c_id": c_id,"price": own_price})
				self.connect.commit()
			logging.info("Insert into table payment completed.")
		except Exception as e:
			logging.error("Insert into payment failed. Error: " + str(e))
			update.message.reply_text("Insert into payment failed.")
			pass

	def user_payment(self, bot, update, user_data):
		user_data['user']=update.message.text
		query = "SELECT E.data_reg as Data, round(P.import, 2) as Import, E.description as Description, P.user_id, P.expense_id "
		query += "FROM payment P INNER JOIN expense E on P.expense_id=E.id "
		query += "INNER JOIN user U on E.user_id=U.id "
		#query += "INNER JOIN user U on U.id=P.user_id "
		query += "WHERE P.user_id=:c_id "
		query += "AND P.paid='FALSE' "
		query += "AND E.user_id = (SELECT U2.id FROM user U2 WHERE U2.name=:user) "
		query += "AND not exists "
		#SUSPEND TUPLE NOT PRESENT
		query += "(SELECT * FROM pending P "
		query += "WHERE P.master_id=U.id "
		query += "AND P.debtor_id=P.user_id "
		query += "AND P.expense_id=E.id) "
		query += "ORDER BY E.data_reg DESC"

		print(query)

		#TODO check if table is empty

		count_row = "SELECT count(*) FROM ( "+ query + " )"
		self.cursor.execute(count_row, {
					"c_id": update.message.chat_id,
					"user": user_data['user']
				})
		tot = self.cursor.fetchone()[0]

		self.cursor.execute(query, {
				"c_id": update.message.chat_id,
				"user": user_data['user']
			}
		)
		keyboard = []
		for i in range(0, tot):
			row = self.cursor.fetchone()
			part = row[0] + " " + str(row[1]) + "€ " + row[2]
			send = str(row[3]) + " " + str(row[4])
			keyboard += [[InlineKeyboardButton(part, callback_data=send)]]
		reply_markup = InlineKeyboardMarkup(keyboard)
		text = "Choose the payment that you made to {}.".format(user_data['user'])
		update.message.reply_text(text, reply_markup=reply_markup)
		return REGISTER_PAYMENT

	def register_payment(self, bot, update, user_data):
		s = update.callback_query.data.split(" ", 1)
		update.callback_query.message.delete()

		user_id = int(s[0])
		expense_id = int(s[1])
		query = "SELECT U.id "
		query += "FROM expense E INNER JOIN user U on E.user_id=U.id "
		query += "WHERE E.id=:e_id "
		query += "LIMIT 1"

		self.cursor.execute(query, {"e_id": expense_id})
		send_to = self.cursor.fetchone()[0]
		try:
			query = "INSERT INTO pending(master_id, debtor_id, expense_id) VALUES(?,?,?)"
			self.cursor.execute(query, (int(send_to), user_id, expense_id))
			self.connect.commit()
			logging.info("There is a new pending payment waiting to be accepted.")
		except Exception as e:
			logging.info("Insert into pending failed")

		query = "SELECT name FROM user WHERE id=:user_id"
		self.cursor.execute(query, {"user_id": user_id})
		debtor= self.cursor.fetchone()[0]

		update.callback_query.message.reply_text("Payment charged, pending confirmation by the creditor.", reply_markup=ReplyKeyboardRemove())
		text = "Payment confirmation request by: @{}. Check action pending to confirm.".format(debtor)
		bot.send_message(chat_id=int(send_to), text = text)

		user_data.clear()
		return ConversationHandler.END
