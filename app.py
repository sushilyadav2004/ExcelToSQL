from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import secrets
import pandas
import pyodbc
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import logging
logging.basicConfig(
   filename="logs/app.log",
   level=logging.INFO,
   format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32)
)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    if response.status_code >= 400:
        logger.error(
            "HTTP Error: %s %s - Status Code: %s",
            request.method,
            request.url.path,
            response.status_code
        )
    return response
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
pyodbc.pooling = False
connection = create_engine(
    "mssql+pyodbc:///?odbc_connect="
    "DRIVER%3D%7BODBC%20Driver%2018%20for%20SQL%20Server%7D%3B"
    "SERVER%3D.%5CSQLEXPRESS%3B"
    "DATABASE%3DStudentDB%3B"
    "Trusted_Connection%3Dyes%3B"
    "TrustServerCertificate%3Dyes%3B",
    poolclass=NullPool
)
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )
@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    try:
        with connection.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT Id, Username, Role
                    FROM Users
                    WHERE Username = :username
                    AND Password = :password
                """),
                {
                    "username": username,
                    "password": password
                }
            )
            user = result.mappings().first()
        if user is None:
            logger.error("Invalid login attempt: %s", username)
            return HTMLResponse(
                "Invalid username or password",
                status_code=401
            )
        request.session["user_id"] = user["Id"]
        request.session["username"] = user["Username"]
        request.session["role"] = user["Role"]
        logger.info(
            "User logged in successfully: %s",
            user["Username"]
        )
        return RedirectResponse(
            url="/students",
            status_code=303
        )
    except Exception as e:
        logger.error("Login error: %s", e)
        return HTMLResponse(
            f"Login error: {e}",
            status_code=500
        )
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        data = pandas.read_excel(file.file)
        data.to_sql(
            "Students",
            connection,
            if_exists="append",
            index=False)
        logger.info("file uploaded successfully:ID=%s",file.filename)
        return {"message": "Data inserted successfully"}
    except Exception as e:
        logger.error("error uploading file: %s",e)
        return {"error": str(e)}
    finally:
        logger.info("Upload process complete")

@app.get("/add", response_class=HTMLResponse)
def add_student_form():
    return Path("templates/add_student.html").read_text()
@app.post("/add")
async def add_student(
    id: int = Form(...),
    name: str = Form(...),
    course: str = Form(...)):
    try:
        with connection.begin() as conn:
         conn.execute(
            text("""INSERT INTO Students (ID, Name, Course) VALUES (:id, :name, :course)"""),
            {
                "id": id,
                "name": name,
                "course": course
            }
        )
        logger.info("student add successfully:ID=%s", id)
        return RedirectResponse(url="/students", status_code=303)
    except Exception as e:
        logger.error("error adding student: %s",e)
        return HTMLResponse(
           f"error adding student:{e}",
           status_code=500)
    finally:
        logger.info("add student complete")
@app.get("/students", response_class=HTMLResponse)
def get_students(request: Request):
    try:
        with connection.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT ID, Name, Course
                    FROM Students
                    ORDER BY ID
                """)
            )

            students = result.mappings().all()

        return templates.TemplateResponse(
            request=request,
            name="students.html",
            context={"students": students}
        )
    except Exception as e:
        logger.error("error getting student: %s", e)

        return HTMLResponse(
            f"error getting student: {e}",
            status_code=500
        )
    finally:
        logger.info("get student complete")
@app.get("/edit/{student_id}", response_class=HTMLResponse)
def edit_student_page(request: Request, student_id: int):
    try:
        with connection.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT ID, Name, Course
                    FROM Students
                    WHERE ID = :id
                """),
                {"id": student_id}
            )
            student = result.mappings().first()
        if student is None:
            return HTMLResponse(
                "Student not found",
                status_code=404
            )
        return templates.TemplateResponse(
            request=request,
            name="edit_student.html",
            context={"student": student}
        )
    except Exception as e:
        logger.error("error opening edit form: %s", e)
        return HTMLResponse(
            f"error opening edit form: {e}",
            status_code=500
        )
    finally:
        logger.info("edit form process complete")
@app.post("/edit/{student_id}")
async def edit_student(
    student_id: int,
    name: str = Form(...),
    course: str = Form(...)
):
    try:
        with connection.begin() as conn:
            conn.execute(
                text("""
                    UPDATE Students
                    SET Name = :name,
                        Course = :course
                    WHERE ID = :id
                """),
                {
                    "id": student_id,
                    "name": name,
                    "course": course
                }
            )
        logger.info(
            "Student updated successfully: ID=%s",
            student_id
        )
        return RedirectResponse(
            url="/students",
            status_code=303
        )
    except Exception as e:
        logger.error("error updating student: %s", e)
        return HTMLResponse(
            f"error updating student: {e}",
            status_code=500
        )
    finally:
        logger.info("edit student complete")
@app.get("/delete/{student_id}")
def delete_student(student_id: int):
    try:
        with connection.begin() as conn:
         conn.execute(
            text("""DELETE FROM Students 
            WHERE ID = :id"""),
            {"id": student_id}
        )
         logger.info(
            "Student deleted successfully: ID=%s", student_id)
        return RedirectResponse(url="/students", status_code=303)
    except Exception as e:
        logger.error("error deleting student: %s",e)
        return HTMLResponse(
          f"error deleting student {e}",
          status_code=500)
    finally:
        logger.info("student delete complete")