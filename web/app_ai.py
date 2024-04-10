from flask import Flask, request, jsonify
from shutil import copyfile
from flask_sqlalchemy import SQLAlchemy
import os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@localhost/database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

UPLOADS_FOLDER = 'uploads'
PROCESSED_IMAGES_FOLDER = 'processed_images'

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.Integer, nullable=False)
    original_image_path = db.Column(db.String(255), nullable=False)
    modified_image_path = db.Column(db.String(255), nullable=False)
    text = db.Column(db.String(255), nullable=False)

@app.route('/process_image', methods=['POST'])
def process_image():
    if request.method == 'POST':
        image_path = request.form['image_path']

        # Determine order number
        last_upload = Upload.query.order_by(Upload.order_number.desc()).first()
        order_number = last_upload.order_number + 1 if last_upload else 1

        # Copy the original image to processed images folder
        modified_image_path = os.path.join(PROCESSED_IMAGES_FOLDER, os.path.basename(image_path))
        copyfile(image_path, modified_image_path)

        return jsonify({'order_number': order_number, 'modified_image_path': modified_image_path}), 200

if __name__ == '__main__':
    app.run(port=5001)
