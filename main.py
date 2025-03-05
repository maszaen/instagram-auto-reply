import os
import json
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
    print("Received data:", json.dumps(data, indent=2))  # Debugging log

    if data.get('object') == 'instagram':
        for entry in data.get('entry', []):
            for messaging in entry.get('messaging', []):
                sender_id = messaging.get('sender', {}).get('id')
                message_text = messaging.get('message', {}).get('text')

                if sender_id and message_text:
                    print(f"Received message: {message_text} from {sender_id}")

                    # Generate reply
                    reply = generate_gemini_reply(message_text)

                    # Send reply via Instagram API
                    try:
                        access_token = get_access_token()
                        url = f"https://graph.facebook.com/v19.0/me/messages"
                        headers = {"Content-Type": "application/json"}
                        payload = {
                            "recipient": {"id": sender_id},
                            "message": {"text": reply}
                        }

                        response = requests.post(
                            url,
                            json=payload,
                            headers=headers,
                            params={"access_token": access_token}
                        )

                        print("Send message response:", response.json())  # Debug response
                    except Exception as e:
                        print(f"Error sending reply: {e}")

    return jsonify(success=True), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
