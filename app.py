import os
import csv
import uuid
import sqlite3
from collections import defaultdict
from flask_wtf.csrf import CSRFProtect
from PIL import Image
import io
from rembg import remove
from flask_cors import CORS
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "e989b7d20a7dcbf8e60588d3214c07fbb32294ded4edff6b6c6c0e8fb66c8fc8"

# Initialize CSRF protection
csrf = CSRFProtect(app)



# Configure the upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Path to the categorization CSV file
CSV_PATH = r"C:\Users\Xpoly\Desktop\Toy_Effect\project\app\database\categorization.csv"

def update_db_schema():
    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()
    cursor.execute("""
    ALTER TABLE Toys ADD COLUMN UserID INTEGER
    """)
    conn.commit()
    conn.close()

# Uncomment and run once to update the database schema
# update_db_schema()

# Function to load categorization data from the CSV
def load_categorization_data(csv_path):
    data = defaultdict(lambda: defaultdict(list))  # {Category: {Sub-Category: [Types]}}
    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            category = row["Category"]
            sub_category = row["Sub-Category"]
            type_ = row["Type"]
            data[category][sub_category].append(type_)
    return data

# Function to ensure categories, subcategories, and types exist in the database
def update_categorization_in_db(categorization_data):
    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()

    for category, subcategories in categorization_data.items():
        # Insert or ignore the category
        cursor.execute("""
            INSERT OR IGNORE INTO Categories (CategoryName)
            VALUES (?)
        """, (category,))
        cursor.execute("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (category,))
        category_id = cursor.fetchone()[0]

        for sub_category, types in subcategories.items():
            # Insert or ignore the subcategory
            cursor.execute("""
                INSERT OR IGNORE INTO Subcategories (SubcategoryName, CategoryID)
                VALUES (?, ?)
            """, (sub_category, category_id))
            cursor.execute("""
                SELECT SubcategoryID FROM Subcategories
                WHERE SubcategoryName = ? AND CategoryID = ?
            """, (sub_category, category_id))
            subcategory_id = cursor.fetchone()[0]

            for type_ in types:
                # Insert or ignore the type
                cursor.execute("""
                    INSERT OR IGNORE INTO Types (TypeName, SubcategoryID)
                    VALUES (?, ?)
                """, (type_, subcategory_id))

    conn.commit()
    conn.close()

# Helper Function to Initialize Database
def init_db():
    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()

    # Create Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        UserID INTEGER PRIMARY KEY AUTOINCREMENT,
        Username TEXT NOT NULL UNIQUE,
        Email TEXT NOT NULL UNIQUE,
        Password TEXT NOT NULL,
        ProfilePicture TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# Signup Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password, method="sha256")

        try:
            with sqlite3.connect("database/toy_inventory.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Users (Username, Email, Password) 
                    VALUES (?, ?, ?)
                """, (username, email, hashed_password))
                conn.commit()
            return redirect(url_for("login"))
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return "An error occurred. Please try again later.", 500

    return render_template("signup.html")


# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Check credentials
        conn = sqlite3.connect("database/toy_inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE Email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            flash("Welcome back, " + user[1] + "!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password!", "danger")

    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("landing"))

# Profile Page
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE UserID = ?", (session["user_id"],))
    user = cursor.fetchone()
    conn.close()

    return render_template("profile.html", user=user)
# Restricted Index Page
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Fetch the username from the session
    username = session.get("username", "Guest")

    # Connect to the database
    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()

    # Fetch stats
    total_toys = cursor.execute("SELECT COUNT(*) FROM Toys WHERE UserID = ?", (session["user_id"],)).fetchone()[0]
    total_categories = cursor.execute("""
        SELECT COUNT(DISTINCT CategoryID) 
        FROM Toys 
        WHERE UserID = ?
    """, (session["user_id"],)).fetchone()[0]
    total_subcategories = cursor.execute("""
        SELECT COUNT(DISTINCT SubcategoryID) 
        FROM Toys 
        WHERE UserID = ?
    """, (session["user_id"],)).fetchone()[0]

    # Calculate the total value of the toy collection
    total_value = cursor.execute("""
        SELECT SUM(Price * Quantity) 
        FROM Toys 
        WHERE UserID = ?
    """, (session["user_id"],)).fetchone()[0] or 0  # Default to 0 if no toys

    conn.close()

    # Render index.html with stats
    return render_template(
        "index.html",
        username=username,
        total_toys=total_toys,
        total_categories=total_categories,
        total_subcategories=total_subcategories,
        total_value=total_value
    )


@app.route("/landing")
def landing():
    return render_template("landing.html")


# Categories Page
@app.route("/categories")
def categories():
    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Categories")
    categories = cursor.fetchall()
    conn.close()
    return render_template("categories.html", categories=categories)

# Subcategories Page
@app.route("/subcategories/<int:category_id>")
def subcategories(category_id):
    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Subcategories WHERE CategoryID = ?", (category_id,))
    subcategories = cursor.fetchall()
    conn.close()
    return render_template("subcategories.html", subcategories=subcategories)

# Types Page
@app.route("/types/<int:subcategory_id>")
def types(subcategory_id):
    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Types WHERE SubcategoryID = ?", (subcategory_id,))
    types = cursor.fetchall()
    conn.close()
    return render_template("types.html", types=types)

# Toys Page
@app.route("/toys", methods=["GET", "POST"])
def toys():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Toys")
    toys = cursor.fetchall() 

    # Pagination variables
    page = int(request.args.get("page", 1))
    per_page = 10  # Number of toys per page
    offset = (page - 1) * per_page

    # Filter parameters
    name_filter = request.args.get("name", "").strip()
    year_filter = request.args.get("year", "").strip()
    category_filter = request.args.get("category", "").strip()
    subcategory_filter = request.args.get("subcategory", "").strip()
    type_filter = request.args.get("type", "").strip()

    # Build the query dynamically
    query = """
        SELECT 
            Toys.ToyID, 
            Toys.Photo, 
            Toys.Subject, 
            Toys.Year, 
            Toys.CharacterAccessories, 
            Categories.CategoryName, 
            Subcategories.SubcategoryName, 
            Types.TypeName, 
            Toys.Quantity, 
            Toys.Price
        FROM Toys
        LEFT JOIN Categories ON Toys.CategoryID = Categories.CategoryID
        LEFT JOIN Subcategories ON Toys.SubcategoryID = Subcategories.SubcategoryID
        LEFT JOIN Types ON Toys.TypeID = Types.TypeID
        WHERE Toys.UserID = ? 
    """
    params = [session["user_id"]]

    # Add filters to the query
    if name_filter:
        query += " AND Toys.Subject LIKE ?"
        params.append(f"%{name_filter}%")
    if year_filter:
        query += " AND Toys.Year = ?"
        params.append(year_filter)
    if category_filter:
        query += " AND Categories.CategoryName LIKE ?"
        params.append(f"%{category_filter}%")
    if subcategory_filter:
        query += " AND Subcategories.SubcategoryName LIKE ?"
        params.append(f"%{subcategory_filter}%")
    if type_filter:
        query += " AND Types.TypeName LIKE ?"
        params.append(f"%{type_filter}%")

    # Add pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    cursor.execute(query, params)
    toys = cursor.fetchall()

    # Get total count for pagination
    count_query = """
        SELECT COUNT(*)
        FROM Toys
        LEFT JOIN Categories ON Toys.CategoryID = Categories.CategoryID
        LEFT JOIN Subcategories ON Toys.SubcategoryID = Subcategories.SubcategoryID
        LEFT JOIN Types ON Toys.TypeID = Types.TypeID
        WHERE Toys.UserID = ?
    """
    count_params = [session["user_id"]]

    if name_filter:
        count_query += " AND Toys.Subject LIKE ?"
        count_params.append(f"%{name_filter}%")
    if year_filter:
        count_query += " AND Toys.Year = ?"
        count_params.append(year_filter)
    if category_filter:
        count_query += " AND Categories.CategoryName LIKE ?"
        count_params.append(f"%{category_filter}%")
    if subcategory_filter:
        count_query += " AND Subcategories.SubcategoryName LIKE ?"
        count_params.append(f"%{subcategory_filter}%")
    if type_filter:
        count_query += " AND Types.TypeName LIKE ?"
        count_params.append(f"%{type_filter}%")

    cursor.execute(count_query, count_params)
    total_toys = cursor.fetchone()[0]
    total_pages = (total_toys + per_page - 1) // per_page

    # Fetch distinct values for filters
    cursor.execute("SELECT DISTINCT CategoryName FROM Categories")
    categories = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT SubcategoryName FROM Subcategories")
    subcategories = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT TypeName FROM Types")
    types = [row[0] for row in cursor.fetchall()]

    conn.close()

    return render_template(
        "toys.html",
        toys=toys,
        categories=categories,
        subcategories=subcategories,
        types=types,
        current_page=page,
        total_pages=total_pages,
    )
@app.route("/add-toy", methods=["GET", "POST"])
def add_toy():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()

    # Fetch categories, subcategories, and types
    cursor.execute("SELECT CategoryID, CategoryName FROM Categories")
    categories = cursor.fetchall()

    categorization_data = {}
    cursor.execute("""
        SELECT c.CategoryID, c.CategoryName, s.SubcategoryID, s.SubcategoryName, t.TypeID, t.TypeName
        FROM Categories c
        LEFT JOIN Subcategories s ON c.CategoryID = s.CategoryID
        LEFT JOIN Types t ON s.SubcategoryID = t.SubcategoryID
    """)
    for category_id, category_name, subcategory_id, subcategory_name, type_id, type_name in cursor.fetchall():
        if category_id not in categorization_data:
            categorization_data[category_id] = {"name": category_name, "subcategories": {}}
        if subcategory_id not in categorization_data[category_id]["subcategories"]:
            categorization_data[category_id]["subcategories"][subcategory_id] = {
                "name": subcategory_name,
                "types": []
            }
        if type_name not in [t["name"] for t in categorization_data[category_id]["subcategories"][subcategory_id]["types"]]:
            categorization_data[category_id]["subcategories"][subcategory_id]["types"].append({"id": type_id, "name": type_name})

    conn.close()

    if request.method == "POST":
        try:
            # Debug: Print form data
            print("Form Data:", request.form)

            # Get form data
            category = request.form.get("category")
            sub_category = request.form.get("subcategory")
            type_ = request.form.get("type")

            if not category or not sub_category or not type_:
                flash("Please select all fields: category, subcategory, and type.", "error")
                return redirect(request.url)

            # Handle file upload
            file = request.files.get("photo")
            photo_path = None
            processed_photo_path = None

            if file and file.filename != "":
                # Validate file type
                file_type = file.filename.split(".")[-1].lower()
                if file_type not in ["jpeg", "jpg", "png"]:
                    flash("Please upload a valid image file (JPEG or PNG).", "error")
                    return redirect(request.url)

                # Save original image
                filename = f"{uuid.uuid4().hex}_{file.filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                photo_path = os.path.join('static/uploads', filename)

                # Remove background using rembg
                try:
                    with open(filepath, "rb") as input_file:
                        input_image = input_file.read()
                        output_image = remove(input_image)
                        # Save processed image
                        processed_filename = f"processed_{filename}"
                        processed_filepath = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)
                        with open(processed_filepath, "wb") as output_file:
                            output_file.write(output_image)
                        processed_photo_path = os.path.join('static/uploads', processed_filename)
                except Exception as e:
                    print(f"Background removal failed: {e}")
                    flash("Failed to process the image background. Original image will be used.", "warning")

            # Save the processed path or original path to the database
            photo_path_to_save = processed_photo_path or photo_path

            # Additional form data
            unique_id = str(uuid.uuid4())
            year = request.form.get("year")
            subject = request.form.get("subject", "")
            manufacturers = request.form.get("manufacturers", "")
            universe = request.form.get("universe", "")
            character_accessories = request.form.get("character_accessories", "")
            material = request.form.get("material", "")
            country = request.form.get("country", "")
            item_condition = request.form.get("item_condition", "")
            is_complete = 1 if "is_complete" in request.form else 0
            box = 1 if "box" in request.form else 0
            box_condition = request.form.get("box_condition", "")
            quantity = request.form.get("quantity")
            price = request.form.get("price")
            user_id = session.get("user_id")

            # Insert toy into the database
            conn = sqlite3.connect("database/toy_inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Toys (
                    UniqueID, Year, CategoryID, SubcategoryID, TypeID, Subject, Manufacturers, Universe,
                    CharacterAccessories, Material, Country, ItemCondition, IsComplete, Box, BoxCondition,
                    Quantity, Price, Photo, UserID
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                unique_id, year, category, sub_category, type_, subject, manufacturers, universe,
                character_accessories, material, country, item_condition, is_complete, box, box_condition,
                quantity, price, photo_path_to_save, user_id
            ))
            conn.commit()
            flash("Toy added successfully! <a href='/add-toy'>Add another toy</a> or <a href='/toys'>View collection</a>.", "success")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            flash("An error occurred while saving your toy. Please try again.", "error")
        finally:
            conn.close()

        return redirect(request.url)

    return render_template(
        "add_toy.html",
        categories=categories,
        categorization_data=categorization_data
    )

@app.route("/edit-toy/<int:toy_id>", methods=["GET", "POST"])
def edit_toy(toy_id):
    if request.method == "POST":
        try:
            # Get updated data from the form
            name = request.form["name"]
            year = request.form["year"]
            character = request.form["character"]
            category = request.form["category"]
            subcategory = request.form["subcategory"]
            type_ = request.form["type"]
            quantity = request.form["quantity"]
            price = request.form["price"]
            
            # Handle photo update if provided
            photo = request.files["photo"]
            photo_path = None
            if photo and photo.filename != "":
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo_path = f"static/uploads/{filename}"

            # Update database
            conn = sqlite3.connect("database/toy_inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Toys
                SET Name = ?, Year = ?, Character = ?, Category = ?, Subcategory = ?, Type = ?, 
                    Quantity = ?, Price = ?, Photo = COALESCE(?, Photo)
                WHERE ToyID = ?
            """, (name, year, character, category, subcategory, type_, quantity, price, photo_path, toy_id))
            conn.commit()
            conn.close()

            flash("Toy updated successfully!", "success")
            return redirect(url_for("toys"))
        except Exception as e:
            flash(f"An error occurred: {e}", "danger")
            return redirect(url_for("edit_toy", toy_id=toy_id))

    # Fetch toy data for pre-populating the form
    conn = sqlite3.connect("database/toy_inventory.db")
    cursor = conn.cursor()
    toy = cursor.execute("SELECT * FROM Toys WHERE ToyID = ?", (toy_id,)).fetchone()
    conn.close()

    return render_template("edit_toy.html", toy=toy)

@app.route('/delete-toy/<int:toy_id>', methods=['POST'])
def delete_toy(toy_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    try:
        conn = sqlite3.connect("database/toy_inventory.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Toys WHERE ToyID = ?", (toy_id,))
        conn.commit()
        conn.close()

        flash("Toy deleted successfully!", "success")
    except sqlite3.Error as e:
        flash(f"An error occurred: {e}", "error")

    return redirect(url_for("toys"))



app.errorhandler(404)
def page_not_found(e):
    return f"URL not found: {request.path}", 404

if __name__ == "__main__":
    app.run(debug=True, port=8000)
