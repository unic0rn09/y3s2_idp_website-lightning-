# # import sklearn # 🚀 JETSON TLS FIX: Must be imported absolutely first
# # import torch   # 🚀 JETSON TLS FIX: Must be imported second

# import os
# os.environ["TRANSFORMERS_NO_TORCHCODEC"] = "1"

# import json 
# import tempfile
# import subprocess
# import time
# import traceback
# from datetime import datetime
# from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, session 
# from flask_sqlalchemy import SQLAlchemy
# from werkzeug.security import generate_password_hash, check_password_hash

# # 🚀 IMPORT FROM YOUR NEW AI ENGINE FILE
# # In app.py (Line 11)
# from ai_engine import (
#     transcribe_wav, 
#     run_post_consultation_pipeline, 
#     clear_old_audio, 
#     _to_safe_visit_id, 
#     INSTANCE_FOLDER, 
#     TARGET_SR,
#     process_clinical_tasks,
#     translate_rojak
# )
# app = Flask(__name__)
# app.secret_key = "super_secret_key"

# # Configure SQLite Database
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scribe.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# db = SQLAlchemy(app)

# # Database Models
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)
#     password_hash = db.Column(db.String(256), nullable=False)
#     role = db.Column(db.String(20), nullable=False)
#     status = db.Column(db.String(20), default='offline')
#     room = db.Column(db.String(20), nullable=True)

# class Patient(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     ic = db.Column(db.String(20), nullable=False)
#     age = db.Column(db.String(20))
#     room = db.Column(db.String(20))
#     symptoms = db.Column(db.Text)
#     priority = db.Column(db.Boolean, default=False)
#     status = db.Column(db.String(20), default='Waiting') # Waiting, Consulting, Draft, Completed
#     date_added = db.Column(db.DateTime, default=datetime.utcnow)
#     bp = db.Column(db.String(20), default="-")
#     hr = db.Column(db.String(20), default="-")
#     temp = db.Column(db.String(20), default="-")
#     rr = db.Column(db.String(20), default="-") 
    
#     # --- NEW: Personal & Emergency Contact Fields ---
#     phone = db.Column(db.String(50), default="")
#     email = db.Column(db.String(120), default="")
#     address = db.Column(db.Text, default="")
#     emergency_name = db.Column(db.String(100), default="")
#     emergency_phone = db.Column(db.String(50), default="")
#     emergency_relation = db.Column(db.String(50), default="")
    
#     # Clinical Draft & Report Fields
#     transcription = db.Column(db.Text, default="")
#     cc = db.Column(db.Text, default="")
#     hpi = db.Column(db.Text, default="")
#     pmh = db.Column(db.Text, default="")
#     meds = db.Column(db.Text, default="")
#     allergies = db.Column(db.Text, default="")
    
#     sh_occupation = db.Column(db.String(255), default="")
#     sh_living = db.Column(db.String(255), default="")
#     sh_smoking = db.Column(db.String(255), default="")
#     sh_alcohol = db.Column(db.String(255), default="")
#     sh_activity = db.Column(db.String(255), default="")
#     sh_diet = db.Column(db.String(255), default="")
#     sh_sleep = db.Column(db.String(255), default="")
#     sh_others = db.Column(db.String(255), default="")


# # --- DATA COLLECTION HELPER ---
# def save_patient_data_to_folder(patient):
#     """Saves patient information into a structured folder hierarchy"""
#     # DO NOT save data if it is the Mock Test Patient
#     if patient.ic == '999999-99-9999':
#         return

#     # 1. Start inside the local 'instance' folder
#     base_dir = os.path.join("instance", "patient_records")
    
#     # 2. Extract the exact date the patient visited
#     date_visited = patient.date_added.strftime("%Y-%m-%d")
    
#     # 3. Create the nested directory: instance/patient_records/IC/Date/
#     target_dir = os.path.join(base_dir, patient.ic, date_visited)
#     os.makedirs(target_dir, exist_ok=True)
    
#     # 4. Simply name it as the final clinical note
#     filename = "final_clinical_note.json"
#     file_path = os.path.join(target_dir, filename)
        
#     # 5. Structure the data to be saved
#     archive_data = {
#         "metadata": {
#             "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
#             "room": patient.room,
#             "status": patient.status
#         },
#         "patient": {"name": patient.name, "ic": patient.ic, "age": patient.age},
#         "vitals": {"bp": patient.bp, "hr": patient.hr, "temp": patient.temp, "rr": patient.rr},
#         "clinical_notes": {
#             "cc": patient.cc, "hpi": patient.hpi, "pmh": patient.pmh, 
#             "meds": patient.meds, "allergies": patient.allergies,
#             "social": {
#                 "occupation": patient.sh_occupation, 
#                 "living": patient.sh_living, 
#                 "smoking": patient.sh_smoking, 
#                 "alcohol": patient.sh_alcohol,
#                 "activity": patient.sh_activity,
#                 "diet": patient.sh_diet,
#                 "sleep": patient.sh_sleep,
#                 "others": patient.sh_others
#             }
#         },
#         "raw_transcription": patient.transcription
#     }
    
#     # 6. Save the file into the new folder structure
#     with open(file_path, 'w') as f:
#         json.dump(archive_data, f, indent=4)
# #--------------------------------------------------------#

# def get_rooms_data():
#     rooms = []
#     for i in range(1, 6):
#         room_num_str = str(i)
#         doc = User.query.filter_by(role='doctor', room=room_num_str).first()
        
#         # Exclude the test patient (IC: 999999-99-9999) from nurse dashboard entirely
#         patients_query = Patient.query.filter(
#             Patient.room == room_num_str, 
#             Patient.status.in_(['Waiting', 'Draft']),
#             Patient.ic != '999999-99-9999' # Filter out mock data
#         ).order_by(Patient.priority.desc(), Patient.id.asc()).all()
        
#         patient_list = [{
#             "id": p.id, "name": p.name, "ic": p.ic, "symptoms": p.symptoms, 
#             "priority": p.priority, "status": p.status, "time": p.date_added.strftime('%H:%M'),
#             "bp": p.bp, "hr": p.hr, "temp": p.temp, "rr": p.rr
#         } for p in patients_query]
        
#         if doc:
#             status = "Waiting" if patient_list else "Available"
#             rooms.append({"id": f"Room {i}", "room_num": room_num_str, "doctor": doc.name, "doctor_email": doc.email, "status": status, "patients": patient_list, "active": True})
#         else:
#             rooms.append({"id": f"Room {i}", "room_num": room_num_str, "doctor": "-", "doctor_email": "", "status": "Not Available", "patients": [], "active": False})
#     return rooms

# @app.route('/')
# def login(): return render_template('login.html')

# @app.route('/login', methods=['POST'])
# def do_login():
#     email = request.form.get('email')
#     password = request.form.get('password')
#     user = User.query.filter_by(email=email).first()

#     if user and check_password_hash(user.password_hash, password) and user.role == request.form.get('role'):
#         session['user_id'] = user.id 
#         if user.role == 'nurse':
#             return redirect(url_for('nurse_dashboard'))
#         elif user.role == 'doctor':
#             selected_room = request.form.get('room')
#             if selected_room:
#                 user.room = selected_room
#                 user.status = 'online'
#                 db.session.commit()
#             return redirect(url_for('doctor_dashboard'))
#     return "Invalid email or password", 401

