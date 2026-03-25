"""
Tạo mock SQLite database cho Banking domain.
Schema: customer, customer_account, transaction
Dữ liệu demo tháng 3/2026.
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "banking.db"

# ── Seed data ──────────────────────────────────────────────────────────────────

CUSTOMERS = [
    ("CIF001", "KH001", "Nguyễn Văn An",    "0901234001", "an.nguyen@email.com",   "ACTIVE"),
    ("CIF002", "KH002", "Trần Thị Bình",    "0901234002", "binh.tran@email.com",   "ACTIVE"),
    ("CIF003", "KH003", "Lê Hoàng Cường",   "0901234003", "cuong.le@email.com",    "ACTIVE"),
    ("CIF004", "KH004", "Phạm Thị Dung",    "0901234004", "dung.pham@email.com",   "ACTIVE"),
    ("CIF005", "KH005", "Hoàng Văn Em",     "0901234005", "em.hoang@email.com",    "ACTIVE"),
    ("CIF006", "KH006", "Vũ Thị Fương",     "0901234006", "fuong.vu@email.com",    "ACTIVE"),
    ("CIF007", "KH007", "Đặng Minh Giang",  "0901234007", "giang.dang@email.com",  "ACTIVE"),
    ("CIF008", "KH008", "Bùi Thị Hoa",      "0901234008", "hoa.bui@email.com",     "INACTIVE"),
]

# (account_no, customer_no, account_class, account_name, status)
ACCOUNTS = [
    ("1000100001", "KH001", "PAYMENT",  "TK thanh toán - Nguyễn Văn An",   "ACTIVE"),
    ("1000100002", "KH001", "SAVING",   "TK tiết kiệm - Nguyễn Văn An",    "ACTIVE"),
    ("1000200001", "KH002", "PAYMENT",  "TK thanh toán - Trần Thị Bình",   "ACTIVE"),
    ("1000200002", "KH002", "SAVING",   "TK tiết kiệm - Trần Thị Bình",    "ACTIVE"),
    ("1000300001", "KH003", "PAYMENT",  "TK thanh toán - Lê Hoàng Cường",  "ACTIVE"),
    ("1000400001", "KH004", "PAYMENT",  "TK thanh toán - Phạm Thị Dung",   "ACTIVE"),
    ("1000500001", "KH005", "PAYMENT",  "TK thanh toán - Hoàng Văn Em",    "ACTIVE"),
    ("1000600001", "KH006", "PAYMENT",  "TK thanh toán - Vũ Thị Fương",    "ACTIVE"),
    ("1000700001", "KH007", "PAYMENT",  "TK thanh toán - Đặng Minh Giang", "ACTIVE"),
    ("1000800001", "KH008", "PAYMENT",  "TK thanh toán - Bùi Thị Hoa",     "INACTIVE"),
    # External recipient accounts (other banks)
    ("9876543210", "EXT001", "PAYMENT", "Tài khoản ngoài - Ngân hàng A",   "ACTIVE"),
    ("9876543211", "EXT002", "PAYMENT", "Tài khoản ngoài - Ngân hàng B",   "ACTIVE"),
    ("9876543212", "EXT003", "PAYMENT", "Tài khoản ngoài - Ngân hàng C",   "ACTIVE"),
]

RECIPIENT_NAMES = [
    "Nguyễn Thị Xuân", "Trần Văn Hùng", "Lê Minh Khoa", "Phạm Thị Lan",
    "Hoàng Văn Nam", "Vũ Thị Oanh", "Đặng Văn Phú", "Bùi Thị Quỳnh",
    "Đỗ Văn Sơn", "Ngô Thị Tuyết",
]

CHANNELS = ["MOBILE_APP", "MOBILE_APP", "MOBILE_APP", "INTERNET_BANKING", "INTERNET_BANKING", "ATM", "COUNTER"]

CATEGORY_CODES = {
    "TRANSFER": ["TRANSFER_INTERNAL", "TRANSFER_INTERBANK", "REQUEST_TRANSFER"],
    "DEPOSIT":  ["TOPUP", "CASH_DEPOSIT"],
    "WITHDRAW": ["WITHDRAW", "CASH_WITHDRAW"],
    "SAVING":   ["SAVING_DEPOSIT", "SAVING_WITHDRAW"],
    "FX":       ["FOREIGN_CURRENCY_BUY", "FOREIGN_CURRENCY_SELL"],
    "BILL":     ["BILL_PAYMENT", "BILL_PAYMENT"],
}

TRANS_NAMES = {
    "TRANSFER": "Chuyển tiền",
    "DEPOSIT":  "Nạp tiền",
    "WITHDRAW": "Rút tiền",
    "SAVING":   "Tiết kiệm",
    "FX":       "Ngoại tệ",
    "BILL":     "Thanh toán hóa đơn",
}

STATUSES_WEIGHTED = ["SUCCESS"] * 8 + ["FAILED"] * 1 + ["PENDING"] * 1
CURRENCIES = ["VND"] * 9 + ["USD"]


def rand_amount(trans_type: str) -> int:
    if trans_type == "TRANSFER":
        return random.choice([
            random.randint(100_000, 5_000_000),
            random.randint(5_000_000, 50_000_000),
            random.randint(50_000_000, 500_000_000),
        ])
    elif trans_type in ("DEPOSIT", "WITHDRAW"):
        return random.randint(500_000, 20_000_000)
    elif trans_type == "SAVING":
        return random.randint(5_000_000, 200_000_000)
    elif trans_type == "FX":
        return random.randint(1_000_000, 100_000_000)
    else:
        return random.randint(50_000, 5_000_000)


def rand_time(day_offset_range: tuple) -> str:
    base = datetime(2026, 3, 1)
    d = base + timedelta(days=random.randint(*day_offset_range))
    h = random.randint(7, 22)
    m = random.randint(0, 59)
    s = random.randint(0, 59)
    return d.strftime(f"%Y-%m-%d {h:02d}:{m:02d}:{s:02d}")


def make_transactions(n: int = 200):
    txns = []
    source_accounts = [a[0] for a in ACCOUNTS if a[2] == "PAYMENT" and a[4] == "ACTIVE"]
    ext_accounts = [a[0] for a in ACCOUNTS if a[0].startswith("98")]

    for i in range(1, n + 1):
        trans_type = random.choices(
            ["TRANSFER", "DEPOSIT", "WITHDRAW", "SAVING", "FX", "BILL"],
            weights=[40, 15, 15, 15, 5, 10],
        )[0]

        cat_code = random.choice(CATEGORY_CODES[trans_type])
        from_acc = random.choice(source_accounts)
        # Determine customer_no from from_acc
        from_cust = next((a[1] for a in ACCOUNTS if a[0] == from_acc), "KH001")

        if trans_type == "TRANSFER":
            to_acc = random.choice(source_accounts + ext_accounts)
            while to_acc == from_acc:
                to_acc = random.choice(source_accounts + ext_accounts)
            to_fullname = random.choice(RECIPIENT_NAMES)
        elif trans_type == "DEPOSIT":
            to_acc = from_acc
            to_fullname = ""
        elif trans_type == "WITHDRAW":
            to_acc = ""
            to_fullname = ""
        else:
            to_acc = from_acc
            to_fullname = ""

        amount = rand_amount(trans_type)
        currency = random.choice(CURRENCIES)
        status = random.choice(STATUSES_WEIGHTED)
        channel = random.choice(CHANNELS)
        trans_time = rand_time((0, 23))

        txns.append((
            f"REF{i:06d}",                        # reference_id
            f"TXN{i:08d}",                         # trans_id
            cat_code,                               # trans_code / category_code
            trans_type,                             # trans_type
            channel,                                # channel_receiver / request_channel
            from_acc,                               # from_account_no
            to_acc,                                 # to_account_no
            to_fullname,                            # to_account_fullname
            amount,                                 # amount_transfer
            currency,                               # amount_currency
            status,                                 # trans_status
            TRANS_NAMES[trans_type],                # trans_name
            f"GD {TRANS_NAMES[trans_type]} {i}",   # trans_desc
            trans_time,                             # trans_time
            from_cust,                              # from_cust_no
        ))
    return txns


# ── Build DB ───────────────────────────────────────────────────────────────────

def create_db():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # customer
    cur.execute("""
        CREATE TABLE customer (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            cif_no        TEXT NOT NULL UNIQUE,
            customer_id   TEXT NOT NULL UNIQUE,
            customer_no   TEXT NOT NULL UNIQUE,
            customer_name TEXT NOT NULL,
            mobile_phone  TEXT,
            email         TEXT,
            status        TEXT DEFAULT 'ACTIVE'
        )
    """)

    # customer_account
    cur.execute("""
        CREATE TABLE customer_account (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            account_no    TEXT NOT NULL UNIQUE,
            customer_no   TEXT NOT NULL,
            account_class TEXT NOT NULL,
            account_name  TEXT,
            status        TEXT DEFAULT 'ACTIVE',
            create_date   TEXT DEFAULT '2024-01-01',
            FOREIGN KEY (customer_no) REFERENCES customer(customer_no)
        )
    """)

    # transaction
    cur.execute("""
        CREATE TABLE "transaction" (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_id        TEXT NOT NULL UNIQUE,
            trans_id            TEXT NOT NULL UNIQUE,
            trans_code          TEXT,
            category_code       TEXT,
            trans_type          TEXT,
            request_channel     TEXT,
            channel_receiver    TEXT,
            from_account_no     TEXT,
            from_cust_no        TEXT,
            to_account_no       TEXT,
            to_account_fullname TEXT,
            amount_transfer     INTEGER DEFAULT 0,
            amount_currency     TEXT DEFAULT 'VND',
            fee_amount          INTEGER DEFAULT 0,
            trans_status        TEXT DEFAULT 'SUCCESS',
            trans_name          TEXT,
            trans_desc          TEXT,
            trans_time          TEXT NOT NULL
        )
    """)

    # Insert customers
    for cif, cid, name, phone, email, status in CUSTOMERS:
        cno = cid.replace("KH", "CUST")
        cur.execute(
            "INSERT INTO customer (cif_no, customer_id, customer_no, customer_name, mobile_phone, email, status) VALUES (?,?,?,?,?,?,?)",
            (cif, cid, cno, name, phone, email, status),
        )

    # Insert accounts (update customer_no to CUST format)
    for acc_no, cust_raw, acc_class, acc_name, status in ACCOUNTS:
        cno = cust_raw.replace("KH", "CUST") if cust_raw.startswith("KH") else cust_raw
        cur.execute(
            "INSERT INTO customer_account (account_no, customer_no, account_class, account_name, status) VALUES (?,?,?,?,?)",
            (acc_no, cno, acc_class, acc_name, status),
        )

    # Insert transactions
    random.seed(42)
    txns = make_transactions(200)
    for t in txns:
        ref, tid, cat, ttype, ch, from_acc, to_acc, to_name, amt, cur2, status, tname, tdesc, ttime, from_cust = t
        cno = from_cust.replace("KH", "CUST")
        cur.execute("""
            INSERT INTO "transaction"
            (reference_id, trans_id, trans_code, category_code, trans_type,
             request_channel, channel_receiver, from_account_no, from_cust_no,
             to_account_no, to_account_fullname, amount_transfer, amount_currency,
             fee_amount, trans_status, trans_name, trans_desc, trans_time)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (ref, tid, cat, cat, ttype, ch, ch, from_acc, cno,
              to_acc, to_name, amt, cur2, random.randint(0, 11000),
              status, tname, tdesc, ttime))

    conn.commit()

    # Print summary
    print(f"Created: {DB_PATH}")
    for tbl in ("customer", "customer_account", '"transaction"'):
        count = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {count} rows")

    # Sample transaction
    row = cur.execute("""
        SELECT t.trans_id, t.trans_time, t.trans_type, t.from_account_no,
               t.to_account_no, t.amount_transfer, t.trans_status
        FROM "transaction" t ORDER BY t.trans_time DESC LIMIT 1
    """).fetchone()
    print(f"  Sample: {row}")

    conn.close()


if __name__ == "__main__":
    create_db()
