"""
This module has the main application basically. It has three connections to other components
One to the rabbitMQ for notifying the admins on the /admin endpoint. And another to the Azure
Compute Vision which makes the car detection and by this it gives back the locations of the cars
from which we can draw the rectangles and get the number of cars. The last connection is to the
mariadb which is used to store the number of the cars and also the path on which the images can be reached.
"""

import os
import json
import cv2
import pika
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@mariadb/database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# RabbitMQ STOMP configuration
RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_PORT = 15674  # Web STOMP port
QUEUE_NAME = '/queue/car_numbers'

class Upload(db.Model):
    """
    This class model which represents an image with the two versions.
    """
    id = db.Column(db.Integer, primary_key=True)
    num_cars = db.Column(db.Integer, nullable=False)
    original_image_path = db.Column(db.String(255), nullable=False)
    modified_image_path = db.Column(db.String(255), nullable=False)
    text = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Upload {self.id}>'

UPLOADS_FOLDER = 'uploads'
if not os.path.exists(UPLOADS_FOLDER):
    os.makedirs(UPLOADS_FOLDER)
PROCESSED_IMAGES_FOLDER = 'processed_images'

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """
    This function serves the uploaded files
    """
    return send_from_directory(UPLOADS_FOLDER, filename)

@app.route('/processed_images/<path:filename>')
def serve_processed_image(filename):
    """
    This function serves the processed images.
    """
    return send_from_directory(PROCESSED_IMAGES_FOLDER, filename)

@app.route('/')
def index():
    """
    This function renders the index page.
    """
    uploads = Upload.query.all()
    return render_template('index.html', uploads=uploads)

@app.route('/admin')
def admin():
    """
    This function renders the admin page.
    """
    return render_template('admin.html')

def detect_cars(image_path):
    """
    This function detects cars in the given image by using Azure
    """
    key = os.environ.get('KEY')
    endpoint = os.environ.get('ENDPOINT')
    client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))

    with open(image_path, 'rb') as image_file:
        analysis = client.analyze_image_in_stream(image_file, [VisualFeatureTypes.objects])

    cars = [obj for obj in analysis.objects if obj.object_property == 'car']
    image = cv2.imread(image_path)  # pylint: disable=no-member

    for car in cars:
        rect = car.rectangle
        cv2.rectangle(image, (rect.x, rect.y), (rect.x + rect.w, rect.y + rect.h), (0, 255, 0), 5)  # pylint: disable=no-member

    annotated_image_path = os.path.splitext(image_path)[0] + '_annotated.jpg'
    cv2.imwrite(annotated_image_path, image)  # pylint: disable=no-member

    return len(cars), annotated_image_path

def send_to_rabbitmq(num_cars, text):
    """
    This function sends the number of cars to RabbitMQ.
    """
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue='car_numbers', durable=True)

    channel.basic_publish(exchange='',
                          routing_key='car_numbers',
                          body=json.dumps({'num_cars': num_cars, 'text': text}))

    print(" [x] Sent 'num_cars'")
    connection.close()

@app.route('/upload', methods=['POST'])
def upload():
    """
    This function handles the upload of images.
    """
    if request.method == 'POST':
        image = request.files['image']
        text = request.form['text']

        if image:
            image_path = os.path.join(UPLOADS_FOLDER, image.filename)
            image.save(image_path)

            num_cars, annotated_image_path = detect_cars(image_path)

            send_to_rabbitmq(num_cars, text)  # Send number of cars to RabbitMQ

            new_upload = Upload(num_cars=num_cars, original_image_path=image_path,
                                modified_image_path=annotated_image_path, text=text)
            db.session.add(new_upload)
            db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True)