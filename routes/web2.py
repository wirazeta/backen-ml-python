import io
from operator import truediv
import os
import json
import random
from PIL import Image
from pathlib import Path
from google.cloud import storage

import torch
from flask import Flask, jsonify, url_for, render_template, request, redirect, make_response

app = Flask(__name__)

RESULT_FOLDER = os.path.join('static')

app.config['RESULT_FOLDER'] = RESULT_FOLDER

model_name = 'best.pt'
model = torch.hub.load("WongKinYiu/yolov7", 'custom', model_name)

model.eval

def get_prediction(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))
    imgs = [img]
    results = model(imgs, size = 640)
    return results

@app.route('/', methods=['POST'])
def predict():
    if request.method != 'POST':
        return "Method false"
    file = request.files.get('file').read()
    if not os.path.exists('./static'):
        os.mkdir('./static')
    # img_bytes = Image.open(io.BytesIO(file))
    results = get_prediction(img_bytes = file)
    print(results)
    results.save('static')
    filename = 'image'+str(0)
    newFilename = check_and_rename(filename)
    print(newFilename)
    if not os.path.exists('static/results') :
        try:
            original_umask = os.umask(0)
            os.mkdir('static/results',mode = 0o777)
        finally:
            os.umask(original_umask)
    os.rename('static/'+filename+'.jpg', 'static/results/'+newFilename+'.jpg')
    filepath = upload_image_to_google_storage('static/results/'+newFilename+'.jpg', 'machine-learning-object-bucket-1')
    results_json = results.pandas().xyxy[0].to_json(orient = "records")
    response = make_response(jsonify({
        'status': 200,
        'message': 'success',
        'image' : filepath,
        'results': results_json
    }))
    return response

def check_and_rename(file_path: Path, add: int = 0) -> Path:
    # original_file_path = file_path
    # if add != 0:
    #     original_file_path = file_path+str(add)
    # if not os.path.exists(original_file_path):
    #     print(os.path.exists(original_file_path+'.jpg'))
    #     return original_file_path
    # else:
    #     return check_and_rename(original_file_path, add+1)
    if not os.path.exists("static/results/"+file_path+".jpg"):
        # check file path and what the fuck happen ???
        # print(os.path.exists("static/"+file_path+".jpg"))
        return file_path
    
    base_dir = os.path.dirname(file_path)
    file_name, file_extension = os.path.splitext(os.path.basename(file_path))
    
    counter = add
    new_file_path = os.path.join(base_dir, f"{file_name}_{counter}{file_extension}")
    print("Fucking Idiot Me "+str(new_file_path))

    while os.path.exists("static/results/"+new_file_path+".jpg"):
        counter += 1
        new_file_path = os.path.join(base_dir, f"{file_name}_{counter}{file_extension}")
    
    return check_and_rename(new_file_path, add+1)
    
def upload_image_to_google_storage(image_path, bucket_name):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'meta-map-351711-90fab2172d72.json'
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(image_path)
    blob.upload_from_filename(image_path)
    return blob.public_url


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug = True)