# @app.route('/logout')
# def logout():
#     session.pop('user_id', None)
#     return redirect(url_for('login'))

# # --- NURSE ROUTES ----------
# @app.route('/register_patient', methods=['POST'])
# def register_patient():
#     room = request.form.get('room')
#     active_rooms = [r for r in get_rooms_data() if r['active']]
#     if not active_rooms: return redirect(request.referrer)
#     if room == 'auto' or not room: room = min(active_rooms, key=lambda r: len(r['patients']))['room_num']
            
#     new_patient = Patient(
#         name=request.form.get('name'), ic=request.form.get('ic'), age=request.form.get('age'), 
#         room=room, symptoms=request.form.get('symptoms'), 
#         priority=True if request.form.get('priority') == 'on' else False,
#         bp=request.form.get('bp') or "-", hr=request.form.get('hr') or "-", 
#         temp=request.form.get('temp') or "-", rr=request.form.get('rr') or "-"
#     )
#     db.session.add(new_patient)
#     db.session.commit()
#     return redirect(request.referrer)

# @app.route('/nurse/dashboard')
# def nurse_dashboard(): 
#     # Get today's date string to match completed patients
#     today_str = datetime.now().strftime('%Y-%m-%d')
    
#     # Fetch all real patients (excluding the automated test patient)
#     all_patients = Patient.query.filter(Patient.ic != '999999-99-9999').all()
    
#     # --- FAKE DATA FOR RED & YELLOW ZONES ---
#     fake_red_waiting = 8
#     fake_red_completed = 15
#     fake_yellow_waiting = 12
#     fake_yellow_completed = 23
    
#     # --- REAL DATA FOR GREEN ZONE ---
#     real_green_waiting = 0
#     real_green_completed = 0
    
#     for p in all_patients:
#         is_today = p.date_added.strftime('%Y-%m-%d') == today_str
#         is_waiting = p.status in ['Waiting', 'Consulting', 'Draft']
        
#         # We assign all non-priority patients to the Green Zone
#         if not p.priority:
#             if is_waiting:
#                 real_green_waiting += 1
#             elif p.status == 'Completed' and is_today:
#                 real_green_completed += 1

#     # Helper function to calculate progress bar percentages
#     def calc_pct(waiting, completed):
#         total = waiting + completed
#         return int((waiting / total) * 100) if total > 0 else 0

#     # Build the final stats dictionary to send to the HTML
#     stats = {
#         'red_waiting': fake_red_waiting,
#         'red_completed': fake_red_completed,
#         'red_pct': calc_pct(fake_red_waiting, fake_red_completed),
        
#         'yellow_waiting': fake_yellow_waiting,
#         'yellow_completed': fake_yellow_completed,
#         'yellow_pct': calc_pct(fake_yellow_waiting, fake_yellow_completed),
        
#         'green_waiting': real_green_waiting,
#         'green_completed': real_green_completed,
#         'green_pct': calc_pct(real_green_waiting, real_green_completed),
        
#         # Total waiting adds the fake Red/Yellow to the real Green queue
#         'total_waiting': fake_red_waiting + fake_yellow_waiting + real_green_waiting
#     }

#     return render_template('nurse_dashboard.html', rooms=get_rooms_data(), stats=stats)

# @app.route('/nurse/registration')
# def patient_registration(): 
#     # Exclude test patient from nurse history
#     history = Patient.query.filter(Patient.status=='Completed', Patient.ic != '999999-99-9999').order_by(Patient.id.desc()).all()
#     return render_template('patient_registration.html', rooms=get_rooms_data(), history=history)

# @app.route('/nurse/rooms')
# def all_rooms(): return render_template('all_rooms.html', rooms=get_rooms_data())

# @app.route('/nurse/history')
# def patient_history(): 
#     # Exclude test patient from global history
#     history = Patient.query.filter(Patient.ic != '999999-99-9999').order_by(Patient.id.desc()).all()
#     return render_template('patient_history.html', history=history, rooms=get_rooms_data())

# @app.route('/delete_patient/<patient_id>', methods=['POST'])
# def delete_patient(patient_id):
#     # Find the patient in the database
#     patient = Patient.query.get_or_404(patient_id)
    
#     # Delete the record and save changes
#     db.session.delete(patient)
#     db.session.commit()
    
#     # Refresh the page automatically so the patient disappears from the table
#     return redirect(request.referrer)

# @app.route('/edit_patient_full/<int:patient_id>', methods=['GET', 'POST'])
# def edit_patient_full(patient_id):
#     # Fetch the patient from the database, return 404 if not found
#     patient = Patient.query.get_or_404(patient_id)
    
#     # If the nurse clicks "Save Changes" (POST request)
#     if request.method == 'POST':
#         # 1. Update Basic Details
#         patient.name = request.form.get('name', patient.name)
#         patient.ic = request.form.get('ic', patient.ic)
#         patient.age = request.form.get('age', patient.age)
        
#         # 2. Update Contact & Address
#         patient.phone = request.form.get('phone', '')
#         patient.email = request.form.get('email', '')
#         patient.address = request.form.get('address', '')
        
#         # 3. Update Emergency Contact
#         patient.emergency_name = request.form.get('emergency_name', '')
#         patient.emergency_phone = request.form.get('emergency_phone', '')
#         patient.emergency_relation = request.form.get('emergency_relation', '')
        
#         # Save to database
#         db.session.commit()
        
#         # Send them back to the history page
#         return redirect(url_for('patient_history'))
        
#     # If they are just opening the page (GET request)
#     return render_template('edit_patient_full.html', patient=patient)

# @app.route('/nurse/statistics')
# def nurse_statistics(): 
#     if 'user_id' not in session: return redirect(url_for('login'))
    
#     # 1. DATE MEMORY
#     req_date = request.args.get('date')
#     if req_date:
#         session['stats_date'] = req_date
#         selected_date_str = req_date
#     else:
#         selected_date_str = session.get('stats_date', datetime.now().strftime('%Y-%m-%d'))
    
#     # 2. Fetch ALL real patients 
#     all_patients = Patient.query.order_by(Patient.date_added.desc()).all()
    
#     # --- FAKE DATA FOR RED & YELLOW ZONES ---
#     fake_red_waiting = 8
#     fake_red_completed = 15
#     fake_yellow_waiting = 12
#     fake_yellow_completed = 23
    
#     # --- REAL DATA FOR GREEN ZONE ---
#     real_green_waiting = 0
#     real_green_completed = 0
#     green_patients = []
#     green_hourly = [0] * 10 
    
#     for p in all_patients:
#         p_date_str = p.date_added.strftime('%Y-%m-%d')
        
#         if p_date_str == selected_date_str:
#             # Add all patients to the list (since you're only working in Green Zone)
#             green_patients.append(p) 
            
#             is_waiting = p.status in ['Waiting', 'Consulting', 'Draft']
#             if is_waiting:
#                 real_green_waiting += 1
#             elif p.status == 'Completed':
#                 real_green_completed += 1
                
#             hour = p.date_added.hour
#             if 7 <= hour <= 16:
#                 green_hourly[hour - 7] += 1

#     def calc_pct(waiting, completed):
#         total = waiting + completed
#         return int((waiting / total) * 100) if total > 0 else 0

