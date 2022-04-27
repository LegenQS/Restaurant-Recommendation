# lambda function two is used to process the given data from lambda function one by SQS.
# Then send verification email to input email address, and with given input do elastic 
# search to find records with "id" and "type". Next use the elastic search outcome to 
# search in dynamoDB with primary key "id" and return the json format of the data.
# Finally send the searching outcome to user through SES (if not verified send to default).


import boto3
import json
import requests
import time
from requests_aws4auth import AWS4Auth
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    # load message from SQS
    message = sqs_load()
    
    # return if no message received
    if not message:
        print('sqs no messages')
        return
    print('sqs message received ')
    
    # test case
    # message = {'cuisine': 'halal', 'email': '654885451@qq.com', 'people': 3, 'time': '19:00', 'date': '2022-02-20'}
    # data = [{'id': 'h0pRCiJDrCN7tm3VX5tILQ'}, {'id': 'bVkjBJlAIwKAj9Aw1KVWjA'}, {'id': 'hNFe8WhCibrqT4sFcZmAgw'}, {'id': 'BNaveJmi-OUGKG9sRfrIhA'},
    # {'id': 'pCfGgX0WxGASGM4-Yhr2Pw'}]
    
    # verify email address
    verify(message['email'])
    
    # elastic search
    data = es_match(message)
    
    # # search in dynamoDB with result from elastic search
    record = lookup(key=data)

    # send suggestions to SES
    send_SES(record, cuisineType=message['cuisine'], people=message['people'], time=message['time'], date=message['date'])

    return 

def lookup(key, db=None, table='6998DB'):
    """
        look up data in dynamoDB with key-value set by format below:
        {
            'primary key': value,
            'primary key': value,
            ... ...
        }
        if nothing found in database, return an empty list, else return
        the found record by json format below:
        [
            {
                'field1': value1,
                'field2': value2,
                ... ...
            }, 
            {
                ... ...    
            }
        ]
    """
    
    result = []
    if not db:
        db = boto3.resource('dynamodb')
    table = db.Table(table)
    if len(key) == 0:
        return None
    
    for val in key:
        try:
            response = table.get_item(Key=val)
        except ClientError as e:
            continue
        try:
            response['Item']
            result.append(response['Item'])
        except:
            continue
    
    return result

def sqs_load():
    """
        return a dict of slots when there's a message in Queue:
        {
            "location": location,
            "cuisine": cuisine,
            "people": people,
            "date": date,
            "time": time,
            "phone": phone,
            "email": email
        }
        Otherwise return None
    """    
    
    # Create SQS client
    sqs = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/359634618028/Q1-test.fifo'

    # Receive message from SQS queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=60,
        WaitTimeSeconds=0
    )
    
    # no message in SQS
    if('Messages' not in response): 
        # print("No message now.")
        return None
    
    # received message content
    message = response['Messages'][0]
    
    # Delete received message from queue
    receipt_handle = message['ReceiptHandle']
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )

    sqs_msg = message
    location = sqs_msg['MessageAttributes']['location']['StringValue']
    cuisine = sqs_msg['MessageAttributes']['cuisine']['StringValue']
    people = sqs_msg['MessageAttributes']['people']['StringValue']
    date = sqs_msg['MessageAttributes']['date']['StringValue']
    time = sqs_msg['MessageAttributes']['time']['StringValue']
    phone = sqs_msg['MessageAttributes']['phone']['StringValue']
    email = sqs_msg['MessageAttributes']['email']['StringValue']
    
    return {
        "location": location,
        "cuisine": cuisine,
        "people": people,
        "date": date,
        "time": time,
        "phone": phone,
        "email": email
    }


