# 📝 AWS Serverless Todo App

A fully serverless **Todo Application** built using:
- **AWS Lambda** (Python)
- **API Gateway (HTTP API)**
- **Amazon DynamoDB**
- **Amazon S3 (Frontend Hosting)**  

This project performs full CRUD operations — add, view, update, and delete todos — using DynamoDB as the database and API Gateway as the interface.

---

## 🚀 Architecture Overview

```
Frontend (S3 / Local Apache)
↓
API Gateway (HTTP API)
↓
AWS Lambda
↓
DynamoDB Table
```

---

## 🛠️ 1. Create DynamoDB Table

1. Go to **AWS Console → DynamoDB → Create Table**
2. Enter:
   - **Table name:** `Todos`
   - **Partition key:** `id` (String)
3. Keep all other settings as default and create the table.

---

## 🔑 2. Create IAM Role for Lambda

1. Navigate to **IAM → Roles → Create role**
2. Select **AWS Service → Lambda**
3. Attach these permissions:
   - `AmazonDynamoDBFullAccess`
   - `CloudWatchLogsFullAccess`
4. Name the role **LambdaTodoRole**
5. Click **Create role**

✅ This allows Lambda to access DynamoDB and write logs to CloudWatch.

---

## 🧠 3. Create Lambda Function

1. Go to **Lambda → Create Function**
   - Name: `todoHandler`
   - Runtime: `Python 3.12`
   - Permissions: **Use existing role** → `LambdaTodoRole`
2. Replace the default code with the following:

```python
import json
import boto3
import uuid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Todos')

def lambda_handler(event, context):
    method = event['requestContext']['http']['method']

    # ✅ Handle CORS preflight
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({'message': 'CORS preflight OK'})
        }

    if method == 'GET':
        result = table.scan()
        return response(200, result['Items'])

    elif method == 'POST':
        data = json.loads(event['body'])
        item = {
            'id': str(uuid.uuid4()),
            'title': data['title'],
            'completed': False
        }
        table.put_item(Item=item)
        return response(200, item)

    elif method == 'PUT':
        data = json.loads(event['body'])
        table.update_item(
            Key={'id': data['id']},
            UpdateExpression="SET completed = :val",
            ExpressionAttributeValues={':val': data['completed']}
        )
        updated = table.get_item(Key={'id': data['id']})
        return response(200, updated['Item'])

    elif method == 'DELETE':
        data = json.loads(event['body'])
        table.delete_item(Key={'id': data['id']})
        return response(200, {'message': 'Deleted', 'id': data['id']})

    else:
        return response(400, {'error': 'Unsupported method'})


def response(status, body):
    return {
        'statusCode': status,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body)
    }
```

3. Click **Deploy**.

✅ Your Lambda is ready to connect to API Gateway.

---

## 🌐 4. Configure API Gateway (HTTP API)

1. Go to **API Gateway → Create API → HTTP API → Build**
2. API Name: `todo-api`
3. Integration: **Add Integration → Lambda → todoHandler**
4. Add routes:

   * `GET /todos`
   * `POST /todos`
   * `PUT /todos`
   * `DELETE /todos`
5. Enable **CORS**:

   * Allowed Origins: `*`
   * Allowed Methods: `OPTIONS,GET,POST,PUT,DELETE`
   * Allowed Headers: `Content-Type`
6. Stage:

   * Use `$default` (Auto Deploy: ON)
7. Click **Create**.

Your API will generate an **Invoke URL** like:

```
https://<api-id>.execute-api.ap-south-1.amazonaws.com/todos
```

---

## 🔍 5. Test API

### GET (View all todos)

```bash
curl https://<api-id>.execute-api.ap-south-1.amazonaws.com/todos
```

### POST (Add a new todo)

```bash
curl -X POST https://<api-id>.execute-api.ap-south-1.amazonaws.com/todos \
-H "Content-Type: application/json" \
-d '{"title": "Buy groceries"}'
```

---

## 💻 6. Frontend (index.html)

