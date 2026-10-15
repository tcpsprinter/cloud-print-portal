import { NextResponse } from 'next/server'
import { createHash } from 'crypto'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SECRET_KEY!)

export async function POST(req: Request) {
  try {
    const { pin } = await req.json()
    const clean = String(pin ?? '').replace(/\D/g, '').slice(0, 4)
    if (clean.length !== 4) return NextResponse.json({ error: 'Enter your 4-digit PIN.' }, { status: 400 })
    const hash = createHash('sha256').update(clean).digest('hex')
    const { data, error } = await supabase.from('print_jobs').select('id,user_name,file_name,copies,status,created_at,expires_at').eq('passcode_hash', hash).maybeSingle()
    if (error) throw error
    if (!data) return NextResponse.json({ error: 'No print request found for that PIN.' }, { status: 404 })
    return NextResponse.json({ job: data })
  } catch (error: any) {
    return NextResponse.json({ error: error?.message ?? 'Unable to check status.' }, { status: 500 })
  }
}
