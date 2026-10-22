-- github.io 공개 대시보드(docs/index.html)용 뷰. publishable(anon) 키로 읽는다.
-- 행 단위 뷰에서 명세서·수진자·요양기관 ID와 진료일을 빼고, 환자수·건수 계산에 필요한
-- 수진자/명세서 구분값만 해시(가명)로 남긴다. 원본 테이블은 여전히 anon에 닫혀 있다.
-- 실습 샘플 데이터 기준의 가명처리이며 익명화는 아니다.

create view dm_rx_public as
select
  left(md5('pid:' || jid), 12) as pid,
  left(md5('cid:' || mid), 12) as cid,
  ym, cl_nm, region_nm, sido_nm, sex, age_grp,
  ingredient, drug_class, amt
from dm_rx;

create view dm_dx_public as
select
  left(md5('pid:' || jid), 12) as pid,
  left(md5('cid:' || mid), 12) as cid,
  ym, cl_nm, region_nm, sido_nm, sex, age_grp,
  total, insurer, self
from dm_dx;

-- security_invoker 를 쓰지 않는다: 뷰 소유자(postgres) 권한으로 원본을 읽고,
-- anon 에게는 이 두 뷰의 select 만 연다.
revoke all on dm_rx_public, dm_dx_public from anon, authenticated;
grant select on dm_rx_public, dm_dx_public to anon, authenticated;
