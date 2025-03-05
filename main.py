import os
import requests
from flask import Flask, request, jsonify
from google.cloud import secretmanager, aiplatform

app = Flask(__name__)

# Config
PROJECT_ID = "apiscamp"
SECRET_NAME = "instagram-access-token"
PAGE_ID = "585261331336119"
VERIFY_TOKEN = "webhook-instagram-token-209-5599-2709"

# Init clients
aiplatform.init(project=PROJECT_ID)
secret_client = secretmanager.SecretManagerServiceClient()


def get_access_token():
    secret_name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    response = secret_client.access_secret_version(name=secret_name)
    return response.payload.data.decode("UTF-8")


def generate_gemini_reply(message):
    model = aiplatform.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(
        f"Balas pesan berikut dengan ramah dan profesional dalam 1 kalimat: {message}"
    )
    return response.text


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verify webhook
        hub_mode = request.args.get('hub.mode')
        hub_token = request.args.get('hub.verify_token')
        hub_challenge = request.args.get('hub.challenge')

        if hub_mode == 'subscribe' and hub_token == VERIFY_TOKEN:
            return hub_challenge, 200
        return "Verification failed", 403

    # Handle incoming messages
    data = request.json
    if data.get('object') == 'instagram':
        for entry in data.get('entry', []):
            # Periksa apakah ada key 'messaging'
            if 'messaging' in entry:
                for messaging in entry['messaging']:
                    sender_id = messaging['sender']['id']
                    if 'text' in messaging['message']:
                        message_text = messaging['message']['text']

                        # Generate reply
                        reply = generate_gemini_reply(message_text)

                        # Send reply via Instagram API
                        try:
                            access_token = get_access_token()
                            url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/messages"
                            params = {
                                'access_token': access_token,
                                'recipient': json.dumps({'id': sender_id}),
                                'message': json.dumps({'text': reply})
                            }
                            requests.post(url, params=params)
                        except Exception as e:
                            print(f"Error sending reply: {e}")
            else:
                print(f"No 'messaging' key in entry: {entry}")

    return jsonify(success=True), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))