from __future__ import annotations

import logging

from langbot_plugin.api.definition.components.page import Page, PageRequest, PageResponse


logger = logging.getLogger(__name__)


class OracleAdminPage(Page):
    """OracleLang admin dashboard page — read-only stats and user summary."""

    async def handle_api(self, request: PageRequest) -> PageResponse:
        if request.method == "GET" and request.endpoint == "/stats":
            return await self._get_stats()
        elif request.method == "GET" and request.endpoint == "/users":
            return await self._get_users()
        elif request.method == "GET" and request.endpoint == "/":
            return PageResponse.ok(data=self._render_dashboard())
        return PageResponse.fail("Unknown endpoint")

    # ------------------------------------------------------------------
    # API handlers
    # ------------------------------------------------------------------

    async def _get_stats(self) -> PageResponse:
        try:
            limit = self.plugin.limit  # type: ignore[attr-defined]
            stats = limit.get_usage_statistics()
            reset_time = limit.get_reset_time()

            return PageResponse.ok(data={
                "total_users": stats["total_users"],
                "today_usage": stats["total_usage"],
                "active_users": stats["total_users"],
                "reset_time": reset_time,
            })
        except Exception as e:
            logger.exception("Failed to load stats")
            return PageResponse.fail(str(e))

    async def _get_users(self) -> PageResponse:
        try:
            limit = self.plugin.limit  # type: ignore[attr-defined]
            stats = limit.get_usage_statistics()

            return PageResponse.ok(data={
                "users": [],
                "total_users": stats["total_users"],
            })
        except Exception as e:
            logger.exception("Failed to load users")
            return PageResponse.fail(str(e))

    # ------------------------------------------------------------------
    # Dashboard HTML (static — JS fetches /stats via api/stats)
    # ------------------------------------------------------------------

    def _render_dashboard(self) -> str:
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>OracleLang 管理面板</title>
<style>
  :root {
    --bg: #0f172a;
    --card-bg: #1e293b;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --accent: #fbbf24;
    --error-bg: #451a1a;
    --error-text: #f87171;
    --radius: 0.5rem;
  }
  * { margin:0;padding:0;box-sizing:border-box; }
  body {
    font-family: system-ui,sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 2rem;
    min-height: 100vh;
  }
  h1 { font-size:1.5rem;margin-bottom:1.5rem;color:#f8fafc; }
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fit,minmax(200px,1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }
  .card {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 1.25rem;
    transition: transform .15s ease;
  }
  .card:hover { transform: translateY(-2px); }
  .card-title {
    font-size: .75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: .05em;
    margin-bottom: .5rem;
  }
  .card-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--accent);
    font-variant-numeric: tabular-nums;
  }
  .error {
    color: var(--error-text);
    background: var(--error-bg);
    padding: 1rem;
    border-radius: var(--radius);
    display: none;
  }
  .spinner {
    display: inline-block;
    width: 1.25rem;
    height: 1.25rem;
    border: 2px solid var(--text-muted);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin .6s linear infinite;
    vertical-align: middle;
    margin-right: .5rem;
  }
  @keyframes spin { to { transform:rotate(360deg); } }
</style>
</head>
<body>
  <h1>🔮 OracleLang 管理面板</h1>

  <div class="cards">
    <div class="card">
      <div class="card-title">总用户数</div>
      <div class="card-value" id="totalUsers">-</div>
    </div>
    <div class="card">
      <div class="card-title">今日使用次数</div>
      <div class="card-value" id="todayUsage">-</div>
    </div>
    <div class="card">
      <div class="card-title">活跃用户</div>
      <div class="card-value" id="activeUsers">-</div>
    </div>
    <div class="card">
      <div class="card-title">下次重置</div>
      <div class="card-value" id="resetTime">-</div>
    </div>
  </div>

  <div id="error" class="error"></div>

<script>
async function loadStats(){
  try {
    var resp = await fetch('api/stats');
    var data = await resp.json();
    if (data.error){ showError(data.error); return; }
    document.getElementById('totalUsers').textContent = data.total_users;
    document.getElementById('todayUsage').textContent  = data.today_usage;
    document.getElementById('activeUsers').textContent = data.active_users;
    document.getElementById('resetTime').textContent   = data.reset_time;
  } catch(e){ showError('加载失败: '+e.message); }
}
function showError(msg){
  var el = document.getElementById('error');
  el.textContent = msg;
  el.style.display = 'block';
}
loadStats();
</script>
</body>
</html>"""
