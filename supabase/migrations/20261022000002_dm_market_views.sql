-- 당뇨병 시장 정의 (dm_market.py 와 같은 규칙)
-- - 약물 시장 dm_rx: 당뇨병용제(약효분류 396) 원외처방 한 줄 = 한 행
-- - 질환 시장 dm_dx: 주상병 E11(2형 당뇨병) 명세서 한 건 = 한 행
-- 지역은 수진자 거주 시도, 종별은 요양기관 cl_cd, 연령 = 진료 연도 - 출생 연도.

create table dm_ingredient (
  gnl_nm     text primary key,  -- drug_ingredient.gnl_nm 원문
  ingredient text not null,     -- 표시명
  drug_class text not null,     -- 계열
  sort_order integer not null
);

insert into dm_ingredient values
  ('sitagliptin phosphate hydrate (as sitagliptin)', '시타글립틴',   'DPP-4 억제제', 1),
  ('glimepiride',                                    '글리메피리드', '설포닐우레아', 2),
  ('metformin hydrochloride',                        '메트포르민',   '비구아나이드', 3);

alter table dm_ingredient enable row level security;

-- 명세서(claim)에 시간·지역·종별·성별·연령 차원을 붙인 공통 뷰
create view claim_dims with (security_invoker = true) as
select
  c.mid,
  c.jid,
  c.yid,
  c.recu_fr_dd,
  c.main_sick,
  to_char(c.recu_fr_dd, 'YYYY-MM')               as ym,
  extract(year from c.recu_fr_dd)::int           as year,
  case i.cl_cd
    when '01' then '상급종합병원'
    when '11' then '종합병원'
    when '21' then '병원'
    when '31' then '의원'
    else '기타'
  end                                            as cl_nm,
  s.region_nm,
  s.sido_nm,
  case p.sex_tp_cd when '1' then '남' when '2' then '여' else '미상' end as sex,
  case
    when extract(year from c.recu_fr_dd)::int - p.birth_yr < 40  then '40세 미만'
    when extract(year from c.recu_fr_dd)::int - p.birth_yr >= 80 then '80세 이상'
    else ((extract(year from c.recu_fr_dd)::int - p.birth_yr) / 10 * 10)::text || '대'
  end                                            as age_grp
from claim c
left join patient p     on p.jid = c.jid
left join institution i on i.yid = c.yid
left join sido_code s   on s.sido_cd = p.sido_cd;

create view dm_rx with (security_invoker = true) as
select
  d.mid, d.jid, d.yid, d.recu_fr_dd, d.ym, d.year,
  d.cl_nm, d.region_nm, d.sido_nm, d.sex, d.age_grp,
  g.gnl_nm,
  coalesce(m.ingredient, g.gnl_nm) as ingredient,
  coalesce(m.drug_class, '기타')    as drug_class,
  r.amt
from claim_rx r
join drug_ingredient g    on g.gnl_cd = r.gnl_cd and g.class_no = '396'
join claim_dims d         on d.mid = r.mid
left join dm_ingredient m on m.gnl_nm = g.gnl_nm;

create view dm_dx with (security_invoker = true) as
select
  d.mid, d.jid, d.yid, d.recu_fr_dd, d.ym, d.year,
  d.cl_nm, d.region_nm, d.sido_nm, d.sex, d.age_grp,
  c.rvd_rpe_tamt_amt   as total,
  c.rvd_insup_brdn_amt as insurer,
  c.rvd_slf_brdn_amt   as self
from claim c
join claim_dims d on d.mid = c.mid
where left(c.main_sick, 3) = 'E11';

-- 행 단위 뷰에는 jid(수진자)가 있으므로 API 역할에는 열지 않는다.
-- 공유판 등 공개 화면용 집계 뷰는 별도 마이그레이션에서 연다.
revoke all on claim_dims, dm_rx, dm_dx from anon, authenticated;
