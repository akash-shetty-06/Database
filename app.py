from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
from flask_session import Session

app = Flask(__name__)

# Configure session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'your_secret_key'
Session(app)

# Database connection
def get_sql_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='1812',
        database='amulya'
    )

@app.route('/')
def index():
    return render_template('index.html')  # Serve the login page

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user_id = data.get('user_id')
    password = data.get('password')
    access_type = data.get('access_type')  # Access type: 'customer' or 'manager'

    conn = get_sql_connection()
    cursor = conn.cursor()

    try:
        # Call the stored procedure
        status_message = ""
        result = cursor.callproc('GetUserAccess', (user_id, password, access_type, status_message))

        # Retrieve the output parameter
        status_message = result[3]

        if "successful" in status_message.lower():
            # Save session details for successful login
            session['user_id'] = user_id
            session['access_type'] = access_type
            if access_type == 'manager':
                return jsonify({'message': status_message, 'redirect': '/manager_dashboard'}), 200
            else:
                return jsonify({'message': status_message, 'redirect': '/dashboard'}), 200
        else:
            return jsonify({'error': status_message}), 401
    finally:
        cursor.close()
        conn.close()

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['access_type'] != 'customer':
        return redirect(url_for('index'))  # Redirect to login if not authenticated

    user_id = session['user_id']

    conn = get_sql_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch user details
        cursor.callproc('GetUserDetails', [user_id])
        user_data = None
        for result in cursor.stored_results():
            user_data = result.fetchone()

        # If no user data is found
        if not user_data:
            return "User data not found", 404

        return render_template('dashboard.html', user=user_data)
    except Exception as e:
        print(f"Error: {e}")
        return "An error occurred while fetching data", 500
    finally:
        cursor.close()
        conn.close()



@app.route('/apply_loan', methods=['GET'])
def apply_loan():
    if 'user_id' not in session or session['access_type'] != 'customer':
        return redirect(url_for('index'))  # Redirect to login if not authenticated or not a customer

    user_id = session['user_id']  # Get the logged-in user ID
    return render_template('apply_loan.html', user_id=user_id)

@app.route('/automated_review', methods=['GET'])
def automated_review():
    if 'user_id' not in session or session['access_type'] != 'customer':
        return redirect(url_for('index'))  # Redirect to login if not authenticated or not a customer

    user_id = session['user_id']  # Get the logged-in user ID
    return render_template('automated_review.html', user_id=user_id)


@app.route('/submit_automated_review', methods=['POST'])
def submit_automated_review():
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redirect to login if not authenticated

    # Retrieve session and form data
    user_id = session['user_id']
    loan_amount = float(request.form.get('amount'))
    duration = int(request.form.get('duration'))
    purpose = request.form.get('reason')

    conn = None
    cursor = None

    try:
        # Connect to the database
        conn = get_sql_connection()
        cursor = conn.cursor()

        # Call the stored procedure
        cursor.callproc('EvaluateLoanApplication', [user_id, loan_amount, duration, purpose])
        conn.commit()

    except mysql.connector.Error as e:
        print(f"MySQL Error: {e}")
        return "An error occurred while processing your loan application.", 500

    finally:
        # Safely close the connection and cursor
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Redirect to the dashboard after submission
    return redirect(url_for('dashboard'))




@app.route('/submit_loan_application', methods=['POST'])
def submit_loan_application():
    if 'user_id' not in session or session['access_type'] != 'customer':
        return redirect(url_for('index'))  # Redirect to login if not authenticated

    user_id = request.form['user_id']
    loan_duration = request.form['loan_duration']
    loan_amount = request.form['loan_amount']
    purpose = request.form['purpose']

    conn = get_sql_connection()
    cursor = conn.cursor()

    try:
        # Insert the loan application
        cursor.callproc('InsertLoanApplication', [user_id, loan_duration, loan_amount, purpose])
        conn.commit()
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()
        conn.close()

@app.route('/loan_applications', methods=['GET'])
def loan_applications():
    if 'user_id' not in session or session['access_type'] != 'customer':
        return redirect(url_for('index'))  # Redirect to login if not authenticated

    user_id = session['user_id']

    conn = get_sql_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch loan applications for the logged-in user
        cursor.execute("""
            SELECT 
                loan_application_id,
                loan_amount,
                loan_duration,
                purpose,
                status
            FROM loan_application
            WHERE user_id = %s
        """, (user_id,))
        loan_applications = cursor.fetchall()

        return render_template('loan_applications.html', loans=loan_applications)
    finally:
        cursor.close()
        conn.close()



