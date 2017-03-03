import json
import os
import shutil
import tempfile
import zipfile
import time
import uuid
from datetime import datetime

import girder_client

GIRDER_URL = 'http://ismi17.diagnijmegen.nl/girder/api/v1'


def submit_results(user, csv_results, description=None):
    client = girder_client.GirderClient(apiUrl=GIRDER_URL)
    upload_challenge_data(client, user, 'lidc', csv_results, metadata=description)
    print(
        "Done. The results of your submission will appear shortly on the leaderboard at http://ismi17.diagnijmegen.nl/")


def upload_challenge_data(client, user, challenge_name, results_file, metadata=None):
    working_directory = tempfile.mkdtemp()
    results_folder = tempfile.mkdtemp()

    try:
        create_results_csv(results_file, results_folder)
        create_challengr_json(results_folder)

        results_zip = zip_directory(results_folder, working_directory)
        upload_file_to_server(client, user, results_zip, challenge_name, metadata)
    finally:
        shutil.rmtree(working_directory)
        shutil.rmtree(results_folder)


def create_results_csv(results_file, results_folder):
    print('Validating the csv file')
    output_file = os.path.join(results_folder, 'algorithm_result.csv')

    with open(os.path.abspath(results_file), 'r') as f:
        filedata = f.readlines()

    # First line must have the correct format
    filedata[0] = 'nodule_id,label\n'

    # Naive checking that we have results for everything
    if len(filedata) != 244:
        raise(ValueError('You do not have enough entries in your csv file. Do you have results for all of the test data?'))

    try:
        int(filedata[1].split(',')[1])
    except ValueError:
        raise(ValueError('The format of your csv file is incorrect. It should be comma separated, the 1st column is nodule_id, the 2nd the label. We could not convert your label to an int.'))

    with open(output_file, 'w') as f:
        f.writelines(filedata)


def upload_file_to_server(client, user, file, challenge_name, metadata=None):
    print('Uploading results to server')
    client.authenticate(username=user['username'], password=user['password'])

    # The following will just return the first item in the list!!!
    collection = client.get('collection', {'text': challenge_name, 'limit': 1})[0]
    folder = client.get('folder', {'parentId': collection['_id'],
                                   'parentType': 'collection',
                                   'name': user['username'].lower()})[0]

    item = client.createItem(folder['_id'], 'Submission %s' % datetime.utcnow())

    if metadata is not None:
        client.addMetadataToItem(item['_id'], metadata)

    # Upload file data
    client.uploadFileToItem(item['_id'], file)


def zip_directory(input_dir, output_dir):
    """
    Creates a temporary directory and creates a zipfile with the algorithm result
    :param folder:
    :return:
    """
    print('Compressing results')
    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)

    foldername = os.path.split(input_dir)[1]
    temp_zip_file = os.path.join(output_dir, foldername + '.zip')

    with zipfile.ZipFile(temp_zip_file, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(input_dir):
            for f in files:
                z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), input_dir))

    return temp_zip_file


def create_challengr_json(results_folder):
    json_filename = os.path.join(results_folder, 'challengr.json')
    print('Creating %s' % json_filename)

    foldername = os.path.basename(os.path.normpath(results_folder))

    challengr_metadata = {"timestamp": time.time(), "algorithmfields": {
        "fields": [],
        "description": "",
        "uuid": str(uuid.uuid1()),
        "name": ""}, "uid": "", "timings": {}, "parametrization": {}, 'uid': str(foldername)}

    with open(json_filename, 'w') as f:
        f.write(json.dumps(challengr_metadata))
