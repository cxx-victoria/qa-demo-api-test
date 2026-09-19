

# 业务流：查询一个不存在的任务，期望返回 404
GET http://127.0.0.1:8000/tasks/this-id-does-not-exist
HTTP 404
