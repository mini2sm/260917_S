import time
import urllib.request
import urllib.parse
import json
import threading
import sys
import os

from app import app, init_db

PORT = 5005

def run_server():
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)

def test_api():
    base_url = f"http://127.0.0.1:{PORT}"
    print(f"[*] 테스트 서버에 연결 중: {base_url}")
    
    # 1. 헬스 체크 / 메인 페이지 서빙
    try:
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req, timeout=5) as res:
            assert res.status == 200
            html = res.read().decode('utf-8')
            assert 'TaskFlow' in html
            print("  [PASS] 1. 메인 페이지 (index.html) 서빙 200 OK")
    except Exception as e:
        print(f"  [FAIL] 1. 메인 페이지 접근 실패: {e}")
        return False

    # 2. 할일 생성 (POST /api/todos)
    todo_ids = []
    sample_todos = [
        {"title": "Flask 웹앱 구현 완성하기", "description": "할일 관리 웹앱 코드 작성", "priority": "high", "category": "업무", "due_date": "2026-09-18"},
        {"title": "파이썬 기초 복습하기", "description": "Flask 및 SQLite 학습", "priority": "medium", "category": "학습", "due_date": "2026-09-20"},
        {"title": "물 2L 마시기", "description": "건강 관리", "priority": "low", "category": "개인", "due_date": "2026-09-17"}
    ]

    for item in sample_todos:
        data = json.dumps(item).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/todos", data=data, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=5) as res:
            assert res.status == 201
            body = json.loads(res.read().decode('utf-8'))
            assert body['title'] == item['title']
            todo_ids.append(body['id'])
    print(f"  [PASS] 2. 할일 3건 생성 완료 (IDs: {todo_ids})")

    # 3. 할일 목록 조회 (GET /api/todos)
    req = urllib.request.Request(f"{base_url}/api/todos")
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200
        todos = json.loads(res.read().decode('utf-8'))
        assert len(todos) >= 3
        print(f"  [PASS] 3. 할일 목록 조회 성공 (조회된 건수: {len(todos)})")

    # 4. 할일 상태 완료로 업데이트 (PUT /api/todos/<id>)
    target_id = todo_ids[0]
    update_data = json.dumps({"completed": 1}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/api/todos/{target_id}", data=update_data, headers={'Content-Type': 'application/json'}, method='PUT')
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200
        updated = json.loads(res.read().decode('utf-8'))
        assert updated['completed'] == 1
        print(f"  [PASS] 4. 할일 완료 토글 성공 (ID: {target_id}, completed=1)")

    # 5. 통계 조회 (GET /api/stats)
    req = urllib.request.Request(f"{base_url}/api/stats")
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200
        stats = json.loads(res.read().decode('utf-8'))
        assert stats['total'] >= 3
        assert stats['completed'] >= 1
        print(f"  [PASS] 5. 대시보드 통계 검증 완료 (전체: {stats['total']}, 완료: {stats['completed']}, 달성률: {stats['completion_rate']}%)")

    # 6. 할일 단건 삭제 (DELETE /api/todos/<id>)
    delete_id = todo_ids[2]
    req = urllib.request.Request(f"{base_url}/api/todos/{delete_id}", method='DELETE')
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200
        print(f"  [PASS] 6. 할일 삭제 성공 (ID: {delete_id})")

    print("\n[SUCCESS] 모든 기능 및 실행 테스트가 완벽히 통과했습니다!")
    return True

if __name__ == '__main__':
    # DB 초기화
    init_db()

    # Flask 서버 백그라운드 스레드로 실행
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 서버 기동 대기
    time.sleep(1.5)

    success = test_api()
    if not success:
        sys.exit(1)
    sys.exit(0)
