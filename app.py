import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DB_DIR = '/tmp' if os.environ.get('VERCEL') else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'todos.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
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

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/todos', methods=['GET'])
def get_todos():
    status = request.args.get('status', 'all')
    priority = request.args.get('priority', 'all')
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()

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

    with get_db() as conn:
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

    with get_db() as conn:
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

    with get_db() as conn:
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
    with get_db() as conn:
        existing = conn.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()
        if not existing:
            return jsonify({'error': '해당 할일을 찾을 수 없습니다.'}), 404

        conn.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        conn.commit()

    return jsonify({'success': True, 'message': '삭제되었습니다.'})

@app.route('/api/todos/clear-completed', methods=['POST'])
def clear_completed():
    with get_db() as conn:
        cursor = conn.execute('DELETE FROM todos WHERE completed = 1')
        conn.commit()
        deleted_count = cursor.rowcount

    return jsonify({'success': True, 'deleted': deleted_count})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    with get_db() as conn:
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
        'categories': categories
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
