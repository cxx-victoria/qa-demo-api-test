
# 异常：伪造一个 token，期望 401
POST http://127.0.0.1:8000/tasks
Authorization: Bearer fake-token-1234567890
Content-Type: application/json
{ "title": "伪造 token", "done": false }
HTTP 401
