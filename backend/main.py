from fastapi import FastAPI, File, UploadFile, HTTPException
import shutil
import os
import mysql.connector
from mysql.connector import errorcode
import csv
import re

# Database connection details
DB_HOST = "mariadb"  # Name of the MariaDB service in Docker
DB_USER = "root"
DB_PASSWORD = "rootpassword"  # Use the password you set for MariaDB
DB_NAME = "csv_data"  # Database name to be created

app = FastAPI()

UPLOAD_DIR = "data"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_location = f"data/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create database if not exists
    create_database_if_not_exists()

    # Create table from CSV and insert data
    try:
        create_table_from_csv(file_location)
        return {"message": f"File '{file.filename}' uploaded successfully", "path": file_location}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating table: {str(e)}")


def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

def create_database_if_not_exists():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn.commit()
        cursor.close()
        conn.close()


import re


def create_table_from_csv(csv_file_path):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()

        # Extract filename without extension and sanitize it
        table_name = os.path.splitext(os.path.basename(csv_file_path))[0]
        table_name = re.sub(r'\W+', '_', table_name).lower()  # Replace non-alphanumeric with underscores

        # Read the CSV to get column names and types
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            columns = reader.fieldnames
            if not columns:
                raise ValueError("CSV file is empty or has no headers.")

            # Generate a CREATE TABLE statement based on CSV columns
            column_defs = [f"`{col}` VARCHAR(255)" for col in columns]  # Enclose column names in backticks

            create_table_query = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(column_defs)})"
            cursor.execute(create_table_query)
            conn.commit()

            # Insert data into the table
            for row in reader:
                placeholders = ', '.join(['%s'] * len(row))
                insert_query = f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in columns])}) VALUES ({placeholders})"
                cursor.execute(insert_query, tuple(row.values()))

            conn.commit()
            cursor.close()
            conn.close()

        print(f"Table '{table_name}' created and data inserted successfully.")


