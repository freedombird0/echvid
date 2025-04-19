with open("routes/admin/ads.py", "rb") as f:
    content = f.read()

null_positions = [i for i, b in enumerate(content) if b == 0]

if null_positions:
    print("❌ Null bytes found at positions:", null_positions)
else:
    print("✅ No null bytes found.")
