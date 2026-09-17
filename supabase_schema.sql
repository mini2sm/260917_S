-- ===================================================
-- Supabase SQL Editor에서 실행할 테이블 및 정책 생성 스크립트
-- 저장소: 26017_S / 웹앱: TaskFlow
-- ===================================================

-- 1. todos 테이블 생성
CREATE TABLE IF NOT EXISTS public.todos (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority TEXT DEFAULT 'medium',
    category TEXT DEFAULT '일반',
    due_date TEXT DEFAULT '',
    completed INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- 2. 성능 향상을 위한 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_todos_completed ON public.todos(completed);
CREATE INDEX IF NOT EXISTS idx_todos_priority ON public.todos(priority);
CREATE INDEX IF NOT EXISTS idx_todos_category ON public.todos(category);

-- 3. Row Level Security (RLS) 활성화
ALTER TABLE public.todos ENABLE ROW LEVEL SECURITY;

-- 4. anon(익명 사용자) 및 authenticated(인증된 사용자) 모두에게 전체 CRUD 권한 부여
DROP POLICY IF EXISTS "Allow all access to todos" ON public.todos;
CREATE POLICY "Allow all access to todos"
ON public.todos
FOR ALL
TO anon, authenticated
USING (true)
WITH CHECK (true);
