"""Writes the n8n upload workflow: whatif-workflow.json (token masked, for the repo) and
whatif-workflow.import.json (real token, gitignored) for `n8n import:workflow`."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "http://172.18.0.1:8798"
YT_CRED = {"youTubeOAuth2Api": {"id": "jangansendirian-youtube", "name": "YouTube Jangan Sendirian"}}  # horror channel
READY = "$('Cek video siap').item.json.body"


def header():
    return {"parameters": [{"name": "X-Token", "value": "<SERVICE_TOKEN>"}]}


def node(i, name, kind, version, pos, params, **extra):
    return {"id": f"w{i}", "name": name, "type": f"n8n-nodes-base.{kind}", "typeVersion": version, "position": pos,
            "parameters": params, **extra}


def mark(i, name, pos, what, body):
    return node(i, name, "httpRequest", 4.2, pos, {
        "method": "POST", "url": f"={API}/api/videos/{{{{ {READY}.id }}}}/{what}", "sendHeaders": True,
        "headerParameters": header(), "sendBody": True, "specifyBody": "json", "jsonBody": body, "options": {}})


nodes = [
    node(1, "Jadwal", "scheduleTrigger", 1.2, [0, 0], {"rule": {"interval": [
        {"field": "cronExpression", "expression": e} for e in ("0 12 * * *", "30 12 * * *", "0 18 * * *", "30 18 * * *")]}}),
    node(2, "Tes manual", "manualTrigger", 1, [0, 200], {}),
    node(3, "Pengaturan", "code", 2, [240, 100], {"jsCode":
        "// 12:00/12:30 upload the 'siang' video, 18:00/18:30 the 'sore' one (the :30 run is a retry: it finds nothing if :00 worked).\n"
        "// Change privacy to 'unlisted' or 'private' to review videos before they go public.\n"
        "const hour = $now.setZone('Asia/Jakarta').hour;\n"
        "return [{ json: { slot: hour < 15 ? 'siang' : 'sore', privacy: 'public' } }];"}),
    node(4, "Cek video siap", "httpRequest", 4.2, [480, 100], {
        "url": f"={API}/api/ready?slot={{{{ $json.slot }}}}", "sendHeaders": True, "headerParameters": header(),
        "options": {"timeout": 30000, "response": {"response": {"fullResponse": True, "neverError": True}}}}),
    node(5, "Ada video?", "if", 2, [720, 100], {"conditions": {
        "options": {"caseSensitive": True, "typeValidation": "loose"}, "combinator": "and",
        "conditions": [{"id": "c1", "leftValue": "={{ $json.statusCode }}", "rightValue": 200,
                        "operator": {"type": "number", "operation": "equals"}}]}, "options": {}}),
    node(6, "Ambil video", "httpRequest", 4.2, [960, 0], {
        "url": "={{ $json.body.video_url }}", "sendHeaders": True, "headerParameters": header(),
        "options": {"timeout": 600000, "response": {"response": {"responseFormat": "file", "outputPropertyName": "data"}}}}),
    node(7, "Upload YouTube", "youTube", 1, [1200, 0], {
        "resource": "video", "operation": "upload", "title": f"={{{{ {READY}.title }}}}", "regionCode": "ID",
        "categoryId": "27", "binaryProperty": "data", "options": {
            "description": f"={{{{ {READY}.description }}}}", "tags": f"={{{{ {READY}.tags.join(',') }}}}",
            "privacyStatus": "={{ $('Pengaturan').item.json.privacy }}", "defaultLanguage": "id",
            "selfDeclaredMadeForKids": False, "notifySubscribers": True}},
        onError="continueErrorOutput", credentials=YT_CRED),
    mark(8, "Tandai terupload", [1440, -100], "uploaded", "={{ JSON.stringify({ youtube_id: $json.uploadId ?? $json.id }) }}"),
    mark(9, "Tandai gagal", [1440, 100], "failed",
         "={{ JSON.stringify({ error: $json.error?.message ?? String($json.error ?? 'upload failed') }) }}"),
    node(10, "Ada thumbnail?", "if", 2, [1680, -100], {"conditions": {
        "options": {"caseSensitive": True, "typeValidation": "loose"}, "combinator": "and",
        "conditions": [{"id": "c2", "leftValue": f"={{{{ {READY}.thumbnail_url }}}}", "rightValue": "",
                        "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}}]}, "options": {}}),
    node(11, "Ambil thumbnail", "httpRequest", 4.2, [1920, -200], {
        "url": f"={{{{ {READY}.thumbnail_url }}}}", "sendHeaders": True, "headerParameters": header(),
        "options": {"timeout": 60000, "response": {"response": {"responseFormat": "file", "outputPropertyName": "data"}}}}),
    # Custom thumbnails need a verified channel; if YouTube refuses, the video simply keeps its own.
    node(12, "Pasang thumbnail", "httpRequest", 4.2, [2160, -200], {
        "method": "POST",
        "url": "=https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={{ $('Upload YouTube').item.json.uploadId ?? $('Upload YouTube').item.json.id }}",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "youTubeOAuth2Api",
        "sendBody": True, "contentType": "binaryData", "inputDataFieldName": "data", "options": {}},
        onError="continueRegularOutput", credentials=YT_CRED),
]
connections = {
    "Jadwal": [["Pengaturan"]], "Tes manual": [["Pengaturan"]], "Pengaturan": [["Cek video siap"]],
    "Cek video siap": [["Ada video?"]], "Ada video?": [["Ambil video"], []], "Ambil video": [["Upload YouTube"]],
    "Upload YouTube": [["Tandai terupload"], ["Tandai gagal"]], "Tandai terupload": [["Ada thumbnail?"]],
    "Ada thumbnail?": [["Ambil thumbnail"], []], "Ambil thumbnail": [["Pasang thumbnail"]],
}
workflow = {
    "id": "whatif-longform", "name": "JANGAN SENDIRIAN — horor POV 5-8 menit (12:00)", "active": True,
    "nodes": nodes,
    "connections": {k: {"main": [[{"node": n, "type": "main", "index": 0} for n in out] for out in v]}
                    for k, v in connections.items()},
    "settings": {"executionOrder": "v1", "timezone": "Asia/Jakarta", "saveManualExecutions": True},
}
token = next(l.split("=", 1)[1] for l in (ROOT / ".env").read_text().split() if l.startswith("SERVICE_TOKEN="))
text = json.dumps(workflow, ensure_ascii=False, indent=1)
(ROOT / "n8n" / "whatif-workflow.json").write_text(text.replace("<SERVICE_TOKEN>", "<SERVICE_TOKEN dari .env>"))
(ROOT / "n8n" / "whatif-workflow.import.json").write_text(text.replace("<SERVICE_TOKEN>", token))
print("written")
