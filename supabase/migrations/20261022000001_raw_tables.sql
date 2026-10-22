-- 원본 청구 데이터 (구글 시트 탭 = 테이블, data/raw/*.csv 그대로)
-- 코드 컬럼은 앞자리 0 보존을 위해 text.

create table sido_code (
  sido_cd   text primary key,
  sido_nm   text not null,
  region_cd text,
  region_nm text
);

create table code_table (
  code_type text,
  code      text,
  code_nm   text,
  primary key (code_type, code)
);

create table patient (
  jid           integer primary key,
  sex_tp_cd     text,
  birth_yr      integer,
  sido_cd       text,
  qlf_tp_cd     text,
  prem_quintile integer
);

create table institution (
  yid         integer primary key,
  cl_cd       text,
  region_cd   text,
  shw_sbjt_cd text
);

create table hospital_open (
  hosp_id     integer primary key,
  yadm_nm     text,
  cl_nm       text,
  sido_nm     text,
  sggu_nm     text,
  shw_sbjt_nm text,
  open_dd     date
);

create table sick_master (
  sickcd  text primary key,
  krnm    text,
  sicknm  text,
  wcd     text,
  msick   text,
  cdd     text,
  sex     text,
  max_age integer,
  min_age integer,
  wocd    text
);

create table drug_ingredient (
  gnl_cd   text primary key,
  form_cd  text,
  form_nm  text,
  gnl_nm   text,
  class_no text,
  route    text,
  strength numeric,
  unit     text
);

create table claim (
  mid                integer primary key,
  jid                integer not null,
  yid                integer,
  insup_tp_cd        text,
  fom_tp_cd          text,
  main_sick          text,
  sub_sick           text,
  dgsbjt_cd          text,
  recu_fr_dd         date,
  recu_to_dd         date,
  vst_ddcnt          integer,
  recu_ddcnt         integer,
  rvd_rpe_tamt_amt   bigint,
  rvd_slf_brdn_amt   bigint,
  rvd_insup_brdn_amt bigint,
  sopr_yn            text,
  dgrslt_tp_cd       text
);

create table claim_rx (
  mid                    integer,
  ln_no                  integer,
  gnl_cd                 text,
  fq1_mdct_qty           numeric,
  dy1_mdct_qty           numeric,
  tot_injc_ddcnt_exec_fq numeric,
  tot_use_qty_or_exec_fq numeric,
  unprc                  bigint,
  amt                    bigint,
  primary key (mid, ln_no)
);

create table claim_sick (
  mid           integer,
  sick_sno      integer,
  dmd_dgsbjt_cd text,
  sick_cd       text,
  primary key (mid, sick_sno)
);

create index on claim (jid);
create index on claim (yid);
create index on claim (main_sick);
create index on claim (recu_fr_dd);
create index on claim_rx (gnl_cd);
create index on claim_sick (sick_cd);
create index on drug_ingredient (class_no);

-- 원본은 API(anon/authenticated)로 노출하지 않는다. 정책이 없으면 전부 거부.
alter table sido_code       enable row level security;
alter table code_table      enable row level security;
alter table patient         enable row level security;
alter table institution     enable row level security;
alter table hospital_open   enable row level security;
alter table sick_master     enable row level security;
alter table drug_ingredient enable row level security;
alter table claim           enable row level security;
alter table claim_rx        enable row level security;
alter table claim_sick      enable row level security;
