from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import TimetableInput, TimetableResult
from .scheduler import solve_timetable, SchedulerError
from .sample_data import build_sample_input

app = FastAPI(title="Timetable Scheduler API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/sample-data", response_model=TimetableInput)
def get_sample_data():
    """Trả về bộ dữ liệu mẫu để test nhanh / làm điểm khởi đầu."""
    return build_sample_input()


@app.post("/api/generate", response_model=TimetableResult)
def generate_timetable(data: TimetableInput):
    """Chạy solver CP-SAT trên dữ liệu do người dùng cung cấp."""
    try:
        return solve_timetable(data)
    except SchedulerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Lỗi không xác định: {e}")


@app.get("/api/health")
def health():
    return {"status": "ok"}
