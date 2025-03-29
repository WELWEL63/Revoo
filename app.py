from flask import Flask, render_template, request, session, redirect, url_for  
import csv
import pandas as pd
import os
import random
from datetime import datetime  # ✅ Ensure datetime is imported
import time
import uuid
from flask_babel import Babel, _
##################################################################################################################
app = Flask(__name__, template_folder="templates")
app.secret_key = 'your_secret_key_here'
app.config['LANGUAGES'] = ['en', 'ar', 'de', 'pl', 'ru', 'fr', 'es', 'cs', 'zh-CN']  # Define available languages

# Initialize Babel
babel = Babel(app)

# ✅ Define locale selector function
def get_locale():
    return session.get('language', request.accept_languages.best_match(app.config['LANGUAGES']))

# Set the locale selector for Babel
babel.init_app(app, locale_selector=get_locale)

@app.context_processor  # ✅ This ensures _() works inside Jinja
def inject_translations():
    return {'_': _}  

@app.route('/set_language/<lang>')
def set_language(lang):
    """Change user language and store it in session."""
    if lang in app.config['LANGUAGES']:
        session['language'] = lang
    return redirect(request.referrer or url_for('home'))
#########################################################################################################################
# Load CSV dynamically based on language
def get_csv_file():
    lang = session.get('language', 'en')  # Default to English if no language set
    csv_files = {
        'pl': "egypttrips_polish2.csv",
        'de': "egypttrips_german2.csv",
        'ru': "egypttrips_russian2.csv",
        'ar': "egypttrips_arabic2.csv",
        ##'fr': "egypttrips_french.csv",
        ##'es': "egypttrips_spanish.csv",
        ##'cs': "egypttrips_czech.csv",
        ##'zh-CN': "egypttrips_chinese.csv",
        'en': "egypttrips55.csv"  # Default English CSV
    }
    return csv_files.get(lang, "egypttrips2.csv")
########################################################################################################################
@app.after_request
def set_response_encoding(response):
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response


translations_dir = "translations"
languages = ["ar", "de", "en"]  # Add more if needed

for lang in languages:
    po_file = f"{translations_dir}/{lang}/LC_MESSAGES/messages.po"
    if os.path.exists(po_file):
        with open(po_file, "r", encoding="utf-8") as file:
            lines = file.readlines()

        with open(po_file, "w", encoding="utf-8") as file:
            for line in lines:
                if "POT-Creation-Date" in line:
                    file.write('"POT-Creation-Date: 2025-03-21 12:00+0000\\n"\n')
                else:
                    file.write(line)

print("✅ All .po files fixed! Now run: pybabel compile -d translations")

##########################################################################################################################
@app.route('/')
def home():
    """Render homepage with search and destination tabs."""
    try:
        df = pd.read_csv(get_csv_file(), encoding='utf-8')  # ✅ Use UTF-8 encoding
        df['short_description'] = df['Description'].apply(
            lambda x: x[:70] + '...' if isinstance(x, str) and len(x) > 70 else x
        )

        unique_destinations = sorted(df["Destination"].unique().tolist())
        grouped_trips = {destination: trips.sample(min(6, len(trips))).to_dict(orient="records")
                         for destination, trips in df.groupby("Destination")}

        sorted_destinations = sorted(grouped_trips.keys(), key=lambda d: (d != "Hurghada", d == "Cairo", d))
        grouped_trips = {destination: grouped_trips[destination] for destination in sorted_destinations}

        featured_trips = df.sample(3).to_dict(orient="records") if not df.empty else []

        return render_template("search.html", destinations=sorted_destinations, featured_trips=featured_trips, grouped_trips=grouped_trips)
    except Exception as e:
        return f"Error loading homepage: {str(e)}", 500

