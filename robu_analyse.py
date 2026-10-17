import asyncio
import json
import random
from playwright.async_api import async_playwright

mutation_addcart = """
mutation AddItemToCart($productId: ID!, $quantity: Int!, $isBuyNow: Boolean, $cartId: ID!) {
  addItemToCart(
    input: {
      productId: $productId
      quantity: $quantity
      isBuyNow: $isBuyNow
      cartId: $cartId
    }
  ) {
    status
    message
    code
    data {
      cartId
      grandTotal
      subTotal
      itemsCount
      itemsQty
      items {
        id
        product {
          id
          name
        }
        quantity
      }
    }
  }
}
"""

async def search_robu(componentlist):
    cart_id = ""

    async with async_playwright() as p:
        # Launch with common arguments to look like a normal user
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # Set standard viewport and modern user agent string
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        page = await context.new_page()
        search_response = None

        async def handle_response(response):
            nonlocal search_response
            if "/api/search/" in response.url:
                if response.status == 200:
                    try:
                        search_response = await response.json()
                        print(f" -> Successfully intercepted search data for current item.")
                    except Exception as e:
                        print("JSON parsing error:", e)

        page.on("response", handle_response)
        
        # Navigate to home once to clear initial Cloudflare checkpoint naturally
        print("Opening target website...")
        await page.goto("https://robu.in/", wait_until="domcontentloaded")
        await page.wait_for_timeout(random.randint(2000, 4000))

        for component in componentlist:
            search_response = None
            print(f"\nSearching for component: '{component}'...")

            # Direct navigation works, but we add realistic, non-uniform pacing
            await page.goto(
                f"https://robu.in/?s={component}&post_type=product",
                wait_until="domcontentloaded"
            )

            # Polling loop waiting for the asynchronous network intercept
            for _ in range(15):
                if search_response is not None:
                    break
                await page.wait_for_timeout(400)

            if search_response is None:
                print(f"Search API payload missed for '{component}'. Moving to next.")
                continue

            products = search_response.get("data", {}).get("products", [])
            if not products:
                print(f"Zero products matched search string for '{component}'.")
                continue

            target_product = products[0]
            print(f"Target Found: ID [{target_product['id']}] | Name: {target_product.get('name')}")

            # Structure the correct GraphQL arguments
            payload = {
                "operationName": "AddItemToCart",
                "variables": {
                    "cartId": cart_id,
                    "productId": str(target_product["id"]),
                    "quantity": 1,
                    "isBuyNow": False
                },
                "query": mutation_addcart.strip()
            }

            print("Injecting payload directly via active browser context session...")
            
            # THE FIX: Native window-level fetch that preserves valid cloudflare cookies
            result = await page.evaluate("""
                async (args) => {
                    const response = await fetch("https://robu.in/api/proxy/graphql/", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify(args.payload)
                    });
                    return response.json();
                }
            """, {"payload": payload})

            # Check for API-level payload errors
            if "errors" in result:
                print("GraphQL Execution Error Output:")
                print(json.dumps(result.get("errors"), indent=2))
                continue

            cart = result.get("data", {}).get("addItemToCart", {}).get("data", {})

            if cart:
                cart_id = cart.get("cartId", "")
                print("============================== STATUS ==============================")
                print("RUNNING CART ID :", cart_id)
                print("CURRENT SUBTOTAL:", cart.get("subTotal"))
                print("GRAND TOTAL     :", cart.get("grandTotal"))
                print("ITEMS COUNT     :", cart.get("itemsCount"))
                print("====================================================================")
            else:
                print("Could not unpack cart metadata. Response structure might have unexpected formatting.")

            # Human-like cool-down period between adding items
            await page.wait_for_timeout(random.randint(3000, 6000))

        await browser.close()

async def main():
    component_list = ["hcsr04", "arduino uno", "raspberry pi 4"]
    await search_robu(component_list)

if __name__ == "__main__":
    asyncio.run(main())
