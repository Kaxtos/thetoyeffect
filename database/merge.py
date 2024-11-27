import sqlite3
import csv
import os

# File paths
db_path = r"C:\Users\Xpoly\Desktop\Toy_Effect\project\app\database\toy_inventory.db"
csv_path = r"C:\Users\Xpoly\Desktop\Toy_Effect\project\app\static\images\space_toy_images\toy_data.csv"
image_folder = "/static/images/space_toy_images/"

# Connect to the database with a timeout
conn = sqlite3.connect(db_path, timeout=10)  # Wait for the lock to clear
cursor = conn.cursor()

# Enable Write-Ahead Logging (WAL) mode
cursor.execute("PRAGMA journal_mode=WAL;")

# Function to check if category exists, and insert if not
def get_or_create_category(category_name):
    cursor.execute("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (category_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    # Insert the new category and return its ID
    cursor.execute("INSERT INTO Categories (CategoryName) VALUES (?)", (category_name,))
    conn.commit()
    return cursor.lastrowid

# Function to check if subcategory exists, and insert if not
def get_or_create_subcategory(subcategory_name, category_id):
    cursor.execute("""
        SELECT SubcategoryID 
        FROM Subcategories 
        WHERE SubcategoryName = ? AND CategoryID = ?
    """, (subcategory_name, category_id))
    result = cursor.fetchone()
    if result:
        return result[0]
    # Insert the new subcategory and return its ID
    cursor.execute("""
        INSERT INTO Subcategories (SubcategoryName, CategoryID) 
        VALUES (?, ?)
    """, (subcategory_name, category_id))
    conn.commit()
    return cursor.lastrowid

# Function to check if type exists, and insert if not
def get_or_create_type(type_name, subcategory_id):
    cursor.execute("""
        SELECT TypeID 
        FROM Types 
        WHERE TypeName = ? AND SubcategoryID = ?
    """, (type_name, subcategory_id))
    result = cursor.fetchone()
    if result:
        return result[0]
    # Insert the new type and return its ID
    cursor.execute("""
        INSERT INTO Types (TypeName, SubcategoryID) 
        VALUES (?, ?)
    """, (type_name, subcategory_id))
    conn.commit()
    return cursor.lastrowid

try:
    # Read CSV and process each row
    with open(csv_path, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            toy_id = int(row["ToyID"])
            unique_id = row["UniqueID"]
            year = row["Year"]
            category_name = row["Category"]
            subcategory_name = "Default Subcategory"  # Use a default subcategory if not provided
            type_name = "Default Type"  # Use a default type if not provided
            universe = row["Universe"]
            manufacturers = row["Manufacturers"]
            subject = row["Subject"]
            photo = os.path.join(image_folder, row["Photo"])

            # Get or create category ID
            category_id = get_or_create_category(category_name)

            # Get or create subcategory ID
            subcategory_id = get_or_create_subcategory(subcategory_name, category_id)

            # Get or create type ID
            type_id = get_or_create_type(type_name, subcategory_id)

            # Insert or update toy data
            cursor.execute("""
                INSERT INTO Toys (ToyID, UniqueID, Year, CategoryID, SubcategoryID, TypeID, Universe, Manufacturers, Subject, Photo, IsComplete, Quantity, BoxCondition)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, 'Unknown')
                ON CONFLICT(ToyID) DO UPDATE SET
                    UniqueID = excluded.UniqueID,
                    Year = excluded.Year,
                    CategoryID = excluded.CategoryID,
                    SubcategoryID = excluded.SubcategoryID,
                    TypeID = excluded.TypeID,
                    Universe = excluded.Universe,
                    Manufacturers = excluded.Manufacturers,
                    Subject = excluded.Subject,
                    Photo = excluded.Photo
            """, (toy_id, unique_id, year, category_id, subcategory_id, type_id, universe, manufacturers, subject, photo))

    conn.commit()
    print("Data successfully merged into the database!")

finally:
    conn.close()
