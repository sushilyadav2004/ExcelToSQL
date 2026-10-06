import pandas
from sqlalchemy import create_engine
connection = create_engine("mssql+pyodbc:///?odbc_connect=DRIVER%3D%7BODBC%20Driver%2018%20for%20SQL%20Server%7D%3BSERVER%3Dlpc%3A.%5CSQLEXPRESS%3BDATABASE%3DStudentDB%3BTrusted_Connection%3Dyes%3BTrustServerCertificate%3Dyes")

student_data = pandas.read_excel("students.xlsx")
student_data.to_sql("Students", connection, if_exists="append", index=False)
print("Data inserted successfully into the Students table.")