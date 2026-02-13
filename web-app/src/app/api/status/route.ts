import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${API_URL}/status`)
    const data = await response.json()

    return NextResponse.json(data)
  } catch (error) {
    return NextResponse.json(
      {
        api_version: '1.0.0',
        uptime: '0s',
        queue_count: 0,
        active_jobs: 0,
        jobs_count: 0,
        talent_count: 0,
      },
      { status: 200 }
    )
  }
}
