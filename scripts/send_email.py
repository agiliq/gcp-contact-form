import os
import datetime
import requests
from flask import redirect
from google.cloud import datastore


def start(request):
    """
    Google cloud platform internally uses flask to run cloud functions.
    So here `request` is Flask.request
    """
    # Initializing Redirect URLs
    REDIRECT_SUCCESS_URL = os.environ.get('REDIRECT_SUCCESS_URL', None)
    REDIRECT_FAILURE_URL = os.environ.get('REDIRECT_FAILURE_URL', None)
    TO_ADDRESS = str(os.environ.get('TO_ADDRESS', None))

    # Consuming input variables required from form
    FROM_EMAIL = request.form['email']
    FROM_NAME = request.form['name']
    body = request.form['body']

    # Before sending the email, keep track of users who are mailing us
    client_key = save_user_data(FROM_NAME, FROM_EMAIL, body)

    # Send an email using MAILGUN API
    # Decoupled send_email() in order to make it easily usable
    response = send_email(FROM_EMAIL, FROM_NAME, 'Contacted at Agiliq form', body +
                          "\n\nRegards,\n{}\n{}".format(FROM_NAME, FROM_EMAIL), TO_ADDRESS)

    # Send confirmation email to the user, as we've got the email
    send_confirmation_email(FROM_EMAIL, TO_ADDRESS)

    # Redirect to success page if 200 else redirect to error page
    if response == 200:
        return redirect(REDIRECT_SUCCESS_URL, code=302)
    return redirect(REDIRECT_FAILURE_URL, code=302)


def save_user_data(FROM_NAME, FROM_EMAIL, body):
    """
    Save the data in our DB as user has not got the email
    """
    # Initializing the data where PROJECT_ID = GCP Project ID
    PROJECT_ID = os.environ.get('PROJECT_ID', None)
    client = datastore.Client(PROJECT_ID)

    key = client.key('Task')

    # Create a new entity
    task = datastore.Entity(key, exclude_from_indexes=['message'])
    task.update({
        'created': datetime.datetime.now(),
        'name': FROM_NAME,
        'email': FROM_EMAIL,
        'message': body
    })

    # Upload the data
    client.put(task)

    return client.key


def send_confirmation_email(FROM_EMAIL, TO_ADDRESS):
    """
    Send a confirmation email to the user saying we're recieved their email.
    """
    CONFIRMATION_EMAIL_TO_ADDRESS = FROM_EMAIL
    CONFIRMATION_EMAIL_FROM_ADDRESS = TO_ADDRESS
    CONFIRMATION_SUBJECT = 'Thank you for contacting us!'
    CONFIRMATION_EMAIL_BODY = os.environ.get('CONFIRMATION_EMAIL_BODY', None)
    CONFIRMATION_EMAIL_FROM_NAME = os.environ.get(
        'CONFIRMATION_EMAIL_FROM_NAME', None)

    send_email(CONFIRMATION_EMAIL_FROM_ADDRESS, CONFIRMATION_EMAIL_FROM_NAME,
               CONFIRMATION_SUBJECT, CONFIRMATION_EMAIL_BODY, CONFIRMATION_EMAIL_TO_ADDRESS)


def send_email(FROM_EMAIL, FROM_NAME, SUBJECT, BODY, TO_ADDRESS):
    """
    Send an email using MailGUN API Client
    """

    # Initializing important data from environment
    MAILGUN_DOMAIN_NAME = os.environ.get('MAILGUN_DOMAIN_NAME', None)
    MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY', None)

    # Preparing the data to be sent as email
    url = 'https://api.mailgun.net/v3/{}/messages'.format(MAILGUN_DOMAIN_NAME)
    auth = ('api', MAILGUN_API_KEY)
    data = {
        'from': '{} <{}>'.format(FROM_NAME, FROM_EMAIL),
        'to': TO_ADDRESS,
        'subject': SUBJECT,
        'text': BODY
    }

    # Sending the email
    response = requests.post(url, auth=auth, data=data)
    return response.status_code
