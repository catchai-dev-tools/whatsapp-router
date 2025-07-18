import os
import json
import threading
import logging
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, make_response
import requests
from datetime import datetime

app = Flask(__name__)
CONFIG_DIR = os.path.abspath(os.path.dirname(__file__))
LOGS = []  # In-memory log for UI

# Configure logging
logger = logging.getLogger("whatsapp_router")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Console handler
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

# In-memory handler for UI
class UILogHandler(logging.Handler):
    def emit(self, record):
        entry = self.format(record)
        LOGS.append(entry)
        if len(LOGS) > 200:
            LOGS.pop(0)

ui_handler = UILogHandler()
ui_handler.setFormatter(formatter)
logger.addHandler(ui_handler)


# HTML template for account config UI
UI_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>WhatsApp Router Accounts</title>
    <style>
        body { font-family: Arial; margin: 2em; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; }
        th { background: #eee; }
        input[type=text] { width: 98%; }
        .log { background: #222; color: #eee; padding: 1em; margin-top: 2em; height: 200px; overflow: auto; }
    </style>
</head>
<body>
<h2>WhatsApp Accounts</h2>
<table>
<tr><th>App ID</th><th>Phone ID</th><th>Secret</th><th>Token</th><th>n8n Webhook</th><th>Actions</th></tr>
{% for acc in accounts %}
<tr>
<form method="POST" action="/accounts">
<td><input type="text" name="appid" value="{{ acc['appid'] }}" readonly></td>
<td><input type="text" name="phoneid" value="{{ acc.get('phoneid', '') }}"></td>
<td><input type="text" name="secret" value="{{ acc['secret'] }}"></td>
<td><input type="text" name="token" value="{{ acc['token'] }}"></td>
<td><input type="text" name="n8n_webhook" value="{{ acc['n8n_webhook'] }}"></td>
<td><button type="submit">Save</button></td>
</form>
<form method="POST" action="/accounts/delete" style="display:inline;">
<input type="hidden" name="phoneid" value="{{ acc['phoneid'] }}">
<td><button type="submit">Delete</button></td>
</form>
</tr>
{% endfor %}
<tr><form method="POST" action="/accounts">
<td><input type="text" name="appid"></td>
<td><input type="text" name="phoneid"></td>
<td><input type="text" name="secret"></td>
<td><input type="text" name="token"></td>
<td><input type="text" name="n8n_webhook"></td>
<td><button type="submit">Add</button></td>
</form></tr>
</table>

<h2>Logs</h2>
<div class="log">{% for l in logs %}{{ l }}<br>{% endfor %}</div>
</body>
</html>
'''



def config_path(phoneid):
    return os.path.join(CONFIG_DIR, f"config_{phoneid}.json")

def load_accounts():
    accounts = []
    for fname in os.listdir(CONFIG_DIR):
        if fname.startswith("config_") and fname.endswith(".json"):
            with open(os.path.join(CONFIG_DIR, fname)) as f:
                acc = json.load(f)
                # Ensure phoneid is present for legacy configs
                if 'phoneid' not in acc:
                    acc['phoneid'] = ''
                accounts.append(acc)
    return accounts

def save_account(acc):
    # Always save all fields, including phoneid
    if not acc.get('phoneid'):
        raise ValueError('phoneid is required to save account')
    with open(config_path(acc['phoneid']), 'w') as f:
        json.dump(acc, f)


def delete_account(phoneid):
    try:
        os.remove(config_path(phoneid))
    except FileNotFoundError:
        pass

@app.route('/webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    logger.info(f"Request received from {request.remote_addr} with data {request.data}")
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        verify_token = 1234
        # Log values being checked
        logger.info(f"mode: {mode}, token: {token}, challenge: {challenge}, verify_token: {verify_token} (type: {type(verify_token)})")
        if mode is not None and token is not None and mode == 'subscribe' and token == str(verify_token):
            logger.info("Webhook verified")
            return challenge or '', 200 
        else:
            logger.info("Webhook verification failed (details above)")
            return "Verification failed", 403
    elif request.method == 'POST':
        json_data = request.get_json(force=True)
        logger.info(f"POST received from {request.remote_addr}")
        
        # Extract phone_number_id if present
        phone_number_id = None
        try:
            phone_number_id = json_data["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
        except (KeyError, IndexError, TypeError):
            pass
        logger.info(f"phone_number_id: {phone_number_id}")

        # Route: find account with matching phoneid
        accounts = load_accounts()
        matched = next((acc for acc in accounts if acc.get('phoneid') == str(phone_number_id)), None)
        if matched and matched.get('n8n_webhook'):
            try:
                resp = requests.post(matched['n8n_webhook'], json=json_data, timeout=10)
                logger.info(f"Forwarded to {matched['n8n_webhook']} (status: {resp.status_code})")
            except Exception as e:
                logger.error(f"Error forwarding to {matched['n8n_webhook']}: {e}")
        else:
            logger.info("No matching account or webhook for this phone_number_id")
        return '', 200

@app.route('/accounts', methods=['GET', 'POST'])
def accounts_ui():
    logger.info(f"UI request: {request.method} {request.path} | form: {dict(request.form)}")
    if request.method == 'POST':
        appid = request.form.get('appid', '').strip()
        phoneid = request.form.get('phoneid', '').strip()
        secret = request.form.get('secret', '').strip()
        token = request.form.get('token', '').strip()
        n8n_webhook = request.form.get('n8n_webhook', '').strip()
        logger.info(f"Received POST to /accounts: appid={appid}, phoneid={phoneid}, secret={'***' if secret else ''}, token={'***' if token else ''}, n8n_webhook={n8n_webhook}")
        if phoneid:
            acc = {'appid': appid, 'phoneid': phoneid, 'secret': secret, 'token': token, 'n8n_webhook': n8n_webhook}
            save_account(acc)
            logger.info(f"Account saved: phoneid={phoneid}")
        return redirect(url_for('accounts_ui'))
    accounts = load_accounts()
    response = make_response(render_template_string(UI_TEMPLATE, accounts=accounts, logs=LOGS))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/accounts/delete', methods=['POST'])
def delete_account_route():
    logger.info(f"UI request: {request.method} {request.path} | form: {dict(request.form)}")
    phoneid = request.form.get('phoneid', '').strip()
    logger.info(f"Received POST to /accounts/delete: phoneid={phoneid}")
    if phoneid:
        delete_account(phoneid)
        logger.info(f"Account deleted: phoneid={phoneid}")
    return redirect(url_for('accounts_ui'))

@app.route('/')
def index():
    response = make_response(redirect(url_for('accounts_ui')))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    logger.info(f"UI request: {request.method} {request.path}")
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
