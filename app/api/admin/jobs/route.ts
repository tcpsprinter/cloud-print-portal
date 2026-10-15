import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SECRET_KEY!)

export async function GET() {
  const { data, error } = await supabase.from('print_jobs').select('id,user_name,file_name,copies,status,created_at,expires_at').order('created_at', { ascending: false }).limit(100)
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json({ jobs: data ?? [] })
}

export async function PATCH(req: Request) {
  try {
    const { id, status } = await req.json()
    if (!id || !['approved', 'rejected'].includes(status)) return NextResponse.json({ error: 'Invalid request.' }, { status: 400 })
    const { error } = await supabase.from('print_jobs').update({ status }).eq('id', id).eq('status', 'pending')
    if (error) throw error
    return NextResponse.json({ ok: true })
  } catch (error: any) {
    return NextResponse.json({ error: error?.message ?? 'Unable to update job.' }, { status: 500 })
  }
}
