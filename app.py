import cv2
import os
import uuid
import numpy as np
import pickle
import mediapipe as mp
from flask import Flask, render_template, redirect, request, url_for, flash, session, Response
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import g
app = Flask(__name__)

# Secret key for session management
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = ''
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = ''
app.config['MYSQL_PORT']=
mysql = MySQL(app)

# Registration Form
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[Length(min=4, max=25), DataRequired()])
    email = StringField('Email', validators=[Email(), DataRequired()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Register')

# Login Form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[Email(), DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


# Routes
@app.route('/')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    return render_template('home.html', username=None)

@app.route('/index')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    flash('Please log in first', 'danger')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = generate_password_hash(form.password.data)

        # Insert into MySQL
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(username, email, password) VALUES(%s, %s, %s)", (username, email, password))
        mysql.connection.commit()
        cur.close()

        flash('You are now registered and can log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password_candidate = form.password.data

        # Check if user exists
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT id, username, email, password FROM users WHERE email = %s", [email])

        if result > 0:
            data = cur.fetchone()
            user_id = data[0] 
            username = data[1]  # Assuming column 1 is 'username'
            stored_email = data[2]  # Assuming column 2 is 'email'
            stored_password = data[3]  # Assuming column 3 is 'password'

            # Compare passwords
            if check_password_hash(stored_password, password_candidate):
                # Set session variables
                session['logged_in'] = True
                session['username'] = username
                session['email'] = stored_email
                session['user_id'] = user_id 
                session_id = str(uuid.uuid4())  # Get user's IP address
                cur.execute("INSERT INTO sessions (session_id, user_id, created_at, last_active) VALUES (%s, %s, NOW(), NOW())",
                    (session_id, user_id)
                )
                mysql.connection.commit()
                 # Insert login history
                ip_address = request.remote_addr  # Get the user's IP address
                cur.execute("""
                    INSERT INTO user_login_history (user_id, ip_address, successful)
                    VALUES (%s, %s, %s)
                """, (user_id, ip_address, 1))  # 1 indicates a successful login
                mysql.connection.commit()
                cur.execute(
                    "INSERT INTO logs (user_id, activity_type, description) VALUES (%s, %s, %s)",
                    (user_id, 'login', f'{username} logged in')
                )
                mysql.connection.commit()
                session['session_id'] = session_id

                # Log session start in session_logs
               
                flash('You are now logged in', 'success')
                cur.close()
                return redirect(url_for('index'))
            else:
                flash('Invalid password', 'danger')
        else:
            flash('User not registered', 'danger')  
        cur.close()
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
     if 'user_id' in session:
        user_id = session['user_id']
        username = session['username']
        
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO logs (user_id, activity_type, description) VALUES (%s, %s, %s)",
            (user_id, 'logout', f'{username} logged out')
        )
        mysql.connection.commit()
        ip_address = request.remote_addr  # Get the user's IP address
        cur.execute("""
            INSERT INTO user_login_history (user_id, ip_address, successful)
            VALUES (%s, %s, %s)
        """, (user_id, ip_address, 0))  # 0 indicates a logout event or unsuccessful login
        mysql.connection.commit()
        cur.close()

     if 'session_id' in session:
        session_id = session['session_id']
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE sessions SET last_active = NOW() WHERE session_id = %s",
            (session_id,)
        )
        mysql.connection.commit()
        cur.close()
     session.clear()  # Clear the session
     flash('You have been successfully logged out!', 'success')  # Flash message
     return redirect(url_for('login'))  # Redirect to login page

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'email' not in session:  # Ensure user is logged in
        flash('Please log in to view your profile.', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the database
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, email, profile_picture FROM users WHERE email = %s", [session['email']])
    user = cur.fetchone()
    cur.close()

    if user:
        user_data = {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'profile_picture': user[3]  # Fetch profile picture
        }
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('logout'))

    # Handle profile update (POST request)
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        profile_picture = request.files.get('profile_picture')

        # Update username and email in the database
        cur = mysql.connection.cursor()
        cur.execute("UPDATE users SET username = %s, email = %s WHERE email = %s", 
                    [username, email, session['email']])
        mysql.connection.commit()

        # Handle profile picture update if a new file is provided
        if profile_picture:
            # Secure the filename and save the image in the uploads folder
            image_filename = secure_filename(profile_picture.filename)
            profile_picture.save(os.path.join('static/uploads', image_filename))

            # Update profile picture in the database
            cur.execute("UPDATE users SET profile_picture = %s WHERE email = %s", 
                        [f'uploads/{image_filename}', session['email']])
            mysql.connection.commit()

        cur.close()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))  # Redirect to profile page after update

    return render_template('profile.html', user=user_data)

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    flash('Please log in first', 'danger')
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' in session:
        if request.method == 'POST':
            selected_theme = request.form.get('theme')  # Get selected theme from form
            session['theme'] = selected_theme  # Save selected theme in session

            # Update the theme in the database
            cur = mysql.connection.cursor()
            cur.execute("SELECT settings_user_id FROM settings WHERE settings_user_id = (SELECT id FROM users WHERE email = %s)", [session['email']])
            existing_settings = cur.fetchone()

            if existing_settings:
                # If settings exist, update the theme (or dark_mode if applicable)
                cur.execute("UPDATE settings SET dark_mode = %s WHERE settings_user_id = %s", [selected_theme, existing_settings[0]])
            else:
                # If settings do not exist, insert new settings
                cur.execute("INSERT INTO settings (settings_user_id, dark_mode) VALUES ((SELECT id FROM users WHERE email = %s), %s)", [session['email'], selected_theme])
            mysql.connection.commit()
            cur.close()

            flash(f'Theme changed to {selected_theme}!', 'success')
            return redirect(url_for('settings'))  # Redirect to refresh the page
        
        # Fetch current theme (or dark_mode) from the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT dark_mode FROM settings WHERE settings_user_id = (SELECT id FROM users WHERE email = %s)", [session['email']])
        theme = cur.fetchone()
        cur.close()

        # Use the theme from the session or fallback to the database
        current_theme = theme[0] if theme else session.get('theme', 'default')

        return render_template('settings.html', username=session['username'], theme=current_theme)

    flash('Please log in first', 'danger')
    return redirect(url_for('login'))


