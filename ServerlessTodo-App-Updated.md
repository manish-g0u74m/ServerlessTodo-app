# Serverless Todo App with Secured API (AWS Lambda + API Gateway + DynamoDB)

This repo shows a simple serverless Todo app (CRUD) with an HTTP API protected by a Lambda authorizer.
Frontend is a static site (S3 or local). Backend is API Gateway (HTTP API) → Lambda → DynamoDB.

## Architecture

```
Frontend (S3 / local)
↓
API Gateway (HTTP API) + Lambda Authorizer
↓
AWS Lambda (todos)
↓
DynamoDB Table
```

## Required resources

- DynamoDB table Todos (partition key id string)
- Lambda function todoHandler (Python)
- Lambda function todoAuthorizer (Python) — HTTP API compatible
- API Gateway HTTP API with routes /todos and an OPTIONS /todos route (mock)
- S3 bucket for frontend (optional)

## Files you will need

- todo_handler.py — main Lambda (handles GET/POST/PUT/DELETE + CORS)
- todo_authorizer.py — Lambda Authorizer for HTTP API
- index.html — frontend that sends Authorization header
- README (this file)

## 1. DynamoDB table

Create table:

- Table name: Todos
- Partition key: id (String)
- Keep other defaults.

## 2. IAM role for Lambda

Create role LambdaTodoRole and attach at least:

- AmazonDynamoDBFullAccess (or scoped DynamoDB policy)
- CloudWatchLogsFullAccess (or scoped logging policy)

Assign the role to both Lambdas or create separate roles as needed.

## 3. todo_authorizer.py (HTTP API compatible)

This is the Lambda Authorizer you should use for API Gateway HTTP API.

```python
# todo_authorizer.py
import json

def lambda_handler(event, context):
    # log event for debugging
    print("Authorizer event:", json.dumps(event))

    # headers may come with different casing so check case-insensitively
    headers = event.get("headers") or {}
    token = None
    for k, v in headers.items():
        if k.lower() == "authorization":
            token = v
            break

    # Use a proper secret store (SSM, Secrets Manager) in production.
    VALID_TOKEN = "my-secret-token"

    if token == VALID_TOKEN:
        return {
            "isAuthorized": True,
            "context": {"user": "manish"}
        }
    else:
        return {"isAuthorized": False}
```

**Notes:**

- This returns isAuthorized only. This is required format for HTTP API Lambda authorizers.
- Replace my-secret-token with a value you store securely.

## 4. todo_handler.py (main Lambda)

This Lambda handles requests and returns CORS headers. It must allow Authorization in headers so browser requests succeed.

```python
# todo_handler.py
import json
import boto3
import uuid

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("Todos")

def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method")

    # Handle CORS preflight
    if method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    if method == "GET":
        result = table.scan()
        return response(200, result.get("Items", []))

    elif method == "POST":
        data = json.loads(event.get("body") or "{}")
        item = {"id": str(uuid.uuid4()), "title": data.get("title"), "completed": False}
        table.put_item(Item=item)
        return response(200, item)

    elif method == "PUT":
        data = json.loads(event.get("body") or "{}")
        table.update_item(
            Key={"id": data["id"]},
            UpdateExpression="SET completed = :val",
            ExpressionAttributeValues={":val": data["completed"]}
        )
        updated = table.get_item(Key={"id": data["id"]})
        return response(200, updated.get("Item"))

    elif method == "DELETE":
        data = json.loads(event.get("body") or "{}")
        table.delete_item(Key={"id": data["id"]})
        return response(200, {"message": "Deleted", "id": data["id"]})

    else:
        return response(400, {"error": "Unsupported method"})

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,DELETE"
    }

def response(status, body):
    return {
        "statusCode": status,
        "headers": cors_headers(),
        "body": json.dumps(body)
    }
```

**Important:**

- Access-Control-Allow-Headers must include Authorization so the browser preflight succeeds.
- Lambda returns these headers on normal responses and on OPTIONS.

## 5. API Gateway (HTTP API) setup

Create HTTP API.

Add integration → Lambda → choose todoHandler.

Add routes:

- GET /todos → integration todoHandler
- POST /todos → integration todoHandler
- PUT /todos → integration todoHandler
- DELETE /todos → integration todoHandler

Create authorizer:

- Type: Lambda
- Lambda function: todoAuthorizer
- Identity source: $route.request.header.Authorization
- Authorizer type: simple Lambda authorizer for HTTP API

Attach authorizer to the routes (GET/POST/PUT/DELETE).

Add an OPTIONS route for /todos:

- Route: OPTIONS /todos
- Integration: Mock integration

Configure the mock response to return HTTP 200 and add these headers:

- Access-Control-Allow-Origin: *
- Access-Control-Allow-Headers: Content-Type,Authorization
- Access-Control-Allow-Methods: OPTIONS,GET,POST,PUT,DELETE

Deploy / verify the $default stage auto deploy is enabled or deploy the stage.

**Why OPTIONS is needed:**

