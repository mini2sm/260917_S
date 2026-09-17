-- ===================================================
-- Supabase SQL Editor에서 실행할 테이블 및 정책 생성 스크립트
-- 저장소: 260917_S / 웹앱: 축제ON (지역별 축제정보)
-- ===================================================

-- 1. festivals 테이블 생성
CREATE TABLE IF NOT EXISTS public.festivals (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT DEFAULT '',
    category TEXT DEFAULT '기타',
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    location TEXT DEFAULT '',
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

-- 2. 성능 향상을 위한 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_festivals_region ON public.festivals(region);
CREATE INDEX IF NOT EXISTS idx_festivals_category ON public.festivals(category);
CREATE INDEX IF NOT EXISTS idx_festivals_start_date ON public.festivals(start_date);
CREATE INDEX IF NOT EXISTS idx_festivals_end_date ON public.festivals(end_date);

-- 3. Row Level Security (RLS) 활성화
ALTER TABLE public.festivals ENABLE ROW LEVEL SECURITY;

-- 4. anon(익명 사용자) 및 authenticated(인증된 사용자) 모두에게 전체 CRUD 권한 부여
DROP POLICY IF EXISTS "Allow all access to festivals" ON public.festivals;
CREATE POLICY "Allow all access to festivals"
ON public.festivals
FOR ALL
TO anon, authenticated
USING (true)
WITH CHECK (true);

-- 5. 샘플 데이터 (선택 사항 — 비어있는 상태로 시작하려면 이 블록은 실행하지 마세요)
INSERT INTO public.festivals (name, region, city, category, start_date, end_date, location, description, created_at)
VALUES
    ('부산불꽃축제', '부산', '수영구', '불빛/조명', '2026-10-24', '2026-10-24', '광안리 해수욕장', '밤하늘을 수놓는 국내 최대 규모의 불꽃 축제.', now()::text),
    ('진주남강유등축제', '경남', '진주시', '전통', '2026-10-01', '2026-10-12', '남강 일원', '강물 위를 수놓는 형형색색의 유등과 전통 문화 체험.', now()::text),
    ('안동국제탈춤페스티벌', '경북', '안동시', '전통', '2026-09-25', '2026-10-04', '탈춤공원 일원', '세계 각국의 탈춤과 안동의 전통 문화를 즐기는 축제.', now()::text),
    ('자라섬재즈페스티벌', '경기', '가평군', '음악', '2026-10-09', '2026-10-11', '자라섬 일원', '가을 강변에서 즐기는 국내 최대 재즈 페스티벌.', now()::text),
    ('서울빛초롱축제', '서울', '종로구', '불빛/조명', '2026-11-06', '2026-11-22', '청계천 일원', '청계천을 가득 채우는 대형 등불 전시와 야경.', now()::text)
ON CONFLICT DO NOTHING;

-- 참고: 예전 todos 테이블은 삭제하지 않았습니다. 필요 없다면 아래 명령으로 직접 정리하세요.
-- DROP TABLE IF EXISTS public.todos;
