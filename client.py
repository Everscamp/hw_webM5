# import asyncio

# import aiohttp


# async def client():
#     # session = aiohttp.ClientSession()
    
#     async with aiohttp.ClientSession() as session:
        
#         try:
#             response = await session.get("lo", timeout=10)
            
#             if response.ok:
#                 body = await response.text() 
#                 print(body[:300])
#             else:
#                 print("Not Ok")
#         except asyncio.TimeoutError as e:
#             print(f"{e}")
#         except aiohttp.ClientConnectorError as e:
#             print(f"{e}")

# if __name__ == '__main__':
#     asyncio.run(client())
