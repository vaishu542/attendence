import PySimpleGUI as sg
import csv

def vcsv():
    filename = sg.popup_get_file('Get required file', no_window=True, file_types=(('CSV Files', '*.csv'),))
    if not filename:
        return

    data = []
    session_data = []
    header = []

    with open(filename, 'r') as infile:
        reader = csv.reader(infile)
        for row in reader:
            if row and row[0].startswith("Session:"):
                if session_data:
                    data.append([])  # Add spacing between sessions
                    data.extend(session_data)
                    session_data = []
                data.append([row[0], '', '', '', '', ''])  # Add session title
            elif row and row[0] == "Id":
                header = row  # Store header row
            elif row:
                session_data.append(row)

        if session_data:
            data.append([])
            data.extend(session_data)
    
    layout = [
        [sg.Text('Attendance Report', font='Helvetica 20', justification='center', pad=(0, 10))],
        [sg.Table(
            values=data,
            headings=header,
            col_widths=[5, 15, 10, 15, 15, 10],
            auto_size_columns=False,
            justification='center',
            background_color='#303030',
            text_color='white',
            alternating_row_color='#505050',
            display_row_numbers=False,
            num_rows=min(25, len(data))
        )],
        [sg.Button('Back', font=('Arial', 14, 'bold'), size=(15, 1), pad=(0, 25))]
    ]
    
    window = sg.Window('Attendance', layout, element_justification='c', location=(200, 150))
    while True:
        event, values = window.read()
        if event in ('Back', sg.WIN_CLOSED):
            window.close()
            break
