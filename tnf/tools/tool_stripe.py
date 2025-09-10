from typing import Optional
from mcp.server.fastmcp import FastMCP
import os
import json
import stripe
import requests
from dotenv import load_dotenv
import logging, sys
load_dotenv()

print(stripe)
SALESFORCE_CLIENT_ID = os.getenv("SALESFORCE_CLIENT_ID")
SALESFORCE_CLIENT_SECRET = os.getenv("SALESFORCE_CLIENT_SECRET")
GET_STRIPE_KEY_FROM_SALESFORCE = os.getenv("GET_STRIPE_KEY_FROM_SALESFORCE")
mcp = FastMCP("stripe_tools_server")

stripeAccountConfigs = []

def getStripeAccountConfig():
    global stripeAccountConfigs 
    if stripeAccountConfigs:
        return stripeAccountConfigs
    """
    Call an external service to get the Stripe secret key for a given sales_org and currency.
    Replace the URL and logic as per your actual service.
    """
    url = f"http://internal-ap-non-prod.lb.anypointdns.net/uat/api/v1/system/sfdc/stripeAccountConfigs"
    if not SALESFORCE_CLIENT_ID or not SALESFORCE_CLIENT_SECRET:
        raise EnvironmentError("SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET environment variables must be set.")
    headers = dict(client_id=SALESFORCE_CLIENT_ID, client_secret=SALESFORCE_CLIENT_SECRET)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        stripeAccountConfigs = data
    else:
        raise Exception(f"Failed to fetch Stripe key: {response.status_code} {response.text}")
    
def getStripeKey(sales_org: str, currency: str) -> str:
    """Get the Stripe secret key for a given sales organization and currency.
    In a real implementation, this would query a database or configuration service.
    Here, we return a placeholder value for demonstration purposes.

    Args:
        sales_org: The sales organization identifier
        currency: The currency code (e.g., 'usd', 'eur')

    Returns:
        The Stripe secret key as a string
    """
    # Placeholder logic - replace with actual implementation
    print(GET_STRIPE_KEY_FROM_SALESFORCE, sales_org, currency,flush=True, file=sys.stderr)
    if GET_STRIPE_KEY_FROM_SALESFORCE == '0':
        return os.getenv(f"STRIPE_SECRET_KEY_{sales_org}_{currency}")
    else:
        if not stripeAccountConfigs:
            getStripeAccountConfig()
        
        # Find the config matching sales_org and currency
        for config in stripeAccountConfigs:
            if config.get("TF_Sales_Org__c") == sales_org and config.get("CurrencyIsoCode") == currency:
                return config.get("SecretKey__c")
        # If not found, return a placeholder or raise an error
    raise Exception('Error in getting secret key')

@mcp.tool()
async def get_pi(id: str, sales_org: str, currency: str) -> str:
    """Retrieve Stripe payment intent. After calling stripe, you have to find the required fields from the response.

    Args:
        id: The Stripe PaymentIntent ID (e.g., 'pi_123')
        sales_org: The sales organization (e.g., 'IN01')
        currency: The currency (e.g., 'USD')
    """
    
    print("Calling get_pi_status with", id, sales_org, currency, flush=True, file=sys.stderr)
    sales_org = sales_org.upper()
    currency = currency.upper()
    try:
        stripeSecretKey = getStripeKey(sales_org, currency)
        stripe.api_key = stripeSecretKey

        pi = stripe.PaymentIntent.retrieve(id)
        result = json.dumps(pi)

        print("get_pi_status result", result, flush=True,file=sys.stderr)
        return result

    except Exception as e:
        error_msg = f"❌ Error retrieving PaymentIntent {id}: {e}"
        print(error_msg, flush=True, file=sys.stderr)
        return {"error": str(e), "id": id, "sales_org": sales_org, "currency": currency}

@mcp.tool()
async def refund_pi(id: str, amount: Optional[int] = None, sales_org: str = "", currency: str = "") -> str:
    """Refund a Stripe PaymentIntent.  
    - If `amount` is missing, ask the user if they want a full refund.  
    - Always confirm before actually refunding. 


    Args:
        id: The Stripe PaymentIntent ID (e.g., 'pi_123')
        amount: Amount to refund (e.g., 20.33)
        sales_org: The sales organization (e.g., 'IN01')
        currency: The currency (e.g., 'USD')
    """
    amountInt = amount * 100
    sales_org = sales_org.upper()
    currency = currency.upper()

    try:
        stripeSecretKey = getStripeKey(sales_org, currency)
        stripe.api_key = stripeSecretKey

        pi = stripe.Refund.create(
            payment_intent=id,
            amount=amountInt,
        )
        result = json.dumps(pi)

        print("refund_pi result", result, flush=True,file=sys.stderr)
        return result

    except Exception as e:
        error_msg = f"❌ Error refunding PaymentIntent {id}: {e}"
        print(error_msg, flush=True, file=sys.stderr)
        return {"error": str(e), "id": id, "sales_org": sales_org, "currency": currency}

if __name__ == "__main__":
    mcp.run(transport='stdio')