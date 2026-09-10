import { useState } from 'react'

const DAY_NAMES = { 1: 'Thứ 2', 2: 'Thứ 3', 3: 'Thứ 4', 4: 'Thứ 5', 5: 'Thứ 6', 6: 'Thứ 7' }

// Bảng thời khoá biểu CHỈ HIỂN THỊ kết quả do solver (CP-SAT) tính ra.
// Không có chỉnh tay / kéo-thả: nếu ràng buộc trường thay đổi, sửa lại
// dữ liệu đầu vào (activities, order_group, sync_key...) rồi bấm
// "Xếp thời khoá biểu" lại để solver tự tính ra lịch mới, luôn đảm bảo
// thoả toàn bộ ràng buộc cứng đã khai báo.
export default function TimetableGrid({ result, config, classes }) {
  const [activeClass, setActiveClass] = useState(classes[0]?.id)

  const days = config.days
  const periods = Array.from({ length: config.periods_per_day }, (_, i) => i + 1)

  function lessonAt(classId, day, period) {
    return result.lessons.find(
      (l) => l.class_ids.includes(classId) && l.day === day && l.period === period
    )
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Thời khoá biểu ({result.status})</h2>
      </div>

      {Object.keys(result.department_free_sessions || {}).length > 0 && (
        <div className="free-sessions">
          <strong>Buổi trống chung theo tổ:</strong>
          <ul>
            {Object.entries(result.department_free_sessions).map(([dept, when]) => (
              <li key={dept}>{dept}: {when}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="tabs">
        {classes.map((c) => (
          <button
            key={c.id}
            className={c.id === activeClass ? 'tab active' : 'tab'}
            onClick={() => setActiveClass(c.id)}
          >
            {c.name}
          </button>
        ))}
      </div>

      <table className="timetable">
        <thead>
          <tr>
            <th>Tiết \ Ngày</th>
            {days.map((d) => (
              <th key={d}>{DAY_NAMES[d] || `Ngày ${d}`}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {periods.map((p) => (
            <tr key={p}>
              <td className="period-label">Tiết {p}</td>
              {days.map((d) => {
                const l = lessonAt(activeClass, d, p)
                return (
                  <td key={d} className={l ? 'cell filled' : 'cell'}>
                    {l && (
                      <div className="lesson" title={`GV: ${l.teacher_ids.join(', ')}`}>
                        <div className="lesson-name">{l.activity_name}</div>
                        <div className="lesson-teacher">{l.teacher_ids.join(', ')}</div>
                      </div>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint">
        Lịch này do solver tính tự động theo toàn bộ ràng buộc đã khai báo — không chỉnh tay
        trực tiếp trên bảng. Muốn thay đổi kết quả: sửa dữ liệu/ràng buộc ở khung phía trên
        rồi bấm lại "Xếp thời khoá biểu" để solver tính lại, đảm bảo luôn hợp lệ 100%.
      </p>
    </div>
  )
}