@app.route('/manager_dashboard', methods=['GET', 'POST'])
def manager_dashboard():
    if 'user_id' not in session or session['access_type'] != 'manager':
        return redirect(url_for('index'))  # Redirect to login if not authenticated

    if request.method == 'POST':
        searched_user_id = request.form.get('user_id')
        if searched_user_id:
            return redirect(url_for('user_details', user_id=searched_user_id))

    # Handle pagination
    page = request.args.get('page', 1, type=int)
    rows_per_page = 3
    offset = (page - 1) * rows_per_page

    conn = get_sql_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch paginated loan applications
        cursor.callproc('GetLoanApplicationsPaginated', [rows_per_page, offset])
        loan_applications = []
        for result in cursor.stored_results():
            loan_applications = result.fetchall()

        # Get total rows for pagination
        cursor.execute("SELECT COUNT(*) AS total FROM loan_application")
        total_rows = cursor.fetchone()['total']
        total_pages = (total_rows + rows_per_page - 1) // rows_per_page

        return render_template(
            'manager_dashboard.html',
            manager_name=session['user_id'],
            loan_applications=loan_applications,
            current_page=page,
            total_pages=total_pages
        )
    except Exception as e:
        print(f"Error: {e}")
        return "An error occurred while fetching loan applications.", 500
    finally:
        cursor.close()
        conn.close()



@app.route('/update_loan_status', methods=['POST'])
def update_loan_status():
    if 'user_id' not in session or session['access_type'] != 'manager':
        return redirect(url_for('index'))  # Redirect to login if not authenticated

    loan_application_id = request.form.get('loan_application_id')
    status = request.form.get('status')

    # Validate inputs
    if not loan_application_id or status not in ['Approved', 'Rejected']:
        return "Invalid input", 400

    conn = get_sql_connection()
    cursor = conn.cursor()

    try:
        # Call the stored procedure to update loan status
        cursor.callproc('UpdateLoanStatus', [loan_application_id, status])
        conn.commit()

        # Verify the status was updated
        cursor.execute(
            "SELECT status FROM loan_application WHERE loan_application_id = %s",
            (loan_application_id,)
        )
        updated_status = cursor.fetchone()

        if updated_status and updated_status[0] == status:
            return redirect(url_for('manager_dashboard'))
        else:
            return "Status update failed. Ensure the application is in 'Pending' state.", 400
    except mysql.connector.Error as e:
        print(f"MySQL Error: {e}")
        return "An error occurred while updating the status.", 500
    finally:
        cursor.close()
        conn.close()





@app.route('/search_user', methods=['GET'])
def search_user():
    if 'user_id' not in session or session['access_type'] != 'manager':
        return redirect(url_for('index'))  # Redirect to login if not authenticated or not manager

    # Get the user_id from the query string
    user_id = request.args.get('user_id')

    conn = get_sql_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch user details from account_holder table
        cursor.callproc('GetUserDetailsById', [user_id])

        # Fetch results from the stored procedure
        user_details = None
        for result in cursor.stored_results():
            user_details = result.fetchone()

        return render_template('user_details.html', user=user_details)
    finally:
        cursor.close()
        conn.close()

@app.route('/user_details', methods=['GET'])
def user_details():
    if 'user_id' not in session or session['access_type'] != 'manager':
        return redirect(url_for('index'))  # Redirect to login if not authenticated

    # Get user_id from the query parameter
    user_id = request.args.get('user_id')

    conn = get_sql_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch user details for the given user_id
        cursor.callproc('GetUserDetailsById', [user_id])
        user_details = None
        for result in cursor.stored_results():
            user_details = result.fetchone()

        # Render user_details.html with the fetched data
        return render_template('user_details.html', user=user_details)
    finally:
        cursor.close()
        conn.close()


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear the session to log the user out
    return redirect(url_for('index'))  # Redirect to the login page

if __name__ == '__main__':
    app.run(debug=True)
