from pathlib import Path

# bill_template.html lives in the project root (one level above this folder).
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "bill_template.html"


GUIDE = """\
# How to use the RetailOps invoice template

Resource `retailops://bill-template` is a ready-made, email-safe HTML invoice.
After `generate_customer_bill` succeeds, fill the template with the bill it returned
and email the result to the customer as an HTML email (htmlBody).

## Placeholders

| Placeholder          | Fill with                                                            |
|----------------------|----------------------------------------------------------------------|
| {{order_id}}         | `sale_id` from the bill                                              |
| {{order_date}}       | Sale date and time in IST, e.g. `11 Oct 2026, 10:35 PM`              |
| {{customer_name}}    | `customer_name`                                                      |
| {{mobile}}           | `mobile` (10 digits, no +91 - the template adds it)                  |
| {{email}}            | `email`                                                              |
| {{items}}            | One table row per entry in `items` (row format below)                |
| {{subtotal}}         | `subtotal`                                                           |
| {{discount}}         | `discount` (use `0` when there is none)                              |
| {{final_amount}}     | `final_amount`                                                       |
| {{loyalty_points}}   | `loyalty_points_earned`                                              |
| {{delivery_status}}  | Short status such as `Paid` or `Delivered at store`                  |

## Row format for {{items}}

Use `product_name`, `quantity`, `final_unit_price` and `total_price` from each item.
The exact `<tr>` markup is in the HTML comment right below `{{items}}` in the template;
copy it for every item.

## Rules

- Write every amount in Indian digit grouping, without decimals when it is a whole
  number of rupees: 324900 -> 3,24,900.
- The template already prints the rupee sign before {{subtotal}}, {{discount}} and
  {{final_amount}}, so put only the number there. Inside the {{items}} rows you must
  write the rupee sign yourself (e.g. ₹1,45,000), as shown in the row format.
- Only replace placeholders. Do not change the layout, colours, fonts or footer text.
- Remove the HTML comment that explains the row format before sending.
- Never show cost price or profit to the customer.
- Create the email as a DRAFT first and let the shop owner confirm before sending.
"""


def register_bill_resources(mcp):

    @mcp.resource(
        "retailops://bill-template",
        name="bill_template",
        description=(
            "Premium HTML invoice email template for RetailOps. Contains {{placeholders}} "
            "(order_id, order_date, customer_name, mobile, email, items, subtotal, discount, "
            "final_amount, loyalty_points, delivery_status). Read retailops://bill-template/guide "
            "first to see how to fill them."
        ),
        mime_type="text/html",
    )
    def bill_template() -> str:
        html = TEMPLATE_PATH.read_text(encoding="utf-8")
        if not html.strip():
            raise ValueError("bill_template.html is empty")
        return html

    @mcp.resource(
        "retailops://bill-template/guide",
        name="bill_template_guide",
        description="Instructions for filling the invoice template and emailing it to the customer.",
        mime_type="text/markdown",
    )
    def bill_template_guide() -> str:
        return GUIDE
