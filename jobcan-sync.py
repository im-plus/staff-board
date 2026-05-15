"""
ジョブカン打刻 → スタッフボード自動連携スクリプト
Kintai.db の打刻データを監視し、Supabase のスタッフボードを自動更新する
"""

import sqlite3
import urllib.request
import json
import time
import logging
import os
import sys

# ===== 設定 =====

KINTAI_DB = r"C:\ProgramData\Donuts\JobcanKintai\Kintai.db"
# 2026-04-24: implus-internal (Free) の staff-board プロジェクトに移行
SUPABASE_URL = "https://ehitufdlbrrjpyivrfod.supabase.co"
SUPABASE_KEY = "sb_publishable_6wwEDm9e6BI4wIp3Qw2bQA_qRQHkLI_"
POLL_INTERVAL = 5  # 秒

# ジョブカンの打刻classとスタッフボードのステータス対応
CLASS_TO_STATUS = {
    1: "在社",      # 出勤
    2: "休み",      # 退勤
    3: "休憩",      # 休憩開始
    4: "在社",      # 休憩終了
}

# ジョブカンstaff_name(苗字) → スタッフボードのmember ID
# ジョブカンのstaff_idで紐づけ
STAFF_MAP = {
    7:  {"board_id": 2, "name": "武藤"},
    5:  {"board_id": 3, "name": "大場"},
    11: {"board_id": 4, "name": "相羽"},
    3:  {"board_id": 5, "name": "岡村"},
    4:  {"board_id": 6, "name": "太田"},
    12: {"board_id": 7, "name": "五藤"},
    13: {"board_id": 8, "name": "今井"},
    14: {"board_id": 9, "name": "加藤"},
}

# ===== ログ設定 =====

log_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "jobcan-sync.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ===== Supabase更新 =====

def update_supabase(board_id, status):
    """スタッフボードのステータスを更新"""
    url = f"{SUPABASE_URL}/rest/v1/members?id=eq.{board_id}"
    data = json.dumps({
        "status": status,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="PATCH", headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    })

    try:
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        log.error(f"Supabase更新失敗: {e}")
        return False

# ===== メイン監視ループ =====

def get_last_id(conn):
    """最新の打刻IDを取得"""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM adit_data")
    row = cursor.fetchone()
    return row[0] if row[0] else 0

def get_new_punches(conn, last_id):
    """前回以降の新しい打刻を取得"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, staff_id, staff_name, class, touch_time FROM adit_data WHERE id > ? ORDER BY id",
        (last_id,),
    )
    return cursor.fetchall()

def main():
    log.info("=== ジョブカン → スタッフボード連携 開始 ===")

    # 初期接続 & 最新IDを記録（起動時点の打刻は処理しない）
    conn = sqlite3.connect(f"file:{KINTAI_DB}?mode=ro", uri=True)
    last_id = get_last_id(conn)
    conn.close()
    log.info(f"監視開始 (最新打刻ID: {last_id})")

    while True:
        try:
            time.sleep(POLL_INTERVAL)

            conn = sqlite3.connect(f"file:{KINTAI_DB}?mode=ro", uri=True)
            punches = get_new_punches(conn, last_id)
            conn.close()

            for punch in punches:
                punch_id, staff_id, staff_name, punch_class, touch_time = punch
                staff_id = int(staff_id)

                if staff_id not in STAFF_MAP:
                    log.info(f"未登録スタッフ: {staff_name} (ID={staff_id}) - スキップ")
                    last_id = punch_id
                    continue

                staff = STAFF_MAP[staff_id]
                new_status = CLASS_TO_STATUS.get(punch_class)

                if not new_status:
                    log.warning(f"不明な打刻class: {punch_class}")
                    last_id = punch_id
                    continue

                log.info(f"打刻検知: {staff['name']} → {new_status} (class={punch_class}, time={touch_time})")

                if update_supabase(staff["board_id"], new_status):
                    log.info(f"  ✓ スタッフボード更新完了: {staff['name']} → {new_status}")
                else:
                    log.error(f"  ✗ スタッフボード更新失敗: {staff['name']}")

                last_id = punch_id

        except sqlite3.OperationalError as e:
            log.warning(f"DB読み取りエラー（ジョブカンが書き込み中の可能性）: {e}")
        except KeyboardInterrupt:
            log.info("=== 連携終了 ===")
            break
        except Exception as e:
            log.error(f"予期しないエラー: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
