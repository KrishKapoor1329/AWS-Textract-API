import os
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import boto3
from trp import Document

# Initialize Flask application
app = Flask(__name__)

# Amazon Textract client
textract = boto3.client('textract', region_name='ap-south-1')

# Configure the upload folder and allowed file extensions
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'jpg', 'jpeg', 'png'}

# Function to check if a file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')

# Route for processing the uploaded file
@app.route('/process', methods=['POST'])
def process_file():
    # Check if a file was uploaded
    if 'file' not in request.files:
        return render_template('index.html', message='No file uploaded')

    file = request.files['file']

    # Check if the file has a valid filename and extension
    if file.filename == '' or not allowed_file(file.filename):
        return render_template('index.html', message='Invalid file name or extension')

    # Save the file to a local location
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Process the file using Amazon Textract
    with open(file_path, "rb") as document:
        response = textract.analyze_document(
            Document={
                'Bytes': document.read(),
            },
            FeatureTypes=["TABLES"])

    doc = Document(response)
    extracted_text = ""
    extracted_tables = []

    for page in doc.pages:
        # Extract text from each page
        if page.text:
            extracted_text += page.text + "\n"

        # Extract tables from each page
        for table in page.tables:
            extracted_table = []
            for r, row in enumerate(table.rows):
                extracted_row = []
                for c, cell in enumerate(row.cells):
                    extracted_row.append(cell.text)
                extracted_table.append(extracted_row)
            extracted_tables.append(extracted_table)

    # Remove the uploaded file
    os.remove(file_path)

    return render_template('result.html', extracted_text=extracted_text, tables=extracted_tables)
    
# Route for downloading the extracted text as a file
@app.route('/download_text')
def download_text():
    extracted_text = request.args.get('text', '')
    if extracted_text:
        with open('extracted_text.txt', 'w') as text_file:
            text_file.write(extracted_text)

        return send_file('extracted_text.txt', as_attachment=True, download_name='extracted_text.txt')
    else:
        return "Error: No extracted text available to download."

# Run the Flask application
if __name__ == '__main__':
    app.run()