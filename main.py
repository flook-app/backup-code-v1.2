from flask import Flask, request, send_from_directory, jsonify, make_response
from flask_cors import CORS
import mysql.connector

# import pandas as pd
from deepface import DeepFace
import gdown
# import numpy as np
# from PIL import Image
# import cv2
# import matplotlib.pyplot as plt
import os
# from IPython.display import display

app = Flask(__name__, static_folder='albums')
CORS(app, resources={r"/*": {"origins": "*"}})


# mysql database config 
config = {
  'user': 'u1652679_identpix_admin',
  'password': 'p++ubr,+LAXq',
  'host': 'kevinchr.com',
  'database': 'u1652679_identpix_db',
  'raise_on_warnings': True
}

cnx = mysql.connector.connect(**config)
cur = cnx.cursor()

@app.route('/', methods=['GET'])
def main_route():
    return 'Hello, World! Main route ...'

@app.route('/get-images/<folder_id>', methods=['GET'])
def get_images(folder_id):
    cur.execute("SELECT * FROM images WHERE folder_id = %s", (folder_id,))
    rows = cur.fetchall()
    return {
        'status' : 'Data fetched',
        'data' : rows
    }, 200
    
    
# user register
@app.route('/register', methods=["POST"])
def register():
    fullname = request.json['fullname']
    email = request.json['email']
    password = request.json['password']

    query = "INSERT INTO users (fullname, email, password) VALUES (%s, %s, %s)"
    data = (fullname, email, password)

    cur.execute(query, data)
    cnx.commit()

    return {'status': 'User created'}, 200

# user login
@app.route('/login', methods=['POST'])
def login():
    email = request.json['email']
    password = request.json['password']

    query = "SELECT * FROM users WHERE email = %s AND password = %s"
    data = (email, password)

    cur.execute(query, data)
    user = cur.fetchone()

    if user:
        return {
            'status': 'Login successful',
            'data' : user
        }, 200
    else:
        return {'status': 'Invalid email or password'}, 401

# get user albums
@app.route('/albums/<user_id>', methods=['GET'])
def get_albums(user_id):
    cur.execute("SELECT * FROM folders WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    return {
        'status' : 'Data fetched',
        'data' : rows
    }, 200

# display one image
@app.route('/images/<driveId>/<path>')
def serve_image(driveId, path):
    album_name = os.listdir('albums/' + driveId)[0]
    dir = 'album/' + driveId + '/' + album_name
    print("ALBUM NAME IS ", album_name)
    print("DIR IS : ", dir)
    print("PATH IS : ", path)
    thumbnail = driveId + '/' + album_name + '/' + path
    return send_from_directory('albums', thumbnail)

# https://519c-36-90-119-16.ngrok-free.app/images/1_album/IMG_1339.JPG

# get all images from an album
@app.route('/album_images', methods=['GET'])
def list_images():
    album_id = request.args.get('album_id')
    folder = os.listdir('albums/' + album_id)[0]
    files = os.listdir('albums/' + album_id + '/' + folder)
    urls = ['https://netdxc.com/identpix_api_v1/images/' + album_id + '/' + file for file in files]
    response = make_response(jsonify(urls))
    response.headers['ngrok-skip-browser-warning'] = 'skip-browser-warning'
    
    cur.execute("SELECT * FROM folders WHERE gdrive_id = %s", (album_id,))
    rows = cur.fetchall()
    
    return response

    
# check list dir
@app.route('/check-listdir', methods=['GET'])
def check_listdir():
    listdir = os.listdir('albums/')
    return {
        'status' : 'success',
        'data' : listdir
    }, 200

# upload face to scan
@app.route('/upload-face', methods=['POSt'])
def upload_face():
    file = request.files['file']
    save_path = file.save(os.path.join('albums/faces', file.filename))
    
    if os.path.isfile('albums/faces/' + file.filename):
        # face1_filename = file.filename
        return {
        'status' : 'Face uploaded successfully'
    }, 200
    else:
        return {
            'status' : 'Error uploading face to server.'
        }, 401
        
        
# scan user's submitted face        
@app.route('/scan-face/<face1_filename>/<album_id>', methods=['GET'])
def scan_face(face1_filename, album_id):
    # face1_filename = request.args.get('filename')
    folder = os.listdir('albums/' + album_id)[0]
    
    try:
        dfs = DeepFace.find(img_path='albums/faces/' + face1_filename, db_path='albums/' + album_id + '/' + folder, model_name='Facenet')
        df = dfs[0]
        print("DF = ", df)
        res = df['identity'].values.tolist()
        print("RES = ", res)
        file_paths = [path.replace('\\\\', '/') for path in res]
        file_names = [os.path.basename(path) for path in file_paths]
        print(file_names)
        
        return {
            'status' : 'Success',
            'data' : file_names,
            'res': res
        }, 200
    except Exception as e:
        return {
            'status' : 'Error'
        }, 200
    
    
@app.route('/fetch-folder', methods=['POST'])
def fetch_folder():
    url = request.json['folder-link']
    # if url.split('/')[-1] == 'usp=drive_link':
    #     url = url.replace('usp=drive_link', '')
        
    folder_id = url.split('/')[-1]
    folder_id = folder_id.split('?')[0]

    # Save the original working directory
    original_dir = os.getcwd()
    print("original directory : " + original_dir)

    # Create a new directory with the name 'url'
    os.makedirs('./albums/' + folder_id, exist_ok=True)

    # Change the current working directory to the new directory
    os.chdir('./albums/' + folder_id)

    # Now the downloaded files will be saved in the new directory
    gdown.download_folder(url)

    # Change back to the original working directory
    os.chdir(original_dir)
    cnx.commit()

    return {
        'status' : 'success',
        'data' : url
    }, 200
    
    
@app.route('/upload-album/<user_id>', methods=['POST'])
def upload_album(user_id):
    link = request.json['link']
    name = request.json['name']
    desc = request.json['description']
    
    folder_id = link.split('/')[-1]
    folder_id = folder_id.split('?')[0]
    
    query = "INSERT INTO folders (gdrive_id, gdrive_link, name, description, status, user_id, thumbnail_path) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    data = (folder_id, link, name, desc, 'Preparing', user_id, '')
    
    cur.execute(query, data)
    cnx.commit()
    
    original_dir = os.getcwd()
    print("original directory : " + original_dir)

    # Create a new directory with the name 'url'
    os.makedirs('./albums/' + folder_id, exist_ok=True)

    # Change the current working directory to the new directory
    os.chdir('./albums/' + folder_id)

    # Now the downloaded files will be saved in the new directory
    gdown.download_folder(link)
    
    listdir = os.listdir()
    album_name = listdir[0]
    thumbnail = os.listdir(album_name)[0]
    
    update_query = "UPDATE folders SET thumbnail_path = %s WHERE gdrive_id = %s"
    update_data = (thumbnail, folder_id)
    cur.execute(update_query, update_data)
    cnx.commit()

    # Change back to the original working directory
    os.chdir(original_dir)

    return {
        'status' : 'success',
        'data' : [link, thumbnail, folder_id]
    }, 200


if __name__ == '__main__':
    app.run(debug=True)