Create an `index.html` file for your UI:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Todo App</title>
  <style>
    body { font-family: "Segoe UI", sans-serif; background:#f6f8fa; display:flex; justify-content:center; align-items:flex-start; min-height:100vh; margin:0; padding:40px; }
    .container { background:white; padding:25px 30px; border-radius:12px; box-shadow:0 3px 10px rgba(0,0,0,0.1); width:400px; }
    h1 { text-align:center; color:#333; margin-bottom:20px; }
    .input-row { display:flex; gap:10px; }
    input { flex:1; padding:10px; border:1px solid #ccc; border-radius:6px; font-size:16px; }
    button { background-color:#0078d7; color:white; border:none; border-radius:6px; padding:10px 15px; cursor:pointer; }
    button:hover { background-color:#005fa3; }
    ul { list-style:none; padding:0; margin-top:20px; }
    li { display:flex; justify-content:space-between; align-items:center; padding:10px; border-bottom:1px solid #eee; }
    li.completed span { text-decoration:line-through; color:#999; }
    .btn-delete { background:#dc3545; border:none; color:white; padding:6px 10px; border-radius:6px; cursor:pointer; font-size:13px; }
    .btn-delete:hover { background:#a71d2a; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Todo List</h1>
    <div class="input-row">
      <input id="todoInput" type="text" placeholder="Add a new task" />
      <button onclick="addTodo()">Add</button>
    </div>
    <ul id="todoList"></ul>
  </div>

  <script>
    const API_URL = "https://<api-id>.execute-api.ap-south-1.amazonaws.com/todos";

    async function loadTodos() {
      const res = await fetch(API_URL);
      const todos = await res.json();
      const list = document.getElementById("todoList");
      list.innerHTML = "";
      todos.forEach(todo => {
        const li = document.createElement("li");
        li.className = todo.completed ? "completed" : "";
        const span = document.createElement("span");
        span.textContent = todo.title;
        span.onclick = () => toggle(todo);
        const del = document.createElement("button");
        del.textContent = "Delete";
        del.className = "btn-delete";
        del.onclick = () => delTodo(todo.id);
        li.appendChild(span);
        li.appendChild(del);
        list.appendChild(li);
      });
    }

    async function addTodo() {
      const input = document.getElementById("todoInput");
      const title = input.value.trim();
      if (!title) return alert("Please enter a task");
      await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title })
      });
      input.value = "";
      loadTodos();
    }

    async function toggle(todo) {
      await fetch(API_URL, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: todo.id, completed: !todo.completed })
      });
      loadTodos();
    }

    async function delTodo(id) {
      await fetch(API_URL, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id })
      });
      loadTodos();
    }

    loadTodos();
  </script>
</body>
</html>
```

Replace `API_URL` with your real API endpoint.

---

## ☁️ 7. Host Frontend on S3

1. Go to **S3 → Create bucket**

   * Bucket name: `todo-frontend-yourname`
   * Region: same as Lambda (recommended)
   * Disable “Block all public access”
   * Enable **Static website hosting**
2. Upload your `index.html`
3. Bucket policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::todo-frontend-yourname/*"
  }]
}
```

4. Copy your **S3 website URL** and open it in your browser.

✅ Your Todo App is now live!

---

## 🧪 Features

* Add new tasks
* View all tasks
* Toggle completed tasks
* Delete tasks
* All data stored in DynamoDB
* CORS enabled (can call from local or S3 frontend)

---

## 🧾 Technologies Used

* **AWS Lambda (Python 3.12)**
* **Amazon DynamoDB**
* **Amazon API Gateway (HTTP API)**
* **Amazon S3 (Static Website Hosting)**
* **HTML, CSS, JavaScript**

---

## 🔒 Future Improvements

* Add authentication (Cognito or IAM)
* Add pagination and filtering in DynamoDB
* Add CloudFront distribution with HTTPS
* Add CI/CD using AWS CodePipeline or GitHub Actions

---

## 👨‍💻 Author

**Manish Sharma**
*AWS & DevOps Enthusiast*
📧 [manish.sharma.devops@gmail.com](mailto:manish.sharma.devops@gmail.com)


---

If you'd like, I can now add badges (AWS, Python, HTML), a small architecture SVG/diagram, or a one-click Deploy-to-AWS guide — tell me which items to add and I'll update `README.md` accordingly.