#     stats = {
#         'red_waiting': fake_red_waiting,
#         'red_completed': fake_red_completed,
#         'yellow_waiting': fake_yellow_waiting,
#         'yellow_completed': fake_yellow_completed,
#         'green_waiting': real_green_waiting,
#         'green_completed': real_green_completed,
#         'green_pct': calc_pct(real_green_waiting, real_green_completed),
#         'green_hourly': green_hourly, 
#         'total_waiting': fake_red_waiting + fake_yellow_waiting + real_green_waiting,
#         'selected_date': selected_date_str 
#     }

#     return render_template('statistics.html', stats=stats, green_patients=green_patients)

# # --- DOCTOR ROUTES -------

# # 🚀 THE REAL-TIME AUDIO ROUTE 
# @app.route('/api/transcribe', methods=['POST'])
# def api_transcribe():
#     audio_file = request.files.get('audio')
#     patient_id = request.form.get('patient_id', 'unknown')
#     chunk_index = request.form.get('chunk_index', '0')
    
#     safe_vid = _to_safe_visit_id(patient_id)
#     # The temporary chunk WAV
#     final_wav_path = os.path.join(INSTANCE_FOLDER, f"visit_{safe_vid}_chunk{chunk_index}.wav")
#     # 🚀 The Master file needed for Pyannote Diarization
#     full_audio_path = os.path.join(INSTANCE_FOLDER, f"visit_{safe_vid}_full.wav")
    
#     with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
#         audio_file.save(temp_webm.name)
#         temp_webm_path = temp_webm.name

#     try:
#         if os.path.getsize(temp_webm_path) < 5000:
#             return jsonify({'text': ''}), 200

#         # Convert chunk to WAV
#         subprocess.run(['ffmpeg', '-y', '-i', temp_webm_path, '-ar', str(TARGET_SR), '-ac', '1', final_wav_path], 
#                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
#         # 🚀 BUILD THE FULL AUDIO FILE: Append this chunk to the master file
#         if not os.path.exists(full_audio_path):
#             # First chunk: just rename it to full.wav
#             subprocess.run(['ffmpeg', '-y', '-i', final_wav_path, '-c', 'copy', full_audio_path], check=True)
#         else:
#             # Subsequent chunks: append to existing master
#             temp_combined = os.path.join(INSTANCE_FOLDER, f"visit_{safe_vid}_temp.wav")
#             # We use the 'concat' protocol for speed on the Jetson
#             subprocess.run([
#                 'ffmpeg', '-y', '-i', f'concat:{full_audio_path}|{final_wav_path}', 
#                 '-c', 'copy', temp_combined
#             ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
#             os.replace(temp_combined, full_audio_path)

#         # Calls the function from ai_engine.py
#         text = transcribe_wav(final_wav_path)
#         return jsonify({'text': text}), 200

#     except Exception as e:
#         print(f"⚠️ Transcription Error: {e}")
#         return jsonify({'text': ''}), 200
#     finally:
#         if os.path.exists(temp_webm_path): os.remove(temp_webm_path)
        
# # 🚀 THE FAST-TRACK FINALIZATION ROUTE
# @app.route('/api/process_final_diarization', methods=['POST'])
# def process_final_diarization():
#     data = request.json
#     patient_id = data.get("patient_id")
#     patient = Patient.query.get_or_404(patient_id)

#     print("⏳ Waiting 3 seconds for final audio chunks to finish uploading...")
#     time.sleep(3)

#     try:
#         # Run the pipeline (passing the ID so it finds the chunks)
#         results = run_post_consultation_pipeline(patient_id)
        
#         # 1. Fill the 'Raw Transcription' box
#         patient.transcription = results.get("labeled_transcript", "")
        
#         # 2. Fill the specific medical boxes (Untouched)
#         notes = results.get("medical_notes", {})
#         patient.cc = notes.get("chief_complaint", "")
#         patient.hpi = notes.get("hpi", "")
#         patient.pmh = notes.get("pmh", "")
#         patient.meds = notes.get("meds", "")
#         patient.allergies = notes.get("allergies", "None reported")
#         patient.sh_others = notes.get("social", "")
        
#         patient.status = 'Draft'
#         db.session.commit()
        
#         # Clean up old audio
#         clear_old_audio(str(patient.id))
        
#         return jsonify({"status": "success"})

#     except Exception as e:
#         print("\n\n❌ DIARIZATION CRASHED! See error below:")
#         traceback.print_exc()
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500

# @app.route('/doctor/dashboard')
# def doctor_dashboard():
#     if 'user_id' not in session: return redirect(url_for('login'))
#     doctor = db.session.get(User, session.get('user_id'))
    
#     # --- AUTO RESET MOCK PATIENT ---
#     # Secretly wipe the mock patient data clean when the doctor returns to dashboard 
#     # so it does not permanently stay in the database as "Completed"
#     test_p = Patient.query.filter_by(ic='999999-99-9999').first()
#     if test_p and test_p.status == 'Completed':
#         test_p.status = 'Waiting'
#         test_p.transcription = ""
#         test_p.cc = ""
#         test_p.hpi = ""
#         test_p.pmh = ""
#         test_p.meds = ""
#         test_p.allergies = ""
#         test_p.sh_occupation = ""
#         test_p.sh_living = ""
#         test_p.sh_smoking = ""
#         test_p.sh_alcohol = ""
#         test_p.sh_activity = ""
#         test_p.sh_diet = ""
#         test_p.sh_sleep = ""
#         test_p.sh_others = ""
#         db.session.commit()

#     queue = Patient.query.filter(Patient.room==doctor.room, Patient.status.in_(['Waiting', 'Consulting', 'Draft'])).order_by(Patient.priority.desc(), Patient.id.asc()).all()
    
#     today_str = datetime.now().strftime('%Y-%m-%d')
#     all_completed = Patient.query.filter_by(room=doctor.room, status='Completed').order_by(Patient.id.desc()).all()
#     # Exclude test patient from "Completed Today"
#     completed_today = [p for p in all_completed if p.date_added.strftime('%Y-%m-%d') == today_str and p.ic != '999999-99-9999']
    
#     return render_template('doctor_dashboard.html', doctor=doctor, queue=queue, completed_today=completed_today)

# @app.route('/doctor/toggle_status', methods=['POST'])
# def toggle_status():
#     if 'user_id' in session:
#         doctor = User.query.get(session['user_id'])
#         doctor.status = 'online' if doctor.status == 'offline' else 'offline'
#         db.session.commit()
#     return redirect(request.referrer)

# #changes here#
# @app.route('/doctor/consult/<patient_id>')
# def live_consultation(patient_id):
#     if 'user_id' not in session: return redirect(url_for('login'))
#     patient = Patient.query.get_or_404(patient_id)
#     patient.status = 'Consulting'
#     db.session.commit()
    
#     # Clean old audio using the imported function
#     clear_old_audio(str(patient.id))
    
#     doctor_user = db.session.get(User, session.get('user_id'))
#     return render_template('live_consultation_session.html', patient=patient, doctor=doctor_user)
# #changes here#
# @app.route('/doctor/cancel_live/<patient_id>')
# def cancel_live(patient_id):
#     patient = Patient.query.get_or_404(patient_id)
#     patient.status = 'Waiting'
#     db.session.commit()
#     clear_old_audio(str(patient.id))
#     return redirect(url_for('doctor_dashboard'))

