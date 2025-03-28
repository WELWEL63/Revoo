from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
import pandas as pd
from flask_mail import Mail, Message
from flask import Response
from werkzeug.utils import secure_filename
import os
import csv
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this to a strong secret key
app.config['UPLOAD_FOLDER'] = 'static/uploads/'  # Ensure this folder exists!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newsletters.db'  # SQLite DB for newsletters
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Allowed file extensions
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'mov', 'avi', 'mkv'}
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}


# Update your mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465  # For SSL, use 465. For TLS, use 587
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'redseaegypt24@gmail.com'  # Your Gmail address
app.config['MAIL_PASSWORD'] = 'nvpvmlraygcibnpt'  # Use the generated app password
app.config['MAIL_DEFAULT_SENDER'] = 'redseaegypt24@gmail.com'

mail = Mail(app)
####################################################################################################
# File paths
DATA_FILES = {
    "bookings": "bookings.csv",
    "reviews": "reviews.csv",
    "quotes": "quotes.csv",
    "contacts": "contact_us.csv",
    "trips": "egypttrips2.csv"
}
# Hardcoded admin credentials
ADMIN_CREDENTIALS = {
    "username": "admin",
    "password": "password123"  # Change this to a stronger password
}

# ✅ Redirect root URL to Login Page
@app.route('/')
def home():
    return redirect(url_for('login'))

# ✅ Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_CREDENTIALS["username"] and password == ADMIN_CREDENTIALS["password"]:
            session['admin_logged_in'] = True
            flash("Login successful!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid username or password. Try again!", "danger")

    return render_template('login.html')

@app.route('/dashboard')  # Changed from /admin to /dashboard
def admin_dashboard():
    if 'admin_logged_in' not in session:
        flash("Please log in to access the admin panel.", "warning")
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')


# ✅ Logout Route
@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))
##############################################################################################################

# Update & Mange trips
def load_data(file_key):
    """Load CSV data into a DataFrame with proper encoding handling."""
    try:
        # Check if the file exists
        if os.path.exists(DATA_FILES[file_key]):
            # Use 'ISO-8859-1' encoding to handle special characters in the file
            return pd.read_csv(DATA_FILES[file_key], encoding='ISO-8859-1', on_bad_lines='skip')  # Skip bad rows
        else:
            # Return an empty DataFrame if the file does not exist
            return pd.DataFrame()
    except Exception as e:
        # Log any errors that occur during file reading
        print(f"Error loading {file_key}.csv: {e}")
        return pd.DataFrame()  # Return an empty DataFrame if there's an error

def save_data(file_key, df):
    """Save DataFrame to CSV."""
    df.to_csv(DATA_FILES[file_key], index=False)

@app.route('/manage/<data_type>')
def manage_data(data_type):
    """View and manage data of a specific type (bookings, reviews, etc.)."""
    if data_type not in DATA_FILES:
        return "Invalid data type", 400
    df = load_data(data_type)
    return render_template(f'manage_{data_type}.html', data=df.to_dict(orient='records'))

@app.route('/edit/<data_type>/<int:index>', methods=['GET', 'POST'])
def edit_data(data_type, index):
    """Edit a specific record."""
    df = load_data(data_type)
    if request.method == 'POST':
        for key in df.columns:
            df.at[index, key] = request.form.get(key, df.at[index, key])
        save_data(data_type, df)
        return redirect(url_for('manage_data', data_type=data_type))
    return render_template('update_trip.html', data=df.iloc[index].to_dict(), data_type=data_type, index=index)

@app.route('/delete/<data_type>/<int:index>', methods=['POST'])
def delete_data(data_type, index):
    """Delete a specific record."""
    df = load_data(data_type)
    df.drop(index, inplace=True)
    df.reset_index(drop=True, inplace=True)
    save_data(data_type, df)
    return redirect(url_for('manage_data', data_type=data_type))

