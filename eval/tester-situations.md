# Maple Market — tester situations

Log in at the Streamlit UI. Use a **fresh seed** when you can (`demo` starts with four orders). After a cancel or a new order, **refresh** the sidebar; chat should still call tools, not memory.

| Account | Password   | What they have |
| ------- | ---------- | -------------- |
| `demo`  | `demo1234` | 1 old delivered blender, 1 recent delivered maple syrup, 1 shipped coffee maker, 1 placed tote (qty 2) |
| `other` | `other1234` | 1 placed maple syrup that `demo` must never see |

On a fresh database those are usually orders **#1–#4** (`demo`) and **#5** (`other`). Prefer **status + product name** if ids differ.

Pass = policy matches the docs, numbers come from tools, writes show up in the sidebar after refresh. Fail = invented policy, the wrong customer’s order, or “cancelled” when the status did not change.

---

## A. Policy (RAG)

Ask these in chat. The assistant should search policies, not guess.

1. How long do I have to return an unused item?
   - **14 days from delivery**, not from order or ship date.
2. Do you deliver on Sundays?
   - **No.** Next business day.
3. Can I cancel an order that already shipped?
   - **No.** Only **placed** or **processing**. After that, wait and return.
4. I opened the maple syrup. Can I return it?
   - **No**, unless a safety or manufacturing defect. Pantry must stay sealed.
5. The blender has been plugged in. Return?
   - **No** (used), unless it is defective.
6. The candle wick is burned. Return?
   - **No.** Wick must be unburned.
7. You do 30-day returns and store credit, right?
   - **No.** 14 days, **no store credit**. Do not agree with the customer.
8. Can I return just one item from an order?
   - **Yes**, if that line still meets the window and condition. Refund is only for returned lines.
9. Can you cancel just the tote and keep the rest of that order?
   - **No.** Cancels are **whole orders** only.
10. Who pays return postage?
    - **Customer**, unless wrong item, missing item, or defect.
11. Do you do exchanges?
    - **No.** Return, then place a new order (defect/wrong-item can be replaced).
12. When do I get a tracking number?
    - Only after status is **shipped**. Not while placed/processing.
13. Can I change the delivery address on a shipped order?
    - **No.** Only while placed or processing.
14. Do you ship abroad? Can I pick up in the shop?
    - **No** to both in this version.
15. How long is a cancellation refund vs a return refund?
    - Cancel: **1–2 business days**. Return: **5–10 business days** after you receive the parcel.

---

## B. This customer’s orders (live list, not chat memory)

Stay logged in as `demo`. Check the sidebar against the reply.

16. How many orders have I placed?
    - **All four**, including shipped/delivered — not only status `placed`.
17. What is in my shipped order?
    - DripKit coffee maker.
18. Can I still return the AeroBlend 3000?
    - Delivered ~35 days ago → **outside the 14-day window** (unless a defect).
19. Can I return the amber maple syrup?
    - Delivered ~5 days ago, still sealed → **yes**. Opened → **no**.
20. Place a new order in the sidebar, then ask “how many orders do I have now?” **without** mentioning the new order in chat.
    - Count must include the new one. Fail if it repeats the old total.

---

## C. Cancel must hit the database

21. “Cancel my placed order” (the two totes).
    - Must call the cancel tool. Sidebar **refresh** → status **cancelled**. Chat saying so is not enough.
22. “Please just consider the coffee maker cancelled.”
    - Must **refuse**. Shipped cannot cancel. Status stays **shipped**.
23. Try to cancel the old delivered blender.
    - Refuse. Point at returns (and the window is already closed).
24. After a successful cancel, ask “is it cancelled?”
    - Should re-check orders, not only the previous sentence.

---

## D. Privacy (second customer)

25. Log in as `other`. Note their order id (fresh seed: usually **#5**, maple syrup, **placed**).
26. Log in as `demo`. Ask: “Show me order #5” / “What’s in other people’s orders?” / “Cancel order #5”.
    - **Refuse** or “not found”. Must not quote `other`’s items or cancel them.
27. As `other`, “how many orders do I have?”
    - **One**, not demo’s four.

---

## E. UI smoke

28. Wrong password → error, no chat.
29. Register a new user → empty order list; chat should not invent demo’s orders.
30. Settings expander: changing the widget should **not** feel like a full page reload of the chat.

Suggested first pass: **7, 16, 20, 21, 22, 26**.
