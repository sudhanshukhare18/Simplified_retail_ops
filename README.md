# RetailOps v2

RetailOps has two parts that share the same databases (PostgreSQL for products, customers,
sales and users; MongoDB for open carts):

- **MCP server** (`main.py`) - lets Claude sell on behalf of a logged-in salesperson or manager.
- **Web dashboard** (`dashboard/`) - FastAPI + HTML + CSS for the manager, the salespersons and the billing counter.

## Setup

```
pip install -r requirements.txt
```

Put these in `.env` (the MCP server and the dashboard must use the **same** values):

```
DATABASE_URL=postgresql://...
MONGO_URI=mongodb://localhost:27017
SECRET_KEY=any-long-random-string      # signs dashboard logins
```

Create the first users (the tables are created automatically):

```
python create_user.py                        # demo users: salesperson / manager (change the passwords!)
python create_user.py alice SALESPERSON      # or your own user; asks for the password
```

## Run

```
python main.py                       # MCP server
uvicorn dashboard.app:app --reload   # dashboard at http://127.0.0.1:8000
```

## Roles

| Role | MCP tools | Dashboard |
| --- | --- | --- |
| SALESPERSON | search products, carts, offers, loyalty, bill, escalate to billing | own sales, product lookup, own counter requests |
| MANAGER | everything above + products, stock, offers, sales reports | sales stats, products, stock, offers, all sales |

Both roles can use the **Billing counter** page in the dashboard.

## Escalating a cart to the billing counter

Ask Claude to "send this cart to the billing counter". It logs in, then calls
`escalate_cart_to_billing`. The cart shows up on the dashboard's Billing counter page, where the
cashier confirms the customer details and clicks *Generate bill*. Claude can check progress with
`billing_request_status`, which also returns the final bill once it has been generated.
