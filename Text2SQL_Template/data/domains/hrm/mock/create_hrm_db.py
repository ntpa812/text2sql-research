"""
Script tạo HRM mock database (SQLite).
Chạy: python data/mock/create_hrm_db.py
Output: data/mock/hrm.db
"""

import sqlite3
import os
import random
from datetime import date, datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "hrm.db")

# ── 1. Schema ────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS department (
    department_id   TEXT PRIMARY KEY,
    department_name TEXT NOT NULL,
    manager_id      TEXT
);

CREATE TABLE IF NOT EXISTS employee (
    employee_id       TEXT PRIMARY KEY,
    employee_name     TEXT NOT NULL,
    department_id     TEXT NOT NULL,
    job_title         TEXT NOT NULL,
    employment_status TEXT NOT NULL,   -- ACTIVE | PROBATION | RESIGNED | SUSPENDED
    hire_date         TEXT NOT NULL,   -- YYYY-MM-DD
    email             TEXT,
    phone             TEXT,
    FOREIGN KEY (department_id) REFERENCES department(department_id)
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     TEXT NOT NULL,
    attendance_date TEXT NOT NULL,     -- YYYY-MM-DD
    check_in_time   TEXT,              -- HH:MM:SS  (NULL nếu absent/on_leave)
    check_out_time  TEXT,              -- HH:MM:SS
    status          TEXT NOT NULL,     -- PRESENT | LATE | REMOTE | ABSENT | ON_LEAVE
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
);

