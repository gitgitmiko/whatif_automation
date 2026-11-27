"""Writes the n8n analytics workflow: analytics-workflow.json (token masked, for the repo) and
analytics-workflow.import.json (real token, gitignored) for `n8n import:workflow`.

Every morning at 05:30 WIB, before the 06:00 idea research, it asks YouTube Analytics for each video's totals and,
for the videos uploaded in the last 30 days, their audience retention curve, and hands both to server.py
(data/analytics/). It signs in with the n8n credential "Google account" (id d9tDBy3bXzQglgXa, Google OAuth2 API,
scopes yt-analytics.readonly + youtube.readonly), which the channel owner connects once in the n8n UI."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "http://172.18.0.1:8798"
CRED = {"googleOAuth2Api": {"id": "d9tDBy3bXzQglgXa", "name": "Google account"}}
REPORTS = "https://youtubeanalytics.googleapis.com/v2/reports"
FROM = "2026-11-01"
TODAY = "={{ $now.setZone('Asia/Jakarta').toFormat('yyyy-MM-dd') }}"


def header():
    return {"parameters": [{"name": "X-Token", "value": "<SERVICE_TOKEN>"}]}


def node(i, name, kind, version, pos, params, **extra):
    return {"id": f"a{i}", "name": name, "type": f"n8n-nodes-base.{kind}", "typeVersion": version, "position": pos,
            "parameters": params, **extra}


def report(i, name, pos, query):
    return node(i, name, "httpRequest", 4.2, pos, {
        "url": REPORTS, "authentication": "predefinedCredentialType", "nodeCredentialType": "googleOAuth2Api",
        "sendQuery": True, "queryParameters": {"parameters": [{"name": k, "value": v} for k, v in query.items()]},
        "options": {"timeout": 60000}}, credentials=CRED, onError="continueRegularOutput")


def post(i, name, pos, path, body, **extra):
    # server.py (http.server) closes each connection after replying; n8n sometimes reuses it and gets ECONNRESET,
    # so a failed POST is simply tried again on a fresh connection.
    return node(i, name, "httpRequest", 4.2, pos, {
        "method": "POST", "url": f"{API}{path}", "sendHeaders": True, "headerParameters": header(),
        "sendBody": True, "specifyBody": "json", "jsonBody": body, "options": {}},
        retryOnFail=True, maxTries=3, waitBetweenTries=2000, **extra)


nodes = [
    node(1, "Jadwal 05:30", "scheduleTrigger", 1.2, [0, 0], {"rule": {"interval": [
        {"field": "cronExpression", "expression": "30 5 * * *"}]}}),
    node(2, "Tes manual", "manualTrigger", 1, [0, 200], {}),
    # Lets server-side tooling run it on demand (n8n execute clashes with the running instance).
    node(8, "Jalankan via webhook", "webhook", 2, [0, 400], {"path": "gimana-analytics-30ba541f9403", "httpMethod": "GET",
                                                            "responseMode": "onReceived", "options": {}}, webhookId="gimana-analytics-run"),
    report(3, "Laporan per video", [240, 100], {
        "ids": "channel==MINE", "startDate": FROM, "endDate": TODAY, "dimensions": "video", "sort": "-views",
        "maxResults": "200", "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
                                        "likes,comments,shares,subscribersGained"}),
    post(4, "Kirim ke server", [480, 100], "/api/stats", "={{ JSON.stringify({ report: $json }) }}"),
    node(5, "Video 30 hari", "httpRequest", 4.2, [720, 100], {
        "url": f"{API}/api/stats/targets", "sendHeaders": True, "headerParameters": header(), "options": {}}),
    report(6, "Retensi", [960, 100], {
        "ids": "channel==MINE", "startDate": FROM, "endDate": TODAY, "dimensions": "elapsedVideoTimeRatio",
        "metrics": "audienceWatchRatio,relativeRetentionPerformance", "filters": "=video=={{ $json.youtube_id }}"}),
    post(7, "Kirim retensi", [1200, 100], "/api/stats/retention",
         "={{ JSON.stringify({ youtube_id: $('Video 30 hari').item.json.youtube_id, report: $json }) }}",
         onError="continueRegularOutput"),  # one video that still fails must not stop the others
]
connections = {"Jadwal 05:30": [["Laporan per video"]], "Tes manual": [["Laporan per video"]],
               "Jalankan via webhook": [["Laporan per video"]],
               "Laporan per video": [["Kirim ke server"]], "Kirim ke server": [["Video 30 hari"]],
               "Video 30 hari": [["Retensi"]], "Retensi": [["Kirim retensi"]]}
workflow = {
    "id": "gimana-analytics", "name": "GIMANA JADINYA? — Analytics harian 05:30", "active": True,
    "nodes": nodes,
    "connections": {k: {"main": [[{"node": n, "type": "main", "index": 0} for n in out] for out in v]}
                    for k, v in connections.items()},
    "settings": {"executionOrder": "v1", "timezone": "Asia/Jakarta", "saveManualExecutions": True},
}
token = next(l.split("=", 1)[1] for l in (ROOT / ".env").read_text().split() if l.startswith("SERVICE_TOKEN="))
text = json.dumps(workflow, ensure_ascii=False, indent=1)
(ROOT / "n8n" / "analytics-workflow.json").write_text(text.replace("<SERVICE_TOKEN>", "<SERVICE_TOKEN dari .env>"))
(ROOT / "n8n" / "analytics-workflow.import.json").write_text(text.replace("<SERVICE_TOKEN>", token))
print("written")
