import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from mysql.connector import Error
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

# Initialize the FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get DB config from environment variables
DB_HOST = os.getenv("DB_HOST", "mariadb")
DB_PORT = os.getenv("DB_PORT", 3306)
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "rootpassword")
DB_NAME = os.getenv("DB_NAME", "app_db")

# Pydantic model to accept the float value
class FloatValue(BaseModel):
    value: float

# Function to connect to MariaDB with retries
def get_db_connection(retries=5, delay=5):
    attempt = 0
    while attempt < retries:
        try:
            connection = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            if connection.is_connected():
                return connection
        except Error as e:
            attempt += 1
            if attempt >= retries:
                raise HTTPException(status_code=500, detail=f"Database connection failed after {retries} attempts: {str(e)}")
            time.sleep(delay)  # Wait for a while before retrying
    raise HTTPException(status_code=500, detail="Database connection failed: Unknown error")

# Create the table if it doesn't exist
def create_table_if_not_exists():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS float_values (
            id INT AUTO_INCREMENT PRIMARY KEY,
            value FLOAT NOT NULL
        );
    """)
    connection.commit()
    cursor.close()
    connection.close()

# Call the function to create the table
create_table_if_not_exists()

# Define the POST endpoint to insert the float value into the database
@app.post("/insert-float/")
async def insert_float(float_value: FloatValue):
    print(f"inserting value {float_value}")
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("INSERT INTO float_values (value) VALUES (%s)", (float_value.value,))
        connection.commit()
        return {"message": "Value inserted successfully", "value": float_value.value}
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Error inserting value: {str(e)}")
    finally:
        cursor.close()
        connection.close()

from fastapi.responses import JSONResponse

@app.options("/insert-float/")
async def options_insert_float():
    return JSONResponse(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",  # Adjust if needed
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )

MONGO_URI = "mongodb://root:rootpassword@mongodb:27017/admin?authSource=admin&authMechanism=SCRAM-SHA-1"
MONGO_DB = "analytics"
MONGO_COLLECTION = "float_statistics"

# Function to get MongoDB connection
def get_mongo_connection():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db[MONGO_COLLECTION]
    return collection


# Endpoint to get the statistics from MongoDB
@app.get("/get-stats/")
async def get_stats():
    collection = get_mongo_connection()

    # Fetch the document that contains the statistics
    stats = collection.find_one({"type": "descriptive_statistics"})

    if not stats:
        raise HTTPException(status_code=404, detail="Statistics not found.")

    # Return the statistics
    return {
        "min": stats.get("min"),
        "max": stats.get("max"),
        "mean": stats.get("mean"),
        "median": stats.get("median")
    }

# To check if the service is running
@app.get("/")
def read_root():
    return {"message": "Database service is running"}