@app.route('/add_trip', methods=['GET', 'POST'])
def add_trip():
    """Add a new trip and save it to egypttrips.csv"""
    if request.method == 'POST':
        trip_data = {
            "Trip ID": request.form.get("trip_id"),
            "Destination": request.form.get("destination"),
            "Trip Name": request.form.get("trip_name"),
            "Description": request.form.get("description"),
            "Trip Category": request.form.get("trip_category"),
            "Duration": request.form.get("duration"),
            "Price Adult": request.form.get("price_adult"),
            "Price Child": request.form.get("price_child"),
            "Included in Price": request.form.get("included"),
            "Not Included": request.form.get("not_included"),
            "Start Date": request.form.get("start_date"),
            "End Date": request.form.get("end_date"),
            "Available Spots": request.form.get("available_spots"),
            "Tour Guide": request.form.get("tour_guide"),
            "Group Size": request.form.get("group_size"),
            "Meeting Point": request.form.get("meeting_point"),
            "Departure Time": request.form.get("departure_time"),
            "Return Time": request.form.get("return_time"),
            "Rating": request.form.get("rating"),
            "Reviews Count": request.form.get("reviews_count"),
            "Photo URL": request.form.get("photo_url"),
            "Contact Email": request.form.get("contact_email"),
            "Contact Phone": request.form.get("contact_phone"),
            "What to Bring": request.form.get("what_to_bring"),
            "Trip Difficulty": request.form.get("trip_difficulty"),
            "Languages Available": request.form.get("languages"),
            "Age Restrictions": request.form.get("age_restrictions"),
            "Transportation Type": request.form.get("transportation"),
            "Meals Included": request.form.get("meals_included"),
            "Cancellation Policy": request.form.get("cancellation_policy"),
            "Accessibility": request.form.get("accessibility"),
            "Special Offers": request.form.get("special_offers"),
            "Trip Schedule": request.form.get("trip_schedule")
        }

        # Load existing trips
        trips_df = load_data("trips")

        # Append new trip
        new_trip = pd.DataFrame([trip_data])
        trips_df = pd.concat([trips_df, new_trip], ignore_index=True)

        # Save back to CSV
        save_data("trips", trips_df)

        flash("New trip added successfully!", "success")
        return redirect(url_for("manage_data", data_type="trips"))

    return render_template("add_trip.html")

@app.route('/export_trips')
def export_trips():
    """Export all trips data as a CSV file."""
    df = load_data("trips")
    if df.empty:
        flash("No trips available to export.", "warning")
        return redirect(url_for('manage_data', data_type='trips'))

    # Convert the dataframe to CSV format
    csv = df.to_csv(index=False)

    # Create a response with the CSV content
    response = Response(csv, mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="all_trips.csv")
    return response

@app.route('/import_trips', methods=['GET', 'POST'])
def import_trips():
    """Import trips from a CSV file."""
    if request.method == 'POST':
        file = request.files['file']
        
        if not file:
            flash("No file selected", "danger")
            return redirect(url_for('import_trips'))

        try:
            # Read the CSV file into a DataFrame
            df_new = pd.read_csv(file)
            
            # Load existing trips data
            df_existing = load_data("trips")

            # Concatenate new data to existing trips
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)

            # Save back to the CSV file
            save_data("trips", df_combined)

            flash(f"Successfully imported {len(df_new)} trips.", "success")
            return redirect(url_for('manage_data', data_type='trips'))
        except Exception as e:
            flash(f"Error importing file: {str(e)}", "danger")
            return redirect(url_for('import_trips'))

    return render_template('import_trips.html')


#########################################################################################################################

# Load bookings data from CSV (Handles Errors & Ignores Missing Columns)
def load_bookings():
    try:
        df = pd.read_csv('bookings.csv', encoding='utf-8', on_bad_lines='skip')  # Skip bad rows
        for col in df.select_dtypes(include=['number']).columns:
            df[col] = df[col].fillna(0).astype(str)  # Convert NaN to '0' as a string to avoid JSON issues
        df.fillna('', inplace=True)  # Replace NaN with empty string for all other columns
        return df
    except Exception as e:
        print(f"Error loading bookings.csv: {e}")
        return pd.DataFrame()  # Return an empty DataFrame if there's an error

from datetime import datetime

