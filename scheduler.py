"""
Scheduler engine: nhận TimetableInput, trả về TimetableResult.

Dùng Google OR-Tools CP-SAT để giải bài toán CSP. Toàn bộ ràng buộc trong
yêu cầu ban đầu được encode ở đây:

  1. Lệch giờ giữa các khối khi 1 GV dạy toàn trường
     (thứ tự order_group tăng dần trong cùng 1 ngày).
  2. Đồng giờ trên khối (các Activity cùng sync_key -> cùng (day, period)).
  3. Hai giáo viên cùng dạy 1 lớp (Activity.teachers có 2 phần tử).
  4. Một giáo viên dạy nhiều phân môn (Teacher dùng chung giữa nhiều Activity,
     ràng buộc "không trùng giờ" tính gộp trên mọi Activity của GV đó).
  5. Buổi trống chung cho từng tổ chuyên môn (1 buổi/tuần).
  6. Giờ phòng máy / GVNN / GVTG cố định trước (Activity.fixed_slots).
  7. Môn 3 tiết/tuần: không xếp cả 3 tiết trong 1 ngày (<=2 tiết/ngày).
  8. Môn 4 tiết/tuần: không xếp 3 tiết trong 1 ngày (<=2 tiết/ngày).
     Môn >=5 tiết/tuần: mỗi ngày tối đa 3 tiết.
  9. Không trùng giờ giữa các lớp bị "chiếm" bởi cùng 1 Activity,
     không trùng phòng theo room_type có capacity giới hạn (vd phòng máy).
  10. Nếu 1 ngày có từ 2 tiết trở lên của CÙNG 1 activity, các tiết đó phải
      LIỀN KỀ nhau (không xếp kiểu tiết A - tiết khác - tiết A lại).
"""

from __future__ import annotations
from collections import defaultdict

from ortools.sat.python import cp_model

from models import TimetableInput, TimetableResult, ScheduledLesson, Activity


class SchedulerError(Exception):
    pass


def _session_of(period: int, cfg) -> str:
    if period in cfg.morning_periods:
        return "morning"
    if period in cfg.afternoon_periods:
        return "afternoon"
    return "other"


DEFAULT_CONSTRAINT_FLAGS = {
    "period_spread": True,       # (7)&(8) không dồn tiết trong ngày
    "room_capacity": True,       # giới hạn phòng theo room_type
    "order_group": True,         # (1) lệch giờ giữa các khối
    "dept_free_session": True,   # (5) buổi trống chung theo tổ
    "no_gap": True,              # (10) 2 tiết cùng môn trong ngày phải liền kề
}


