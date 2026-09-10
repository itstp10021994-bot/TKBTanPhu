import { useState } from 'react'

export default function DataEditor({ value, onChange, onLoadSample, onGenerate, loading }) {
  const [text, setText] = useState(JSON.stringify(value, null, 2))
  const [error, setError] = useState('')

  function handleTextChange(e) {
    setText(e.target.value)
  }

  function handleApply() {
    try {
      const parsed = JSON.parse(text)
      setError('')
      onChange(parsed)
    } catch (e) {
      setError('JSON không hợp lệ: ' + e.message)
    }
  }

  async function handleLoadSample() {
    const sample = await onLoadSample()
    setText(JSON.stringify(sample, null, 2))
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Dữ liệu đầu vào</h2>
        <div className="button-row">
          <button onClick={handleLoadSample}>Tải dữ liệu mẫu</button>
          <button onClick={handleApply}>Áp dụng JSON</button>
          <button className="primary" onClick={() => onGenerate()} disabled={loading}>
            {loading ? 'Đang xếp lịch...' : 'Xếp thời khoá biểu'}
          </button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <textarea
        className="json-editor"
        value={text}
        onChange={handleTextChange}
        spellCheck={false}
      />
      <p className="hint">
        Chỉnh sửa GV / lớp / môn / hoạt động (activities) trực tiếp trong JSON này rồi bấm
        "Áp dụng JSON" trước khi "Xếp thời khoá biểu". Mỗi <code>activity</code> là 1 khối
        (lớp + môn + GV) cần xếp; xem README để biết ý nghĩa từng trường.
      </p>
    </div>
  )
}
