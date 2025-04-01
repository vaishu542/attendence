import datetime
import os
import time
import PySimpleGUI as sg
import cv2
import pandas as pd

attendance_saved = False
lecture_started = False
lecture_duration = None
lecture_end_time = None
extra_clockout_time = None
current_session_name = None  # New variable to track session name

def get_session_name():
    global current_session_name
    layout = [
        [sg.Text("Enter Session Name")],
        [sg.Input("", key='-SESSION-', size=(20, 1))],
        [sg.Button("OK"), sg.Button("Cancel")]
    ]
    
    window = sg.Window("Session Name", layout, modal=True)
    
    while True:
        event, values = window.read()
        
        if event in (sg.WIN_CLOSED, "Cancel"):
            current_session_name = None
            break
        elif event == "OK":
            current_session_name = values['-SESSION-']
            if current_session_name.strip():
                window.close()
                return current_session_name
            sg.popup_error("Please enter a valid session name.")
    
    window.close()
    return None

def validate_duration_input(event, values, window):
    text = values['-DURATION-']
    text = ''.join(filter(str.isdigit, text))
    
    if len(text) > 6:
        text = text[:6]
    
    formatted = ':'.join([text[i:i+2] for i in range(0, len(text), 2)])
    window['-DURATION-'].update(formatted)

def get_lecture_duration():
    global lecture_duration, current_session_name
    
    # Ensure session name is set
    if not current_session_name:
        current_session_name = get_session_name()
        if not current_session_name:
            return None
    
    layout = [[sg.Text(f"Session: {current_session_name}")],
              [sg.Text("Enter Lecture Duration (HH:MM:SS)")],
              [sg.Input("", key='-DURATION-', size=(10, 1), enable_events=True)],
              [sg.Button("OK"), sg.Button("Cancel")]]
    
    window = sg.Window("Lecture Duration", layout, modal=True)
    duration = None
    
    while True:
        event, values = window.read()
        
        if event in (sg.WIN_CLOSED, "Cancel"):
            break
        elif event == "OK":
            duration = values['-DURATION-']
            if len(duration) == 8 and duration.count(':') == 2:
                window.close()
                return duration
            sg.popup_error("Please enter a valid duration in HH:MM:SS format.")
        elif event == "-DURATION-":
            validate_duration_input(event, values, window)
    
    window.close()
    return duration

def calculate_end_times(start_time, duration):
    FMT = "%H:%M:%S"
    end_time = (datetime.datetime.strptime(start_time, FMT) + datetime.timedelta(
        hours=int(duration.split(":")[0]),
        minutes=int(duration.split(":")[1]),
        seconds=int(duration.split(":")[2])
    )).strftime(FMT)
    extra_time = (datetime.datetime.strptime(end_time, FMT) + datetime.timedelta(minutes=2)).strftime(FMT)
    return end_time, extra_time

def get_attendance_file():
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    return f"Attendance{os.sep}Attendance_{date}.csv"

