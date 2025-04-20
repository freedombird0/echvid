# backend/database.py

import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext
import os

# مسار ملف القاعدة
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "users.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            DB_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """
    تنشئ الجداول إذا لم توجد أو تهاجر schema عند إضافات.
    - users: جدول المستخدمين مع plan, role, created_at
    - site_settings
    - ads
    """
    db = get_db()
    cursor = db.cursor()

    # إنشاء جدول المستخدمين الأساسي إذا لم يوجد
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    """)

    # التحقق من الأعمدة في users وترحيل إذا افتقدت
    cursor.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cursor.fetchall()]

    if 'plan' not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'free'")
    if 'role' not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    if 'created_at' not in cols:
        # إضافة العمود بدون default expression ثم تعيين القيم
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
        cursor.execute(
            "UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
        )

    # إنشاء جدول إعدادات الموقع
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    # إنشاء جدول الإعلانات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            image_url TEXT NOT NULL,
            link TEXT
        );
    """)

    # إدخال القيم الافتراضية في site_settings
    default_settings = {
        "siteName": "Echvid",
        "primaryColor": "#38bdf8",
        "seoTitle": "Echvid - Smart Media Tools",
        "seoDescription": "AI-powered tools for media processing",
        "maintenanceMode": "false"
    }
    for k, v in default_settings.items():
        cursor.execute(
            "INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?)",
            (k, v)
        )

    db.commit()

@click.command("init-db")
@with_appcontext
def init_db_command():
    """flask init-db"""
    init_db()
    click.echo("✅ Initialized the database and applied migrations.")

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
