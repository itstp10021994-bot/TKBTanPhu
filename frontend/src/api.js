const BASE = '/api'

export async function fetchSampleData() {
  const res = await fetch(`${BASE}/sample-data`)
  if (!res.ok) throw new Error('Không tải được dữ liệu mẫu')
  return res.json()
}

export async function generateTimetable(input) {
  const res = await fetch(`${BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  const data = await res.json()
  if (!res.ok) {
    throw new Error(data.detail || 'Lỗi khi xếp lịch')
  }
  return data
}
