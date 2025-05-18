import sqlite3


def create_table():
    conn = sqlite3.connect('base/base.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER DEFAULT 0,
            register TEXT DEFAULT 0,
            ban INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


def format_fonts_count(count):
    forms = ['шрифт', 'шрифта', 'шрифтов']
    remainder = count % 100

    if 11 <= remainder <= 19:
        return f"{count} {forms[2]}"
    last_digit = count % 10
    if last_digit == 1:
        return f"{count} {forms[0]}"
    elif last_digit in [2, 3, 4]:
        return f"{count} {forms[1]}"
    else:
        return f"{count} {forms[2]}"
