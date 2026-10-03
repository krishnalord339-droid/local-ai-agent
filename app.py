import os
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# Environment Variables
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ApexLocalSecret2026")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Client Setup
client = genai.Client(api_key=GEMINI_API_KEY)

# केवल बिजनेस क्लाइंट्स की अनुमति सूची (देश कोड के साथ, बिना '+' के)
# अपने पर्सनल या रिश्तेदारों के नंबर इसमें कभी न जोड़ें
ALLOWED_CLIENTS = [
    "916206757181", 
]

def ask_gemini(user_prompt):
    system_instruction = (
        "आप ApexLocal Media के एक प्रोफेशनल और कुशल बिजनेस AI असिस्टेंट हैं। "
        "आपका उद्देश्य केवल बिजनेस क्लाइंट्स को उनकी पूछताछ, सेवाओं और बुकिंग में सहायता करना है। "
        "हमेशा विनम्र, सटीक और संक्षिप्त व्यावसायिक हिंदी/हिंग्लिश में उत्तर दें।"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config={"system_instruction": system_instruction}
    )
    return response.text

def send_whatsapp_message(to_number, message_text):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text}
    }
    requests.post(url, headers=headers, json=payload)

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return "No data", 400

    try:
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            msg = messages[0]
            from_number = msg.get("from")
            msg_type = msg.get("type")

            # स्ट्रिक्ट फ़िल्टर: केवल स्वीकृत बिजनेस क्लाइंट्स को ही जवाब दें
            if from_number not in ALLOWED_CLIENTS:
                return jsonify({"status": "ignored_non_client"}), 200

            if msg_type == "text":
                user_text = msg.get("text", {}).get("body", "")
                ai_reply = ask_gemini(user_text)
                send_whatsapp_message(from_number, ai_reply)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 200

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
      
