-- Provider acquisition: capture runs, and outages recorded as evidence.
--
-- traffic_observations and weather_observations already carry a full bitemporal
-- record and a unique identity index that makes a repeated capture idempotent at
-- the database rather than in application code. Both tables have 0 rows: nothing
-- has ever acquired into them, because acquisition only happens when a demo page
-- is loaded. Two things were missing to make continuous acquisition provable.
--
-- 1. A CAPTURE RUN. Observations carried a nullable run_id pointing at nothing,
--    so there was no way to say "these rows came from one cycle at this time
--    against this build", and therefore no way to show that cycles advance.
--
-- 2. AN OUTAGE RECORD. When a provider failed, nothing was written. Absence of
--    data then looked exactly like absence of traffic, which is the failure mode
--    this product exists to avoid: a value the system cannot establish must read
--    UNAVAILABLE, never 0 and never a plausible substitute. An outage is
--    evidence about the world - we tried, at this time, and could not observe -
--    so it is stored, not logged and forgotten.
--
-- Deliberately NOT stored here: raw provider payloads. The provider licence
-- review (docs/data/DATA_LICENSES.md) found retention and redistribution
-- concerns with retaining raw third-party responses indefinitely. These tables
-- keep normalized values plus enough safe metadata - a response hash, a request
-- trace id, timestamps and their provenance - to prove an acquisition happened
-- without retaining the restricted payload. No column here may hold an API key,
-- an authorization header, or a URL containing either.

begin;

create table if not exists public.provider_capture_runs (
    capture_run_id      uuid primary key default gen_random_uuid(),
    workspace_id        uuid        not null,
    started_at          timestamptz not null,
    completed_at        timestamptz,
    candidate_sha       text        not null,
    environment         text        not null,
    providers_attempted text[]      not null default '{}',
    providers_succeeded text[]      not null default '{}',
    providers_failed    text[]      not null default '{}',
    observation_count   integer     not null default 0,

    constraint provider_capture_runs_completes_after_start
        check (completed_at is null or completed_at >= started_at),
    constraint provider_capture_runs_observation_count_non_negative
        check (observation_count >= 0),
    -- A provider cannot both succeed and fail in one run. Without this the two
    -- arrays could drift into a state that no report could interpret.
    constraint provider_capture_runs_outcome_is_disjoint
        check (not (providers_succeeded && providers_failed)),
    constraint provider_capture_runs_outcomes_were_attempted
        check (providers_succeeded <@ providers_attempted
               and providers_failed <@ providers_attempted),
    constraint provider_capture_runs_environment_not_blank
        check (length(btrim(environment)) > 0),
    constraint provider_capture_runs_candidate_sha_not_blank
        check (length(btrim(candidate_sha)) > 0)
);

create index if not exists provider_capture_runs_recent
    on public.provider_capture_runs (workspace_id, started_at desc);

-- Observations belong to the run that produced them. The column already existed
-- and pointed at nothing; give it a referent. ON DELETE RESTRICT because
-- discarding a run while its observations survive would orphan their provenance.
alter table public.traffic_observations
    drop constraint if exists traffic_observations_run_id_fkey;
alter table public.traffic_observations
    add constraint traffic_observations_run_id_fkey
    foreign key (run_id) references public.provider_capture_runs (capture_run_id)
    on delete restrict;

alter table public.weather_observations
    drop constraint if exists weather_observations_run_id_fkey;
alter table public.weather_observations
    add constraint weather_observations_run_id_fkey
    foreign key (run_id) references public.provider_capture_runs (capture_run_id)
    on delete restrict;

-- An attempt that produced no observation. This is the record that keeps
-- "we could not see" distinguishable from "there was nothing to see".
create table if not exists public.provider_outages (
    outage_id       uuid primary key default gen_random_uuid(),
    workspace_id    uuid        not null,
    capture_run_id  uuid        not null
        references public.provider_capture_runs (capture_run_id) on delete restrict,
    provider        text        not null,
    reason_code     text        not null,
    detail          text,
    attempted_at    timestamptz not null,
    last_success_at timestamptz,

    constraint provider_outages_provider_not_blank
        check (length(btrim(provider)) > 0),
    -- A free-text reason becomes an unqueryable grab bag within a month.
    constraint provider_outages_reason_code_is_known
        check (reason_code in (
            'HTTP_ERROR',
            'TIMEOUT',
            'CONNECTION_FAILED',
            'AUTH_REJECTED',
            'RATE_LIMITED',
            'MALFORMED_RESPONSE',
            'NO_CREDENTIAL',
            'UNKNOWN'
        )),
    constraint provider_outages_last_success_precedes_attempt
        check (last_success_at is null or last_success_at <= attempted_at),
    -- One outage row per provider per run. A retry loop must not inflate the
    -- failure count into something that looks like a worse incident than it was.
    constraint provider_outages_one_per_provider_per_run
        unique (capture_run_id, provider)
);

create index if not exists provider_outages_recent
    on public.provider_outages (workspace_id, provider, attempted_at desc);

-- Safe acquisition metadata on the observations themselves. Nullable because
-- not every provider supplies a trace id, and inventing one would be worse than
-- leaving it absent.
alter table public.traffic_observations
    add column if not exists request_trace_id text,
    add column if not exists response_sha256  text,
    -- Whether event_time came from the provider or is the fetch time standing in
    -- for it. Publishing a fetch time as though the provider had stamped it is a
    -- provenance claim the system cannot support.
    add column if not exists event_time_source text not null default 'PROVIDER_SUPPLIED';

alter table public.weather_observations
    add column if not exists request_trace_id text,
    add column if not exists response_sha256  text,
    add column if not exists event_time_source text not null default 'PROVIDER_SUPPLIED';

alter table public.traffic_observations
    drop constraint if exists traffic_observations_event_time_source_known;
alter table public.traffic_observations
    add constraint traffic_observations_event_time_source_known
    check (event_time_source in ('PROVIDER_SUPPLIED', 'FETCH_TIME_SUBSTITUTED'));

alter table public.weather_observations
    drop constraint if exists weather_observations_event_time_source_known;
alter table public.weather_observations
    add constraint weather_observations_event_time_source_known
    check (event_time_source in ('PROVIDER_SUPPLIED', 'FETCH_TIME_SUBSTITUTED'));

-- A sha256 hex digest or nothing; a truncated or malformed digest proves nothing.
alter table public.traffic_observations
    drop constraint if exists traffic_observations_response_sha256_is_a_digest;
alter table public.traffic_observations
    add constraint traffic_observations_response_sha256_is_a_digest
    check (response_sha256 is null or response_sha256 ~ '^[0-9a-f]{64}$');

alter table public.weather_observations
    drop constraint if exists weather_observations_response_sha256_is_a_digest;
alter table public.weather_observations
    add constraint weather_observations_response_sha256_is_a_digest
    check (response_sha256 is null or response_sha256 ~ '^[0-9a-f]{64}$');

commit;
