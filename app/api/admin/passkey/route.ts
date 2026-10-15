import { NextResponse } from 'next/server'
import { createHash } from 'crypto'
import { createClient } from '@supabase/supabase-js'

function authorized(req: Request) {
  return !!process.env.ADMIN_PASSWORD && req.headers.get('x-admin-password') === process.env.ADMIN_PASSWORD
}

function db() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  )
}

export async function GET(req: Request) {
  if (!authorized(req)) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { data, error } = await db()
    .from('print_settings')
    .select('passkey,updated_at')
    .eq('id', true)
    .single()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json(data)
}

export async function PATCH(req: Request) {
  if (!authorized(req)) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    const body = await req.json()
    const passkey = String(body?.passkey ?? '').trim()

    if (passkey.length < 4 || passkey.length > 128) {
      return NextResponse.json(
        { error: 'Passkey must be between 4 and 128 characters.' },
        { status: 400 }
      )
    }

    const hash = createHash('sha256').update(passkey, 'utf8').digest('hex')
    const supabase = db()

    const { data, error } = await supabase
      .from('print_settings')
      .update({ passkey, passkey_hash: hash, updated_at: new Date().toISOString() })
      .eq('id', true)
      .select('passkey,updated_at')
      .single()

    if (error) throw error

    const { error: jobsError } = await supabase
      .from('print_jobs')
      .update({ passcode_hash: hash })
      .eq('status', 'pending')

    if (jobsError) throw jobsError

    return NextResponse.json({ ...data, ok: true })
  } catch (error: any) {
    return NextResponse.json(
      { error: error?.message ?? 'Unable to update the print passkey.' },
      { status: 500 }
    )
  }
}
