from flask import Flask, render_template, request, session, redirect, url_for
import csv
import pandas as pd
import os
import random
import uuid
from flask_babel import Babel, _
from datetime import datetime  # ✅ Import at the top


app = Flask(__name__, template_folder="templates")
app.secret_key = 'your_secret_key_here'
app.config['LANGUAGES'] = ['en', 'ar', 'fr']  # Define available languages

# Load CSV and extract unique destinations
df = pd.read_csv("egypttrips.csv")
unique_destinations = df["Destination"].unique().tolist()


# Define available languages
app.config['LANGUAGES'] = ['en', 'ar']

# ✅ Define locale selector function (without decorator)
def get_locale():
    babel = Babel(locale_selector=lambda: session.get('language', request.accept_languages.best_match(app.config['LANGUAGES'])))


# ✅ Initialize Babel with `locale_selector`
babel = Babel(app, locale_selector=get_locale)


@app.context_processor  # ✅ This ensures `_()` works inside Jinja
def inject_translations():
    return {'_': _}  


@app.route('/set_language/<lang>')
def set_language(lang):
    """Change user language and store it in session."""
    if lang in app.config['LANGUAGES']:
        session['language'] = lang
    return redirect(request.referrer or url_for('home'))


# Extract unique destinations
unique_destinations = sorted(df["Destination"].unique().tolist())

# Group trips by destination and select 3 random trips for each destination
grouped_trips = {
    destination: trips.sample(3).to_dict(orient="records")  # Select 3 random trips per destination
    for destination, trips in df.groupby("Destination")
}


@app.route('/')
def home():
    """Render homepage with search and destination tabs."""
    try:
        # Select 3 random featured trips for the homepage
        featured_trips = df.sample(3).to_dict(orient="records") if not df.empty else []

        # Group trips by destination
        grouped_trips = {}
        for _, trip in df.iterrows():
            destination = trip["Destination"]
            if destination not in grouped_trips:
                grouped_trips[destination] = []
            grouped_trips[destination].append(trip.to_dict())

        # Randomly select up to 6 trips for each destination
        for destination in grouped_trips:
            grouped_trips[destination] = random.sample(grouped_trips[destination], min(6, len(grouped_trips[destination])))

        # Ensure Hurghada is first and Cairo is last in the destination list
        sorted_destinations = sorted(
            grouped_trips.keys(), key=lambda d: (d != "Hurghada", d == "Cairo", d)
        )

        # Reorder grouped_trips according to sorted destinations
        grouped_trips = {destination: grouped_trips[destination] for destination in sorted_destinations}

        # Pass the sorted destinations and grouped trips to the template
        return render_template(
            "search.html",
            destinations=sorted_destinations,  # Sorted: Hurghada first, Cairo last
            featured_trips=featured_trips,  # Featured trips section
            grouped_trips=grouped_trips,  # Grouped trips per destination (now properly ordered)
        )
    except Exception as e:
        return f"Error loading homepage: {str(e)}", 500

    
@app.route("/result", methods=["POST"])
def search_results():
    """Process search requests and display results in result.html."""
    destination = request.form.get("destination")
    date = request.form.get("date")
    alt_day = request.form.get("alt_day")
    adults = int(request.form.get("adults", 1))
    children = int(request.form.get("children", 0))

    # Save search parameters in session
    session['search_params'] = {
        'adults': adults,
        'children': children,
        'date': date,
        'alt_day': alt_day
    }

    # Filter trips based on destination
    filtered_trips = df[df["Destination"] == destination].copy()

    # Calculate total price for each trip
    for index, row in filtered_trips.iterrows():
        adult_price = float(row["Price Adult"])
        child_price = float(row["Price Child"])
        total_price = (adults * adult_price) + (children * child_price)
        filtered_trips.at[index, "Total Price"] = round(total_price, 2)
        filtered_trips.at[index, "Rating"] = row.get("Rating", "N/A")  # Include Rating


    # Convert to list of dictionaries
    trips = filtered_trips.to_dict(orient="records")

    return render_template("result.html", trips=trips, destination=destination, date=date, alt_day=alt_day, adults=adults, children=children)

    
