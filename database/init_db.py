import sqlite3
import os

# Database path
db_path = "database/toy_inventory.db"
os.makedirs(os.path.dirname(db_path), exist_ok=True)  # Ensure the directory exists

# SQL commands to create tables
create_tables_sql = """
CREATE TABLE IF NOT EXISTS Categories (
    CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
    CategoryName TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Subcategories (
    SubcategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
    SubcategoryName TEXT NOT NULL,
    CategoryID INTEGER NOT NULL,
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID)
);

CREATE TABLE IF NOT EXISTS Types (
    TypeID INTEGER PRIMARY KEY AUTOINCREMENT,
    TypeName TEXT NOT NULL,
    SubcategoryID INTEGER NOT NULL,
    FOREIGN KEY (SubcategoryID) REFERENCES Subcategories(SubcategoryID)
);

CREATE TABLE IF NOT EXISTS Toys (
    ToyID INTEGER PRIMARY KEY AUTOINCREMENT,
    UniqueID TEXT NOT NULL UNIQUE,
    Year INTEGER,
    CategoryID INTEGER NOT NULL,
    SubcategoryID INTEGER NOT NULL,
    TypeID INTEGER NOT NULL,
    Subject TEXT,
    Manufacturers TEXT,
    Universe TEXT,
    CharacterAccessories TEXT,
    Material TEXT,
    Country TEXT,
    ItemCondition TEXT,
    IsComplete INTEGER DEFAULT 0,
    Box INTEGER DEFAULT 0,
    BoxCondition TEXT,
    Quantity INTEGER NOT NULL,
    Price REAL,
    Photo TEXT,
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID),
    FOREIGN KEY (SubcategoryID) REFERENCES Subcategories(SubcategoryID),
    FOREIGN KEY (TypeID) REFERENCES Types(TypeID)
);
"""

# Initialize database
def initialize_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(create_tables_sql)  # Execute all create statements
    conn.commit()
    conn.close()
    print(f"Database initialized successfully at {db_path}")

if __name__ == "__main__":
    initialize_database()
