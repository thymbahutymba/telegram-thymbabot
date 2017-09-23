#!/usr/bin/env python3

import sqlite3, logging
from sqlite3 import Error

from bot import *

def main():
	logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='thymbabot.log')
	
	thymba = core()
	thymba.start()

if __name__ == '__main__':
    main()