@app.route('/manage/bookings')
def manage_bookings():
    df = load_bookings()

    if df.empty:
        return render_template('manage_bookings.html', grouped_bookings={}, trip_names=[])

    # Ensure "Trip Name" exists
    if 'Trip Name' not in df.columns:
        grouped_bookings = {'Unknown': df.to_dict(orient='records')}
        trip_names = ['Unknown']
    else:
        # Get today's date
        today = datetime.today().strftime('%Y-%m-%d')

        # Convert dataframe to dictionary and add booking date
        grouped_bookings = {}
        for trip_name, group in df.groupby('Trip Name'):
            bookings = group.to_dict(orient='records')

            # Add the "date_of_booking" field
            for booking in bookings:
                if "date_of_booking" in booking and booking["date_of_booking"]:
                    booking_date = booking["date_of_booking"]
                    # If booking was made today, show "Today"
                    if booking_date == today:
                        booking["date_of_booking"] = "Today"
                else:
                    booking["date_of_booking"] = "Unknown"

            grouped_bookings[trip_name] = bookings

        trip_names = list(grouped_bookings.keys())

    return render_template(
        'manage_bookings.html',
        grouped_bookings=grouped_bookings,  # Pass grouped bookings
        trip_names=trip_names  # Pass unique trip names for tabs
    )
#####################################################################################################################

REVIEWS_CSV = "reviews.csv"

# 📌 Load Reviews with Error Handling
def load_reviews():
    if not os.path.exists(REVIEWS_CSV):
        return pd.DataFrame(columns=["trip_id", "name", "rating", "comment", "email"])

    try:
        df = pd.read_csv(REVIEWS_CSV, encoding="utf-8", on_bad_lines="skip", dtype=str)
        df.fillna('', inplace=True)  # Replace NaN values with empty strings
        return df
    except Exception as e:
        print(f"Error loading reviews: {e}")
        return pd.DataFrame(columns=["trip_id", "name", "rating", "comment", "email"])

# 📌 Route: Manage Reviews (View All)
@app.route('/manage/reviews')
def manage_reviews():
    df = load_reviews()

    # ✅ Fix: Ensure all fields exist (including email)
    df.fillna("", inplace=True)  # Replace NaN values with empty strings

    # ✅ Convert entire DataFrame to a list of dictionaries (ALL reviews in one list)
    all_reviews = df.to_dict(orient='records')

    return render_template(
        'manage_reviews.html',
        all_reviews=all_reviews  # ✅ Pass all reviews in a single list
    )

# 📌 Route: Add Review
@app.route('/add/review', methods=['POST'])
def add_review():
    review_data = {
        "trip_id": request.form.get("trip_id"),
        "name": request.form.get("name"),
        "rating": request.form.get("rating"),
        "comment": request.form.get("comment"),
        "email": request.form.get("email"),
    }

    # Save review to CSV
    file_exists = os.path.isfile(REVIEWS_CSV)
    with open(REVIEWS_CSV, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["trip_id", "name", "rating", "comment", "email"])  # Write headers if file is new
        writer.writerow(review_data.values())

    return redirect(url_for("manage_reviews"))

# 📌 Route: Edit Review
@app.route('/edit/review/<int:review_index>', methods=['GET', 'POST'])
def edit_review(review_index):
    df = load_reviews()

    if review_index >= len(df):
        return "Review not found", 404  # Handle case where index is out of range

    if request.method == 'POST':
        df.at[review_index, "trip_id"] = request.form.get("trip_id")
        df.at[review_index, "name"] = request.form.get("name")
        df.at[review_index, "rating"] = request.form.get("rating")
        df.at[review_index, "comment"] = request.form.get("comment")
        df.at[review_index, "email"] = request.form.get("email")

        df.to_csv(REVIEWS_CSV, index=False)
        return redirect(url_for("manage_reviews"))

    review = df.iloc[review_index].to_dict()
    return render_template('edit_review.html', review=review, index=review_index)

# 📌 Route: Delete Review
@app.route('/delete/review/<int:review_index>', methods=['POST'])
def delete_review(review_index):
    df = load_reviews()

    if review_index >= len(df):
        return "Review not found", 404  # Handle case where index is out of range

    df = df.drop(index=review_index).reset_index(drop=True)
    df.to_csv(REVIEWS_CSV, index=False)

    return redirect(url_for("manage_reviews"))

