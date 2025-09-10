# server_salesforce.py
import os
import sys
import logging
from typing import Any, Dict
import requests
from mcp.server.fastmcp import FastMCP
from simple_salesforce import Salesforce
from dotenv import load_dotenv
load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, )  # logs to stderr, not stdout

mcp = FastMCP("salesforce")
inst = None
# -------------------------------------------------------------------
# Connection helper
# -------------------------------------------------------------------
def _connect() -> Salesforce:
    global inst
    print("Salesforce instance", inst,flush=True, file=sys.stderr)
    
    if inst:
        return inst

    # Otherwise, do OAuth2 username-password flow
    logging.info("Fetching Salesforce access token using Client ID/Secret")
    print("Fetching Salesforce access token using Client ID/Secret",flush=True, file=sys.stderr)
    client_id = os.environ["SF_CLIENT_ID"]
    client_secret = os.environ["SF_CLIENT_SECRET"]
    username = os.environ["SF_USERNAME"]
    password = os.environ["SF_PASSWORD"]
    
    domain = os.getenv("SF_DOMAIN", "login")  # "login" for prod, "test" for sandbox
    token_url = f"https://{domain}.salesforce.com/services/oauth2/token"

    data = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
    }

    resp = requests.post(token_url, data=data).json()
    if "error" in resp:
        print("Error in getting Salesforce Instance ",resp, flush=True, file=sys.stderr)
        raise Exception(f"Salesforce OAuth failed: {resp}")

    access_token = resp["access_token"]
    instance_url = resp["instance_url"]

    logging.info("Got new Salesforce access token")
    print("Got new Salesforce access token",flush=True, file=sys.stderr)
    inst = Salesforce(instance_url=instance_url, session_id=access_token)
    return inst

# -------------------------------------------------------------------
# MCP Tools
# -------------------------------------------------------------------
@mcp.tool()
def get_order(order_id: str) -> Dict[str, Any]:
    """Get the order details from Salesforce
    
    - If order_id is not passed, ask for it first.
    
    Args:
        order_id: Required. Id of salesforce Order
    """
    print('get_order order_id', order_id, flush=True, file=sys.stderr)
    sf = _connect()
    query = f"SELECT Fields(All) from Order Where Id = '{order_id}'"
    print('get_order Query', query, flush=True, file=sys.stderr)
    
    res = sf.query(query)
    return res


# -------------------------------------------------------------------
# Run server
# -------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
