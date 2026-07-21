-- Smart Kundli — order/payment tracking table.
-- Run once in Supabase: SQL Editor → paste → Run.
-- The backend writes with the service_role key, which bypasses RLS; RLS is
-- enabled with no public policy so the table is private (no anon/public access).

create table if not exists public.kundli_orders (
    id              bigint generated always as identity primary key,
    order_id        text not null unique,           -- Razorpay order id
    payment_id      text,                            -- Razorpay payment id (set on payment)
    status          text not null default 'created', -- created|paid|generating|archived|generated_no_archive|timeout|pdf_failed|drive_failed

    -- Payment
    amount_paise    integer,
    amount_rupees   integer,
    currency        text,
    paid_at         timestamptz,

    -- Customer form fields
    name            text,
    phone           text,
    email           text,
    gender          text,
    place           text,
    state           text,
    pincode         text,

    -- Birth details (raw)
    dob_day         integer,
    dob_month       integer,
    dob_year        integer,
    birth_hour      integer,
    birth_min       integer,
    lat             double precision,
    lon             double precision,
    tzone           double precision,

    -- Pre-formatted, human-friendly
    date_of_birth   text,       -- e.g. "15 Aug 1990"
    time_of_birth   text,       -- e.g. "2:30"
    am_pm           text,       -- "AM" / "PM"
    lang            text,       -- "en" / "hi"
    language        text,       -- "English" / "Hindi"
    report_tier     text,       -- "detailed" / "lite"

    -- Delivery / outcome
    drive_file_id   text,
    drive_link      text,
    error_detail    text,
    elapsed_s       numeric,

    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index if not exists kundli_orders_status_idx     on public.kundli_orders (status);
create index if not exists kundli_orders_created_at_idx on public.kundli_orders (created_at desc);

-- Auto-maintain updated_at on every UPDATE (e.g. upserts that touch an existing row).
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists kundli_orders_set_updated_at on public.kundli_orders;
create trigger kundli_orders_set_updated_at
    before update on public.kundli_orders
    for each row execute function public.set_updated_at();

-- Private by default: enable RLS, add no policies. The service_role key the
-- backend uses bypasses RLS; anon/public keys get no access at all.
alter table public.kundli_orders enable row level security;

-- Admit the writer. Supabase no longer auto-grants new public tables to the API roles —
-- exposure is opt-in as of 2026-05-30 for new projects, 2026-10-30 for existing ones. The
-- live table predates this and keeps its old grants, so this line changes nothing today;
-- it is what makes a fresh project built from this file actually work.
--
-- Privileges are checked before RLS, so this GRANT — not a policy — is what admits the
-- backend; service_role bypasses RLS anyway. anon and authenticated get nothing.
--
-- update is required, unlike sheet_orders: _upsert() POSTs with
-- resolution=merge-duplicates on order_id (supabase_repo.py), i.e. ON CONFLICT DO UPDATE,
-- which is how a row moves created -> paid -> archived. Nothing ever deletes.
grant select, insert, update on public.kundli_orders to service_role;
