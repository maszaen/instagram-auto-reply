import os
import requests
from flask import Flask, request, jsonify
from google.cloud import secretmanager, aiplatform

app = Flask(__name__)

# Config
PROJECT_ID = "apiscamp"
SECRET_NAME = "instagram-access-token"
VERIFY_TOKEN = "webhook-instagram-token-209-5599-2709"

INSTAGRAM_BUSINESS_ID = "17841413148402065"

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


def send_instagram_reply(sender_id, reply_text):
    try:
        access_token = get_access_token()
        url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_BUSINESS_ID}/messages"

        payload = {
            "recipient": {"id": sender_id},
            "message": {"text": reply_text}
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, headers=headers, json=payload, params={"access_token": access_token})

        if response.status_code == 200:
            print(f"✅ Reply terkirim ke {sender_id}: {reply_text}")
        else:
            print(f"❌ Gagal mengirim reply: {response.text}")

    except Exception as e:
        print(f"🔥 Error send_instagram_reply: {e}")


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verifikasi webhook dari Meta
        hub_mode = request.args.get('hub.mode')
        hub_token = request.args.get('hub.verify_token')
        hub_challenge = request.args.get('hub.challenge')

        if hub_mode == 'subscribe' and hub_token == VERIFY_TOKEN:
            return hub_challenge, 200
        return "Verification failed", 403

    data = request.json
    print("📩 Webhook received:", json.dumps(data, indent=2))  # Debugging log

    if data.get('object') == 'instagram':
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                message_data = change.get('value', {}).get('messages', [])

                for message in message_data:
                    sender_id = message.get("from", {}).get("id")
                    message_text = message.get("text", "")

                    if sender_id and message_text:
                        print(f"📨 Pesan dari {sender_id}: {message_text}")

                        reply = generate_gemini_reply(message_text)

                        send_instagram_reply(sender_id, reply)

    return jsonify(success=True), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
