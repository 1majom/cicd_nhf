from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@localhost/database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.Integer, nullable=False)
    original_image_path = db.Column(db.String(255), nullable=False)
    modified_image_path = db.Column(db.String(255), nullable=False)
    text = db.Column(db.String(255), nullable=False)

UPLOADS_FOLDER = 'uploads'
PROCESSED_IMAGES_FOLDER = 'processed_images'

# Define the URL of the image processing service
IMAGE_PROCESSING_URL = 'http://localhost:5001/process_image'



# Define routes to serve static files
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

@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        image = request.files['image']
        text = request.form['text']

        if image:
            # Save the original image
            image_path = os.path.join(UPLOADS_FOLDER, image.filename)
            image.save(image_path)

            # Call the image processing service to assign order number and copy image
            response = requests.post(IMAGE_PROCESSING_URL, data={'image_path': image_path})

            if response.status_code == 200:
                data = response.json()
                order_number = data['order_number']
                modified_image_path = data['modified_image_path']

                # Save data to the database
                new_upload = Upload(order_number=order_number, original_image_path=image_path,
                                    modified_image_path=modified_image_path, text=text)
                db.session.add(new_upload)
                db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        db.create_all()
    # Run the Flask app
    app.run(debug=True)
