# lambda function one is used to check the error of input messages and delivery
# correct messages to lambda function three to process. Triggered when all the 
# required information are fulfilled in lex. 

import json
import boto3
from datetime import datetime, timezone, timedelta


# Create SQS client
sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/359634618028/Q1-test.fifo'

def lambda_handler(event, context):
    # TODO implement
    
    location = event["currentIntent"]["slots"]["location"]
    cuisine = event["currentIntent"]["slots"]["cuisine"]
    people = event["currentIntent"]["slots"]["people"]
    date = event["currentIntent"]["slots"]["date"]
    time = event["currentIntent"]["slots"]["time"]
    phone = event["currentIntent"]["slots"]["phone"]
    email = event["currentIntent"]["slots"]["email"]
    
    error = validation(date, time, phone) 
    if error[0] == "time":
        return {
                  "dialogAction": {
                        "type": "ElicitSlot",
                        "message": {
                          "contentType": "PlainText",
                          "content": error[1] + " What is your date?"
                        },
                       "intentName": "DiningSuggestionsIntent",
                       "slots": {
                          "location": location,
                          "cuisine": cuisine,
                          "people": people,
                          "phone": phone,
                          "email": email
                       },
                       "slotToElicit" : "date",
                    }
                }
    elif error[0] == "phone":
        return {
          "dialogAction": {
                "type": "ElicitSlot",
                "message": {
                  "contentType": "PlainText",
                  "content": error[1] + " What is your phone number?"
                },
               "intentName": "DiningSuggestionsIntent",
               "slots": {
                  "location": location,
                  "cuisine": cuisine,
                  "people": people,
                  "date": date,
                  "time": time,
                  "email": email
               },
               "slotToElicit" : "phone",
            }
        }
    
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageAttributes={
            'location': {
                'DataType': 'String',
                'StringValue': location
            },
            'cuisine': {
                'DataType': 'String',
                'StringValue': cuisine
            },
            'people': {
                'DataType': 'String',
                'StringValue': people
            },
            'date': {
                'DataType': 'String',
                'StringValue': date
            },
            'time': {
                'DataType': 'String',
                'StringValue': time
            },
            'phone': {
                'DataType': 'String',
                'StringValue': phone
            },
            'email': {
                'DataType': 'String',
                'StringValue': email
            }
        },
        MessageBody='Get recommendation according to user info.',
        MessageGroupId='chatbox'
    )

    return {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
                "contentType": "PlainText",
                "content": '''
                                You're all set!
                                You will have a verification email from me, 
                                please click and verify it within one minute to 
                                successfully receive suggestions from me.
                                Expect my suggestions shortly~ Have a good day!
                           '''
            }
        }
    }
    

def validation(date, time, phone):
    
    # Time Validation
    concat_time = date + " " + time
    
    timezone_offset = -5.0  # (UTC−05:00)
    tzinfo = timezone(timedelta(hours=timezone_offset))
    now = datetime.now(tzinfo)
    # print(now)
    
    ordered_date = datetime.strptime(concat_time, '%Y-%m-%d %H:%M').replace(tzinfo=tzinfo)
    # print(ordered_date)
    
    if(ordered_date < now):
        # print("You cannot order a restaurant at a past time.")
        return ["time","You cannot order a restaurant at a past time."]
    
    # Phone Validation
    if(len(phone) != 10):
        # print("You must input a valid US phone number.")
        return ["phone", "You must input a valid US phone number."]
        
    
    # Email Validation
    # ----------------
    
    return ["", ""]