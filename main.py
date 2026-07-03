from aiohttp import web, __version__


async def hello(request: web.Request) -> web.Response:
    return web.Response(text=f"Hello, aiohttp {__version__}\n")


def main() -> None:
    app = web.Application()
    app.add_routes([web.get("/", hello)])
    web.run_app(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()
