class BodyLimit:
    def __init__(self, app, maximum=65536):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in ('POST', 'PUT', 'DELETE', 'PATCH'):
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body', b''))
            if size > self.maximum:
                await send({'type': 'http.response.start', 'status': 413, 'headers': [(b'content-type', b'application/json; charset=utf-8')]})
                await send({'type': 'http.response.body', 'body': b'{"error":"Permintaan terlalu besar."}'})
                return
            chunks.append(message)
            if not message.get('more_body', False):
                break
        index = 0
        async def replay():
            nonlocal index
            if index < len(chunks):
                message = chunks[index]
                index += 1
                return message
            return await receive()
        await self.app(scope, replay, send)
