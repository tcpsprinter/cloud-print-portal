-- A valid shared print passkey is the authorization for a print request.
-- New jobs therefore enter the printer queue immediately instead of waiting
-- for manual administrator approval.

create or replace function public.create_print_job(
  p_user_name text,
  p_file_name text,
  p_file_path text,
  p_copies integer default 1,
  p_admin_pin text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public', 'extensions'
as $$
declare
  v_job public.print_jobs;
  v_tracking_pin text;
  v_global_passkey_hash text;
begin
  if length(trim(coalesce(p_user_name, ''))) < 2 then
    raise exception 'Name is required';
  end if;

  if lower(coalesce(split_part(p_file_name, '.', 2), '')) <> 'pdf' then
    raise exception 'Only PDF files are allowed';
  end if;

  if p_copies < 1 or p_copies > 99 then
    raise exception 'Invalid copies';
  end if;

  select passkey_hash
    into v_global_passkey_hash
  from public.print_settings
  where id = true;

  if v_global_passkey_hash is null then
    raise exception 'Print passkey has not been configured by the administrator';
  end if;

  if encode(digest(trim(coalesce(p_admin_pin, ''))::text, 'sha256'::text), 'hex') <> v_global_passkey_hash then
    raise exception 'Invalid print passkey';
  end if;

  v_tracking_pin := lpad((floor(random() * 10000))::int::text, 4, '0');

  insert into public.print_jobs(
    user_name,
    file_name,
    file_path,
    passcode_hash,
    tracking_pin_hash,
    copies,
    status
  )
  values (
    trim(p_user_name),
    p_file_name,
    p_file_path,
    v_global_passkey_hash,
    encode(digest(v_tracking_pin::text, 'sha256'::text), 'hex'),
    p_copies,
    'approved'
  )
  returning * into v_job;

  return jsonb_build_object(
    'id', v_job.id,
    'pin', v_tracking_pin,
    'status', v_job.status,
    'expires_at', v_job.expires_at
  );
end;
$$;
