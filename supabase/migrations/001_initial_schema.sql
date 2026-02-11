-- ════════════════════════════════════════════════════════════
-- ATS Resume App — Supabase Schema (consolidated)
-- Applied via Supabase MCP migrations:
--   20260211163947_initial_schema
--   20260211164000_analytics_views
--   20260211164042_fix_security_issues
--   (latest)_allow_anon_role_access
-- ════════════════════════════════════════════════════════════

-- Enable UUID extension (already enabled by default on Supabase)
create extension if not exists "uuid-ossp";

-- ─── Sessions ───────────────────────────────────────────────
-- Tracks every resume upload / parse event
create table if not exists sessions (
    id              uuid primary key default uuid_generate_v4(),
    session_id      text unique not null,
    resume_name     text default '',
    resume_email    text default '',
    experience_count integer default 0,
    skills_count    integer default 0,
    projects_count  integer default 0,
    certifications_count integer default 0,
    created_at      timestamptz default now()
);

create index if not exists idx_sessions_session_id on sessions (session_id);
create index if not exists idx_sessions_created_at on sessions (created_at desc);

-- ─── Analyses ───────────────────────────────────────────────
-- Tracks every ATS analysis run
create table if not exists analyses (
    id                    uuid primary key default uuid_generate_v4(),
    session_id            text not null references sessions(session_id) on delete cascade,
    overall_score         integer default 0,
    grade                 text default '',
    keyword_match_pct     real default 0.0,
    matched_count         integer default 0,
    missing_count         integer default 0,
    format_issues_count   integer default 0,
    skill_gaps_count      integer default 0,
    job_description_snippet text default '',
    created_at            timestamptz default now()
);

create index if not exists idx_analyses_session_id on analyses (session_id);
create index if not exists idx_analyses_created_at on analyses (created_at desc);

-- ─── Generations ────────────────────────────────────────────
-- Tracks every resume generation event
create table if not exists generations (
    id              uuid primary key default uuid_generate_v4(),
    session_id      text not null references sessions(session_id) on delete cascade,
    filename        text default '',
    output_format   text default 'docx',
    ats_score       integer default 0,
    ats_compatible  boolean default true,
    ats_issues_count integer default 0,
    keywords_used   jsonb default '[]'::jsonb,
    job_title       text default '',
    fast_mode       boolean default false,
    created_at      timestamptz default now()
);

create index if not exists idx_generations_session_id on generations (session_id);
create index if not exists idx_generations_created_at on generations (created_at desc);

-- ─── Row Level Security ─────────────────────────────────────
alter table sessions enable row level security;
alter table analyses enable row level security;
alter table generations enable row level security;

-- Service role: full CRUD access
create policy "Service role insert on sessions"   on sessions for INSERT to service_role with check (true);
create policy "Service role select on sessions"   on sessions for SELECT to service_role using (true);
create policy "Service role delete on sessions"   on sessions for DELETE to service_role using (true);

create policy "Service role insert on analyses"   on analyses for INSERT to service_role with check (true);
create policy "Service role select on analyses"   on analyses for SELECT to service_role using (true);
create policy "Service role delete on analyses"   on analyses for DELETE to service_role using (true);

create policy "Service role insert on generations" on generations for INSERT to service_role with check (true);
create policy "Service role select on generations" on generations for SELECT to service_role using (true);
create policy "Service role delete on generations" on generations for DELETE to service_role using (true);

-- Anon role: insert + select (backend uses anon key server-side)
create policy "Anon insert on sessions"    on sessions for INSERT to anon with check (true);
create policy "Anon select on sessions"    on sessions for SELECT to anon using (true);

create policy "Anon insert on analyses"    on analyses for INSERT to anon with check (true);
create policy "Anon select on analyses"    on analyses for SELECT to anon using (true);

create policy "Anon insert on generations" on generations for INSERT to anon with check (true);
create policy "Anon select on generations" on generations for SELECT to anon using (true);

-- ─── Views for quick analytics ──────────────────────────────

-- Daily usage summary (security invoker for RLS compliance)
create or replace view daily_usage
with (security_invoker = true)
as
select
    date_trunc('day', s.created_at)::date as day,
    count(distinct s.session_id) as sessions,
    count(distinct a.id) as analyses,
    count(distinct g.id) as generations,
    round(avg(a.overall_score), 1) as avg_analysis_score,
    round(avg(g.ats_score), 1) as avg_generation_score
from sessions s
left join analyses a on a.session_id = s.session_id
left join generations g on g.session_id = s.session_id
group by 1
order by 1 desc;

-- Score distribution
create or replace view score_distribution
with (security_invoker = true)
as
select
    case
        when overall_score >= 90 then 'A (90-100)'
        when overall_score >= 80 then 'B (80-89)'
        when overall_score >= 70 then 'C (70-79)'
        when overall_score >= 60 then 'D (60-69)'
        else 'F (0-59)'
    end as score_range,
    count(*) as count
from analyses
group by 1
order by 1;
