
# 异常：分页参数 limit 传 0（文档要求 >=1），期望 422
GET http://127.0.0.1:8000/tasks?limit=0
HTTP 422