# # @app.route('/doctor/finish_live/<patient_id>', methods=['POST'])
# # def finish_live(patient_id):
# #     patient = Patient.query.get_or_404(patient_id)
# #     patient.transcription = request.form.get('transcription', '')
# #     patient.status = 'Draft'
# #     db.session.commit()
# #     return redirect(url_for('consultation_summary', patient_id=patient.id))

# @app.route('/doctor/summary/<patient_id>')
# def consultation_summary(patient_id):
#     if 'user_id' not in session: return redirect(url_for('login'))
    
#     current_patient = Patient.query.get_or_404(patient_id)
#     doctor = User.query.get(session['user_id'])
    
#     # --- FETCH PAST REPORTS ---
#     # Match by IC, ensure status is 'Completed', and exclude the current ongoing visit
#     # .asc() ensures the oldest dates appear first as page 1
#     past_records = Patient.query.filter(
#         Patient.ic == current_patient.ic,
#         Patient.status == 'Completed',
#         Patient.id != current_patient.id
#     ).order_by(Patient.date_added.asc()).all()
    
#     past_reports = []
#     for record in past_records:
#         past_reports.append({
#             'date': record.date_added.strftime('%Y-%m-%d'),
#             # Note: Since the Patient table doesn't explicitly save the historical doctor's name,
#             # we assign it to the current doctor or default to a generic string.
#             'doctor': 'E.M.M.A.S Records', 
#             'cc': record.cc,
#             'hpi': record.hpi,
#             'pmh': record.pmh,
#             'meds': record.meds,
#             'allergies': record.allergies
#         })
        
#     return render_template('consultation_summary.html', 
#                            patient=current_patient, 
#                            doctor=doctor, 
#                            past_reports=past_reports)

# @app.route('/doctor/save_draft/<patient_id>', methods=['POST'])
# def save_draft(patient_id):
#     patient = Patient.query.get_or_404(patient_id)
#     patient.transcription = request.form.get('transcription', '')
#     patient.cc = request.form.get('cc', '')
#     patient.hpi = request.form.get('hpi', '')
#     patient.pmh = request.form.get('pmh', '')
#     patient.meds = request.form.get('meds', '')
#     patient.allergies = request.form.get('allergies', '')
    
#     patient.sh_occupation = request.form.get('sh_occupation', '')
#     patient.sh_living = request.form.get('sh_living', '')
#     patient.sh_smoking = request.form.get('sh_smoking', '')
#     patient.sh_alcohol = request.form.get('sh_alcohol', '')
#     patient.sh_activity = request.form.get('sh_activity', '')
#     patient.sh_diet = request.form.get('sh_diet', '')
#     patient.sh_sleep = request.form.get('sh_sleep', '')
#     patient.sh_others = request.form.get('sh_others', '')
    
#     patient.status = 'Draft'
#     db.session.commit()
#     return redirect(url_for('doctor_dashboard'))

# @app.route('/doctor/generate_report/<patient_id>', methods=['POST'])
# def generate_report(patient_id):
#     patient = Patient.query.get_or_404(patient_id)
#     patient.cc = request.form.get('cc', '')
#     patient.hpi = request.form.get('hpi', '')
#     patient.pmh = request.form.get('pmh', '')
#     patient.meds = request.form.get('meds', '')
#     patient.allergies = request.form.get('allergies', '')
    
#     patient.sh_occupation = request.form.get('sh_occupation', '')
#     patient.sh_living = request.form.get('sh_living', '')
#     patient.sh_smoking = request.form.get('sh_smoking', '')
#     patient.sh_alcohol = request.form.get('sh_alcohol', '')
#     patient.sh_activity = request.form.get('sh_activity', '')
#     patient.sh_diet = request.form.get('sh_diet', '')
#     patient.sh_sleep = request.form.get('sh_sleep', '')
#     patient.sh_others = request.form.get('sh_others', '')
    
#     patient.status = 'Completed'
#     # Trigger Folder-based Data Collection (Test patient is blocked inside this function)
#     save_patient_data_to_folder(patient)
    

#     db.session.commit()
#     return redirect(url_for('final_medical_note', patient_id=patient.id))

# @app.route('/doctor/report/<patient_id>')
# def final_medical_note(patient_id):
#     if 'user_id' not in session: return redirect(url_for('login'))
    
#     current_patient = Patient.query.get_or_404(patient_id)
#     doctor = User.query.get(session['user_id'])
    
#     # ✅ FIX 1: Grab the source from the URL so we can hide the dashboard button
#     source = request.args.get('source', 'consultation')
    
#     # Fetch ALL completed reports for this patient's IC (The entire book)
#     all_records = Patient.query.filter(
#         Patient.ic == current_patient.ic,
#         Patient.status == 'Completed'
#     ).order_by(Patient.date_added.asc()).all()
    
#     past_reports = []
#     # Find which page number corresponds to the specific report the doctor clicked
#     target_page_index = 1 
    
#     for index, record in enumerate(all_records, start=1):
#         if record.id == current_patient.id:
#             target_page_index = index
            
#         past_reports.append({
#             'id': record.id,
#             'date': record.date_added.strftime('%Y-%m-%d'),
#             'time': record.date_added.strftime('%H:%M'),
#             'doctor': doctor.name, 
#             'room': record.room,
#             'cc': record.cc,
#             'hpi': record.hpi,
#             'pmh': record.pmh,
#             'meds': record.meds,
#             'allergies': record.allergies,
            
#             # ✅ FIX 2: Added Social History and Vitals so they don't appear blank!
#             'sh_occupation': record.sh_occupation,
#             'sh_living': record.sh_living,
#             'sh_smoking': record.sh_smoking,
#             'sh_alcohol': record.sh_alcohol,
#             'sh_activity': record.sh_activity,
#             'sh_diet': record.sh_diet,
#             'sh_sleep': record.sh_sleep,
#             'temp': record.temp,
#             'hr': record.hr,
#             'rr': record.rr,
#             'bp': record.bp
#         })

#     return render_template('final_medical_note.html', 
#                            patient=current_patient, 
#                            doctor=doctor, 
#                            past_reports=past_reports,
#                            target_page=target_page_index,
#                            source=source) # ✅ FIX 3: Passed the source to the HTML

# @app.route('/doctor/history')
# def consultation_history():
#     if 'user_id' not in session: return redirect(url_for('login'))
#     doctor = User.query.get(session['user_id'])
#     # Exclude test patient from doctor history
#     history = Patient.query.filter(Patient.status=='Completed', Patient.ic != '999999-99-9999').order_by(Patient.id.desc()).all()
#     return render_template('consultation_history.html', history=history, doctor=doctor)

# @app.route('/doctor/mock_consultation')
# def mock_consultation():
#     if 'user_id' not in session: return redirect(url_for('login'))
#     return render_template('mock_consultation.html', doctor=User.query.get(session['user_id']))

# # ==========================================
# #OPEN AI ROUTE
# # ==========================================
# @app.route('/api/translate', methods=['POST'])
# def api_translate():
#     # Optional security check
#     # if session.get("role") != "doctor":
#     #     return jsonify({"success": False, "error": "Unauthorized"}), 403
        
#     data = request.json
#     raw_text = data.get("text", "")
    
#     if not raw_text:
#         return jsonify({"success": False, "error": "No text provided"}), 400
        