############################################################################################################### 
@app.route("/result", methods=["POST"])
def search_results():
    """Process search requests and display results in result.html."""
    try:
        df = pd.read_csv(get_csv_file(), encoding='utf-8')  # ✅ Correct encoding

        destination = request.form.get("destination")
        date = request.form.get("date")
        alt_day = request.form.get("alt_day")
        adults = int(request.form.get("adults", 1))
        children = int(request.form.get("children", 0))

        session['search_params'] = {'adults': adults, 'children': children, 'date': date, 'alt_day': alt_day}
        
        filtered_trips = df[df["Destination"] == destination].copy()
        
        for index, row in filtered_trips.iterrows():
            adult_price = int(row.get("Price Adult", 0))
            child_price = int(row.get("Price Child", 0))
            total_price = (adults * adult_price) + (children * child_price)
            filtered_trips.at[index, "Total Price"] = round(total_price, 2)
            filtered_trips.at[index, "Rating"] = row.get("Rating", "N/A")

        trips = filtered_trips.to_dict(orient="records")
        
        return render_template("result.html", trips=trips, destination=destination, date=date, alt_day=alt_day, adults=adults, children=children)
    except Exception as e:
        return f"Error processing search results: {str(e)}", 500

####################################################################################################### 
@app.route("/view/<trip_id>")
def view_trip(trip_id):
    """Load trip details dynamically from the correct CSV based on the selected language and display reviews properly."""
    try:
        # ✅ Load the correct CSV file based on language selection
        df = pd.read_csv(get_csv_file(), encoding='utf-8')  # ✅ Force UTF-8

        # ✅ Find the trip by its Trip ID
        trip = df[df["Trip ID"].astype(str) == str(trip_id)]
        if trip.empty:
            return "Trip not found!", 404  # ✅ Handle case where trip ID does not exist

        trip = trip.iloc[0].to_dict()  # Convert to dictionary

        # ✅ Retrieve search parameters from session
        search_params = session.get('search_params', {})
        adults = int(search_params.get('adults', 1))  # Default 1 adult
        children = int(search_params.get('children', 0))  # Default 0 children

        # ✅ Extract pricing details (handle missing values safely)
        price_adult = int(trip.get("Price Adult", 0))  # Default to 0 if not found
        price_child = int(trip.get("Price Child", 0))  # Default to 0 if not found
        total_price = (adults * price_adult) + (children * price_child)  # ✅ Calculate total price
        trip["Total Price"] = round(total_price, 2)

        # ✅ Extract schedule details (if available)
        trip_schedule = {key: trip[key] for key in trip if 'Schedule' in key}

        # ✅ Load reviews for this specific trip
        reviews = load_reviews_for_trip(trip_id)

        # ✅ Retrieve selected date and alternative date from search parameters
        selected_date = search_params.get("date", "")
        alt_day = search_params.get("alt_day", "")

        # ✅ Render trip details page with all required data
        return render_template(
            "trip_details.html",
            trip=trip,
            price_adult=price_adult,
            price_child=price_child,
            total_price=total_price,
            trip_schedule=trip_schedule,
            selected_date=selected_date,
            alt_day=alt_day,
            search_params=search_params,
            reviews=reviews  # ✅ Pass reviews to the template
        )

    except Exception as e:
        return f"Error loading trip details: {str(e)}", 500  # ✅ Improved error handling
    
#####################################################################################################

@app.route('/submit_review/<trip_id>', methods=['POST'])
def submit_review(trip_id):
    """Handle review submission and store it in a CSV file."""
    name = request.form.get('name')
    email = request.form.get('email')
    rating = request.form.get('rating')
    comment = request.form.get('comment')

    if not name or not rating or not comment:
        return "All fields are required!", 400

    review_data = {
        "trip_id": str(trip_id),  # Ensure trip_id is always stored as a string
        "name": name,
        "email": email,
        "rating": rating,
        "comment": comment
    }

    save_review_to_csv(review_data)

    # ✅ Redirect back to the same trip details page after submission
    return redirect(url_for('view_trip', trip_id=trip_id))


