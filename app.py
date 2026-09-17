import os
import sqlite3
from datetime import date, datetime
from flask import Flask, render_template, request, jsonify

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
DB_PATH = os.path.join(DB_DIR, 'festivals.db')

REGIONS = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
           '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']
CATEGORIES = ['문화예술', '음식', '전통', '음악', '자연/생태', '불빛/조명', '기타']

SEED_FESTIVALS = [
    ('부산불꽃축제', '부산', '수영구', '불빛/조명', '2026-10-24', '2026-10-24', '광안리 해수욕장', '밤하늘을 수놓는 국내 최대 규모의 불꽃 축제.'),
    ('진주남강유등축제', '경남', '진주시', '불빛/조명', '2026-10-01', '2026-10-12', '남강 일원', '강물 위를 수놓는 형형색색의 유등과 전통 문화 체험.'),
    ('안동국제탈춤페스티벌', '경북', '안동시', '전통', '2026-09-25', '2026-10-04', '탈춤공원 일원', '세계 각국의 탈춤과 안동의 전통 문화를 즐기는 축제.'),
    ('자라섬재즈페스티벌', '경기', '가평군', '음악', '2026-10-09', '2026-10-11', '자라섬 일원', '가을 강변에서 즐기는 국내 최대 재즈 페스티벌.'),
    ('김제지평선축제', '전북', '김제시', '전통', '2026-09-30', '2026-10-04', '벽골제 일원', '너른 들녘에서 펼쳐지는 풍요의 가을걷이 축제.'),
    ('서울빛초롱축제', '서울', '종로구', '불빛/조명', '2026-11-06', '2026-11-22', '청계천 일원', '청계천을 가득 채우는 대형 등불 전시와 야경.'),
    ('광주프린지페스티벌', '광주', '동구', '문화예술', '2026-10-16', '2026-10-18', '충장로 일대', '거리 곳곳에서 펼쳐지는 자유로운 예술가들의 무대.'),
    ('순천만갈대축제', '전남', '순천시', '자연/생태', '2026-10-23', '2026-10-26', '순천만 국가정원', '은빛 갈대밭과 습지 생태를 만끽하는 가을 축제.'),
    ('보령머드축제', '충남', '보령시', '문화예술', '2026-07-18', '2026-07-26', '대천해수욕장', '머드를 주제로 한 국내 대표 여름 체험 축제.'),
    ('대구치맥페스티벌', '대구', '수성구', '음식', '2026-07-22', '2026-07-26', '두류공원', '치킨과 맥주를 즐기며 여름밤을 즐기는 축제.'),
    ('함평나비대축제', '전남', '함평군', '자연/생태', '2026-04-24', '2026-05-06', '함평엑스포공원', '나비와 꽃으로 가득한 봄철 생태 체험 축제.'),
    ('화천산천어축제', '강원', '화천군', '자연/생태', '2027-01-08', '2027-01-31', '화천천 일원', '얼음낚시로 산천어를 잡는 겨울 대표 축제.'),
]


def get_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite():
    with get_sqlite() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS festivals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                region TEXT NOT NULL,
                city TEXT DEFAULT '',
                category TEXT DEFAULT '기타',
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                location TEXT DEFAULT '',
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        ''')
        conn.commit()
        count = conn.execute('SELECT COUNT(*) FROM festivals').fetchone()[0]
        if count == 0:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.executemany('''
                INSERT INTO festivals (name, region, city, category, start_date, end_date, location, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [seed + (now,) for seed in SEED_FESTIVALS])
            conn.commit()


init_sqlite()


def compute_status(start_date, end_date):
    """오늘 날짜 기준으로 진행중 / 예정 / 종료 상태와 D-day를 계산."""
    today = date.today()
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date or start_date)
    except (ValueError, TypeError):
        return 'upcoming', None

    if today < start:
        return 'upcoming', (start - today).days
    elif start <= today <= end:
        return 'ongoing', (end - today).days
    else:
        return 'ended', (today - end).days


def enrich(festival):
    status, d_day = compute_status(festival.get('start_date'), festival.get('end_date'))
    festival['status'] = status
    festival['d_day'] = d_day
    return festival


def sort_key(festival):
    rank = {'ongoing': 0, 'upcoming': 1, 'ended': 2}
    try:
        ordinal = date.fromisoformat(festival['start_date']).toordinal()
    except (ValueError, TypeError):
        ordinal = 0
    if festival['status'] == 'ended':
        return (rank[festival['status']], -ordinal)
    return (rank[festival['status']], ordinal)


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


