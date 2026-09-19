
# 幂等：删除同一个任务两次，第二次应该 404
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "删除两次", "done": false }
HTTP 201
[Captures]
task_id: jsonpath "$.id"

DELETE http://127.0.0.1:8000/tasks/{{task_id}}
Authorization: Bearer {{token}}
HTTP 204

DELETE http://127.0.0.1:8000/tasks/{{task_id}}
Authorization: Bearer {{token}}
HTTP 404