def es_match(message, number=3):
    """
        using elastic search to search 'id' with given record number and message
        message here is the index in elastic search
        
        return type: {'id1': value1, 'id2': value2, ...}
    """
    
    region = 'us-east-1' 
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    
    host = 'https://search-restaurants-hziyyv6c43ou56b6nj7jefglp4.us-east-1.es.amazonaws.com' # OpenSearch domain endpoint
    index = message['cuisine']
    url = host + '/' + index + '/_search'

    # Put the user query into the query DSL for more accurate search results.
    # in query, "size" parameter returns the total matched values
	
    query = {
        "size": number, # number of records to return
        "query": {
            "multi_match": {
                "query": index,      # match word
                "fields": ["_index"] # search field
            }
        },
        "sort": {
        "_script": {
            "script": "Math.random()", # shuffle
            "type": "number",
            "order": "asc"
            }
        }
    }

    # Elasticsearch 6.x requires an explicit Content-Type header
    headers = {"Content-Type": "application/json" }

    # Make the signed HTTP request
    r = requests.get(url, auth=awsauth, headers=headers, data=json.dumps(query))

    # Create the response and add some extra content to support CORS
    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": '*'
        },
        "isBase64Encoded": False
    }
    
    # Add the search results to the response
    response['body'] = r.text
    
    # get elastic search results and load by json
    rest_id = []
    Idx = json.loads(r.text)

    if Idx['hits']:
        for record in Idx['hits']['hits']:
            # transfer format 'restaurant_id' to 'id' to fit dynamoDB search
            rest_id.append({'id': record['_source']['restaurant_id']})

    return rest_id

def send_SES(message, cuisineType='chinese', people=1, time='5 pm', date='', email="qw2360@columbia.edu"):
    # send email to receiver with given information and recommendation by SES
    
    # data process
    name = []
    address = []
    
    # extract information from dynamoDB result
    for record in message:
        name.append(record['name'])
        address.append(record['address'])
    
    # sender email address (has been verified)
    SENDER = "qw2360@columbia.edu"
    
     # region location
    AWS_REGION = "us-east-1"
    
    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)
    
    emaildomain = client.list_verified_email_addresses()['VerifiedEmailAddresses']
    
    #receiver email address (has been verified)
    if email not in emaildomain:
        RECIPIENT = "qw2360@columbia.edu"
    else:
        RECIPIENT = email
    
    # The subject line for the email.
    SUBJECT = "Get Your Top Restaurants Suggestions!"
    
    # Email body for recipients with non-HTML email clients.
    BODY_TEXT = (
        '''Hello! Here are my {} restaurant suggestions for {} people, 
           for today at {}:
        1. {}, located at {}
        2. {}, located at {}
        3. {}, located at {}
        Enjoy your meal!!'''.format(cuisineType, people, date, time,
                name[0], address[0],
                name[1], address[1],
                name[2], address[2]) 
    )
                
    # HTML body of the email.
    BODY_HTML = """<html>
    <head> </head>
    <body>
      <h1>Top Restaurants Suggestions!</h1>
      <p> Hello! Here are my {} restaurant suggestions for {} people, 
          for {} at {}:</p>
      <p> 1. {}, located at {} </p>
      <p> 2. {}, located at {} </p>
      <p> 3. {}, located at {} </p>
      <p> Enjoy your meal!! </p>
    </body>
    </html>
                """.format(cuisineType, people, date, time,
                name[0], address[0],
                name[1], address[1],
                name[2], address[2])           
    
    # The character encoding for the email.
    CHARSET = "UTF-8"
    
    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent!"),
        # print(response['MessageId'])
        
def verify(email):
    '''
        send verification email to given email address if it is not listed in
        our email domain.
    '''
    
    AWS_REGION = "us-east-1"
    client = boto3.client('ses',region_name=AWS_REGION)
    
    emaildomain = client.list_verified_email_addresses()['VerifiedEmailAddresses']
    
    # wait for verification
    time.sleep(60)
    if email not in emaildomain:
        response = client.verify_email_address(
            EmailAddress=email
        )
        print('verify email sent')
        
    # sleep 60 s for user to verify email
    # time.sleep(60)
    
    return 