def solve_timetable(
    data: TimetableInput,
    enabled: dict | None = None,
    forbid_signatures: list[dict] | None = None,
    random_seed: int | None = None,
) -> TimetableResult:
    """enabled: dict bật/tắt các ràng buộc TUỲ CHỌN (xem DEFAULT_CONSTRAINT_FLAGS).
    Các ràng buộc CỐT LÕI (không trùng giờ GV/lớp, đồng bộ sync_key, đủ số
    tiết/tuần, đồng giảng, giờ cố định trước) luôn được áp dụng — không thể
    tắt, vì tắt đi sẽ tạo ra lịch vô nghĩa (chồng giờ).

    forbid_signatures: danh sách "chữ ký" lời giải TRƯỚC ĐÓ (result.solution_signature)
    — nếu truyền vào, solver bị ép tìm 1 lời giải khác với MỖI lời giải đó ít
    nhất 1 tiết, dùng cho tính năng "Xếp phương án khác".
    random_seed: đổi giá trị này giữa các lần gọi để CP-SAT khám phá vùng lời
    giải khác nhau (kết hợp với forbid_signatures cho ra phương án đa dạng
    hơn là chỉ khác 1 tiết).
    """
    flags = {**DEFAULT_CONSTRAINT_FLAGS, **(enabled or {})}
    cfg = data.config
    days = cfg.days
    periods = list(range(1, cfg.periods_per_day + 1))
    sessions = sorted({_session_of(p, cfg) for p in periods} - {"other"})

    model = cp_model.CpModel()

    activities: dict[str, Activity] = {a.id: a for a in data.activities}
    teacher_dept = {t.id: t.department_id for t in data.teachers}
    class_order_group = {c.id: c.order_group for c in data.classes}
    room_capacity = {r.room_type: r.capacity for r in data.rooms}

    # ---------------------------------------------------------------
    # 1) Biến quyết định x[a, d, p] cho từng activity KHÔNG cố định.
    #    Activity đã có fixed_slots đủ số tiết thì không cần biến quyết định,
    #    nhưng vẫn cần "biết" nó chiếm slot nào để chặn xung đột GV/lớp/phòng.
    # ---------------------------------------------------------------
    x: dict[tuple[str, int, int], cp_model.IntVar] = {}
    fixed_occupied: dict[tuple[str, int, int], bool] = {}

    for a in data.activities:
        fixed_set = {(s.day, s.period) for s in a.fixed_slots}
        if len(fixed_set) not in (0, a.periods_per_week):
            raise SchedulerError(
                f"Activity {a.id}: fixed_slots ({len(fixed_set)}) phải bằng 0 "
                f"hoặc bằng periods_per_week ({a.periods_per_week})"
            )
        is_fixed = len(fixed_set) == a.periods_per_week and a.periods_per_week > 0
        for d in days:
            for p in periods:
                if is_fixed:
                    fixed_occupied[(a.id, d, p)] = (d, p) in fixed_set
                else:
                    x[(a.id, d, p)] = model.NewBoolVar(f"x_{a.id}_{d}_{p}")

    def occ(a_id: str, d: int, p: int):
        """Trả về biến/giá trị 'activity a có chạy ở (d,p) hay không'."""
        if (a_id, d, p) in x:
            return x[(a_id, d, p)]
        return int(fixed_occupied.get((a_id, d, p), False))

    # ---------------------------------------------------------------
    # 2) Đủ số tiết/tuần cho activity không cố định.
    # ---------------------------------------------------------------
    for a in data.activities:
        if all((a.id, d, p) in x for d in days for p in periods) is False:
            continue
        var_list = [x[(a.id, d, p)] for d in days for p in periods if (a.id, d, p) in x]
        if var_list:
            model.Add(sum(var_list) == a.periods_per_week)

    # ---------------------------------------------------------------
    # 2b) Số tiết thực tế theo (khối, ngày) — BẮT BUỘC, không thể tắt, vì
    #     đây là thực tế vật lý (khối đó ngày đó chỉ học các tiết đã khai
    #     báo trong thời gian biểu). Nếu 1 activity liên quan nhiều lớp
    #     thuộc nhiều khối khác nhau, chỉ dùng các tiết mà MỌI khối đó
    #     cùng học trong ngày tương ứng (giao các tập tiết).
    # ---------------------------------------------------------------
    grade_of_class = {c.id: c.grade for c in data.classes}
    grade_day_allowed: dict[tuple[int, int], set[int]] = {
        (g.grade, g.day): (
            set(g.allowed_periods) if g.allowed_periods is not None
            else set(range(1, g.periods_count + 1))
        )
        for g in data.grade_day_periods
    }

    if grade_day_allowed:
        for a in data.activities:
            grades_involved = {
                grade_of_class[cid] for cid in a.blocked_classes if cid in grade_of_class
            }
            if not grades_involved:
                continue
            for d in days:
                allowed_sets = [
                    grade_day_allowed[(g, d)] for g in grades_involved if (g, d) in grade_day_allowed
                ]
                if not allowed_sets:
                    continue
                allowed_today = set.intersection(*allowed_sets)
                for p in periods:
                    if p in allowed_today:
                        continue
                    v = occ(a.id, d, p)
                    if isinstance(v, int):
                        if v:
                            raise SchedulerError(
                                f"Activity {a.id}: giờ cố định trước rơi vào ngày {d} tiết {p}, "
                                f"không nằm trong các tiết khối liên quan được học hôm đó "
                                f"({sorted(allowed_today)})."
                            )
                    else:
                        model.Add(v == 0)

    # ---------------------------------------------------------------
    # 3) Phân bổ tiết/ngày theo môn (ràng buộc 7 & 8) — tuỳ chọn.
    #    - 3 tiết/tuần  -> tối đa 2 tiết/ngày (không dồn cả 3 trong 1 ngày).
    #    - 4 tiết/tuần  -> tối đa 2 tiết/ngày (không dồn 3 tiết trong 1 ngày).
    #    - >=5 tiết/tuần -> tối đa 3 tiết/ngày.
    # ---------------------------------------------------------------
    if flags["period_spread"]:
        for a in data.activities:
            if a.periods_per_week <= 0:
                continue
            day_vars = []
            for d in days:
                vs = [x[(a.id, d, p)] for p in periods if (a.id, d, p) in x]
                if vs:
                    day_vars.append(sum(vs))
            if not day_vars:
                continue
            if a.periods_per_week in (3, 4):
                cap = 2
            elif a.periods_per_week >= 5:
                cap = 3
            else:
                cap = None
            if cap is not None:
                for dv in day_vars:
                    model.Add(dv <= cap)

    # ---------------------------------------------------------------
    # 4) Không trùng giờ của LỚP: mỗi lớp chỉ tham gia tối đa 1 activity
    #    tại mỗi (d, p) -- trừ các activity cùng sync_key (được coi là
    #    một hoạt động song song duy nhất, xem bước 6).
    # ---------------------------------------------------------------
    # Gom activity theo sync_key để không đếm trùng nhiều lần trong 1 nhóm.
    sync_groups: dict[str, list[Activity]] = defaultdict(list)
    standalone: list[Activity] = []
    for a in data.activities:
        if a.sync_key:
            sync_groups[a.sync_key].append(a)
        else:
            standalone.append(a)

    class_to_units: dict[str, list[tuple[str, list[Activity]]]] = defaultdict(list)
    for a in standalone:
        for c in a.blocked_classes:
            class_to_units[c].append((a.id, [a]))
    for key, acts in sync_groups.items():
        classes_in_group = {c for a in acts for c in a.blocked_classes}
        for c in classes_in_group:
            class_to_units[c].append((key, acts))

    for c, units in class_to_units.items():
        for d in days:
            for p in periods:
                terms = []
                for _, acts in units:
                    # cùng 1 sync group, tất cả các activity trùng giá trị
                    # (được ép bằng constraint ở bước 6) nên chỉ cần lấy 1
                    # đại diện để tránh đếm lặp.
                    terms.append(occ(acts[0].id, d, p))
                if terms:
                    model.Add(sum(terms) <= 1)

    # ---------------------------------------------------------------
    # 5) Không trùng giờ của GIÁO VIÊN (tính gộp mọi activity/phân môn).
    # ---------------------------------------------------------------
    teacher_to_activities: dict[str, list[str]] = defaultdict(list)
    for a in data.activities:
        for t in a.teachers:
            teacher_to_activities[t].append(a.id)

    for t, act_ids in teacher_to_activities.items():
        for d in days:
            for p in periods:
                terms = [occ(aid, d, p) for aid in act_ids]
                if terms:
                    model.Add(sum(terms) <= 1)

    # ---------------------------------------------------------------
    # 6) Đồng giờ trên khối: các activity cùng sync_key phải trùng
    #    (day, period) với nhau tuyệt đối.
    # ---------------------------------------------------------------
    for key, acts in sync_groups.items():
        base = acts[0]
        for other in acts[1:]:
            for d in days:
                for p in periods:
                    ov1 = occ(base.id, d, p)
                    ov2 = occ(other.id, d, p)
                    # Nếu 1 trong 2 là hằng số (fixed) thì so sánh trực tiếp,
                    # nếu cả 2 là biến thì ép bằng nhau.
                    if isinstance(ov1, int) and isinstance(ov2, int):
                        if ov1 != ov2:
                            raise SchedulerError(
                                f"sync_key '{key}': activity {base.id} và "
                                f"{other.id} có fixed_slots không khớp nhau."
                            )
                    else:
                        model.Add(ov1 == ov2)

    # ---------------------------------------------------------------
    # 7) Giới hạn phòng theo room_type (vd phòng máy chỉ có N phòng) — tuỳ chọn.
    # ---------------------------------------------------------------
    if flags["room_capacity"]:
        room_type_to_activities: dict[str, list[str]] = defaultdict(list)
        for a in data.activities:
            if a.room_type:
                room_type_to_activities[a.room_type].append(a.id)

        for rtype, act_ids in room_type_to_activities.items():
            cap = room_capacity.get(rtype, 1)
            for d in days:
                for p in periods:
                    terms = [occ(aid, d, p) for aid in act_ids]
                    if terms:
                        model.Add(sum(terms) <= cap)

    # ---------------------------------------------------------------
    # 8) Lệch giờ giữa các khối: GV dạy nhiều order_group phải dạy theo
    #    thứ tự order_group tăng dần trong CÙNG 1 NGÀY (không xen kẽ).
    #    Cách làm: với mỗi GV, mỗi ngày, mỗi order_group có mặt trong ngày
    #    đó -> lấy period sớm nhất/muộn nhất; ép max(group nhỏ hơn) <
    #    min(group lớn hơn kế tiếp).
    # ---------------------------------------------------------------
    BIG_LATE = max(periods) + 1
    BIG_EARLY = 0

    for t, act_ids in (teacher_to_activities.items() if flags["order_group"] else []):
        # nhóm activity của GV này theo order_group của lớp mà nó phục vụ
        group_to_acts: dict[int, list[str]] = defaultdict(list)
        for aid in act_ids:
            a = activities[aid]
            groups = {class_order_group.get(c, 0) for c in a.blocked_classes}
            for g in groups:
                group_to_acts[g].append(aid)

        distinct_groups = sorted(g for g in group_to_acts if g > 0)
        if len(distinct_groups) < 2:
            continue  # GV chỉ dạy 1 nhóm khối -> không cần ràng buộc thứ tự

        for d in days:
            # has_g: GV có dạy nhóm g vào ngày d không
            has_g = {}
            min_p = {}
            max_p = {}
            for g in distinct_groups:
                occs = [occ(aid, d, p) for aid in group_to_acts[g] for p in periods
                        if True]
                # Xây period-indicator cho nhóm g ngày d
                per_occ = []
                for p in periods:
                    vals = [occ(aid, d, p) for aid in group_to_acts[g]]
                    if all(isinstance(v, int) for v in vals):
                        per_occ.append((p, int(any(vals))))
                    else:
                        b = model.NewBoolVar(f"grp_{t}_{g}_{d}_{p}")
                        # b == OR(vals)
                        real_vals = [v for v in vals if not isinstance(v, int) or v]
                        int_any = any(v for v in vals if isinstance(v, int))
                        var_vals = [v for v in vals if not isinstance(v, int)]
                        if int_any:
                            model.Add(b == 1)
                        elif var_vals:
                            model.AddMaxEquality(b, var_vals)
                        else:
                            model.Add(b == 0)
                        per_occ.append((p, b))

                hg = model.NewBoolVar(f"has_{t}_{g}_{d}")
                terms = [v for _, v in per_occ]
                if all(isinstance(v, int) for v in terms):
                    model.Add(hg == int(any(terms)))
                else:
                    model.AddMaxEquality(hg, terms)
                has_g[g] = hg

                mn = model.NewIntVar(0, BIG_LATE, f"min_{t}_{g}_{d}")
                mx = model.NewIntVar(0, BIG_LATE, f"max_{t}_{g}_{d}")
                # min/max chỉ có ý nghĩa khi has_g=1; khi has_g=0 để giá trị
                # trung lập (không ràng buộc thật nhờ OnlyEnforceIf).
                for p, v in per_occ:
                    if isinstance(v, int):
                        if v:
                            model.Add(mn <= p).OnlyEnforceIf(hg)
                            model.Add(mx >= p).OnlyEnforceIf(hg)
                    else:
                        model.Add(mn <= p).OnlyEnforceIf([hg, v])
                        model.Add(mx >= p).OnlyEnforceIf([hg, v])
                min_p[g] = mn
                max_p[g] = mx

            for i in range(len(distinct_groups) - 1):
                g1, g2 = distinct_groups[i], distinct_groups[i + 1]
                both = model.NewBoolVar(f"both_{t}_{g1}_{g2}_{d}")
                model.AddMultiplicationEquality(both, [has_g[g1], has_g[g2]])
                model.Add(max_p[g1] < min_p[g2]).OnlyEnforceIf(both)

    # ---------------------------------------------------------------
    # 9) Buổi trống chung cho từng tổ chuyên môn (1 buổi/tuần).
    # ---------------------------------------------------------------
    dept_free_choice: dict[str, dict[tuple[int, str], cp_model.IntVar]] = {}
    for dept_id in (data.departments_needing_free_session if flags["dept_free_session"] else []):
        dept_teachers = [tid for tid, did in teacher_dept.items() if did == dept_id]
        if not dept_teachers:
            continue
        choices = {}
        for d in days:
            for s in sessions:
                choices[(d, s)] = model.NewBoolVar(f"free_{dept_id}_{d}_{s}")
        model.Add(sum(choices.values()) == 1)
        dept_free_choice[dept_id] = choices

        for (d, s), chosen in choices.items():
            sess_periods = [p for p in periods if _session_of(p, cfg) == s]
            for t in dept_teachers:
                for aid in teacher_to_activities.get(t, []):
                    for p in sess_periods:
                        v = occ(aid, d, p)
                        if isinstance(v, int):
                            if v:
                                model.Add(chosen == 0)
                        else:
                            model.Add(v == 0).OnlyEnforceIf(chosen)

    # ---------------------------------------------------------------
    # 10) Không ngắt quãng: nếu 1 ngày có >=2 tiết của CÙNG 1 activity,
    #     các tiết đó phải liền kề nhau (không xếp kiểu A - (nghỉ/môn khác) - A).
    #     Cách làm: với mọi bộ ba tiết p1 < pm < p2 trong cùng ngày, nếu p1
    #     và p2 đều được xếp thì pm cũng phải được xếp (nếu không sẽ tạo ra
    #     1 khoảng trống ở giữa 2 tiết của cùng activity đó).
    # ---------------------------------------------------------------
    if flags["no_gap"]:
        for a in data.activities:
            if a.periods_per_week < 2:
                continue
            for d in days:
                for i, p1 in enumerate(periods):
                    for j in range(i + 2, len(periods)):
                        p2 = periods[j]
                        for k in range(i + 1, j):
                            pm = periods[k]
                            v1 = occ(a.id, d, p1)
                            vm = occ(a.id, d, pm)
                            v2 = occ(a.id, d, p2)
                            if isinstance(v1, int) and isinstance(vm, int) and isinstance(v2, int):
                                if v1 and v2 and not vm:
                                    raise SchedulerError(
                                        f"Activity {a.id}: giờ cố định trước tạo khoảng "
                                        f"trống giữa 2 tiết cùng môn trong ngày {d} "
                                        f"(tiết {p1} và {p2} có giờ nhưng tiết {pm} thì không)."
                                    )
                            else:
                                # v1 + v2 - vm <= 1  <=>  không thể v1=v2=1 mà vm=0
                                model.Add(v1 + v2 - vm <= 1)

    # ---------------------------------------------------------------
    # "Xếp phương án khác": ép lời giải mới khác MỖI lời giải trước đó
    # ít nhất 1 tiết (những tiết đã =1 ở lời giải cũ không được y nguyên
    # 100% ở lời giải mới).
    # ---------------------------------------------------------------
    for sig in (forbid_signatures or []):
        ones = []
        for key in sig:
            try:
                aid, d_str, p_str = key.split("|")
                d, p = int(d_str), int(p_str)
            except ValueError:
                continue
            if (aid, d, p) in x:
                ones.append(x[(aid, d, p)])
        if ones:
            model.Add(sum(ones) <= len(ones) - 1)

    # ---------------------------------------------------------------
    # Giải
    # ---------------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.max_solver_seconds
    solver.parameters.num_search_workers = 8
    if random_seed is not None:
        solver.parameters.random_seed = int(random_seed)
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return TimetableResult(
            status="INFEASIBLE" if status == cp_model.INFEASIBLE else "ERROR",
            message="Không tìm được lịch thoả mãn mọi ràng buộc trong thời gian cho phép. "
                    "Hãy kiểm tra lại dữ liệu đầu vào (số tiết/tuần, số GV, ràng buộc cứng).",
        )

    lessons: list[ScheduledLesson] = []
    for a in data.activities:
        for d in days:
            for p in periods:
                v = occ(a.id, d, p)
                val = solver.Value(v) if not isinstance(v, int) else v
                if val:
                    lessons.append(ScheduledLesson(
                        activity_id=a.id,
                        activity_name=a.name,
                        subject_id=a.subject_id,
                        class_ids=a.blocked_classes,
                        teacher_ids=a.teachers,
                        day=d,
                        period=p,
                    ))

    dept_free = {}
    for dept_id, choices in dept_free_choice.items():
        for (d, s), var in choices.items():
            if solver.Value(var):
                ten_ngay = {1: "Thứ 2", 2: "Thứ 3", 3: "Thứ 4", 4: "Thứ 5", 5: "Thứ 6",
                            6: "Thứ 7", 7: "Chủ nhật"}.get(d, f"Ngày {d}")
                dept_free[dept_id] = f"{ten_ngay} — buổi {('sáng' if s == 'morning' else 'chiều')}"

    signature = {
        f"{aid}|{d}|{p}": 1
        for (aid, d, p), var in x.items()
        if solver.Value(var)
    }

    return TimetableResult(
        status="OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
        message="Xếp lịch thành công.",
        lessons=lessons,
        department_free_sessions=dept_free,
        solution_signature=signature,
    )
