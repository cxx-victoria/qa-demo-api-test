
# 异常：创建任务时不带 Authorization，期望 401
POST http://127.0.0.1:8000/tasks
Content-Type: application/json
{ "title": "没有 token", "done": false }
HTTP 401
