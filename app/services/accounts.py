"""Five identity categories, distinct registered students, and preserved legacy records.

Identity comes from the unique login name, never the mutable nickname. Existing
administrative permissions remain independent of the display category.
"""
import re
from datetime import datetime

from app import auth
from app.services import blindbox, events

CATEGORIES = [('dad','爸爸'),('mom','妈妈'),('sunny','Sunny'),('student','同学'),('guest','访客')]
FAMILY = {'dad','mom','sunny'}
RESERVED = FAMILY | {'guest','student','classmate','admin','administrator','同学','访客'}


def kind(row):
    name = auth.normalize_username(row['username'] or '')
    if name in FAMILY:
        return name
    return 'guest' if not name or name == 'guest' else 'student'


def historical(row):
    return 'account_status' in row.keys() and row['account_status'] == 'historical'


def _item(row):
    return {k:row[k] for k in ('id','username','nickname','points','created_at')} | {
        'account_type':kind(row),'is_historical':historical(row),'is_admin':row['role']=='admin',
        'last_seen':(row['last_seen'] or '')[:10], 'progress_count':row['progress_count']}


def directory(conn):
    rows=conn.execute('SELECT u.*,(SELECT count(*) FROM progress p WHERE p.user_id=u.id) AS progress_count FROM users u ORDER BY u.created_at,u.id').fetchall()
    registered=[_item(r) for r in rows if kind(r)!='guest' and not historical(r)]
    guests=[r for r in rows if kind(r)=='guest' and not historical(r)]
    legacy=[_item(r) for r in rows if historical(r)]
    groups=[{'type':key,'label':label,'users':[r for r in registered if r['account_type']==key],
             'count':len(guests) if key=='guest' else sum(r['account_type']==key for r in registered)}
            for key,label in CATEGORIES]
    return {'users':registered,'groups':groups,'registered_count':len(registered),
            'guest_count':len(guests),'historical_count':len(legacy),'historical_users':legacy}


def create_student(conn, username, nickname, password, actor, legacy_user_id=None):
    name=auth.normalize_username(username)
    nick=nickname.strip()
    if name in RESERVED or not re.fullmatch(r'[a-z][a-z0-9_-]{2,31}',name):
        raise ValueError('账号需为3–32位，以字母开头，可用字母、数字、下划线和短横线；不能使用系统保留名称')
    if not 1<=len(nick)<=20 or not 8<=len(password)<=128 or password.isspace():
        raise ValueError('昵称为1–20字，初始密码为8–128位')
    if conn.execute('SELECT 1 FROM users WHERE lower(trim(username))=?',(name,)).fetchone():
        raise ValueError('该账号名已被使用')
    now=datetime.now().isoformat(timespec='seconds')
    pwd=auth.hash_password(password)
    if legacy_user_id:
        row=conn.execute('SELECT * FROM users WHERE id=?',(legacy_user_id,)).fetchone()
        if not row or not historical(row) or (row['username'] or '').strip() or row['role']:
            raise ValueError('只能将未登记的历史临时记录转为同学账号')
        uid=row['id']
        conn.execute("UPDATE users SET username=?,nickname=?,password_hash=?,account_status='active' WHERE id=?",
                     (name,nick,pwd,uid))
        # 历史同步码和旧设备令牌不应成为新正式账号的隐含登录入口。
        conn.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
        conn.execute('UPDATE users SET sync_code=?,token_hash=? WHERE id=?',
                     (auth.normalize_sync_code(auth.new_sync_code()),auth.hash_token(auth.new_token()),uid))
    else:
        uid=auth.new_id()
        conn.execute('INSERT INTO users(id,token_hash,sync_code,username,nickname,password_hash,created_at,last_seen) VALUES(?,?,?,?,?,?,?,?)',
            (uid,auth.hash_token(auth.new_token()),auth.normalize_sync_code(auth.new_sync_code()),name,nick,pwd,now,now))
        blindbox.grant_daily_tickets(conn,uid,initial=True)
    events.log(conn,uid,'student_registered','student_registered',{'actor':actor,'from_history':bool(legacy_user_id)})
    return {'id':uid,'username':name,'nickname':nick,'account_type':'student','is_admin':False,'from_history':bool(legacy_user_id)}
