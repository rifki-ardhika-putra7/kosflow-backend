# Setup MySQL untuk KosFlow

## 1. Install MySQL Server

### Windows

Download dari: https://dev.mysql.com/downloads/mysql/
Atau pakai `chocolatey`: `choco install mysql`

### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install mysql-server
sudo mysql_secure_installation
```

### macOS

```bash
brew install mysql
mysql.server start
mysql_secure_installation
```

---

## 2. Buat User MySQL

Buka MySQL CLI:

```bash
mysql -u root -p
```

Buat user baru (recommended):

```sql
CREATE USER 'kosflow_user'@'localhost' IDENTIFIED BY 'kosflow_password';
GRANT ALL PRIVILEGES ON kosflow_db.* TO 'kosflow_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Atau pakai `root` (tidak recommended untuk production).

---

## 3. Update Konfigurasi di `app.py`

Buka `app.py` dan ubah `MYSQL_CONFIG`:

```python
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'kosflow_user',          # Ganti sesuai username
    'password': 'kosflow_password',  # Ganti sesuai password
    'database': 'kosflow_db',
    'raise_on_warnings': True
}
```

---

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 5. Jalankan Server

```bash
uvicorn app:app --reload
```

Server akan berjalan di: http://localhost:8000

---

## 6. Test API

### GET - Lihat semua pengeluaran

```bash
curl http://localhost:8000/api/expenses
```

### POST - Tambah pengeluaran

```bash
curl -X POST http://localhost:8000/api/expenses \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50000,
    "category": "food",
    "note": "Makan soto",
    "date": "2026-05-30"
  }'
```

### DELETE - Hapus pengeluaran

```bash
curl -X DELETE http://localhost:8000/api/expenses/abc123xyz
```

---

## Troubleshooting

### Error: "Access denied for user 'root'@'localhost'"

- Pastikan MySQL sudah running
- Cek password MySQL Anda

### Error: "Unknown database 'kosflow_db'"

- Database akan dibuat otomatis saat app.py dijalankan pertama kali

### Error: "Module not found mysql.connector"

- Jalankan: `pip install mysql-connector-python`

---

## Cek Database via MySQL CLI

```bash
mysql -u kosflow_user -p
USE kosflow_db;
SELECT * FROM expenses;
```
