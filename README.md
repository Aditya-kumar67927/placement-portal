# APP DEV 1 PROJECT FOR PLACEMENT PROTAL APP

 A Placement Portal web application that allows Admin (Institute), Company, and students to interact with the system based on their roles.

 ## Stack
- **Backend:** Flask and Python
- **Database:** Flask-SQLAlchemy + SQLAlchemy (SQLite)
- **Auth:** Plain Flask session
- **Frontend:** Jinja2 + pure HTML/CSS

Create virtual environment using the below command in terminal
python -m venv .venv

Activate virtual environment
In Windows: CMD: .venv\Scripts\activate
Powershell: .venv\Scripts\Activate.ps1

In Linux/Mac:
source .venv/bin/activate

To run the app, first install the requirements.txt using
pip install -r requirements.txt

Set a Flask secret key before starting the app. In PowerShell:

```powershell
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
```

For deployments, configure `SECRET_KEY` as an environment variable and keep its value private and stable.

creates DB + seeds demo data
python init_db.py

Run app.py using
python app.py