###########################################################################################################################################

QUOTES_CSV = "quotes.csv"

# ✅ Load Quotes from CSV
def load_quotes():
    """Load quotes data from CSV, ensuring correct column alignment."""
    if not os.path.exists(QUOTES_CSV):
        return pd.DataFrame(columns=["quote_id", "name", "email", "phone", "trip", "dates", "date", "adults", "children", "stay", "special_requests", "details"])

    try:
        df = pd.read_csv(QUOTES_CSV, encoding="utf-8", dtype=str)  # Read all as strings to prevent errors
        df.fillna("", inplace=True)  # Replace NaN values with empty strings

        # Ensure correct column order
        expected_columns = ["quote_id", "name", "email", "phone", "trip", "dates", "date", "adults", "children", "stay", "special_requests", "details"]
        df = df.reindex(columns=expected_columns, fill_value="")  # Reorder and fill missing columns

        return df
    except Exception as e:
        print(f"Error loading quotes: {e}")
        return pd.DataFrame(columns=["quote_id", "name", "email", "phone", "trip", "dates", "date", "adults", "children", "stay", "special_requests", "details"])

# ✅ Route: Manage Quotes (View All)
@app.route('/manage/quotes')
def manage_quotes():
    df = load_quotes()
    quotes = df.to_dict(orient='records')  # Convert dataframe to a list of dictionaries
    return render_template('manage_quotes.html', quotes=quotes)

@app.route('/edit/quote/<int:quote_index>', methods=['GET', 'POST'])
def edit_quote(quote_index):
    df = load_quotes()

    if quote_index < 0 or quote_index >= len(df):
        return "Error: Quote not found", 404  

    if request.method == 'POST':
        df.at[quote_index, "quote_id"] = request.form.get("quote_id")
        df.at[quote_index, "name"] = request.form.get("name")
        df.at[quote_index, "email"] = request.form.get("email")
        df.at[quote_index, "phone"] = request.form.get("phone")
        df.at[quote_index, "trip"] = request.form.get("trip")
        df.at[quote_index, "dates"] = request.form.get("dates")
        df.at[quote_index, "date"] = request.form.get("date")
        df.at[quote_index, "adults"] = request.form.get("adults")
        df.at[quote_index, "children"] = request.form.get("children")
        df.at[quote_index, "stay"] = request.form.get("stay")
        df.at[quote_index, "special_requests"] = request.form.get("special_requests")
        df.at[quote_index, "details"] = request.form.get("details")
        df.at[quote_index, "price_per_adult"] = request.form.get("price_per_adult")
        df.at[quote_index, "price_per_child"] = request.form.get("price_per_child")
        df.at[quote_index, "total_price"] = request.form.get("total_price")
        df.at[quote_index, "discount"] = request.form.get("discount")

        df.to_csv(QUOTES_CSV, index=False)  # ✅ Save changes
        return redirect(url_for("manage_quotes"))

    quote = df.iloc[quote_index].to_dict()
    return render_template('edit_quote.html', quote=quote, index=quote_index)


def load_quotes():
    """Load quotes data from CSV, ensuring correct column alignment."""
    if not os.path.exists(QUOTES_CSV):
        return pd.DataFrame(columns=["name", "email", "phone", "trip", "dates", "date", "adults", "children", "stay", "special_requests", "details"])

    try:
        df = pd.read_csv(QUOTES_CSV, encoding="utf-8", dtype=str)  # Read all as strings
        df.fillna("", inplace=True)  # Replace NaN values with empty strings

        # Rename columns to remove spaces (matching what Flask expects)
        df.rename(columns={
            "Name": "name",
            "Email": "email",
            "Phone": "phone",
            "Trip": "trip",
            "Dates": "dates",
            "Date": "date",
            "Adults": "adults",
            "Children": "children",
            "Stay": "stay",
            "Special Requests": "special_requests",  # Fix space issue
            "Details": "details"
        }, inplace=True)

        expected_columns = ["name", "email", "phone", "trip", "dates", "date", "adults", "children", "stay", "special_requests", "details"]
        df = df.reindex(columns=expected_columns, fill_value="")  # Ensure correct order

        return df
    except Exception as e:
        print(f"Error loading quotes: {e}")
        return pd.DataFrame(columns=["name", "email", "phone", "trip", "dates", "date", "adults", "children", "stay", "special_requests", "details"])


