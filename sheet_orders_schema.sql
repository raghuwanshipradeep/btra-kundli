-- Smart Kundli — Google Sheet order mirror.
-- Run once in Supabase: SQL Editor → paste → Run.
--
-- Fed by scripts/sheet_to_supabase.gs, an hourly Apps Script on the orders sheet
-- that POSTs new rows straight to PostgREST. This is a SEPARATE order stream from
-- public.kundli_orders (the Razorpay flow) — different source, own dedup scheme, plus
-- addons/UTM columns — so it gets its own table rather than sharing one. The two streams are
-- fully independent and are NOT joinable on order_id — see the order_id comment below.
--
-- Like kundli_orders, the writer uses the service_role key, which bypasses RLS; RLS
-- is enabled with no public policy so the table is private (no anon/public access).

create table if not exists public.sheet_orders (
    id              bigint generated always as identity primary key,

    -- Dedup. row_hash is a SHA-256 over the row's cell values, computed by the Apps
    -- Script. The unique constraint is what makes the sync idempotent: re-running,
    -- resetting the cursor, or retrying a half-failed batch can never duplicate a row
    -- (the script POSTs with Prefer: resolution=ignore-duplicates on this column).
    row_hash        text not null unique,
    sheet_row       integer,                         -- source row number, for tracing back

    -- The order id as it appears in the sheet. Despite what this comment used to claim, it is
    -- NOT a Razorpay id and does NOT join public.kundli_orders: the sheet is fed by the
    -- admin/user web app, which mints its own cuid-style ids ('cmruho0m700opltrt...'), whereas
    -- kundli_orders holds Razorpay ids ('order_T8zLLOKd7YPe67'). Measured overlap between the
    -- two tables is exactly zero. Treat them as separate id namespaces.
    --
    -- That mistaken assumption has already cost one bug: credit_transactions.order_id is
    -- FK-constrained to kundli_orders, so writing a sheet order id there raises 23503 (see
    -- credits_schema.sql, which now nulls the column and keeps the id in `note`). Check the
    -- namespace before wiring this column to anything that references kundli_orders.
    --
    -- No foreign key here either, on purpose: the sheet is an independent hand-maintained
    -- record and may hold ids kundli_orders never saw. An FK would reject those rows and stall
    -- the hourly sync.
    --
    -- Nullable and non-unique: this column copies whatever the cell happens to say.
    -- Constraining it would fail a whole 500-row batch on one blank or repeated cell.
    -- Dedup stays on row_hash above.
    order_id        text,

    -- Order timing. *_raw keeps the sheet's original string so a parse miss loses nothing.
    order_date      date,
    order_date_raw  text,
    order_time      text,
    order_time_raw  text,
    order_at        timestamptz,                     -- order_date + order_time in Asia/Kolkata

    -- Customer
    name            text,
    phone           text,                            -- text, never numeric: keeps leading 0 / +91
    email           text,
    gender          text,
    state           text,
    pin_code        text,                            -- text: keeps leading zeros

    -- Birth details
    place_of_birth  text,
    date_of_birth   date,
    date_of_birth_raw text,
    time_of_birth   text,
    time_of_birth_raw text,
    longitude       double precision,
    longitude_raw   text,
    latitude        double precision,
    latitude_raw    text,

    -- Report / payment
    report_language text,
    report_name     text,
    order_total_amount     numeric,
    order_total_amount_raw text,
    addons_name     text,
    payment_status  text,

    -- Attribution
    utm_id          text,
    utm_source      text,
    utm_campaign    text,
    utm_medium      text,
    utm_content     text,
    utm_term        text,

    synced_at       timestamptz not null default now(),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index if not exists sheet_orders_order_at_idx       on public.sheet_orders (order_at desc);
create index if not exists sheet_orders_order_id_idx       on public.sheet_orders (order_id);
create index if not exists sheet_orders_email_idx          on public.sheet_orders (email);
create index if not exists sheet_orders_phone_idx          on public.sheet_orders (phone);
create index if not exists sheet_orders_payment_status_idx on public.sheet_orders (payment_status);
create index if not exists sheet_orders_synced_at_idx      on public.sheet_orders (synced_at desc);

-- Reuses public.set_updated_at(), already defined by supabase_schema.sql. Run that
-- file first if this is a fresh project.
drop trigger if exists sheet_orders_set_updated_at on public.sheet_orders;
create trigger sheet_orders_set_updated_at
    before update on public.sheet_orders
    for each row execute function public.set_updated_at();

-- Private by default: enable RLS, add no policies. The service_role key the Apps
-- Script uses bypasses RLS; anon/public keys get no access at all.
alter table public.sheet_orders enable row level security;

-- Admit the writer. Supabase no longer auto-grants new public tables to the API roles —
-- exposure is opt-in as of 2026-05-30 for new projects, and 2026-10-30 for all existing
-- ones. Without this the Apps Script POST fails 403 42501 "permission denied for table",
-- even holding a valid service_role key.
--
-- This GRANT, not a policy, is what lets the sync write: privileges are checked before RLS
-- is ever consulted, so no policy can substitute for it (and service_role bypasses RLS
-- anyway, which makes a policy for it inert).
--
-- service_role only. anon and authenticated are granted nothing, deliberately — that is what
-- keeps the table private, together with the RLS line above. update is included for the
-- kundli-generation worker (below), which marks rows as it produces PDFs; the hourly sync
-- itself only ever inserts (ON CONFLICT DO NOTHING). No sequence grant needed: id is
-- `generated always as identity`, whose sequence is internally owned (a `serial` would have
-- needed `grant usage on sequence`).
grant select, insert, update on public.sheet_orders to service_role;

-- Kundli generation tracking. Written by the sheet-driven worker (POST /admin/process-sheet-
-- orders), which reads SUCCESSFUL rows, generates a PDF, and archives it to Drive. These
-- columns are that worker's durable, idempotent state — a row that reached 'archived' is
-- never regenerated. Separate from public.kundli_orders (the paid Razorpay stream); the two
-- share only order_id.
--   kundli_status:  null = pending, 'generating' = claimed, 'archived' = done,
--                   'failed' = retryable, 'failed_permanent' = gave up after the attempt cap.
--   kundli_attempts: incremented on each claim; caps retries so a poison row can't loop.
-- Idempotent adds, so this block is safe to re-run against the live table.
alter table public.sheet_orders add column if not exists kundli_status        text;
alter table public.sheet_orders add column if not exists kundli_attempts       integer not null default 0;
alter table public.sheet_orders add column if not exists kundli_drive_file_id  text;
alter table public.sheet_orders add column if not exists kundli_drive_link     text;
alter table public.sheet_orders add column if not exists kundli_error          text;
alter table public.sheet_orders add column if not exists kundli_generated_at   timestamptz;

create index if not exists sheet_orders_kundli_status_idx on public.sheet_orders (kundli_status);
