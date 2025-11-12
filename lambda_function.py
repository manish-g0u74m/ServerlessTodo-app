import json
import boto3
import uuid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Todos')

def lambda_handler(event, context):
    method = event['requestContext']['http']['method']

    # Handle CORS preflight
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
