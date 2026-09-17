import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# -------------------------------------------------------------
# 데이터베이스 설정 (Supabase 우선, 미설정 시 SQLite 폴백)
# -------------------------------------------------------------
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '').strip()

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"[DB INFO] Connected to Supabase: {SUPABASE_URL}")
    except Exception as e:
        print(f"[DB WARN] Supabase 초기화 실패, SQLite로 폴백합니다: {e}")
        supabase = None

# SQLite 폴백 설정
DB_DIR = '/tmp' if os.environ.get('VERCEL') else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'todos.db')

def get_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite():
    with get_sqlite() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority TEXT DEFAULT 'medium',
                category TEXT DEFAULT '일반',
                due_date TEXT DEFAULT '',
                completed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        conn.commit()

init_sqlite()
init_db = init_sqlite

# -------------------------------------------------------------
# 웹 페이지 라우트
# -------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# -------------------------------------------------------------
# API 라우트
# -------------------------------------------------------------
@app.route('/api/db-status', methods=['GET'])
def db_status():
    """현재 연결된 데이터베이스 상태 확인"""
    return jsonify({
        'engine': 'supabase' if supabase else 'sqlite',
        'is_supabase': bool(supabase),
        'supabase_url': SUPABASE_URL if SUPABASE_URL else None
    })

@app.route('/api/todos', methods=['GET'])
def get_todos():
    status = request.args.get('status', 'all')
    priority = request.args.get('priority', 'all')
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()

    if supabase:
        try:
            query = supabase.table('todos').select('*')
            if status == 'active':
                query = query.eq('completed', 0)
            elif status == 'completed':
                query = query.eq('completed', 1)

            if priority != 'all':
                query = query.eq('priority', priority)

            if category != 'all':
                query = query.eq('category', category)

            if search:
                query = query.or_(f'title.ilike.%{search}%,description.ilike.%{search}%')

            res = query.order('id', desc=True).execute()
            todos = res.data or []

            priority_order = {'high': 1, 'medium': 2, 'low': 3}
            todos.sort(key=lambda t: (
                int(t.get('completed', 0) or 0),
                priority_order.get(t.get('priority'), 4),
                -int(t.get('id', 0))
            ))
            return jsonify(todos)
        except Exception as e:
            print(f"[Supabase Query Error] {e}")

    # SQLite 폴백 조회
    query = "SELECT * FROM todos WHERE 1=1"
    params = []

    if status == 'active':
        query += " AND completed = 0"
    elif status == 'completed':
        query += " AND completed = 1"

    if priority != 'all':
        query += " AND priority = ?"
        params.append(priority)

    if category != 'all':
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    query += " ORDER BY completed ASC, CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, id DESC"

    with get_sqlite() as conn:
        rows = conn.execute(query, params).fetchall()
        todos = [dict(row) for row in rows]

    return jsonify(todos)

