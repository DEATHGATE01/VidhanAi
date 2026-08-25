"""Assemble new-bill-alerts-workflow.json from alerts_email_code.js (valid JSON guaranteed)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "alerts_email_code.js"), encoding="utf-8") as f:
    JS = f.read()

wf = {
    "name": "VidhanAI - New Bill & Status Alerts",
    "nodes": [
        {
            "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}},
            "id": "wf-alerts-01",
            "name": "Every hour",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [-260, 0],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://127.0.0.1:5000/api/check-new-bills",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify({ lookback_hours: 25 }) }}",
                "options": {"timeout": 120000},
            },
            "id": "wf-alerts-02",
            "name": "Check backend for alerts",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [-40, 0],
        },
        {
            "parameters": {"mode": "runOnceForAllItems", "jsCode": JS},
            "id": "wf-alerts-03",
            "name": "Build alert emails",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [180, 0],
        },
        {
            "parameters": {
                "fromEmail": "vidhanai-alerts@example.com",
                "toEmail": "={{ $json.email }}",
                "subject": "=VidhanAI | {{ $json.subject }}",
                "emailFormat": "html",
                "html": "={{ $json.html }}",
                "options": {},
            },
            "id": "wf-alerts-04",
            "name": "Send email",
            "type": "n8n-nodes-base.emailSend",
            "typeVersion": 2.1,
            "position": [400, 0],
        },
    ],
    "connections": {
        "Every hour": {"main": [[{"node": "Check backend for alerts", "type": "main", "index": 0}]]},
        "Check backend for alerts": {"main": [[{"node": "Build alert emails", "type": "main", "index": 0}]]},
        "Build alert emails": {"main": [[{"node": "Send email", "type": "main", "index": 0}]]},
    },
    "settings": {"executionOrder": "v1"},
    "active": False,
}

out = os.path.join(HERE, "new-bill-alerts-workflow.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)
print("written", out)
