import asyncio
import httpx


async def search_robocraze(query):

    url = "https://robocraze.com/search/suggest.json"

    params = {
        "q": query,
        "resources[type]": "product"
    }

    async with httpx.AsyncClient() as client:

        response = await client.get(
            url,
            params=params,
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
        )

        print("Status:", response.status_code)
        print("Content-Type:", response.headers.get("content-type"))

        if response.status_code != 200:
            print(await response.aread())
            return []
        print("Response:", response)
        data = response.json()

        return data


async def main():

    data = await search_robocraze("hcsr04")

    for product in data['resources']['results']['products']:
        print(product['title'])
        print(product['price'])

asyncio.run(main())