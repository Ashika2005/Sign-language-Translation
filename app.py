
import os
import pickle
import uuid
from collections import Counter, deque

import cv2
import mediapipe as mp
import nltk
import numpy as np
import torch
from flask import (Flask, Response, flash, g, jsonify, redirect,
                   render_template, request, session, url_for)
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from deep_translator import GoogleTranslator
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import TreebankWordTokenizer
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


app = Flask(__name__)

# Secret key for session management
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = ''
app.config['MYSQL_PORT'] = 3006
mysql = MySQL(app)

# ==================================================================
# Forms
# ==================================================================
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[Length(min=4, max=25), DataRequired()])
    email = StringField('Email', validators=[Email(), DataRequired()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[Email(), DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# ==================================================================
# Helper Functions
# ==================================================================
def process_text_for_animation(text):
    tokenizer = TreebankWordTokenizer()
    words = tokenizer.tokenize(text.lower())
    tagged = nltk.pos_tag(words)

    tense = {
        "future": len([w for w in tagged if w[1] == "MD"]),
        "present": len([w for w in tagged if w[1] in ["VBP", "VBZ", "VBG"]]),
        "past": len([w for w in tagged if w[1] in ["VBD", "VBN"]]),
        "present_continuous": len([w for w in tagged if w[1] == "VBG"])
    }

    stop_words = set(stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()
    filtered_text = []

    for w, p in zip(words, tagged):
        if w not in stop_words:
            if p[1] in ['VBG', 'VBD', 'VBZ', 'VBN', 'NN']:
                filtered_text.append(lemmatizer.lemmatize(w, pos='v'))
            elif p[1] in ['JJ', 'JJR', 'JJS', 'RBR', 'RBS']:
                filtered_text.append(lemmatizer.lemmatize(w, pos='a'))
            else:
                filtered_text.append(lemmatizer.lemmatize(w))

    words = ["Me" if w == "i" else w for w in filtered_text]
    
    probable_tense = max(tense, key=tense.get) if tense else None

    if probable_tense == "past" and tense["past"] >= 1:
        words.insert(0, "Before")
    elif probable_tense == "future" and tense["future"] >= 1:
        if "will" not in words:
            words.insert(0, "Will")
    elif probable_tense == "present" and tense["present_continuous"] >= 1:
        words.insert(0, "Now")

    final_text = []
    for w in words:
        path = os.path.join('static', f"{w.capitalize()}.mp4")
        if not os.path.exists(path):
            final_text.extend(list(w))
        else:
            final_text.append(w.capitalize())

    return final_text

# ==================================================================
# Routes
# ==================================================================
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

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT id, username, email, password FROM users WHERE email = %s", [email])

        if result > 0:
            data = cur.fetchone()
            user_id, username, stored_email, stored_password = data

            if check_password_hash(stored_password, password_candidate):
                session['logged_in'] = True
                session['username'] = username
                session['email'] = stored_email
                session['user_id'] = user_id
                
                # Session and Login History
                session_id = str(uuid.uuid4())
                cur.execute("INSERT INTO sessions (session_id, user_id, created_at, last_active) VALUES (%s, %s, NOW(), NOW())", (session_id, user_id))
                ip_address = request.remote_addr
                cur.execute("INSERT INTO user_login_history (user_id, ip_address, successful) VALUES (%s, %s, %s)", (user_id, ip_address, 1))
                cur.execute("INSERT INTO logs (user_id, activity_type, description) VALUES (%s, %s, %s)", (user_id, 'login', f'{username} logged in'))
                mysql.connection.commit()
                session['session_id'] = session_id
                
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
        cur.execute("INSERT INTO logs (user_id, activity_type, description) VALUES (%s, %s, %s)", (user_id, 'logout', f'{username} logged out'))
        ip_address = request.remote_addr
        cur.execute("INSERT INTO user_login_history (user_id, ip_address, successful) VALUES (%s, %s, %s)", (user_id, ip_address, 0))
        mysql.connection.commit()
        cur.close()

    if 'session_id' in session:
        session_id = session['session_id']
        cur = mysql.connection.cursor()
        cur.execute("UPDATE sessions SET last_active = NOW() WHERE session_id = %s", (session_id,))
        mysql.connection.commit()
        cur.close()
        
    session.clear()
    flash('You have been successfully logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'email' not in session:
        flash('Please log in to view your profile.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, email, profile_picture FROM users WHERE email = %s", [session['email']])
    user = cur.fetchone()
    cur.close()

    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('logout'))

    user_data = {
        'id': user[0],
        'username': user[1],
        'email': user[2],
        'profile_picture': user[3]
    }

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        profile_picture = request.files.get('profile_picture')

        cur = mysql.connection.cursor()
        cur.execute("UPDATE users SET username = %s, email = %s WHERE email = %s", [username, email, session['email']])
        mysql.connection.commit()

        if profile_picture:
            image_filename = secure_filename(profile_picture.filename)
            profile_picture.save(os.path.join('static/uploads', image_filename))
            cur.execute("UPDATE users SET profile_picture = %s WHERE email = %s", [f'uploads/{image_filename}', session['email']])
            mysql.connection.commit()

        cur.close()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

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
            selected_theme = request.form.get('theme')
            session['theme'] = selected_theme

            cur = mysql.connection.cursor()
            cur.execute("SELECT settings_user_id FROM settings WHERE settings_user_id = (SELECT id FROM users WHERE email = %s)", [session['email']])
            existing_settings = cur.fetchone()

            if existing_settings:
                cur.execute("UPDATE settings SET dark_mode = %s WHERE settings_user_id = %s", [selected_theme, existing_settings[0]])
            else:
                cur.execute("INSERT INTO settings (settings_user_id, dark_mode) VALUES ((SELECT id FROM users WHERE email = %s), %s)", [session['email'], selected_theme])
            mysql.connection.commit()
            cur.close()

            flash(f'Theme changed to {selected_theme}!', 'success')
            return redirect(url_for('settings'))
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT dark_mode FROM settings WHERE settings_user_id = (SELECT id FROM users WHERE email = %s)", [session['email']])
        theme = cur.fetchone()
        cur.close()

        current_theme = theme[0] if theme else session.get('theme', 'default')
        return render_template('settings.html', username=session['username'], theme=current_theme)

    flash('Please log in first', 'danger')
    return redirect(url_for('login'))

@app.before_request
def before_request():
    g.language = session.get('language', 'en')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'username' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        feedback_text = request.form.get('feedback')
        rating = request.form.get('rating')
        
        if not feedback_text:
            flash('Feedback cannot be empty!', 'danger')
            return redirect(url_for('feedback'))
        
        if rating == '':
            rating = None
            
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO feedback(feedback_user_id, message, rating) VALUES(%s, %s, %s)", (session['user_id'], feedback_text, rating))
        mysql.connection.commit()
        cur.close()

        flash('Your feedback has been submitted!', 'success')
        return redirect(url_for('feedback'))

    return render_template('feedback.html', username=session['username'])

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if 'username' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        message = request.form['message']
        username = session['username']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if user:
            user_id = user[0]
            cur.execute("INSERT INTO contact (customer_id, message) VALUES (%s, %s)", (user_id, message))
            mysql.connection.commit()
            flash('Your message has been sent!', 'success')
        else:
            flash('User not found. Please log in again.', 'danger')

        cur.close()
        return redirect(url_for('contact'))

    return render_template('contact.html', username=session['username'])

@app.route('/animation_home')
def animation_home():
    return render_template('animation_home.html')

@app.route('/animation', methods=['GET', 'POST'])
def animation():
    if 'username' not in session:
        flash('Please log in to use the animation feature.', 'danger')
        return redirect(url_for('login'))

    text = ""
    words = []

    if request.method == 'POST':
        text = request.form.get('sen', '')
        words = process_text_for_animation(text)

    return render_template('animation.html', words=words, text=text)

# ==================================================================
# Machine Learning / Video Stream Routes
# ==================================================================
try:
    model_dict = pickle.load(open('./model.p', 'rb'))
    model = model_dict['model']
except Exception as e:
    print("Error loading the model:", e)
    model = None

@app.route('/generate_frames')
def generate_frames():
    cap = cv2.VideoCapture(0)
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

    hands = mp_hands.Hands(static_image_mode=False, min_detection_confidence=0.3)
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
                    mp_drawing_styles.get_default_hand_connections_style()
                )

                for landmark in hand_landmarks.landmark:
                    x_.append(landmark.x)
                    y_.append(landmark.y)

                for landmark in hand_landmarks.landmark:
                    data_aux.append(landmark.x - min(x_))
                    data_aux.append(landmark.y - min(y_))

                x1 = int(min(x_) * W) - 10
                y1 = int(min(y_) * H) - 10
                x2 = int(max(x_) * W) - 10
                y2 = int(max(y_) * H) - 10

                try:
                    prediction = model.predict([np.asarray(data_aux)])
                    predicted_character = labels_dict[int(prediction[0])]
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), 4)
                    cv2.putText(frame, predicted_character, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3, cv2.LINE_AA)
                except Exception as e:
                    pass

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ==================================================================
# API Routes
# ==================================================================
LANG_MAP = {
    'en-US': 'en',
    'hi-IN': 'hi',
    'bn-IN': 'bn',
    'te-IN': 'te',
    'mr-IN': 'mr',
    'ta-IN': 'ta',
    'gu-IN': 'gu',
    'kn-IN': 'kn',
    'ml-IN': 'ml'
}

# In app.py, find and replace the entire @app.route('/translate', ...) function

@app.route('/translate', methods=['POST'])
def translate_text():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    text_to_translate = data.get('text')
    # Get the target language from the request, default to 'en' if not provided
    target_language = data.get('target_lang', 'en') 
    
    if not text_to_translate.strip():
        return jsonify({'translated_text': ''}) 

    try:
        # Use the dynamic target_language variable
        translated_text = GoogleTranslator(source='auto', target=target_language).translate(text_to_translate)
        print(f"Translated '{text_to_translate}' to '{target_language}': '{translated_text}'")
        return jsonify({'translated_text': translated_text})
        
    except Exception as e:
        print(f"Translation Error with deep-translator: {e}")
        return jsonify({'error': 'Translation failed'}), 500


# ==================================================================
# Main Execution
# ==================================================================
if __name__ == '__main__':
    app.run(debug=True)