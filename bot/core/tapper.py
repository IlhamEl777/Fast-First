import asyncio
import json
from random import randint
from urllib.parse import unquote

import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from pyrogram.raw.functions.messages import RequestWebView

from bot.config import settings
from bot.exceptions import InvalidSession
from bot.utils import logger
from .headers import headers


async def gen_data_login(data_parser):
    data_user = json.loads(data_parser["user"])
    data = {
        "externalId": int(data_user["id"]),
        "firstName": data_user["first_name"],
        "gameId": 3,
        "initData": {
            "auth_date": data_parser["auth_date"],
            "hash": data_parser["hash"],
            "query_id": data_parser["query_id"],
            "user": data_parser["user"],
        },
        "language": "en",
        "lastName": data_user["last_name"],
        "refId": "",
        "username": data_user["username"],
    }

    return data


async def data_parsing(data):
    res = unquote(data)
    data = {}
    for i in res.split("&"):
        j = unquote(i)
        y, z = j.split("=")
        data[y] = z

    return data


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

    async def get_tg_web_data(self, proxy: str | None) -> str:
        try:
            if proxy:
                proxy = Proxy.from_str(proxy)
                proxy_dict = dict(
                    scheme=proxy.protocol,
                    hostname=proxy.host,
                    port=proxy.port,
                    username=proxy.login,
                    password=proxy.password
                )
            else:
                proxy_dict = None

            self.tg_client.proxy = proxy_dict

            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            web_view = await self.tg_client.invoke(
                RequestWebView(
                    peer=await self.tg_client.resolve_peer("FirstDuck_bot"),
                    bot=await self.tg_client.resolve_peer("FirstDuck_bot"),
                    platform="android",
                    from_bot_menu=False,
                    url="https://tgames-duck.bcsocial.net/",
                )
            )

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=7)

    async def bypas_captcha(self, http_client: aiohttp.ClientSession, data_captcha):
        captcha = data_captcha.replace("=", "")
        result = eval(captcha)
        url = "https://tgames-duck.bcsocial.net/panel/users/verifyCapcha"
        data = json.dumps({"code": result})

        # async with http_client.post(url, headers=headers, data=data) as res:
        async with http_client.post(url, data=data) as res:
            res_text = await res.text()
        if "ok" in res_text:
            logger.success(f"{self.session_name} | Success Bypass Captcha !")
        else:
            logger.error("Failed to bypass captcha, response: {}".format(res_text))

    async def login(self, http_client: aiohttp.ClientSession, data_login: str) -> dict:
        try:

            response = await http_client.post(
                url="https://tgames-duck.bcsocial.net/panel/users/login",
                json=data_login,
            )
            response.raise_for_status()

            response_json = await response.json()
            if "capcha" in response_json["data"].keys():
                if response_json["data"]["capcha"] != "":
                    logger.warning(f"{self.session_name} | CAPTCHA detected")
                    await self.bypas_captcha(http_client, response_json["data"]["capcha"])

            # logger.info(f" response_login | {response_json}")
            return response_json["data"]
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error : {error}")
            await asyncio.sleep(delay=7)

    async def send_taps(self, http_client: aiohttp.ClientSession, slaps: int, active_turbo: bool) -> dict:
        try:
            response = await http_client.post(
                url="https://tgames-duck.bcsocial.net/panel/games/claim",
                json={
                    "amount": slaps,
                },
            )
            response.raise_for_status()

            response_json = await response.json()

            # Periksa keberadaan kunci "message" dan "data"
            if "message" in response_json and response_json["message"] == 'incorrect time':
                logger.warning(f"{self.session_name} | incorrect time | Sleep {settings.SLEEP_INCORECT_TIME}s")
                await asyncio.sleep(settings.SLEEP_INCORECT_TIME)

            if "data" in response_json:
                return response_json["data"]
            else:
                logger.error(f"{self.session_name} | 'data' key not found in response: {response_json}")
                return {}

        except aiohttp.ClientResponseError as e:
            logger.error(f"{self.session_name} | HTTP error when Slapping: {e.status} - {e.message}")
            await asyncio.sleep(7)
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Slapping: {error}")
            await asyncio.sleep(7)

        return {}

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy | str) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def run(self, proxy: str | None) -> None:
        active_turbo = False

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            while True:
                try:

                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    res_parser = await data_parsing(tg_web_data)
                    data_login = await gen_data_login(res_parser)
                    profile_data = await self.login(http_client=http_client, data_login=data_login)

                    balance = profile_data["balance"]
                    tap_level = profile_data["earnByTap"]
                    level = profile_data["level"]

                    logger.info(
                        f"{self.session_name} | Balance: <c>{balance}</c> | Level: <m>{level}</m>"
                    )

                    tap = randint(a=settings.RANDOM_TAP_COUNT[0], b=settings.RANDOM_TAP_COUNT[1])

                    if active_turbo:
                        tap += settings.ADD_TAP_ON_TURBO

                    tap *= tap_level

                    player_data = await self.send_taps(http_client=http_client, slaps=tap, active_turbo=active_turbo)

                    if not player_data:
                        continue

                    new_balance = player_data['balance']
                    calc_slaps = new_balance - balance
                    balance = new_balance
                    total = profile_data["totalCoin"]

                    logger.success(f"{self.session_name} | Successful slapped! | "
                                   f"Balance: <c>{balance}</c> (<g>+{calc_slaps}</g>) | Total: <e>{total}</e>")

                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=7)

                else:
                    sleep_between_clicks = randint(a=settings.SLEEP_BETWEEN_TAP[0], b=settings.SLEEP_BETWEEN_TAP[1])

                    if active_turbo is True:
                        active_turbo = False

                    logger.warning(f"Sleep {sleep_between_clicks}s")
                    await asyncio.sleep(delay=sleep_between_clicks)


async def run_slapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
