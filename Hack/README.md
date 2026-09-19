# Canteen Queue & Ordering System

A Flask-based smart queue and ordering system for campus canteens and cafeterias. It assigns automated queue tokens, provides real-time estimated waiting time calculations, and includes an admin dashboard for canteen staff to update live order status.

## 🚀 Features

- **User Authentication**: Student and Admin registration and login with encrypted passwords (`werkzeug.security`).
- **Food Menu**: Browsable food items with dynamic cart addition.
- **Cart & Checkout**: Multi-item cart with automated subtotal and total calculations.
- **Smart Queue & Token System**:
  - Auto-incrementing queue tokens upon checkout.
  - Live order tracking page with automatic 5-second polling refresh.
  - Dynamic waiting time estimation based on active orders ahead in the queue (3 mins/order).
- **Admin Dashboard**:
  - Live queue view with token numbers, customer summary, and total amount.
  - Instant order status updates: `Preparing`, `Ready`, and `Completed`.
- **Order History**: `My Orders` page for students to view previous orders and active tokens.

---

## 🛠️ Quick Start

### 1. Run with the batch file (Windows):
Double click `run.bat` or run:
```cmd
run.bat
```

### 2. Or run via PowerShell / Terminal:
```powershell
.\.venv\Scripts\python.exe app.py
```

Open your browser and navigate to: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔑 Default Credentials

- **Admin Account**:
  - **Username**: `admin`
  - **Password**: `admin123`
- Or check the **"Register as Admin"** box during registration to create your own admin account.

---

## 📁 Project Structure

- [app.py](file:///c:/Users/acer/Desktop/Hack/app.py): Complete Flask application, models, routing, and embedded HTML templates.
- [requirements.txt](file:///c:/Users/acer/Desktop/Hack/requirements.txt): Python package dependencies.
- [run.bat](file:///c:/Users/acer/Desktop/Hack/run.bat): One-click starter script.
- `instance/canteen.db`: SQLite database file (created automatically on startup).