@app.before_request
def before_request():
    # Set the language for all templates globally
    g.language = session.get('language', 'en')  # Default language is 'en' if not set
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'username' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        feedback_text = request.form.get('feedback')
        rating = request.form.get('rating') 
        username = session['username']  # Get logged-in username
        
        if not feedback_text:
            flash('Feedback cannot be empty!', 'danger')
            return redirect(url_for('feedback'))
        
        # Set rating to None if no rating is selected
        if rating == '':
            rating = None
        # Insert feedback into the database
        cur = mysql.connection.cursor()
      # Assuming 'session['user_id']' contains the user's ID
        cur.execute("INSERT INTO feedback(feedback_user_id, message, rating) VALUES(%s, %s, %s)",
            (session['user_id'], feedback_text, rating))  # or provide an actual rating value


        mysql.connection.commit()
        cur.close()

        flash('Your feedback has been submitted!', 'success')
        return redirect(url_for('feedback'))

    return render_template('feedback.html', username=session['username'])

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if 'username' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('login'))  # If user is not logged in, redirect to login page

    # Fetch user ID based on the logged-in username
     
    if request.method == 'POST':
        # Fetch the message from the form
        message = request.form['message']
        
        # Fetch user ID based on the logged-in username
        username = session['username']
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        # Insert message into the database
        if user:
            user_id = user[0]
            # Insert the message into the contact table
            cur.execute(
                "INSERT INTO contact (customer_id, message) VALUES (%s, %s)",
                (user_id, message)
            )
            mysql.connection.commit()
            flash('Your message has been sent!', 'success')
        else:
            flash('User not found. Please log in again.', 'danger')

        cur.close()
        return redirect(url_for('contact'))

    return render_template('contact.html', username=session['username'])

# Video Stream Route
try:
    model_dict = pickle.load(open('./model.p', 'rb'))
    model = model_dict['model']
except Exception as e:
    print("Error loading the model:", e)
    model = None
@app.route('/generate_frames', methods=['POST'])
def generate_frames():
    cap = cv2.VideoCapture(0)
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

    hands = mp_hands.Hands(static_image_mode=True, min_detection_confidence=0.3)

    labels_dict = {0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9'}

    while True:
        data_aux = []
        x_ = []
        y_ = []

        ret, frame = cap.read()
        if not ret:
            break

        H, W, _ = frame.shape
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = hands.process(frame_rgb)
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())

            # Landmark processing
            for i in range(len(hand_landmarks.landmark)):
                x = hand_landmarks.landmark[i].x
                y = hand_landmarks.landmark[i].y

                x_.append(x)
                y_.append(y)

            for i in range(len(hand_landmarks.landmark)):
                x = hand_landmarks.landmark[i].x
                y = hand_landmarks.landmark[i].y
                data_aux.append(x - min(x_))
                data_aux.append(y - min(y_))

            x1 = int(min(x_) * W) - 10
            y1 = int(min(y_) * H) - 10
            x2 = int(max(x_) * W) - 10
            y2 = int(max(y_) * H) - 10

            try:
                prediction = model.predict([np.asarray(data_aux)])
                predicted_character = labels_dict[int(prediction[0])]
                response_data = {'characters': predicted_character}
                print("Predicted character : ",predicted_character)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), 4)
                cv2.putText(frame, predicted_character, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3,cv2.LINE_AA)
                flash(f'Predicted Character is {predicted_character}.', category='success')
            except Exception as e:
                   pass

          

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)  