@app.route("/view/<trip_id>") 
def view_trip(trip_id):
    # Use the Trip ID to get the row corresponding to that trip
    trip = df[df["Trip ID"] == trip_id].iloc[0].to_dict()  # Find the trip by its ID

    # Get the search parameters from the session
    search_params = session.get('search_params', {})

    adults = search_params.get('adults', 1)  # Default to 1 if not found
    children = search_params.get('children', 0)  # Default to 0 if not found

    price_adult = int(trip.get("Price Adult", 0))  # Default to 0 if not found
    price_child = int(trip.get("Price Child", 0))  # Default to 0 if not found

    # Calculate total price for the party (adults + children)
    total_price = (adults * price_adult) + (children * price_child)
    trip["Total Price"] = round(total_price, 2)

    # Get the trip schedule details (if available)
    trip_schedule = {key: trip[key] for key in trip if 'Schedule' in key}

    # Load reviews for this trip
    reviews = []
    if os.path.exists("reviews.csv"):
        with open("reviews.csv", mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["trip_id"] == trip_id:
                    reviews.append(row)

    # ✅ Get selected date and alternative date from search_params
    selected_date = search_params.get("date", "")
    alt_day = search_params.get("alt_day", "")

    # Return trip_details.html with reviews
    return render_template(
        "trip_details.html",
        trip=trip,
        price_adult=price_adult,
        price_child=price_child,
        total_price=total_price,
        trip_schedule=trip_schedule,
        selected_date=selected_date,  # ✅ Pass selected date
        alt_day=alt_day,  # ✅ Pass alternative date
        search_params=search_params,
        reviews=reviews  # ✅ Pass reviews to the template
    )

@app.route('/submit_review/<trip_id>', methods=['POST'])
def submit_review(trip_id):
    """Handle review submission and store it in a CSV file."""
    name = request.form.get('name')
    email= request.form.get('email')
    rating = request.form.get('rating')
    comment = request.form.get('comment')

    if not name or not rating or not comment:
        return "All fields are required!", 400

    review_data = {
        "trip_id": trip_id,
        "name": name,
        "email":email,
        "rating": rating,
        "comment": comment
    }

    save_review_to_csv(review_data)

    # Redirect back to the same trip details page, not trip_view.html
    return redirect(url_for('view_trip', trip_id=trip_id))  # 🔥 Redirect to trip details!

def save_review_to_csv(review_data):
    """Save user reviews to reviews.csv."""
    file_path = "reviews.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Write the header if the file does not exist
        if not file_exists:
            writer.writerow(["trip_id", "name", "rating", "comment","email"])

        # Write review data
        writer.writerow([review_data["trip_id"], review_data["name"], review_data["rating"], review_data["comment"], review_data["email"]])

    print("✅ Review saved successfully!")
@app.route('/trip/<trip_id>')
def trip_view(trip_id):
    """Display trip details along with user reviews."""
    trip_data = df[df["Trip ID"] == trip_id].to_dict(orient="records")

    if not trip_data:
        return render_template("error.html", message="Trip not found"), 404

    trip = trip_data[0]

    # Load reviews for this trip
    reviews = []
    if os.path.exists("reviews.csv"):
        with open("reviews.csv", mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["trip_id"] == trip_id:
                    reviews.append(row)

    return render_template("trip_view.html", trip=trip, reviews=reviews)


@app.route("/book/<trip_id>", methods=["GET", "POST"]) 
def book_trip(trip_id):
    from datetime import datetime  # ✅ Ensure datetime is imported

    # Retrieve search parameters from session
    search_params = session.get('search_params', {'adults': 1, 'children': 0, 'date': "", 'alt_day': ""})
    
    # Retrieve and handle empty values
    adults = int(request.args.get('adults', search_params.get('adults', 1)) or 1)
    children = int(request.args.get('children', search_params.get('children', 0)) or 0)

    # ✅ Extract selected date and alternative date safely
    selected_date = search_params.get("date", "")  
    alt_day = search_params.get("alt_day", "")

    # Fetch trip details
    trip = df.loc[df["Trip ID"] == trip_id].to_dict(orient="records")
    if not trip:
        return "Trip not found", 404

    trip = trip[0]  # Extract the trip details

    # Price calculation
    price_adult = int(trip.get("Price Adult", 0))
    price_child = int(trip.get("Price Child", 0))
    total_price = (adults * price_adult) + (children * price_child)

    if request.method == "POST":
        # Generate a unique booking reference
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
        csv_file = "booking.csv"
        file_exists = os.path.isfile(csv_file)

        with open(csv_file, "a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=booking_details.keys())
            if not file_exists:
                writer.writeheader()  # Write headers if file doesn't exist
            writer.writerow(booking_details)

        # ✅ Store booking details in session for confirmation page
        session["booking_details"] = booking_details

        ## ✅ Redirect to confirmation page with trip_id
        return render_template("Booking.html", trip=trip, trip_id=trip['Trip ID'])

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


def save_booking_to_csv(booking_details):
    """Save booking details into a CSV file."""
    file_path = "bookings.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Write the header only if the file does not exist
        if not file_exists:
            writer.writerow(booking_details.keys())

        # Write booking data
        writer.writerow(booking_details.values())

    print("✅ Booking successfully saved to CSV!")
    
@app.route('/confirmation/<trip_id>', methods=['GET', 'POST'])  
def booking_confirmation(trip_id):
    from datetime import datetime  # ✅ Ensure datetime is imported
    import time

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        payment_method = request.form.get('payment_method')
        how_heard = request.form.get('how_heard')  # ✅ Get "How did you hear about us?"
        stay_location = request.form.get('stay_location')  # ✅ Get "Where are you staying?"

        # Retrieve trip details
        trip_data = df[df["Trip ID"] == trip_id].to_dict(orient="records")
        if not trip_data:
            return render_template("error.html", message="Trip not found"), 404

        trip = trip_data[0]  # Extract the trip details

        # Get search parameters from session
        search_params = session.get('search_params', {"adults": 1, "children": 0, "date": "", "alt_day": ""})
        adults = int(search_params.get('adults', 1))
        children = int(search_params.get('children', 0))
        selected_date = search_params.get("date", "")  
        alt_day = search_params.get("alt_day", "")

        # Convert price values safely
        price_adult = float(trip.get("Price Adult", 0))
        price_child = float(trip.get("Price Child", 0))
        total_price = (adults * price_adult) + (children * price_child)

        # Generate unique booking reference
        booking_reference = f"BOOK-{trip_id}-{int(time.time())}"
        trip_image = f"{trip_id}.jpg"

        # ✅ Store booking details including new fields
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
            "how_heard": how_heard,  # ✅ Store "How did you hear about us?"
            "stay_location": stay_location,  # ✅ Store "Where are you staying?"
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

        # ✅ Save the booking details to CSV
        save_booking_to_csv(booking_details)

        # Store booking details in session (optional)
        session['booking_details'] = booking_details

        return render_template("confirmation.html", booking_details=booking_details)

    elif request.method == 'GET':
        booking_details = session.get('booking_details')
        if not booking_details:
            return render_template("error.html", message="No booking details found"), 400
        return render_template("confirmation.html", booking_details=booking_details)


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

        # Validate the data
        if not all([name, email, phone, trip, dates, date, adults, children, stay, special_requests, details]):
            return "All fields are required!", 400

        # Save to CSV
        file_path = "quotes.csv"
        file_exists = os.path.isfile(file_path)

        try:
            with open(file_path, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                # Write headers if file does not exist
                if not file_exists:
                    writer.writerow(["Name", "Email", "Phone", "Trip", "Dates", "Date", "Adults", "Children", "Stay", "Special Requests", "Details"])
                # Write form data to CSV
                writer.writerow([name, email, phone, trip, dates, date, adults, children, stay, special_requests, details])

        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return f"Error saving data: {e}", 500

        # Return thank you message
        return render_template('request_quote.html', thank_you=True)

    return render_template('request_quote.html')

# Run the Flask app
if __name__ == "__main__":
   app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))  # Use port from Render

