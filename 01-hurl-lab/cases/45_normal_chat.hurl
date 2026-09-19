# 正常：调用大模型问答接口（没配 Key 时会返回兜底回答）
POST http://127.0.0.1:8000/chat
Content-Type: application/json
{ "q": "你们的退货政策是什么？" }
HTTP 200
[Asserts]
jsonpath "$.answer" isString