@app.route('/api/festivals', methods=['GET'])
def get_festivals():
    region = request.args.get('region', 'all')
    category = request.args.get('category', 'all')
    status = request.args.get('status', 'all')
    search = request.args.get('search', '').strip()

    rows = None

    if supabase:
        try:
            query = supabase.table('festivals').select('*')
            if region != 'all':
                query = query.eq('region', region)
            if category != 'all':
                query = query.eq('category', category)
            if search:
                query = query.or_(f'name.ilike.%{search}%,description.ilike.%{search}%')
            res = query.execute()
            rows = res.data or []
        except Exception as e:
            print(f"[Supabase Query Error] {e}")
            rows = None

    if rows is None:
        query = "SELECT * FROM festivals WHERE 1=1"
        params = []
        if region != 'all':
            query += " AND region = ?"
            params.append(region)
        if category != 'all':
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])

        with get_sqlite() as conn:
            fetched = conn.execute(query, params).fetchall()
            rows = [dict(row) for row in fetched]

    festivals = [enrich(dict(row)) for row in rows]
    if status != 'all':
        festivals = [f for f in festivals if f['status'] == status]
    festivals.sort(key=sort_key)

    return jsonify(festivals)


@app.route('/api/festivals', methods=['POST'])
def create_festival():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    region = data.get('region', '').strip()
    start_date = data.get('start_date', '').strip()

    if not name:
        return jsonify({'error': '축제명을 입력해주세요.'}), 400
    if not region:
        return jsonify({'error': '지역을 선택해주세요.'}), 400
    if not start_date:
        return jsonify({'error': '시작일을 입력해주세요.'}), 400

    city = data.get('city', '').strip()
    category = data.get('category', '기타')
    end_date = data.get('end_date', '').strip() or start_date
    location = data.get('location', '').strip()
    description = data.get('description', '').strip()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    payload = {
        'name': name, 'region': region, 'city': city, 'category': category,
        'start_date': start_date, 'end_date': end_date, 'location': location,
        'description': description, 'created_at': created_at
    }

    if supabase:
        try:
            res = supabase.table('festivals').insert(payload).execute()
            if res.data:
                return jsonify(enrich(res.data[0])), 201
        except Exception as e:
            print(f"[Supabase Insert Error] {e}")

    with get_sqlite() as conn:
        cursor = conn.execute('''
            INSERT INTO festivals (name, region, city, category, start_date, end_date, location, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, region, city, category, start_date, end_date, location, description, created_at))
        conn.commit()
        festival_id = cursor.lastrowid
        row = conn.execute('SELECT * FROM festivals WHERE id = ?', (festival_id,)).fetchone()

    return jsonify(enrich(dict(row))), 201


@app.route('/api/festivals/<int:festival_id>', methods=['PUT'])
def update_festival(festival_id):
    data = request.get_json() or {}

    if supabase:
        try:
            existing = supabase.table('festivals').select('*').eq('id', festival_id).execute()
            if not existing.data:
                return jsonify({'error': '해당 축제를 찾을 수 없습니다.'}), 404

            prev = existing.data[0]
            name = data.get('name', prev['name']).strip()
            region = data.get('region', prev['region']).strip()
            start_date = data.get('start_date', prev['start_date']).strip()
            if not name:
                return jsonify({'error': '축제명은 비어있을 수 없습니다.'}), 400
            if not region:
                return jsonify({'error': '지역은 비어있을 수 없습니다.'}), 400
            if not start_date:
                return jsonify({'error': '시작일은 비어있을 수 없습니다.'}), 400

            update_data = {
                'name': name,
                'region': region,
                'city': data.get('city', prev.get('city', '')),
                'category': data.get('category', prev.get('category', '기타')),
                'start_date': start_date,
                'end_date': data.get('end_date', prev.get('end_date', '')).strip() or start_date,
                'location': data.get('location', prev.get('location', '')),
                'description': data.get('description', prev.get('description', ''))
            }

            res = supabase.table('festivals').update(update_data).eq('id', festival_id).execute()
            if res.data:
                return jsonify(enrich(res.data[0]))
        except Exception as e:
            print(f"[Supabase Update Error] {e}")

    with get_sqlite() as conn:
        existing = conn.execute('SELECT * FROM festivals WHERE id = ?', (festival_id,)).fetchone()
        if not existing:
            return jsonify({'error': '해당 축제를 찾을 수 없습니다.'}), 404

        name = data.get('name', existing['name']).strip()
        region = data.get('region', existing['region']).strip()
        start_date = data.get('start_date', existing['start_date']).strip()
        if not name:
            return jsonify({'error': '축제명은 비어있을 수 없습니다.'}), 400
        if not region:
            return jsonify({'error': '지역은 비어있을 수 없습니다.'}), 400
        if not start_date:
            return jsonify({'error': '시작일은 비어있을 수 없습니다.'}), 400

        city = data.get('city', existing['city'])
        category = data.get('category', existing['category'])
        end_date = (data.get('end_date', existing['end_date']) or '').strip() or start_date
        location = data.get('location', existing['location'])
        description = data.get('description', existing['description'])

        conn.execute('''
            UPDATE festivals
            SET name = ?, region = ?, city = ?, category = ?, start_date = ?, end_date = ?, location = ?, description = ?
            WHERE id = ?
        ''', (name, region, city, category, start_date, end_date, location, description, festival_id))
        conn.commit()
        row = conn.execute('SELECT * FROM festivals WHERE id = ?', (festival_id,)).fetchone()

    return jsonify(enrich(dict(row)))


@app.route('/api/festivals/<int:festival_id>', methods=['DELETE'])
def delete_festival(festival_id):
    if supabase:
        try:
            existing = supabase.table('festivals').select('id').eq('id', festival_id).execute()
            if not existing.data:
                return jsonify({'error': '해당 축제를 찾을 수 없습니다.'}), 404

            supabase.table('festivals').delete().eq('id', festival_id).execute()
            return jsonify({'success': True, 'message': '삭제되었습니다.'})
        except Exception as e:
            print(f"[Supabase Delete Error] {e}")

    with get_sqlite() as conn:
        existing = conn.execute('SELECT * FROM festivals WHERE id = ?', (festival_id,)).fetchone()
        if not existing:
            return jsonify({'error': '해당 축제를 찾을 수 없습니다.'}), 404

        conn.execute('DELETE FROM festivals WHERE id = ?', (festival_id,))
        conn.commit()

    return jsonify({'success': True, 'message': '삭제되었습니다.'})


@app.route('/api/festivals/clear-ended', methods=['POST'])
def clear_ended():
    today = date.today().isoformat()

    if supabase:
        try:
            res = supabase.table('festivals').delete().lt('end_date', today).execute()
            deleted_count = len(res.data) if res.data else 0
            return jsonify({'success': True, 'deleted': deleted_count})
        except Exception as e:
            print(f"[Supabase Clear Ended Error] {e}")

    with get_sqlite() as conn:
        cursor = conn.execute('DELETE FROM festivals WHERE end_date < ?', (today,))
        conn.commit()
        deleted_count = cursor.rowcount

    return jsonify({'success': True, 'deleted': deleted_count})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    rows = None

    if supabase:
        try:
            res = supabase.table('festivals').select('region, category, start_date, end_date').execute()
            rows = res.data or []
        except Exception as e:
            print(f"[Supabase Stats Error] {e}")
            rows = None

    engine = 'supabase' if rows is not None else 'sqlite'
    if rows is None:
        with get_sqlite() as conn:
            fetched = conn.execute('SELECT region, category, start_date, end_date FROM festivals').fetchall()
            rows = [dict(row) for row in fetched]

    total = len(rows)
    ongoing = sum(1 for r in rows if compute_status(r.get('start_date'), r.get('end_date'))[0] == 'ongoing')
    upcoming = sum(1 for r in rows if compute_status(r.get('start_date'), r.get('end_date'))[0] == 'upcoming')
    ended = total - ongoing - upcoming
    regions = sorted({r.get('region') for r in rows if r.get('region')})
    categories = sorted({r.get('category') for r in rows if r.get('category')})
    ongoing_rate = round((ongoing / total * 100), 1) if total > 0 else 0

    return jsonify({
        'total': total,
        'ongoing': ongoing,
        'upcoming': upcoming,
        'ended': ended,
        'ongoing_rate': ongoing_rate,
        'regions': regions,
        'categories': categories,
        'engine': engine
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
