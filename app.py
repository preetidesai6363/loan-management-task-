from flask import Flask, render_template, request, session,redirect,url_for,jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import secrets
from bson.objectid import ObjectId 

# Initialize the Flask app and MongoDB connection
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Set up MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['loan']  # Replace with your database name
users_collection = db['user'] 
loans_collection = db['loans'] 
admins_collection = db['admins']
# loan_data_collection = db['loan_data']
# Replace with your collection name

# Set up Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'preetidesai6363@gmail.com'
app.config['MAIL_PASSWORD'] = 'hyxqnrqyyqgjllrc'
mail = Mail(app)

# Email validation function
def validate_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email)

# Password validation function
def validate_password(password):
    return len(password) >= 8


@app.route('/')
def index():
    return render_template('index.html')

@app.route("/admin")
def admin():
    return render_template('admin.html')

@app.route("/user", methods=["POST", "GET"])
def user():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        contact = request.form['mobile']
        address = request.form['address']

        # Input validation
        if not validate_email(email):
            return render_template('user.html', msg="Invalid email format")
        
        if not validate_password(password):
            return render_template('user.html', msg="Password must be at least 8 characters long")
        
        if users_collection.find_one({"email": email}):
            return render_template('user.html', msg="Email is already registered")

        # Hash the password before saving it in the database
        hashed_password = generate_password_hash(password)

        # Insert the new user into the MongoDB database
        user_data = {
            "name": name,
            "email": email,
            "password": hashed_password,
            "contact": contact,
            "address": address
        }

        users_collection.insert_one(user_data)

        return render_template('userlog.html', msg='Registered successfully')
    
    return render_template('user.html')

@app.route("/userlog", methods=["POST", "GET"])
def userlog():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        
        # MongoDB query to check for user existence
        user = users_collection.find_one({
            "email": email
        })
        
        if user and check_password_hash(user['password'], password):
            session['useremail'] = email
            return render_template('userhome.html', msg="Login successful")
        else:
            return render_template('userlog.html', msg="Invalid email or password")
    
    return render_template('userlog.html')

# Helper function to validate loan amount
def validate_loan_amount(amount):
    return 50000 <= amount <= 1000000

# Helper function to validate loan tenure
def validate_loan_tenure(tenure):
    return 1 <= tenure <= 5

# Helper function to validate purpose
def validate_purpose(purpose):
    return len(purpose.strip()) > 0 and len(purpose.strip()) <= 200

@app.route("/apply_loan", methods=["POST", "GET"])
def apply_loan():
    # Check if the user is logged in
    if 'useremail' not in session:
        return redirect(url_for('userlog'))  # Redirect to login if not logged in

    if request.method == "POST":
        loan_amount = int(request.form['loan_amount'])  # Loan amount (convert to integer)
        loan_tenure = int(request.form['loan_tenure'])  # Loan tenure (convert to integer)
        purpose = request.form['purpose']  # Loan purpose

        # Validate loan amount
        if not validate_loan_amount(loan_amount):
            return render_template('apply_loan.html', msg="Loan amount must be between 50,000 and 10,00,000.")

        # Validate loan tenure
        if not validate_loan_tenure(loan_tenure):
            return render_template('apply_loan.html', msg="Loan tenure must be between 1 and 5 years.")

        # Validate purpose
        if not validate_purpose(purpose):
            return render_template('apply_loan.html', msg="Purpose must be non-empty and within 200 characters.")

        # Check for duplicate loan application for the same purpose by the same user
        user_email = session['useremail']
        duplicate_loan = loans_collection.find_one({
            "email": user_email,
            "purpose": purpose
        })

        if duplicate_loan:
            return render_template('apply_loan.html', msg="You have already applied for a loan with the same purpose.")

        # Insert the new loan application into the database
        loan_data = {
            "email": user_email,
            "loan_amount": loan_amount,
            "loan_tenure": loan_tenure,
            "purpose": purpose,
            "status": "pending"  # Initial status of the loan
        }

        loans_collection.insert_one(loan_data)

        return redirect(url_for('apply_loan'), msg="Loan application submitted successfully.")
    
    return render_template('apply_loan.html')

# Default admin credentials
DEFAULT_EMAIL = 'admin@gmail.com'
DEFAULT_PASSWORD = 'admin'  # Change this to a more secure password in production

