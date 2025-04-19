import sqlite3

db_path = "users.db"  # تأكد من المسار الصحيح لملف قاعدة البيانات
email = "younesmahdi797@gmail.com"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("UPDATE users SET role = 'admin' WHERE email = ?", (email,))
conn.commit()

print("✅ Role updated to admin for:", email)
conn.close()
