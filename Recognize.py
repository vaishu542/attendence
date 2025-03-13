import datetime
import os
import time
import PySimpleGUI as sg
import cv2
import pandas as pd

attendance_saved = False  # Track if attendance is saved
lecture_started = False  # Track if lecture has started
lecture_duration = None  # Store lecture duration in memory

def get_lecture_duration():
    """Prompt user for lecture duration if not already set"""
    global lecture_duration
    if lecture_duration is None:
        lecture_duration = sg.popup_get_text('Enter Lecture Duration (HH:MM:SS)', 'Lecture Duration')
    return lecture_duration

def get_lecture_end_time(start_time, duration):
    """Calculate lecture end time based on duration"""
    FMT = "%H:%M:%S"
    end_time = (datetime.datetime.strptime(start_time, FMT) + datetime.timedelta(
        hours=int(duration.split(":")[0]), 
        minutes=int(duration.split(":")[1]), 
        seconds=int(duration.split(":")[2])
    )).strftime(FMT)
    return end_time

def get_attendance_file():
    """Generate a daily attendance file name"""
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    return "Attendance" + os.sep + f"Attendance_{date}.csv"

def recognize_attendence():
    global attendance_saved, lecture_started, lecture_duration

    sg.theme('DarkGrey5')

    # Get lecture details
    lecture_duration = get_lecture_duration()
    start_time = datetime.datetime.now().strftime("%H:%M:%S")
    end_time = get_lecture_end_time(start_time, lecture_duration)
    lecture_started = True

    layout = [  
        [sg.Text(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}", key='_date_', font=('Helvetica', 16)),
         sg.Text(f"Time: {datetime.datetime.now().strftime('%H:%M:%S')}", key='_time_', font=('Helvetica', 16)),
         sg.Text(f"Lecture Duration: {lecture_duration}", key='_lecture_duration_', font=('Helvetica', 16), text_color='yellow'),
         sg.Text(f"Lecture Ends At: {end_time}", key='_lecture_end_time_', font=('Helvetica', 16), text_color='red')],
        
        [sg.Image(filename='', key='image')],
        [sg.Text("Recognized Name: ", font=('Helvetica', 16)), sg.Text("", key="_name_", font=('Helvetica', 16), text_color="green")],

        [sg.Button("Clock IN", key="ClockIN", size=(15, 2), font=('Helvetica', 14), button_color=('white', '#4CAF50')), 
         sg.Button("Clock OUT", key="ClockOUT", size=(15, 2), font=('Helvetica', 14), button_color=('white', '#FF5733'), visible=False),
         sg.Button("Save Attendance", key="SaveAttendance", size=(20, 2), font=('Helvetica', 14), button_color=('white', 'blue')),
         sg.Button("Back", key="Back", size=(15, 2), font=('Helvetica', 14), button_color=('white', 'red'))] 
    ]
    
    window = sg.Window('Mark Attendance', layout, auto_size_buttons=False, element_justification='c', location=(350, 75))
    
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("TrainingImageLabel"+os.sep+"Trainner.yml")
    faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    df = pd.read_csv("StudentDetails"+os.sep+"StudentDetails.csv")
    font = cv2.FONT_HERSHEY_SIMPLEX

    cam = cv2.VideoCapture(2, cv2.CAP_DSHOW)
    cam.set(3, 640)
    cam.set(4, 480)

    minW = 0.1 * cam.get(3)
    minH = 0.1 * cam.get(4)

    recognized_name = "Unknown"

    while True:
        event, values = window.read(timeout=1000)  # Refresh every second
        current_time = datetime.datetime.now().strftime("%H:%M:%S")

        # Update UI Elements
        window['_date_'].update(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}")
        window['_time_'].update(f"Time: {current_time}")
        window['_lecture_end_time_'].update(f"Lecture Ends At: {end_time}")

        # Show Clock OUT only after lecture ends
        if current_time >= end_time:
            window['ClockIN'].update(visible=False)
            window['ClockOUT'].update(visible=True)

        # Face Recognition Logic
        ret, im = cam.read()
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        faces = faceCascade.detectMultiScale(gray, 1.2, 5, minSize=(int(minW), int(minH)), flags=cv2.CASCADE_SCALE_IMAGE)

        recognized_name = "Unknown"
        for (x, y, w, h) in faces:
            cv2.rectangle(im, (x, y), (x+w, y+h), (10, 159, 255), 2)
            Id, conf = recognizer.predict(gray[y:y+h, x:x+w])

            if conf < 100:
                recognized_name = df.loc[df['Id'] == Id, 'Name'].values[0]
            else:
                recognized_name = "Unknown"

            cv2.putText(im, recognized_name, (x+5, y-5), font, 1, (255, 255, 255), 2)

        window["_name_"].update(recognized_name)

        imgbytes = cv2.imencode(".png", im)[1].tobytes()
        window["image"].update(data=imgbytes)

        attendance_file = get_attendance_file()

        # Handle Button Events
        if event == "Back":
            if not attendance_saved:
                save_option = sg.PopupYesNo("Attendance not saved. Do you want to save before exiting?")
                if save_option == "Yes":
                    attendance_saved = True
                    sg.popup_timed("Attendance Saved Successfully!")
                else:
                    continue  # Stay on the same page
            else:
                cam.release()
                cv2.destroyAllWindows()
                window.close()
                break  # Exit the page only after clicking Back again

        elif event == "SaveAttendance":
            attendance_saved = True
            sg.popup_timed("Attendance Saved Successfully!")

        elif event == "ClockIN":
            if recognized_name == "Unknown":
                sg.popup_error("Face not recognized! Cannot Clock IN.")
            else:
                check = sg.PopupYesNo(f'{recognized_name}, are you clocking in?')
                if check == 'Yes':
                    ts = time.time()
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                    timeStamp = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')

                    df_attendance = pd.DataFrame([[Id, recognized_name, date, timeStamp, '-', '-', '-']], 
                                                 columns=["Id", "Name", "Date", "Clock IN Time", "Clock OUT Time", "Duration", "Status"])
                    
                    # Save to daily file
                    file_exists = os.path.isfile(attendance_file)
                    df_attendance.to_csv(attendance_file, mode='a', header=not file_exists, index=False)

                    sg.popup_timed(f'{recognized_name} Clocked In Successfully!')

        elif event == "ClockOUT":
            if recognized_name == "Unknown":
                sg.popup_error("Face not recognized! Cannot Clock OUT.")
            else:
                df_attendance = pd.read_csv(attendance_file)
                user_index = df_attendance[df_attendance['Name'] == recognized_name].index
                if user_index.empty:
                    sg.popup_error(f"{recognized_name}, you must Clock IN first before Clock OUT.")
                else:
                    check = sg.PopupYesNo(f'{recognized_name}, are you clocking out?')
                    if check == 'Yes':
                        ts = time.time()
                        timeStamp = datetime.datetime.now().strftime("%H:%M:%S")

                        df_attendance.at[user_index[-1], 'Clock OUT Time'] = timeStamp
                        df_attendance.to_csv(attendance_file, index=False)
                        sg.popup_timed(f"{recognized_name} Clocked Out Successfully!")

    cam.release()
    cv2.destroyAllWindows()
    os.system('cls')
