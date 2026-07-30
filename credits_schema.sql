-- Smart Kundli — credit consumption for sheet-driven generation.
-- Run once in Supabase: SQL Editor → paste → Run.
--
-- Context: the credit system is owned by a separate admin/user web app. An admin assigns
-- credits to an astrologer; each assignment is appended to public.credit_transactions
-- (type='assign') and the resulting balance is held on public.astrologers.credits_balance.
-- This function is the other half of that loop — the sweeper spending one credit per PDF.
--
-- WHY A FUNCTION AND NOT A PATCH
--   PostgREST writes literal values: there is no way to express
--   `set credits_balance = credits_balance - 1` over the REST API. Reading the balance and
--   writing back balance-1 is a lost-update race — two callers both read 5 and both write 4,
--   spending one credit for two PDFs. Here the check and the decrement are a single
--   conditional UPDATE, so concurrent callers serialise on the row lock and the balance can
--   never go negative. It also means an admin top-up landing mid-generation is never clobbered.
--
-- NOTE FOR THE WEB APP: this writes type='deduct' rows, a value the ledger has never held
-- (every existing row is 'assign'). Any transaction list that filters or labels by type needs
-- to learn 'deduct', or these rows will render blank / be filtered out.
--
-- THE order_id FOREIGN KEY
--   credit_transactions.order_id is FK-constrained to kundli_orders.order_id
--   (credit_transactions_order_id_fkey). Sheet-driven orders live in sheet_orders and their ids
--   come from a different namespace entirely — cuid-style 'cmruho0m700op...' versus Razorpay's
--   'order_T8zLL...'; measured overlap between the two tables is exactly zero. Writing a sheet
--   order id into that column raises 23503 and, because the decrement and the insert share one
--   transaction, aborts the whole spend. So the column is populated only when the id genuinely
--   exists in kundli_orders; otherwise it stays null and the id is preserved in `note`, which
--   carries no constraint. Verified the hard way: the first live call failed on this FK.

create or replace function public.consume_kundli_credit(
    p_astrologer_id uuid,
    p_order_id      text default null,
    p_note          text default 'Kundli PDF generated'
)
returns table (ok boolean, balance_after integer)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_balance  integer;
    v_fk_order text;
begin
    -- The WHERE clause is the check. If the astrologer is inactive, unknown, or out of
    -- credits, zero rows match, v_balance stays null, and nothing is spent.
    update public.astrologers
       set credits_balance    = credits_balance - 1,
           total_credits_used = coalesce(total_credits_used, 0) + 1,
           updated_at         = now()
     where id = p_astrologer_id
       and is_active
       and credits_balance > 0
    returning credits_balance into v_balance;

    if v_balance is null then
        -- Report the current balance (may itself be null for an unknown id) so the caller
        -- can log WHY it was refused rather than just that it was.
        return query
            select false,
                   (select a.credits_balance from public.astrologers a where a.id = p_astrologer_id);
        return;
    end if;

    -- Only reference the order if it actually exists in kundli_orders — see THE order_id
    -- FOREIGN KEY above. A sheet order id is not there, and writing it would abort the spend.
    select k.order_id into v_fk_order
      from public.kundli_orders k
     where k.order_id = p_order_id;

    -- Audit trail. Same transaction as the decrement: a ledger row exists if and only if a
    -- credit was actually spent. The order id always survives in `note`, even when the FK
    -- column has to stay null, so a deduction can still be traced back to its kundli.
    insert into public.credit_transactions
        (astrologer_id, type, amount, order_id, note, created_by)
    values
        (p_astrologer_id,
         'deduct',
         1,
         v_fk_order,
         case
             when p_order_id is null then p_note
             else p_note || ' (order ' || p_order_id || ')'
         end,
         'sheet_worker');

    return query select true, v_balance;
end;
$$;

-- The sweeper authenticates with the service_role key.
grant execute on function public.consume_kundli_credit(uuid, text, text) to service_role;
