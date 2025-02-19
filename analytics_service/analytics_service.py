import os
import mysql.connector
import time
from pymongo import MongoClient, errors
import numpy as np
from mysql.connector import Error

# MySQL configuration from environment variables
MYSQL_HOST = os.getenv("MYSQL_HOST", "mariadb")
MYSQL_DB = os.getenv("MYSQL_DB", "app_db")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "rootpassword")

# MongoDB configuration from environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:rootpassword@mongodb:27017/admin?authSource=admin&authMechanism=SCRAM-SHA-1")
MONGO_COLLECTION = "float_statistics"


# Function to connect to MySQL with retries
def get_mysql_connection(retries=5, delay=5):
    attempt = 0
    while attempt < retries:
        try:
            connection = mysql.connector.connect(
                host=MYSQL_HOST,
                database=MYSQL_DB,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD
            )
            if connection.is_connected():
                return connection
        except Error as e:
            attempt += 1
            print(f"MySQL connection attempt {attempt} failed: {str(e)}")
            if attempt >= retries:
                raise Exception(f"MySQL connection failed after {retries} attempts: {str(e)}")
            time.sleep(delay)  # Wait before retrying


def get_mongo_connection(retries=10, delay=10):
    attempt = 0
    while attempt < retries:
        try:
            client = MongoClient(MONGO_URI)
            client.admin.command('ping')  # Test the connection
            return client
        except errors.ServerSelectionTimeoutError as e:
            attempt += 1
            print(f"MongoDB connection attempt {attempt} failed: {str(e)}")
            if attempt >= retries:
                raise Exception(f"MongoDB connection failed after {retries} attempts: {str(e)}")
            time.sleep(delay)  # Wait before retrying (increased delay)


def get_mysql_data():
    """Fetch data from the MySQL database."""
    connection = get_mysql_connection()  # Ensure we get a valid connection
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT value FROM float_values")
        result = cursor.fetchall()  # Fetch all rows of the table
        return [row[0] for row in result]  # Return only the float values
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return []
    finally:
        if connection:
            connection.close()


def compute_statistics(values):
    """Compute descriptive statistics: min, max, mean, and median."""
    if not values:
        return {"min": None, "max": None, "mean": None, "median": None}

    stats = {
        "min": np.min(values),
        "max": np.max(values),
        "mean": np.mean(values),
        "median": np.median(values),
    }
    return stats


def insert_to_mongodb(stats):
    """Insert statistics into MongoDB."""
    client = get_mongo_connection()  # Ensure MongoDB connection is valid
    db = client['analytics']
    collection = db[MONGO_COLLECTION]

    # Replace the existing document with the type "descriptive_statistics", ensuring it's only one document
    collection.replace_one(
        {"type": "descriptive_statistics"},  # Find document by the type
        {"type": "descriptive_statistics", **stats},  # Replace it with the new stats, keeping the same type field
        upsert=True  # If no document exists, insert it; if one exists, replace it
    )


def main():
    while True:
        # Fetch data from MySQL
        values = get_mysql_data()
        if values:
            # Compute statistics
            stats = compute_statistics(values)

            # Insert stats into MongoDB (overwrite)
            insert_to_mongodb(stats)

        # Wait for 5 seconds before running again
        time.sleep(5)


if __name__ == "__main__":
    main()
