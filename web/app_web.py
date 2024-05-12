from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
import os
import cv2
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@localhost/database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    num_cars = db.Column(db.Integer, nullable=False)
    original_image_path = db.Column(db.String(255), nullable=False)
    modified_image_path = db.Column(db.String(255), nullable=False)
    text = db.Column(db.String(255), nullable=False)

UPLOADS_FOLDER = 'uploads'
PROCESSED_IMAGES_FOLDER = 'processed_images'

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOADS_FOLDER, filename)

@app.route('/processed_images/<path:filename>')
def serve_processed_image(filename):
    return send_from_directory(PROCESSED_IMAGES_FOLDER, filename)

@app.route('/')
def index():
    uploads = Upload.query.all()
    return render_template('index.html', uploads=uploads)



def detect_cars(image_path):
    key = "b9dce00fccf942b3a535639980d7c367"
    endpoint = "https://cardet14624.cognitiveservices.azure.com/"
    client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))

    with open(image_path, 'rb') as image_file:
        analysis = client.analyze_image_in_stream(image_file, [VisualFeatureTypes.objects])

    cars = [obj for obj in analysis.objects if obj.object_property == 'car']
    image = cv2.imread(image_path)

    for car in cars:
        rect = car.rectangle
        cv2.rectangle(image, (rect.x, rect.y), (rect.x + rect.w, rect.y + rect.h), (0, 255, 0), 5)

    annotated_image_path = os.path.splitext(image_path)[0] + '_annotated.jpg'
    cv2.imwrite(annotated_image_path, image)

    return len(cars), annotated_image_path

@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        image = request.files['image']
        text = request.form['text']

        if image:
            image_path = os.path.join(UPLOADS_FOLDER, image.filename)
            image.save(image_path)

            num_cars, annotated_image_path = detect_cars(image_path)

            new_upload = Upload(num_cars=num_cars, original_image_path=image_path,
                                modified_image_path=annotated_image_path, text=text)
            db.session.add(new_upload)
            db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)