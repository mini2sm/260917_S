import time
import urllib.request
import urllib.parse
import json
import threading
import sys
import os

from app import app, init_sqlite

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
            assert '축제ON' in html
            print("  [PASS] 1. 메인 페이지 (index.html) 서빙 200 OK")
    except Exception as e:
        print(f"  [FAIL] 1. 메인 페이지 접근 실패: {e}")
        return False

    # 2. 축제 생성 (POST /api/festivals)
    festival_ids = []
    sample_festivals = [
        {"name": "테스트 봄꽃축제", "region": "경기", "category": "자연/생태", "start_date": "2026-04-01", "end_date": "2026-04-10", "location": "테스트공원"},
        {"name": "테스트 재즈페스티벌", "region": "서울", "category": "음악", "start_date": "2026-11-01", "end_date": "2026-11-03", "location": "한강공원"},
        {"name": "테스트 지난축제", "region": "부산", "category": "음식", "start_date": "2026-01-01", "end_date": "2026-01-03", "location": "해운대"},
    ]

    for item in sample_festivals:
        data = json.dumps(item).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/festivals", data=data, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=5) as res:
            assert res.status == 201
            body = json.loads(res.read().decode('utf-8'))
            assert body['name'] == item['name']
            assert body['status'] in ('ongoing', 'upcoming', 'ended')
            festival_ids.append(body['id'])
    print(f"  [PASS] 2. 축제 3건 생성 완료 (IDs: {festival_ids})")

    # 3. 축제 목록 조회 (GET /api/festivals)
    req = urllib.request.Request(f"{base_url}/api/festivals")
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200
        festivals = json.loads(res.read().decode('utf-8'))
        assert len(festivals) >= 3
        print(f"  [PASS] 3. 축제 목록 조회 성공 (조회된 건수: {len(festivals)})")

    # 4. 축제 정보 수정 (PUT /api/festivals/<id>)
    target_id = festival_ids[0]
    update_data = json.dumps({"location": "수정된 장소"}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/api/festivals/{target_id}", data=update_data, headers={'Content-Type': 'application/json'}, method='PUT')
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200
        updated = json.loads(res.read().decode('utf-8'))
        assert updated['location'] == '수정된 장소'
        print(f"  [PASS] 4. 축제 정보 수정 성공 (ID: {target_id})")

    # 5. 통계 조회 (GET /api/stats)
    req = urllib.request.Request(f"{base_url}/api/stats")
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200
        stats = json.loads(res.read().decode('utf-8'))
        assert stats['total'] >= 3
        print(f"  [PASS] 5. 대시보드 통계 검증 완료 (전체: {stats['total']}, 진행중: {stats['ongoing']}, 예정: {stats['upcoming']})")

    # 6. 축제 단건 삭제 (DELETE /api/festivals/<id>)
    delete_id = festival_ids[2]
    req = urllib.request.Request(f"{base_url}/api/festivals/{delete_id}", method='DELETE')
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.status == 200
        print(f"  [PASS] 6. 축제 삭제 성공 (ID: {delete_id})")

    print("\n[SUCCESS] 모든 기능 및 실행 테스트가 완벽히 통과했습니다!")
    return True

if __name__ == '__main__':
    # DB 초기화
    init_sqlite()

    # Flask 서버 백그라운드 스레드로 실행
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 서버 기동 대기
    time.sleep(1.5)

    success = test_api()
    if not success:
        sys.exit(1)
    sys.exit(0)