@app.route('/api/todos', methods=['POST'])
def create_todo():
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': '할일 제목을 입력해주세요.'}), 400

    description = data.get('description', '').strip()
    priority = data.get('priority', 'medium')
    category = data.get('category', '일반')
    due_date = data.get('due_date', '')
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if supabase:
        try:
            res = supabase.table('todos').insert({
                'title': title,
                'description': description,
                'priority': priority,
                'category': category,
                'due_date': due_date,
                'completed': 0,
                'created_at': created_at
            }).execute()
            if res.data:
                return jsonify(res.data[0]), 201
        except Exception as e:
            print(f"[Supabase Insert Error] {e}")

    with get_sqlite() as conn:
        cursor = conn.execute('''
            INSERT INTO todos (title, description, priority, category, due_date, completed, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
        ''', (title, description, priority, category, due_date, created_at))
        conn.commit()
        todo_id = cursor.lastrowid
        row = conn.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()

    return jsonify(dict(row)), 201

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    data = request.get_json() or {}

    if supabase:
        try:
            existing = supabase.table('todos').select('*').eq('id', todo_id).execute()
            if not existing.data:
                return jsonify({'error': '해당 할일을 찾을 수 없습니다.'}), 404

            prev = existing.data[0]
            title = data.get('title', prev['title']).strip()
            if not title:
                return jsonify({'error': '제목은 비어있을 수 없습니다.'}), 400

            update_data = {
                'title': title,
                'description': data.get('description', prev.get('description', '')),
                'priority': data.get('priority', prev.get('priority', 'medium')),
                'category': data.get('category', prev.get('category', '일반')),
                'due_date': data.get('due_date', prev.get('due_date', '')),
                'completed': int(data.get('completed', prev.get('completed', 0)))
            }

            res = supabase.table('todos').update(update_data).eq('id', todo_id).execute()
            if res.data:
                return jsonify(res.data[0])
        except Exception as e:
            print(f"[Supabase Update Error] {e}")

    with get_sqlite() as conn:
        existing = conn.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()
        if not existing:
            return jsonify({'error': '해당 할일을 찾을 수 없습니다.'}), 404

        title = data.get('title', existing['title']).strip()
        if not title:
            return jsonify({'error': '제목은 비어있을 수 없습니다.'}), 400

        description = data.get('description', existing['description'])
        priority = data.get('priority', existing['priority'])
        category = data.get('category', existing['category'])
        due_date = data.get('due_date', existing['due_date'])
        completed = int(data.get('completed', existing['completed']))

        conn.execute('''
            UPDATE todos
            SET title = ?, description = ?, priority = ?, category = ?, due_date = ?, completed = ?
            WHERE id = ?
        ''', (title, description, priority, category, due_date, completed, todo_id))
        conn.commit()
        row = conn.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()

    return jsonify(dict(row))

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    if supabase:
        try:
            existing = supabase.table('todos').select('id').eq('id', todo_id).execute()
            if not existing.data:
                return jsonify({'error': '해당 할일을 찾을 수 없습니다.'}), 404

            supabase.table('todos').delete().eq('id', todo_id).execute()
            return jsonify({'success': True, 'message': '삭제되었습니다.'})
        except Exception as e:
            print(f"[Supabase Delete Error] {e}")

    with get_sqlite() as conn:
        existing = conn.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()
        if not existing:
            return jsonify({'error': '해당 할일을 찾을 수 없습니다.'}), 404

        conn.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        conn.commit()

    return jsonify({'success': True, 'message': '삭제되었습니다.'})

@app.route('/api/todos/clear-completed', methods=['POST'])
def clear_completed():
    if supabase:
        try:
            res = supabase.table('todos').delete().eq('completed', 1).execute()
            deleted_count = len(res.data) if res.data else 0
            return jsonify({'success': True, 'deleted': deleted_count})
        except Exception as e:
            print(f"[Supabase Clear Completed Error] {e}")

    with get_sqlite() as conn:
        cursor = conn.execute('DELETE FROM todos WHERE completed = 1')
        conn.commit()
        deleted_count = cursor.rowcount

    return jsonify({'success': True, 'deleted': deleted_count})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    if supabase:
        try:
            res = supabase.table('todos').select('completed, category').execute()
            rows = res.data or []
            total = len(rows)
            completed = sum(1 for r in rows if int(r.get('completed', 0) or 0) == 1)
            active = total - completed
            rate = round((completed / total * 100), 1) if total > 0 else 0
            categories = sorted(list({r.get('category') for r in rows if r.get('category')}))

            return jsonify({
                'total': total,
                'completed': completed,
                'active': active,
                'completion_rate': rate,
                'categories': categories,
                'engine': 'supabase'
            })
        except Exception as e:
            print(f"[Supabase Stats Error] {e}")

    with get_sqlite() as conn:
        total = conn.execute('SELECT COUNT(*) FROM todos').fetchone()[0]
        completed = conn.execute('SELECT COUNT(*) FROM todos WHERE completed = 1').fetchone()[0]
        active = total - completed
        rate = round((completed / total * 100), 1) if total > 0 else 0
        categories = [row[0] for row in conn.execute('SELECT DISTINCT category FROM todos WHERE category != ""').fetchall()]

    return jsonify({
        'total': total,
        'completed': completed,
        'active': active,
        'completion_rate': rate,
        'categories': categories,
        'engine': 'sqlite'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