# ✅ Route: Delete Quote
@app.route('/delete/quote/<int:quote_index>', methods=['POST'])
def delete_quote(quote_index):
    df = load_quotes()

    df = df.drop(index=quote_index).reset_index(drop=True)
    df.to_csv(QUOTES_CSV, index=False)

    return redirect(url_for("manage_quotes"))

###############################################################################################################################################

QUOTES_CSV = "quotes.csv"

def load_quotes():
    if not os.path.exists(QUOTES_CSV):
        return pd.DataFrame(columns=["quote_id", "name", "email", "phone", "trip", "dates", "date", "adults", "children", "stay", "special_requests", "details", "price_per_adult", "price_per_child", "total_price", "discount", "payment_method"])
    try:
        df = pd.read_csv(QUOTES_CSV, encoding="utf-8", dtype=str)
        df.fillna("", inplace=True)
        return df
    except Exception as e:
        print(f"Error loading quotes: {e}")
        return pd.DataFrame(columns=["quote_id", "name", "email", "phone", "trip", "dates", "date", "adults", "children", "stay", "special_requests", "details", "price_per_adult", "price_per_child", "total_price", "discount", "payment_method"])

@app.route("/send_quote_email/<quote_index>", methods=["GET", "POST"])
def send_quote_email(quote_index):
    if request.method == "POST":
        # Attempt to convert quote_index to an integer
        try:
            quote_index = int(quote_index)
        except ValueError:
            flash("Invalid quote index format. Please provide an integer.", "error")
            return redirect(url_for('edit_quote'))

        # Load your quotes data
        df = load_quotes()
        if quote_index < 0 or quote_index >= len(df):
            flash("Quote not found.", "error")
            return redirect(url_for('manage_quotes'))

        quote = df.iloc[quote_index].to_dict()
        recipient_email = quote.get("email", "")

        # Attempt to parse price fields
        try:
            adult_price = float(quote.get("price_per_adult", "0"))
            child_price = float(quote.get("price_per_child", "0"))
            discount = float(quote.get("discount", "0"))
            total_price = float(quote.get("total_price", "0")) - discount
        except ValueError as e:
            flash(f"Invalid price format: {e}", "error")
            return redirect(url_for('manage_quotes'))

        # Compose the email content
        subject = f"Your Quote Request for {quote.get('trip', 'N/A')}"
        body = f"""
        <html>
        <body>
            <h2>Hello {quote.get('name', 'Valued Customer')},</h2>
            <p>Thank you for your quote request. Below are the details:</p>
            <table>
                <tr><td><strong>Trip:</strong></td><td>{quote.get('trip', 'N/A')}</td></tr>
                <tr><td><strong>Dates:</strong></td><td>{quote.get('dates', 'N/A')}</td></tr>
                <tr><td><strong>Adults:</strong></td><td>{quote.get('adults', '0')}</td></tr>
                <tr><td><strong>Children:</strong></td><td>{quote.get('children', '0')}</td></tr>
                <tr><td><strong>Price per Adult:</strong></td><td>{adult_price}</td></tr>
                <tr><td><strong>Price per Child:</strong></td><td>{child_price}</td></tr>
                <tr><td><strong>Discount:</strong></td><td>{discount}</td></tr>
                <tr><td><strong>Total Price (After Discount):</strong></td><td>{total_price}</td></tr>
                <tr><td><strong>Payment Method:</strong></td><td>{quote.get('payment_method', 'N/A')}</td></tr>
            </table>
            <p>Best regards,<br>Excursion Team</p>
        </body>
        </html>
        """

        # Send the email (ensure you have configured your mail settings)
        msg = Message(subject, sender="your-email@gmail.com", recipients=[recipient_email])
        msg.html = body
        mail.send(msg)

        # Flash a success message
        flash("Email sent successfully!", "success")
        return redirect(url_for('manage_quotes'))

    # Render the template with any flashed messages
    return render_template("manage_quotes")

###########################################################################################################################


