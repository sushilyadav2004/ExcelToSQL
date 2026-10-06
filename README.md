# ExcelToSQL

A FastAPI student-management app that reads Excel workbooks and stores student
records in Microsoft SQL Server.

## Setup

1. Create a SQL Server database and configure the connection string in
   `app.py` for your local server.
2. Install the Python dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

3. Set `SESSION_SECRET` to a long, random value before starting the app. If it
   is not set, the app generates a random key when it starts; sessions will not
   survive a restart.
4. Start the app:

   ```powershell
   py -m uvicorn app:app --reload
   ```

The sample student workbooks, logs, and local virtual environment are excluded
from this repository. Provide your own workbook when using the Excel import.
