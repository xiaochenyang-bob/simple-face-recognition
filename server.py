import os
from flask import Flask, render_template, request, Response, session, redirect, url_for
import pymysql
import cv2
import face_recognition

#initialize flask object
app = Flask(__name__)

#initialize database
db = pymysql.connect("localhost","root","11433020Abc","TESTDB" )
cursor = db.cursor()

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
print(APP_ROOT)

#fetch data from database to do face-encoding
known_face_encodings = []
known_face_names = []

sql = "SELECT * FROM faces"
cursor.execute(sql)
results = cursor.fetchall()
for result in results:
    #for name
    known_face_names.append(result[1])
    #for encoding
    target = os.path.join(APP_ROOT, "images/")
    face_image = face_recognition.load_image_file("/".join([target, result[2]]))
    face_encoding = face_recognition.face_encodings(face_image)[0]
    known_face_encodings.append(face_encoding)

#username variable
class Username():
    name=None

username = Username()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    if username.name:
        return render_template("success.html", name=username.name)
    else:
        return render_template('scan.html')


def get_frame():
    with app.test_request_context():
        capture=cv2.VideoCapture(0)

        while True:
            retval, frame = capture.read()
            #facial recognition
            rgb_frame = frame[:, :, ::-1]
            name = ""
            face_locations = []
            process_this_frame = True
            if process_this_frame:
                # detect a face
                face_locations = face_recognition.face_locations(rgb_frame)
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
                    if True in matches:
                        match_index = matches.index(True)
                        name = known_face_names[match_index]
                        username.name = name
            process_this_frame = not process_this_frame

            #draw the face detected
            if face_locations:
                print(face_locations)
                top, right, bottom, left = face_locations[0]
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                # draw a label with name
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

            frame=cv2.imencode('.jpg',frame)[1]
            yield (b'--frame\r\n'
                b'Content-Type: text/plain\r\n\r\n'+frame.tostring()+b'\r\n')

@app.route('/calc')
def calc():
    return Response(get_frame(),mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route("/register")
def register():
    return render_template("upload.html")

@app.route("/upload", methods=['POST'])
def upload():
    target = os.path.join(APP_ROOT, "images/")
    #if images folder doesn't exist, create it
    print(target)

    if not os.path.isdir(target):
        os.mkdir(target)

    for file in request.files.getlist("file"):
        print(file)
        filename = file.filename
        destination = "/".join([target, filename])
        print(destination)
        file.save(destination)
        #save the user name
        username = request.form.get("username")
        print(username)
        print(filename)
        sql = """INSERT INTO faces(username,
                   filename)
                   VALUES ('%s', '%s')""" % (username, filename)
        print(sql)
        try:
            cursor.execute(sql)
            db.commit()
        except pymysql.InternalError as error:
            code, message = error.args
            print(">>>>>>>>>>>>>", code, message)
            db.rollback()

        #add this new image to the list
        known_face_names.append(username)
        new_image = face_recognition.load_image_file(destination)
        new_encoding = face_recognition.face_encodings(new_image)[0]
        known_face_encodings.append(new_encoding)

    return render_template("index.html")

@app.route('/logout')
def logout():
    username.name = ""
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(debug=True)

