# 项目3：Schemathesis OpenAPI契约测试项目
> 项目背景：基于demo‑api服务（FastAPI），使用 **Schemathesis 4.27.5** 完成契约测试（属性化测试 Property‑Based Testing）。
> 被测服务地址：`http://127.0.0.1:8000`
> OpenAPI契约地址：`http://127.0.0.1:8000/openapi.json`

## 一、项目目标
1. 利用OpenAPI接口契约，自动生成大量边界、畸形测试用例，完成接口容错测试；
2. 区分失败类型：**真缺陷、契约缺失、工具误报、框架细节问题**；
3. 产出JUnit / JSON / Allure测试报告；
4. 将Schemathesis集成到pytest，和手工测试用例统一执行，适配CI流程；
5. 分析工具能力边界，输出对后端开发的契约改进建议。

## 二、环境准备
### 2.1 启动被测demo‑api服务
打开终端A，启动后端服务：
```powershell
cd D:\qa-projects\00-demo-api
.\.venv\Scripts\Activate.ps1
uvicorn app:app --port 8000
