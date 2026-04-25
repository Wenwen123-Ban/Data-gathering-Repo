"""
LBAS Smart Launcher — Admin_page1.py
Double-click START_SERVER_LIB.bat or run this file directly.
"""
import os
import sys
import subprocess
import webbrowser
import time
import socket

HOST = "0.0.0.0"
PORT = 5000
BROWSER_URL = f"http://localhost:{PORT}/welcome"


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def run_cmd(args, label):
    """Run a manage.py command and SHOW output so errors are visible."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"[LBAS] {label}...")
    result = subprocess.run(
        args,
        cwd=base_dir,
        capture_output=False   # show ALL output in the console window
    )
    return result.returncode == 0


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    manage_py = os.path.join(base_dir, "manage.py")

    if not os.path.exists(manage_py):
        print("[LBAS] ERROR: manage.py not found.")
        input("Press Enter to exit...")
        sys.exit(1)

    os.chdir(base_dir)


    # Ensure Profile folder and default avatar exist
    profile_dir = os.path.join(base_dir, 'Profile')
    static_img_dir = os.path.join(base_dir, 'static', 'img')
    os.makedirs(profile_dir, exist_ok=True)
    os.makedirs(static_img_dir, exist_ok=True)
    # Copy default.png from static/img to Profile if missing or empty
    src_default = os.path.join(static_img_dir, 'default.png')
    dst_default = os.path.join(profile_dir, 'default.png')
    if not os.path.exists(dst_default) or os.path.getsize(dst_default) < 100:
        if os.path.exists(src_default) and os.path.getsize(src_default) > 100:
            import shutil
            shutil.copy2(src_default, dst_default)
            print("[LBAS] Restored Profile/default.png")

    # Step 1: Run migrations (VISIBLE output so you can see if MySQL is down)
    # Detect which database will be used
    try:
        import MySQLdb
        conn = MySQLdb.connect(host='127.0.0.1', port=3306, user='root', passwd='', db='lbas_db', connect_timeout=3)
        conn.close()
        print("[LBAS] Database: MySQL (lbas_db) ✓")
    except Exception:
        try:
            import pymysql as MySQLdb
            MySQLdb.install_as_MySQLdb()
            import MySQLdb as _my
            conn = _my.connect(host='127.0.0.1', port=3306, user='root', passwd='', db='lbas_db', connect_timeout=3)
            conn.close()
            print("[LBAS] Database: MySQL via pymysql (lbas_db) ✓")
        except Exception:
            print("[LBAS] Database: SQLite fallback (db.sqlite3) — MySQL unavailable")

    ok = run_cmd([sys.executable, "manage.py", "migrate", "--run-syncdb"], "Running migrations")
    if not ok:
        print("\n[LBAS] Migration had issues - trying safe recovery...")
        # Try fake-applying migrations that may already be in the DB
        run_cmd([sys.executable, "manage.py", "migrate", "--fake-initial", "--run-syncdb"], "Recovery migrate")
        ok2 = run_cmd([sys.executable, "manage.py", "migrate", "--run-syncdb"], "Re-running migrations")
        if not ok2:
            print("\n[LBAS] !! MIGRATION FAILED !!")
            print("[LBAS] Most likely cause: MySQL is not running.")
            print("[LBAS] FIX: Open XAMPP → click Start next to MySQL → then relaunch this.")
            input("\nPress Enter to exit...")
            sys.exit(1)

    # Step 2: Seed demo data if DB is empty (separate subprocess, safe)
    print("[LBAS] Checking demo data...")
    seed_result = subprocess.run(
        [sys.executable, "manage.py", "seed_demo"],
        cwd=base_dir,
        capture_output=False
    )
    if seed_result.returncode != 0:
        print("[LBAS] WARNING: seed_demo had an issue, but continuing...")

    # Step 3: Start the server
    print(f"\n[LBAS] Starting server on port {PORT}...")
    try:
        import waitress  # noqa: F401
        server_cmd = [
            sys.executable, "-c",
            f"import waitress; from lbas_project.wsgi import application; "
            f"waitress.serve(application, host='{HOST}', port={PORT}, threads=2)"
        ]
    except ImportError:
        server_cmd = [sys.executable, "manage.py", "runserver", f"{HOST}:{PORT}", "--noreload"]

    server_proc = subprocess.Popen(server_cmd, cwd=base_dir)

    print("[LBAS] Waiting for server...")
    for _ in range(30):
        time.sleep(0.5)
        if is_port_in_use(PORT):
            break

    if not is_port_in_use(PORT):
        print("[LBAS] ERROR: Server did not start on port 5000.")
        print("[LBAS] Check if another app is using port 5000, then retry.")
        input("Press Enter to exit...")
        sys.exit(1)

    print(f"[LBAS] Server ready. Opening: {BROWSER_URL}")
    print("[LBAS] Admin login: ID=admin  Password=admin")
    print("[LBAS] Close this window to stop the server.\n")
    webbrowser.open(BROWSER_URL)

    try:
        server_proc.wait()
    except KeyboardInterrupt:
        server_proc.terminate()
        print("[LBAS] Server stopped.")


if __name__ == "__main__":
    main()
