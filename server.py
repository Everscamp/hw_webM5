import asyncio
import logging

import httpx
import websockets
import names
from datetime import date, timedelta, datetime
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK
from aiopath import AsyncPath
from aiofile import async_open

logging.basicConfig(level=logging.INFO)
URL = 'https://api.privatbank.ua/p24api/exchange_rates?json&date=data_variable'

currencies = 'USD - Долар США. EUR - Євро. CHF - Швейцарський франк. \n\
                    GBP - Британський фунт. SEK - Шведська крона.\
                    XAU - Золото. CAD - Канадський долар. AUD - Австралійський долар. \n \
                    AZN - Азербайджанський манат. CNY - Юань Женьміньбі. CZK - Чеська крона. \n \
                    DKK - Данська крона. GEL - Грузинський ларі. HUF - Угорський форинт.  \n \
                    ILS - Новий ізраїльський шекель. JPY - Японська єна. KZT - Казахстанський теньге. \n \
                    MDL - Молдовський лей. NOK - Норвезька крона. PLN - Злотий. \n \
                    SGD - Сінгапурський долар. TRY - Турецька ліра. UZS - Узбецький сум.'


async def request(url: str) -> dict | str:
    async with httpx.AsyncClient(timeout=None) as client:
        r = await client.get(url)
        print(r)
        if r.status_code == 200:
            result = r.json()
            return result
        else:
            return "Не вийшло в мене взнати курс. Приват не відповідає :)"

def dayCounter(days):
    modified_date = date.today() - timedelta(days=days)
    return modified_date

def pb_handler(result, modifiedDay, currency=None):
        response = {modifiedDay:{}}
        for i in result['exchangeRate']:
            if "USD" in list(i.values()):
                response[modifiedDay].update({"USD": {'sale': i.get("saleRateNB"),
        'purchase': i.get("purchaseRateNB")}})
            
            if "EUR" in list(i.values()):
                response[modifiedDay].update({"EUR": {'sale': i.get("saleRateNB"),
        'purchase': i.get("purchaseRateNB")}})

            if currency and currency in list(i.values()):
                response[modifiedDay].update({currency: {'sale': i.get("saleRateNB"),
        'purchase': i.get("purchaseRateNB")}})
        print(response)
        return response

async def get_exchange(handler, days, currency=None):
    if days == 1:
        modifiedDay = dayCounter(int(days)).strftime("%d.%m.%Y")
        newUrl = URL.replace("data_variable", modifiedDay)
        result = await request(newUrl)
        return handler(result, modifiedDay, currency)
    
    if days > 1:
        listResponse = []
        for i in range(days):
            modifiedDay = dayCounter(int(i)).strftime("%d.%m.%Y")
            newUrl = URL.replace("data_variable", modifiedDay)
            result = await request(newUrl)
            print(newUrl)
            
            listResponse.append(handler(result, modifiedDay, currency))

        return listResponse

    return "Failed to retrieve data"

def ms_parser(message):
    raw_m = message.rsplit(" ")
    new_m = []
    if len(raw_m) == 1:
        new_m = [1, None]

    if len(raw_m) == 2:
        days = int(raw_m[1]) if raw_m[1].isnumeric() else 1
        currency = raw_m[1] if raw_m[1].isalpha() else None
        new_m = [days, currency]

    if len(raw_m) == 3:
        days = int(raw_m[1]) if raw_m[1].isnumeric() else 1
        currency = raw_m[2] if raw_m[2].isalpha() else None
        new_m = [days, currency]

    return new_m

async def log_file(currency=None):
    apath = AsyncPath("logging.txt")
    if not await apath.exists():
        async with async_open("logging.txt", 'w+') as afp:
            await afp.write(f'Exchange was used on {datetime.today()} for {currency if currency else "USD/EUR"} currency\n')
    elif await apath.exists():
        async with async_open("logging.txt", 'a+') as afp:
            await afp.write(f'Exchange was used on {datetime.today()} for {currency if currency else "USD/EUR"} currency\n')

class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distrubute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            if message.find("exchange") != -1:
                ms = ms_parser(message)
                print(ms)
                if ms[0] >= 10:
                    await self.send_to_clients("Only for period that is less than 10 days!")
                    continue
                exchange = await get_exchange(pb_handler, ms[0], ms[1])
                await log_file(ms[1])
                await self.send_to_clients(str(exchange))
            if message == "codes":
                await self.send_to_clients(currencies)
            elif message == 'Hello server':
                await self.send_to_clients("Привіт мої карапузи!")
            else:
                await self.send_to_clients(f"{ws.name}: {message}")

async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    asyncio.run(main())