import { useState } from 'react'
import DataEditor from './components/DataEditor.jsx'
import TimetableGrid from './components/TimetableGrid.jsx'
import { fetchSampleData, generateTimetable } from './api.js'

const EMPTY_INPUT = {
  config: { days: [1, 2, 3, 4, 5, 6], periods_per_day: 10, morning_periods: [1,2,3,4,5], afternoon_periods: [6,7,8,9,10], max_solver_seconds: 30 },
  departments: [],
  teachers: [],
  classes: [],
  rooms: [],
  activities: [],
  departments_needing_free_session: [],
}

export default function App() {
  const [input, setInput] = useState(EMPTY_INPUT)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleLoadSample() {
    const sample = await fetchSampleData()
    setInput(sample)
    return sample
  }

  async function handleGenerate() {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await generateTimetable(input)
      if (res.status === 'INFEASIBLE' || res.status === 'ERROR') {
        setError(res.message)
      } else {
        setResult(res)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header>
        <h1>Hệ thống Xếp Thời Khoá Biểu</h1>
      </header>

      <DataEditor
        value={input}
        onChange={setInput}
        onLoadSample={handleLoadSample}
        onGenerate={handleGenerate}
        loading={loading}
      />

      {error && <div className="panel error-panel">Lỗi: {error}</div>}

      {result && (
        <TimetableGrid result={result} config={input.config} classes={input.classes} />
      )}
    </div>
  )
}