def save_review_to_csv(review_data):
    """Save user reviews to reviews.csv."""
    file_path = "reviews.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # ✅ Write header if the file is new
        if not file_exists:
            writer.writerow(["trip_id", "name", "email", "rating", "comment"])

        # ✅ Store review data
        writer.writerow([
            review_data["trip_id"],
            review_data["name"],
            review_data["rating"],
            review_data["comment"],
            review_data["email"],
        ])

def load_reviews_for_trip(trip_id):
    """Retrieve all reviews for a specific trip from reviews.csv."""
    reviews = []
    file_path = "reviews.csv"
    
    if os.path.exists(file_path):
        with open(file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["trip_id"] == str(trip_id):  # ✅ Match trip_id correctly
                    reviews.append(row)

    return reviews  # ✅ Return list of reviews

#######################################################################################################################

@app.route("/book/<trip_id>", methods=["GET", "POST"])
def book_trip(trip_id):
    """Handle trip booking dynamically from the correct CSV and process the booking."""
    try:
        # ✅ Load the correct CSV file based on the selected language
        df = pd.read_csv(get_csv_file(), encoding='utf-8')  # ✅ Fix encoding


        # ✅ Find the trip by its Trip ID
        trip = df[df["Trip ID"].astype(str) == str(trip_id)]
        if trip.empty:
            return "Trip not found", 404  # ✅ Handle case where trip ID does not exist

        trip = trip.iloc[0].to_dict()  # Convert to dictionary

        # ✅ Retrieve search parameters from session
        search_params = session.get('search_params', {'adults': 1, 'children': 0, 'date': "", 'alt_day': ""})
        adults = int(request.args.get('adults', search_params.get('adults', 1)) or 1)
        children = int(request.args.get('children', search_params.get('children', 0)) or 0)

        # ✅ Extract selected date and alternative date safely
        selected_date = search_params.get("date", "")
        alt_day = search_params.get("alt_day", "")

        # ✅ Extract pricing details (handle missing values safely)
        price_adult =int(trip.get("Price Adult", 0))  # Default to 0 if not found
        price_child = int(trip.get("Price Child", 0))  # Default to 0 if not found
        total_price = (adults * price_adult) + (children * price_child)  # ✅ Calculate total price

        if request.method == "POST":
            # ✅ Generate a unique booking reference
            booking_reference = f"BOOK-{uuid.uuid4().hex[:8].upper()}"

            # ✅ Collect and store booking details
            booking_details = {
                "booking_reference": booking_reference,
                "date_of_booking": datetime.today().strftime('%Y-%m-%d'),  # ✅ Store today's date
                "customer_name": request.form.get("customer_name"),
                "email": request.form.get("email"),
                "phone": request.form.get("phone"),
                "trip_name": trip["Trip Name"],
                "destination": trip.get("Destination", ""),
                "selected_date": selected_date,  # ✅ Store user-selected date
                "alternative_date": alt_day,  # ✅ Store alternative date
                "adults": adults,
                "children": children,
                "total_price": total_price,
                "payment_method": request.form.get("payment_method"),
                "card_number": request.form.get("card_number") if request.form.get("payment_method") == "Credit Card" else "N/A",
                "bank_transfer_details": request.form.get("bank_transfer_details") if request.form.get("payment_method") == "Bank Transfer" else "N/A",
                "paypal_email": request.form.get("paypal_email") if request.form.get("payment_method") == "PayPal" else "N/A",
                "how_heard": request.form.get("how_heard"),
                "special_requests": request.form.get("special_requests", ""),
                "deposit_required": trip.get("Deposit Required", "No"),
                "visa_required": trip.get("Visa Required", "No"),
                "visa_fee": trip.get("Visa Fee", "N/A")
            }

            # ✅ Save booking details to CSV
            save_booking_to_csv(booking_details)

            # ✅ Store booking details in session for confirmation page
            session["booking_details"] = booking_details

            # ✅ Redirect to confirmation page with trip_id
            return render_template("Booking.html", trip=trip, trip_id=trip["Trip ID"])

        return render_template(
            "booking.html",
            trip=trip,
            trip_id=trip_id,
            adults=adults,
            children=children,
            total_price=total_price,
            search_params=search_params,
            date=selected_date,  # ✅ Pass selected date to booking.html
            alt_day=alt_day  # ✅ Pass alternative date to booking.html
        )

    except Exception as e:
        return f"Error processing booking: {str(e)}", 500  # ✅ Improved error handling


#####################################################################################################

def save_booking_to_csv(booking_details):
    """Save booking details into a CSV file."""
    file_path = "bookings.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=booking_details.keys())

        # ✅ Write the header only if the file does not exist
        if not file_exists:
            writer.writeheader()

        # ✅ Write booking data
        writer.writerow(booking_details)

    print("✅ Booking successfully saved to CSV!")

 ######################################################################################################################  

@app.route('/confirmation/<trip_id>', methods=['GET', 'POST'])  
def booking_confirmation(trip_id):
    from datetime import datetime  # ✅ Ensure datetime is imported
    import time
    """Process trip booking confirmation dynamically and store details in CSV."""
    try:
        # ✅ Load the correct CSV file based on selected language
        df = pd.read_csv(get_csv_file(), encoding='utf-8')  # ✅ Fix encoding


        # ✅ Retrieve trip details safely
        trip = df[df["Trip ID"].astype(str) == str(trip_id)]
        if trip.empty:
            return render_template("error.html", message="Trip not found"), 404

        trip = trip.iloc[0].to_dict()  # Convert trip to dictionary

        # ✅ Retrieve search parameters from session
        search_params = session.get('search_params', {"adults": 1, "children": 0, "date": "", "alt_day": ""})
        adults = int(search_params.get('adults', 1))
        children = int(search_params.get('children', 0))
        selected_date = search_params.get("date", "")
        alt_day = search_params.get("alt_day", "")

        # ✅ Convert price values safely
        price_adult = float(trip.get("Price Adult", 0))
        price_child = float(trip.get("Price Child", 0))
        total_price = (adults * price_adult) + (children * price_child)

        if request.method == 'POST':
            # ✅ Retrieve form details
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            payment_method = request.form.get('payment_method')
            how_heard = request.form.get('how_heard')  # ✅ "How did you hear about us?"
            stay_location = request.form.get('stay_location')  # ✅ "Where are you staying?"

            # ✅ Generate unique booking reference
            booking_reference = f"BOOK-{trip_id}-{int(time.time())}"
            trip_image = f"{trip_id}.jpg"

            # ✅ Store all booking details
            booking_details = {
                "booking_reference": booking_reference,
                "date_of_booking": datetime.today().strftime('%Y-%m-%d'),
                "customer_name": name,
                "email": email,
                "phone": phone,
                "trip_name": trip.get("Trip Name", "N/A"),
                "trip_image": trip_image,
                "destination": trip.get("Destination", "N/A"),
                "selected_date": selected_date,
                "alternative_date": alt_day,
                "adults": adults,
                "children": children,
                "price_adult": price_adult,
                "price_child": price_child,
                "total_price": total_price,
                "payment_method": payment_method,
                "how_heard": how_heard,
                "stay_location": stay_location,
                "Description": trip.get("Description", "N/A"),
                "Trip Category": trip.get("Trip Category", "N/A"),
                "available_spots": trip.get("Available Spots", "N/A"),
                "tour_guide": trip.get("Tour Guide", "N/A"),
                "group_size": trip.get("Group Size", "N/A"),
                "meeting_point": trip.get("Meeting Point", "N/A"),
                "departure_time": trip.get("Departure Time", "N/A"),
                "return_time": trip.get("Return Time", "N/A"),
                "rating": trip.get("Rating", "N/A"),
                "reviews_count": trip.get("Reviews Count", "N/A"),
                "contact_email": trip.get("Contact Email", "N/A"),
                "contact_phone": trip.get("Contact Phone", "N/A"),
                "what_to_bring": trip.get("What to Bring", "N/A"),
                "trip_difficulty": trip.get("Trip Difficulty", "N/A"),
                "languages_available": trip.get("Languages Available", "N/A"),
                "age_restrictions": trip.get("Age Restrictions", "N/A"),
                "transportation_type": trip.get("Transportation Type", "N/A"),
                "meals_included": trip.get("Meals Included", "N/A"),
                "cancellation_policy": trip.get("Cancellation Policy", "N/A"),
                "included_in_price": trip.get("Included in Price", "N/A"),
                "not_included": trip.get("Not Included", "N/A"),
            }

            # ✅ Save booking details to CSV
            save_booking_to_csv(booking_details)

            # ✅ Store booking details in session for confirmation page
            session['booking_details'] = booking_details

            # ✅ Redirect to confirmation page
            return render_template("confirmation.html", booking_details=booking_details)

        elif request.method == 'GET':
            # ✅ Retrieve booking details from session if available
            booking_details = session.get('booking_details')
            if not booking_details:
                return render_template("error.html", message="No booking details found"), 400

            return render_template("confirmation.html", booking_details=booking_details)

    except Exception as e:
        return f"Error processing booking confirmation: {str(e)}", 500  # ✅ Improved error handling

#####################################################################################################

def save_booking_to_csv(booking_details):
    """Save booking details into a CSV file."""
    file_path = "bookings.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=booking_details.keys())

        # ✅ Write the header only if the file does not exist
        if not file_exists:
            writer.writeheader()

        # ✅ Write booking data
        writer.writerow(booking_details)

    print("✅ Booking successfully saved to CSV!")

#################################################################################################################

@app.route('/about')
def about():
    return render_template('about.html')

 # Contact Us Page 
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        message = request.form.get('message')

        # Check if all fields are filled
        if not name or not phone or not email or not message:
            return "All fields are required!", 400

        # Debugging: Print form data
        print(f"Received form data: Name: {name}, Phone: {phone}, Email: {email}, Message: {message}")

        # Save to CSV
        file_path = "contact_us.csv"  # You can change this to an absolute path if needed
        file_exists = os.path.isfile(file_path)
        
        print(f"File exists: {file_exists}")  # Debugging file existence

        try:
            with open(file_path, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(["Name","Phone", "Email", "Message"])  # Write headers if file is new
                writer.writerow([name, phone, email, message])  # Write user data
                print("Data written to CSV successfully.")  # Debugging message

        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return f"Error saving data: {e}", 500
        
        # Debugging: Confirm successful form submission
        return render_template('contact.html', thank_you=True)  # Pass thank_you flag to render template

    return render_template('contact.html')  # Render the contact page template

###################################################################################################################################

# Request a Quote Page
@app.route('/quote', methods=['GET', 'POST'])
def request_quote():
    if request.method == 'POST':
        # Retrieve form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        trip = request.form.get('trip')
        dates = request.form.get('dates')
        date = request.form.get("date")
        adults = request.form.get('adults')
        children = request.form.get('children')
        stay = request.form.get('stay')
        special_requests = request.form.get('special_requests')
        details = request.form.get('details')

        # Save to CSV
        file_path = "quotes.csv"
        file_exists = os.path.isfile(file_path)

        try:
            with open(file_path, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(["Name", "Email", "Phone", "Trip", "Dates", "Date", "Adults", "Children", "Stay", "Special Requests", "Details", "price_per_adult", "price_per_child", "total_price", "discount"])
                writer.writerow([name, email, phone, trip, dates, date, adults, children, stay, special_requests, details, "", "", "", ""])  # Empty price fields
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return f"Error saving data: {e}", 500

        return render_template('request_quote.html', thank_you=True)

    return render_template('request_quote.html')


# Run the Flask app
if __name__ == "__main__":
   app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))  # Use port from Render