CREATE TABLE IF NOT EXISTS leave_type (
    leave_type_id     TEXT PRIMARY KEY,
    leave_type_name   TEXT NOT NULL,
    max_days_per_year INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS leave_balance (
    balance_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     TEXT NOT NULL,
    leave_type_id   TEXT NOT NULL,
    year            INTEGER NOT NULL,
    total_days      REAL NOT NULL,
    used_days       REAL NOT NULL DEFAULT 0,
    remaining_days  REAL NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    FOREIGN KEY (leave_type_id) REFERENCES leave_type(leave_type_id)
);

CREATE TABLE IF NOT EXISTS leave_request (
    request_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     TEXT NOT NULL,
    leave_type_id   TEXT NOT NULL,
    start_date      TEXT NOT NULL,     -- YYYY-MM-DD
    end_date        TEXT NOT NULL,     -- YYYY-MM-DD
    total_days      REAL NOT NULL,
    reason          TEXT,
    status          TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING | APPROVED | REJECTED | CANCELLED
    created_at      TEXT NOT NULL,     -- YYYY-MM-DD HH:MM:SS
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    FOREIGN KEY (leave_type_id) REFERENCES leave_type(leave_type_id)
);
"""

# ── 2. Dữ liệu phòng ban ─────────────────────────────────────────────────────

DEPARTMENTS = [
    ("DEPT001", "Ban Giám Đốc",                  "EMP001"),
    ("DEPT002", "Phòng Nhân Sự",                 "EMP005"),
    ("DEPT003", "Phòng Kế Toán - Tài Chính",     "EMP010"),
    ("DEPT004", "Phòng Kinh Doanh",              "EMP015"),
    ("DEPT005", "Phòng Marketing",               "EMP020"),
    ("DEPT006", "Phòng Công Nghệ Thông Tin",     "EMP025"),
    ("DEPT007", "Phòng Hành Chính",              "EMP030"),
    ("DEPT008", "Phòng Pháp Chế",               "EMP035"),
    ("DEPT009", "Phòng Vận Hành",               "EMP040"),
    ("DEPT010", "Phòng Chăm Sóc Khách Hàng",    "EMP045"),
]

# ── 3. Dữ liệu nhân viên ────────────────────────────────────────────────────
# (employee_id, employee_name, department_id, job_title, employment_status, hire_date)

EMPLOYEES = [
    # Ban Giám Đốc
    ("EMP001", "Nguyễn Văn An",     "DEPT001", "Giám Đốc Điều Hành",        "ACTIVE",    "2018-03-01"),
    ("EMP002", "Trần Thị Bích",     "DEPT001", "Phó Giám Đốc",              "ACTIVE",    "2019-05-15"),
    ("EMP003", "Lê Văn Cường",      "DEPT001", "Trợ Lý Giám Đốc",           "ACTIVE",    "2021-07-10"),
    ("EMP004", "Phạm Thị Dung",     "DEPT001", "Thư Ký Điều Hành",          "RESIGNED",  "2020-01-20"),

    # Phòng Nhân Sự
    ("EMP005", "Hoàng Văn Em",      "DEPT002", "Trưởng Phòng Nhân Sự",      "ACTIVE",    "2019-02-01"),
    ("EMP006", "Vũ Thị Hoa",        "DEPT002", "Chuyên Viên Nhân Sự",       "ACTIVE",    "2020-06-15"),
    ("EMP007", "Đặng Văn Giang",    "DEPT002", "Chuyên Viên Tuyển Dụng",    "ACTIVE",    "2021-09-01"),
    ("EMP008", "Bùi Thị Hương",     "DEPT002", "Nhân Viên Nhân Sự",         "PROBATION", "2025-12-01"),
    ("EMP009", "Ngô Văn Khoa",      "DEPT002", "Nhân Viên Đào Tạo",         "ACTIVE",    "2022-03-10"),

    # Phòng Kế Toán - Tài Chính
    ("EMP010", "Dương Thị Lan",     "DEPT003", "Trưởng Phòng Kế Toán",      "ACTIVE",    "2018-08-01"),
    ("EMP011", "Lý Văn Minh",       "DEPT003", "Kế Toán Tổng Hợp",          "ACTIVE",    "2020-04-20"),
    ("EMP012", "Trịnh Thị Nhung",   "DEPT003", "Kế Toán Viên",              "ACTIVE",    "2021-11-15"),
    ("EMP013", "Phan Văn Quân",     "DEPT003", "Kế Toán Thuế",              "RESIGNED",  "2019-06-01"),
    ("EMP014", "Hồ Thị Phúc",       "DEPT003", "Kiểm Soát Viên Tài Chính",  "ACTIVE",    "2022-01-05"),

    # Phòng Kinh Doanh
    ("EMP015", "Đinh Văn Sơn",      "DEPT004", "Trưởng Phòng Kinh Doanh",   "ACTIVE",    "2018-11-01"),
    ("EMP016", "Mai Thị Trang",     "DEPT004", "Chuyên Viên Kinh Doanh",    "ACTIVE",    "2020-08-10"),
    ("EMP017", "Cao Văn Tuấn",      "DEPT004", "Nhân Viên Kinh Doanh",      "ACTIVE",    "2021-03-15"),
    ("EMP018", "Lưu Thị Uyên",      "DEPT004", "Nhân Viên Kinh Doanh",      "PROBATION", "2026-01-10"),
    ("EMP019", "Hà Văn Vinh",       "DEPT004", "Nhân Viên Kinh Doanh",      "ACTIVE",    "2023-07-01"),

    # Phòng Marketing
    ("EMP020", "Nguyễn Thị Xuân",   "DEPT005", "Trưởng Phòng Marketing",    "ACTIVE",    "2019-09-01"),
    ("EMP021", "Trần Văn Yên",      "DEPT005", "Chuyên Viên Marketing",     "ACTIVE",    "2021-02-20"),
    ("EMP022", "Lê Thị Ánh",        "DEPT005", "Chuyên Viên Content",       "ACTIVE",    "2022-05-10"),
    ("EMP023", "Phạm Văn Bình",     "DEPT005", "Nhân Viên Marketing",       "RESIGNED",  "2021-08-01"),
    ("EMP024", "Hoàng Thị Châu",    "DEPT005", "Nhân Viên Thiết Kế",        "ACTIVE",    "2023-01-15"),

    # Phòng Công Nghệ Thông Tin
    ("EMP025", "Vũ Văn Đức",        "DEPT006", "Trưởng Phòng CNTT",         "ACTIVE",    "2018-05-01"),
    ("EMP026", "Đặng Thị Giang",    "DEPT006", "Lập Trình Viên Senior",     "ACTIVE",    "2019-10-15"),
    ("EMP027", "Bùi Văn Hải",       "DEPT006", "Lập Trình Viên",            "ACTIVE",    "2021-04-01"),
    ("EMP028", "Ngô Thị Hạnh",      "DEPT006", "Kỹ Thuật Viên Hệ Thống",   "ACTIVE",    "2022-08-20"),
    ("EMP029", "Dương Văn Kiên",    "DEPT006", "Lập Trình Viên",            "PROBATION", "2026-02-01"),

    # Phòng Hành Chính
    ("EMP030", "Lý Thị Linh",       "DEPT007", "Trưởng Phòng Hành Chính",   "ACTIVE",    "2019-01-15"),
    ("EMP031", "Trịnh Văn Long",    "DEPT007", "Nhân Viên Hành Chính",      "ACTIVE",    "2020-10-01"),
    ("EMP032", "Phan Thị Mỹ",       "DEPT007", "Nhân Viên Văn Phòng",       "ACTIVE",    "2022-03-20"),
    ("EMP033", "Hồ Văn Nam",        "DEPT007", "Nhân Viên Lái Xe",          "SUSPENDED", "2020-07-10"),
    ("EMP034", "Đinh Thị Oanh",     "DEPT007", "Nhân Viên Hành Chính",      "ACTIVE",    "2023-05-15"),

    # Phòng Pháp Chế
    ("EMP035", "Mai Văn Phong",     "DEPT008", "Trưởng Phòng Pháp Chế",    "ACTIVE",    "2019-04-01"),
    ("EMP036", "Cao Thị Quyên",     "DEPT008", "Chuyên Viên Pháp Lý",      "ACTIVE",    "2020-12-10"),
    ("EMP037", "Lưu Văn Rạng",      "DEPT008", "Chuyên Viên Hợp Đồng",     "ACTIVE",    "2022-06-01"),
    ("EMP038", "Hà Thị Sương",      "DEPT008", "Nhân Viên Pháp Chế",       "RESIGNED",  "2022-09-01"),

    # Phòng Vận Hành
    ("EMP039", "Nguyễn Văn Thắng",  "DEPT009", "Chuyên Viên Vận Hành",     "ACTIVE",    "2021-01-10"),
    ("EMP040", "Trần Thị Uyên",     "DEPT009", "Trưởng Phòng Vận Hành",    "ACTIVE",    "2018-12-01"),
    ("EMP041", "Lê Văn Vũ",         "DEPT009", "Nhân Viên Vận Hành",       "ACTIVE",    "2022-04-15"),
    ("EMP042", "Phạm Thị Yến",      "DEPT009", "Nhân Viên Vận Hành",       "ACTIVE",    "2023-08-20"),
    ("EMP043", "Hoàng Văn Anh",     "DEPT009", "Kỹ Thuật Viên Vận Hành",   "SUSPENDED", "2021-06-01"),

    # Phòng Chăm Sóc Khách Hàng
    ("EMP044", "Vũ Thị Bình",       "DEPT010", "Chuyên Viên CSKH",         "ACTIVE",    "2020-09-15"),
    ("EMP045", "Đặng Văn Chiến",    "DEPT010", "Trưởng Phòng CSKH",        "ACTIVE",    "2019-07-01"),
    ("EMP046", "Bùi Thị Diệu",      "DEPT010", "Nhân Viên CSKH",           "ACTIVE",    "2021-10-20"),
    ("EMP047", "Ngô Văn Hậu",       "DEPT010", "Nhân Viên CSKH",           "PROBATION", "2026-01-20"),
    ("EMP048", "Dương Thị Khánh",   "DEPT010", "Nhân Viên CSKH",           "ACTIVE",    "2022-11-10"),
    ("EMP049", "Lý Văn Lộc",        "DEPT010", "Chuyên Viên CSKH",         "ACTIVE",    "2020-03-05"),
    ("EMP050", "Trịnh Thị Mai",     "DEPT010", "Nhân Viên CSKH",           "RESIGNED",  "2023-04-01"),
]

# ── 4. Tạo email & phone ─────────────────────────────────────────────────────

def make_email(name: str, emp_id: str) -> str:
    import unicodedata, re
    name_ascii = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    parts = name_ascii.lower().split()
    if len(parts) >= 2:
        local = parts[-1] + "." + parts[0][0]
    else:
        local = parts[0]
    local = re.sub(r"[^a-z0-9.]", "", local)
    return f"{local}@company.vn"


def make_phone(emp_id: str) -> str:
    seed = int(emp_id.replace("EMP", ""))
    random.seed(seed * 17 + 3)
    prefix = random.choice(["090", "091", "093", "094", "096", "097", "098", "032", "033", "034", "035"])
    suffix = "".join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{prefix}{suffix}"


# ── 5. Sinh dữ liệu chấm công ────────────────────────────────────────────────

def working_days(start: date, end: date):
    """Trả về các ngày làm việc (T2-T6) trong khoảng."""
    cur = start
    while cur <= end:
        if cur.weekday() < 5:  # 0=Mon, 4=Fri
            yield cur
        cur += timedelta(days=1)


STATUS_WEIGHTS = [
    ("PRESENT",  70),
    ("REMOTE",   12),
    ("LATE",      8),
    ("ON_LEAVE",  6),
    ("ABSENT",    4),
]
STATUSES = [s for s, w in STATUS_WEIGHTS for _ in range(w)]


def rand_time(base_h: int, base_m: int, jitter_m: int, seed: int) -> str:
    random.seed(seed)
    delta = random.randint(0, jitter_m)
    total_m = base_h * 60 + base_m + delta
    h, m = divmod(total_m, 60)
    s = random.randint(0, 59)
    return f"{h:02d}:{m:02d}:{s:02d}"


def gen_attendance(employees, start: date, end: date):
    rows = []
    active_statuses = {"ACTIVE", "PROBATION"}
    active_emps = [e for e in employees if e[4] in active_statuses]

    for emp in active_emps:
        emp_id = emp[0]
        hire_dt = date.fromisoformat(emp[5])

        for wday in working_days(start, end):
            if wday < hire_dt:
                continue

            seed = hash(f"{emp_id}{wday}") & 0xFFFFFF
            random.seed(seed)
            status = random.choice(STATUSES)

            if status in ("ABSENT", "ON_LEAVE"):
                check_in = None
                check_out = None
            elif status == "REMOTE":
                check_in = None
                check_out = None
            elif status == "LATE":
                check_in  = rand_time(8, 10, 80, seed)      # 08:10 ~ 09:30
                check_out = rand_time(17, 5, 55, seed + 1)  # 17:05 ~ 18:00
            else:  # PRESENT
                check_in  = rand_time(7, 30, 30, seed)      # 07:30 ~ 08:00
                check_out = rand_time(17, 0, 30, seed + 1)  # 17:00 ~ 17:30

            rows.append((emp_id, wday.isoformat(), check_in, check_out, status))

    return rows


# ── 6. Loại nghỉ phép ────────────────────────────────────────────────────────

LEAVE_TYPES = [
    ("AL", "Phép năm",       12),
    ("SL", "Phép ốm",        30),
    ("CL", "Phép đặc biệt",   5),
    ("ML", "Phép thai sản",  180),
    ("UL", "Nghỉ không lương", 0),
]


# ── 7. Sinh dữ liệu leave_balance ────────────────────────────────────────────

def gen_leave_balances(employees, year=2026):
    """Sinh số dư phép cho NV ACTIVE/PROBATION.
    EMP001 khớp với leave_request APPROVED (AL=2, SL=2, CL=0)."""
    rows = []
    active = [e for e in employees if e[4] in ("ACTIVE", "PROBATION")]
    cfg = [("AL", 12, 5), ("SL", 30, 3), ("CL", 5, 2)]
    emp001_used = {"AL": 2.0, "SL": 2.0, "CL": 0.0}

    for emp in active:
        eid = emp[0]
        rng_seed = hash(f"balance-{eid}") & 0xFFFFFF
        random.seed(rng_seed)
        for lt_id, total, max_used in cfg:
            if eid == "EMP001":
                used = emp001_used[lt_id]
            else:
                used = float(random.randint(0, max_used))
            rows.append((eid, lt_id, year, float(total), used, float(total) - used))
    return rows


# ── 8. Sinh dữ liệu leave_request ────────────────────────────────────────────

def gen_leave_requests(employees):
    """Sinh ~20 đơn nghỉ phép Q1/2026.
    EMP001: 2 APPROVED + 1 PENDING. Còn lại random."""
    rows = []

    # Đơn cố định cho EMP001
    rows.append(("EMP001", "AL", "2026-01-13", "2026-01-14", 2.0,
                 "Nghỉ giải quyết việc gia đình", "APPROVED", "2026-01-10 09:00:00"))
    rows.append(("EMP001", "SL", "2026-02-17", "2026-02-18", 2.0,
                 "Bị ốm cần nghỉ dưỡng", "APPROVED", "2026-02-16 14:30:00"))
    rows.append(("EMP001", "AL", "2026-03-27", "2026-03-28", 2.0,
                 "Đưa con đi khám bệnh", "PENDING", "2026-03-20 08:15:00"))

    # Random cho NV ACTIVE khác
    active_others = [e[0] for e in employees if e[4] == "ACTIVE" and e[0] != "EMP001"]
    random.seed(42)
    reasons = [
        "Nghỉ phép cá nhân", "Về quê thăm gia đình", "Đi khám bệnh định kỳ",
        "Giải quyết việc riêng", "Nghỉ ốm", "Tham dự đám cưới",
        "Chăm con ốm", "Nghỉ phép du lịch",
    ]
    statuses = ["APPROVED"] * 3 + ["PENDING"] + ["REJECTED"]

    for _ in range(17):
        eid = random.choice(active_others)
        lt = random.choice(["AL", "AL", "SL", "SL", "CL"])
        st = random.choice(statuses)
        month = random.randint(1, 3)
        day = random.randint(1, 25)
        start = date(2026, month, day)
        while start.weekday() >= 5:
            start += timedelta(days=1)
        dur = random.randint(1, 4)
        end = start
        cnt = 1
        while cnt < dur:
            end += timedelta(days=1)
            if end.weekday() < 5:
                cnt += 1
        created = datetime(start.year, start.month, start.day,
                           random.randint(8, 17), random.randint(0, 59), 0)
        created -= timedelta(days=random.randint(1, 5))
        rows.append((eid, lt, start.isoformat(), end.isoformat(), float(dur),
                     random.choice(reasons), st, created.strftime("%Y-%m-%d %H:%M:%S")))
    return rows


# ── 9. Main ──────────────────────────────────────────────────────────────────

def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Schema
    cur.executescript(SCHEMA)

    # Departments
    cur.executemany(
        "INSERT INTO department VALUES (?, ?, ?)",
        DEPARTMENTS,
    )

    # Employees (thêm email + phone)
    emp_rows = []
    for e in EMPLOYEES:
        emp_id, name, dept, title, status, hire = e
        emp_rows.append((emp_id, name, dept, title, status, hire,
                         make_email(name, emp_id), make_phone(emp_id)))
    cur.executemany(
        "INSERT INTO employee VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        emp_rows,
    )

    # Attendance: 2026-01-01 → 2026-03-24
    att_rows = gen_attendance(EMPLOYEES, date(2026, 1, 1), date(2026, 3, 24))
    cur.executemany(
        "INSERT INTO attendance (employee_id, attendance_date, check_in_time, check_out_time, status) VALUES (?, ?, ?, ?, ?)",
        att_rows,
    )

    # Leave types
    cur.executemany(
        "INSERT INTO leave_type VALUES (?, ?, ?)",
        LEAVE_TYPES,
    )

    # Leave balances
    bal_rows = gen_leave_balances(EMPLOYEES)
    cur.executemany(
        "INSERT INTO leave_balance (employee_id, leave_type_id, year, total_days, used_days, remaining_days) VALUES (?, ?, ?, ?, ?, ?)",
        bal_rows,
    )

    # Leave requests
    req_rows = gen_leave_requests(EMPLOYEES)
    cur.executemany(
        "INSERT INTO leave_request (employee_id, leave_type_id, start_date, end_date, total_days, reason, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        req_rows,
    )

    conn.commit()
    conn.close()

    print(f"[OK] Created: {DB_PATH}")
    print(f"     Departments : {len(DEPARTMENTS)}")
    print(f"     Employees   : {len(EMPLOYEES)}")
    print(f"     Attendance  : {len(att_rows)} records")
    print(f"     Leave types : {len(LEAVE_TYPES)}")
    print(f"     Leave bal.  : {len(bal_rows)} records")
    print(f"     Leave req.  : {len(req_rows)} records")


if __name__ == "__main__":
    main()