CONTACTS_CSV = "contact_us.csv"

# ✅ Load Contacts from CSV
def load_contacts():
    """Load contacts from CSV with proper column alignment."""
    if not os.path.exists(CONTACTS_CSV):
        return pd.DataFrame(columns=["Name", "Phone", "Email", "Message"])

    try:
        df = pd.read_csv(CONTACTS_CSV, encoding="utf-8", dtype=str)
        df.fillna("", inplace=True)  # Replace NaN values with empty strings
        return df
    except Exception as e:
        print(f"Error loading contacts: {e}")
        return pd.DataFrame(columns=["Name", "Phone", "Email", "Message"])
    

# ✅ Route: Manage Contacts (View All)
@app.route('/manage/contacts')
def manage_contacts():
    df = load_contacts()
    contacts = df.to_dict(orient='records')
    return render_template('manage_contacts.html', contacts=contacts)

# ✅ Route: Add Contact
@app.route('/add/contact', methods=['POST'])
def add_contact():
    contact_data = {
        "Name": request.form.get("name"),
        "Phone": request.form.get("phone"),
        "Email": request.form.get("email"),
        "Message": request.form.get("message"),
    }

    file_exists = os.path.isfile(CONTACTS_CSV)
    with open(CONTACTS_CSV, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Name", "Phone", "Email", "Message"])  # Write headers if file is new
        writer.writerow(contact_data.values())

    return redirect(url_for("manage_contacts"))

# ✅ Route: Edit Contact
@app.route('/edit/contact/<int:contact_index>', methods=['GET', 'POST'])
def edit_contact(contact_index):
    df = load_contacts()

    if contact_index < 0 or contact_index >= len(df):
        return "Error: Contact not found", 404

    if request.method == 'POST':
        df.at[contact_index, "Name"] = request.form.get("name")
        df.at[contact_index, "Phone"] = request.form.get("phone")
        df.at[contact_index, "Email"] = request.form.get("email")
        df.at[contact_index, "Message"] = request.form.get("message")

        df.to_csv(CONTACTS_CSV, index=False)
        return redirect(url_for("manage_contacts"))

    contact = df.iloc[contact_index].to_dict()
    return render_template('edit_contact.html', contact=contact, index=contact_index)

# ✅ Route: Delete Contact
@app.route('/delete/contact/<int:contact_index>', methods=['POST'])
def delete_contact(contact_index):
    df = load_contacts()

    df = df.drop(index=contact_index).reset_index(drop=True)
    df.to_csv(CONTACTS_CSV, index=False)

    return redirect(url_for("manage_contacts"))

####################################################################################################################################

# ✅ Route: for Reports
@app.route('/report/bookings', methods=['GET', 'POST'])
def report_bookings():
    df = load_bookings()

    if df.empty:
        return render_template('booking_report.html', report_data=[], total_sales=0, destinations=[], trips=[])

    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    selected_destination = request.form.get("destination", "All")
    selected_trip = request.form.get("trip_name", "All")

    # Convert dates
    df["date_of_booking"] = pd.to_datetime(df["date_of_booking"], errors='coerce')

    if not start_date or not end_date:
        return render_template('booking_report.html', report_data=[], total_sales=0, destinations=[], trips=[])

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Filter by date range
    filtered_df = df[(df["date_of_booking"] >= start_date) & (df["date_of_booking"] <= end_date)]

    # Get unique destinations and trips for the dropdown
    destinations = df["destination"].dropna().unique().tolist()
    trips = df["trip_name"].dropna().unique().tolist()

    # Apply destination filter if not "All"
    if selected_destination != "All":
        filtered_df = filtered_df[filtered_df["destination"] == selected_destination]

    # Apply trip name filter if not "All"
    if selected_trip != "All":
        filtered_df = filtered_df[filtered_df["trip_name"] == selected_trip]

    if filtered_df.empty:
        return render_template('booking_report.html', report_data=[], total_sales=0, destinations=destinations, trips=trips)

    # Generate report data
    report_data = []
    total_sales = 0

    for _, row in filtered_df.iterrows():
        total_price = float(row["total_price"])

        report_data.append({
            "booking_reference": row["booking_reference"],
            "booking_date": row["date_of_booking"].strftime('%Y-%m-%d'),
            "trip_name": row["trip_name"],
            "destination": row["destination"],
            "stay_location": row.get("stay_location", "N/A"),
            "pickup_time": row["departure_time"],
            "trip_date": row.get("selected_date", "N/A"),
            "alt_date": row.get("alternative_date", "N/A"),
            "customer_name": row["customer_name"],
            "phone": row["phone"],
            "email": row["email"],
            "adults": int(row["adults"]),
            "children": int(row["children"]),
            "price_adult": float(row["price_adult"]),
            "price_child": float(row["price_child"]),
            "total_price": total_price,
            "payment_method": row["payment_method"]
        })

        total_sales += total_price

    return render_template('booking_report.html', report_data=report_data, total_sales=total_sales,
                           destinations=destinations, trips=trips, 
                           selected_destination=selected_destination, selected_trip=selected_trip)

########################################################################################################################################

# Flask-Mail Configuration for Gmail (Change this based on your email service)
#app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Your SMTP server
#app.config['MAIL_PORT'] = 587
#app.config['MAIL_USE_TLS'] = True
#app.config['MAIL_USERNAME'] = 'your_email@gmail.com'  # Your email address
#app.config['MAIL_PASSWORD'] = 'your_email_password'  # Your email password (or app password if using 2FA)
#app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'  # Your email address
#app.secret_key = 'your_secret_key'  # Secret key for flash messages

#mail = Mail(app)
# Check if the file has an allowed extension
# Check if the file has an allowed extension
# Newsletter model
class Newsletter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    header = db.Column(db.String(100), nullable=True)  # Path for header image
    image = db.Column(db.String(100), nullable=True)  # Path for image
    video = db.Column(db.String(100), nullable=True)  # Path for video
    footer = db.Column(db.String(255), nullable=True)  # Footer text

    def __repr__(self):
        return f'<Newsletter {self.title}>'

# Create the database tables
with app.app_context():
    db.create_all()

# Check if the file has an allowed extension
def allowed_file(filename, file_type):
    if file_type == 'image':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_IMAGE_EXTENSIONS']
    if file_type == 'video':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_VIDEO_EXTENSIONS']
    return False

# Route for creating and previewing the newsletter
# Route for creating and previewing the newsletter
@app.route('/newsletter', methods=['GET', 'POST'])
def newsletter():
    preview_data = None
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        header_image = request.files.get('header')  # Header image
        footer_text = request.form.get('footer')  # Footer text
        image = request.files.get('image')  # Image
        video = request.files.get('video')  # Video

        # Check if the required fields are filled
        if not title or not content:
            flash("Title and Content are required!", "danger")
            return redirect(url_for('newsletter'))

        # Prepare preview data to be shown below the form
        preview_data = {
            'title': title,
            'content': content,
            'header': header_image.filename if header_image else None,
            'image': image.filename if image else None,
            'video': video.filename if video else None,
            'footer': footer_text
        }

        # Handle the file saving and allow for the preview
        if header_image and allowed_file(header_image.filename, 'image'):
            header_filename = secure_filename(header_image.filename)
            header_image.save(os.path.join(app.config['UPLOAD_FOLDER'], header_filename))

        if image and allowed_file(image.filename, 'image'):
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        if video and allowed_file(video.filename, 'video'):
            video_filename = secure_filename(video.filename)
            video.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))

        # Render the preview in the same page
        return render_template('newsletter.html', preview_data=preview_data)

    return render_template('newsletter.html', preview_data=preview_data)

# Route to save the newsletter
@app.route('/save_newsletter', methods=['POST'])
def save_newsletter():
    # Here we would save the newsletter to a database or file
    # For now, let's just simulate saving by flashing a success message
    flash("Newsletter created and saved successfully!", "success")
    return redirect(url_for('newsletter'))

# Helper function to check allowed file extensions
def allowed_file(filename, file_type):
    if file_type == 'image':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_IMAGE_EXTENSIONS']
    if file_type == 'video':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_VIDEO_EXTENSIONS']
    return False




if __name__ == "__main__":
   app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))  # Use port from Render