# Function to ensure the default admin exists
def ensure_default_admin():
    # Check if the admin already exists
    if not admins_collection.find_one({"email": DEFAULT_EMAIL}):
        # Hash the default password
        hashed_password = generate_password_hash(DEFAULT_PASSWORD)
        # Insert the default admin into the database
        admins_collection.insert_one({"email": DEFAULT_EMAIL, "password": hashed_password})

# Call the function at the start of the application
ensure_default_admin()

@app.route("/adminlog", methods=["POST", "GET"])
def adminlog():
    if request.method == "POST":
        username = request.form['email']
        password = request.form['password']
        
        # Fetch admin credentials from the database
        admin = admins_collection.find_one({"email": username})

        # Check if the admin exists and verify the password
        if admin and check_password_hash(admin['password'], password):
            session['adminemail'] = username  # Store admin email in session
            return render_template('adminhome.html', msg="Login successful")
        else:
            return render_template('admin.html', msg="Login Failed!")

    return render_template('admin.html')

@app.route("/adminhome")
def adminhome():
    # Ensure the admin is logged in
    if 'adminemail' not in session:
        return redirect(url_for('adminlog'))  # Redirect to login if not logged in
    return render_template('adminhome.html')

@app.route("/adminlogout")
def adminlogout():
    session.pop('adminemail', None)  # Remove admin email from session
    return redirect(url_for('adminlog'))  # Redirect to admin login page

@app.route("/viewloan")
def viewloan():
    # Fetch loan data with status 'pending' from MongoDB
    data = loans_collection.find({"status": "pending"})
    
    # Convert the cursor to a list to easily manipulate
    data_list = list(data)
    
    # If data is empty, handle it gracefully
    if not data_list:
        return render_template('viewloan.html', cols=[], rows=[])

    # Get column names from the first document
    cols = data_list[0].keys()

    # Convert documents to a list of values for rendering
    rows = [[item[col] for col in cols] for item in data_list]

    return render_template('viewloan.html', cols=cols, rows=rows)



@app.route("/acceptloanrequest/<id>/<email>", methods=["POST", "GET"])
def acceptloanrequest(id, email):
    print(id)
    print(session.get('useremail'))  # Safely access session variable
    
    # Convert string ID to ObjectId
    loan_id = ObjectId(id)
    
    # Fetch the loan details based on the loan ID
    loan = loans_collection.find_one({"_id": loan_id})
    
    if loan is None:
        print("No loan found with the specified ID.")
        return redirect(url_for('viewloan'))  # Handle no loan case

    print(loan)
    
    # Prepare email content
    mail_content = 'Your Loan request is accepted by admin'
    sender_address = 'preetidesai6363@gmail.com'
    receiver_address = email
    message = Message(subject='Loan Management System',
                      sender=sender_address,
                      recipients=[receiver_address])
    message.body = mail_content

    # Send the email
    mail.send(message)

    # Update loan status to 'Approved'
    result = loans_collection.update_one({"_id": loan_id}, {"$set": {"status": "Approved"}})

    if result.modified_count > 0:
        print("Loan status updated successfully.")
    else:
        print("No documents were updated. Check if the document exists or the update is needed.")

    return redirect(url_for('viewloan'))

@app.route("/rejectloanrequest/<id>", methods=["POST", "GET"])
def rejectloanrequest(id):
    print(id)
    print(session.get('useremail'))  # Safely access session variable
    
    # Convert string ID to ObjectId
    loan_id = ObjectId(id)
    
    # Update loan status to 'Rejected'
    result = loans_collection.update_one({"_id": loan_id}, {"$set": {"status": "Rejected"}})

    if result.modified_count > 0:
        print("Loan status updated successfully.")
    else:
        print("No documents were updated. Check if the document exists or the update is needed.")
    
    return redirect(url_for('viewloan'))

@app.route("/viewuserstatus")
def viewuserstatus():
    return render_template('viewuserstatus.html')  # Ensure this template exists


@app.route("/loan_status", methods=["GET"])
def loan_status():
    # Check if the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('viewuserstatus'))  # Redirect to the viewuserstatus page

    user_id = session['user_id']  # Get logged-in user's ID

    # Fetch the loan status for the logged-in user
    loan = loans_collection.find_one({"user_id": user_id})

    if loan:
        return jsonify({
            "loan_id": str(loan["_id"]),
            "amount": loan["amount"],
            "tenure": loan["tenure"],
            "purpose": loan["purpose"],
            "status": loan["status"]
        }), 200
    else:
        return redirect(url_for('viewuserstatus'))  
    
# Ensure the app runs
if __name__ == "__main__":
    app.run(debug=True)