#     # Calls your new GPT translation function
#     translated_text = translate_rojak(raw_text)
    
#     if translated_text:
#         return jsonify({"success": True, "translation": translated_text})
#     else:
#         return jsonify({"success": False, "error": "Translation failed. Please try again."}), 500

# @app.route('/api/structure', methods=['POST'])
# def api_structure():
#     data = request.get_json()
#     text = data.get('text', '')
#     if not text:
#         return jsonify({})
    
#     # Calls your GPT-4o-mini structuring mode
#     _, _, structured = process_clinical_tasks(text, mode="structure")
#     return jsonify(structured)
# #==================================================================================
# #-------help and feedback route------------
# @app.route('/help_feedback')
# def help_feedback():
#     return render_template('help_feedback.html')

# @app.route('/submit_feedback', methods=['POST'])
# def submit_feedback():
#     topic = request.form.get('topic')
#     message = request.form.get('message')
    
#     # Send a flash message back to the user to confirm success
#     flash("Thank you! Your feedback has been sent to the development team.", "success")
#     return redirect(url_for('help_feedback'))
# #--------------------------------------------

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#         if not User.query.filter_by(email='nurse@test.com').first():
#             db.session.add(User(name="Nurse Joy", email='nurse@test.com', password_hash=generate_password_hash('nurse123'), role='nurse'))
#         if not User.query.filter_by(email='doctor@test.com').first():
#             db.session.add(User(name="Lim", email='doctor@test.com', password_hash=generate_password_hash('doctor123'), role='doctor', status='online', room='1'))
#         db.session.commit()
        
#         # ==============================================================
#         # ⬇️ TEST PATIENT CREATION TOGGLE ⬇️
#         # Uncomment the lines below to spawn the test patient on startup.
#         # Leave them commented out to run the app normally.
#         # ==============================================================
#         test_patient = Patient.query.filter_by(ic='999999-99-9999').first()
#         if not test_patient:
#             test_patient = Patient(name="Auto Test Patient", ic="999999-99-9999", age="25", room="1", symptoms="Mock Test", status='Waiting')
#             db.session.add(test_patient)
#         else:
#             test_patient.status = 'Waiting'
#         db.session.commit()
#         # ==============================================================
        
#     app.run(host='0.0.0.0', port=5000, debug=True)
# import sklearn # 🚀 JETSON TLS FIX: Must be imported absolutely first
# import torch   # 🚀 JETSON TLS FIX: Must be imported second

# import sklearn # 🚀 JETSON TLS FIX: Must be imported absolutely first
# import torch   # 🚀 JETSON TLS FIX: Must be imported second

# import sklearn # 🚀 JETSON TLS FIX: Must be imported absolutely first
# import torch   # 🚀 JETSON TLS FIX: Must be imported second

import os
os.environ["TRANSFORMERS_NO_TORCHCODEC"] = "1"

import json 
import tempfile
import subprocess
import time
import traceback
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# 🚀 IMPORT FROM YOUR NEW AI ENGINE FILE
from ai_engine import (
    transcribe_wav, 
    run_post_consultation_pipeline, 
    clear_old_audio, 
    _to_safe_visit_id, 
    INSTANCE_FOLDER, 
    TARGET_SR,
    process_clinical_tasks,
    translate_rojak
)
app = Flask(__name__)
app.secret_key = "super_secret_key"

# Configure SQLite Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scribe.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ============================================
# HARDCODED AVAILABLE ROOMS — edit this list
# ============================================
AVAILABLE_ROOMS = ['1', '2', '3', '4', '5']

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='offline')
    room = db.Column(db.String(20), nullable=True)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ic = db.Column(db.String(20), nullable=False)
    age = db.Column(db.String(20))
    room = db.Column(db.String(20))
    symptoms = db.Column(db.Text)
    priority = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='Waiting') # Waiting, Consulting, Draft, Completed
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    bp = db.Column(db.String(20), default="-")
    hr = db.Column(db.String(20), default="-")
    temp = db.Column(db.String(20), default="-")
    rr = db.Column(db.String(20), default="-") 
    
    # --- NEW: Personal & Emergency Contact Fields ---
    phone = db.Column(db.String(50), default="")
    email = db.Column(db.String(120), default="")
    address = db.Column(db.Text, default="")
    emergency_name = db.Column(db.String(100), default="")
    emergency_phone = db.Column(db.String(50), default="")
    emergency_relation = db.Column(db.String(50), default="")
    
    # Clinical Draft & Report Fields
    transcription = db.Column(db.Text, default="")
    cc = db.Column(db.Text, default="")
    hpi = db.Column(db.Text, default="")
    pmh = db.Column(db.Text, default="")
    meds = db.Column(db.Text, default="")
    allergies = db.Column(db.Text, default="")
    
    sh_occupation = db.Column(db.String(255), default="")
    sh_living = db.Column(db.String(255), default="")
    sh_smoking = db.Column(db.String(255), default="")
    sh_alcohol = db.Column(db.String(255), default="")
    sh_activity = db.Column(db.String(255), default="")
    sh_diet = db.Column(db.String(255), default="")
    sh_sleep = db.Column(db.String(255), default="")
    sh_others = db.Column(db.String(255), default="")


# --- DATA COLLECTION HELPER ---
def save_patient_data_to_folder(patient):
    """Saves patient information into a structured folder hierarchy"""
    # DO NOT save data if it is the Mock Test Patient
    if patient.ic == '999999-99-9999':
        return

    # 1. Start inside the local 'instance' folder
    base_dir = os.path.join("instance", "patient_records")
    date_visited = patient.date_added.strftime("%Y-%m-%d")
    target_dir = os.path.join(base_dir, patient.ic, date_visited)
    os.makedirs(target_dir, exist_ok=True)
    
    filename = "final_clinical_note.json"
    file_path = os.path.join(target_dir, filename)
        
    archive_data = {
        "metadata": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            "room": patient.room,
            "status": patient.status
        },
        "patient": {"name": patient.name, "ic": patient.ic, "age": patient.age},
        "vitals": {"bp": patient.bp, "hr": patient.hr, "temp": patient.temp, "rr": patient.rr},
        "clinical_notes": {
            "cc": patient.cc, "hpi": patient.hpi, "pmh": patient.pmh, 
            "meds": patient.meds, "allergies": patient.allergies,
            "social": {
                "occupation": patient.sh_occupation, 
                "living": patient.sh_living, 
                "smoking": patient.sh_smoking, 
                "alcohol": patient.sh_alcohol,
                "activity": patient.sh_activity,
                "diet": patient.sh_diet,
                "sleep": patient.sh_sleep,
                "others": patient.sh_others
            }
        },
        "raw_transcription": patient.transcription
    }
    
    with open(file_path, 'w') as f:
        json.dump(archive_data, f, indent=4)
#--------------------------------------------------------#

