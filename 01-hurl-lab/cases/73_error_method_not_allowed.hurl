
# 异常：用不支持的方法访问接口，期望 405
PUT http://127.0.0.1:8000/tasks
Content-Type: application/json
{ "title": "方法不对" }
HTTP 405
