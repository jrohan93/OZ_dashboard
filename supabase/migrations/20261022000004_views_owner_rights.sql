-- 공개 뷰(dm_*_public)가 내부 뷰를 거쳐 원본을 읽을 수 있도록 내부 뷰를 소유자 권한으로 실행한다.
-- 내부 뷰는 anon/authenticated 권한이 회수돼 있어서 API로 직접 읽히지는 않는다.
alter view claim_dims set (security_invoker = false);
alter view dm_rx      set (security_invoker = false);
alter view dm_dx      set (security_invoker = false);
