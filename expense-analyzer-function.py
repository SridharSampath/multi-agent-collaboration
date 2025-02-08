import json
import boto3
from decimal import Decimal

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = "multiAgent-UserTransactions"  # Update with your table name

# Helper function to convert Decimal values from DynamoDB to float
def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)  # Convert Decimal to float
    return obj

def lambda_handler(event, context):
    try:
        print("Event from Bedrock:", json.dumps(event, indent=2))

        agent = event.get('agent', 'Unknown Agent')
        actionGroup = event.get('actionGroup', 'Unknown Action Group')
        function = event.get('function', 'Unknown Function')

        # Extract parameters
        parameters_list = event.get("parameters", [])
        print("🛠 Extracted parameters list:", parameters_list)

        # Extract user_id (which is now the real name, like "Sam" or "John")
        user_id = None
        for param in parameters_list:
            if param.get("name") == "user_id" or param.get("name") == "name":  
                user_id = param.get("value")  # Use the name directly

        print(f"🔍 Extracted user_id: {user_id}")

        if not user_id:
            response_body = {
                "TEXT": {"body": "Error: Please provide your name to fetch transactions."}
            }
        else:
            # Query DynamoDB to fetch all transactions for this user
            table = dynamodb.Table(table_name)
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
            )
            transactions = response.get('Items', [])
            print("Retrieved transactions:", transactions)

            if not transactions:
                response_body = {
                    "TEXT": {"body": f"No transactions found for {user_id}."}
                }
            else:
                # Convert Decimals to float
                formatted_transactions = convert_decimals([
                    {
                        "transaction_id": txn.get("transaction_id", ""),
                        "date": txn.get("date", ""),
                        "category": txn.get("category", ""),
                        "amount": txn.get("amount", 0),
                        "merchant": txn.get("merchant", ""),
                        "payment_method": txn.get("payment_method", "")
                    }
                    for txn in transactions
                ])

                print("Final formatted transactions response:", formatted_transactions)

                response_body = {
                    "TEXT": {
                        "body": f"Here are the last {len(formatted_transactions)} transactions for {user_id}:\n" + 
                                "\n".join(
                                    [f"- {txn['date']} | {txn['category']} | ₹{txn['amount']} | {txn['merchant']} ({txn['payment_method']})" 
                                     for txn in formatted_transactions]
                                )
                    }
                }

        # Ensure the response follows Bedrock's format
        function_response = {
            "actionGroup": actionGroup,
            "function": function,
            "functionResponse": {
                "responseBody": response_body
            }
        }

        # Include session attributes (if needed)
        session_attributes = event.get("sessionAttributes", {})
        prompt_session_attributes = event.get("promptSessionAttributes", {})

        action_response = {
            "messageVersion": "1.0",
            "response": function_response,
            "sessionAttributes": session_attributes,
            "promptSessionAttributes": prompt_session_attributes
        }

        return action_response

    except Exception as e:
        print("Error occurred:", str(e))
        response_body = {
            "TEXT": {"body": f"Error fetching transactions: {str(e)}"}
        }

        function_response = {
            "actionGroup": event.get("actionGroup", ""),
            "function": function,
            "functionResponse": {
                "responseBody": response_body
            }
        }

        return {
            "messageVersion": "1.0",
            "response": function_response,
            "sessionAttributes": event.get("sessionAttributes", {}),
            "promptSessionAttributes": event.get("promptSessionAttributes", {})
        }