- Browser sends a preflight OPTIONS with Access-Control-Request-Headers: Authorization
- If API Gateway authorizer tried to validate this without an OPTIONS route, preflight may fail
- Mock OPTIONS returns CORS headers without invoking authorizer

## 6. Frontend (index.html)

This is the working index.html that includes Authorization header with requests. Replace API_URL and AUTH_TOKEN accordingly.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Todo App</title>
  <style>
    /* same styles as your app */
  </style>
</head>
<body>
  <div class="container">
    <h1>Todo List</h1>
    <div class="input-row">
      <input id="todoInput" placeholder="Add a new task" />
      <button onclick="addTodo()">Add</button>
    </div>
    <ul id="todoList"></ul>
  </div>

  <script>
    const API_URL = "https://<api-id>.execute-api.ap-south-1.amazonaws.com/todos";
    // store token securely in real app. This is for demo.
    const AUTH_TOKEN = "my-secret-token";

    async function loadTodos() {
      const res = await fetch(API_URL, {
        headers: { "Authorization": AUTH_TOKEN }
      });
      const todos = await res.json();
      render(todos);
    }

    async function addTodo() {
      const input = document.getElementById("todoInput");
      const title = input.value.trim();
      if (!title) return alert("Please enter a task");
      await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": AUTH_TOKEN
        },
        body: JSON.stringify({ title })
      });
      input.value = "";
      loadTodos();
    }

    async function toggle(todo) {
      await fetch(API_URL, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": AUTH_TOKEN
        },
        body: JSON.stringify({ id: todo.id, completed: !todo.completed })
      });
      loadTodos();
    }

    async function delTodo(id) {
      await fetch(API_URL, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "Authorization": AUTH_TOKEN
        },
        body: JSON.stringify({ id })
      });
      loadTodos();
    }

    function render(todos) {
      const list = document.getElementById("todoList");
      list.innerHTML = "";
      (todos || []).forEach(todo => {
        const li = document.createElement("li");
        li.className = todo.completed ? "completed" : "";
        const span = document.createElement("span");
        span.textContent = todo.title;
        span.onclick = () => toggle(todo);
        const del = document.createElement("button");
        del.textContent = "Delete";
        del.onclick = () => delTodo(todo.id);
        li.appendChild(span);
        li.appendChild(del);
        list.appendChild(li);
      });
    }

    loadTodos();
  </script>
</body>
</html>
```

## 7. Testing with Postman or curl

### GET all todos

**Postman:**

- Method: GET
- URL: https://<api-id>.execute-api.ap-south-1.amazonaws.com/todos
- Header:
  - Authorization: my-secret-token

**curl:**

```bash
curl -H "Authorization: my-secret-token" \
  https://<api-id>.execute-api.ap-south-1.amazonaws.com/todos
```

### POST (add todo)

**Postman:**

- Method: POST
- Header:
  - Content-Type: application/json
  - Authorization: my-secret-token
- Body raw JSON:
```json
{"title": "testing from postman"}
```

**curl:**

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: my-secret-token" \
  -d '{"title":"testing from curl"}' \
  https://<api-id>.execute-api.ap-south-1.amazonaws.com/todos
```

### PUT (update)

Use an id from GET response.

```bash
curl -X PUT \
  -H "Content-Type: application/json" \
  -H "Authorization: my-secret-token" \
  -d '{"id":"<id>","completed":true}' \
  https://<api-id>.execute-api.ap-south-1.amazonaws.com/todos
```

### DELETE

```bash
curl -X DELETE \
  -H "Content-Type: application/json" \
  -H "Authorization: my-secret-token" \
  -d '{"id":"<id>"}' \
  https://<api-id>.execute-api.ap-south-1.amazonaws.com/todos
```

## 8. Common troubleshooting

**Browser CORS error mentioning No 'Access-Control-Allow-Origin' header:**

- Ensure todo_handler returns CORS headers.
- Ensure OPTIONS /todos mock route exists and returns CORS headers.
- Ensure Access-Control-Allow-Headers includes Authorization.

**403 Forbidden in Postman:**

- Authorizer returned isAuthorized: False.
- Check that header key is Authorization and value matches authorizer.
- Check authorizer identity source is $route.request.header.Authorization.

**500 Internal Server Error when authorizer invoked:**

- Check CloudWatch logs for the authorizer Lambda.
- Ensure authorizer returns JSON with isAuthorized boolean for HTTP API.

## 9. Security notes

Do not store secrets inline in code for production. Use:

- AWS Secrets Manager
- AWS Systems Manager Parameter Store (secure string)
- Lambda environment variables (encrypted)

Consider using JWTs or Cognito for a real auth flow instead of a static token.

Scope IAM permissions narrowly. Avoid FullAccess in production.

## 10. Next steps (optional)

- Replace static token with JWT verification in todo_authorizer.
- Use Cognito or Auth0 and create a JWT authorizer or use built-in JWT Authorizer in API Gateway.
- Add a custom domain to API Gateway.
- Deploy everything with Terraform or CloudFormation.

## Contact / Author

Manish Sharma  
AWS & DevOps Enthusiast  
manish.sharma.devops@gmail.com