def get_rooms_data():
    rooms = []
    for i in range(1, 6):
        room_num_str = str(i)
        doc = User.query.filter_by(role='doctor', room=room_num_str).first()
        
        # Exclude the test patient from nurse dashboard entirely
        patients_query = Patient.query.filter(
            Patient.room == room_num_str, 
            Patient.status.in_(['Waiting', 'Draft']),
            Patient.ic != '999999-99-9999' # Filter out mock data
        ).order_by(Patient.priority.desc(), Patient.id.asc()).all()
        
        patient_list = [{
            "id": p.id, "name": p.name, "ic": p.ic, "symptoms": p.symptoms, 
            "priority": p.priority, "status": p.status, "time": p.date_added.strftime('%H:%M'),
            "bp": p.bp, "hr": p.hr, "temp": p.temp, "rr": p.rr
        } for p in patients_query]
        
        if doc:
            # ✅ REQ 3: Incorporates Offline -> Online -> Waiting status lifecycle
            if doc.status == 'offline':
                status = "Offline"
            else:
                status = "Waiting" if patient_list else "Online"
                
            rooms.append({"id": f"Room {i}", "room_num": room_num_str, "doctor": doc.name, "doctor_email": doc.email, "status": status, "patients": patient_list, "active": True})
        else:
            rooms.append({"id": f"Room {i}", "room_num": room_num_str, "doctor": "-", "doctor_email": "", "status": "Not Available", "patients": [], "active": False})
    return rooms

@app.route('/')
def login():
    # ✅ REQ 2: Only empty rooms are available for the doctor to choose
    occupied_rooms = [u.room for u in User.query.filter(User.role == 'doctor', User.room != None).all()]
    return render_template('login.html', available_rooms=AVAILABLE_ROOMS, occupied_rooms=occupied_rooms)

@app.route('/login', methods=['POST'])
def do_login():
    email = request.form.get('email')
    password = request.form.get('password')
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password_hash, password) and user.role == request.form.get('role'):
        session['user_id'] = user.id
        session['user_name'] = user.name # ✅ REQ 5: Sets the name dynamically for frontend displays
        
        if user.role == 'nurse':
            return redirect(url_for('nurse_dashboard'))
            
        elif user.role == 'doctor':
            # ✅ REQ 4: Dr Lim exception - Always force Room 1 & Online
            if user.email == 'doctor@test.com':
                user.room = '1'
                user.status = 'online'
                db.session.commit()
            else:
                selected_room = request.form.get('room')
                if selected_room:
                    # Reject rooms not in the available list
                    if selected_room not in AVAILABLE_ROOMS:
                        return "Room not available", 400
                    # Reject rooms already occupied by another doctor
                    occupied = User.query.filter(User.role == 'doctor', User.room == selected_room, User.id != user.id).first()
                    if occupied:
                        return "Room already occupied by another doctor", 400
                    
                    # ✅ REQ 2 & 3: Lock the room to this doctor and set to online immediately
                    user.room = selected_room
                    user.status = 'online'
                    db.session.commit()
            return redirect(url_for('doctor_dashboard'))
    return "Invalid email or password", 401

@app.route('/logout')
def logout():
    # ✅ REQ 2: Releasing the room when a generic doctor logs out 
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        # Dr Lim keeps his room forever, everyone else loses it upon logout
        if user and user.role == 'doctor' and user.email != 'doctor@test.com':
            user.room = None
            user.status = 'offline'
            db.session.commit()
            
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('login'))

# --- NURSE ROUTES ----------
@app.route('/register_patient', methods=['POST'])
def register_patient():
    room = request.form.get('room')
    active_rooms = [r for r in get_rooms_data() if r['active']]
    if not active_rooms: return redirect(request.referrer)
    if room == 'auto' or not room: room = min(active_rooms, key=lambda r: len(r['patients']))['room_num']
            
    new_patient = Patient(
        name=request.form.get('name'), ic=request.form.get('ic'), age=request.form.get('age'), 
        room=room, symptoms=request.form.get('symptoms'), 
        priority=True if request.form.get('priority') == 'on' else False,
        bp=request.form.get('bp') or "-", hr=request.form.get('hr') or "-", 
        temp=request.form.get('temp') or "-", rr=request.form.get('rr') or "-"
    )
    db.session.add(new_patient)
    db.session.commit()
    return redirect(request.referrer)

@app.route('/nurse/dashboard')
def nurse_dashboard(): 
    today_str = datetime.now().strftime('%Y-%m-%d')
    all_patients = Patient.query.filter(Patient.ic != '999999-99-9999').all()
    
    fake_red_waiting = 8
    fake_red_completed = 15
    fake_yellow_waiting = 12
    fake_yellow_completed = 23
    
    real_green_waiting = 0
    real_green_completed = 0
    
    for p in all_patients:
        is_today = p.date_added.strftime('%Y-%m-%d') == today_str
        is_waiting = p.status in ['Waiting', 'Consulting', 'Draft']
        
        if not p.priority:
            if is_waiting:
                real_green_waiting += 1
            elif p.status == 'Completed' and is_today:
                real_green_completed += 1

    def calc_pct(waiting, completed):
        total = waiting + completed
        return int((waiting / total) * 100) if total > 0 else 0

    stats = {
        'red_waiting': fake_red_waiting,
        'red_completed': fake_red_completed,
        'red_pct': calc_pct(fake_red_waiting, fake_red_completed),
        'yellow_waiting': fake_yellow_waiting,
        'yellow_completed': fake_yellow_completed,
        'yellow_pct': calc_pct(fake_yellow_waiting, fake_yellow_completed),
        'green_waiting': real_green_waiting,
        'green_completed': real_green_completed,
        'green_pct': calc_pct(real_green_waiting, real_green_completed),
        'total_waiting': fake_red_waiting + fake_yellow_waiting + real_green_waiting
    }

    nurse_user = db.session.get(User, session.get('user_id'))
    return render_template('nurse_dashboard.html', rooms=get_rooms_data(), stats=stats, nurse=nurse_user)

@app.route('/nurse/registration')
def patient_registration(): 
    history = Patient.query.filter(Patient.status=='Completed', Patient.ic != '999999-99-9999').order_by(Patient.id.desc()).all()
    nurse_user = db.session.get(User, session.get('user_id'))
    return render_template('patient_registration.html', rooms=get_rooms_data(), history=history, nurse=nurse_user)

@app.route('/nurse/rooms')
def all_rooms(): 
    nurse_user = db.session.get(User, session.get('user_id'))
    return render_template('all_rooms.html', rooms=get_rooms_data(), nurse=nurse_user)

@app.route('/nurse/history')
def patient_history(): 
    history = Patient.query.filter(Patient.ic != '999999-99-9999').order_by(Patient.id.desc()).all()
    nurse_user = db.session.get(User, session.get('user_id'))
    return render_template('patient_history.html', history=history, rooms=get_rooms_data(), nurse=nurse_user)

@app.route('/delete_patient/<patient_id>', methods=['POST'])
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    return redirect(request.referrer)

