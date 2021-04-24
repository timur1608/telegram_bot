import sqlite3
from random import randint


class Sqliter():
    def __init__(self, database, table):
        self.data = sqlite3.connect(database)
        self.table = table
        self.cur = self.data.cursor()

    def count_rows(self):
        res = self.cur.execute('''SELECT * FROM [quiz]''').fetchall()
        return len(res)

    def select_user_completed_questions(self, user_id):
        res = self.cur.execute('''SELECT quiz_ids FROM balance WHERE user_id = ?''', (user_id,)).fetchall()[0]
        return res

    def select_question(self, user_id):
        if len(self.select_user_completed_questions(user_id=user_id)) != self.count_rows():
            rand_num = randint(1, self.count_rows())
            while rand_num in self.select_user_completed_questions(user_id=user_id):
                rand_num = randint(1, self.count_rows())
            res = self.cur.execute('''SELECT * FROM [quiz] WHERE id=?''', (rand_num,)).fetchall()[0]
            return res
        else:
            return 'error'

    def create_user(self, user_id):
        f = False
        for i in self.all_users():
            if user_id == int(i):
                f = True
                break
        if not f:
            balance = 0
            self.cur.execute('''INSERT INTO balance VALUES (?, ?)''', (user_id, balance))

    def select_user(self, user_id):
        res = self.cur.execute('''SELECT balance FROM balance WHERE user_id=?''', (user_id,)).fetchall()[0][0]
        return res

    def all_users(self):
        res = [i[0] for i in self.cur.execute('''SELECT user_id FROM [balance]''').fetchall()]
        return res

    def bought_book(self, user_id):
        balance_for_user_id = \
            self.cur.execute('''SELECT balance FROM [balance] WHERE user_id=''', (user_id)).fetchall()[0]
        if balance_for_user_id > 0:
            self.cur.execute('''UPDATE [balance] SET balance = balance - 5 WHERE user_id=''', (user_id,))
        else:
            return

    def close(self):
        self.data.commit()
        self.data.close()
