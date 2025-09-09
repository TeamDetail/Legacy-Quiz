import mysql.connector
from mysql.connector import Error
import time
import os

DB_CONFIG = {
    # 'host': os.getenv('DB_HOST'),
    # 'database': os.getenv('DB_NAME'),
    # 'user': os.getenv('DB_USER'),
    # 'password': os.getenv('DB_PASSWORD')
    'database': 'legacy',
    'user': 'root',
    'password': 'n9800211'
}