@app.route('/edit_patient_full/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient_full(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient.name = request.form.get('name', patient.name)
        patient.ic = request.form.get('ic', patient.ic)
        patient.age = request.form.get('age', patient.age)
        
        patient.phone = request.form.get('phone', '')
        patient.email = request.form.get('email', '')
        patient.address = request.form.get('address', '')
        
        patient.emergency_name = request.form.get('emergency_name', '')
        patient.emergency_phone = request.form.get('emergency_phone', '')
        patient.emergency_relation = request.form.get('emergency_relation', '')
        
        db.session.commit()
        return redirect(url_for('patient_history'))
        
    nurse_user = db.session.get(User, session.get('user_id'))
    return render_template('edit_patient_full.html', patient=patient, nurse=nurse_user)

@app.route('/nurse/statistics')
def nurse_statistics(): 
    if 'user_id' not in session: return redirect(url_for('login'))
    
    req_date = request.args.get('date')
    if req_date:
        session['stats_date'] = req_date
        selected_date_str = req_date
    else:
        selected_date_str = session.get('stats_date', datetime.now().strftime('%Y-%m-%d'))
    
    all_patients = Patient.query.order_by(Patient.date_added.desc()).all()
    
    fake_red_waiting = 8
    fake_red_completed = 15
    fake_yellow_waiting = 12
    fake_yellow_completed = 23
    real_green_waiting = 0
    real_green_completed = 0
    green_patients = []
    green_hourly = [0] * 10 
    
    for p in all_patients:
        p_date_str = p.date_added.strftime('%Y-%m-%d')
        if p_date_str == selected_date_str:
            green_patients.append(p) 
            is_waiting = p.status in ['Waiting', 'Consulting', 'Draft']
            if is_waiting:
                real_green_waiting += 1
            elif p.status == 'Completed':
                real_green_completed += 1
                
            hour = p.date_added.hour
            if 7 <= hour <= 16:
                green_hourly[hour - 7] += 1

    def calc_pct(waiting, completed):
        total = waiting + completed
        return int((waiting / total) * 100) if total > 0 else 0

    stats = {
        'red_waiting': fake_red_waiting,
        'red_completed': fake_red_completed,
        'yellow_waiting': fake_yellow_waiting,
        'yellow_completed': fake_yellow_completed,
        'green_waiting': real_green_waiting,
        'green_completed': real_green_completed,
        'green_pct': calc_pct(real_green_waiting, real_green_completed),
        'green_hourly': green_hourly, 
        'total_waiting': fake_red_waiting + fake_yellow_waiting + real_green_waiting,
        'selected_date': selected_date_str 
    }

    nurse_user = db.session.get(User, session.get('user_id'))
    return render_template('statistics.html', stats=stats, green_patients=green_patients, nurse=nurse_user)


# --- DOCTOR ROUTES -------
@app.route('/api/transcribe', methods=['POST'])
def api_transcribe():
    audio_file = request.files.get('audio')
    patient_id = request.form.get('patient_id', 'unknown')
    chunk_index = request.form.get('chunk_index', '0')
    
    safe_vid = _to_safe_visit_id(patient_id)
    final_wav_path = os.path.join(INSTANCE_FOLDER, f"visit_{safe_vid}_chunk{chunk_index}.wav")
    full_audio_path = os.path.join(INSTANCE_FOLDER, f"visit_{safe_vid}_full.wav")
    
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
        audio_file.save(temp_webm.name)
        temp_webm_path = temp_webm.name

    try:
        if os.path.getsize(temp_webm_path) < 5000:
            return jsonify({'text': ''}), 200

        subprocess.run(['ffmpeg', '-y', '-i', temp_webm_path, '-ar', str(TARGET_SR), '-ac', '1', final_wav_path], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        if not os.path.exists(full_audio_path):
            subprocess.run(['ffmpeg', '-y', '-i', final_wav_path, '-c', 'copy', full_audio_path], check=True)
        else:
            temp_combined = os.path.join(INSTANCE_FOLDER, f"visit_{safe_vid}_temp.wav")
            subprocess.run([
                'ffmpeg', '-y', '-i', f'concat:{full_audio_path}|{final_wav_path}', 
                '-c', 'copy', temp_combined
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            os.replace(temp_combined, full_audio_path)

        text = transcribe_wav(final_wav_path)
        return jsonify({'text': text}), 200

    except Exception as e:
        print(f"⚠️ Transcription Error: {e}")
        return jsonify({'text': ''}), 200
    finally:
        if os.path.exists(temp_webm_path): os.remove(temp_webm_path)
        
@app.route('/api/process_final_diarization', methods=['POST'])
def process_final_diarization():
    data = request.json
    patient_id = data.get("patient_id")
    patient = Patient.query.get_or_404(patient_id)

    print("⏳ Waiting 3 seconds for final audio chunks to finish uploading...")
    time.sleep(3)

    try:
        results = run_post_consultation_pipeline(patient_id)
        
        patient.transcription = results.get("labeled_transcript", "")
        
        notes = results.get("medical_notes", {})
        patient.cc = notes.get("chief_complaint", "")
        patient.hpi = notes.get("hpi", "")
        patient.pmh = notes.get("pmh", "")
        patient.meds = notes.get("meds", "")
        patient.allergies = notes.get("allergies", "None reported")
        patient.sh_others = notes.get("social", "")
        
        patient.status = 'Draft'
        db.session.commit()
        clear_old_audio(str(patient.id))
        
        return jsonify({"status": "success"})

    except Exception as e:
        print("\n\n❌ DIARIZATION CRASHED! See error below:")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    doctor = db.session.get(User, session.get('user_id'))
    
    test_p = Patient.query.filter_by(ic='999999-99-9999').first()
    if test_p and test_p.status == 'Completed':
        test_p.status = 'Waiting'
        test_p.transcription = ""
        test_p.cc = ""
        test_p.hpi = ""
        test_p.pmh = ""
        test_p.meds = ""
        test_p.allergies = ""
        test_p.sh_occupation = ""
        test_p.sh_living = ""
        test_p.sh_smoking = ""
        test_p.sh_alcohol = ""
        test_p.sh_activity = ""
        test_p.sh_diet = ""
        test_p.sh_sleep = ""
        test_p.sh_others = ""
        db.session.commit()

    queue = Patient.query.filter(Patient.room==doctor.room, Patient.status.in_(['Waiting', 'Consulting', 'Draft'])).order_by(Patient.priority.desc(), Patient.id.asc()).all()
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    all_completed = Patient.query.filter_by(room=doctor.room, status='Completed').order_by(Patient.id.desc()).all()
    completed_today = [p for p in all_completed if p.date_added.strftime('%Y-%m-%d') == today_str and p.ic != '999999-99-9999']
    
    return render_template('doctor_dashboard.html', doctor=doctor, queue=queue, completed_today=completed_today)

@app.route('/doctor/toggle_status', methods=['POST'])
def toggle_status():
    if 'user_id' in session:
        doctor = User.query.get(session['user_id'])
        doctor.status = 'online' if doctor.status == 'offline' else 'offline'
        db.session.commit()
    return redirect(request.referrer)

@app.route('/doctor/consult/<patient_id>')
def live_consultation(patient_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    patient = Patient.query.get_or_404(patient_id)
    patient.status = 'Consulting'
    db.session.commit()
    clear_old_audio(str(patient.id))
    doctor_user = db.session.get(User, session.get('user_id'))
    return render_template('live_consultation_session.html', patient=patient, doctor=doctor_user)

@app.route('/doctor/cancel_live/<patient_id>')
def cancel_live(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.status = 'Waiting'
    db.session.commit()
    clear_old_audio(str(patient.id))
    return redirect(url_for('doctor_dashboard'))

@app.route('/doctor/summary/<patient_id>')
def consultation_summary(patient_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    current_patient = Patient.query.get_or_404(patient_id)
    doctor = User.query.get(session['user_id'])
    
    past_records = Patient.query.filter(
        Patient.ic == current_patient.ic,
        Patient.status == 'Completed',
        Patient.id != current_patient.id
    ).order_by(Patient.date_added.asc()).all()
    
    past_reports = []
    for record in past_records:
        past_reports.append({
            'date': record.date_added.strftime('%Y-%m-%d'),
            'doctor': 'E.M.M.A.S Records', 
            'cc': record.cc,
            'hpi': record.hpi,
            'pmh': record.pmh,
            'meds': record.meds,
            'allergies': record.allergies
        })
        
    return render_template('consultation_summary.html', 
                           patient=current_patient, 
                           doctor=doctor, 
                           past_reports=past_reports)

@app.route('/doctor/save_draft/<patient_id>', methods=['POST'])
def save_draft(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.transcription = request.form.get('transcription', '')
    patient.cc = request.form.get('cc', '')
    patient.hpi = request.form.get('hpi', '')
    patient.pmh = request.form.get('pmh', '')
    patient.meds = request.form.get('meds', '')
    patient.allergies = request.form.get('allergies', '')
    
    patient.sh_occupation = request.form.get('sh_occupation', '')
    patient.sh_living = request.form.get('sh_living', '')
    patient.sh_smoking = request.form.get('sh_smoking', '')
    patient.sh_alcohol = request.form.get('sh_alcohol', '')
    patient.sh_activity = request.form.get('sh_activity', '')
    patient.sh_diet = request.form.get('sh_diet', '')
    patient.sh_sleep = request.form.get('sh_sleep', '')
    patient.sh_others = request.form.get('sh_others', '')
    
    patient.status = 'Draft'
    db.session.commit()
    return redirect(url_for('doctor_dashboard'))

@app.route('/doctor/generate_report/<patient_id>', methods=['POST'])
def generate_report(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.cc = request.form.get('cc', '')
    patient.hpi = request.form.get('hpi', '')
    patient.pmh = request.form.get('pmh', '')
    patient.meds = request.form.get('meds', '')
    patient.allergies = request.form.get('allergies', '')
    
    patient.sh_occupation = request.form.get('sh_occupation', '')
    patient.sh_living = request.form.get('sh_living', '')
    patient.sh_smoking = request.form.get('sh_smoking', '')
    patient.sh_alcohol = request.form.get('sh_alcohol', '')
    patient.sh_activity = request.form.get('sh_activity', '')
    patient.sh_diet = request.form.get('sh_diet', '')
    patient.sh_sleep = request.form.get('sh_sleep', '')
    patient.sh_others = request.form.get('sh_others', '')
    
    patient.status = 'Completed'
    save_patient_data_to_folder(patient)
    
    db.session.commit()
    return redirect(url_for('final_medical_note', patient_id=patient.id))

@app.route('/doctor/report/<patient_id>')
def final_medical_note(patient_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    current_patient = Patient.query.get_or_404(patient_id)
    doctor = User.query.get(session['user_id'])
    
    source = request.args.get('source', 'consultation')
    
    all_records = Patient.query.filter(
        Patient.ic == current_patient.ic,
        Patient.status == 'Completed'
    ).order_by(Patient.date_added.asc()).all()
    
    past_reports = []
    target_page_index = 1 
    
    for index, record in enumerate(all_records, start=1):
        if record.id == current_patient.id:
            target_page_index = index
            
        past_reports.append({
            'id': record.id,
            'date': record.date_added.strftime('%Y-%m-%d'),
            'time': record.date_added.strftime('%H:%M'),
            'doctor': doctor.name, 
            'room': record.room,
            'cc': record.cc,
            'hpi': record.hpi,
            'pmh': record.pmh,
            'meds': record.meds,
            'allergies': record.allergies,
            
            'sh_occupation': record.sh_occupation,
            'sh_living': record.sh_living,
            'sh_smoking': record.sh_smoking,
            'sh_alcohol': record.sh_alcohol,
            'sh_activity': record.sh_activity,
            'sh_diet': record.sh_diet,
            'sh_sleep': record.sh_sleep,
            'temp': record.temp,
            'hr': record.hr,
            'rr': record.rr,
            'bp': record.bp
        })

    return render_template('final_medical_note.html', 
                           patient=current_patient, 
                           doctor=doctor, 
                           past_reports=past_reports,
                           target_page=target_page_index,
                           source=source)

@app.route('/doctor/history')
def consultation_history():
    if 'user_id' not in session: return redirect(url_for('login'))
    doctor = User.query.get(session['user_id'])
    history = Patient.query.filter(Patient.status=='Completed', Patient.ic != '999999-99-9999').order_by(Patient.id.desc()).all()
    return render_template('consultation_history.html', history=history, doctor=doctor)

@app.route('/doctor/mock_consultation')
def mock_consultation():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('mock_consultation.html', doctor=User.query.get(session['user_id']))

# ==========================================
#OPEN AI ROUTE
# ==========================================
@app.route('/api/translate', methods=['POST'])
def api_translate():
    data = request.json
    raw_text = data.get("text", "")
    
    if not raw_text:
        return jsonify({"success": False, "error": "No text provided"}), 400
        
    translated_text = translate_rojak(raw_text)
    
    if translated_text:
        return jsonify({"success": True, "translation": translated_text})
    else:
        return jsonify({"success": False, "error": "Translation failed. Please try again."}), 500

@app.route('/api/structure', methods=['POST'])
def api_structure():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({})
    
    _, _, structured = process_clinical_tasks(text, mode="structure")
    return jsonify(structured)

#-------help and feedback route------------
@app.route('/help_feedback')
def help_feedback():
    return render_template('help_feedback.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    topic = request.form.get('topic')
    message = request.form.get('message')
    flash("Thank you! Your feedback has been sent to the development team.", "success")
    return redirect(url_for('help_feedback'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # ==============================================================
        # ✅ REQ 1: ONLY NAME, EMAIL, PASSWORD, ROLE are hardcoded here.
        # ==============================================================
        demo_users = [
            {"name": "Nurse Joy", "email": "nurse@test.com", "password": "nurse123", "role": "nurse"},
            {"name": "Dr. Lim", "email": "doctor@test.com", "password": "doctor123", "role": "doctor"},
            {"name": "Dr. Smith", "email": "smith@test.com", "password": "smith123", "role": "doctor"},
            {"name": "Dr. Ali", "email": "ali@test.com", "password": "ali123", "role": "doctor"}
        ]

        for u in demo_users:
            if not User.query.filter_by(email=u['email']).first():
                new_user = User(
                    name=u['name'],
                    email=u['email'],
                    password_hash=generate_password_hash(u['password']),
                    role=u['role'],
                    status='offline',
                    room=None # Initialize with NO ROOM assigned
                )
                
                # ✅ REQ 4: Dr. Lim Exception (Force Room 1 & Online default)
                if u['email'] == 'doctor@test.com':
                    new_user.room = '1'
                    new_user.status = 'online'
                    
                db.session.add(new_user)
        
        db.session.commit()
        
        # ==============================================================
        # ⬇️ TEST PATIENT CREATION TOGGLE ⬇️
        # ==============================================================
        test_patient = Patient.query.filter_by(ic='999999-99-9999').first()
        if not test_patient:
            test_patient = Patient(name="Auto Test Patient", ic="999999-99-9999", age="25", room="1", symptoms="Mock Test", status='Waiting')
            db.session.add(test_patient)
        else:
            test_patient.status = 'Waiting'
        db.session.commit()
        
    app.run(host='0.0.0.0', port=5000, debug=True)