def recognize_attendance():
    global attendance_saved, lecture_started, lecture_duration, lecture_end_time, extra_clockout_time, current_session_name

    sg.theme('DarkGrey5')
    
    if not lecture_started:
        current_session_name = get_session_name()
        if not current_session_name:
            return
        
        lecture_duration = get_lecture_duration()
        if not lecture_duration:
            return
        
        start_time = datetime.datetime.now().strftime("%H:%M:%S")
        lecture_end_time, extra_clockout_time = calculate_end_times(start_time, lecture_duration)
        lecture_started = True
    
    layout = [  
        [sg.Text(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}", key='_date_', font=('Helvetica', 16)),
        sg.Text(f"Session: {current_session_name}", key='_session_', font=('Helvetica', 16), text_color='blue'),
        sg.Text(f"Time: {datetime.datetime.now().strftime('%H:%M:%S')}", key='_time_', font=('Helvetica', 16)),
        sg.Text(f"Lecture Duration: {lecture_duration}", key='_lecture_duration_', font=('Helvetica', 16), text_color='yellow'),
        sg.Text(f"Lecture Ends At: {lecture_end_time}", key='_lecture_end_', font=('Helvetica', 16), text_color='red')],
        
        [sg.Image(filename='', key='image')],
        [sg.Text("Recognized Name: ", font=('Helvetica', 16)), sg.Text("", key="_name_", font=('Helvetica', 16), text_color="green")],

        [sg.Button("Clock IN", key="ClockIN", size=(15, 2), font=('Helvetica', 14), button_color=('white', '#4CAF50')), 
        sg.Button("Clock OUT", key="ClockOUT", size=(15, 2), font=('Helvetica', 14), button_color=('white', '#FF5733'), visible=False),
        sg.Button("Save Attendance", key="SaveAttendance", size=(20, 2), font=('Helvetica', 14), button_color=('white', 'blue')),
        sg.Button("Back", key="Back", size=(15, 2), font=('Helvetica', 14), button_color=('white', 'red'))] 
    ]
    
    window = sg.Window('Mark Attendance', layout, location=(350, 75))
    
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("TrainingImageLabel" + os.sep + "Trainner.yml")
    df = pd.read_csv("StudentDetails" + os.sep + "StudentDetails.csv")
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    while True:
        event, values = window.read(timeout=1000)
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        window['_time_'].update(f"Time: {current_time}")
        window['_lecture_end_'].update(f"Lecture Ends At: {lecture_end_time}")
        
        if current_time >= lecture_end_time and current_time < extra_clockout_time:
            window['ClockIN'].update(visible=False)
            window['ClockOUT'].update(visible=True)
        elif current_time >= extra_clockout_time:
            sg.popup_timed("Clock-out time has ended. Attendance is closed.")
            lecture_started = False
            lecture_duration = None
            break
        
        ret, im = cam.read()
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        faces = faceCascade.detectMultiScale(gray, 1.2, 5)
        recognized_name = "Unknown"
        Id = None

        for (x, y, w, h) in faces:
            cv2.rectangle(im, (x, y), (x+w, y+h), (10, 159, 255), 2)
            
            Id, conf = recognizer.predict(gray[y:y+h, x:x+w])

            recognized_name = df.loc[df['Id'] == Id, 'Name'].values[0] if conf < 100 else "Unknown"
            cv2.putText(im, recognized_name, (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        window["_name_"].update(recognized_name)
        imgbytes = cv2.imencode(".png", im)[1].tobytes()
        window["image"].update(data=imgbytes)
        
        if event == "Back":
            if not attendance_saved:
                if sg.PopupYesNo("Attendance not saved. Do you want to save?") == "Yes":
                    save_attendance(recognized_name, Id)
                    sg.popup_timed("Attendance Saved Successfully!")
            break
        
        elif event == "SaveAttendance":
            save_attendance(recognized_name, Id)
            attendance_saved = True
            sg.popup_timed("Attendance Saved Successfully!")

        elif event == "ClockIN":
            if recognized_name == "Unknown":
                sg.popup_timed("Cannot clock in: Face not recognized!")
            else:
                clock_in(recognized_name, Id)

        elif event == "ClockOUT":
            if recognized_name == "Unknown":
                sg.popup_timed("Cannot clock out: Face not recognized!")
            else:
                clock_out(recognized_name,Id)
    
    cam.release()
    cv2.destroyAllWindows()
    window.close()

def save_attendance(recognized_name, Id):
    attendance_file = get_attendance_file()
    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    
    if not os.path.exists("Attendance"):
        os.makedirs("Attendance")

    new_entry = f"{Id},{recognized_name},{current_time},-,-,Present\n"

    # Read existing attendance file
    if os.path.exists(attendance_file):
        with open(attendance_file, "r") as file:
            lines = file.readlines()
    else:
        lines = []

    # Check if session exists, if not, add it
    session_header = f"{current_session_name} Session\n"
    if session_header not in lines:
        lines.append("\n" + session_header)
        lines.append("Id,Name,Clock IN Time,Clock OUT Time,Duration,Status\n")

    # Append new entry
    lines.append(new_entry)

    with open(attendance_file, "w") as file:
        file.writelines(lines)


def clock_in(recognized_name, Id):
    attendance_file = get_attendance_file()
    current_time = datetime.datetime.now().strftime('%H:%M:%S')

    # Ensure the directory exists
    if not os.path.exists("Attendance"):
        os.makedirs("Attendance")

    # Ensure the file exists before reading
    file_exists = os.path.exists(attendance_file)
    
    if not file_exists:
        with open(attendance_file, "w") as file:
            file.write(f"{current_session_name} Session\n")
            file.write("Id,Name,Clock IN Time,Clock OUT Time,Duration,Status\n")

    with open(attendance_file, "r") as file:
        lines = file.readlines()

    session_header = f"{current_session_name} Session\n"
    session_index = None

    # Find the session's start index
    for i, line in enumerate(lines):
        if line.strip() == session_header.strip():
            session_index = i
            break

    # If session header is not found, append it at the end
    if session_index is None:
        lines.append(session_header)
        lines.append("Id,Name,Clock IN Time,Clock OUT Time,Duration,Status\n")
        session_index = len(lines) - 2  # Adjust index after adding new session header

    # Check if user has already clocked in
    for i in range(session_index + 2, len(lines)):
        if lines[i].startswith(f"{Id},"):
            sg.popup_timed(f"{recognized_name} has already clocked in for this session!")
            return

    # Insert new entry correctly
    new_entry = f"{Id},{recognized_name},{current_time},-,-,Present\n"
    insert_index = session_index + 2 if session_index + 2 < len(lines) else len(lines)
    lines.insert(insert_index, new_entry)

    with open(attendance_file, "w") as file:
        file.writelines(lines)

    sg.popup_timed(f"{recognized_name} Clocked In Successfully!")


def clock_out(recognized_name,Id):
    attendance_file = get_attendance_file()
    current_time = datetime.datetime.now().strftime('%H:%M:%S')

    # Ensure the directory and file exist
    if not os.path.exists("Attendance"):
        os.makedirs("Attendance")

    if not os.path.exists(attendance_file):
        sg.popup_timed(f"No attendance record found for today.")
        return

    with open(attendance_file, "r") as file:
        lines = file.readlines()

    session_header = f"{current_session_name} Session\n"
    session_index = None
    record_index = None

    # Find the session start index
    for i, line in enumerate(lines):
        if line.strip() == session_header.strip():
            session_index = i
            break

    if session_index is not None:
        for i in range(session_index + 2, len(lines)):  # Start after session header and table headers
            record_data = lines[i].strip().split(",")
            if record_data[0] == str(Id) and record_data[3] == "-":  # Check if ID matches and Clock OUT is pending
                record_index = i
                break


    if record_index is None:
        sg.popup_timed(f"{recognized_name} has not clocked in for this session!")
        return

    clock_in_time = lines[record_index].split(",")[2]
    duration = str(datetime.datetime.strptime(current_time, '%H:%M:%S') - 
                   datetime.datetime.strptime(clock_in_time, '%H:%M:%S'))

    # Update the record with Clock OUT time and duration
    record_data = lines[record_index].strip().split(",")
    record_data[3] = current_time  # Update Clock OUT Time
    record_data[4] = duration  # Update Duration
    lines[record_index] = ",".join(record_data) + "\n"

    with open(attendance_file, "w") as file:
        file.writelines(lines)

    sg.popup_timed(f"{recognized_name} Clocked Out Successfully!")


def main():
    recognize_attendance()

if __name__ == "__main__":
    main()