from flask import Flask, request, redirect, url_for, render_template_string
import psycopg2
import boto3
import os

app = Flask(__name__)

from prometheus_flask_exporter import PrometheusMetrics
metrics = PrometheusMetrics(app)
BUCKET = "izaz-flask-app-bucket-2026"
s3 = boto3.client("s3", region_name="ap-south-1")

def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )
    return conn

HTML = """
<!DOCTYPE html>
<html>
<head><title>Flask S3 App</title></head>
<body>
  <h1>Flask + PostgreSQL + S3</h1>

  <h2>Database</h2>
  <p>Connected to: {{ db_version }}</p>

  <h2>Upload File to S3</h2>
  <form method="POST" action="/upload" enctype="multipart/form-data">
    <input type="file" name="file" required>
    <button type="submit">Upload</button>
  </form>

  <h2>Files in S3</h2>
  <ul>
    {% for file in files %}
      <li>
        {{ file }}
        <a href="/download/{{ file }}">Download</a>
      </li>
    {% endfor %}
  </ul>
</body>
</html>
"""

@app.route('/')
def index():
    # Get DB version
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT version();')
    db_version = cur.fetchone()[0]
    cur.close()
    conn.close()

    # List S3 files
    response = s3.list_objects_v2(Bucket=BUCKET)
    files = [obj['Key'] for obj in response.get('Contents', [])]

    return render_template_string(HTML, db_version=db_version, files=files)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file:
        s3.upload_fileobj(file, BUCKET, file.filename)
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download(filename):
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET, 'Key': filename},
        ExpiresIn=300  # URL valid for 5 minutes
    )
    return redirect(url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
