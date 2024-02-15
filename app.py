from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import boto3
import datetime
import io

app = Flask(__name__)

# Initialize CORS extension with specific options
cors = CORS(app, supports_credentials=True)

# Replace these with your actual MySQL connection details
host = 'db-mysql-sgp1-63748-do-user-15012910-0.c.db.ondigitalocean.com'  # or '127.0.0.1' for localhost
user = 'doadmin'
password = 'AVNS_KSG7UKuWQNmOCa8KZVQ'
database = 'defaultdb'
port = 25060

spaces_access_key = 'DO00CY9QCZK27QARV2LP'
secrets_access_key = 'al7zummlFpomgSccYkNhpYVIbcq1RPRdleVEX3pup9c'


# Initialize MySQL database


def init_db():
    # Create a MySQL connection
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port
    )
    cursor = conn.cursor()
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS data (id INT AUTO_INCREMENT PRIMARY KEY,name VARCHAR(255),room_name VARCHAR(255),session_id VARCHAR(255),ocr_time FLOAT,ocr_result VARCHAR(5000),origin_image_path TEXT,yolo_image_path TEXT)')
    conn.commit()
    conn.close()


init_db()


def get_upload_to_digitalocean_spaces(file, file_name, folder, access_key, secret_key):
    try:
        space_name = 'hoacm-image-upload'
        endpoint_url = f'https://{space_name}.sgp1.digitaloceanspaces.com'

        # Create an S3 client
        s3 = boto3.client('s3', endpoint_url=endpoint_url,
                          aws_access_key_id=access_key, aws_secret_access_key=secret_key)

        # Set file metadata
        file_metadata = {
            'ACL': 'public-read',  # Set ACL to make the object publicly readable
        }

        # Upload the file
        s3.upload_fileobj(file, folder, file_name, ExtraArgs=file_metadata)

        # print(f"File uploaded successfully to DigitalOcean Spaces: {endpoint_url}/{folder}/{file_name}")
        return f'{endpoint_url}/{folder}/{file_name}'

    except Exception as e:
        print(e)


@app.route('/api/store-info', methods=['POST'])
def upload_data():
    try:
        # Get data from the request
        data = request.form
        name = data.get('name')
        room_name = data.get('room_name')
        session_id = data.get('session_id')
        ocr_time = data.get('ocr_time')
        ocr_result = data.get('ocr_result')

        # Get files from the request
        origin_image = request.files['originImage']
        yolo_image = request.files['yoloImage']

        # Generate a timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        # Save the files
        origin_image_path = f'origin_image_path_{timestamp}.png'
        yolo_image_path = f'yolo_image_path_{timestamp}.png'

        # Ensure the filename is not None
        if origin_image.filename:
            # Read the content of the file
            file_content = origin_image.read()

            # Create a file-like object from the bytes
            file_like_object = io.BytesIO(file_content)

            origin_image_path = get_upload_to_digitalocean_spaces(file_like_object, origin_image_path, 'origin_image',
                                                                  access_key=spaces_access_key,
                                                                  secret_key=secrets_access_key)

        # Ensure the filename is not None
        if yolo_image.filename:
            # Read the content of the file
            file_content = yolo_image.read()

            # Create a file-like object from the bytes
            file_like_object = io.BytesIO(file_content)

            yolo_image_path = get_upload_to_digitalocean_spaces(file_like_object, yolo_image_path,
                                                                'yolo_image',
                                                                access_key=spaces_access_key,
                                                                secret_key=secrets_access_key)

        # origin_image.save(origin_image_path)
        # yolo_image.save(yolo_image_path)

        # Create a MySQL connection
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )

        # Store data in the MySQL database
        cursor = conn.cursor()
        print(ocr_result)
        cursor.execute(
            'INSERT INTO data (name, room_name, session_id, ocr_time, ocr_result, origin_image_path, yolo_image_path) VALUES (%s, %s, %s,%s, %s, %s, %s)',
            (name, room_name, session_id, ocr_time, ocr_result, origin_image_path, yolo_image_path))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Data uploaded successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/list-data', methods=['GET'])
def list_data():
    try:
        # Create a MySQL connection
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )

        # Fetch data from the MySQL database
        cursor = conn.cursor(dictionary=True)
        # Use LIMIT to limit the number of rows returned
        cursor.execute('SELECT * FROM data LIMIT 100')  # Adjust the limit as needed
        data_list = cursor.fetchall()
        conn.close()

        # Convert the result to JSON
        result = {'code': 0, 'data': data_list}

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run()
