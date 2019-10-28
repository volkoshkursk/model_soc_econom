import sqlite3
import mysql.connector
import re
import tqdm
import argparse
import logging.config
"""
Вспомогательный скрипт, необходимый для миграции и очистки баз
"""


def load(conn_in):
    """
    Загрузка данных из соединения conn_in
    :param conn_in: соединение с бд
    :return: список
    """
    cursor_in = conn_in.cursor()
    cursor_in.execute('select * from inp')
    result = cursor_in.fetchall()
    cursor_in.close()
    conn_in.close()
    return result


def save(conn_out, data):
    """
    выгрузка в бд
    :param conn_out: соединение с бд
    :param data: данные (формат вывод load, м б любой итерируемой сущностью)
    """
    cursor = conn_out.cursor()

    for obj in tqdm.tqdm(data):
        command = "INSERT into inp values (" + "'" + re.sub(r'None', 'NULL', str(obj[0])) + "','" + \
                  re.sub(r'None', 'NULL', str(obj[1])) + "','" + \
                  re.sub(r'None', 'NULL', str(obj[2])) + "','" + re.sub(r'None', 'NULL', str(obj[3])) \
                  + "','" + re.sub(r'None', 'NULL', str(obj[4])) + "'," + re.sub(r'None', 'NULL', str(obj[5])) + \
                  ',' + re.sub(r'None', 'NULL', str(obj[6])) + ',' + re.sub(r'None', 'NULL', str(obj[7])) \
                  + ",'" + re.sub(r'None', 'NULL', str(obj[8])) + "'," + re.sub(r'None', 'NULL', str(obj[9])) \
                  + ',"' + re.sub(r'None', 'NULL', str(obj[10])) + '",' + re.sub(r'None', 'NULL', str(obj[11])) \
                  + ",'" + re.sub(r'None', 'NULL', str(obj[12])) + "');"
        cursor.execute(command)
    conn_out.commit()
    cursor.close()
    conn_out.close()


def new_db():
    pass


if __name__ == '__main__':
    logging.config.fileConfig('log_config')
    logger = logging.getLogger("root")
    logger.info("program started")
    parser = argparse.ArgumentParser(description='support script')
    parser.add_argument(
        '-b',
        '--back',
        action='store_const',
        const=True,
        default=False,
        help='if true, then copy db from MySQL to SQLite3, else copy from SQLite3 to MySQL (default: False)'
    )
    parser.add_argument(
        '-f',
        '--filter',
        action='store_const',
        const=False,
        default=True,
        help='If is needed to remove duplicates (default: True)'
    )
    parser.add_argument(
        '-n',
        '--new',
        action='store_const',
        const=True,
        default=False,
        help='If is needed to create new db (collection_temp.db) (default: False)'
    )
    parser.add_argument(
        '-c',
        '--check',
        action='store_const',
        const=True,
        default=False,
        help='Check db value (default: False)'
    )
    arg = parser.parse_args()
    logger.info("args: " + str(arg.back) + str(arg.filter) + str(arg.new) + str(arg.check))
    if arg.check:
        f = open('history')
        history = []
        for lines in tqdm.tqdm(f):
            history.append(tuple(map(lambda x: int(x), lines.split(','))))
        f.close()
        conn = mysql.connector.connect(user='user', password='goszakupki', host='localhost', database='collection')
        base = load(conn)
        print('до: ', end=' ')
        before = len(base)
        print(before, end=' ')
        print(before - history[len(history)-1][0])
        after = len(set(base))
        print('после: ', end=' ')
        print(after, end=' ')
        print(after - history[len(history)-1][1])
        f = open('history', 'a')
        f.write(str(before) + ',' + str(after) + '\n')
        f.close()
    else:
        if arg.back:
            conn = mysql.connector.connect(user='user', password='goszakupki', host='localhost', database='collection')
            base = load(conn)
        else:
            base = load(sqlite3.connect('collection.db'))
        if arg.filter:
            print('до: ', end=' ')
            print(len(base))
            base = set(base)
            print('после: ', end=' ')
            print(len(base))
        else:
            print(len(base))
        if arg.back:
            sqlite3.connect('collection.db')
            save(sqlite3.connect('collection.db'), base)
        else:
            conn = mysql.connector.connect(user='user', password='goszakupki', host='localhost', database='collection')
            save(conn, base)
