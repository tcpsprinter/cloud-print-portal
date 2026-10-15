import {NextResponse} from 'next/server'
import {createClient} from '@supabase/supabase-js'

function authorized(req: Request) {
  return !!process.env.ADMIN_PASSWORD && req.headers.get('x-admin-password') === process.env.ADMIN_PASSWORD
}

function db() {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!)
}

export async function GET(req: Request) {
  if (!authorized(req)) return NextResponse.json({error: 'Unauthorized'}, {status: 401})

  const {data, error} = await db()
    .from('print_jobs')
    .select('id,user_name,file_name,file_path,copies,status,failure_reason,created_at,expires_at')
    .order('created_at', {ascending: false})
    .limit(100)

  if (error) return NextResponse.json({error: error.message}, {status: 500})
  return NextResponse.json({jobs: data ?? []})
}

export async function PATCH(req: Request) {
  if (!authorized(req)) return NextResponse.json({error: 'Unauthorized'}, {status: 401})

  try {
    const {id, status} = await req.json()
    if (!id || !['approved', 'rejected'].includes(status)) {
      return NextResponse.json({error: 'Invalid request.'}, {status: 400})
    }

    const {data, error} = await db()
      .from('print_jobs')
      .update({status, failure_reason: null})
      .eq('id', id)
      .eq('status', 'pending')
      .select('id,status')
      .maybeSingle()

    if (error) throw error
    if (!data) {
      return NextResponse.json(
        {error: 'This print request is no longer pending, or the request ID was not found.'},
        {status: 409}
      )
    }

    return NextResponse.json({ok: true, job: data})
  } catch (e: any) {
    return NextResponse.json({error: e?.message ?? 'Unable to update job.'}, {status: 500})
  }
}
