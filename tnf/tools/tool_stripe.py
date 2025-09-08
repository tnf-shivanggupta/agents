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
    Call an external service to get the Stripe secret key for a given salesOrg and currency.
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
    
def getStripeKey(salesOrg: str, currency: str) -> str:
    """Get the Stripe secret key for a given sales organization and currency.
    In a real implementation, this would query a database or configuration service.
    Here, we return a placeholder value for demonstration purposes.

    Args:
        salesOrg: The sales organization identifier
        currency: The currency code (e.g., 'usd', 'eur')

    Returns:
        The Stripe secret key as a string
    """
    # Placeholder logic - replace with actual implementation
    print(GET_STRIPE_KEY_FROM_SALESFORCE, salesOrg, currency,flush=True, file=sys.stderr)
    if GET_STRIPE_KEY_FROM_SALESFORCE == '0':
        return os.getenv(f"STRIPE_SECRET_KEY_{salesOrg}_{currency}")
    else:
        if not stripeAccountConfigs:
            getStripeAccountConfig()
        
        # Find the config matching salesOrg and currency
        for config in stripeAccountConfigs:
            if config.get("TF_Sales_Org__c") == salesOrg and config.get("CurrencyIsoCode") == currency:
                return config.get("SecretKey__c")
        # If not found, return a placeholder or raise an error
    raise Exception('Error in getting secret key')

@mcp.tool()
async def get_pi(id: str, salesOrg: str, currency: str) -> str:
    """Retrieve Stripe payment intent. After calling stripe, you have to find the required fields from the response.

    Args:
        id: The Stripe PaymentIntent ID (e.g., 'pi_123')
        salesOrg: The sales organization (e.g., 'IN01')
        currency: The currency (e.g., 'USD')
    """
    print("Calling get_pi_status with", id, salesOrg, currency, flush=True, file=sys.stderr)

    try:
        stripeSecretKey = getStripeKey(salesOrg, currency)
        stripe.api_key = stripeSecretKey

        pi = stripe.PaymentIntent.retrieve(id)
        result = json.dumps(pi)

        print("get_pi_status result", result, flush=True,file=sys.stderr)
        return result

    except Exception as e:
        error_msg = f"❌ Error retrieving PaymentIntent {id}: {e}"
        print(error_msg, flush=True, file=sys.stderr)
        return {"error": str(e), "id": id, "salesOrg": salesOrg, "currency": currency}

if __name__ == "__main__":
    mcp.run(transport='stdio')